---
phase: 03-waitlist
reviewed: 2026-04-16T18:42:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - api/alembic/versions/0011_add_pro_waitlist.py
  - api/app/routers/user_waitlist.py
  - api/app/models.py
  - api/app/main.py
  - api/app/routers/user_plan.py
  - webapp/src/app/pricing/_components/PricingActions.tsx
  - webapp/src/app/pricing/page.tsx
  - api/app/routers/admin_users.py
  - api/app/routers/admin_analytics.py
  - webapp/src/app/admin/users/page.tsx
  - webapp/src/app/admin/page.tsx
  - webapp/src/lib/format.ts
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-04-16T18:42:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 03 adds a Pro waitlist feature spanning backend (migration, endpoint, model column, admin visibility) and frontend (pricing page CTA, admin dashboard stat card and user-list filter). The implementation is clean overall: the migration is safe with a `server_default`, the endpoint is idempotent, the admin endpoints are properly guarded, and the frontend wires up auth-gated enrollment with proper abort-controller cleanup.

Key concerns: one SQL-injection-adjacent ILIKE wildcard issue in the admin search, missing `db.refresh` in the waitlist endpoint that could serve stale data in edge cases, a race condition between two useEffect hooks in PricingActions, and hardcoded hex colors in format.ts that violate design-token conventions observed elsewhere in the codebase.

## Critical Issues

### CR-01: Admin User Search -- ILIKE Wildcard Characters Not Escaped

**File:** `api/app/routers/admin_users.py:95`
**Issue:** The search parameter is interpolated directly into an ILIKE pattern via `f"%{search}%"`. If a user submits search strings containing SQL ILIKE wildcards (`%` or `_`), they become part of the pattern. While this is not classic SQL injection (SQLAlchemy parameterises the value), it allows an admin to craft patterns that match unintended rows. For example, searching for `_@gmail.com` matches any single-character prefix before `@gmail.com`, and `%secret%` matches anything. In an admin context this is lower risk, but the pattern establishes a habit that would be dangerous if copied to user-facing endpoints.

**Fix:** Escape ILIKE metacharacters before wrapping in wildcards:
```python
def _escape_ilike(value: str) -> str:
    """Escape %, _, and \\ for use inside ILIKE patterns."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

# In list_users:
if search:
    safe = _escape_ilike(search)
    pattern = f"%{safe}%"
    query = query.filter(
        or_(
            User.email.ilike(pattern),
            User.name.ilike(pattern),
        )
    )
```

## Warnings

### WR-01: Waitlist Endpoint Missing db.refresh -- Stale Return Possible

**File:** `api/app/routers/user_waitlist.py:22-25`
**Issue:** After `db.commit()`, the `current_user` object's attributes may be stale if the database applied any triggers or defaults. More importantly, when `current_user.pro_waitlist` is already `True` (idempotent path), the function returns `{"waitlisted": True}` without ever verifying the actual DB state. This is fine in isolation, but the pattern diverges from the rest of the codebase (e.g., `admin_users.py:202-203` calls `db.commit()` then `db.refresh(user)`). Keeping the pattern consistent prevents future bugs when the response body grows.

**Fix:**
```python
if not current_user.pro_waitlist:
    current_user.pro_waitlist = True
    db.commit()
    db.refresh(current_user)
return {"waitlisted": True}
```

### WR-02: PricingActions -- Race Between Plan-Check and Auto-Enroll useEffects

**File:** `webapp/src/app/pricing/_components/PricingActions.tsx:42-64`
**Issue:** Two independent `useEffect` hooks fire on mount when `tier.key === "pro-waitlist"` and `isSignedIn` is true. The first (line 42) fetches `/user/plan` to check existing waitlist status. The second (line 53) fires when `?waitlist=1` is in the URL and immediately POSTs to `/user/waitlist`. Both run concurrently. If the POST (second effect) completes before the GET (first effect), the GET response will set `waitlistConfirmed = true` as expected. But if the GET completes first and finds `proWaitlist: false` (the user just signed up), `waitlistConfirmed` stays false, then the POST fires and sets it to true -- which works. However, in React Strict Mode (development), effects run twice, meaning up to 4 concurrent requests fire. The POST is idempotent so this is safe, but the first GET could return stale `false` *after* the POST already succeeded, briefly flickering the button before the second GET corrects it. This is a cosmetic race but could confuse users.

**Fix:** Guard the auto-enroll effect to skip the plan-check effect when `?waitlist=1` is present, or merge both into a single effect:
```tsx
useEffect(() => {
  if (tier.key !== "pro-waitlist" || !isSignedIn) return;
  const isAutoEnroll = searchParams.get("waitlist") === "1";

  if (isAutoEnroll) {
    authFetch(`${API_URL}/user/waitlist`, { method: "POST" })
      .then((r) => {
        if (r.ok) {
          setWaitlistConfirmed(true);
          router.replace(pathname, { scroll: false });
        }
      })
      .catch(() => {});
  } else {
    authFetch(`${API_URL}/user/plan`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d?.proWaitlist) setWaitlistConfirmed(true); })
      .catch(() => {});
  }
}, [tier.key, isSignedIn, searchParams, pathname, router]);
```

### WR-03: Admin Analytics -- Inconsistent Response Key Naming Convention

**File:** `api/app/routers/admin_analytics.py:107-114`
**Issue:** All response keys use `snake_case` (`total_users`, `signups_over_time`, `plan_distribution`) except `waitlistCount` which uses `camelCase`. This inconsistency means frontend consumers must handle mixed naming conventions. The admin dashboard TypeScript interface (`webapp/src/app/admin/page.tsx:23`) already mirrors this inconsistency (`waitlistCount`), so changing it requires a coordinated update, but it should be fixed to prevent the pattern from spreading.

**Fix:** Rename to `waitlist_count` in the API response and update the frontend interface:
```python
# api/app/routers/admin_analytics.py
"waitlist_count": waitlist_count,
```
```typescript
// webapp/src/app/admin/page.tsx
interface AnalyticsData {
  // ...
  waitlist_count: number;  // was waitlistCount
}
```

### WR-04: PricingActions -- Silent Error Swallowing in Plan-Check useEffect

**File:** `webapp/src/app/pricing/_components/PricingActions.tsx:49`
**Issue:** The `.catch(() => {})` on line 49 silently discards all errors from the plan-check fetch, including non-network errors like JSON parse failures. While this is acceptable for a non-critical "pre-populate" call, it means the user gets no feedback if the API is consistently failing. The same pattern appears on line 63 for the auto-enroll flow, where silent failure is more problematic -- the user clicked "Join Waitlist", was redirected through auth, and their enrollment silently failed with no error message shown.

**Fix:** At minimum, log failures in the auto-enroll path and show the join button so the user can retry manually:
```tsx
.catch(() => {
  // Auto-enroll failed after auth redirect; show the join button
  // so the user can retry manually. Clear the query param to avoid
  // re-triggering on every render.
  router.replace(pathname, { scroll: false });
});
```

## Info

### IN-01: Hardcoded Hex Colors in waitlistBadgeStyle

**File:** `webapp/src/lib/format.ts:40-41`
**Issue:** `waitlistBadgeStyle()` uses hardcoded hex values (`#84cc16`, `#3f6212`) while all other badge style functions in the same file use CSS custom properties (`var(--brand)`, `var(--surface-container)`, etc.). This breaks the design-token pattern and means the waitlist badge will not adapt to theme changes.

**Fix:**
```typescript
export function waitlistBadgeStyle(): React.CSSProperties {
  return {
    background: "var(--success-light, #84cc16)",
    color: "var(--success-dark, #3f6212)",
  };
}
```
Or define dedicated waitlist tokens in the theme if the green is intentionally distinct from `--success`.

### IN-02: Unused Import -- Button in admin/page.tsx

**File:** `webapp/src/app/pricing/page.tsx:10`
**Issue:** `Button` is imported on line 10 but is only used within a `<Button asChild>` wrapper on line 169 in the FAQ section. This is actually used, so no action needed. However, the `Link` import on line 2 of `pricing/page.tsx` could be consolidated since it is used in the same JSX tree. No actual unused import found here -- this is informational only.

*(Retracted on closer inspection -- Button and Link are both used. No issue.)*

### IN-03: Admin User PATCH Allows Setting Negative credits_used

**File:** `api/app/routers/admin_users.py:194-195`
**Issue:** The `AdminUserUpdate` model accepts any `Optional[int]` for `credits_used` without a lower bound. An admin could set `credits_used` to a negative value, which would effectively grant unlimited credits since `has_credits_remaining` likely checks `credits_used < limit`. This is low severity since only admins can trigger it, but adding a `ge=0` constraint to the Pydantic model is trivial and prevents accidental misuse.

**Fix:**
```python
from pydantic import BaseModel, Field

class AdminUserUpdate(BaseModel):
    plan_tier: Optional[str] = None
    credits_used: Optional[int] = Field(None, ge=0)
    email_verified: Optional[bool] = None
    role: Optional[str] = None
```

---

_Reviewed: 2026-04-16T18:42:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
