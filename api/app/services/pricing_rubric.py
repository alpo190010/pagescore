"""Scoring rubric and tip selector for pricing psychology signals.

Converts :class:`PricingSignals` into a deterministic 0–100 score using
weighted criteria derived from MIT, Princeton, and industry research on
price presentation and conversion optimisation, and selects up to 3
prioritised improvement tips.
"""

from __future__ import annotations

from app.services.pricing_detector import PricingSignals


# ---------------------------------------------------------------------------
# Scoring rubric
# ---------------------------------------------------------------------------


def score_pricing(signals: PricingSignals) -> int:
    """Compute a 0–100 pricing psychology score from extracted signals.

    Weighted criteria (max 100 pts total):

        Compare-at / strikethrough price:                   30 pts
        Charm pricing (.99/.95, non-round):                 20 pts
        BNPL installment messaging (Klarna/Afterpay/etc.):  25 pts
        Truthful urgency (scarcity or timer, no fake risk): 15 pts
        Scarcity text present but timer has fake risk:      10 pts

    Returns:
        Integer clamped to 0–100.
    """
    score = 0

    # Compare-at / strikethrough anchoring (30 pts)
    if signals.has_compare_at_price or signals.has_strikethrough_price:
        score += 30

    # Charm pricing — only for non-round prices (20 pts)
    if signals.has_charm_pricing and not signals.is_round_price:
        score += 20

    # BNPL installment messaging (25 pts)
    if signals.has_bnpl_near_price:
        score += 25

    # Urgency / scarcity scoring
    has_any_urgency = signals.has_countdown_timer or signals.has_scarcity_messaging
    if has_any_urgency:
        if signals.has_fake_timer_risk and not signals.has_scarcity_messaging:
            # Timer only, likely fake — no credit
            pass
        elif signals.has_fake_timer_risk and signals.has_scarcity_messaging:
            # Scarcity text is real but timer anchor is unverified — partial credit
            score += 10
        else:
            # Truthful urgency (verifiable timer or scarcity text without fake-timer risk)
            score += 15

    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# Tip selector
# ---------------------------------------------------------------------------

# Tips ordered by impact priority (highest first). Each entry is a
# (condition_callable, tip_string) pair. The condition receives the
# signals *and* the computed score.

_TIP_RULES: list[tuple] = [
    # 1. No compare-at / strikethrough price → anchoring lift
    (
        lambda s, _score: not s.has_compare_at_price and not s.has_strikethrough_price,
        (
            "Add a compare-at price \u2014 strikethrough anchoring produces a "
            "25\u201340% conversion lift through price anchoring and the "
            "left-digit effect (MIT/Shopify)"
        ),
    ),
    # 2. No charm pricing on a round price
    (
        lambda s, _score: (
            not s.has_charm_pricing
            and s.is_round_price
            and s.price_value is not None
        ),
        (
            "Switch to charm pricing (e.g. $49.99 instead of $50) \u2014 "
            "MIT field experiments show a 24% sales increase from .99 endings"
        ),
    ),
    # 3. No BNPL installment messaging
    (
        lambda s, _score: not s.has_bnpl_near_price,
        (
            "Add Klarna or Afterpay installment messaging near the price \u2014 "
            "\u201cPay in 4\u201d framing increases conversion 20\u201335% on "
            "items over $50 (McKinsey/RBC Capital Markets)"
        ),
    ),
    # 4. Fake timer risk — trust warning before generic urgency tip
    (
        lambda s, _score: s.has_fake_timer_risk,
        (
            "Your countdown timer may appear fake \u2014 Princeton research found "
            "~40% of e-commerce timers are artificial, damaging trust. Use only "
            "truthful, verifiable scarcity (e.g. bind timer to actual sale end date)"
        ),
    ),
    # 5. No urgency messaging at all
    (
        lambda s, _score: not s.has_countdown_timer and not s.has_scarcity_messaging,
        (
            "Add real-time stock levels (\u2018Only 3 left\u2019) \u2014 "
            "truthful scarcity messaging increases conversion up to 17.8% "
            "(Poper/Tuncer et al. 2023)"
        ),
    ),
    # 6. Congratulatory — pricing strategy is strong
    (
        lambda s, score: score >= 85,
        (
            "Excellent pricing strategy \u2014 your store uses anchoring, "
            "charm pricing, BNPL installments, and truthful urgency"
        ),
    ),
]


def get_pricing_tips(signals: PricingSignals) -> list[str]:
    """Return up to 3 research-backed pricing improvement tips.

    Tips are selected based on which pricing signals are missing or
    weak, prioritised by conversion impact (most impactful first).

    Args:
        signals: Extracted pricing psychology signals.

    Returns:
        A list of 0\u20133 tip strings.
    """
    score = score_pricing(signals)
    tips: list[str] = []

    for condition, tip in _TIP_RULES:
        if condition(signals, score):
            tips.append(tip)
            if len(tips) >= 3:
                break

    return tips
