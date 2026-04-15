# Phase 1: Pricing Page - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the existing 4-tier pricing grid (Free/Starter/Growth/Pro with LemonSqueezy checkout) with a single free plan card + a Pro teaser card with waitlist CTA. Remove all old tier references from the pricing page and simplify the PlanTier type across the codebase.

</domain>

<decisions>
## Implementation Decisions

### Free Plan Card
- **D-01:** Generous feature list with all checkmarks, no X marks. List: 3 scans per month, Full 18-dimension scoring, Actionable recommendations, Revenue leak estimates.
- **D-02:** Keep the 3 scans/month limit (existing backend logic stays). Do not change to unlimited.
- **D-03:** CTA button: "Get Started" linking to homepage (same as current free tier behavior).

### Pro Waitlist CTA
- **D-04:** Side-by-side teaser card next to free card (2-column grid on desktop, stacked on mobile).
- **D-05:** Pro card has "coming soon" styling — grayed/muted, distinct from the active free card.
- **D-06:** Lists 4 future features: AI-powered fixes, Store monitoring, Competitor insights, Unlimited scans.
- **D-07:** "Join Waitlist" button. When clicked: if not authenticated, prompt signup first. If authenticated, record waitlist interest and show confirmation. (Waitlist backend is Phase 3 — this phase only needs the CTA button wired to auth check.)

### Old Tier Cleanup
- **D-08:** Remove Starter/Growth/Pro tier definitions from pricing page entirely. No dormant code.
- **D-09:** Remove LemonSqueezy checkout logic from PricingActions.tsx (env vars, buildCheckoutUrl, variant maps).
- **D-10:** Remove or simplify PaywallModal.tsx — the $29/$79/$149 subscription prompts are no longer used.
- **D-11:** Simplify PlanTier type from `"free" | "starter" | "growth" | "pro"` to `"free" | "pro"` across the codebase. Update getDimensionAccess() and any consuming code.

### Claude's Discretion
- Page hero copy ("Simple, transparent pricing") — update if it no longer fits, or keep if it still works
- Card styling details — reuse existing design tokens and card patterns
- Whether PricingActions.tsx is still needed or can be simplified/inlined after removing checkout logic

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pricing Page
- `webapp/src/app/pricing/page.tsx` — Current 4-tier pricing grid (to be replaced)
- `webapp/src/app/pricing/_components/PricingActions.tsx` — Client island with LemonSqueezy checkout (to be gutted)
- `webapp/src/app/pricing/error.tsx` — Error boundary (keep)

### Tier Gating System
- `webapp/src/lib/analysis/types.ts` — PlanTier type definition (line 9)
- `webapp/src/lib/analysis/conversion-model.ts` — getDimensionAccess() function (line 57)
- `webapp/src/lib/analysis/helpers.ts` — Re-exports PlanTier

### PaywallModal
- `webapp/src/components/PaywallModal.tsx` — Subscription upgrade modal (to be removed/simplified)

### Design System
- `webapp/src/components/ui/Button.tsx` — Button component with variant/size/shape props
- `webapp/src/components/ui/Modal.tsx` — Modal component (used by PaywallModal)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Button component** (`ui/Button`): Has variant (primary/secondary), size (md), shape (pill) props — reuse for both cards' CTAs
- **Design tokens**: --brand, --surface-container-lowest, --outline-variant, --shadow-brand-md already used in pricing cards
- **AuthModal**: Dynamic import pattern already set up in PricingActions.tsx — reuse for waitlist auth gate
- **Phosphor icons**: Already imported (Sparkle, RocketLaunch, Crown, etc.) — pick appropriate ones for new cards

### Established Patterns
- Pricing page is a Server Component with client islands (PricingActions) for interactive parts
- Card layout uses Tailwind with CSS custom properties for theming
- "Popular" badge pattern exists — can be adapted to "Coming Soon" badge for Pro card

### Integration Points
- `pricing/page.tsx` is the main file to rewrite (tier definitions + JSX)
- `PricingActions.tsx` will be heavily simplified (remove checkout, keep auth check for waitlist)
- `PlanTier` type change will touch: types.ts, conversion-model.ts, helpers.ts, and any components importing PlanTier
- `tier-gating.test.ts` will need updating after PlanTier simplification

</code_context>

<specifics>
## Specific Ideas

- Two-card layout: Free (active, prominent) + Pro (teaser, muted/coming-soon styling)
- Pro card should feel aspirational but clearly not yet available
- All feature lines on free card use checkmarks (generous feel, no X marks)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-pricing-page*
*Context gathered: 2026-04-15*
