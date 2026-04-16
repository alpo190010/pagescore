---
phase: 2
slug: paywall-gates
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), pytest (backend) |
| **Config file** | `frontend/vitest.config.ts`, `backend/pytest.ini` |
| **Quick run command** | `cd frontend && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd frontend && npx vitest run && cd ../backend && python -m pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run --reporter=verbose`
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | GATE-01 | — | Anonymous users see scores only, no recommendation text | integration | `npx vitest run` | ⬜ W0 | ⬜ pending |
| TBD | TBD | TBD | GATE-02 | — | Authenticated users see full recommendations | integration | `npx vitest run` | ⬜ W0 | ⬜ pending |
| TBD | TBD | TBD | GATE-03 | — | Signup prompt displayed to anonymous users | integration | `npx vitest run` | ⬜ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Update `tier-gating.test.ts` — invert 18 assertions from "locked" to "unlocked" for free tier
- [ ] Add anonymous vs authenticated rendering tests for IssueCard component
- [ ] Add signup prompt visibility tests for results page

*Existing vitest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual appearance of locked cards | GATE-01 | CSS blur/overlay styling | Load results page as anonymous user, verify scores visible but recommendations blurred/hidden |
| Signup prompt UX flow | GATE-03 | Full browser interaction | Click signup CTA on results page, verify AuthModal opens with signup mode |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
