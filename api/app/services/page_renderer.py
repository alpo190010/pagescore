"""Playwright-based headless Chromium page renderer.

Launches a headless Chromium instance, navigates to a URL, waits for
network-idle, and returns the fully rendered DOM HTML including
JS-loaded content (e.g. review widgets on Shopify pages).

Also provides :func:`measure_mobile_cta` which renders at a 375×812
mobile viewport, locates the primary add-to-cart CTA, measures its
bounding box, checks above-fold visibility, and detects sticky
behaviour after scrolling.
"""

from __future__ import annotations

import logging
import time

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

_CHROMIUM_ARGS: list[str] = [
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-gpu",
]

# Mobile viewport matching iPhone 13/14 (375×812 logical pixels).
_MOBILE_VIEWPORT = {"width": 375, "height": 812}


async def render_page(url: str, timeout_ms: int = 30_000) -> str:
    """Render a page with headless Chromium and return the full DOM HTML.

    Navigates with ``networkidle`` wait, but if the page never reaches
    network-idle (common with heavy analytics/tracking scripts), falls
    back to ``domcontentloaded`` + a short settle delay so we still
    capture JS-rendered content like review widgets.

    Args:
        url: The URL to navigate to and render.
        timeout_ms: Maximum time in milliseconds to wait for navigation
            (including networkidle). Defaults to 30 000 ms.

    Returns:
        The fully rendered DOM HTML as a string.

    Raises:
        PlaywrightTimeoutError: If even the fallback navigation fails.
        RuntimeError: If Chromium crashes or cannot start.
    """
    browser = None
    start = time.monotonic()

    async with async_playwright() as pw:
        try:
            browser = await pw.chromium.launch(
                headless=True,
                args=_CHROMIUM_ARGS,
            )
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            except PlaywrightTimeoutError:
                # networkidle never settled (common with analytics-heavy
                # e-commerce pages). The page is already loaded and JS has
                # been running — just give widgets a moment to paint.
                elapsed_ms = (time.monotonic() - start) * 1_000
                logger.warning(
                    "networkidle timed out for %s after %.0f ms — "
                    "capturing current content after settle delay",
                    url,
                    elapsed_ms,
                )
                await page.wait_for_timeout(3_000)

            html = await page.content()

            elapsed_ms = (time.monotonic() - start) * 1_000
            logger.info(
                "Rendered %s in %.0f ms (%d chars)",
                url,
                elapsed_ms,
                len(html),
            )
            return html

        except PlaywrightError as exc:
            elapsed_ms = (time.monotonic() - start) * 1_000
            logger.error(
                "Chromium error rendering %s after %.0f ms: %s",
                url,
                elapsed_ms,
                exc,
            )
            raise RuntimeError(
                f"Chromium failed to render {url}: {exc}"
            ) from exc

        finally:
            if browser is not None:
                await browser.close()


# ---------------------------------------------------------------------------
# Mobile CTA measurement (Playwright Layer 2)
# ---------------------------------------------------------------------------

# JavaScript executed in the mobile page context to locate and measure
# the primary add-to-cart CTA button.
_CTA_MEASURE_JS = """
() => {
    // Selector cascade matching mobile_cta_detector.py
    const selectors = [
        'form[action*="/cart/add"] button[type="submit"]',
        '.product-form__submit',
        'button[name="add"]',
        '[data-add-to-cart]',
        '#AddToCart',
        '.btn--add-to-cart',
        '.btn-add-to-cart',
        '.add-to-cart',
    ];

    let btn = null;
    for (const sel of selectors) {
        btn = document.querySelector(sel);
        if (btn) break;
    }

    // Text-content fallback
    if (!btn) {
        for (const el of document.querySelectorAll('button')) {
            if (/add\\s*to\\s*cart|buy\\s*now/i.test(el.textContent)) {
                btn = el;
                break;
            }
        }
    }

    // input[type=submit] inside cart form
    if (!btn) {
        btn = document.querySelector('form[action*="/cart/add"] input[type="submit"]');
    }

    if (!btn) return null;

    const rect = btn.getBoundingClientRect();
    const style = window.getComputedStyle(btn);
    return {
        width: rect.width,
        height: rect.height,
        top: rect.top,
        bottom: rect.bottom,
        position: style.position,
        viewportHeight: window.innerHeight,
        viewportWidth: window.innerWidth,
    };
}
"""

_CTA_POST_SCROLL_JS = """
() => {
    const selectors = [
        'form[action*="/cart/add"] button[type="submit"]',
        '.product-form__submit',
        'button[name="add"]',
        '[data-add-to-cart]',
        '#AddToCart',
        '.btn--add-to-cart',
        '.btn-add-to-cart',
        '.add-to-cart',
    ];

    let btn = null;
    for (const sel of selectors) {
        btn = document.querySelector(sel);
        if (btn) break;
    }
    if (!btn) {
        for (const el of document.querySelectorAll('button')) {
            if (/add\\s*to\\s*cart|buy\\s*now/i.test(el.textContent)) {
                btn = el;
                break;
            }
        }
    }
    if (!btn) {
        btn = document.querySelector('form[action*="/cart/add"] input[type="submit"]');
    }

    if (!btn) return null;

    const rect = btn.getBoundingClientRect();
    const style = window.getComputedStyle(btn);
    return {
        top: rect.top,
        bottom: rect.bottom,
        position: style.position,
        viewportHeight: window.innerHeight,
    };
}
"""


async def measure_mobile_cta(url: str, timeout_ms: int = 15_000) -> dict | None:
    """Render page at mobile viewport and measure CTA button properties.

    Launches a separate headless Chromium instance at 375×812 (iPhone
    13/14), locates the primary add-to-cart button, measures its
    bounding box, checks whether it's above the fold, then scrolls
    600 px and re-checks to detect sticky/fixed positioning.

    Args:
        url: The URL to navigate to and measure.
        timeout_ms: Maximum navigation timeout in milliseconds.

    Returns:
        A dict with measurement keys matching
        :class:`MobileCtaSignals` Playwright fields, or ``None`` if
        measurement fails (CTA not found, timeout, Chromium error).
    """
    browser = None
    start = time.monotonic()

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=_CHROMIUM_ARGS,
            )
            page = await browser.new_page(viewport=_MOBILE_VIEWPORT)

            try:
                await page.goto(
                    url, wait_until="domcontentloaded", timeout=timeout_ms
                )
            except PlaywrightTimeoutError:
                elapsed_ms = (time.monotonic() - start) * 1_000
                logger.warning(
                    "mobile CTA: domcontentloaded timed out for %s after %.0f ms "
                    "— attempting measurement on partial page",
                    url,
                    elapsed_ms,
                )
                await page.wait_for_timeout(2_000)

            # Measure CTA before scroll
            initial = await page.evaluate(_CTA_MEASURE_JS)
            if initial is None:
                logger.info(
                    "mobile CTA: no add-to-cart button found on %s", url
                )
                return None

            vp_h = initial["viewportHeight"]
            vp_w = initial["viewportWidth"]
            width = initial["width"]
            height = initial["height"]

            above_fold = (initial["bottom"] <= vp_h) and (initial["top"] >= 0)
            in_thumb_zone = initial["top"] >= (vp_h * 0.6)

            # Scroll 600px and re-measure for sticky detection
            await page.evaluate("window.scrollBy(0, 600)")
            await page.wait_for_timeout(300)  # Allow CSS transitions

            post = await page.evaluate(_CTA_POST_SCROLL_JS)
            is_sticky = False
            if post is not None:
                pos = post.get("position", "")
                if pos in ("fixed", "sticky"):
                    is_sticky = True
                elif post["top"] >= 0 and post["bottom"] <= post["viewportHeight"]:
                    # Button is still in viewport after scrolling — likely sticky
                    is_sticky = True

            elapsed_ms = (time.monotonic() - start) * 1_000
            logger.info(
                "mobile CTA measured for %s in %.0f ms: %.0f×%.0f px, "
                "above_fold=%s, sticky=%s, thumb_zone=%s",
                url,
                elapsed_ms,
                width,
                height,
                above_fold,
                is_sticky,
                in_thumb_zone,
            )

            return {
                "button_width_px": width,
                "button_height_px": height,
                "meets_min_44px": width >= 44 and height >= 44,
                "meets_optimal_60_72px": 60 <= height <= 72,
                "above_fold": above_fold,
                "is_sticky": is_sticky,
                "in_thumb_zone": in_thumb_zone,
                "is_full_width": width >= (vp_w * 0.9),
            }

    except (PlaywrightError, PlaywrightTimeoutError, Exception) as exc:
        elapsed_ms = (time.monotonic() - start) * 1_000
        logger.warning(
            "mobile CTA measurement failed for %s after %.0f ms: %s",
            url,
            elapsed_ms,
            exc,
        )
        return None

    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass
