# Phase 1: Pricing Page - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-15
**Phase:** 01-pricing-page
**Areas discussed:** Free plan card content, Pro waitlist CTA design, Old tier cleanup

---

## Free Plan Card Content

| Option | Description | Selected |
|--------|-------------|----------|
| Generous list | List what users GET with all checkmarks, no X marks. Feels abundant. | ✓ |
| Minimal and clean | Just headline + 1-2 bullets + CTA. Less detail, more inviting. | |
| You decide | Claude picks based on design system | |

**User's choice:** Generous list
**Notes:** All features should be checkmarked — no exclusion markers.

| Option | Description | Selected |
|--------|-------------|----------|
| Unlimited scans | No limit. Scans cost ~$0.01 each. | |
| Keep 3/month limit | Keeps existing backend logic. Creates natural friction. | ✓ |
| Raise to 10/month | More generous but still bounded. | |

**User's choice:** Keep 3/month limit
**Notes:** Existing backend logic stays unchanged.

---

## Pro Waitlist CTA Design

| Option | Description | Selected |
|--------|-------------|----------|
| Teaser card | Second card with "Pro SOON" badge, grayed styling, future features list, "Join Waitlist" button | ✓ |
| Banner below | Horizontal banner below free card with button | |
| Inline in free card | Divider inside free card with coming-soon section | |

**User's choice:** Teaser card (side-by-side with free card)

| Option | Description | Selected |
|--------|-------------|----------|
| AI-powered fixes | "Get AI-generated rewrites for your product pages" | ✓ |
| Store monitoring | "Weekly score tracking across your store" | ✓ |
| Competitor insights | "See how your pages compare to competitors" | ✓ |
| Unlimited scans | "No monthly scan limit" | ✓ |

**User's choice:** All four features listed on the Pro teaser card.

---

## Old Tier Cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Remove entirely | Delete old checkout flow, PaywallModal refs, LemonSqueezy from pricing. Clean break. | ✓ |
| Leave dormant | Keep code but hide from users. Less work, stale code lingers. | |
| You decide | Claude picks cleanest approach | |

**User's choice:** Remove entirely

| Option | Description | Selected |
|--------|-------------|----------|
| Leave for Phase 2 | Only touch pricing page. Tier type reworked in Phase 2. | |
| Simplify now | Change PlanTier to "free" \| "pro". Touches more files, overlaps Phase 2. | ✓ |

**User's choice:** Simplify PlanTier now (in Phase 1, not deferred to Phase 2)

---

## Claude's Discretion

- Hero copy update if "Simple, transparent pricing" no longer fits
- Card styling details using existing design tokens
- Whether PricingActions.tsx survives or gets inlined after removing checkout logic

## Deferred Ideas

None
