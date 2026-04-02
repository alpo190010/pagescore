"""Unit tests for social_proof_detector and social_proof_rubric."""

import pytest

from app.services.social_proof_detector import (
    SocialProofSignals,
    detect_social_proof,
)
from app.services.social_proof_rubric import (
    get_social_proof_tips,
    score_social_proof,
)


# ---------------------------------------------------------------------------
# HTML fixture helpers — minimal but realistic per vendor
# ---------------------------------------------------------------------------


def _judgeme_html() -> str:
    """Judge.me widget with star rating, review count, and photo container."""
    return """
    <html><body>
        <div class="jdgm-prev-badge" data-score="4.5">
            <span class="jdgm-prev-badge__stars" aria-label="4.5 out of 5 stars"></span>
            <span>42 reviews</span>
        </div>
        <div id="judgeme_product_reviews">
            <div class="jdgm-widget" data-number-of-reviews="42">
                <div class="jdgm-rev">
                    <div class="jdgm-rev__photos">
                        <img src="photo1.jpg" />
                    </div>
                    <p>Great product!</p>
                </div>
                <div class="jdgm-sort">
                    <select><option>Most Recent</option></select>
                </div>
            </div>
        </div>
    </body></html>
    """


def _yotpo_html() -> str:
    """Yotpo legacy widget with script src."""
    return """
    <html><head>
        <script src="https://staticw2.yotpo.com/widget.js"></script>
    </head><body>
        <div class="yotpo yotpo-main-widget" data-score="4.2">
            <div class="yotpo-bottomline">
                <span>128 reviews</span>
            </div>
            <div class="yotpo-review-images">
                <img src="review-img.jpg" />
            </div>
            <div class="yotpo-reviews-filters">
                <select><option>Sort by</option></select>
            </div>
        </div>
    </body></html>
    """


def _yotpo_v3_html() -> str:
    """Yotpo v3 widget with data attribute and CDN script."""
    return """
    <html><head>
        <script src="https://cdn-widgetsrepository.yotpo.com/v1/loader.js"></script>
    </head><body>
        <div class="yotpo-widget-instance" data-yotpo-instance-id="abc123" data-rating="4.8">
            <span data-review-count="95">95 reviews</span>
        </div>
    </body></html>
    """


def _loox_html() -> str:
    """Loox widget with aggregate rating and images."""
    return """
    <html><body>
        <div class="loox-rating" data-loox-aggregate="4.7">
            <img src="review-photo.jpg" />
        </div>
        <div class="loox-reviews-default">
            <div data-number-of-reviews="63">
                <p>63 reviews</p>
            </div>
        </div>
    </body></html>
    """


def _stamped_html() -> str:
    """Stamped.io widget with summary and data-score."""
    return """
    <html><head>
        <script src="https://cdn.stamped.io/files/widget.js"></script>
    </head><body>
        <div class="stamped-summary" data-score="4.3">
            <span data-number-of-reviews="77">77 reviews</span>
        </div>
        <div class="stamped-reviews-widget">
            <div class="stamped-reviews-filter">
                <select><option>Filter</option></select>
            </div>
        </div>
    </body></html>
    """


def _okendo_html() -> str:
    """Okendo widget with data-oke-widget attribute."""
    return """
    <html><body>
        <div data-oke-widget="reviews" data-score="4.6">
            <span data-number-of-reviews="31">31 reviews</span>
        </div>
    </body></html>
    """


def _spr_html() -> str:
    """Shopify Product Reviews (SPR) with badge and starrating."""
    return """
    <html><body>
        <span class="spr-badge" data-rating="3.8">
            <span class="spr-starrating">
                <span class="spr-starratings-top" style="width: 76%"></span>
            </span>
            <span class="spr-badge-caption">19 reviews</span>
        </span>
        <div id="shopify-product-reviews">
            <div class="spr-container">
                <div class="spr-review">
                    <p>Nice item</p>
                </div>
            </div>
        </div>
    </body></html>
    """


def _fera_html() -> str:
    """Fera.ai widget with data attribute and script src."""
    return """
    <html><head>
        <script src="https://cdn.fera.ai/widget.js"></script>
    </head><body>
        <div data-fera-widget="product_reviews" data-score="4.1">
            <span data-number-of-reviews="12">12 reviews</span>
            <img src="user-photo.jpg" />
        </div>
    </body></html>
    """


def _no_reviews_html() -> str:
    """Plain product page with no review widgets at all."""
    return """
    <html><body>
        <h1>Awesome Widget</h1>
        <p>$29.99</p>
        <button>Add to Cart</button>
    </body></html>
    """


# ---------------------------------------------------------------------------
# Vendor detection tests
# ---------------------------------------------------------------------------


class TestVendorDetection:
    """Each vendor fixture produces the correct review_app string."""

    def test_judgeme_detected(self):
        signals = detect_social_proof(_judgeme_html())
        assert signals.review_app == "judge.me"

    def test_yotpo_detected(self):
        signals = detect_social_proof(_yotpo_html())
        assert signals.review_app == "yotpo"

    def test_yotpo_v3_detected(self):
        signals = detect_social_proof(_yotpo_v3_html())
        assert signals.review_app == "yotpo-v3"

    def test_loox_detected(self):
        signals = detect_social_proof(_loox_html())
        assert signals.review_app == "loox"

    def test_stamped_detected(self):
        signals = detect_social_proof(_stamped_html())
        assert signals.review_app == "stamped.io"

    def test_okendo_detected(self):
        signals = detect_social_proof(_okendo_html())
        assert signals.review_app == "okendo"

    def test_spr_detected(self):
        signals = detect_social_proof(_spr_html())
        assert signals.review_app == "shopify-spr"

    def test_fera_detected(self):
        signals = detect_social_proof(_fera_html())
        assert signals.review_app == "fera.ai"

    def test_no_reviews_no_vendor(self):
        signals = detect_social_proof(_no_reviews_html())
        assert signals.review_app is None


# ---------------------------------------------------------------------------
# Signal extraction tests
# ---------------------------------------------------------------------------


class TestStarRatingExtraction:
    """Star rating parsed from data attributes."""

    def test_data_score_attribute(self):
        signals = detect_social_proof(_judgeme_html())
        assert signals.star_rating == 4.5

    def test_data_score_yotpo(self):
        signals = detect_social_proof(_yotpo_html())
        assert signals.star_rating == 4.2

    def test_data_loox_aggregate(self):
        signals = detect_social_proof(_loox_html())
        assert signals.star_rating == 4.7

    def test_spr_starrating_percentage(self):
        signals = detect_social_proof(_spr_html())
        # SPR uses data-rating="3.8" which is found first
        assert signals.star_rating == 3.8

    def test_no_reviews_no_rating(self):
        signals = detect_social_proof(_no_reviews_html())
        assert signals.star_rating is None


class TestReviewCountExtraction:
    """Review count parsed from data-number-of-reviews or text."""

    def test_data_number_of_reviews(self):
        signals = detect_social_proof(_judgeme_html())
        assert signals.review_count == 42

    def test_loox_review_count(self):
        signals = detect_social_proof(_loox_html())
        assert signals.review_count == 63

    def test_spr_badge_caption(self):
        signals = detect_social_proof(_spr_html())
        assert signals.review_count == 19

    def test_no_reviews_no_count(self):
        signals = detect_social_proof(_no_reviews_html())
        assert signals.review_count is None

    def test_okendo_review_count(self):
        signals = detect_social_proof(_okendo_html())
        assert signals.review_count == 31


# ---------------------------------------------------------------------------
# Photo and video review detection
# ---------------------------------------------------------------------------


class TestPhotoReviews:
    """Photo review containers detected per vendor."""

    def test_judgeme_photo_container(self):
        signals = detect_social_proof(_judgeme_html())
        assert signals.has_photo_reviews is True

    def test_yotpo_photo_images(self):
        signals = detect_social_proof(_yotpo_html())
        assert signals.has_photo_reviews is True

    def test_loox_photo_images(self):
        signals = detect_social_proof(_loox_html())
        assert signals.has_photo_reviews is True

    def test_fera_photo_images(self):
        signals = detect_social_proof(_fera_html())
        assert signals.has_photo_reviews is True

    def test_no_reviews_no_photos(self):
        signals = detect_social_proof(_no_reviews_html())
        assert signals.has_photo_reviews is False


class TestVideoReviews:
    """Video elements inside review widgets."""

    def test_no_videos_by_default(self):
        signals = detect_social_proof(_judgeme_html())
        assert signals.has_video_reviews is False

    def test_video_inside_widget(self):
        html = """
        <html><body>
            <div class="jdgm-widget">
                <video src="review-video.mp4"></video>
            </div>
        </body></html>
        """
        signals = detect_social_proof(html)
        assert signals.has_video_reviews is True


# ---------------------------------------------------------------------------
# Above-fold and filtering detection
# ---------------------------------------------------------------------------


class TestAboveFold:
    """Badge before main widget = above-fold star rating."""

    def test_judgeme_badge_before_widget(self):
        signals = detect_social_proof(_judgeme_html())
        assert signals.star_rating_above_fold is True

    def test_spr_badge_before_container(self):
        signals = detect_social_proof(_spr_html())
        assert signals.star_rating_above_fold is True

    def test_no_reviews_not_above_fold(self):
        signals = detect_social_proof(_no_reviews_html())
        assert signals.star_rating_above_fold is False


class TestReviewFiltering:
    """Filter/sort UI detection."""

    def test_judgeme_sort_present(self):
        signals = detect_social_proof(_judgeme_html())
        assert signals.has_review_filtering is True

    def test_yotpo_filters_present(self):
        signals = detect_social_proof(_yotpo_html())
        assert signals.has_review_filtering is True

    def test_no_reviews_no_filtering(self):
        signals = detect_social_proof(_no_reviews_html())
        assert signals.has_review_filtering is False


# ---------------------------------------------------------------------------
# Negative / boundary tests
# ---------------------------------------------------------------------------


class TestMalformedInputs:
    """Empty, missing body, and data-less HTML don't crash."""

    def test_empty_string(self):
        signals = detect_social_proof("")
        assert signals.review_app is None
        assert signals.star_rating is None
        assert signals.review_count is None
        assert signals.has_photo_reviews is False
        assert signals.has_video_reviews is False
        assert signals.star_rating_above_fold is False
        assert signals.has_review_filtering is False

    def test_no_body_tag(self):
        signals = detect_social_proof("<p>Hello</p>")
        assert signals.review_app is None
        assert signals.star_rating is None

    def test_review_class_no_data(self):
        """Vendor detected but no extractable star/count data."""
        html = '<html><body><div class="jdgm-widget"></div></body></html>'
        signals = detect_social_proof(html)
        assert signals.review_app == "judge.me"
        assert signals.star_rating is None
        assert signals.review_count is None

    def test_review_count_text_no_digits(self):
        """Review text without digits yields no count."""
        html = """
        <html><body>
            <div class="jdgm-widget" data-number-of-reviews="abc">
                <span>No reviews yet</span>
            </div>
        </body></html>
        """
        signals = detect_social_proof(html)
        assert signals.review_app == "judge.me"
        assert signals.review_count is None

    def test_multiple_vendors_first_wins(self):
        """When multiple vendor selectors match, first in fingerprint list wins."""
        html = """
        <html><body>
            <div class="jdgm-widget" data-score="4.0"></div>
            <div class="yotpo" data-score="3.5"></div>
        </body></html>
        """
        signals = detect_social_proof(html)
        assert signals.review_app == "judge.me"
        # Star rating from first data-score in DOM
        assert signals.star_rating == 4.0

    def test_star_rating_out_of_range(self):
        """Star rating > 5.0 is rejected."""
        html = """
        <html><body>
            <div class="jdgm-widget" data-score="7.5"></div>
        </body></html>
        """
        signals = detect_social_proof(html)
        assert signals.review_app == "judge.me"
        assert signals.star_rating is None


# ---------------------------------------------------------------------------
# Dataclass structure test
# ---------------------------------------------------------------------------


class TestDataclassStructure:
    """SocialProofSignals has exactly 7 fields with correct defaults."""

    def test_field_count(self):
        import dataclasses

        fields = dataclasses.fields(SocialProofSignals)
        assert len(fields) == 7

    def test_default_values(self):
        signals = SocialProofSignals()
        assert signals.review_app is None
        assert signals.star_rating is None
        assert signals.review_count is None
        assert signals.has_photo_reviews is False
        assert signals.has_video_reviews is False
        assert signals.star_rating_above_fold is False
        assert signals.has_review_filtering is False

    def test_field_names(self):
        import dataclasses

        names = {f.name for f in dataclasses.fields(SocialProofSignals)}
        expected = {
            "review_app",
            "star_rating",
            "review_count",
            "has_photo_reviews",
            "has_video_reviews",
            "star_rating_above_fold",
            "has_review_filtering",
        }
        assert names == expected


# ===========================================================================
# Scoring rubric tests
# ===========================================================================


class TestScoreSocialProof:
    """score_social_proof returns 0–100 based on weighted criteria."""

    def test_all_signals_maxed_out_returns_100(self):
        signals = SocialProofSignals(
            review_app="judge.me",
            star_rating=4.5,
            review_count=150,
            has_photo_reviews=True,
            has_video_reviews=True,
            star_rating_above_fold=True,
            has_review_filtering=True,
        )
        assert score_social_proof(signals) == 100

    def test_no_review_app_all_empty_returns_0(self):
        signals = SocialProofSignals()
        assert score_social_proof(signals) == 0

    def test_review_app_only_returns_25(self):
        signals = SocialProofSignals(review_app="yotpo")
        assert score_social_proof(signals) == 25

    def test_review_app_plus_star_rating(self):
        signals = SocialProofSignals(review_app="loox", star_rating=3.9)
        # 25 (app) + 15 (rating displayed) = 40
        assert score_social_proof(signals) == 40

    def test_review_app_5_reviews_star_rating(self):
        signals = SocialProofSignals(
            review_app="stamped.io",
            star_rating=4.3,
            review_count=5,
        )
        # 25 (app) + 15 (rating) + 15 (count>=5) + 10 (optimal range) = 65
        assert score_social_proof(signals) == 65

    def test_review_count_30_bonus(self):
        signals = SocialProofSignals(
            review_app="judge.me",
            review_count=30,
        )
        # 25 (app) + 15 (count>=5) + 5 (count>=30) = 45
        assert score_social_proof(signals) == 45

    def test_review_count_100_bonus(self):
        signals = SocialProofSignals(
            review_app="judge.me",
            review_count=100,
        )
        # 25 (app) + 15 (count>=5) + 5 (count>=30) + 5 (count>=100) = 50
        assert score_social_proof(signals) == 50

    def test_photo_reviews_add_15(self):
        signals = SocialProofSignals(
            review_app="yotpo",
            has_photo_reviews=True,
        )
        # 25 + 15 = 40
        assert score_social_proof(signals) == 40

    def test_video_reviews_add_15(self):
        signals = SocialProofSignals(
            review_app="yotpo",
            has_video_reviews=True,
        )
        # 25 + 15 = 40
        assert score_social_proof(signals) == 40

    def test_photo_and_video_still_15(self):
        """Photo OR video is 15 pts — having both doesn't double."""
        signals = SocialProofSignals(
            review_app="yotpo",
            has_photo_reviews=True,
            has_video_reviews=True,
        )
        # 25 + 15 = 40
        assert score_social_proof(signals) == 40

    def test_optimal_star_range_adds_10(self):
        signals = SocialProofSignals(
            review_app="okendo",
            star_rating=4.5,
        )
        # 25 (app) + 15 (rating) + 10 (optimal range) = 50
        assert score_social_proof(signals) == 50

    def test_star_outside_optimal_range_no_bonus(self):
        signals = SocialProofSignals(
            review_app="okendo",
            star_rating=3.9,
        )
        # 25 (app) + 15 (rating) = 40  (no optimal bonus)
        assert score_social_proof(signals) == 40

    def test_star_4_2_boundary_included(self):
        signals = SocialProofSignals(
            review_app="okendo",
            star_rating=4.2,
        )
        # 25 + 15 + 10 = 50
        assert score_social_proof(signals) == 50

    def test_star_4_7_boundary_included(self):
        signals = SocialProofSignals(
            review_app="okendo",
            star_rating=4.7,
        )
        # 25 + 15 + 10 = 50
        assert score_social_proof(signals) == 50

    def test_above_fold_adds_5(self):
        signals = SocialProofSignals(
            review_app="judge.me",
            star_rating_above_fold=True,
        )
        # 25 + 5 = 30
        assert score_social_proof(signals) == 30

    def test_filtering_adds_5(self):
        signals = SocialProofSignals(
            review_app="judge.me",
            has_review_filtering=True,
        )
        # 25 + 5 = 30
        assert score_social_proof(signals) == 30

    def test_near_perfect_setup(self):
        """150 reviews, photos, rating 4.5, above fold, filtering."""
        signals = SocialProofSignals(
            review_app="judge.me",
            star_rating=4.5,
            review_count=150,
            has_photo_reviews=True,
            has_video_reviews=False,
            star_rating_above_fold=True,
            has_review_filtering=True,
        )
        # 25 + 15 + 15 + 5 + 5 + 15 + 10 + 5 + 5 = 100
        assert score_social_proof(signals) == 100

    def test_review_count_4_not_enough(self):
        """4 reviews don't reach the >=5 tier."""
        signals = SocialProofSignals(
            review_app="loox",
            review_count=4,
        )
        # 25 only
        assert score_social_proof(signals) == 25

    def test_review_count_0_treated_as_real(self):
        """review_count=0 is not None — but below 5, so no count points."""
        signals = SocialProofSignals(
            review_app="loox",
            review_count=0,
        )
        assert score_social_proof(signals) == 25

    def test_star_rating_0_treated_as_real(self):
        """star_rating=0.0 is a valid rating (not None)."""
        signals = SocialProofSignals(
            review_app="loox",
            star_rating=0.0,
        )
        # 25 (app) + 15 (rating displayed) = 40
        assert score_social_proof(signals) == 40

    def test_score_clamped_to_100(self):
        """Even if internal arithmetic could exceed 100, result is clamped."""
        signals = SocialProofSignals(
            review_app="judge.me",
            star_rating=4.5,
            review_count=200,
            has_photo_reviews=True,
            has_video_reviews=True,
            star_rating_above_fold=True,
            has_review_filtering=True,
        )
        assert score_social_proof(signals) <= 100

    def test_score_never_negative(self):
        signals = SocialProofSignals()
        assert score_social_proof(signals) >= 0

    def test_score_is_int(self):
        signals = SocialProofSignals(review_app="yotpo", star_rating=4.3)
        result = score_social_proof(signals)
        assert isinstance(result, int)


# ===========================================================================
# Tip selector tests
# ===========================================================================


class TestGetSocialProofTips:
    """get_social_proof_tips returns max 3 prioritised, research-backed tips."""

    def test_no_review_app_first_tip_is_install(self):
        signals = SocialProofSignals()
        tips = get_social_proof_tips(signals)
        assert len(tips) >= 1
        assert "Install a review app" in tips[0]
        assert "270%" in tips[0]

    def test_has_app_but_few_reviews(self):
        signals = SocialProofSignals(review_app="yotpo", review_count=2)
        tips = get_social_proof_tips(signals)
        assert any("Collect more reviews" in t for t in tips)
        assert any("270%" in t for t in tips)

    def test_has_app_but_review_count_none(self):
        signals = SocialProofSignals(review_app="yotpo", review_count=None)
        tips = get_social_proof_tips(signals)
        assert any("Collect more reviews" in t for t in tips)

    def test_no_photo_reviews_tip(self):
        signals = SocialProofSignals(
            review_app="yotpo",
            review_count=10,
            has_photo_reviews=False,
        )
        tips = get_social_proof_tips(signals)
        assert any("photo reviews" in t.lower() for t in tips)
        assert any("106%" in t for t in tips)

    def test_perfect_5_0_rating_tip(self):
        signals = SocialProofSignals(
            review_app="judge.me",
            star_rating=5.0,
            review_count=50,
            has_photo_reviews=True,
        )
        tips = get_social_proof_tips(signals)
        assert any("5.0 rating" in t for t in tips)
        assert any("4.2" in t for t in tips)

    def test_star_not_above_fold_tip(self):
        signals = SocialProofSignals(
            review_app="yotpo",
            review_count=50,
            has_photo_reviews=True,
            star_rating_above_fold=False,
        )
        tips = get_social_proof_tips(signals)
        assert any("above the fold" in t for t in tips)

    def test_no_filtering_tip(self):
        signals = SocialProofSignals(
            review_app="yotpo",
            review_count=50,
            has_photo_reviews=True,
            star_rating_above_fold=True,
            has_review_filtering=False,
        )
        tips = get_social_proof_tips(signals)
        assert any("filtering" in t.lower() for t in tips)

    def test_review_count_5_to_29_tip(self):
        signals = SocialProofSignals(
            review_app="judge.me",
            review_count=15,
            has_photo_reviews=True,
            star_rating_above_fold=True,
            has_review_filtering=True,
        )
        tips = get_social_proof_tips(signals)
        assert any("past 30" in t for t in tips)

    def test_high_score_encouraging_tip(self):
        signals = SocialProofSignals(
            review_app="judge.me",
            star_rating=4.5,
            review_count=150,
            has_photo_reviews=True,
            has_video_reviews=True,
            star_rating_above_fold=True,
            has_review_filtering=True,
        )
        tips = get_social_proof_tips(signals)
        assert any("Q&A" in t for t in tips)

    def test_max_3_tips(self):
        signals = SocialProofSignals()
        tips = get_social_proof_tips(signals)
        assert len(tips) <= 3

    def test_returns_list_of_strings(self):
        signals = SocialProofSignals(review_app="loox")
        tips = get_social_proof_tips(signals)
        assert isinstance(tips, list)
        for t in tips:
            assert isinstance(t, str)

    def test_no_tips_for_fully_optimised(self):
        """When score is 100, only the encouraging Q&A tip fires."""
        signals = SocialProofSignals(
            review_app="judge.me",
            star_rating=4.5,
            review_count=150,
            has_photo_reviews=True,
            has_video_reviews=True,
            star_rating_above_fold=True,
            has_review_filtering=True,
        )
        tips = get_social_proof_tips(signals)
        # Only the ≥70 encouragement tip should remain
        assert len(tips) == 1
        assert "Q&A" in tips[0]

    def test_video_review_tip_when_no_video(self):
        signals = SocialProofSignals(
            review_app="judge.me",
            review_count=50,
            has_photo_reviews=True,
            star_rating_above_fold=True,
            has_review_filtering=True,
            has_video_reviews=False,
        )
        tips = get_social_proof_tips(signals)
        assert any("video" in t.lower() for t in tips)

    def test_empty_signals_gets_install_tip_first(self):
        """With completely empty signals, highest-priority tip is install."""
        tips = get_social_proof_tips(SocialProofSignals())
        assert tips[0].startswith("Install a review app")


# ===========================================================================
# Edge case tests for rubric + tips
# ===========================================================================


class TestRubricEdgeCases:
    """Edge cases around 0.0 and None boundaries."""

    def test_star_rating_0_is_not_none(self):
        """0.0 is a real rating — earns the 'star displayed' points."""
        signals = SocialProofSignals(review_app="loox", star_rating=0.0)
        score = score_social_proof(signals)
        # 25 + 15 = 40  (star displayed is 15 pts)
        assert score == 40

    def test_review_count_0_is_not_none(self):
        """0 is a real count — but below 5, so no count points."""
        signals = SocialProofSignals(review_app="loox", review_count=0)
        score = score_social_proof(signals)
        assert score == 25

    def test_star_5_0_exactly_not_optimal(self):
        """5.0 is outside the 4.2–4.7 optimal range — no bonus."""
        signals = SocialProofSignals(review_app="loox", star_rating=5.0)
        score = score_social_proof(signals)
        # 25 + 15 = 40  (no optimal range bonus)
        assert score == 40

    def test_star_4_1_below_optimal(self):
        """4.1 is below the 4.2 lower bound — no optimal bonus."""
        signals = SocialProofSignals(review_app="loox", star_rating=4.1)
        assert score_social_proof(signals) == 40

    def test_star_4_8_above_optimal(self):
        """4.8 is above the 4.7 upper bound — no optimal bonus."""
        signals = SocialProofSignals(review_app="loox", star_rating=4.8)
        assert score_social_proof(signals) == 40
