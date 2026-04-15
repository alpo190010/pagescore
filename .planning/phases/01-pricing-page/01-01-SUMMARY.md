---
phase: 01-pricing-page
plan: "01"
subsystem: analysis-lib
tags: [tier-gating, type-system, paywall, refactor]
dependency_graph:
  requires: []
  provides: [PlanTier-2-tier, getDimensionAccess-2-tier, PaywallModal-simplified]
  affects: [analyze-page, admin-users, tier-gating-tests]
tech_stack:
  added: []
  patterns: [2-tier-plan-model, type-narrowing, pure-function-gate]
key_files:
  created: []
  modified:
    - webapp/src/lib/analysis/types.ts
    - webapp/src/lib/analysis/conversion-model.ts
    - webapp/src/lib/analysis/helpers.ts
    - webapp/src/lib/analysis/constants.tsx
    - webapp/src/lib/format.ts
    - webapp/src/app/admin/users/[id]/page.tsx
    - webapp/src/app/admin/users/page.tsx
    - webapp/src/app/admin/page.tsx
    - webapp/src/components/PaywallModal.tsx
    - webapp/src/app/analyze/page.tsx
    - webapp/src/lib/analysis/__tests__/tier-gating.test.ts
decisions:
  - "PlanTier narrowed to free|pro only — starter and growth permanently removed from type system"
  - "getDimensionAccess simplified to single-branch: pro=unlocked, else locked — no dimension-key dependency"
  - "PaywallModal gutted to minimal 2-prop shell — Phase 2 will add sign-up CTA"
  - "STARTER_DIMENSIONS constant deleted from conversion-model.ts and all re-export points"
metrics:
  duration: "~7 minutes"
  completed: "2026-04-16"
  tasks_completed: 3
  files_modified: 11
  commits: 6
---

# Phase 1 Plan 01: Narrow PlanTier to 2-tier model — Summary

**One-liner:** PlanTier narrowed from `"free"|"starter"|"growth"|"pro"` to `"free"|"pro"` across entire codebase, with STARTER_DIMENSIONS deleted and PaywallModal stripped of LemonSqueezy checkout logic.

## Tasks Completed

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | Narrow PlanTier, rewrite getDimensionAccess, update library consumers | 98d1959 | Done |
| 2 | Simplify PaywallModal and update analyze/page.tsx consumers | 7226186 | Done |
| 3 | Rewrite tier-gating tests for 2-tier model | a6b936a | Done |

## Verification Results

- `npx tsc --noEmit` — zero errors in plan files (pre-existing next-auth/vitest/radix-ui missing-module errors are environmental, not caused by this plan)
- `npx vitest run src/lib/analysis/__tests__/tier-gating.test.ts` — 4 tests pass
- No `STARTER_DIMENSIONS` references anywhere in `webapp/src/`
- No `starter` or `growth` logic references in analysis lib, admin UI, or analyze page

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] constants.tsx re-exported STARTER_DIMENSIONS**
- **Found during:** Task 1
- **Issue:** `webapp/src/lib/analysis/constants.tsx` re-exported `STARTER_DIMENSIONS` from `conversion-model.ts`. After deleting the constant, this would cause a TypeScript build error not caught by the plan's file list.
- **Fix:** Removed `STARTER_DIMENSIONS` from the `export { CATEGORY_BENCHMARKS, STARTER_DIMENSIONS }` line in constants.tsx.
- **Files modified:** `webapp/src/lib/analysis/constants.tsx`
- **Commit:** 98d1959

**2. [Rule 1 - Bug] admin/users/page.tsx PLAN_OPTIONS had stale tier values**
- **Found during:** Task 3 verification
- **Issue:** `webapp/src/app/admin/users/page.tsx` (the users list page) had `PLAN_OPTIONS = ["all", "free", "starter", "growth", "pro"]` — a filter dropdown with stale tier values not in the plan's file list.
- **Fix:** Narrowed to `["all", "free", "pro"]`.
- **Files modified:** `webapp/src/app/admin/users/page.tsx`
- **Commit:** a9de218

**3. [Rule 1 - Bug] admin/page.tsx planBarColor had stale growth/starter cases**
- **Found during:** Task 3 verification
- **Issue:** `webapp/src/app/admin/page.tsx` had a `planBarColor` function with `case "growth"` and `case "starter"` switch cases not in the plan's file list.
- **Fix:** Removed both cases, left only `case "pro"` and `default`.
- **Files modified:** `webapp/src/app/admin/page.tsx`
- **Commit:** f5e4997

**4. [Rule 1 - Bug] Stale comment in analyze/page.tsx**
- **Found during:** Task 3 verification
- **Issue:** JSX comment `{/* CTA card for free, starter, and teaser users */}` referenced starter.
- **Fix:** Updated comment to `{/* CTA card for free and teaser users */}`.
- **Files modified:** `webapp/src/app/analyze/page.tsx`
- **Commit:** dbb5f58

### Out of Scope (Deferred)

- `webapp/src/app/pricing/page.tsx` and `webapp/src/app/pricing/_components/PricingActions.tsx` still reference `starter`/`growth` tier keys and LemonSqueezy variant env vars. These are the **old pricing page** files that will be fully replaced in plan 01-02 (the pricing page UI rewrite). Fixing them here would conflict with that plan's scope.

## Threat Surface

T-01-01 mitigated: `getDimensionAccess` is now strictly more restrictive — free returns locked for all dims, no accidental over-permissiveness possible.

T-01-02 mitigated: All `LS_STORE_URL`, `LS_VARIANT_*` declarations removed from PaywallModal.tsx — no env vars leak to client bundle from this component.

T-01-03 accepted: `(planData?.plan as PlanTier)` runtime cast is safe — `getDimensionAccess` returns `"locked"` for any non-`"pro"` value at runtime, so stale server data sending `"starter"` silently falls to the secure default.

## Known Stubs

None — the PaywallModal shell is intentionally minimal with a `{/* Phase 2 will add sign-up / paywall gate CTA here */}` placeholder. This is documented in the plan (D-10) and intentional for Phase 2.

## Self-Check: PASSED

All 12 files found on disk. All 6 commits verified in git log.
