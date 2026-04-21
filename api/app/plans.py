"""Plan tier definitions — single source of truth for billing configuration.

Checkout URL contract (R085):
    https://<store>.lemonsqueezy.com/checkout/buy/<VARIANT_ID>?checkout[custom][user_id]=<USER_UUID>

The frontend (S04) constructs checkout URLs using this format. Each variant ID
maps to a plan tier via get_tier_for_variant() below. The variant IDs are
configured as environment variables (LEMONSQUEEZY_VARIANT_*) so they differ
between dev/staging/production LemonSqueezy stores.

credits_limit semantics: an integer cap per calendar month for metered tiers,
or None for unlimited-scan tiers.
"""

from app.config import settings

PLAN_TIERS: dict[str, dict] = {
    "free":    {"credits_limit": 3,    "price_monthly": 0},
    "starter": {"credits_limit": None, "price_monthly": 29},
    "pro":     {"credits_limit": None, "price_monthly": 99},
}


def get_tier_for_variant(variant_id: str) -> str | None:
    """Map a LemonSqueezy variant ID to its plan tier name.

    Both the monthly and annual Starter variants resolve to "starter".
    Pro remains defined but is not purchasable in v1 — it has no variant
    mapping until the Pro plan launches.

    Returns the tier string ("starter", "pro") or None if the variant_id
    is unknown or empty.
    """
    mapping = {
        settings.lemonsqueezy_variant_starter: "starter",
        settings.lemonsqueezy_variant_starter_annual: "starter",
    }
    return mapping.get(variant_id)
