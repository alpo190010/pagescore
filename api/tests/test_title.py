"""Unit tests for title_detector and title_rubric.

Covers H1 detection (Dawn + older Shopify themes), meta title extraction,
brand detection cascades, keyword stuffing heuristics, ALL CAPS detection,
promotional text flagging, H1/meta title differentiation, specifics detection,
deterministic 0–100 scoring, and research-cited tip selection.
"""

from dataclasses import fields, is_dataclass

import pytest

from app.services.title_detector import TitleSignals, detect_title
from app.services.title_rubric import get_title_tips, score_title


# ---------------------------------------------------------------------------
# HTML fixture helpers
# ---------------------------------------------------------------------------


def _empty_html() -> str:
    """Baseline page with no H1 or meaningful content."""
    return "<html><head><title>Shop</title></head><body><p>Hello</p></body></html>"


def _dawn_theme_html() -> str:
    """Dawn theme with h1.product__title, JSON-LD brand, and <title> tag."""
    return (
        "<html><head>"
        "<title>Acme Leather Wallet - Black - Acme Store</title>"
        "</head><body>"
        '<h1 class="product__title">Acme Leather Wallet - Black</h1>'
        '<script type="application/ld+json">'
        '{"@type": "Product", "name": "Acme Leather Wallet", '
        '"brand": {"@type": "Brand", "name": "Acme"}}'
        "</script>"
        "</body></html>"
    )


def _older_theme_html() -> str:
    """Older Shopify theme with h1.product-single__title."""
    return (
        "<html><head><title>Classic Bag</title></head><body>"
        '<h1 class="product-single__title">Classic Bag</h1>'
        "</body></html>"
    )


def _no_h1_html() -> str:
    """Page with no H1 tag at all."""
    return (
        "<html><head><title>Some Product - Store</title></head><body>"
        "<h2>Product Name</h2><p>Description here.</p>"
        "</body></html>"
    )


def _multiple_h1_html() -> str:
    """Page with 3 H1 tags."""
    return (
        "<html><head><title>Multi H1 Page</title></head><body>"
        "<h1>First Title</h1>"
        "<h1>Second Title</h1>"
        "<h1>Third Title</h1>"
        "</body></html>"
    )


def _long_title_html() -> str:
    """H1 with >80 characters."""
    long = "A" * 120
    return (
        f"<html><head><title>Short Meta</title></head><body>"
        f"<h1>{long}</h1>"
        f"</body></html>"
    )


def _long_meta_title_html() -> str:
    """Meta title with >60 characters, short H1."""
    meta = "X" * 75
    return (
        f'<html><head><title>{meta}</title></head><body>'
        f'<h1>Short H1</h1>'
        f'</body></html>'
    )


def _keyword_stuffed_pipe_html() -> str:
    """Title with pipe-separated keyword list."""
    return (
        "<html><head><title>Wallet</title></head><body>"
        "<h1>Leather Wallet | Mens Wallet | Best Wallet | Wallet for Men</h1>"
        "</body></html>"
    )


def _keyword_stuffed_repeat_html() -> str:
    """Title with same word repeated 3+ times."""
    return (
        "<html><head><title>Leather</title></head><body>"
        "<h1>Premium Leather Genuine Leather Real Leather Wallet</h1>"
        "</body></html>"
    )


def _keyword_stuffed_commas_html() -> str:
    """Title with excessive commas."""
    return (
        "<html><head><title>Product</title></head><body>"
        "<h1>Wallet, Leather, Black, Mens, Bifold, RFID</h1>"
        "</body></html>"
    )


def _all_caps_html() -> str:
    """Title that is entirely ALL CAPS."""
    return (
        "<html><head><title>Wallet</title></head><body>"
        "<h1>PREMIUM GENUINE LEATHER WALLET FOR MEN</h1>"
        "</body></html>"
    )


def _caps_with_acronyms_html() -> str:
    """Title with legitimate acronyms — should NOT flag as all caps."""
    return (
        "<html><head><title>Charger</title></head><body>"
        "<h1>Premium LED USB Charging Station</h1>"
        "</body></html>"
    )


def _all_acronyms_html() -> str:
    """Title where all uppercase words are known acronyms — should NOT flag."""
    return (
        "<html><head><title>Mount</title></head><body>"
        "<h1>USB LED TV Mount</h1>"
        "</body></html>"
    )


def _promotional_html() -> str:
    """Title with promotional language."""
    return (
        "<html><head><title>Sale</title></head><body>"
        "<h1>Men's Wallet - 50% Off! Free Shipping!</h1>"
        "</body></html>"
    )


def _identical_titles_html() -> str:
    """H1 and meta title are identical."""
    return (
        "<html><head><title>Leather Wallet</title></head><body>"
        "<h1>Leather Wallet</h1>"
        "</body></html>"
    )


def _different_titles_html() -> str:
    """H1 and meta title differ meaningfully."""
    return (
        "<html><head><title>Best Leather Wallet for Men | Acme Store</title></head><body>"
        "<h1>Acme Premium Leather Bifold Wallet - Black</h1>"
        '<script type="application/ld+json">'
        '{"@type": "Product", "brand": {"@type": "Brand", "name": "Acme"}}'
        "</script>"
        "</body></html>"
    )


def _brand_og_site_name_html() -> str:
    """Brand detected via og:site_name (no JSON-LD brand)."""
    return (
        '<html><head><title>Widget</title>'
        '<meta property="og:site_name" content="BrandCo">'
        '</head><body>'
        '<h1>BrandCo Super Widget - Red</h1>'
        '</body></html>'
    )


def _brand_shopify_product_json_html() -> str:
    """Brand detected via Shopify product JSON vendor field."""
    return (
        "<html><head><title>Hat</title></head><body>"
        "<h1>CapBrand Classic Hat</h1>"
        '<script type="application/json" data-product-json>'
        '{"title": "Classic Hat", "vendor": "CapBrand"}'
        "</script>"
        "</body></html>"
    )


def _specifics_color_html() -> str:
    """Title with a color word."""
    return (
        "<html><head><title>Wallet</title></head><body>"
        "<h1>Premium Wallet - Black</h1>"
        "</body></html>"
    )


def _specifics_material_html() -> str:
    """Title with a material word."""
    return (
        "<html><head><title>Bag</title></head><body>"
        "<h1>Premium Leather Bag</h1>"
        "</body></html>"
    )


def _specifics_size_html() -> str:
    """Title with size info."""
    return (
        "<html><head><title>Bottle</title></head><body>"
        "<h1>Water Bottle 500ml</h1>"
        "</body></html>"
    )


def _generic_title_html() -> str:
    """Title with no specifics at all."""
    return (
        "<html><head><title>Product</title></head><body>"
        "<h1>Premium Widget</h1>"
        "</body></html>"
    )


def _single_word_caps_html() -> str:
    """Single ALL CAPS word — should NOT flag."""
    return (
        "<html><head><title>Test</title></head><body>"
        "<h1>WALLET</h1>"
        "</body></html>"
    )


def _h1_whitespace_only_html() -> str:
    """H1 with only whitespace."""
    return (
        "<html><head><title>Test</title></head><body>"
        "<h1>   </h1>"
        "</body></html>"
    )


def _brand_suffix_meta_html() -> str:
    """Meta title with ' - Brand' suffix, H1 matches base."""
    return (
        "<html><head><title>Leather Wallet - Acme Store</title></head><body>"
        "<h1>Leather Wallet</h1>"
        "</body></html>"
    )


def _perfect_title_html() -> str:
    """Title that should score ~100: brand, short, specifics, different meta."""
    return (
        "<html><head>"
        "<title>Acme Leather Wallet Black | Acme Store</title>"
        "</head><body>"
        '<h1 class="product__title">Acme Premium Leather Bifold Wallet - Black</h1>'
        '<script type="application/ld+json">'
        '{"@type": "Product", "name": "Acme Wallet", '
        '"brand": {"@type": "Brand", "name": "Acme"}}'
        "</script>"
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# H1 Detection Tests
# ---------------------------------------------------------------------------


class TestH1Detection:
    def test_dawn_theme_h1(self):
        signals = detect_title(_dawn_theme_html())
        assert signals.has_h1 is True
        assert signals.h1_text == "Acme Leather Wallet - Black"
        assert signals.h1_count == 1
        assert signals.has_single_h1 is True

    def test_older_theme_h1(self):
        signals = detect_title(_older_theme_html())
        assert signals.has_h1 is True
        assert signals.h1_text == "Classic Bag"

    def test_no_h1(self):
        signals = detect_title(_no_h1_html())
        assert signals.has_h1 is False
        assert signals.h1_text is None
        assert signals.h1_count == 0
        assert signals.h1_length == 0

    def test_multiple_h1(self):
        signals = detect_title(_multiple_h1_html())
        assert signals.has_h1 is True
        assert signals.h1_count == 3
        assert signals.has_single_h1 is False
        assert signals.h1_text == "First Title"

    def test_whitespace_only_h1(self):
        signals = detect_title(_h1_whitespace_only_html())
        assert signals.has_h1 is False
        assert signals.h1_text is None

    def test_empty_html(self):
        signals = detect_title(_empty_html())
        assert signals.has_h1 is False
        assert signals.h1_count == 0


# ---------------------------------------------------------------------------
# Meta Title Tests
# ---------------------------------------------------------------------------


class TestMetaTitleExtraction:
    def test_title_tag(self):
        signals = detect_title(_dawn_theme_html())
        assert signals.meta_title == "Acme Leather Wallet - Black - Acme Store"
        assert signals.meta_title_length == len("Acme Leather Wallet - Black - Acme Store")

    def test_og_title_fallback(self):
        html = (
            '<html><head><meta property="og:title" content="OG Product Title"></head>'
            "<body><h1>Product</h1></body></html>"
        )
        signals = detect_title(html)
        assert signals.meta_title == "OG Product Title"

    def test_no_meta_title(self):
        html = "<html><body><h1>Just H1</h1></body></html>"
        signals = detect_title(html)
        assert signals.meta_title is None
        assert signals.meta_title_length == 0


# ---------------------------------------------------------------------------
# Brand Detection Tests
# ---------------------------------------------------------------------------


class TestBrandDetection:
    def test_json_ld_brand(self):
        signals = detect_title(_dawn_theme_html())
        assert signals.brand_name == "Acme"

    def test_og_site_name_fallback(self):
        signals = detect_title(_brand_og_site_name_html())
        assert signals.brand_name == "BrandCo"

    def test_shopify_product_json_vendor(self):
        signals = detect_title(_brand_shopify_product_json_html())
        assert signals.brand_name == "CapBrand"

    def test_no_brand(self):
        signals = detect_title(_empty_html())
        assert signals.brand_name is None

    def test_json_ld_brand_string(self):
        html = (
            "<html><body><h1>Test</h1>"
            '<script type="application/ld+json">'
            '{"@type": "Product", "brand": "SimpleBrand"}'
            "</script></body></html>"
        )
        signals = detect_title(html)
        assert signals.brand_name == "SimpleBrand"


# ---------------------------------------------------------------------------
# Brand in Title Tests
# ---------------------------------------------------------------------------


class TestBrandInTitle:
    def test_brand_present(self):
        signals = detect_title(_dawn_theme_html())
        assert signals.has_brand_in_title is True

    def test_brand_missing_from_title(self):
        html = (
            '<html><head><meta property="og:site_name" content="Acme"></head>'
            "<body><h1>Premium Leather Wallet</h1></body></html>"
        )
        signals = detect_title(html)
        assert signals.brand_name == "Acme"
        assert signals.has_brand_in_title is False

    def test_no_brand_detected(self):
        signals = detect_title(_generic_title_html())
        assert signals.has_brand_in_title is False

    def test_brand_case_insensitive(self):
        html = (
            '<html><head><meta property="og:site_name" content="ACME"></head>'
            "<body><h1>acme Premium Wallet</h1></body></html>"
        )
        signals = detect_title(html)
        assert signals.has_brand_in_title is True


# ---------------------------------------------------------------------------
# Keyword Stuffing Tests
# ---------------------------------------------------------------------------


class TestKeywordStuffing:
    def test_pipe_separated(self):
        signals = detect_title(_keyword_stuffed_pipe_html())
        assert signals.has_keyword_stuffing is True

    def test_repeated_words(self):
        signals = detect_title(_keyword_stuffed_repeat_html())
        assert signals.has_keyword_stuffing is True

    def test_excessive_commas(self):
        signals = detect_title(_keyword_stuffed_commas_html())
        assert signals.has_keyword_stuffing is True

    def test_clean_title(self):
        signals = detect_title(_dawn_theme_html())
        assert signals.has_keyword_stuffing is False

    def test_two_pipes_not_stuffing(self):
        """Two segments (one pipe) should NOT trigger stuffing."""
        html = (
            "<html><body><h1>Brand | Product Name</h1></body></html>"
        )
        signals = detect_title(html)
        assert signals.has_keyword_stuffing is False


# ---------------------------------------------------------------------------
# ALL CAPS Tests
# ---------------------------------------------------------------------------


class TestAllCaps:
    def test_all_caps(self):
        signals = detect_title(_all_caps_html())
        assert signals.is_all_caps is True

    def test_mixed_case_with_acronyms(self):
        signals = detect_title(_caps_with_acronyms_html())
        assert signals.is_all_caps is False

    def test_all_known_acronyms(self):
        signals = detect_title(_all_acronyms_html())
        assert signals.is_all_caps is False

    def test_single_word_caps(self):
        signals = detect_title(_single_word_caps_html())
        assert signals.is_all_caps is False

    def test_normal_case(self):
        signals = detect_title(_dawn_theme_html())
        assert signals.is_all_caps is False


# ---------------------------------------------------------------------------
# Promotional Text Tests
# ---------------------------------------------------------------------------


class TestPromotionalText:
    def test_promotional_detected(self):
        signals = detect_title(_promotional_html())
        assert signals.has_promotional_text is True

    def test_clean_title(self):
        signals = detect_title(_dawn_theme_html())
        assert signals.has_promotional_text is False

    def test_double_exclamation(self):
        html = "<html><body><h1>Amazing Product!!</h1></body></html>"
        signals = detect_title(html)
        assert signals.has_promotional_text is True

    def test_clearance(self):
        html = "<html><body><h1>Clearance Winter Jacket</h1></body></html>"
        signals = detect_title(html)
        assert signals.has_promotional_text is True


# ---------------------------------------------------------------------------
# H1 vs Meta Title Tests
# ---------------------------------------------------------------------------


class TestH1MetaDiffer:
    def test_identical_titles(self):
        signals = detect_title(_identical_titles_html())
        assert signals.h1_meta_differ is False

    def test_different_titles(self):
        signals = detect_title(_different_titles_html())
        assert signals.h1_meta_differ is True

    def test_suffix_stripped(self):
        """Meta title with ' - Brand' suffix: after stripping, matches H1 → not different."""
        signals = detect_title(_brand_suffix_meta_html())
        assert signals.h1_meta_differ is False

    def test_missing_meta(self):
        html = "<html><body><h1>Product</h1></body></html>"
        signals = detect_title(html)
        assert signals.h1_meta_differ is False

    def test_missing_h1(self):
        signals = detect_title(_no_h1_html())
        assert signals.h1_meta_differ is False


# ---------------------------------------------------------------------------
# Specifics Tests
# ---------------------------------------------------------------------------


class TestSpecifics:
    def test_color(self):
        signals = detect_title(_specifics_color_html())
        assert signals.has_specifics is True

    def test_material(self):
        signals = detect_title(_specifics_material_html())
        assert signals.has_specifics is True

    def test_size(self):
        signals = detect_title(_specifics_size_html())
        assert signals.has_specifics is True

    def test_no_specifics(self):
        signals = detect_title(_generic_title_html())
        assert signals.has_specifics is False

    def test_model_designator(self):
        html = "<html><body><h1>Headphones Pro Max</h1></body></html>"
        signals = detect_title(html)
        assert signals.has_specifics is True


# ---------------------------------------------------------------------------
# Scoring Tests
# ---------------------------------------------------------------------------


class TestScoreTitle:
    def test_perfect_score(self):
        signals = detect_title(_perfect_title_html())
        score = score_title(signals)
        assert score == 100

    def test_no_h1_low_score(self):
        signals = detect_title(_no_h1_html())
        score = score_title(signals)
        # No H1 = 0 for H1(20), single H1(10), H1 length(10), brand in title(15), specifics(5)
        # Gets: no stuffing(10), no caps(5), no promo(5), meta title under 60 depends on length
        assert score <= 40

    def test_score_range(self):
        signals = detect_title(_dawn_theme_html())
        score = score_title(signals)
        assert 0 <= score <= 100

    def test_h1_length_boundary_80(self):
        """H1 at exactly 80 chars should earn length points."""
        title_80 = "A" * 80
        html = f"<html><head><title>Short</title></head><body><h1>{title_80}</h1></body></html>"
        signals = detect_title(html)
        assert signals.h1_length == 80
        # Score should include the 10 pts for H1 length
        score_with = score_title(signals)

        title_81 = "A" * 81
        html2 = f"<html><head><title>Short</title></head><body><h1>{title_81}</h1></body></html>"
        signals2 = detect_title(html2)
        assert signals2.h1_length == 81
        score_without = score_title(signals2)

        assert score_with > score_without

    def test_meta_length_boundary_60(self):
        """Meta at exactly 60 chars should earn length points."""
        meta_60 = "M" * 60
        html = f"<html><head><title>{meta_60}</title></head><body><h1>Product</h1></body></html>"
        signals = detect_title(html)
        assert signals.meta_title_length == 60
        score_with = score_title(signals)

        meta_61 = "M" * 61
        html2 = f"<html><head><title>{meta_61}</title></head><body><h1>Product</h1></body></html>"
        signals2 = detect_title(html2)
        assert signals2.meta_title_length == 61
        score_without = score_title(signals2)

        assert score_with > score_without

    def test_empty_html_score(self):
        signals = detect_title("")
        score = score_title(signals)
        assert score >= 0

    def test_all_issues_low_score(self):
        """Page with multiple problems should score very low."""
        html = (
            "<html><head><title>" + "X" * 75 + "</title></head><body>"
            "<h1>WALLET | WALLET | WALLET | 50% Off! Free Shipping!</h1>"
            "<h1>ANOTHER H1</h1>"
            "</body></html>"
        )
        signals = detect_title(html)
        score = score_title(signals)
        # H1 exists(20) + short(10) + titles differ(10) + not-all-caps(5) = 45
        assert score <= 50


# ---------------------------------------------------------------------------
# Tips Tests
# ---------------------------------------------------------------------------


class TestGetTitleTips:
    def test_no_h1_first_tip(self):
        signals = detect_title(_no_h1_html())
        tips = get_title_tips(signals)
        assert len(tips) >= 1
        assert "H1 tag" in tips[0]

    def test_max_three_tips(self):
        html = (
            "<html><head><title>" + "X" * 75 + "</title></head><body>"
            "<h1>WALLET | WALLET | WALLET | 50% Off!</h1>"
            "<h1>ANOTHER</h1>"
            "</body></html>"
        )
        tips = get_title_tips(detect_title(html))
        assert len(tips) <= 3

    def test_strong_score_encouragement(self):
        tips = get_title_tips(detect_title(_perfect_title_html()))
        assert any("Excellent" in t for t in tips)

    def test_tips_are_strings(self):
        tips = get_title_tips(detect_title(_dawn_theme_html()))
        assert all(isinstance(t, str) for t in tips)

    def test_brand_tip_requires_detected_brand(self):
        """Brand tip should NOT fire when no brand was detected."""
        signals = detect_title(_generic_title_html())
        assert signals.brand_name is None
        tips = get_title_tips(signals)
        assert not any("brand name" in t.lower() for t in tips)

    def test_brand_tip_fires_when_brand_missing(self):
        """Brand tip fires when brand detected but not in title."""
        html = (
            '<html><head><meta property="og:site_name" content="Acme">'
            "<title>Short</title></head>"
            "<body><h1>Premium Wallet</h1></body></html>"
        )
        signals = detect_title(html)
        assert signals.brand_name == "Acme"
        assert signals.has_brand_in_title is False
        tips = get_title_tips(signals)
        assert any("brand name" in t.lower() for t in tips)


# ---------------------------------------------------------------------------
# Dataclass Structure Tests
# ---------------------------------------------------------------------------


class TestDataclassStructure:
    def test_is_dataclass(self):
        assert is_dataclass(TitleSignals)

    def test_field_count(self):
        assert len(fields(TitleSignals)) == 14

    def test_default_values(self):
        sig = TitleSignals()
        assert sig.h1_text is None
        assert sig.meta_title is None
        assert sig.brand_name is None
        assert sig.h1_count == 0
        assert sig.h1_length == 0
        assert sig.meta_title_length == 0
        assert sig.has_h1 is False
        assert sig.has_single_h1 is False
        assert sig.has_brand_in_title is False
        assert sig.has_keyword_stuffing is False
        assert sig.is_all_caps is False
        assert sig.has_promotional_text is False
        assert sig.h1_meta_differ is False
        assert sig.has_specifics is False
