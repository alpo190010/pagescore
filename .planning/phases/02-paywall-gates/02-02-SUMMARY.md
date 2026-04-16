---
phase: 02-paywall-gates
plan: "02"
subsystem: frontend-ui
tags: [paywall, auth-gate, anonymous-scan, issue-cards, cta]
dependency_graph:
  requires: ["02-01"]
  provides: [anonymous-real-scan-ui, locked-issue-cards, inline-cta, authmodal-signup-mode]
  affects: [webapp/src/app/analyze/page.tsx, webapp/src/components/AuthModal.tsx, webapp/src/components/analysis/IssueCard.tsx, webapp/src/components/analysis/CTACard.tsx]
tech_stack:
  added: []
  patterns: [isAnonymous-flag, initialMode-prop, locked-card-collapsed-view, inline-cta-card]
key_files:
  created: []
  modified:
    - webapp/src/app/analyze/page.tsx
    - webapp/src/components/AuthModal.tsx
    - webapp/src/components/analysis/IssueCard.tsx
    - webapp/src/components/analysis/CTACard.tsx
  deleted:
    - webapp/src/components/PaywallModal.tsx
decisions:
  - "Replaced isTeaser/isShallow/hasFullAccess with single isAnonymous = status === 'unauthenticated' flag"
  - "openCTAModal removed entirely; CTACard click wires directly to setAuthModalOpen(true)"
  - "handleSignIn callback removed; openIssueModal calls setAuthModalOpen(true) directly"
  - "Bottom gradient banner sections for anonymous/free removed; replaced with bare 'Analyze Another Page' button"
  - "AuthModal always opens with initialMode='signup' from analyze page (all entry points are anonymous users)"
metrics:
  duration_minutes: 25
  completed_date: "2026-04-16"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
---

# Phase 02 Plan 02: Paywall Gates UI Summary

**One-liner:** Rewrote analyze results page to gate recommendations behind signup using real anonymous scans, collapsed locked IssueCards, and an inline CTACard — replacing SAMPLE_SCAN fake data and deleting PaywallModal entirely.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add initialMode prop to AuthModal, redesign IssueCard locked state, add anonymous CTACard copy | 88931e1 | AuthModal.tsx, IssueCard.tsx, CTACard.tsx |
| 2 | Rewrite analyze page: anonymous real scan, PaywallModal removal, isAnonymous flag, CTA wiring | 848eba9 | analyze/page.tsx, PaywallModal.tsx (deleted) |

---

## What Was Built

### AuthModal.tsx
- Added `initialMode?: "signin" | "signup"` prop (default `"signin"` — backward compatible)
- `useState<AuthMode>` initializes from `initialMode`
- `useEffect` reset uses `initialMode` and includes it in dependency array
- All existing usage sites unaffected (default remains `"signin"`)

### IssueCard.tsx (locked state redesign)
- Locked card collapses to 4-row minimal layout: icon + score, dimension name only, impact badge, lock footer with "Sign up to see fixes"
- Problem text, revenue estimate, and tip are hidden when locked
- `aria-label` added to locked Button: `"{dimension} — locked. Sign up to see fixes."` (accessibility)
- `aria-hidden="true"` on LockKeyIcon (decorative)
- Unlocked layout unchanged; outer wrapper div identical for both states (grid layout preserved)

### CTACard.tsx
- Added `isAnonymous?: boolean` prop
- Anonymous copy: "Your page has {N} issues." / "Sign up free to see how to fix them." / "Create Free Account" button
- Default copy unchanged for existing non-anonymous usage

### analyze/page.tsx
- `isAnonymous = status === "unauthenticated"` replaces `isTeaser`, `isShallow`, `hasFullAccess`
- Anonymous scan: real `fetch` to `/analyze` with AbortController — no more SAMPLE_SCAN timer
- `captureEvent("anon_scan_completed")`, `captureEvent("locked_card_clicked")`, `captureEvent("cta_card_clicked")` added
- `openIssueModal`: anonymous path opens AuthModal directly (no PaywallModal)
- `openCTAModal` removed entirely; CTACard onClick wires directly
- `handleSignIn` callback removed (direct `setAuthModalOpen(true)` calls used instead)
- dimAccess: `isAnonymous ? "locked" as const : getDimensionAccess(planTier, leak.key)`
- Issues sub-heading: conditional copy for anonymous vs authenticated
- CTACard: anonymous-only (`{isAnonymous && <CTACard isAnonymous ... />}`)
- Credit exhaustion: "Join Pro Waitlist" button calls `router.push("/pricing")`
- Bottom sections: anonymous gets bare "Analyze Another Page" button; authenticated gets scan-another section
- Both old gradient banner sections (teaser and free-tier) removed
- AuthModal: `initialMode="signup"` always passed (all page.tsx entry points are for anonymous users)

### PaywallModal.tsx
- Deleted. Zero references remain in codebase.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Cleanup] Removed handleSignIn callback**
- **Found during:** Task 2
- **Issue:** After removing `openCTAModal`, `handleSignIn` was only used in that callback and the old teaser sign-in banner (both removed). Leaving it would be dead code and a TypeScript unused-variable warning.
- **Fix:** Removed `handleSignIn` useCallback; `openIssueModal` calls `setAuthModalOpen(true)` directly.
- **Files modified:** webapp/src/app/analyze/page.tsx
- **Commit:** 848eba9

**2. [Rule 1 - Cleanup] Removed isTeaser useState**
- **Found during:** Task 2
- **Issue:** `isTeaser` state variable (`const [isTeaser, setIsTeaser] = useState(false)`) was rendered unused after removing the SAMPLE_SCAN block and the `setIsTeaser(false)` call in the authenticated branch.
- **Fix:** Removed state declaration and the `setIsTeaser(false)` call in the authenticated fetch chain.
- **Files modified:** webapp/src/app/analyze/page.tsx
- **Commit:** 848eba9

---

## Known Stubs

None. All anonymous CTACard copy uses `leaks.length` from real scan result state. No hardcoded counts or placeholder text.

---

## Threat Flags

No new threat surface beyond what is documented in the plan's threat model. The `callbackUrl` pattern (`/analyze?url=${encodeURIComponent(url)}`) is unchanged — existing safe pattern.

---

## Verification Results

| Check | Result |
|-------|--------|
| `grep -E "isTeaser\|isShallow\|hasFullAccess\|paywallOpen\|PaywallModal\|SAMPLE_SCAN" page.tsx` | 0 matches (CLEAN) |
| `grep -r "PaywallModal" webapp/src/` | 0 matches (CLEAN) |
| `test ! -f webapp/src/components/PaywallModal.tsx` | DELETED |
| `grep -c "isAnonymous" page.tsx` | 9 usages |
| `grep -c "initialMode" AuthModal.tsx` | 5 usages |
| `grep -c "Sign up to see fixes" IssueCard.tsx` | 2 (aria-label + visible text) |
| `grep -c "Sign up free to see how to fix them" CTACard.tsx` | 2 (string + template) |
| `npx tsc --noEmit` | 0 errors |

---

## Self-Check: PASSED

- webapp/src/app/analyze/page.tsx: exists, modified
- webapp/src/components/AuthModal.tsx: exists, modified
- webapp/src/components/analysis/IssueCard.tsx: exists, modified
- webapp/src/components/analysis/CTACard.tsx: exists, modified
- webapp/src/components/PaywallModal.tsx: confirmed deleted
- Commit 88931e1: exists
- Commit 848eba9: exists
