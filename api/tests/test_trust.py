"""Unit tests for trust_detector and trust_rubric.

Covers trust badge detection, guarantee/return policy signals, security
indicators, live chat widgets, contact info, ATC proximity detection,
deterministic 0-100 scoring, and research-cited tip selection (max 3).
"""

from dataclasses import fields, is_dataclass

import pytest

from app.services.trust_detector import TrustSignals, detect_trust
from app.services.trust_rubric import get_trust_tips, score_trust


# ---------------------------------------------------------------------------
# HTML fixture helpers — minimal but realistic Shopify product page fragments
# ---------------------------------------------------------------------------


def _empty_html() -> str:
    """Baseline page with no trust signals."""
    return "<html><body><h1>Product</h1></body></html>"


def _money_back_guarantee_html() -> str:
    """Page with money-back guarantee text."""
    return (
        "<html><body>"
        "<h1>Product</h1>"
        '<p class="guarantee">30-day money-back guarantee</p>'
        "</body></html>"
    )


def _return_policy_html() -> str:
    """Page with visible return policy text."""
    return (
        "<html><body>"
        "<h1>Product</h1>"
        "<p>Free returns within 30 days</p>"
        "</body></html>"
    )


def _security_badge_html() -> str:
    """Page with Norton security badge and secure checkout text."""
    return (
        "<html><body>"
        "<h1>Product</h1>"
        '<img src="https://cdn.example.com/norton-seal.png" alt="Norton Secured" />'
        "<p>Secure checkout guaranteed</p>"
        "</body></html>"
    )


def _safe_checkout_html() -> str:
    """Page with 'Guaranteed Safe Checkout' badge and payment icons."""
    return (
        "<html><body>"
        "<h1>Product</h1>"
        "<div>Guaranteed Safe Checkout</div>"
        '<img src="/icons/visa.svg" alt="Visa" />'
        '<img src="/icons/mastercard.svg" alt="Mastercard" />'
        "</body></html>"
    )


def _live_chat_html() -> str:
    """Page with Tidio chat widget."""
    return (
        "<html><body>"
        "<h1>Product</h1>"
        '<div id="tidio-chat"></div>'
        '<script src="https://code.tidio.co/abc123.js"></script>'
        "</body></html>"
    )


def _phone_email_html() -> str:
    """Page with phone number and contact email links."""
    return (
        "<html><body>"
        "<h1>Product</h1>"
        '<a href="tel:+1-555-123-4567">Call us</a>'
        '<a href="mailto:support@example.com">Email us</a>'
        "</body></html>"
    )


def _trust_near_atc_html() -> str:
    """Page with ATC button and trust badge in same parent container."""
    return (
        "<html><body>"
        "<h1>Product</h1>"
        '<form action="/cart/add" method="post">'
        '  <button type="submit" name="add">Add to Cart</button>'
        '  <div class="trust-badges">'
        '    <img src="/trust-badge.png" alt="Trust Badge" />'
        "  </div>"
        "  <p>30-day money-back guarantee</p>"
        "</form>"
        "</body></html>"
    )


def _hextom_badge_html() -> str:
    """Page with Hextom trust badge app elements."""
    return (
        "<html><body>"
        "<h1>Product</h1>"
        '<div class="usb-trust-badges">'
        '  <img src="/trust-badge-1.png" alt="Trust Badge" />'
        '  <img src="/secure-badge.png" alt="Secure Badge" />'
        "</div>"
        '<script src="https://cdn.hextom.com/badge.js"></script>'
        "</body></html>"
    )


def _free_shipping_html() -> str:
    """Page with free shipping messaging."""
    return (
        "<html><body>"
        "<h1>Product</h1>"
        "<p>Free shipping on all orders</p>"
        "</body></html>"
    )


def _full_trust_html() -> str:
    """Page combining ALL trust signals for maximum score."""
    return (
        "<html><body>"
        "<h1>Product</h1>"
        # Trust badge app (Hextom) + badges
        '<div class="hextom-trust-badges">'
        '  <img src="/trust-badge-1.png" alt="Trust Badge 1" />'
        '  <img src="/secure-badge.png" alt="Secure Badge" />'
        "</div>"
        # Payment icons
        '<img src="/icons/visa.svg" alt="Visa" />'
        '<img src="/icons/mastercard.svg" alt="Mastercard" />'
        # Money-back guarantee
        "<p>30-day money-back guarantee</p>"
        # Return policy
        "<p>Free returns within 30 days</p>"
        # Free shipping
        "<p>Free shipping on orders over $50</p>"
        # Secure checkout text
        "<p>Secure checkout guaranteed</p>"
        # Security badge
        '<img src="/norton-seal.png" alt="Norton Secured" />'
        # Safe checkout badge
        "<div>Guaranteed Safe Checkout</div>"
        # Live chat (Tidio)
        '<div id="tidio-chat"></div>'
        '<script src="https://code.tidio.co/abc123.js"></script>'
        # Phone + email
        '<a href="tel:+1-555-123-4567">Call us</a>'
        '<a href="mailto:support@example.com">Email us</a>'
        # ATC form with trust inside
        '<form action="/cart/add" method="post">'
        '  <button type="submit" name="add">Add to Cart</button>'
        '  <span class="trust-seal">Secure checkout</span>'
        "</form>"
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# Helper to build signals directly for rubric tests
# ---------------------------------------------------------------------------


def _all_true_signals() -> TrustSignals:
    """Signals with every boolean True and max counts."""
    return TrustSignals(
        trust_badge_app="hextom",
        trust_badge_count=2,
        has_payment_icons=True,
        has_money_back_guarantee=True,
        has_return_policy=True,
        has_free_shipping_badge=True,
        has_secure_checkout_text=True,
        has_security_badge=True,
        has_safe_checkout_badge=True,
        has_live_chat=True,
        has_phone_number=True,
        has_contact_email=True,
        has_trust_near_atc=True,
        trust_element_count=11,
    )


# ---------------------------------------------------------------------------
# 1. TestDetection
# ---------------------------------------------------------------------------


class TestDetection:
    """Detection of individual trust signals from HTML."""

    def test_empty_html_no_signals(self):
        """Empty page -> every boolean signal is False."""
        signals = detect_trust(_empty_html())
        assert signals.has_money_back_guarantee is False
        assert signals.has_return_policy is False
        assert signals.has_security_badge is False
        assert signals.has_safe_checkout_badge is False
        assert signals.has_live_chat is False
        assert signals.has_phone_number is False
        assert signals.has_contact_email is False
        assert signals.has_trust_near_atc is False
        assert signals.trust_badge_count == 0
        assert signals.trust_badge_app is None
        assert signals.trust_element_count == 0

    def test_money_back_guarantee_detected(self):
        signals = detect_trust(_money_back_guarantee_html())
        assert signals.has_money_back_guarantee is True

    def test_return_policy_detected(self):
        signals = detect_trust(_return_policy_html())
        assert signals.has_return_policy is True

    def test_security_badge_detected(self):
        signals = detect_trust(_security_badge_html())
        assert signals.has_security_badge is True

    def test_secure_checkout_text_detected(self):
        signals = detect_trust(_security_badge_html())
        assert signals.has_secure_checkout_text is True

    def test_safe_checkout_badge_detected(self):
        signals = detect_trust(_safe_checkout_html())
        assert signals.has_safe_checkout_badge is True

    def test_payment_icons_detected(self):
        signals = detect_trust(_safe_checkout_html())
        assert signals.has_payment_icons is True

    def test_live_chat_detected(self):
        signals = detect_trust(_live_chat_html())
        assert signals.has_live_chat is True

    def test_phone_number_detected(self):
        signals = detect_trust(_phone_email_html())
        assert signals.has_phone_number is True

    def test_contact_email_detected(self):
        signals = detect_trust(_phone_email_html())
        assert signals.has_contact_email is True

    def test_trust_near_atc_detected(self):
        signals = detect_trust(_trust_near_atc_html())
        assert signals.has_trust_near_atc is True

    def test_hextom_app_detected(self):
        signals = detect_trust(_hextom_badge_html())
        assert signals.trust_badge_app == "hextom"

    def test_trust_badge_count(self):
        signals = detect_trust(_hextom_badge_html())
        assert signals.trust_badge_count >= 2

    def test_free_shipping_detected(self):
        signals = detect_trust(_free_shipping_html())
        assert signals.has_free_shipping_badge is True

    def test_full_html_all_key_signals_true(self):
        """Full trust HTML sets all key boolean signals to True."""
        signals = detect_trust(_full_trust_html())
        assert signals.has_money_back_guarantee is True
        assert signals.has_return_policy is True
        assert signals.has_security_badge is True
        assert signals.has_safe_checkout_badge is True
        assert signals.has_live_chat is True
        assert signals.has_phone_number is True
        assert signals.has_contact_email is True
        assert signals.has_payment_icons is True
        assert signals.has_secure_checkout_text is True
        assert signals.has_free_shipping_badge is True
        assert signals.trust_badge_app is not None

    def test_empty_string_returns_defaults(self):
        """Empty string input returns all-default signals."""
        signals = detect_trust("")
        assert signals.has_money_back_guarantee is False
        assert signals.trust_badge_count == 0
        assert signals.trust_element_count == 0

    def test_trust_element_count_reflects_signals(self):
        """trust_element_count matches number of true boolean signals."""
        signals = detect_trust(_phone_email_html())
        # phone + email = 2 true booleans
        assert signals.trust_element_count == 2

    def test_trust_near_atc_false_without_trust_elements(self):
        """ATC button alone without trust elements -> has_trust_near_atc is False."""
        html = (
            "<html><body>"
            '<form action="/cart/add" method="post">'
            '  <button type="submit" name="add">Add to Cart</button>'
            "</form>"
            "</body></html>"
        )
        signals = detect_trust(html)
        assert signals.has_trust_near_atc is False


# ---------------------------------------------------------------------------
# 2. TestScoring
# ---------------------------------------------------------------------------


class TestScoring:
    """Deterministic 0-100 scoring from TrustSignals."""

    def test_empty_signals_score_0(self):
        assert score_trust(TrustSignals()) == 0

    def test_full_signals_score_100(self):
        assert score_trust(_all_true_signals()) == 100

    def test_money_back_guarantee_only_score(self):
        """Money-back guarantee alone -> 20 pts."""
        s = TrustSignals(has_money_back_guarantee=True)
        assert score_trust(s) == 20

    def test_trust_near_atc_only_score(self):
        """Trust near ATC alone -> 15 pts."""
        s = TrustSignals(has_trust_near_atc=True)
        assert score_trust(s) == 15

    def test_return_policy_only_score(self):
        """Return policy alone -> 12 pts."""
        s = TrustSignals(has_return_policy=True)
        assert score_trust(s) == 12

    def test_security_badge_only_score(self):
        """Security badge alone -> 10 pts."""
        s = TrustSignals(has_security_badge=True)
        assert score_trust(s) == 10

    def test_badge_count_scoring(self):
        """1 badge -> 5 pts, 2 badges -> 5 + 3 = 8 pts."""
        s1 = TrustSignals(trust_badge_count=1)
        assert score_trust(s1) == 5
        s2 = TrustSignals(trust_badge_count=2)
        assert score_trust(s2) == 8

    def test_partial_score_predictable(self):
        """Guarantee + return + phone -> 20 + 12 + 4 = 36."""
        s = TrustSignals(
            has_money_back_guarantee=True,
            has_return_policy=True,
            has_phone_number=True,
        )
        assert score_trust(s) == 36

    def test_score_clamped_to_0_100(self):
        """Score is always clamped within [0, 100]."""
        assert score_trust(TrustSignals()) >= 0
        assert score_trust(_all_true_signals()) <= 100


# ---------------------------------------------------------------------------
# 3. TestTipSelection
# ---------------------------------------------------------------------------


class TestTipSelection:
    """Tip ordering, max count, citations, and content verification."""

    def test_empty_signals_tips_returned(self):
        """Empty signals -> 3 most impactful tips returned."""
        tips = get_trust_tips(TrustSignals())
        assert len(tips) == 3

    def test_full_signals_congratulatory_tip(self):
        """All signals present (score >= 75) -> congratulatory tip."""
        tips = get_trust_tips(_all_true_signals())
        assert len(tips) == 1
        assert "Strong trust setup" in tips[0]

    def test_max_3_tips_enforced(self):
        """Never more than 3 tips regardless of missing signals."""
        tips = get_trust_tips(TrustSignals())
        assert len(tips) <= 3

    def test_tips_are_strings_and_nonempty(self):
        """All tips are non-empty strings with meaningful content."""
        tips = get_trust_tips(TrustSignals())
        assert all(isinstance(t, str) for t in tips)
        assert all(len(t) > 10 for t in tips)

    def test_no_guarantee_tip_includes_citation(self):
        """Money-back guarantee tip cites VWO research."""
        tips = get_trust_tips(TrustSignals())
        guarantee_tips = [t for t in tips if "money-back" in t.lower() or "guarantee" in t.lower()]
        assert len(guarantee_tips) >= 1
        assert "VWO" in guarantee_tips[0]

    def test_tip_priority_order(self):
        """Tips follow defined priority: guarantee -> return -> security."""
        tips = get_trust_tips(TrustSignals())
        assert len(tips) == 3
        # First: money-back guarantee
        assert "money-back" in tips[0].lower() or "guarantee" in tips[0].lower()
        # Second: return policy (since empty signals has no trust elements, tip #2 skips "near ATC")
        assert "return" in tips[1].lower()
        # Third: security badge
        assert "security" in tips[2].lower() or "badge" in tips[2].lower()

    def test_partial_signals_fewer_tips(self):
        """Having most signals gives congratulatory tip."""
        tips = get_trust_tips(_all_true_signals())
        assert len(tips) == 1
        assert "Strong" in tips[0]


# ---------------------------------------------------------------------------
# 4. TestDataclassStructure
# ---------------------------------------------------------------------------


class TestDataclassStructure:
    """TrustSignals dataclass invariants."""

    def test_signals_is_dataclass(self):
        assert is_dataclass(TrustSignals)

    def test_field_count(self):
        """14 fields: 3 badge + 3 guarantee + 3 security + 3 contact + 2 aggregate."""
        assert len(fields(TrustSignals)) == 14

    def test_default_values_all_false_or_zero_or_none(self):
        """All bools default to False; ints to 0; strings to None."""
        s = TrustSignals()
        for f in fields(s):
            val = getattr(s, f.name)
            if isinstance(val, bool):
                assert val is False, f"{f.name} should default to False"
            elif isinstance(val, int):
                assert val == 0, f"{f.name} should default to 0"
            elif val is not None:
                pytest.fail(f"{f.name} should default to None, got {val}")

    def test_instantiation_with_no_args(self):
        """Can instantiate with no args and get valid defaults."""
        s = TrustSignals()
        assert s.trust_badge_app is None
        assert s.trust_badge_count == 0
        assert s.has_money_back_guarantee is False


# ---------------------------------------------------------------------------
# 5. TestEndToEnd
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """Full pipeline: HTML -> detect -> score -> tips."""

    def test_full_html_high_score_congratulatory(self):
        """Full trust HTML -> high score, congratulatory tip."""
        signals = detect_trust(_full_trust_html())
        score = score_trust(signals)
        assert score >= 75
        tips = get_trust_tips(signals)
        assert any("Strong" in t for t in tips)

    def test_empty_html_scores_0_with_tips(self):
        """Empty HTML -> score 0, 3 improvement tips."""
        signals = detect_trust(_empty_html())
        assert score_trust(signals) == 0
        tips = get_trust_tips(signals)
        assert len(tips) == 3

    def test_partial_html_mid_range_score(self):
        """Security badge HTML -> mid-range score with tips."""
        signals = detect_trust(_security_badge_html())
        score = score_trust(signals)
        assert 0 < score < 100
        tips = get_trust_tips(signals)
        assert 0 < len(tips) <= 3

    def test_detect_score_tips_pipeline_consistent(self):
        """detect -> score -> tips pipeline produces consistent typed results."""
        signals = detect_trust(_full_trust_html())
        score = score_trust(signals)
        tips = get_trust_tips(signals)
        assert isinstance(score, int)
        assert 0 <= score <= 100
        assert isinstance(tips, list)
        assert all(isinstance(t, str) for t in tips)
