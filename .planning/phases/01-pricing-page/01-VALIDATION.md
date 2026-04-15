---
phase: 1
slug: pricing-page
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-15
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest |
| **Config file** | `webapp/vitest.config.ts` |
| **Quick run command** | `cd webapp && npx vitest run src/lib/analysis/__tests__/tier-gating.test.ts` |
| **Full suite command** | `cd webapp && npm run test` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd webapp && npx vitest run src/lib/analysis/__tests__/tier-gating.test.ts`
- **After every plan wave:** Run `cd webapp && npm run test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01/1 | 01 | 1 | PRICE-03 | T-01-01 | PlanTier narrowed to "free" \| "pro"; no starter/growth references in library code | build | `cd webapp && npx tsc --noEmit` | N/A (type check) | pending |
| 01-01/2 | 01 | 1 | PRICE-03 | T-01-02 | PaywallModal stripped of LS env vars; no checkout URLs in client bundle | build | `cd webapp && npx tsc --noEmit` | N/A (type check) | pending |
| 01-01/3 | 01 | 1 | PRICE-03 | T-01-01 | getDimensionAccess("free", key) returns "locked"; getDimensionAccess("pro", key) returns "unlocked" | unit | `cd webapp && npx vitest run src/lib/analysis/__tests__/tier-gating.test.ts` | Exists (needs rewrite) | pending |
| 01-02/1 | 02 | 2 | PRICE-01, PRICE-02 | T-01-05 | No stale tier names or checkout URLs in page source | build | `cd webapp && npx tsc --noEmit` | N/A (type check) | pending |
| 01-02/2 | 02 | 2 | PRICE-02 | T-01-04 | Auth gate uses existing useSession; no new auth surface | build | `cd webapp && npx tsc --noEmit` | N/A (type check) | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `webapp/src/lib/analysis/__tests__/tier-gating.test.ts` — rewrite stubs for PRICE-03 (file exists but must be rewritten for 2-tier model; handled by Plan 01 Task 3)

*Existing test infrastructure covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Free card renders with correct features and styling | PRICE-01 | Visual layout and design token verification | Visit /pricing; confirm 2-card layout, green checkmarks, active border on Free card |
| Pro card has "Coming Soon" badge and muted styling | PRICE-02 | Visual styling check | Visit /pricing; confirm muted opacity, "Coming Soon" badge on Pro card |
| "Join Waitlist" opens AuthModal when signed out | PRICE-02 | Interactive flow requires browser session | Click "Join Waitlist" while signed out; AuthModal should open |
| "Join Waitlist" shows confirmation when signed in | PRICE-02 | Interactive flow requires authenticated session | Click "Join Waitlist" while signed in; inline confirmation should appear |
| No $79, starter, growth, LemonSqueezy text on /pricing | PRICE-03 | Visual scan of rendered page | Ctrl+F for "$79", "$29", "$149", "LemonSqueezy", "Starter", "Growth" on /pricing |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
