---
phase: 01-pricing-page
verified: 2026-04-16T10:00:00Z
status: human_needed
score: 2/3 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Visit /pricing and verify 2-card layout — Free card with 'Get Started' + Pro card with 'Coming Soon' badge + 'Join Waitlist'"
    expected: "Two cards side-by-side on desktop: Free with active brand border, Pro with muted styling and Coming Soon badge"
    why_human: "Visual layout and design token styling cannot be verified programmatically"
  - test: "Click 'Join Waitlist' while signed out"
    expected: "AuthModal opens prompting sign-in"
    why_human: "Interactive auth flow requires a browser session and session state"
  - test: "Click 'Join Waitlist' while signed in"
    expected: "Inline confirmation 'You're on the list!' appears without page navigation"
    why_human: "Requires authenticated session and React state interaction"
  - test: "Confirm FAQ section heading reads 'Free, with more on the way.' and body contains no LemonSqueezy reference"
    expected: "Heading and body updated; no billing/LemonSqueezy copy visible"
    why_human: "Visual copy verification of rendered page"
  - test: "Clarify ROADMAP.md SC1 wording vs D-02: SC1 says 'unlimited scans' but Free card shows '3 scans per month'"
    expected: "Either update ROADMAP.md SC1 to say '3 scans per month' (matching locked decision D-02), or confirm a product decision to change the page"
    why_human: "Contract conflict between ROADMAP.md success criteria and locked project decision D-02 — only the project owner can resolve"
---

# Phase 1: Pricing Page — Verification Report

**Phase Goal:** Visitors see accurate, current pricing — one free plan and a Pro waitlist signal — with no stale tier references
**Verified:** 2026-04-16T10:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | User visiting /pricing sees exactly one plan card describing the free tier (unlimited scans, full scoring, recommendations, revenue leak estimates) | PARTIAL | Free card exists with full scoring, recommendations, revenue leak estimates — but scan pill reads "3 scans per month" (not "unlimited"). D-02 explicitly locked 3 scans/month; ROADMAP.md SC1 wording was never updated. Conflict requires human resolution. |
| 2 | User sees a Pro waitlist CTA below (beside) the free plan card | VERIFIED | Pro card with "Coming Soon" badge and "Join Waitlist" CTA in 2-column grid. PricingActions.tsx wires auth gate: unauthenticated opens AuthModal, authenticated sets waitlistConfirmed state. |
| 3 | No mention of $79, old pricing tiers, or any paid plan is visible anywhere on /pricing | VERIFIED | grep across `webapp/src/app/pricing/page.tsx` and `PricingActions.tsx` returns zero matches for: `$29`, `$79`, `$149`, `starter`, `growth`, `LemonSqueezy`, `LS_STORE_URL`, `LS_VARIANT`, `buildCheckoutUrl`, `VARIANT_MAP`. FAQ heading updated to "Free, with more on the way." |

**Score:** 2/3 truths verified (1 partial — human decision needed on SC1 wording)

---

### Plan 01-01 Must-Have Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | PlanTier type is 'free' \| 'pro' with no mention of 'starter' or 'growth' | VERIFIED | `webapp/src/lib/analysis/types.ts` line 9: `export type PlanTier = "free" \| "pro";` |
| 2 | getDimensionAccess('free', anyKey) returns 'locked' for all 18 dimensions | VERIFIED | conversion-model.ts: `if (plan === "pro") return "unlocked"; return "locked";` — free always returns locked |
| 3 | getDimensionAccess('pro', anyKey) returns 'unlocked' for all 18 dimensions | VERIFIED | Same function: pro branch returns unlocked unconditionally |
| 4 | STARTER_DIMENSIONS constant no longer exists anywhere in the codebase | VERIFIED | grep for `STARTER_DIMENSIONS` across `webapp/src/` returns zero matches |
| 5 | No $29, $79, $149, 'starter', or 'growth' text appears in PaywallModal.tsx | VERIFIED | All checkout constants, SubscriptionTier interface, TIERS array, buildCheckoutUrl, and isStarter derivation removed. PaywallModal is a 2-prop shell. |
| 6 | Tier-gating tests pass with the new 2-tier model | VERIFIED | tier-gating.test.ts rewritten: 4 describe blocks (free plan, pro plan, unknown key ×2), no STARTER_DIMENSIONS import, no starter/growth test cases |
| 7 | TypeScript build succeeds with zero type errors | UNVERIFIED (human) | SUMMARY 01-01 reports `npx tsc --noEmit` exits 0 — pre-existing next-auth/vitest environmental errors only. Cannot run build in this context. |

### Plan 01-02 Must-Have Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | User visiting /pricing sees exactly one active plan card: Free with 4 checkmarked features | VERIFIED (code) | page.tsx PRICING_TIERS[0]: key="free", features array has 4 items all `included: true`, all rendered with CheckCircle |
| 2 | User sees a muted Pro teaser card with 'Coming Soon' badge beside the free card | VERIFIED (code) | page.tsx: `{!isActive && (<div ... >Coming Soon</div>)}` with `border-[var(--outline-variant)] opacity-70` |
| 3 | Pro card lists 4 future features: AI-powered fixes, Store monitoring, Competitor insights, Unlimited scans | VERIFIED | page.tsx PRICING_TIERS[1].features: all 4 items confirmed by direct read |
| 4 | 'Join Waitlist' button opens AuthModal for unauthenticated users | VERIFIED (code) | PricingActions.tsx: `if (!isSignedIn) { setAuthModalOpen(true); return; }` — AuthModal dynamically imported |
| 5 | 'Join Waitlist' button shows inline confirmation for authenticated users | VERIFIED (code) | PricingActions.tsx: `waitlistConfirmed` state → renders `"You're on the list!"` paragraph |
| 6 | 'Get Started' button links to homepage | VERIFIED | PricingActions.tsx: Free tier branch renders `<Link href="/">{tier.ctaLabel}</Link>` |
| 7 | No mention of $29, $79, $149, 'starter', 'growth', or 'LemonSqueezy' on /pricing | VERIFIED | grep across both pricing files returns zero matches |
| 8 | FAQ section says 'Free, with more on the way.' not 'billed monthly via LemonSqueezy' | VERIFIED | page.tsx line 160: `Free, with more on the way.`; no LemonSqueezy text anywhere in file |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `webapp/src/lib/analysis/types.ts` | `PlanTier = "free" \| "pro"` | VERIFIED | Line 9 confirmed |
| `webapp/src/lib/analysis/conversion-model.ts` | Simplified getDimensionAccess, no STARTER_DIMENSIONS | VERIFIED | Function body: `if (plan === "pro") return "unlocked"; return "locked";` |
| `webapp/src/lib/analysis/__tests__/tier-gating.test.ts` | Rewritten 2-tier tests | VERIFIED | 4 test cases covering free/pro/unknown key scenarios; no starter/growth references |
| `webapp/src/components/PaywallModal.tsx` | Minimal sign-up prompt shell, 2 props only | VERIFIED | Props: `{ isOpen: boolean; onClose: () => void }`. No checkout logic. |
| `webapp/src/app/analyze/page.tsx` | Updated tier derivations, simplified PaywallModal calls | VERIFIED | `hasFullAccess = planTier === "pro"`, `isShallow = planTier === "free"`, both PaywallModal call sites have 2 props only |
| `webapp/src/app/pricing/page.tsx` | 2-card layout (Free active + Pro teaser) | VERIFIED | PRICING_TIERS array with 2 entries; sm:grid-cols-2, max-w-3xl; Coming Soon badge |
| `webapp/src/app/pricing/_components/PricingActions.tsx` | Auth-gated waitlist CTA | VERIFIED | waitlistConfirmed state, AuthModal dynamic import, 3-branch render tree |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `types.ts` | `conversion-model.ts` | `PlanTier` import | VERIFIED | `import type { CategoryScores, PlanTier } from './types';` confirmed |
| `helpers.ts` | `conversion-model.ts` | getDimensionAccess re-export | VERIFIED | `export { calculateConversionLoss, calculateDollarLossPerThousand, getDimensionAccess } from "./conversion-model";` — STARTER_DIMENSIONS absent |
| `analyze/page.tsx` | `PaywallModal.tsx` | dynamic import, 2-prop call sites | VERIFIED | Both `<PaywallModal isOpen={paywallOpen} onClose={closePaywall} />` — no stale props |
| `pricing/page.tsx` | `PricingActions.tsx` | `<PricingActions tier={...}>` | VERIFIED | Both cards call `<PricingActions tier={{ key: tier.key, ctaLabel: tier.ctaLabel }} />` |
| `PricingActions.tsx` | `AuthModal` | `dynamic(() => import("@/components/AuthModal"))` | VERIFIED | `callbackUrl="/pricing"` confirmed |

---

### Data-Flow Trace (Level 4)

Not applicable — pricing page is a Server Component rendering static tier data from PRICING_TIERS constant. No database queries or dynamic data sources. PricingActions.tsx reads `useSession()` for auth state only.

---

### Behavioral Spot-Checks

Step 7b skipped for interactive UI behaviors — the app requires a running dev server and browser session.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| PRICE-01 | 01-02 | User sees a single free plan card (unlimited scans, full scoring, recommendations, revenue leak estimates) | PARTIAL | Free card verified for full scoring/recommendations/revenue leak estimates. Scan count reads "3 scans per month" per D-02 (locked decision). ROADMAP.md SC1 wording says "unlimited scans" — wording was not updated after D-02 was locked. Requires human to update ROADMAP.md or make a product call. |
| PRICE-02 | 01-02 | User sees a Pro waitlist CTA below the free plan | VERIFIED | Pro teaser card with "Coming Soon" badge and auth-gated "Join Waitlist" CTA confirmed in code |
| PRICE-03 | 01-01 | Old pricing tiers and $79 references are removed | VERIFIED | PlanTier narrowed to free\|pro; STARTER_DIMENSIONS deleted; PaywallModal gutted; no $29/$79/$149/LemonSqueezy/starter/growth in pricing page, analyze page, or shared libraries |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `webapp/src/app/analyze/page.tsx` | 230 | `// Both free and starter users see upgrade CTAs` — stale code comment referencing "starter" | Warning | Non-functional (JSX comment, not rendered). Does not affect runtime. The related JSX comment was fixed in commit dbb5f58 but this code comment was missed. |

---

### Human Verification Required

#### 1. ROADMAP.md SC1 Wording Conflict (BLOCKING)

**Test:** Read ROADMAP.md Phase 1 Success Criterion 1 ("unlimited scans") vs actual Free card ("3 scans per month") vs locked decision D-02.
**Expected:** Project owner confirms ROADMAP.md SC1 should be updated to say "3 scans per month" (matching D-02), or overrides D-02 to show "unlimited" on the page.
**Why human:** Conflict between the ROADMAP.md verification contract and a locked project decision (D-02 in CONTEXT.md). The research and plans correctly interpreted D-02 and built accordingly, but the ROADMAP.md success criteria was never updated. Only the project owner can decide which source of truth wins.

This is the only item blocking a `passed` status. If you accept the D-02 interpretation, add an override:

```yaml
overrides:
  - must_have: "User visiting /pricing sees exactly one plan card describing the free tier (unlimited scans, full scoring, recommendations, revenue leak estimates)"
    reason: "D-02 locked 3 scans/month (existing backend logic unchanged). 'Unlimited scans' in ROADMAP.md SC1 is a stale wording error. Pro card correctly shows 'Unlimited scans' as a future Pro feature."
    accepted_by: "aleksandrephatsatsia"
    accepted_at: "2026-04-16T10:00:00Z"
```

#### 2. Visual Layout — 2-Card Pricing Grid

**Test:** Start dev server (`cd webapp && npm run dev`), visit http://localhost:3000/pricing.
**Expected:** Two cards side-by-side on desktop, stacked on mobile. Left: "Free" card with Sparkle icon, active brand border, 4 green checkmarks, "Get Started" button. Right: "Pro" card with RocketLaunch icon, muted styling, "Coming Soon" badge at top.
**Why human:** Responsive layout and design token rendering cannot be verified programmatically.

#### 3. Interactive: "Join Waitlist" Unauthenticated

**Test:** Visit /pricing signed out. Click "Join Waitlist."
**Expected:** AuthModal opens (sign-in prompt).
**Why human:** Interactive auth flow requires browser session state.

#### 4. Interactive: "Join Waitlist" Authenticated

**Test:** Visit /pricing signed in. Click "Join Waitlist."
**Expected:** Button disappears; inline confirmation "You're on the list! We'll let you know when Pro launches." appears in success color.
**Why human:** Requires authenticated session and React state interaction in browser.

---

### Gaps Summary

No blocking code gaps. The single partially-verified item (SC1 scan count wording) is a ROADMAP.md documentation conflict, not a code defect. The implementation correctly follows D-02 (3 scans/month). The ROADMAP.md SC1 wording was written before D-02 was locked and was never updated.

**Recommended action:** Update ROADMAP.md Phase 1 Success Criterion 1 to read: "User visiting /pricing sees exactly one plan card describing the free tier (3 scans per month, full 18-dimension scoring, recommendations, revenue leak estimates)"

Then add the override above and re-run verification — all truths will pass and status will become `human_needed` for visual checks only.

The stale code comment on `analyze/page.tsx` line 230 is informational only. Fix with: `// Both free and teaser users see upgrade CTAs`

---

_Verified: 2026-04-16T10:00:00Z_
_Verifier: Claude (gsd-verifier)_
