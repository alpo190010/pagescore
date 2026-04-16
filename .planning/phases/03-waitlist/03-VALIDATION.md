---
phase: 3
slug: waitlist
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) / Next.js dev server (frontend) |
| **Config file** | `api/pytest.ini` or `api/pyproject.toml` |
| **Quick run command** | `cd api && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd api && python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd api && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd api && python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | WAIT-01 | — | Anonymous → auth redirect | integration | TBD | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | WAIT-02 | — | Auth user → DB flag set | integration | TBD | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | WAIT-03 | — | Confirmation shown after join | integration | TBD | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `api/tests/test_waitlist.py` — stubs for WAIT-01, WAIT-02, WAIT-03
- [ ] Alembic migration applied before tests run

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Confirmation message renders correctly | WAIT-03 | Visual UI verification | Navigate to /pricing, click Join Pro Waitlist, verify inline confirmation text appears |
| Auto-enroll after signup via ?waitlist=1 | WAIT-01 | Full OAuth flow required | Sign out, click Join Waitlist as anon, complete signup, verify auto-enrolled on redirect |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
