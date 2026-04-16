# Phase 3: Waitlist - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 03-waitlist
**Areas discussed:** Persistent waitlist state, Post-signup auto-enroll, Confirmation experience, Admin visibility

---

## Persistent waitlist state

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, persist | Backend stores waitlist flag. Frontend checks on load — button shows "You're on the list" permanently. | ✓ |
| No, fire-and-forget | Backend records signup but frontend doesn't check. Button resets on refresh. | |

**User's choice:** Yes, persist (Recommended)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Boolean flag on User | Simple `pro_waitlist` boolean column. Matches STATE.md suggestion. | ✓ |
| Boolean + timestamp on User | Boolean AND `pro_waitlist_at` datetime. Captures when they joined. | |
| Separate waitlist table | New `waitlist_entries` table. More flexible but heavier. | |

**User's choice:** Boolean flag on User (Recommended)
**Notes:** No timestamp needed — simple boolean is sufficient.

---

## Post-signup auto-enroll

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-enroll after signup | Auto-set pro_waitlist=true after signup. Smoother experience. | ✓ |
| Require second click | Return to /pricing, user clicks "Join Waitlist" again. | |

**User's choice:** Auto-enroll after signup (Recommended)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Query param approach | AuthModal callbackUrl becomes /pricing?waitlist=1. On load, detects param + session, fires POST automatically. | ✓ |
| You decide | Claude picks best implementation approach. | |

**User's choice:** Query param approach (Recommended)
**Notes:** None

---

## Confirmation experience

| Option | Description | Selected |
|--------|-------------|----------|
| Inline text swap | Button area becomes confirmation message. Already stubbed in PricingActions.tsx. | ✓ |
| Success toast + disabled button | Toast notification + greyed-out button. | |
| You decide | Claude picks best approach. | |

**User's choice:** Inline text swap (Recommended)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Same inline message | Pro card always shows "You're on the list!" instead of Join button on return visits. | ✓ |
| Subtle badge only | Button stays but disabled with "✓ Waitlisted" badge. | |

**User's choice:** Same inline message (Recommended)
**Notes:** Consistent experience — no confusion on return visits.

---

## Admin visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Add to existing /admin/users | Badge/filter on users list. Include pro_waitlist in API response. | ✓ |
| Skip admin changes | Query DB directly when needed. | |
| You decide | Claude picks simplest approach. | |

**User's choice:** Add to existing /admin/users (Recommended)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add to analytics | Waitlist count on GET /admin/analytics. Quick demand signal. | ✓ |
| No, filter is enough | Just badge/filter on users list. | |
| You decide | Claude picks based on simplicity. | |

**User's choice:** Yes, add to analytics
**Notes:** None

## Claude's Discretion

- Error handling for POST /user/waitlist (duplicate calls, edge cases)
- Whether to strip `?waitlist=1` query param after auto-enrolling
- Exact admin badge styling and filter implementation
- Whether results page credit exhaustion CTA should also check waitlist status

## Deferred Ideas

None — discussion stayed within phase scope
