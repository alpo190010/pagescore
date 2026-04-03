"""Unit tests for checkout_detector and checkout_rubric.

Covers R130–R136 requirements: express checkout detection, BNPL provider
detection, payment diversity counting, cart experience signals, deterministic
0–100 scoring, and research-cited tip selection (max 3).
"""

from dataclasses import fields, is_dataclass

import pytest

from app.services.checkout_detector import CheckoutSignals, detect_checkout
from app.services.checkout_rubric import get_checkout_tips, score_checkout


# ---------------------------------------------------------------------------
# HTML fixture helpers — minimal but realistic Shopify product page fragments
# ---------------------------------------------------------------------------


def _empty_html() -> str:
    """Baseline page with no checkout signals."""
    return "<html><body><h1>Product</h1></body></html>"


def _shop_pay_html() -> str:
    """Page with ``<shopify-accelerated-checkout>`` element."""
    return (
        "<html><body>"
        "<shopify-accelerated-checkout>"
        "</shopify-accelerated-checkout>"
        "</body></html>"
    )


def _dynamic_button_html() -> str:
    """Page with ``.shopify-payment-button`` and ``[data-shopify="payment-button"]``."""
    return (
        "<html><body>"
        '<div class="shopify-payment-button" '
        'data-shopify="payment-button">Buy now</div>'
        "</body></html>"
    )


def _paypal_html() -> str:
    """Page with ``paypal-button-container`` and PayPal SDK script."""
    return (
        "<html><body>"
        '<div class="paypal-button-container"></div>'
        '<script src="https://www.paypal.com/sdk/js?client-id=test"></script>'
        "</body></html>"
    )


def _klarna_html() -> str:
    """Page with ``<klarna-placement>`` and klarnaservices.com script."""
    return (
        "<html><body>"
        '<klarna-placement data-key="credit-promotion-auto-size">'
        "</klarna-placement>"
        '<script src="https://x.klarnaservices.com/lib.js"></script>'
        "</body></html>"
    )


def _afterpay_html() -> str:
    """Page with ``<square-placement>`` and afterpay script."""
    return (
        "<html><body>"
        '<square-placement data-mpid="afterpay"></square-placement>'
        '<script src="https://js.afterpay.com/afterpay-1.x.js"></script>'
        "</body></html>"
    )


def _affirm_html() -> str:
    """Page with ``.affirm-as-low-as`` and affirm.js script."""
    return (
        "<html><body>"
        '<p class="affirm-as-low-as" data-amount="5000"></p>'
        '<script src="https://cdn1.affirm.com/js/v2/affirm.js"></script>'
        "</body></html>"
    )


def _sezzle_html() -> str:
    """Page with ``.sezzle-widget`` and sezzle.com script."""
    return (
        "<html><body>"
        '<div class="sezzle-widget"></div>'
        '<script src="https://widget.sezzle.com/v1/javascript/price-widget">'
        "</script>"
        "</body></html>"
    )


def _drawer_cart_html() -> str:
    """Page with ``.cart-drawer``, AJAX cart references (``/cart/add.js``)."""
    return (
        "<html><body>"
        '<div class="cart-drawer" data-cart-drawer>'
        "  <p>Your cart</p>"
        "</div>"
        "<script>"
        '  fetch("/cart/add.js", {method: "POST"});'
        "</script>"
        "</body></html>"
    )


def _sticky_checkout_html() -> str:
    """Page with ``.sticky-checkout`` fixed add-to-cart button."""
    return (
        "<html><body>"
        '<div class="sticky-checkout">Add to Cart</div>'
        "</body></html>"
    )


def _full_checkout_html() -> str:
    """Page with ALL signals: express checkout, all BNPL, cart, PayPal."""
    return (
        "<html><body>"
        # Express checkout
        "<shopify-accelerated-checkout></shopify-accelerated-checkout>"
        '<div class="shopify-payment-button" '
        'data-shopify="payment-button">Buy now</div>'
        # PayPal
        '<div class="paypal-button-container"></div>'
        '<script src="https://www.paypal.com/sdk/js?client-id=test"></script>'
        # BNPL — all four providers
        '<klarna-placement data-key="credit-promotion-auto-size">'
        "</klarna-placement>"
        '<script src="https://x.klarnaservices.com/lib.js"></script>'
        '<square-placement data-mpid="afterpay"></square-placement>'
        '<script src="https://js.afterpay.com/afterpay-1.x.js"></script>'
        '<p class="affirm-as-low-as" data-amount="5000"></p>'
        '<script src="https://cdn1.affirm.com/js/v2/affirm.js"></script>'
        '<div class="sezzle-widget"></div>'
        '<script src="https://widget.sezzle.com/v1/javascript/price-widget">'
        "</script>"
        # Cart experience
        '<div class="cart-drawer" data-cart-drawer>'
        "  <p>Your cart</p>"
        "</div>"
        '<script>fetch("/cart/add.js");</script>'
        '<div class="sticky-checkout">Add to Cart</div>'
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# Helper to build signals directly for rubric tests
# ---------------------------------------------------------------------------


def _all_true_signals() -> CheckoutSignals:
    """Signals with every boolean True and max payment count."""
    return CheckoutSignals(
        has_accelerated_checkout=True,
        has_dynamic_checkout_button=True,
        has_paypal=True,
        has_klarna=True,
        has_afterpay=True,
        has_affirm=True,
        has_sezzle=True,
        payment_method_count=5,
        has_drawer_cart=True,
        has_ajax_cart=True,
        has_sticky_checkout=True,
    )


# ---------------------------------------------------------------------------
# 1. TestDetection
# ---------------------------------------------------------------------------


class TestDetection:
    """Detection of individual checkout signals from HTML."""

    def test_empty_html_no_signals(self):
        """Empty page → every boolean signal is False."""
        signals = detect_checkout(_empty_html())
        assert signals.has_accelerated_checkout is False
        assert signals.has_dynamic_checkout_button is False
        assert signals.has_paypal is False
        assert signals.has_klarna is False
        assert signals.has_afterpay is False
        assert signals.has_affirm is False
        assert signals.has_sezzle is False
        assert signals.has_drawer_cart is False
        assert signals.has_ajax_cart is False
        assert signals.has_sticky_checkout is False

    def test_accelerated_checkout_detected(self):
        signals = detect_checkout(_shop_pay_html())
        assert signals.has_accelerated_checkout is True

    def test_dynamic_button_detected(self):
        signals = detect_checkout(_dynamic_button_html())
        assert signals.has_dynamic_checkout_button is True

    def test_paypal_detected_element(self):
        """PayPal button container element alone triggers detection."""
        html = '<html><body><div class="paypal-button-container"></div></body></html>'
        signals = detect_checkout(html)
        assert signals.has_paypal is True

    def test_paypal_detected_script(self):
        """PayPal SDK script alone triggers detection."""
        html = (
            "<html><body>"
            '<script src="https://www.paypal.com/sdk/js"></script>'
            "</body></html>"
        )
        signals = detect_checkout(html)
        assert signals.has_paypal is True

    def test_paypal_detected_combined(self):
        """Both element and script together triggers detection."""
        signals = detect_checkout(_paypal_html())
        assert signals.has_paypal is True

    def test_klarna_detected(self):
        signals = detect_checkout(_klarna_html())
        assert signals.has_klarna is True

    def test_afterpay_detected(self):
        signals = detect_checkout(_afterpay_html())
        assert signals.has_afterpay is True

    def test_affirm_detected(self):
        signals = detect_checkout(_affirm_html())
        assert signals.has_affirm is True

    def test_sezzle_detected(self):
        signals = detect_checkout(_sezzle_html())
        assert signals.has_sezzle is True

    def test_drawer_cart_detected(self):
        signals = detect_checkout(_drawer_cart_html())
        assert signals.has_drawer_cart is True

    def test_ajax_cart_detected(self):
        """AJAX cart detected via /cart/add.js reference in drawer cart fixture."""
        signals = detect_checkout(_drawer_cart_html())
        assert signals.has_ajax_cart is True

    def test_sticky_checkout_detected(self):
        signals = detect_checkout(_sticky_checkout_html())
        assert signals.has_sticky_checkout is True

    def test_payment_method_count_empty(self):
        """Empty HTML → baseline payment count of 1 (credit card always counted)."""
        signals = detect_checkout(_empty_html())
        assert signals.payment_method_count == 1

    def test_payment_method_count_full(self):
        """Full HTML → all methods: 1 (cc) + 2 (accel) + 1 (PayPal) + 1 (BNPL) = 5."""
        signals = detect_checkout(_full_checkout_html())
        assert signals.payment_method_count == 5

    def test_full_html_all_signals_true(self):
        """Full checkout HTML sets every boolean signal to True."""
        signals = detect_checkout(_full_checkout_html())
        assert signals.has_accelerated_checkout is True
        assert signals.has_dynamic_checkout_button is True
        assert signals.has_paypal is True
        assert signals.has_klarna is True
        assert signals.has_afterpay is True
        assert signals.has_affirm is True
        assert signals.has_sezzle is True
        assert signals.has_drawer_cart is True
        assert signals.has_ajax_cart is True
        assert signals.has_sticky_checkout is True

    def test_empty_string_returns_defaults(self):
        """Empty string input returns all-default signals."""
        signals = detect_checkout("")
        assert signals.has_accelerated_checkout is False
        assert signals.payment_method_count == 1

    def test_accelerated_checkout_not_dynamic_button(self):
        """Accelerated checkout alone does not set dynamic button flag."""
        signals = detect_checkout(_shop_pay_html())
        assert signals.has_accelerated_checkout is True
        assert signals.has_dynamic_checkout_button is False


# ---------------------------------------------------------------------------
# 2. TestScoring
# ---------------------------------------------------------------------------


class TestScoring:
    """Deterministic 0–100 scoring from CheckoutSignals."""

    def test_empty_signals_score_0(self):
        assert score_checkout(CheckoutSignals()) == 0

    def test_full_signals_score_100(self):
        assert score_checkout(_all_true_signals()) == 100

    def test_express_checkout_only_score(self):
        """Accelerated checkout (without computed payment count) → 30 pts."""
        s = CheckoutSignals(has_accelerated_checkout=True)
        assert score_checkout(s) == 30

    def test_bnpl_only_score(self):
        """Single BNPL provider alone → 20 pts."""
        s = CheckoutSignals(has_klarna=True)
        assert score_checkout(s) == 20

    def test_paypal_only_score(self):
        """PayPal alone → 10 pts."""
        s = CheckoutSignals(has_paypal=True)
        assert score_checkout(s) == 10

    def test_dynamic_button_gets_express_and_bonus(self):
        """Dynamic checkout button → 30 (express) + 5 (dynamic bonus) = 35."""
        s = CheckoutSignals(has_dynamic_checkout_button=True)
        assert score_checkout(s) == 35

    def test_drawer_cart_only_score(self):
        """Drawer cart alone → 10 pts."""
        s = CheckoutSignals(has_drawer_cart=True)
        assert score_checkout(s) == 10

    def test_partial_score_predictable(self):
        """Express + drawer cart + PayPal → 30 + 10 + 10 = 50."""
        s = CheckoutSignals(
            has_accelerated_checkout=True,
            has_drawer_cart=True,
            has_paypal=True,
        )
        assert score_checkout(s) == 50

    def test_payment_diversity_bonus(self):
        """payment_method_count >= 3 → +10; >= 5 → +5 more = 15 total."""
        s = CheckoutSignals(payment_method_count=5)
        assert score_checkout(s) == 15

    def test_score_clamped_to_0_100(self):
        """Score is always clamped within [0, 100]."""
        assert score_checkout(CheckoutSignals()) >= 0
        assert score_checkout(_all_true_signals()) <= 100


# ---------------------------------------------------------------------------
# 3. TestTipSelection
# ---------------------------------------------------------------------------


class TestTipSelection:
    """Tip ordering, max count, citations, and content verification."""

    def test_empty_signals_tips_returned(self):
        """Empty signals → 3 most impactful tips returned."""
        tips = get_checkout_tips(CheckoutSignals())
        assert len(tips) == 3

    def test_full_signals_congratulatory_tip(self):
        """All signals present (score 100 ≥ 90) → congratulatory tip only."""
        tips = get_checkout_tips(_all_true_signals())
        assert len(tips) == 1
        assert "Excellent" in tips[0]

    def test_max_3_tips_enforced(self):
        """Never more than 3 tips regardless of missing signals."""
        tips = get_checkout_tips(CheckoutSignals())
        assert len(tips) <= 3

    def test_tips_are_strings_and_nonempty(self):
        """All tips are non-empty strings with meaningful content."""
        tips = get_checkout_tips(CheckoutSignals())
        assert all(isinstance(t, str) for t in tips)
        assert all(len(t) > 10 for t in tips)

    def test_no_express_checkout_tip_includes_citation(self):
        """Express checkout tip cites Shopify research."""
        tips = get_checkout_tips(CheckoutSignals())
        express_tips = [t for t in tips if "express checkout" in t.lower() or "Shop Pay" in t]
        assert len(express_tips) >= 1
        assert "Shopify" in express_tips[0]

    def test_no_bnpl_tip_includes_citation(self):
        """BNPL tip cites McKinsey / RBC Capital Markets research."""
        tips = get_checkout_tips(CheckoutSignals())
        bnpl_tips = [t for t in tips if "buy-now-pay-later" in t.lower()]
        assert len(bnpl_tips) >= 1
        assert "McKinsey" in bnpl_tips[0] or "RBC" in bnpl_tips[0]

    def test_tip_priority_order(self):
        """Tips follow defined priority: express → BNPL → payment diversity."""
        tips = get_checkout_tips(CheckoutSignals())
        assert len(tips) == 3
        # First: express checkout
        assert "express checkout" in tips[0].lower() or "Shop Pay" in tips[0]
        # Second: BNPL
        assert "buy-now-pay-later" in tips[1].lower()
        # Third: payment methods
        assert "payment method" in tips[2].lower()

    def test_partial_signals_fewer_tips(self):
        """Having most signals reduces tip count to congratulatory only."""
        s = CheckoutSignals(
            has_accelerated_checkout=True,
            has_klarna=True,
            payment_method_count=5,
            has_drawer_cart=True,
            has_paypal=True,
            has_sticky_checkout=True,
        )
        # Score = 30 + 20 + 10 + 5 + 10 + 10 + 5 = 90 → congratulatory
        tips = get_checkout_tips(s)
        assert len(tips) == 1
        assert "Excellent" in tips[0]


# ---------------------------------------------------------------------------
# 4. TestDataclassStructure
# ---------------------------------------------------------------------------


class TestDataclassStructure:
    """CheckoutSignals dataclass invariants."""

    def test_signals_is_dataclass(self):
        assert is_dataclass(CheckoutSignals)

    def test_field_count(self):
        """11 fields: 3 express + 4 BNPL + 1 payment count + 3 cart."""
        assert len(fields(CheckoutSignals)) == 11

    def test_default_values_all_false_or_zero_except_payment_count(self):
        """All bools default to False; payment_method_count defaults to 1."""
        s = CheckoutSignals()
        for f in fields(s):
            val = getattr(s, f.name)
            if f.name == "payment_method_count":
                assert val == 1, "payment_method_count should default to 1"
            elif isinstance(val, bool):
                assert val is False, f"{f.name} should default to False"

    def test_instantiation_with_no_args(self):
        """Can instantiate with no args and get valid defaults."""
        s = CheckoutSignals()
        assert s.has_accelerated_checkout is False
        assert s.payment_method_count == 1


# ---------------------------------------------------------------------------
# 5. TestEndToEnd
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """Full pipeline: HTML → detect → score → tips."""

    def test_full_html_scores_100_congratulatory_only(self):
        """Full checkout HTML → score 100, only congratulatory tip."""
        signals = detect_checkout(_full_checkout_html())
        assert score_checkout(signals) == 100
        tips = get_checkout_tips(signals)
        assert len(tips) == 1
        assert "Excellent" in tips[0]

    def test_empty_html_scores_0_with_tips(self):
        """Empty HTML → score 0, 3 improvement tips."""
        signals = detect_checkout(_empty_html())
        assert score_checkout(signals) == 0
        tips = get_checkout_tips(signals)
        assert len(tips) == 3

    def test_partial_html_mid_range_score(self):
        """Shop Pay HTML → mid-range score with improvement tips."""
        signals = detect_checkout(_shop_pay_html())
        score = score_checkout(signals)
        # has_accelerated_checkout=True → 30 pts
        # payment_method_count=3 (1 base + 2 accel) → +10 pts
        # Total: 40
        assert score == 40
        assert 0 < score < 100
        tips = get_checkout_tips(signals)
        assert 0 < len(tips) <= 3

    def test_paypal_plus_bnpl_mid_range(self):
        """PayPal + Klarna → predictable mid-range score."""
        html = (
            "<html><body>"
            '<div class="paypal-button-container"></div>'
            '<script src="https://www.paypal.com/sdk/js"></script>'
            '<klarna-placement></klarna-placement>'
            '<script src="https://x.klarnaservices.com/lib.js"></script>'
            "</body></html>"
        )
        signals = detect_checkout(html)
        score = score_checkout(signals)
        # PayPal: 10, BNPL: 20, payment_method_count = 1+1+1 = 3 → 10
        # Total: 40
        assert score == 40

    def test_detect_score_tips_pipeline_consistent(self):
        """detect → score → tips pipeline produces consistent typed results."""
        signals = detect_checkout(_full_checkout_html())
        score = score_checkout(signals)
        tips = get_checkout_tips(signals)
        assert isinstance(score, int)
        assert score == 100
        assert isinstance(tips, list)
        assert all(isinstance(t, str) for t in tips)
