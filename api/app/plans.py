"""Plan tier definitions — single source of truth for billing configuration.

Billing provider: **Paddle** (Paddle Billing API, not Paddle Classic).

The frontend opens Paddle's inline checkout via `@paddle/paddle-js`:

    paddle.Checkout.open({
        items: [{ priceId, quantity: 1 }],
        customData: { user_id: "<uuid>" },
        customer: { email },
    })

Paddle then delivers webhook events (subscription.created, subscription.updated,
subscription.canceled, subscription.past_due) to `POST /webhook`. Each event's
`data.items[].price.id` maps to a tier via `get_tier_for_price_id`.

credits_limit semantics: an integer cap per calendar month for metered tiers,
or None for unlimited-scan tiers.
"""

from app.config import settings

PLAN_TIERS: dict[str, dict] = {
    "free":    {"credits_limit": 3,    "price_monthly": 0},
    "starter": {"credits_limit": None, "price_monthly": 29},
    "pro":     {"credits_limit": None, "price_monthly": 99},
}


def get_tier_for_price_id(price_id: str) -> str | None:
    """Map a Paddle price ID to its plan tier name.

    Three prices currently resolve to ``"starter"``:
      - the $79 Membership (current paid offer — 1-year access);
      - the legacy Starter monthly subscription (dormant — no UI);
      - the legacy Starter annual subscription (dormant — no UI).

    Reusing ``"starter"`` keeps the entitlement gates ("unlimited scans,
    full recommendations") working unchanged. The user-facing label
    "Membership" lives on the pricing page; ``plan_tier`` stays semantic.

    Returns the tier string or None if the price_id is unknown or empty.
    """
    mapping = {
        settings.paddle_price_membership: "starter",
        settings.paddle_price_starter_monthly: "starter",
        settings.paddle_price_starter_annual: "starter",
    }
    # Treat the empty-string env default as a sentinel for "unmapped".
    mapping.pop("", None)
    return mapping.get(price_id)
