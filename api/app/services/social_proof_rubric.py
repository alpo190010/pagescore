"""Scoring rubric and tip selector for social proof signals.

Converts :class:`SocialProofSignals` into a deterministic 0–100 score
using weighted criteria derived from e-commerce conversion research,
and selects up to 3 prioritised improvement tips.
"""

from __future__ import annotations

from app.services.social_proof_detector import SocialProofSignals


# ---------------------------------------------------------------------------
# Scoring rubric
# ---------------------------------------------------------------------------


def score_social_proof(signals: SocialProofSignals) -> int:
    """Compute a 0–100 social proof score from extracted signals.

    Weighted criteria (max 100 pts total):
        - Review app present:           25 pts
        - Star rating displayed:        15 pts
        - Review count ≥ 5:             15 pts
        - Review count ≥ 30:             5 pts bonus
        - Review count ≥ 100:            5 pts bonus
        - Has photo or video reviews:   15 pts
        - Star rating in 4.2–4.7:       10 pts
        - Star rating above fold:        5 pts
        - Has review filtering/sorting:  5 pts

    Returns:
        Integer clamped to 0–100.
    """
    score = 0

    # Review app present (25 pts)
    if signals.review_app is not None:
        score += 25

    # Star rating displayed (15 pts)
    if signals.star_rating is not None:
        score += 15

    # Review count tiers (15 + 5 + 5 = 25 pts max)
    if signals.review_count is not None and signals.review_count >= 5:
        score += 15
        if signals.review_count >= 30:
            score += 5
        if signals.review_count >= 100:
            score += 5

    # Photo or video reviews (15 pts)
    if signals.has_photo_reviews or signals.has_video_reviews:
        score += 15

    # Optimal star range 4.2–4.7 (10 pts)
    if signals.star_rating is not None and 4.2 <= signals.star_rating <= 4.7:
        score += 10

    # Star rating above fold (5 pts)
    if signals.star_rating_above_fold:
        score += 5

    # Review filtering / sorting (5 pts)
    if signals.has_review_filtering:
        score += 5

    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# Tip selector
# ---------------------------------------------------------------------------

# Tips ordered by impact priority (highest first).  Each entry is a
# (condition_callable, tip_string) pair.  The condition receives the
# signals *and* the computed score.

_TIP_RULES: list[tuple] = [
    # 1. No review app at all — biggest gap
    (
        lambda s, _score: s.review_app is None,
        (
            "Install a review app \u2014 products with just 5 reviews see a "
            "270% increase in purchase likelihood (Spiegel Research Center)."
        ),
    ),
    # 2. Has app but very few reviews
    (
        lambda s, _score: (
            s.review_app is not None
            and (s.review_count is None or s.review_count < 5)
        ),
        (
            "Collect more reviews \u2014 the jump from 0 to 5 reviews "
            "delivers a 270% conversion lift."
        ),
    ),
    # 3. No photo reviews (but has app)
    (
        lambda s, _score: (
            s.review_app is not None and not s.has_photo_reviews
        ),
        (
            "Enable photo reviews \u2014 products with customer photos see "
            "106% higher conversion rates (PowerReviews)."
        ),
    ),
    # 4. Perfect 5.0 rating — suspicious
    (
        lambda s, _score: s.star_rating is not None and s.star_rating == 5.0,
        (
            "A perfect 5.0 rating can reduce trust \u2014 the optimal range "
            "is 4.2\u20134.7 stars (Spiegel Research Center)."
        ),
    ),
    # 5. Star rating not above fold
    (
        lambda s, _score: (
            s.review_app is not None and not s.star_rating_above_fold
        ),
        (
            "Move your star rating badge above the fold \u2014 56% of "
            "shoppers check reviews before anything else."
        ),
    ),
    # 6. No filtering
    (
        lambda s, _score: (
            s.review_app is not None and not s.has_review_filtering
        ),
        (
            "Add review filtering \u2014 shoppers who filter reviews are "
            "2x more likely to convert."
        ),
    ),
    # 7. 5–29 reviews — nudge toward 30
    (
        lambda s, _score: (
            s.review_count is not None and 5 <= s.review_count <= 29
        ),
        (
            "Grow your review count past 30 \u2014 conversion rates plateau "
            "around 30-50 reviews for most product categories."
        ),
    ),
    # 8. No video reviews (but has app)
    (
        lambda s, _score: (
            s.review_app is not None and not s.has_video_reviews
        ),
        (
            "Add video reviews \u2014 video testimonials are 3x more "
            "engaging than text-only reviews."
        ),
    ),
    # 9. High score — already strong, encourage Q&A
    (
        lambda s, score: score >= 70,
        (
            "Your review setup is strong. Consider adding Q&A alongside "
            "reviews to address pre-purchase questions."
        ),
    ),
]


def get_social_proof_tips(signals: SocialProofSignals) -> list[str]:
    """Return up to 3 research-backed improvement tips.

    Tips are selected based on which signals are missing or weak,
    prioritised by impact (most impactful first).

    Args:
        signals: Extracted social proof signals.

    Returns:
        A list of 0–3 tip strings.
    """
    score = score_social_proof(signals)
    tips: list[str] = []

    for condition, tip in _TIP_RULES:
        if condition(signals, score):
            tips.append(tip)
            if len(tips) >= 3:
                break

    return tips
