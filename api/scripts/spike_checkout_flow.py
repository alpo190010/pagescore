"""Spike: can we drive a headless browser through add-to-cart -> /checkouts/c/ on a live Shopify store?

Throwaway. Proves feasibility before we build the real simulator.

Usage:
    /Users/aleksandrephatsatsia/projects/alpo/.venv/bin/python api/scripts/spike_checkout_flow.py <origin>

Examples:
    .../python api/scripts/spike_checkout_flow.py https://www.allbirds.com
    .../python api/scripts/spike_checkout_flow.py https://shop.gymshark.com
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_OUT_DIR = Path(__file__).parent / "spike_output"


async def run(origin: str) -> None:
    origin = origin.rstrip("/")
    host = urlparse(origin).netloc.replace(":", "_")
    _OUT_DIR.mkdir(exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        ctx = await browser.new_context(
            user_agent=_UA,
            viewport={"width": 1366, "height": 900},
            locale="en-US",
        )
        page = await ctx.new_page()

        # -- Step 1: discover a product URL via /products.json --------------
        print(f"[1] Probing {origin}/products.json ...")
        variant_id: int | None = None
        product_handle: str | None = None
        try:
            resp = await ctx.request.get(
                f"{origin}/products.json?limit=25", timeout=20_000
            )
            print(f"    HTTP {resp.status}")
            if resp.ok:
                data = await resp.json()
                for prod in data.get("products", []):
                    for v in prod.get("variants", []):
                        if v.get("available"):
                            variant_id = v["id"]
                            product_handle = prod["handle"]
                            print(
                                f"    Picked variant_id={variant_id} "
                                f"from product '{product_handle}'"
                            )
                            break
                    if variant_id:
                        break
        except Exception as exc:
            print(f"    products.json probe failed: {exc}")

        # Fallback: load homepage and scrape first /products/ link, then PDP
        if not variant_id:
            print(f"[1b] Fallback: loading homepage {origin} ...")
            await page.goto(origin, wait_until="domcontentloaded", timeout=30_000)
            html = await page.content()
            m = re.search(r'href="(/products/[^"?#]+)"', html)
            if not m:
                print("    Could not find /products/ link on homepage.")
                return
            pdp_url = origin + m.group(1)
            print(f"    PDP: {pdp_url}")
            await page.goto(pdp_url, wait_until="domcontentloaded", timeout=30_000)

            pdp_html = await page.content()
            # Try to find a variant id via form input
            mv = re.search(
                r'<input[^>]+name="id"[^>]+value="(\d+)"', pdp_html
            )
            if mv:
                variant_id = int(mv.group(1))
                print(f"    Extracted variant_id={variant_id} from PDP form.")
            else:
                # Try ShopifyAnalytics meta.product.variants
                mm = re.search(
                    r'"variants"\s*:\s*\[\s*\{\s*"id"\s*:\s*(\d+)', pdp_html
                )
                if mm:
                    variant_id = int(mm.group(1))
                    print(
                        f"    Extracted variant_id={variant_id} "
                        f"via ShopifyAnalytics JSON."
                    )

        if not variant_id:
            print("FAIL: could not find any variant_id. Aborting.")
            return

        # -- Step 2: POST /cart/add.js -----------------------------------
        print(f"[2] POST {origin}/cart/add.js id={variant_id} ...")
        add_resp = await ctx.request.post(
            f"{origin}/cart/add.js",
            form={"id": str(variant_id), "quantity": "1"},
            timeout=20_000,
            headers={
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        print(f"    HTTP {add_resp.status}")
        add_text = await add_resp.text()
        if not add_resp.ok:
            print(f"    Body (first 400 chars): {add_text[:400]}")
            # 422 commonly means out of stock or variant ID mismatch
            if add_resp.status == 422:
                print("    (422: variant likely unavailable / out of stock)")
            print("FAIL: add-to-cart rejected.")
            return
        try:
            add_json = json.loads(add_text)
            print(
                f"    Added. product_title={add_json.get('product_title')!r} "
                f"line_price={add_json.get('line_price')}"
            )
        except json.JSONDecodeError:
            print("    Response was not JSON (possible HTML redirect).")

        # -- Step 3: sanity check /cart.json -----------------------------
        cart_resp = await ctx.request.get(
            f"{origin}/cart.json", timeout=15_000
        )
        print(f"[3] GET {origin}/cart.json -> HTTP {cart_resp.status}")
        if cart_resp.ok:
            cart = await cart_resp.json()
            print(f"    item_count={cart.get('item_count')} total_price={cart.get('total_price')}")

        # -- Step 4: navigate to /checkout -------------------------------
        print(f"[4] Navigating to {origin}/checkout ...")
        t0 = time.monotonic()
        try:
            resp = await page.goto(
                f"{origin}/checkout",
                wait_until="domcontentloaded",
                timeout=45_000,
            )
        except Exception as exc:
            print(f"    navigation error: {exc}")
            return
        elapsed = (time.monotonic() - t0) * 1000
        final_url = page.url
        print(f"    final url: {final_url}  (status {resp.status if resp else '?'}, {elapsed:.0f} ms)")

        if "/checkouts/" not in final_url:
            print(
                "WARN: did NOT land on /checkouts/c/ — may be redirected to "
                "login, password page, cart, or bot wall."
            )

        # Give JS a moment to paint wallet buttons
        await page.wait_for_timeout(4_000)

        html = await page.content()
        print(f"    HTML size: {len(html)} chars")

        # Quick heuristics
        indicators = {
            "shop_pay_button": ("shop-pay" in html.lower() or "shop_pay" in html.lower()),
            "apple_pay_button": ("apple-pay" in html.lower() or "apple_pay" in html.lower() or "applepay" in html.lower()),
            "google_pay_button": ("google-pay" in html.lower() or "google_pay" in html.lower() or "gpay" in html.lower()),
            "klarna": "klarna" in html.lower(),
            "afterpay": "afterpay" in html.lower() or "clearpay" in html.lower(),
            "affirm": "affirm" in html.lower(),
            "checkout_email_input": bool(re.search(r'name="checkout\[email\]"', html)),
            "customer_password_field": bool(re.search(r'name="customer\[password\]"', html)),
            "one_page_markers_all3": all(
                m in html for m in ("contact_information", "shipping_method", "payment_method")
            ),
            "cloudflare_challenge": "cf-challenge" in html.lower() or "cloudflare" in html.lower() and "challenge" in html.lower(),
            "shopify_password_page": "password" in html.lower() and "name=\"password\"" in html,
        }
        print("[5] Checkout page indicators:")
        for k, v in indicators.items():
            print(f"    {k}: {v}")

        out = _OUT_DIR / f"checkout_{host}.html"
        out.write_text(html, encoding="utf-8")
        print(f"[6] Saved to {out}")

        await browser.close()


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(run(sys.argv[1]))


if __name__ == "__main__":
    main()
