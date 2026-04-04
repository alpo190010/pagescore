"""Unit tests for pricing_detector and pricing_rubric.

Covers detection of compare-at/strikethrough pricing, charm pricing,
countdown timers, scarcity messaging, BNPL installment widgets, deterministic
0–100 scoring, fake-timer risk flagging, and research-cited tip selection.
"""

from dataclasses import fields, is_dataclass

import pytest

from app.services.pricing_detector import PricingSignals, detect_pricing
from app.services.pricing_rubric import get_pricing_tips, score_pricing


# ---------------------------------------------------------------------------
# HTML fixture helpers
# ---------------------------------------------------------------------------


def _empty_html() -> str:
    """Baseline page with no pricing signals."""
    return "<html><body><h1>Product</h1><p>$50</p></body></html>"


def _compare_at_price_html() -> str:
    """Dawn theme sale price with .price--on-sale container."""
    return (
        "<html><body>"
        '<div class="price price--on-sale">'
        '  <span class="price-item price-item--regular">$80.00</span>'
        '  <span class="price-item price-item--sale">$49.99</span>'
        "</div>"
        "</body></html>"
    )


def _compare_at_json_html() -> str:
    """Page with compare_at_price in inline Shopify JSON."""
    return (
        "<html><body>"
        "<script>"
        '  var product = {"price": 4999, "compare_at_price": 8000};'
        "</script>"
        "</body></html>"
    )


def _strikethrough_price_html() -> str:
    """Page with .price-item--regular (Dawn strikethrough pattern)."""
    return (
        "<html><body>"
        '<span class="price-item price-item--regular">$80.00</span>'
        '<span class="price-item price-item--sale">$49.99</span>'
        "</body></html>"
    )


def _strikethrough_style_html() -> str:
    """Page with explicit text-decoration:line-through inline style."""
    return (
        "<html><body>"
        '<s style="text-decoration: line-through;">$80.00</s>'
        '<span class="product__price">$49.99</span>'
        "</body></html>"
    )


def _charm_price_html() -> str:
    """Product price ending in .99 (charm pricing)."""
    return (
        "<html><body>"
        '<span class="price-item--sale">$49.99</span>'
        "</body></html>"
    )


def _charm_price_95_html() -> str:
    """Product price ending in .95 (charm pricing variant)."""
    return (
        "<html><body>"
        '<span class="price-item--sale">$29.95</span>'
        "</body></html>"
    )


def _round_price_html() -> str:
    """Product price with round dollar amount."""
    return (
        "<html><body>"
        '<span class="price-item--sale">$50.00</span>'
        "</body></html>"
    )


def _json_ld_price_html() -> str:
    """Product price from JSON-LD schema."""
    return (
        "<html><body>"
        '<script type="application/ld+json">'
        '{"@type": "Product", "name": "Widget", "offers": {"@type": "Offer", "price": "29.99", "priceCurrency": "USD"}}'
        "</script>"
        "</body></html>"
    )


def _countdown_timer_element_html() -> str:
    """Page with <countdown-timer> custom element."""
    return (
        "<html><body>"
        "<countdown-timer data-seconds='3600'>"
        "  <span id='timer'>01:00:00</span>"
        "</countdown-timer>"
        "</body></html>"
    )


def _countdown_with_end_time_html() -> str:
    """Countdown timer WITH data-end-time (verifiable — not fake)."""
    return (
        "<html><body>"
        '<div class="countdown" data-countdown data-end-time="2099-12-31T23:59:59Z">'
        "  <span>01:00:00</span>"
        "</div>"
        "</body></html>"
    )


def _countdown_no_end_time_html() -> str:
    """Countdown timer WITHOUT data-end-time (fake-timer risk)."""
    return (
        "<html><body>"
        '<div class="countdown" data-countdown>'
        "  <span>01:00:00</span>"
        "</div>"
        "</body></html>"
    )


def _scarcity_messaging_html() -> str:
    """Page with "Only 3 left" scarcity text."""
    return (
        "<html><body>"
        '<p class="stock-notice">Only 3 left in stock</p>'
        "</body></html>"
    )


def _scarcity_low_stock_html() -> str:
    """Page with "Low stock" text."""
    return (
        "<html><body>"
        '<span class="availability">Low stock — order soon</span>'
        "</body></html>"
    )


def _scarcity_selling_fast_html() -> str:
    """Page with "Selling fast" text."""
    return (
        "<html><body>"
        "<p>Selling fast! Only a few remain.</p>"
        "</body></html>"
    )


def _klarna_html() -> str:
    """Page with <klarna-placement> element."""
    return (
        "<html><body>"
        '<klarna-placement data-key="credit-promotion-auto-size">'
        "</klarna-placement>"
        "</body></html>"
    )


def _afterpay_html() -> str:
    """Page with Afterpay badge via <square-placement>."""
    return (
        "<html><body>"
        '<square-placement data-mpid="afterpay"></square-placement>'
        "</body></html>"
    )


def _afterpay_script_html() -> str:
    """Page with Afterpay via script src."""
    return (
        "<html><body>"
        '<script src="https://js.afterpay.com/afterpay-1.x.js"></script>'
        "</body></html>"
    )


def _shop_pay_installments_html() -> str:
    """Page with shop-pay-installment-details element."""
    return (
        "<html><body>"
        "<shop-pay-installment-details>"
        "  <p>4 payments of $12.50</p>"
        "</shop-pay-installment-details>"
        "</body></html>"
    )


def _shop_pay_installments_text_html() -> str:
    """Page with 'shop pay installments' text."""
    return (
        "<html><body>"
        "<p>Shop Pay Installments: 4 payments of $12.50 with 0% APR</p>"
        "</body></html>"
    )


def _full_pricing_html() -> str:
    """Page with ALL pricing signals present."""
    return (
        "<html><body>"
        # Compare-at / strikethrough
        '<div class="price price--on-sale">'
        '  <span class="price-item price-item--regular">$80.00</span>'
        '  <span class="price-item price-item--sale">$49.99</span>'
        "</div>"
        # Countdown with verifiable end time
        '<div class="countdown" data-countdown data-end-time="2099-01-01T00:00:00Z">'
        "  01:00:00"
        "</div>"
        # Scarcity
        "<p>Only 3 left in stock!</p>"
        # BNPL — Klarna + Afterpay + Shop Pay Installments
        '<klarna-placement data-key="credit-promotion-auto-size"></klarna-placement>'
        '<square-placement data-mpid="afterpay"></square-placement>'
        "<shop-pay-installment-details></shop-pay-installment-details>"
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# Helper to build signals directly for rubric tests
# ---------------------------------------------------------------------------


def _all_true_signals() -> PricingSignals:
    """Signals with maximum scoring values."""
    return PricingSignals(
        has_compare_at_price=True,
        has_strikethrough_price=True,
        price_value=49.99,
        has_charm_pricing=True,
        is_round_price=False,
        has_countdown_timer=True,
        has_scarcity_messaging=True,
        has_fake_timer_risk=False,
        has_klarna_placement=True,
        has_afterpay_badge=True,
        has_shop_pay_installments=True,
        has_bnpl_near_price=True,
    )


def _no_signals() -> PricingSignals:
    """All-False signals with a round price (worst case)."""
    return PricingSignals(
        price_value=50.0,
        is_round_price=True,
    )


# ---------------------------------------------------------------------------
# 1. TestDetection — compare-at / strikethrough
# ---------------------------------------------------------------------------


class TestCompareAtDetection:
    """Compare-at / strikethrough price detection."""

    def test_empty_html_no_compare_at(self):
        signals = detect_pricing(_empty_html())
        assert signals.has_compare_at_price is False
        assert signals.has_strikethrough_price is False

    def test_price_on_sale_class_detected(self):
        """Dawn .price--on-sale class triggers compare_at detection."""
        signals = detect_pricing(_compare_at_price_html())
        assert signals.has_compare_at_price is True

    def test_compare_at_in_json_script_detected(self):
        """compare_at_price key in inline script triggers detection."""
        signals = detect_pricing(_compare_at_json_html())
        assert signals.has_compare_at_price is True

    def test_price_item_regular_class_detected(self):
        """Dawn .price-item--regular triggers strikethrough detection."""
        signals = detect_pricing(_strikethrough_price_html())
        assert signals.has_strikethrough_price is True

    def test_line_through_style_detected(self):
        """Inline text-decoration: line-through style triggers detection."""
        signals = detect_pricing(_strikethrough_style_html())
        assert signals.has_strikethrough_price is True

    def test_both_compare_at_and_strikethrough_detected(self):
        """Full Dawn sale price sets both flags."""
        signals = detect_pricing(_compare_at_price_html())
        assert signals.has_compare_at_price is True
        assert signals.has_strikethrough_price is True


# ---------------------------------------------------------------------------
# 2. TestCharmPricing — price extraction and .99/.95 detection
# ---------------------------------------------------------------------------


class TestCharmPricing:
    """Price extraction and charm pricing detection."""

    def test_charm_price_99_detected(self):
        signals = detect_pricing(_charm_price_html())
        assert signals.price_value == pytest.approx(49.99)
        assert signals.has_charm_pricing is True
        assert signals.is_round_price is False

    def test_charm_price_95_detected(self):
        signals = detect_pricing(_charm_price_95_html())
        assert signals.price_value == pytest.approx(29.95)
        assert signals.has_charm_pricing is True

    def test_round_price_detected(self):
        signals = detect_pricing(_round_price_html())
        assert signals.price_value == pytest.approx(50.0)
        assert signals.has_charm_pricing is False
        assert signals.is_round_price is True

    def test_json_ld_price_extracted(self):
        """Price from JSON-LD Product schema is extracted correctly."""
        signals = detect_pricing(_json_ld_price_html())
        assert signals.price_value == pytest.approx(29.99)
        assert signals.has_charm_pricing is True

    def test_no_price_element_returns_none(self):
        signals = detect_pricing("<html><body><h1>Product</h1></body></html>")
        assert signals.price_value is None
        assert signals.has_charm_pricing is False
        assert signals.is_round_price is False

    def test_empty_html_price_none(self):
        signals = detect_pricing("")
        assert signals.price_value is None


# ---------------------------------------------------------------------------
# 3. TestUrgencyScarcity — countdown timers and stock messages
# ---------------------------------------------------------------------------


class TestUrgencyScarcity:
    """Countdown timer and scarcity messaging detection."""

    def test_countdown_timer_element_detected(self):
        signals = detect_pricing(_countdown_timer_element_html())
        assert signals.has_countdown_timer is True

    def test_countdown_with_end_time_not_fake(self):
        """Timer with data-end-time is verified — fake risk should be False."""
        signals = detect_pricing(_countdown_with_end_time_html())
        assert signals.has_countdown_timer is True
        assert signals.has_fake_timer_risk is False

    def test_countdown_without_end_time_is_fake_risk(self):
        """Timer without data-end-time and no scarcity text → fake timer risk."""
        signals = detect_pricing(_countdown_no_end_time_html())
        assert signals.has_countdown_timer is True
        assert signals.has_fake_timer_risk is True

    def test_scarcity_text_clears_fake_timer_risk(self):
        """Countdown without end-time BUT with scarcity text → risk cleared.

        Scarcity text (e.g. "Only 3 left") is evidence of real inventory,
        which cancels the fake-timer risk flag.
        """
        html = (
            "<html><body>"
            '<div class="countdown" data-countdown>01:00:00</div>'
            "<p>Only 5 left in stock</p>"
            "</body></html>"
        )
        signals = detect_pricing(html)
        assert signals.has_countdown_timer is True
        assert signals.has_scarcity_messaging is True
        assert signals.has_fake_timer_risk is False

    def test_only_n_left_detected(self):
        signals = detect_pricing(_scarcity_messaging_html())
        assert signals.has_scarcity_messaging is True

    def test_low_stock_detected(self):
        signals = detect_pricing(_scarcity_low_stock_html())
        assert signals.has_scarcity_messaging is True

    def test_selling_fast_detected(self):
        signals = detect_pricing(_scarcity_selling_fast_html())
        assert signals.has_scarcity_messaging is True

    def test_no_urgency_in_empty_html(self):
        signals = detect_pricing(_empty_html())
        assert signals.has_countdown_timer is False
        assert signals.has_scarcity_messaging is False
        assert signals.has_fake_timer_risk is False


# ---------------------------------------------------------------------------
# 4. TestBnpl — BNPL installment widget detection
# ---------------------------------------------------------------------------


class TestBnpl:
    """BNPL installment widget detection."""

    def test_klarna_placement_detected(self):
        signals = detect_pricing(_klarna_html())
        assert signals.has_klarna_placement is True
        assert signals.has_bnpl_near_price is True

    def test_afterpay_square_placement_detected(self):
        signals = detect_pricing(_afterpay_html())
        assert signals.has_afterpay_badge is True
        assert signals.has_bnpl_near_price is True

    def test_afterpay_script_detected(self):
        signals = detect_pricing(_afterpay_script_html())
        assert signals.has_afterpay_badge is True
        assert signals.has_bnpl_near_price is True

    def test_shop_pay_installments_element_detected(self):
        signals = detect_pricing(_shop_pay_installments_html())
        assert signals.has_shop_pay_installments is True
        assert signals.has_bnpl_near_price is True

    def test_shop_pay_installments_text_detected(self):
        signals = detect_pricing(_shop_pay_installments_text_html())
        assert signals.has_shop_pay_installments is True
        assert signals.has_bnpl_near_price is True

    def test_no_bnpl_in_empty_html(self):
        signals = detect_pricing(_empty_html())
        assert signals.has_klarna_placement is False
        assert signals.has_afterpay_badge is False
        assert signals.has_shop_pay_installments is False
        assert signals.has_bnpl_near_price is False

    def test_empty_string_returns_defaults(self):
        signals = detect_pricing("")
        assert signals.has_bnpl_near_price is False


# ---------------------------------------------------------------------------
# 5. TestScoring — deterministic 0–100 score
# ---------------------------------------------------------------------------


class TestScoring:
    """Deterministic 0–100 scoring from PricingSignals."""

    def test_no_signals_score_0(self):
        """All-False signals (no price) → score 0."""
        assert score_pricing(PricingSignals()) == 0

    def test_full_signals_score_90(self):
        """All pricing signals → 30 + 20 + 25 + 15 = 90 pts."""
        assert score_pricing(_all_true_signals()) == 90

    def test_compare_at_only_score_30(self):
        s = PricingSignals(has_compare_at_price=True)
        assert score_pricing(s) == 30

    def test_charm_pricing_only_score_20(self):
        s = PricingSignals(has_charm_pricing=True, price_value=49.99, is_round_price=False)
        assert score_pricing(s) == 20

    def test_round_price_no_charm_bonus(self):
        """Round price with charm=False → charm 0 pts even if is_round_price."""
        s = PricingSignals(is_round_price=True, price_value=50.0, has_charm_pricing=False)
        assert score_pricing(s) == 0

    def test_bnpl_only_score_25(self):
        s = PricingSignals(has_bnpl_near_price=True)
        assert score_pricing(s) == 25

    def test_truthful_urgency_score_15(self):
        """Scarcity messaging without fake timer risk → 15 pts."""
        s = PricingSignals(has_scarcity_messaging=True, has_fake_timer_risk=False)
        assert score_pricing(s) == 15

    def test_fake_timer_only_score_0(self):
        """Timer without end-time anchor and no scarcity → 0 pts for urgency."""
        s = PricingSignals(has_countdown_timer=True, has_fake_timer_risk=True)
        assert score_pricing(s) == 0

    def test_fake_timer_with_scarcity_score_10(self):
        """Fake timer risk + scarcity text → partial 10 pts."""
        s = PricingSignals(
            has_countdown_timer=True,
            has_scarcity_messaging=True,
            has_fake_timer_risk=False,  # scarcity clears fake risk in detector
        )
        # Scarcity without fake risk → 15 pts (not 10)
        assert score_pricing(s) == 15

    def test_fake_timer_risk_signals_directly(self):
        """Directly set fake_timer_risk=True with scarcity → 10 pts."""
        s = PricingSignals(
            has_countdown_timer=True,
            has_scarcity_messaging=True,
            has_fake_timer_risk=True,
        )
        assert score_pricing(s) == 10

    def test_compare_at_plus_charm_plus_bnpl(self):
        """Compare-at (30) + charm (20) + BNPL (25) = 75."""
        s = PricingSignals(
            has_compare_at_price=True,
            has_charm_pricing=True,
            is_round_price=False,
            price_value=49.99,
            has_bnpl_near_price=True,
        )
        assert score_pricing(s) == 75

    def test_score_clamped_to_100(self):
        assert score_pricing(_all_true_signals()) <= 100

    def test_score_clamped_to_0(self):
        assert score_pricing(PricingSignals()) >= 0


# ---------------------------------------------------------------------------
# 6. TestTipSelection
# ---------------------------------------------------------------------------


class TestTipSelection:
    """Tip ordering, max count, citations, and content."""

    def test_no_signals_returns_3_tips(self):
        """All-False signals → 3 most impactful tips."""
        tips = get_pricing_tips(PricingSignals())
        assert len(tips) == 3

    def test_full_signals_congratulatory(self):
        """All signals (score 90 ≥ 85) → congratulatory tip."""
        tips = get_pricing_tips(_all_true_signals())
        assert len(tips) == 1
        assert "Excellent" in tips[0]

    def test_max_3_tips_enforced(self):
        tips = get_pricing_tips(PricingSignals())
        assert len(tips) <= 3

    def test_tips_are_nonempty_strings(self):
        tips = get_pricing_tips(PricingSignals())
        assert all(isinstance(t, str) and len(t) > 10 for t in tips)

    def test_no_compare_at_tip_includes_citation(self):
        """Compare-at tip cites MIT/Shopify research."""
        tips = get_pricing_tips(PricingSignals())
        compare_tips = [t for t in tips if "compare-at" in t.lower() or "strikethrough" in t.lower()]
        assert len(compare_tips) >= 1
        assert "MIT" in compare_tips[0] or "Shopify" in compare_tips[0]

    def test_no_bnpl_tip_includes_citation(self):
        """BNPL tip cites McKinsey/RBC research."""
        tips = get_pricing_tips(PricingSignals())
        bnpl_tips = [t for t in tips if "Klarna" in t or "Afterpay" in t or "installment" in t.lower()]
        assert len(bnpl_tips) >= 1
        assert "McKinsey" in bnpl_tips[0] or "RBC" in bnpl_tips[0]

    def test_fake_timer_tip_appears_before_urgency_tip(self):
        """Fake timer warning takes priority over generic urgency tip."""
        s = PricingSignals(
            has_compare_at_price=True,
            has_charm_pricing=True,
            is_round_price=False,
            price_value=49.99,
            has_bnpl_near_price=True,
            has_countdown_timer=True,
            has_fake_timer_risk=True,
        )
        tips = get_pricing_tips(s)
        fake_tips = [t for t in tips if "Princeton" in t or "fake" in t.lower()]
        assert len(fake_tips) >= 1

    def test_round_price_charm_tip_shown(self):
        """Round price with no charm pricing triggers the .99 tip."""
        s = PricingSignals(price_value=50.0, is_round_price=True, has_charm_pricing=False)
        tips = get_pricing_tips(s)
        charm_tips = [t for t in tips if "49.99" in t or "charm" in t.lower() or "MIT" in t]
        assert len(charm_tips) >= 1

    def test_tip_priority_order_no_signals(self):
        """Priority: compare-at → BNPL → urgency."""
        tips = get_pricing_tips(PricingSignals())
        # First tip: compare-at anchoring
        assert "compare-at" in tips[0].lower() or "strikethrough" in tips[0].lower()
        # Second: charm or BNPL — depends on price_value being None
        # (no round-price tip when price is None)
        assert "Klarna" in tips[1] or "Afterpay" in tips[1] or "installment" in tips[1].lower()


# ---------------------------------------------------------------------------
# 7. TestDataclassStructure
# ---------------------------------------------------------------------------


class TestDataclassStructure:
    """PricingSignals dataclass invariants."""

    def test_signals_is_dataclass(self):
        assert is_dataclass(PricingSignals)

    def test_field_count(self):
        """12 fields: 2 compare-at + 3 charm + 3 urgency + 4 BNPL."""
        assert len(fields(PricingSignals)) == 12

    def test_default_values(self):
        """All bool fields default False; price_value defaults None."""
        s = PricingSignals()
        assert s.has_compare_at_price is False
        assert s.has_strikethrough_price is False
        assert s.price_value is None
        assert s.has_charm_pricing is False
        assert s.is_round_price is False
        assert s.has_countdown_timer is False
        assert s.has_scarcity_messaging is False
        assert s.has_fake_timer_risk is False
        assert s.has_klarna_placement is False
        assert s.has_afterpay_badge is False
        assert s.has_shop_pay_installments is False
        assert s.has_bnpl_near_price is False

    def test_instantiation_with_no_args(self):
        s = PricingSignals()
        assert s.price_value is None
        assert s.has_bnpl_near_price is False


# ---------------------------------------------------------------------------
# 8. TestEndToEnd — HTML → detect → score → tips
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """Full pipeline: HTML → detect → score → tips."""

    def test_full_html_high_score_congratulatory(self):
        """Full pricing HTML → high score, congratulatory tip."""
        signals = detect_pricing(_full_pricing_html())
        score = score_pricing(signals)
        assert score >= 85
        tips = get_pricing_tips(signals)
        assert any("Excellent" in t for t in tips)

    def test_empty_html_score_0(self):
        """Page with no recognisable pricing signals → score 0."""
        signals = detect_pricing("<html><body><h1>Product</h1></body></html>")
        assert score_pricing(signals) == 0

    def test_empty_string_input(self):
        """Empty string → all defaults, score 0."""
        signals = detect_pricing("")
        assert score_pricing(signals) == 0
        tips = get_pricing_tips(signals)
        assert isinstance(tips, list)
        assert len(tips) <= 3

    def test_dawn_sale_page_pipeline(self):
        """Dawn theme sale page → compare-at + strikethrough + charm + score 50."""
        signals = detect_pricing(_compare_at_price_html())
        # compare_at=True (30) + strikethrough=True (no extra pts) + charm=True (20) = 50
        assert signals.has_compare_at_price is True
        assert signals.has_strikethrough_price is True
        assert signals.has_charm_pricing is True
        score = score_pricing(signals)
        assert score == 50
        tips = get_pricing_tips(signals)
        assert isinstance(tips, list)
        # Should recommend BNPL since none present
        assert any("Klarna" in t or "Afterpay" in t or "installment" in t.lower() for t in tips)

    def test_pipeline_types_consistent(self):
        """detect → score → tips produce consistent typed results."""
        signals = detect_pricing(_full_pricing_html())
        score = score_pricing(signals)
        tips = get_pricing_tips(signals)
        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert isinstance(tips, list)
        assert all(isinstance(t, str) for t in tips)
