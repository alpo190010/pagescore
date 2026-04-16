# Phase 3: Waitlist - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Backend + flow for Pro interest capture. An authenticated user clicking "Join Waitlist" on the pricing page is recorded in the database with a waitlist flag, and sees immediate confirmation. Anonymous users are directed to sign up first, then auto-enrolled. The pricing page remembers waitlist status across sessions.

</domain>

<decisions>
## Implementation Decisions

### Database storage
- **D-01:** Add a `pro_waitlist` boolean column (default false) to the existing `users` table. No separate table.
- **D-02:** Alembic migration to add the column. No timestamp column — the boolean is sufficient.

### Backend endpoint
- **D-03:** New `POST /user/waitlist` endpoint. Requires authentication (`get_current_user_required`). Sets `pro_waitlist = true` on the user record. Returns success.
- **D-04:** `GET /user/plan` response should include `proWaitlist` boolean so the frontend can check waitlist status on page load.

### Frontend wiring (PricingActions.tsx)
- **D-05:** Replace the `// Phase 3: replace with POST /user/waitlist` stub with an actual `authFetch` call to `POST /user/waitlist`.
- **D-06:** On page load, check waitlist status from the `/user/plan` response. If already waitlisted, show the confirmation message immediately — no "Join Waitlist" button.
- **D-07:** On return visits, the Pro card permanently shows "You're on the list! We'll let you know when Pro launches." instead of the Join button. Same message as initial confirmation.

### Post-signup auto-enroll
- **D-08:** When an anonymous user clicks "Join Waitlist", the AuthModal callback URL includes `?waitlist=1` (e.g., `/pricing?waitlist=1`).
- **D-09:** After signup/signin, PricingActions detects the `waitlist=1` query param + authenticated session and automatically fires `POST /user/waitlist`. User sees confirmation without clicking again.

### Confirmation experience
- **D-10:** Inline text swap in the button area — "You're on the list! We'll let you know when Pro launches." Already stubbed in PricingActions.tsx. No toast, no modal, no redirect.
- **D-11:** Confirmation is identical for first-time join and return visits. Single consistent message.

### Admin visibility
- **D-12:** Add `pro_waitlist` flag to the `GET /admin/users` response. Show a "Waitlisted" badge/filter in the admin users list.
- **D-13:** Add a `waitlistCount` field to the `GET /admin/analytics` response — simple `SELECT COUNT(*) FROM users WHERE pro_waitlist = true`.

### Claude's Discretion
- Error handling for the POST /user/waitlist endpoint (duplicate calls, edge cases)
- Whether to strip the `?waitlist=1` query param from the URL after auto-enrolling
- Exact admin badge styling and filter implementation
- Whether the results page credit exhaustion "Join Pro Waitlist" link should also check/show waitlist status, or just link to /pricing as-is

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Waitlist CTA (frontend)
- `webapp/src/app/pricing/_components/PricingActions.tsx` — Client island with waitlist stub at line 63. Primary file to modify.
- `webapp/src/app/pricing/page.tsx` — Pricing page server component. May need to pass waitlist status as prop.

### User model and auth
- `api/app/models.py` — User class at line 123. Add `pro_waitlist` column here.
- `api/app/routers/auth_routes.py` — Auth endpoints. Reference for `get_current_user_required` pattern.
- `api/app/routers/user_plan.py` — `GET /user/plan` endpoint. Add `proWaitlist` to response.

### Database migrations
- `api/alembic/versions/` — Existing migrations. New migration adds `pro_waitlist` boolean to users table.

### Admin endpoints
- `api/app/routers/admin_users.py` — `GET /admin/users` endpoint. Include `pro_waitlist` in response.
- `api/app/routers/admin_analytics.py` — `GET /admin/analytics` endpoint. Add `waitlistCount`.

### Related components
- `webapp/src/components/AuthModal.tsx` — Auth modal opened for anonymous users. Callback URL needs `?waitlist=1`.
- `webapp/src/lib/auth-fetch.ts` — `authFetch` utility for authenticated API calls.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **PricingActions.tsx**: Already has auth gate logic (`useSession`, `AuthModal` dynamic import), `waitlistConfirmed` state, and inline confirmation message. Just needs backend wiring.
- **authFetch**: Existing utility for authenticated API calls — use for `POST /user/waitlist`.
- **get_current_user_required**: FastAPI dependency for auth — standard pattern across all user endpoints.
- **Alembic migration pipeline**: 10+ existing migrations with consistent patterns (UUID PKs, server defaults).

### Established Patterns
- FastAPI routers with `Depends(get_current_user_required)` + `Depends(get_db)`
- `GET /user/plan` returns user state as JSON — extend with `proWaitlist`
- Admin endpoints query with SQLAlchemy and return paginated results
- Frontend uses `useSession` hook for auth checks, `authFetch` for API calls

### Integration Points
- `PricingActions.tsx` line 63: Replace stub with actual API call
- `user_plan.py` response dict: Add `proWaitlist` key
- `admin_users.py` response: Include `pro_waitlist` field
- `admin_analytics.py` response: Add `waitlistCount` aggregate
- AuthModal `callbackUrl` prop: Change from `/pricing` to `/pricing?waitlist=1` when triggered from waitlist CTA

</code_context>

<specifics>
## Specific Ideas

- Auto-enroll via query param (`?waitlist=1`) so the signup-to-waitlist flow is seamless — user expressed intent, don't make them click again
- Confirmation message matches the existing stub: "You're on the list! We'll let you know when Pro launches."
- Waitlist count on admin analytics gives a quick demand signal without needing to query the DB

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-waitlist*
*Context gathered: 2026-04-16*
