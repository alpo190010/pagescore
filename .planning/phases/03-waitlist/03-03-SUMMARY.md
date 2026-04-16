---
phase: 03-waitlist
plan: "03"
subsystem: admin
tags: [admin, waitlist, backend, frontend, analytics]
dependency_graph:
  requires: ["03-01"]
  provides: ["admin-waitlist-visibility"]
  affects: ["api/app/routers/admin_users.py", "api/app/routers/admin_analytics.py", "webapp/src/app/admin/users/page.tsx", "webapp/src/app/admin/page.tsx", "webapp/src/lib/format.ts"]
tech_stack:
  added: []
  patterns: ["Optional[bool] FastAPI query param", "React conditional badge rendering", "useCallback dependency array extension"]
key_files:
  created: []
  modified:
    - api/app/routers/admin_users.py
    - api/app/routers/admin_analytics.py
    - webapp/src/app/admin/users/page.tsx
    - webapp/src/app/admin/page.tsx
    - webapp/src/lib/format.ts
decisions:
  - "waitlistCount key uses camelCase (per D-13 spec) unlike other snake_case analytics keys"
  - "Waitlist badge uses hardcoded lime-green (#84cc16/#3f6212) to visually distinguish from plan badges that use CSS vars"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-16"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 5
---

# Phase 03 Plan 03: Admin Waitlist Visibility Summary

Admin panel augmented with pro_waitlist filter on GET /admin/users and waitlistCount aggregate in GET /admin/analytics, plus frontend Waitlisted badge column, filter dropdown, and Pro Waitlist stat card.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Admin backend -- users filter and analytics waitlistCount | 228b7cc | api/app/routers/admin_users.py, api/app/routers/admin_analytics.py |
| 2 | Admin frontend -- badge style, users table column/filter, analytics stat card | 0bf118b | webapp/src/lib/format.ts, webapp/src/app/admin/users/page.tsx, webapp/src/app/admin/page.tsx |

## What Was Built

### Backend (Task 1)

**`api/app/routers/admin_users.py`:**
- Added `"pro_waitlist": user.pro_waitlist` to `_user_to_dict` response dict (10 keys total)
- Added `pro_waitlist: Optional[bool] = None` query param to `list_users` signature
- Added `query.filter(User.pro_waitlist == pro_waitlist)` filter block after existing plan_tier filter

**`api/app/routers/admin_analytics.py`:**
- Added `waitlist_count` query using `func.count(User.id).filter(User.pro_waitlist == True)`
- Added `"waitlistCount": waitlist_count` to return dict

### Frontend (Task 2)

**`webapp/src/lib/format.ts`:**
- Added `waitlistBadgeStyle()` returning `{ background: "#84cc16", color: "#3f6212" }` (lime-green)

**`webapp/src/app/admin/users/page.tsx`:**
- Extended `AdminUser` interface with `pro_waitlist: boolean`
- Added `WAITLIST_OPTIONS = ["all", "waitlisted"] as const`
- Added `waitlistFilter` state (default `"all"`)
- Extended reset-on-filter `useEffect` deps to include `waitlistFilter`
- Added `params.set("pro_waitlist", "true")` when `waitlistFilter === "waitlisted"`
- Extended `useCallback` dep array with `waitlistFilter`
- Extended empty-state condition with `waitlistFilter !== "all"`
- Added waitlist filter `<Select>` dropdown with `aria-label="Filter by waitlist"`
- Added `<th>Waitlist</th>` column header
- Added conditional `<Badge style={waitlistBadgeStyle()}>Waitlisted</Badge>` cell per user row
- Updated import to include `waitlistBadgeStyle`

**`webapp/src/app/admin/page.tsx`:**
- Extended `AnalyticsData` interface with `waitlistCount: number`
- Added `<StatCard label="Pro Waitlist" value={fmtNum(data.waitlistCount)} />`
- Updated skeleton grid from `[1, 2, 3]` to `[1, 2, 3, 4]`

## Decisions Made

1. **waitlistCount camelCase:** Key name matches D-13 spec exactly. Intentional mismatch with other snake_case analytics keys — frontend AnalyticsData interface matches.
2. **Hardcoded lime-green colors:** Waitlist badge uses `#84cc16`/`#3f6212` (not CSS vars) to visually distinguish from plan/role badges that use design system vars. Per UI-SPEC.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data flows are wired. `waitlistCount` and `pro_waitlist` come from the real DB via the augmented endpoints.

## Self-Check: PASSED

- api/app/routers/admin_users.py: modified, 4 occurrences of pro_waitlist
- api/app/routers/admin_analytics.py: modified, 1 occurrence of waitlistCount
- webapp/src/lib/format.ts: modified, waitlistBadgeStyle exported
- webapp/src/app/admin/users/page.tsx: modified, Waitlisted badge and filter present
- webapp/src/app/admin/page.tsx: modified, Pro Waitlist stat card present
- Commit 228b7cc: Task 1 backend
- Commit 0bf118b: Task 2 frontend
