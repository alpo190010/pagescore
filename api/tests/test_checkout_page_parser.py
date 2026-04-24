"""Tests for the Shopify checkout page parser.

The allbirds_onepage.html fixture was captured live via the spike
script on 2026-04-24 and anonymized (tokens/HMACs stripped). It is
the golden case for the new React one-page checkout. Synthetic
fixtures exercise failure paths and the classic-checkout fallback.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.checkout_page_parser import (
    CheckoutPageSignals,
    parse_checkout_page,
    unreached,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "checkout"


@pytest.fixture(scope="module")
def allbirds_html() -> str:
    path = _FIXTURES / "allbirds_onepage.html"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------
# Allbirds (new React one-page checkout) — golden case
# ---------------------------------------------------------------------


class TestAllbirdsOnepage:
    def test_flavor_detected(self, allbirds_html: str) -> None:
        sig = parse_checkout_page(allbirds_html)
        assert sig.reached_checkout is True
        assert sig.failure_reason is None
        assert sig.checkout_flavor == "onepage"

    def test_wallets_from_typenames(self, allbirds_html: str) -> None:
        sig = parse_checkout_page(allbirds_html)
        # The captured JSON payload contains ShopPay, ApplePay, Paypal
        # wallet configs. Google Pay / Amazon Pay / Meta Pay were not
        # in the config and must remain false.
        assert sig.has_shop_pay is True
        assert sig.has_apple_pay is True
        assert sig.has_paypal is True
        assert sig.has_google_pay is False
        assert sig.has_amazon_pay is False
        assert sig.has_meta_pay is False

    def test_bnpl_detection(self, allbirds_html: str) -> None:
        sig = parse_checkout_page(allbirds_html)
        # Allbirds offers Afterpay (as a radio option) and Shop Pay
        # Installments (via WalletConfig).
        assert sig.has_afterpay is True
        assert sig.has_shop_pay_installments is True
        assert sig.has_klarna is False
        assert sig.has_affirm is False
        assert sig.has_sezzle is False

    def test_card_brands(self, allbirds_html: str) -> None:
        sig = parse_checkout_page(allbirds_html)
        # From ApplePayWalletConfig.supportedNetworks:
        # "visa","masterCard","amex","discover","elo","jcb"
        assert "visa" in sig.card_brands
        assert "mastercard" in sig.card_brands
        assert "amex" in sig.card_brands
        assert "discover" in sig.card_brands
        assert "elo" in sig.card_brands
        assert "jcb" in sig.card_brands

    def test_guest_checkout_not_forced(self, allbirds_html: str) -> None:
        sig = parse_checkout_page(allbirds_html)
        assert sig.guest_checkout_available is True
        assert sig.forced_account_creation is False

    def test_one_page_step_count(self, allbirds_html: str) -> None:
        sig = parse_checkout_page(allbirds_html)
        assert sig.checkout_step_count == 1

    def test_form_fields_counted(self, allbirds_html: str) -> None:
        sig = parse_checkout_page(allbirds_html)
        # Expected step-1 fields (excluding opt-ins, authenticity, and
        # the "basic" radio group name): email, firstName, lastName,
        # address1, address2, city, postalCode, country, countryCode,
        # province, zone, phone, company, billingAddress, reductions.
        # Allow slack for minor markup variation.
        assert 10 <= sig.total_form_fields_step_one <= 25

    def test_discount_field_present(self, allbirds_html: str) -> None:
        sig = parse_checkout_page(allbirds_html)
        assert sig.has_discount_code_field is True

    def test_shipping_calculator_always_true_onepage(self, allbirds_html: str) -> None:
        sig = parse_checkout_page(allbirds_html)
        assert sig.has_shipping_calculator is True

    def test_wallet_and_bnpl_counts(self, allbirds_html: str) -> None:
        sig = parse_checkout_page(allbirds_html)
        # 3 wallets: Shop Pay, Apple Pay, PayPal
        assert sig.wallet_count == 3
        # 2 BNPL: Afterpay, Shop Pay Installments
        assert sig.bnpl_count == 2


# ---------------------------------------------------------------------
# Failure / unreached checkout
# ---------------------------------------------------------------------


class TestUnreached:
    def test_unreached_default_shape(self) -> None:
        sig = unreached("bot_wall")
        assert sig.reached_checkout is False
        assert sig.failure_reason == "bot_wall"
        assert sig.checkout_flavor == "unknown"
        assert sig.card_brands == ()
        assert sig.wallet_count == 0
        assert sig.bnpl_count == 0
        assert sig.total_form_fields_step_one == 0
        assert sig.currency_code is None

    def test_empty_html_returns_unreached(self) -> None:
        sig = parse_checkout_page("")
        assert sig.reached_checkout is False
        assert sig.failure_reason == "empty_html"

    @pytest.mark.parametrize(
        "reason",
        ["out_of_stock", "bot_wall", "timeout", "password_protected", "network_error"],
    )
    def test_unreached_accepts_any_reason(self, reason: str) -> None:
        sig = unreached(reason)
        assert sig.failure_reason == reason


# ---------------------------------------------------------------------
# Synthetic: classic checkout (old Liquid flavor)
# ---------------------------------------------------------------------


CLASSIC_CHECKOUT_HTML = """
<!doctype html>
<html>
<head><meta data-currency="USD"></head>
<body>
<form data-payment-form action="/checkouts/xyz" method="POST">
  <div data-step="contact_information">
    <input type="email" name="checkout[email]" required />
  </div>
  <div>
    <input type="text" name="checkout[shipping_address][first_name]" />
    <input type="text" name="checkout[shipping_address][last_name]" />
    <input type="text" name="checkout[shipping_address][address1]" />
    <input type="text" name="checkout[shipping_address][city]" />
    <input type="text" name="checkout[shipping_address][zip]" />
  </div>
  <div>
    <input type="text" name="checkout[reduction_code]" />
  </div>
  <script src="https://js.klarnaservices.com/lib.js"></script>
  <img src="/icons/visa.png" alt="Visa" />
  <img src="/icons/mastercard.png" alt="Mastercard" />
  <img src="/icons/amex.png" alt="American Express" />
  <script src="https://www.paypal.com/sdk/js"></script>
</form>
</body>
</html>
"""


class TestClassicCheckout:
    def test_flavor_classic(self) -> None:
        sig = parse_checkout_page(
            CLASSIC_CHECKOUT_HTML,
            final_url="https://shop.example.com/checkouts/abc?step=contact_information",
        )
        assert sig.reached_checkout is True
        assert sig.checkout_flavor == "classic"

    def test_klarna_fallback_string_match(self) -> None:
        sig = parse_checkout_page(CLASSIC_CHECKOUT_HTML)
        # Klarna is detected via the script src even though no radio or
        # __typename marker exists.
        assert sig.has_klarna is True

    def test_card_brands_from_alt_text(self) -> None:
        sig = parse_checkout_page(CLASSIC_CHECKOUT_HTML)
        # No ApplePayWalletConfig block, so we fall back to image alts.
        assert "visa" in sig.card_brands
        assert "mastercard" in sig.card_brands
        assert "amex" in sig.card_brands

    def test_step_count_three_from_url(self) -> None:
        sig = parse_checkout_page(
            CLASSIC_CHECKOUT_HTML,
            final_url="https://shop.example.com/checkouts/abc?step=contact_information",
        )
        assert sig.checkout_step_count == 3

    def test_discount_field_classic_name(self) -> None:
        sig = parse_checkout_page(CLASSIC_CHECKOUT_HTML)
        assert sig.has_discount_code_field is True

    def test_currency_from_meta(self) -> None:
        sig = parse_checkout_page(CLASSIC_CHECKOUT_HTML)
        assert sig.currency_code == "USD"


# ---------------------------------------------------------------------
# Synthetic: forced account creation
# ---------------------------------------------------------------------


FORCED_ACCOUNT_HTML = """
<html>
<body>
<form data-payment-form>
  <input type="email" name="checkout[email]" required />
  <input type="password" name="customer[password]" required />
</form>
</body>
</html>
"""


class TestForcedAccountCreation:
    def test_forced_account_detected(self) -> None:
        sig = parse_checkout_page(FORCED_ACCOUNT_HTML)
        assert sig.forced_account_creation is True
        assert sig.guest_checkout_available is False


# ---------------------------------------------------------------------
# Synthetic: many BNPL providers
# ---------------------------------------------------------------------


MULTI_BNPL_HTML = """
<html>
<body>
<form data-payment-form>
  <input type="email" name="email" />
  <input type="radio" name="basic" aria-label="Klarna" />
  <input type="radio" name="basic" aria-label="Affirm" />
  <input type="radio" name="basic" aria-label="Sezzle" />
  <input type="radio" name="basic" aria-label="Zip" />
  <input type="radio" name="basic" aria-label="Clearpay" />
</form>
</body>
</html>
"""


class TestMultipleBNPL:
    def test_all_bnpl_detected_from_radios(self) -> None:
        sig = parse_checkout_page(MULTI_BNPL_HTML)
        assert sig.has_klarna is True
        assert sig.has_affirm is True
        assert sig.has_sezzle is True
        assert sig.has_zip is True
        assert sig.has_clearpay is True
        assert sig.bnpl_count == 5


# ---------------------------------------------------------------------
# CheckoutPageSignals dataclass contract
# ---------------------------------------------------------------------


class TestDataclassContract:
    def test_is_frozen(self) -> None:
        sig = unreached("test")
        with pytest.raises((AttributeError, TypeError)):
            sig.has_shop_pay = True  # type: ignore[misc]

    def test_wallet_count_property(self) -> None:
        # Construct manually to verify property
        sig = CheckoutPageSignals(
            reached_checkout=True,
            failure_reason=None,
            checkout_flavor="onepage",
            has_shop_pay=True,
            has_apple_pay=True,
            has_google_pay=False,
            has_paypal=True,
            has_amazon_pay=False,
            has_meta_pay=False,
            has_stripe_link=False,
            has_klarna=False,
            has_afterpay=True,
            has_clearpay=False,
            has_affirm=False,
            has_sezzle=False,
            has_shop_pay_installments=True,
            has_zip=False,
            card_brands=("visa", "mastercard"),
            guest_checkout_available=True,
            forced_account_creation=False,
            checkout_step_count=1,
            total_form_fields_step_one=15,
            has_discount_code_field=True,
            has_gift_card_field=False,
            has_shipping_calculator=True,
            has_address_autocomplete=True,
            trust_badge_count=2,
            currency_code="USD",
        )
        assert sig.wallet_count == 3
        assert sig.bnpl_count == 2
