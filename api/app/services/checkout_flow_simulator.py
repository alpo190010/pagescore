"""End-to-end checkout flow simulator for Shopify stores.

Drives a real headless browser through the buyer flow:

    1. Render the product page (provides variant id + cookies)
    2. POST /cart/add.js with the chosen variant
    3. Sanity-check /cart.json (item_count > 0)
    4. Navigate to /checkout and follow Shopify's redirect to
       /checkouts/c/<token> or /checkouts/cn/<token>
    5. Capture the rendered checkout HTML
    6. Parse ground-truth signals via checkout_page_parser

Failures are classified into a small enum so callers can distinguish
between "we couldn't see it" vs "the store has a real problem" when
rendering results:

    out_of_stock, password_protected, bot_wall, timeout,
    variant_not_found, checkout_redirect, network_error,
    invalid_shopify_store, empty_html

This service never raises on known failure modes; it always returns a
``CheckoutPageSignals`` with ``reached_checkout=False`` and a
``failure_reason``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.services.checkout_page_parser import (
    CheckoutPageSignals,
    parse_checkout_page,
    unreached,
)

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_CHROMIUM_ARGS: list[str] = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
]

_CHECKOUT_URL_RE = re.compile(r"/checkouts/c[n]?/[A-Za-z0-9_-]+")
# Match an <input> tag that has BOTH type="password" and name="password",
# regardless of attribute order.
_SHOPIFY_PASSWORD_PAGE_RE = re.compile(
    r'<input\b(?=[^>]*\btype="password")(?=[^>]*\bname="password")[^>]*>',
    re.I,
)


@dataclass(frozen=True)
class FlowResult:
    """Wrapper combining parsed signals with raw capture metadata.

    Useful for logging / observability; callers that only want signals
    can access ``result.signals``.
    """

    signals: CheckoutPageSignals
    final_url: str | None
    duration_ms: int
    variant_id: int | None


async def simulate_checkout_flow(
    product_url: str,
    timeout_s: float = 45.0,
) -> FlowResult:
    """Drive the full buyer flow against a Shopify store.

    Args:
        product_url: A product detail page URL on the target store,
            e.g. ``https://www.allbirds.com/products/tree-loungers``.
            The store origin is derived from this URL.
        timeout_s: Overall wall-clock budget. If exceeded, returns a
            ``timeout`` failure.

    Returns:
        A :class:`FlowResult` with parsed signals. On any failure the
        signals have ``reached_checkout=False`` and ``failure_reason``
        set.
    """
    start = time.monotonic()
    try:
        return await asyncio.wait_for(
            _run_flow(product_url, start),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        elapsed = int((time.monotonic() - start) * 1000)
        logger.warning("Checkout flow timed out after %d ms for %s", elapsed, product_url)
        return FlowResult(
            signals=unreached("timeout"),
            final_url=None,
            duration_ms=elapsed,
            variant_id=None,
        )


async def _run_flow(product_url: str, start: float) -> FlowResult:
    origin = _origin_of(product_url)
    variant_id: int | None = None
    final_url: str | None = None

    async with async_playwright() as pw:
        browser = None
        try:
            browser = await pw.chromium.launch(
                headless=True,
                args=_CHROMIUM_ARGS,
            )
            ctx = await browser.new_context(
                user_agent=_UA,
                viewport={"width": 1366, "height": 900},
                locale="en-US",
            )
            page = await ctx.new_page()

            # ---- Step 1: load the PDP ---------------------------------
            try:
                resp = await page.goto(
                    product_url,
                    wait_until="domcontentloaded",
                    timeout=20_000,
                )
            except PlaywrightTimeoutError:
                return _fail("timeout", start, final_url, variant_id)
            except PlaywrightError as exc:
                logger.warning("PDP navigation failed for %s: %s", product_url, exc)
                return _fail("network_error", start, final_url, variant_id)

            if resp and resp.status >= 500:
                return _fail("network_error", start, final_url, variant_id)

            pdp_html = await page.content()

            # Shopify password-protected storefronts return the password
            # page for every URL.
            if _is_password_page(pdp_html, page.url, origin):
                return _fail("password_protected", start, final_url, variant_id)

            # Canonicalize the origin using the post-redirect URL. Many
            # Shopify stores redirect bare-domain to www (or to a locale
            # subdomain), and cookies are scoped to the canonical host.
            # If we kept using the input's origin for /cart/add.js and
            # /checkout, the request context's cookies wouldn't match and
            # Shopify would redirect us back to the homepage with an
            # empty session. Use page.url — it reflects all redirects
            # Chromium followed on the PDP load.
            try:
                canonical_origin = _origin_of(page.url)
                if canonical_origin != origin:
                    logger.info(
                        "Canonical origin changed after redirect: %s -> %s",
                        origin,
                        canonical_origin,
                    )
                    origin = canonical_origin
            except ValueError:
                pass

            # ---- Step 2: pick a variant id ---------------------------
            # Prefer /products.json because it surfaces an
            # ``available`` flag; this avoids the common case where the
            # PDP's default variant is out of stock. Fall back to PDP
            # extraction if the feed is unavailable (blocked, custom
            # theme, Shopify Plus storefront with feed disabled).
            variant_candidates = await _candidate_variants(ctx, origin, pdp_html)
            if not variant_candidates:
                return _fail("variant_not_found", start, final_url, variant_id)

            # ---- Step 3: POST /cart/add.js (with fallback retries) --
            add_status: int | None = None
            for candidate in variant_candidates:
                try:
                    add_resp = await ctx.request.post(
                        f"{origin}/cart/add.js",
                        form={"id": str(candidate), "quantity": "1"},
                        headers={
                            "Accept": "application/json",
                            "X-Requested-With": "XMLHttpRequest",
                        },
                        timeout=20_000,
                    )
                except PlaywrightError as exc:
                    logger.warning("/cart/add.js POST failed for %s: %s", origin, exc)
                    return _fail("network_error", start, final_url, candidate)

                add_status = add_resp.status
                if add_resp.ok:
                    variant_id = candidate
                    break
                if add_resp.status == 404:
                    return _fail("invalid_shopify_store", start, final_url, candidate)
                # On 422 (OOS/unavailable) or 5xx, keep trying other
                # candidates before giving up.

            if variant_id is None:
                # All candidates rejected — surface the most recent
                # status for debugging but classify based on the
                # dominant failure shape.
                if add_status == 422:
                    return _fail("out_of_stock", start, final_url, variant_candidates[-1])
                return _fail("network_error", start, final_url, variant_candidates[-1])

            # ---- Step 4: sanity check /cart.json ---------------------
            try:
                cart_resp = await ctx.request.get(
                    f"{origin}/cart.json", timeout=10_000
                )
                if cart_resp.ok:
                    cart_body = await cart_resp.json()
                    if not cart_body.get("item_count"):
                        return _fail("out_of_stock", start, final_url, variant_id)
            except (PlaywrightError, json.JSONDecodeError):
                # Non-fatal; continue to checkout even if the sanity
                # check fails.
                pass

            # ---- Step 5: navigate to /checkout -----------------------
            try:
                resp = await page.goto(
                    f"{origin}/checkout",
                    wait_until="domcontentloaded",
                    timeout=30_000,
                )
            except PlaywrightTimeoutError:
                return _fail("timeout", start, final_url, variant_id)
            except PlaywrightError as exc:
                logger.warning("/checkout navigation failed for %s: %s", origin, exc)
                return _fail("network_error", start, final_url, variant_id)

            final_url = page.url

            if resp and resp.status >= 500:
                return _fail("network_error", start, final_url, variant_id)

            # Give React / wallet iframes a moment to paint before we
            # scrape the HTML.
            await page.wait_for_timeout(4_000)

            # Did Shopify actually route us to a checkout URL?
            if not _CHECKOUT_URL_RE.search(final_url or ""):
                # Classify why. Common cases:
                # - Cloudflare/PerimeterX bot challenge
                # - Back-to-cart redirect (empty cart, session issue)
                # - Password page on checkout subdomain
                checkout_html = await page.content()
                if _is_bot_wall(checkout_html):
                    return _fail("bot_wall", start, final_url, variant_id)
                if _is_password_page(checkout_html, final_url, origin):
                    return _fail("password_protected", start, final_url, variant_id)
                return _fail("checkout_redirect", start, final_url, variant_id)

            checkout_html = await page.content()
            if not checkout_html:
                return _fail("empty_html", start, final_url, variant_id)
            if _is_bot_wall(checkout_html):
                return _fail("bot_wall", start, final_url, variant_id)

            # ---- Step 6: parse ---------------------------------------
            signals = parse_checkout_page(checkout_html, final_url=final_url)
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "Checkout flow for %s: flavor=%s wallets=%d bnpl=%d duration=%dms",
                origin,
                signals.checkout_flavor,
                signals.wallet_count,
                signals.bnpl_count,
                duration_ms,
            )
            return FlowResult(
                signals=signals,
                final_url=final_url,
                duration_ms=duration_ms,
                variant_id=variant_id,
            )

        finally:
            if browser is not None:
                await browser.close()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _origin_of(url: str) -> str:
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        raise ValueError(f"Invalid product URL: {url!r}")
    return f"{p.scheme}://{p.netloc}"


def _extract_variant_id(pdp_html: str) -> int | None:
    """Pull a variant id from a Shopify product detail page.

    Tries a cascade of patterns because themes vary:
        1. <input type="hidden" name="id" value="..."> inside add-to-cart form
        2. ShopifyAnalytics.meta.product.variants[0].id in inline script
        3. JSON-LD offers.sku with numeric id
        4. <form action="/cart/add"...><input name="id" value="..."> (any form)
    """
    # 1) hidden form input — most common on Liquid themes
    for match in re.finditer(
        r'<input[^>]+name="id"[^>]+value="(\d{8,})"', pdp_html
    ):
        return int(match.group(1))

    # 2) ShopifyAnalytics meta
    m = re.search(
        r'"variants"\s*:\s*\[\s*\{[^}]*"id"\s*:\s*(\d+)', pdp_html
    )
    if m:
        return int(m.group(1))

    # 3) productVariants structured data
    m = re.search(r'variantId["\']?\s*[:=]\s*["\']?(\d{8,})', pdp_html)
    if m:
        return int(m.group(1))

    return None


async def _candidate_variants(
    ctx, origin: str, pdp_html: str
) -> list[int]:
    """Return an ordered list of variant ids to try against /cart/add.js.

    Ordering is "most likely to succeed first":

        1. Variants flagged ``available=true`` in ``/products.json``.
           This feed is served by Shopify itself and filters to in-stock
           variants, so it's by far the most reliable source.
        2. The variant id parsed from the PDP markup (often the user's
           default / selected variant).

    Up to 5 candidates are returned; the simulator keeps trying until
    one succeeds or the list is exhausted.
    """
    candidates: list[int] = []

    # Source 1: /products.json feed (available-only)
    try:
        resp = await ctx.request.get(
            f"{origin}/products.json?limit=25", timeout=15_000
        )
        if resp.ok:
            try:
                data = await resp.json()
            except Exception:
                data = {}
            for prod in data.get("products", []):
                for v in prod.get("variants", []):
                    if v.get("available") and v.get("id"):
                        candidates.append(int(v["id"]))
                        break  # first available variant per product
                if len(candidates) >= 4:
                    break
    except PlaywrightError:
        pass

    # Source 2: the PDP's declared variant (de-duped)
    pdp_variant = _extract_variant_id(pdp_html)
    if pdp_variant is not None and pdp_variant not in candidates:
        candidates.append(pdp_variant)

    return candidates[:5]


def _is_password_page(html: str, final_url: str | None, origin: str) -> bool:
    if final_url and "/password" in final_url:
        return True
    # Shopify's stock password page ships a distinctive markup
    if _SHOPIFY_PASSWORD_PAGE_RE.search(html) and "shopify" in html.lower():
        return True
    return False


def _is_bot_wall(html: str) -> bool:
    lower = html.lower()
    # Cloudflare
    if "cf-challenge" in lower or "cloudflare" in lower and "challenge" in lower:
        return True
    # PerimeterX / Kasada / other bot-detection vendors
    if "_pxcaptcha" in lower or "perimeterx" in lower:
        return True
    if "datadome" in lower and "blocked" in lower:
        return True
    # Generic "Are you a human?" markers
    if "verify you are a human" in lower or "unusual traffic" in lower:
        return True
    return False


def _fail(
    reason: str,
    start: float,
    final_url: str | None,
    variant_id: int | None,
) -> FlowResult:
    duration_ms = int((time.monotonic() - start) * 1000)
    logger.info(
        "Checkout flow failed (%s) after %dms; variant=%s url=%s",
        reason,
        duration_ms,
        variant_id,
        final_url,
    )
    return FlowResult(
        signals=unreached(reason),
        final_url=final_url,
        duration_ms=duration_ms,
        variant_id=variant_id,
    )
