"""End-to-end smoke test of the merged checkout chain.

Exercises the exact code path analyze.py uses via
``_run_merged_checkout_chain``: render PDP -> detect_checkout (PDP
signals) -> simulate_checkout_flow (live flow) -> combine_signals ->
score_merged_checkout + get_merged_checkout_tips.

Usage:
    /Users/aleksandrephatsatsia/projects/alpo/.venv/bin/python \\
        api/scripts/smoke_merged_checkout.py https://www.allbirds.com/products/tree-loungers
"""

from __future__ import annotations

import asyncio
import json
import sys

from app.routers.analyze import _run_merged_checkout_chain
from app.services.page_renderer import render_page


async def main(product_url: str) -> None:
    print(f"[1] Rendering PDP: {product_url}")
    html = await render_page(product_url)
    print(f"    got {len(html)} chars of HTML")

    print("[2] Running merged chain (detect + simulate + score)...")
    merged, score, tips, elapsed_ms = await _run_merged_checkout_chain(
        html, product_url
    )

    print(f"\n=== RESULT (elapsed: {elapsed_ms} ms) ===")
    print(f"Score: {score}/100")
    print(f"Reached checkout: {merged.reached_checkout}")
    print(f"Failure reason: {merged.failure_reason}")
    print(f"Flavor: {merged.checkout_page.checkout_flavor}")
    print()
    print("Wallets:")
    cp = merged.checkout_page
    print(f"  Shop Pay:      {cp.has_shop_pay}")
    print(f"  Apple Pay:     {cp.has_apple_pay}")
    print(f"  Google Pay:    {cp.has_google_pay}")
    print(f"  PayPal:        {cp.has_paypal}")
    print(f"  Amazon Pay:    {cp.has_amazon_pay}")
    print(f"  Meta Pay:      {cp.has_meta_pay}")
    print(f"  Stripe Link:   {cp.has_stripe_link}")
    print()
    print("BNPL:")
    print(f"  Klarna:                {cp.has_klarna}")
    print(f"  Afterpay:              {cp.has_afterpay}")
    print(f"  Clearpay:              {cp.has_clearpay}")
    print(f"  Affirm:                {cp.has_affirm}")
    print(f"  Sezzle:                {cp.has_sezzle}")
    print(f"  Shop Pay Installments: {cp.has_shop_pay_installments}")
    print(f"  Zip:                   {cp.has_zip}")
    print()
    print(f"Card brands: {cp.card_brands}")
    print(f"Guest checkout: {cp.guest_checkout_available}")
    print(f"Forced account creation: {cp.forced_account_creation}")
    print(f"Checkout steps: {cp.checkout_step_count}")
    print(f"Form fields (step 1): {cp.total_form_fields_step_one}")
    print(f"Discount code field: {cp.has_discount_code_field}")
    print(f"Address autocomplete: {cp.has_address_autocomplete}")
    print(f"Currency: {cp.currency_code}")
    print()
    print("Top tips:")
    for i, tip in enumerate(tips, 1):
        print(f"  {i}. {tip}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
