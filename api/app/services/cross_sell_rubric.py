"""Scoring rubric and tip selector for cross-sell & upsell signals.

Converts :class:`CrossSellSignals` into a deterministic 0-100 score
using weighted criteria derived from Amazon, Omnisend, Getkard, Clerk,
and Shopify research on cross-sell and recommendation conversion impact,
and selects up to 3 prioritised improvement tips.
"""

from __future__ import annotations

from app.services.cross_sell_detector import CrossSellSignals


# ---------------------------------------------------------------------------
# Scoring rubric
# ---------------------------------------------------------------------------


def score_cross_sell(signals: CrossSellSignals) -> int:
    """Compute a 0-100 cross-sell & upsell score from extracted signals.

    Weighted criteria (max ~95 pts total):

        Cross-sell section present:             20 pts
        FBT bundle type (vs simple recs):       15 pts
        Bundle discount visible:                15 pts
        Optimal product count (3-4):            12 pts
        Near buy button placement:              10 pts
        Checkbox selection (FBT):                8 pts
        "Add all to cart" CTA:                   8 pts
        Bundle pricing shown:                    7 pts
        Penalty: >6 items (paradox of choice):  -5 pts
        Penalty: only 1 item:                   -3 pts

    Returns:
        Integer clamped to 0-100.
    """
    score = 0

    # Cross-sell section present (20 pts) \u2014 foundational
    if signals.has_cross_sell_section:
        score += 20

    # FBT bundle type (15 pts) \u2014 +55% AOV vs 10-15% for simple recs
    if signals.widget_type == "fbt_bundle":
        score += 15

    # Bundle discount visible (15 pts) \u2014 discounted bundles outperform
    if signals.has_discount_on_bundle:
        score += 15

    # Optimal product count 3-4 (12 pts) \u2014 below paradox of choice
    if signals.recommendation_count_optimal:
        score += 12

    # Near buy button (10 pts) \u2014 proximity = engagement
    if signals.near_buy_button:
        score += 10

    # Checkbox selection (8 pts) \u2014 Amazon FBT pattern
    if signals.has_checkbox_selection:
        score += 8

    # "Add all to cart" CTA (8 pts) \u2014 one-click friction reduction
    if signals.has_add_all_to_cart:
        score += 8

    # Bundle pricing shown (7 pts) \u2014 price transparency
    if signals.has_bundle_pricing:
        score += 7

    # Penalty: too many items >6 (-5 pts) \u2014 paradox of choice
    if signals.product_count > 6:
        score -= 5

    # Penalty: only 1 recommended item (-3 pts) \u2014 insufficient variety
    if signals.has_cross_sell_section and signals.product_count == 1:
        score -= 3

    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# Tip selector
# ---------------------------------------------------------------------------

# Tips ordered by impact priority (highest first).  Each entry is a
# (condition_callable, tip_string) pair.  The condition receives the
# signals *and* the computed score.

_TIP_RULES: list[tuple] = [
    # 1. No cross-sell at all \u2014 biggest opportunity
    (
        lambda s, _score: not s.has_cross_sell_section,
        (
            "Install a cross-sell app \u2014 Amazon attributes 35% of revenue "
            "to recommendations; even a basic \u2018Frequently Bought Together\u2019 "
            "block lifts AOV 20\u201330% (Omnisend/Shopify data)"
        ),
    ),
    # 2. Simple recs instead of FBT bundle
    (
        lambda s, _score: (
            s.has_cross_sell_section
            and s.widget_type == "simple_recommendation"
        ),
        (
            "Upgrade to \u2018Frequently Bought Together\u2019 bundles with "
            "discounts \u2014 FBT bundles lift AOV 55% vs 10\u201315% for "
            "simple \u2018You might also like\u2019 sections (Getkard)"
        ),
    ),
    # 3. No bundle discount
    (
        lambda s, _score: (
            s.has_cross_sell_section and not s.has_discount_on_bundle
        ),
        (
            "Add bundle discounts with visible savings \u2014 bundles with "
            "strikethrough pricing dramatically outperform flat "
            "recommendations; shoppers who click recommendations are "
            "4.5\u00d7 more likely to purchase (Clerk)"
        ),
    ),
    # 4. Too many items (>6) \u2014 paradox of choice
    (
        lambda s, _score: s.product_count > 6,
        (
            "Reduce to 3\u20134 recommended products \u2014 the paradox-of-"
            "choice threshold means more options = fewer conversions; "
            "3\u20134 is the optimal range"
        ),
    ),
    # 5. Not near buy button
    (
        lambda s, _score: s.has_cross_sell_section and not s.near_buy_button,
        (
            "Move cross-sell section near the buy button \u2014 "
            "recommendations placed near Add to Cart see 4.5\u00d7 "
            "higher click-through (Clerk)"
        ),
    ),
    # 6. No checkbox / add-all-to-cart
    (
        lambda s, _score: (
            s.has_cross_sell_section
            and not s.has_checkbox_selection
            and not s.has_add_all_to_cart
        ),
        (
            "Add \u2018Add all to cart\u2019 functionality \u2014 reducing "
            "the bundle purchase to one click removes friction and "
            "increases take rate; the 25% rule says cross-sell items "
            "should be priced at \u223c25% of the main product"
        ),
    ),
    # 7. Only 1 recommended item
    (
        lambda s, _score: (
            s.has_cross_sell_section and s.product_count == 1
        ),
        (
            "Show 3\u20134 recommended products \u2014 single "
            "recommendations lack the bundle psychology that drives "
            "AOV lift; product bundling lifts AOV 20\u201330% on "
            "average and up to 55% in best cases"
        ),
    ),
    # 8. Congratulatory \u2014 strong cross-sell setup
    (
        lambda s, score: score >= 80,
        (
            "Strong cross-sell setup \u2014 your FBT bundles with discounts "
            "follow Amazon\u2019s proven model. Consider A/B testing bundle "
            "discount percentages for further lift"
        ),
    ),
]


def get_cross_sell_tips(signals: CrossSellSignals) -> list[str]:
    """Return up to 3 research-backed cross-sell improvement tips.

    Tips are selected based on which cross-sell signals are missing or
    weak, prioritised by AOV/conversion impact (most impactful first).

    Args:
        signals: Extracted cross-sell & upsell signals.

    Returns:
        A list of 0-3 tip strings.
    """
    score = score_cross_sell(signals)
    tips: list[str] = []

    for condition, tip in _TIP_RULES:
        if condition(signals, score):
            tips.append(tip)
            if len(tips) >= 3:
                break

    return tips
