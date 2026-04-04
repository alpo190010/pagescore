"""Unit tests for mobile_cta_detector and mobile_cta_rubric.

Covers CTA button detection via Shopify selector cascade, viewport meta
detection, sticky class / app fingerprinting, Playwright measurement
injection, deterministic 0-100 scoring with HTML fallback tiers, and
research-cited tip selection (max 3).
"""

from dataclasses import fields, is_dataclass

import pytest

from app.services.mobile_cta_detector import MobileCtaSignals, detect_mobile_cta
from app.services.mobile_cta_rubric import get_mobile_cta_tips, score_mobile_cta


# ---------------------------------------------------------------------------
# HTML fixture helpers — minimal but realistic Shopify product page fragments
# ---------------------------------------------------------------------------


def _empty_html() -> str:
    """Baseline page with no CTA."""
    return "<html><body><h1>Product</h1></body></html>"


def _shopify_dawn_html() -> str:
    """Shopify Dawn theme with canonical cart form + submit button."""
    return (
        '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        "<body>"
        "<h1>Product</h1>"
        '<form action="/cart/add" method="post">'
        '<button type="submit" class="product-form__submit">Add to Cart</button>'
        "</form>"
        "</body></html>"
    )


def _name_add_button_html() -> str:
    """Page with button[name="add"] pattern."""
    return (
        '<html><head><meta name="viewport" content="width=device-width"></head>'
        "<body>"
        '<button name="add">Add to Cart</button>'
        "</body></html>"
    )


def _data_add_to_cart_html() -> str:
    """Page with [data-add-to-cart] attribute."""
    return (
        "<html><body>"
        '<button data-add-to-cart="">Buy Now</button>'
        "</body></html>"
    )


def _add_to_cart_id_html() -> str:
    """Page with #AddToCart element."""
    return (
        "<html><body>"
        '<button id="AddToCart">Add to Bag</button>'
        "</body></html>"
    )


def _class_btn_add_html() -> str:
    """Page with .btn--add-to-cart class."""
    return (
        "<html><body>"
        '<button class="btn--add-to-cart">Add to Cart</button>'
        "</body></html>"
    )


def _text_fallback_html() -> str:
    """Page where CTA is only detectable by text content."""
    return (
        "<html><body>"
        "<button>Add to Cart</button>"
        "</body></html>"
    )


def _multiple_ctas_html() -> str:
    """Page with multiple CTA buttons."""
    return (
        '<html><head><meta name="viewport" content="width=device-width"></head>'
        "<body>"
        '<form action="/cart/add" method="post">'
        '<button type="submit">Add to Cart</button>'
        "</form>"
        '<button class="btn--add-to-cart">Quick Buy</button>'
        "<button>Add to Cart</button>"
        "</body></html>"
    )


def _sticky_class_html() -> str:
    """Page with sticky CTA class."""
    return (
        '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        "<body>"
        '<div class="sticky-add-to-cart">'
        '<form action="/cart/add" method="post">'
        '<button type="submit">Add to Cart</button>'
        "</form>"
        "</div>"
        "</body></html>"
    )


def _sticky_app_vitals_html() -> str:
    """Page with Vitals sticky ATC app fingerprint."""
    return (
        '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        "<body>"
        '<div class="vitals-sticky">'
        '<button name="add">Add to Cart</button>'
        "</div>"
        '<script src="https://cdn.vitals.co/sticky-atc.js"></script>'
        "</body></html>"
    )


def _sticky_app_cartimize_html() -> str:
    """Page with Cartimize sticky ATC app."""
    return (
        "<html><body>"
        '<div class="cartimize-sticky">'
        '<button name="add">Buy Now</button>'
        "</div>"
        "</body></html>"
    )


def _viewport_meta_only_html() -> str:
    """Page with only viewport meta, no CTA."""
    return (
        '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        "<body><h1>Product</h1></body></html>"
    )


def _input_submit_html() -> str:
    """Page with input[type=submit] inside cart form."""
    return (
        "<html><body>"
        '<form action="/cart/add" method="post">'
        '<input type="submit" value="Add to Cart" />'
        "</form>"
        "</body></html>"
    )


def _inline_sticky_style_html() -> str:
    """Page with inline position:fixed style on a CTA container."""
    return (
        "<html><body>"
        '<div style="position: fixed; bottom: 0; width: 100%;">'
        "<button>Add to Cart</button>"
        "</div>"
        "</body></html>"
    )


def _full_playwright_measurements() -> dict:
    """Measurements dict simulating Playwright results for a well-optimised page."""
    return {
        "button_width_px": 343.0,
        "button_height_px": 64.0,
        "meets_min_44px": True,
        "meets_optimal_60_72px": True,
        "above_fold": True,
        "is_sticky": True,
        "in_thumb_zone": True,
        "is_full_width": True,
    }


def _partial_playwright_measurements() -> dict:
    """Measurements where button is small, not sticky, above fold."""
    return {
        "button_width_px": 180.0,
        "button_height_px": 36.0,
        "meets_min_44px": False,
        "meets_optimal_60_72px": False,
        "above_fold": True,
        "is_sticky": False,
        "in_thumb_zone": False,
        "is_full_width": False,
    }


# ===========================================================================
# TestDetection — CTA selector cascade and meta detection
# ===========================================================================


class TestDetection:
    """HTML fixture tests for signal extraction accuracy."""

    def test_empty_html_no_cta(self):
        signals = detect_mobile_cta(_empty_html())
        assert signals.cta_found is False
        assert signals.cta_text is None
        assert signals.cta_count == 0
        assert signals.cta_selector_matched is None
        assert signals.has_viewport_meta is False

    def test_shopify_dawn_form_detected(self):
        signals = detect_mobile_cta(_shopify_dawn_html())
        assert signals.cta_found is True
        assert signals.cta_text == "Add to Cart"
        assert signals.cta_count >= 1
        assert "cart/add" in signals.cta_selector_matched
        assert signals.has_viewport_meta is True
        assert signals.has_responsive_meta is True

    def test_name_add_button(self):
        signals = detect_mobile_cta(_name_add_button_html())
        assert signals.cta_found is True
        assert signals.cta_text == "Add to Cart"

    def test_data_add_to_cart(self):
        signals = detect_mobile_cta(_data_add_to_cart_html())
        assert signals.cta_found is True
        assert signals.cta_text == "Buy Now"
        assert signals.cta_selector_matched == "[data-add-to-cart]"

    def test_add_to_cart_id(self):
        signals = detect_mobile_cta(_add_to_cart_id_html())
        assert signals.cta_found is True
        assert signals.cta_text == "Add to Bag"

    def test_class_btn_add(self):
        signals = detect_mobile_cta(_class_btn_add_html())
        assert signals.cta_found is True
        assert signals.cta_selector_matched == ".btn--add-to-cart"

    def test_text_content_fallback(self):
        signals = detect_mobile_cta(_text_fallback_html())
        assert signals.cta_found is True
        assert signals.cta_text == "Add to Cart"
        assert signals.cta_selector_matched == "text:add-to-cart"

    def test_multiple_ctas_counted(self):
        signals = detect_mobile_cta(_multiple_ctas_html())
        assert signals.cta_found is True
        assert signals.cta_count >= 2

    def test_viewport_meta_detected(self):
        signals = detect_mobile_cta(_viewport_meta_only_html())
        assert signals.has_viewport_meta is True
        assert signals.has_responsive_meta is True
        assert signals.cta_found is False

    def test_no_viewport_meta(self):
        signals = detect_mobile_cta(_empty_html())
        assert signals.has_viewport_meta is False
        assert signals.has_responsive_meta is False

    def test_sticky_class_detected(self):
        signals = detect_mobile_cta(_sticky_class_html())
        assert signals.has_sticky_class is True

    def test_sticky_app_vitals(self):
        signals = detect_mobile_cta(_sticky_app_vitals_html())
        assert signals.has_sticky_app == "vitals"

    def test_sticky_app_cartimize(self):
        signals = detect_mobile_cta(_sticky_app_cartimize_html())
        assert signals.has_sticky_app == "cartimize"

    def test_input_submit_detected(self):
        signals = detect_mobile_cta(_input_submit_html())
        assert signals.cta_found is True
        assert signals.cta_text == "Add to Cart"

    def test_inline_sticky_style(self):
        signals = detect_mobile_cta(_inline_sticky_style_html())
        assert signals.has_sticky_class is True

    def test_measurements_injected(self):
        signals = detect_mobile_cta(
            _shopify_dawn_html(),
            measurements=_full_playwright_measurements(),
        )
        assert signals.button_width_px == 343.0
        assert signals.button_height_px == 64.0
        assert signals.meets_min_44px is True
        assert signals.meets_optimal_60_72px is True
        assert signals.above_fold is True
        assert signals.is_sticky is True
        assert signals.in_thumb_zone is True
        assert signals.is_full_width is True

    def test_no_measurements_stays_none(self):
        signals = detect_mobile_cta(_shopify_dawn_html())
        assert signals.button_width_px is None
        assert signals.is_sticky is None
        assert signals.above_fold is None

    def test_empty_string_returns_defaults(self):
        signals = detect_mobile_cta("")
        assert signals.cta_found is False
        assert signals.cta_count == 0


# ===========================================================================
# TestScoring — deterministic score verification
# ===========================================================================


class TestScoring:
    """Verify scoring rubric produces correct weighted totals."""

    def test_empty_signals_score_0(self):
        assert score_mobile_cta(MobileCtaSignals()) == 0

    def test_cta_found_only_base_score(self):
        signals = MobileCtaSignals(cta_found=True, cta_count=1, cta_text="Add to Cart")
        score = score_mobile_cta(signals)
        # 15 (found) + 5 (count==1) + 5 (action text) + 5 (partial touch) = 30
        assert score == 30

    def test_full_html_signals_max_without_playwright(self):
        """HTML-only signals should cap around 65."""
        signals = MobileCtaSignals(
            cta_found=True,
            cta_text="Add to Cart",
            cta_count=1,
            has_viewport_meta=True,
            has_responsive_meta=True,
            has_sticky_class=True,
        )
        score = score_mobile_cta(signals)
        # 15 (found) + 15 (sticky class) + 10 (above proxy) + 5 (touch partial)
        # + 3 (full-width proxy) + 5 (responsive) + 5 (count) + 5 (text) = 63
        assert 55 <= score <= 70

    def test_full_signals_with_playwright_score_100(self):
        """All signals true + Playwright measurements should hit 100."""
        signals = MobileCtaSignals(
            cta_found=True,
            cta_text="Add to Cart",
            cta_count=1,
            has_viewport_meta=True,
            has_responsive_meta=True,
            has_sticky_class=True,
            is_sticky=True,
            above_fold=True,
            meets_min_44px=True,
            meets_optimal_60_72px=True,
            in_thumb_zone=True,
            is_full_width=True,
        )
        score = score_mobile_cta(signals)
        assert score == 100

    def test_sticky_html_fallback_vs_playwright(self):
        """HTML sticky class gives 15 pts, Playwright is_sticky gives 20 pts."""
        html_only = MobileCtaSignals(cta_found=True, has_sticky_class=True)
        pw_only = MobileCtaSignals(cta_found=True, is_sticky=True)
        assert score_mobile_cta(pw_only) > score_mobile_cta(html_only)

    def test_score_clamped_to_0_100(self):
        """Score never exceeds 100 or goes below 0."""
        # Max everything
        signals = MobileCtaSignals(
            cta_found=True, cta_text="Buy Now", cta_count=1,
            has_viewport_meta=True, has_responsive_meta=True,
            has_sticky_class=True, has_sticky_app="vitals",
            is_sticky=True, above_fold=True, meets_min_44px=True,
            meets_optimal_60_72px=True, in_thumb_zone=True, is_full_width=True,
        )
        assert 0 <= score_mobile_cta(signals) <= 100
        # Min everything
        assert score_mobile_cta(MobileCtaSignals()) >= 0

    def test_excessive_ctas_penalised(self):
        """More than 3 CTAs should reduce score."""
        one_cta = MobileCtaSignals(cta_found=True, cta_count=1)
        many_ctas = MobileCtaSignals(cta_found=True, cta_count=5)
        assert score_mobile_cta(one_cta) > score_mobile_cta(many_ctas)

    def test_partial_playwright_measurements(self):
        """Partial Playwright data: above_fold=True but not sticky."""
        signals = MobileCtaSignals(
            cta_found=True,
            cta_text="Add to Cart",
            cta_count=1,
            has_responsive_meta=True,
            above_fold=True,
            is_sticky=False,
            meets_min_44px=False,
            in_thumb_zone=False,
            is_full_width=False,
        )
        score = score_mobile_cta(signals)
        # 15 (found) + 15 (above fold) + 5 (responsive) + 5 (count) + 5 (text) = 45
        assert score == 45


# ===========================================================================
# TestTipSelection — priority ordering and research citations
# ===========================================================================


class TestTipSelection:
    """Verify tip selection logic, priority, and content."""

    def test_empty_signals_returns_tips(self):
        tips = get_mobile_cta_tips(MobileCtaSignals())
        assert len(tips) >= 1
        assert len(tips) <= 3

    def test_no_cta_tip_first_priority(self):
        tips = get_mobile_cta_tips(MobileCtaSignals())
        assert "Add to Cart button" in tips[0] or "CTA" in tips[0] or "79%" in tips[0]

    def test_sticky_tip_includes_citation(self):
        signals = MobileCtaSignals(
            cta_found=True, cta_count=1,
            has_responsive_meta=True,
        )
        tips = get_mobile_cta_tips(signals)
        sticky_tips = [t for t in tips if "sticky" in t.lower() or "Growth Rock" in t]
        assert len(sticky_tips) >= 1
        assert "Growth Rock" in sticky_tips[0]

    def test_max_3_tips_enforced(self):
        tips = get_mobile_cta_tips(MobileCtaSignals())
        assert len(tips) <= 3

    def test_full_signals_congratulatory(self):
        signals = MobileCtaSignals(
            cta_found=True, cta_text="Add to Cart", cta_count=1,
            has_viewport_meta=True, has_responsive_meta=True,
            is_sticky=True, above_fold=True, meets_min_44px=True,
            meets_optimal_60_72px=True, in_thumb_zone=True, is_full_width=True,
        )
        tips = get_mobile_cta_tips(signals)
        assert any("Excellent" in t or "ahead" in t for t in tips)

    def test_tip_priority_no_cta_before_sticky(self):
        """Missing CTA tip should appear before sticky tip."""
        tips = get_mobile_cta_tips(MobileCtaSignals())
        # First tip should be about missing CTA, not about sticky
        assert "79%" in tips[0] or "Add" in tips[0]

    def test_viewport_meta_tip_present(self):
        signals = MobileCtaSignals(
            cta_found=True, cta_count=1,
            has_responsive_meta=False,
            is_sticky=True, above_fold=True,
            meets_min_44px=True,
        )
        tips = get_mobile_cta_tips(signals)
        viewport_tips = [t for t in tips if "viewport" in t.lower()]
        assert len(viewport_tips) >= 1


# ===========================================================================
# TestDataclassStructure — invariants
# ===========================================================================


class TestDataclassStructure:
    """Verify MobileCtaSignals dataclass structure and defaults."""

    def test_is_dataclass(self):
        assert is_dataclass(MobileCtaSignals)

    def test_field_count(self):
        assert len(fields(MobileCtaSignals)) == 16

    def test_default_values(self):
        signals = MobileCtaSignals()
        assert signals.cta_found is False
        assert signals.cta_text is None
        assert signals.cta_count == 0
        assert signals.cta_selector_matched is None
        assert signals.has_viewport_meta is False
        assert signals.has_responsive_meta is False
        assert signals.has_sticky_class is False
        assert signals.has_sticky_app is None
        assert signals.button_width_px is None
        assert signals.button_height_px is None
        assert signals.meets_min_44px is None
        assert signals.meets_optimal_60_72px is None
        assert signals.above_fold is None
        assert signals.is_sticky is None
        assert signals.in_thumb_zone is None
        assert signals.is_full_width is None


# ===========================================================================
# TestEndToEnd — full pipeline HTML → detect → score → tips
# ===========================================================================


class TestEndToEnd:
    """Full pipeline tests combining detector, scorer, and tip selector."""

    def test_empty_html_scores_0_with_tips(self):
        signals = detect_mobile_cta(_empty_html())
        score = score_mobile_cta(signals)
        tips = get_mobile_cta_tips(signals)
        assert score == 0
        assert len(tips) >= 1

    def test_dawn_html_scores_reasonable(self):
        signals = detect_mobile_cta(_shopify_dawn_html())
        score = score_mobile_cta(signals)
        tips = get_mobile_cta_tips(signals)
        assert score > 0
        assert isinstance(tips, list)

    def test_sticky_html_scores_higher(self):
        plain_score = score_mobile_cta(detect_mobile_cta(_shopify_dawn_html()))
        sticky_score = score_mobile_cta(detect_mobile_cta(_sticky_class_html()))
        assert sticky_score > plain_score

    def test_pipeline_with_playwright_measurements(self):
        signals = detect_mobile_cta(
            _shopify_dawn_html(),
            measurements=_full_playwright_measurements(),
        )
        score = score_mobile_cta(signals)
        tips = get_mobile_cta_tips(signals)
        assert score >= 85
        assert any("Excellent" in t or "ahead" in t for t in tips)

    def test_pipeline_with_partial_measurements(self):
        signals = detect_mobile_cta(
            _shopify_dawn_html(),
            measurements=_partial_playwright_measurements(),
        )
        score = score_mobile_cta(signals)
        tips = get_mobile_cta_tips(signals)
        # Should score lower than full measurements
        assert score < 85
        assert len(tips) >= 1
