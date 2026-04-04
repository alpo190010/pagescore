"""Tests for description quality detector and rubric.

Covers: extraction fallbacks, readability metrics, persuasion language,
HTML formatting, scoring boundaries, tip selection, and end-to-end flow.
"""

from dataclasses import fields, is_dataclass

import pytest

from app.services.description_detector import (
    DescriptionSignals,
    _count_syllables,
    _split_sentences,
    detect_description,
)
from app.services.description_rubric import (
    get_description_tips,
    score_description,
)


# ---------------------------------------------------------------------------
# HTML fixture helpers
# ---------------------------------------------------------------------------


def _empty_html() -> str:
    return "<html><head></head><body><h1>Product</h1></body></html>"


def _dawn_description_html(content: str = "") -> str:
    """Dawn theme with product__description rte container."""
    if not content:
        content = (
            "<h2>Why You'll Love It</h2>"
            "<p>Experience the ultimate comfort with our premium organic cotton tee. "
            "Your skin will feel amazing every day. Enjoy effortless style that transforms "
            "your wardrobe. Discover the perfect blend of luxury and durability.</p>"
            "<ul><li>100% organic cotton</li><li>Pre-shrunk fabric</li>"
            "<li>Machine washable</li></ul>"
            "<p>This <strong>beautiful</strong> piece is <em>designed</em> for "
            "everyday wear. Made from the finest materials, it includes a reinforced "
            "neckline and double-stitched hems.</p>"
        )
    return (
        '<html><head></head><body>'
        f'<div class="product__description rte">{content}</div>'
        '</body></html>'
    )


def _plain_text_description_html() -> str:
    """Description with no HTML formatting tags."""
    return (
        '<html><body>'
        '<div class="product__description rte">'
        'This is a simple product. It is made from cotton. '
        'The material is soft. You will enjoy wearing it. '
        'It comes in multiple sizes. The product features a classic design.'
        '</div></body></html>'
    )


def _short_description_html() -> str:
    """Under 50 words."""
    return (
        '<html><body>'
        '<div class="product__description rte">'
        '<p>A nice shirt. Very comfortable.</p>'
        '</div></body></html>'
    )


def _long_description_html() -> str:
    """Over 600 words — padded with repeated sentences."""
    sentences = (
        "This premium product is crafted from the finest materials. "
        "You will enjoy the exceptional quality and comfort it provides. "
        "Experience the difference that genuine craftsmanship makes. "
        "Our team has designed this with your needs in mind. "
        "The stunning details set it apart from the competition. "
    )
    # ~50 words per block × 13 = ~650 words
    return (
        '<html><body>'
        '<div class="product__description rte">'
        f'<p>{sentences * 13}</p>'
        '</div></body></html>'
    )


def _feature_heavy_html() -> str:
    """Feature-dominant language (low benefit ratio)."""
    return (
        '<html><body>'
        '<div class="product__description rte">'
        '<p>This product is made from premium materials. It includes a zipper closure. '
        'The specifications are impressive. Dimensions are 10 x 5 x 3 inches. '
        'Weight is 2 pounds. Material is constructed from recycled polyester. '
        'It is built with reinforced stitching. The technical features include '
        'water resistance. It is rated for outdoor use. Compatible with all sizes. '
        'Certified by international standards. Manufactured in our facility.</p>'
        '</div></body></html>'
    )


def _benefit_heavy_html() -> str:
    """Benefit-dominant language (high benefit ratio)."""
    return (
        '<html><body>'
        '<div class="product__description rte">'
        '<p>You will love how this feels. Your confidence will soar. '
        'Experience the freedom of effortless style. Enjoy the comfort '
        'that transforms your daily routine. Discover your perfect look. '
        'Feel amazing every single day. Imagine the compliments you will receive. '
        'Achieve the style you have always wanted. Delight in the smooth texture.</p>'
        '</div></body></html>'
    )


def _complex_language_html() -> str:
    """High FK grade — complex, verbose sentences."""
    return (
        '<html><body>'
        '<div class="product__description rte">'
        '<p>The extraordinarily sophisticated manufacturing methodology employed '
        'in the fabrication of this particular merchandise ensures an unparalleled '
        'level of exceptional craftsmanship and meticulous attention to the most '
        'intricate specifications and dimensions that characterize the overall '
        'construction methodology throughout the comprehensive production lifecycle.</p>'
        '</div></body></html>'
    )


def _simple_language_html() -> str:
    """Low FK grade — short, simple sentences."""
    return (
        '<html><body>'
        '<div class="product__description rte">'
        '<p>A soft tee. You will love it. It feels great. '
        'Made for you. Enjoy the fit. It is smooth. '
        'Your new go-to shirt. Feel the comfort.</p>'
        '</div></body></html>'
    )


def _json_ld_description_html() -> str:
    """Description only in JSON-LD Product schema."""
    return (
        '<html><head>'
        '<script type="application/ld+json">'
        '{"@type": "Product", "name": "Tee", '
        '"description": "Experience the ultimate comfort with our premium cotton tee. '
        'You will enjoy effortless style that transforms your wardrobe every day."}'
        '</script>'
        '</head><body><h1>Product</h1></body></html>'
    )


def _meta_description_html() -> str:
    """Description only in meta tag."""
    return (
        '<html><head>'
        '<meta name="description" content="Experience the ultimate comfort with our '
        'premium organic cotton tee. You will enjoy wearing this beautiful shirt every day.">'
        '</head><body><h1>Product</h1></body></html>'
    )


def _older_theme_html() -> str:
    """Older Shopify theme with product-description class."""
    return (
        '<html><body>'
        '<div class="product-description">'
        '<p>You will love this amazing product. It feels incredibly comfortable. '
        'Experience the premium quality every day.</p>'
        '</div></body></html>'
    )


def _rich_format_html() -> str:
    """Description with extensive HTML formatting."""
    return (
        '<html><body>'
        '<div class="product__description rte">'
        '<h2>Overview</h2>'
        '<p>Experience the <strong>ultimate</strong> comfort with our '
        '<em>premium</em> organic cotton tee.</p>'
        '<h3>Features</h3>'
        '<ul><li>100% organic cotton</li><li>Pre-shrunk fabric</li></ul>'
        '<ol><li>Step one: enjoy</li><li>Step two: love it</li></ol>'
        '<table><tr><td>Material</td><td>Cotton</td></tr></table>'
        '<blockquote>Best shirt ever</blockquote>'
        '<p>Your new favorite piece. You deserve the best.</p>'
        '<img src="detail.jpg" alt="detail" />'
        '</div></body></html>'
    )


def _optimal_description_html() -> str:
    """~200 words, good structure, balanced language, rich formatting."""
    return (
        '<html><body>'
        '<div class="product__description rte">'
        '<h2>Why You Will Love This</h2>'
        '<p>Experience the ultimate comfort with our premium organic cotton tee. '
        'Your skin will feel amazing every single day. Enjoy effortless style that '
        'transforms your entire wardrobe. Discover the perfect blend of luxury and '
        'incredible durability that you deserve.</p>'
        '<h3>Key Benefits</h3>'
        '<ul>'
        '<li>Breathable organic cotton keeps you comfortable all day</li>'
        '<li>Pre-shrunk fabric maintains your perfect fit wash after wash</li>'
        '<li>Reinforced stitching for exceptional long-lasting durability</li>'
        '<li>Available in twelve stunning colors to match your style</li>'
        '</ul>'
        '<p>This <strong>beautiful</strong> piece is <em>designed</em> for '
        'everyday wear. Made from the finest materials sourced from certified '
        'organic farms. It includes a reinforced neckline and double-stitched hems '
        'for guaranteed quality and lasting comfort.</p>'
        '<h3>Specifications</h3>'
        '<table>'
        '<tr><td>Material</td><td>100% Organic Cotton</td></tr>'
        '<tr><td>Weight</td><td>5.3 oz</td></tr>'
        '<tr><td>Care</td><td>Machine washable</td></tr>'
        '</table>'
        '<p>Trusted by thousands of happy customers. This is your new essential.</p>'
        '</div></body></html>'
    )


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestDescriptionExtraction:
    """Tests for cascading fallback extraction."""

    def test_dawn_theme_extraction(self):
        signals = detect_description(_dawn_description_html())
        assert signals.description_found is True
        assert signals.word_count > 30

    def test_older_theme_extraction(self):
        signals = detect_description(_older_theme_html())
        assert signals.description_found is True
        assert signals.word_count > 10

    def test_json_ld_fallback(self):
        signals = detect_description(_json_ld_description_html())
        assert signals.description_found is True
        assert signals.word_count > 10
        # Text-only extraction: no formatting signals
        assert signals.html_tag_variety == 0
        assert signals.has_headings is False

    def test_meta_fallback(self):
        signals = detect_description(_meta_description_html())
        assert signals.description_found is True
        assert signals.word_count > 10
        assert signals.html_tag_variety == 0

    def test_empty_html(self):
        signals = detect_description(_empty_html())
        assert signals.description_found is False
        assert signals.word_count == 0

    def test_empty_string(self):
        signals = detect_description("")
        assert signals.description_found is False

    def test_data_attribute_extraction(self):
        html = (
            '<html><body>'
            '<div data-product-description>'
            '<p>You will enjoy this comfortable premium cotton shirt.</p>'
            '</div></body></html>'
        )
        signals = detect_description(html)
        assert signals.description_found is True

    def test_class_contains_fallback(self):
        html = (
            '<html><body>'
            '<div class="custom-product-description-area">'
            '<p>You will enjoy this comfortable premium cotton shirt every day.</p>'
            '</div></body></html>'
        )
        signals = detect_description(html)
        assert signals.description_found is True


class TestReadabilityMetrics:
    """Tests for Flesch-Kincaid grade, sentence length, syllable counting."""

    def test_syllable_short_word(self):
        assert _count_syllables("it") == 1
        assert _count_syllables("a") == 1

    def test_syllable_multisyllable(self):
        assert _count_syllables("beautiful") >= 3
        assert _count_syllables("comfortable") >= 3

    def test_syllable_silent_e(self):
        # "made" should be 1 syllable (silent e removed)
        assert _count_syllables("made") == 1

    def test_sentence_splitting(self):
        text = "This is great. You will love it! Buy now?"
        sentences = _split_sentences(text)
        assert len(sentences) == 3

    def test_sentence_splitting_newlines(self):
        text = "First point\nSecond point\nThird point here"
        sentences = _split_sentences(text)
        assert len(sentences) >= 2

    def test_fk_grade_simple_text(self):
        signals = detect_description(_simple_language_html())
        assert signals.flesch_kincaid_grade < 6.0

    def test_fk_grade_complex_text(self):
        signals = detect_description(_complex_language_html())
        assert signals.flesch_kincaid_grade > 10.0

    def test_avg_sentence_length(self):
        signals = detect_description(_dawn_description_html())
        assert signals.avg_sentence_length > 0
        assert signals.sentence_count > 0

    def test_sentence_count_plain_text(self):
        signals = detect_description(_plain_text_description_html())
        assert signals.sentence_count >= 3


class TestPersuasionLanguage:
    """Tests for benefit/feature ratio and emotional density."""

    def test_feature_heavy_low_ratio(self):
        signals = detect_description(_feature_heavy_html())
        assert signals.benefit_ratio < 0.3
        assert signals.feature_word_count > signals.benefit_word_count

    def test_benefit_heavy_high_ratio(self):
        signals = detect_description(_benefit_heavy_html())
        assert signals.benefit_ratio > 0.6
        assert signals.benefit_word_count > signals.feature_word_count

    def test_balanced_language(self):
        signals = detect_description(_dawn_description_html())
        assert signals.benefit_word_count > 0
        assert signals.feature_word_count > 0

    def test_emotional_density_range(self):
        signals = detect_description(_dawn_description_html())
        assert 0.0 <= signals.emotional_density <= 1.0

    def test_no_description_zero_counts(self):
        signals = detect_description(_empty_html())
        assert signals.benefit_word_count == 0
        assert signals.feature_word_count == 0
        assert signals.emotional_density == 0.0


class TestHtmlFormatting:
    """Tests for tag variety, headings, bullets, emphasis detection."""

    def test_rich_format_variety(self):
        signals = detect_description(_rich_format_html())
        assert signals.html_tag_variety >= 7
        assert signals.has_headings is True
        assert signals.has_bullet_lists is True
        assert signals.has_emphasis is True

    def test_plain_text_no_formatting(self):
        signals = detect_description(_plain_text_description_html())
        assert signals.html_tag_variety == 0
        assert signals.has_headings is False
        assert signals.has_bullet_lists is False
        assert signals.has_emphasis is False

    def test_dawn_description_has_structure(self):
        signals = detect_description(_dawn_description_html())
        assert signals.has_headings is True
        assert signals.has_bullet_lists is True
        assert signals.has_emphasis is True
        assert signals.html_tag_variety >= 4

    def test_json_ld_no_formatting(self):
        signals = detect_description(_json_ld_description_html())
        assert signals.html_tag_variety == 0
        assert signals.has_headings is False

    def test_headings_detection(self):
        html = (
            '<html><body><div class="product__description rte">'
            '<h2>Title</h2><p>Some text here for the description.</p>'
            '</div></body></html>'
        )
        signals = detect_description(html)
        assert signals.has_headings is True


class TestScoring:
    """Tests for deterministic scoring with known inputs."""

    def test_no_description_scores_zero(self):
        signals = DescriptionSignals(description_found=False)
        assert score_description(signals) == 0

    def test_optimal_scores_high(self):
        signals = detect_description(_optimal_description_html())
        score = score_description(signals)
        assert score >= 60

    def test_plain_text_scores_lower(self):
        signals = detect_description(_plain_text_description_html())
        score = score_description(signals)
        # No formatting tags = lower score
        assert score < 60

    def test_short_description_low_score(self):
        signals = detect_description(_short_description_html())
        score = score_description(signals)
        assert score < 40

    def test_score_clamped_0_100(self):
        signals = detect_description(_dawn_description_html())
        score = score_description(signals)
        assert 0 <= score <= 100

    def test_word_count_scoring_optimal(self):
        """200 words in optimal range should get full 20 pts for word count."""
        signals = DescriptionSignals(
            description_found=True,
            word_count=200,
            flesch_kincaid_grade=7.0,
            avg_sentence_length=15.0,
            sentence_count=13,
            benefit_ratio=0.5,
            benefit_word_count=10,
            feature_word_count=10,
            emotional_density=0.05,
            html_tag_variety=5,
            has_headings=True,
            has_bullet_lists=True,
            has_emphasis=True,
        )
        score = score_description(signals)
        # All criteria optimal: 20+15+10+20+10+12+5+5 = 97
        assert score >= 90

    def test_word_count_scoring_partial(self):
        """75 words should get partial credit."""
        signals = DescriptionSignals(
            description_found=True,
            word_count=75,
        )
        score = score_description(signals)
        assert score >= 10  # At least partial word count credit

    def test_long_description_scoring(self):
        signals = detect_description(_long_description_html())
        score = score_description(signals)
        # Still gets points for other criteria even though word count is over 600
        assert score > 0


class TestTipSelection:
    """Tests for tip count, priority, and research citations."""

    def test_max_three_tips(self):
        signals = detect_description(_plain_text_description_html())
        tips = get_description_tips(signals)
        assert len(tips) <= 3

    def test_no_description_first_tip(self):
        signals = detect_description(_empty_html())
        tips = get_description_tips(signals)
        assert len(tips) >= 1
        assert "87%" in tips[0] or "description" in tips[0].lower()

    def test_short_description_thin_tip(self):
        signals = detect_description(_short_description_html())
        tips = get_description_tips(signals)
        assert len(tips) >= 1
        assert any("thin" in t.lower() or "words" in t.lower() for t in tips)

    def test_feature_heavy_benefit_tip(self):
        signals = detect_description(_feature_heavy_html())
        tips = get_description_tips(signals)
        assert any("benefit" in t.lower() for t in tips)

    def test_complex_language_simplify_tip(self):
        """FK grade > 10 tip fires when higher-priority tips are absent."""
        signals = DescriptionSignals(
            description_found=True,
            word_count=200,
            flesch_kincaid_grade=12.5,
            avg_sentence_length=25.0,
            sentence_count=8,
            benefit_ratio=0.5,
            benefit_word_count=8,
            feature_word_count=8,
            emotional_density=0.05,
            html_tag_variety=5,
            has_headings=True,
            has_bullet_lists=True,
            has_emphasis=True,
        )
        tips = get_description_tips(signals)
        assert any("simplify" in t.lower() or "grade" in t.lower() for t in tips)

    def test_plain_text_formatting_tip(self):
        signals = detect_description(_plain_text_description_html())
        tips = get_description_tips(signals)
        assert any("bullet" in t.lower() or "heading" in t.lower() or "format" in t.lower() for t in tips)

    def test_congratulatory_tip_high_score(self):
        signals = DescriptionSignals(
            description_found=True,
            word_count=200,
            flesch_kincaid_grade=7.0,
            avg_sentence_length=15.0,
            sentence_count=13,
            benefit_ratio=0.5,
            benefit_word_count=10,
            feature_word_count=10,
            emotional_density=0.05,
            html_tag_variety=7,
            has_headings=True,
            has_bullet_lists=True,
            has_emphasis=True,
        )
        tips = get_description_tips(signals)
        assert any("excellent" in t.lower() for t in tips)

    def test_tips_have_citations(self):
        """Tips for actionable issues should include research citations."""
        signals = detect_description(_empty_html())
        tips = get_description_tips(signals)
        # The no-description tip should cite research
        assert any(
            "salsify" in t.lower() or "baymard" in t.lower() or "nngroup" in t.lower()
            or "87%" in t
            for t in tips
        )


class TestDataclassStructure:
    """Tests for DescriptionSignals dataclass integrity."""

    def test_is_dataclass(self):
        assert is_dataclass(DescriptionSignals)

    def test_field_count(self):
        assert len(fields(DescriptionSignals)) == 13

    def test_default_values(self):
        signals = DescriptionSignals()
        assert signals.description_found is False
        assert signals.word_count == 0
        assert signals.flesch_kincaid_grade == 0.0
        assert signals.avg_sentence_length == 0.0
        assert signals.sentence_count == 0
        assert signals.benefit_ratio == 0.0
        assert signals.benefit_word_count == 0
        assert signals.feature_word_count == 0
        assert signals.emotional_density == 0.0
        assert signals.html_tag_variety == 0
        assert signals.has_headings is False
        assert signals.has_bullet_lists is False
        assert signals.has_emphasis is False

    def test_instantiation_with_values(self):
        signals = DescriptionSignals(
            description_found=True,
            word_count=150,
            flesch_kincaid_grade=7.2,
        )
        assert signals.description_found is True
        assert signals.word_count == 150
        assert signals.flesch_kincaid_grade == 7.2


class TestEndToEnd:
    """Full pipeline: HTML → detect → score → tips."""

    def test_full_pipeline_optimal(self):
        html = _optimal_description_html()
        signals = detect_description(html)
        score = score_description(signals)
        tips = get_description_tips(signals)

        assert signals.description_found is True
        assert signals.word_count >= 100
        assert signals.has_headings is True
        assert signals.has_bullet_lists is True
        assert 0 <= score <= 100
        assert len(tips) <= 3

    def test_full_pipeline_empty(self):
        html = _empty_html()
        signals = detect_description(html)
        score = score_description(signals)
        tips = get_description_tips(signals)

        assert signals.description_found is False
        assert score == 0
        assert len(tips) >= 1

    def test_full_pipeline_dawn(self):
        html = _dawn_description_html()
        signals = detect_description(html)
        score = score_description(signals)
        tips = get_description_tips(signals)

        assert signals.description_found is True
        assert score > 0
        assert isinstance(tips, list)

    def test_full_pipeline_feature_heavy(self):
        html = _feature_heavy_html()
        signals = detect_description(html)
        score = score_description(signals)
        tips = get_description_tips(signals)

        assert signals.description_found is True
        assert signals.benefit_ratio < 0.4
        assert any("benefit" in t.lower() for t in tips)

    def test_full_pipeline_json_ld(self):
        html = _json_ld_description_html()
        signals = detect_description(html)
        score = score_description(signals)
        tips = get_description_tips(signals)

        assert signals.description_found is True
        assert score > 0
        # Text-only: no formatting
        assert signals.html_tag_variety == 0
