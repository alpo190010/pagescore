# Phase 3: Waitlist - Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 9 new/modified files
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `api/alembic/versions/0011_add_pro_waitlist.py` | migration | batch | `api/alembic/versions/0006_add_role_column.py` | exact |
| `api/app/models.py` | model | CRUD | self (existing User class at line 123) | exact |
| `api/app/routers/user_waitlist.py` | controller | request-response | `api/app/routers/user_plan.py` | exact |
| `api/app/main.py` | config | request-response | self (existing include_router block lines 73–86) | exact |
| `api/app/routers/user_plan.py` | controller | request-response | self (existing return dict lines 25–42) | exact |
| `api/app/routers/admin_users.py` | controller | CRUD | self (existing `_user_to_dict` + filter pattern) | exact |
| `api/app/routers/admin_analytics.py` | controller | CRUD | self (existing `func.count` aggregate pattern) | exact |
| `webapp/src/app/pricing/_components/PricingActions.tsx` | component | request-response | `webapp/src/app/scan/[domain]/page.tsx` | role-match |
| `webapp/src/app/admin/users/page.tsx` | component | request-response | self (existing `Badge`, `Select`, filter pattern) | exact |

---

## Pattern Assignments

### `api/alembic/versions/0011_add_pro_waitlist.py` (migration, batch)

**Analog:** `api/alembic/versions/0006_add_role_column.py`

**Full file structure pattern** (lines 1–31):
```python
"""Add pro_waitlist column to users

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "pro_waitlist",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "pro_waitlist")
```

**Key detail:** `server_default=sa.text("false")` is mandatory — makes the column NOT NULL while safely defaulting all existing rows. Matches `email_verified` column pattern in `models.py` line 132 and `role` column in migration 0006.

**Verified chain:** `down_revision = "0010"` confirmed via `alembic heads` output — `0010` is the current head.

---

### `api/app/models.py` — User class addition (model, CRUD)

**Analog:** Existing `User` class at lines 123–151. Match existing column style exactly.

**Column definition pattern to copy** (lines 132, 141, 150 — Boolean and Text with server_default):
```python
# Line 132 — Boolean column with server_default pattern:
email_verified = Column(Boolean, nullable=False, server_default=text("false"))

# Line 141 — Text column with server_default pattern:
plan_tier = Column(Text, server_default="free")

# Line 150 — Text column with nullable=False:
role = Column(Text, server_default="user", nullable=False)
```

**New column to add** after line 150 (the `role` line), before the closing of the User class:
```python
# --- Waitlist ---
pro_waitlist = Column(Boolean, nullable=False, server_default=text("false"))
```

**Import check:** `Boolean`, `text` are already imported at the top of `models.py` (confirmed by `email_verified` and `id` column usage).

---

### `api/app/routers/user_waitlist.py` (controller, request-response) — NEW FILE

**Analog:** `api/app/routers/user_plan.py` (lines 1–42)

**Imports pattern** (from `user_plan.py` lines 1–14):
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user_required
from app.database import get_db
from app.models import User
```

**Auth pattern** (from `user_plan.py` lines 19–22):
```python
router = APIRouter()

@router.post("/user/waitlist", status_code=200)
def join_waitlist(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
```

**Core pattern — idempotent update** (modeled on `auth_routes.py` lines 177–182, db.commit pattern):
```python
    """Record the authenticated user's Pro waitlist interest."""
    # Idempotent: safe to call multiple times (handles React Strict Mode double-invoke)
    if not current_user.pro_waitlist:
        current_user.pro_waitlist = True
        db.commit()
    return {"waitlisted": True}
```

**Error handling:** No try/except needed — `get_current_user_required` raises 401 automatically if unauthenticated (verified in `auth_routes.py` dependency chain). DB errors propagate to the global unhandled exception handler in `main.py` lines 49–58 which returns clean JSON.

---

### `api/app/main.py` — Router registration (config, request-response)

**Analog:** Existing import + include_router block at lines 16–86.

**Import pattern to copy** (lines 24–26, style for user_plan and auth routers):
```python
from app.routers.user_plan import router as user_plan_router
from app.routers.auth_routes import router as auth_router
```

**New import to add** (after line 25, `user_plan` import):
```python
from app.routers.user_waitlist import router as user_waitlist_router
```

**include_router pattern** (lines 81–82):
```python
app.include_router(user_plan_router)
app.include_router(user_scans_router)
```

**New registration to add** (after `user_plan_router` line 81):
```python
app.include_router(user_waitlist_router)
```

---

### `api/app/routers/user_plan.py` — Response augmentation (controller, request-response)

**Analog:** Self. Add one key to the existing return dict.

**Existing return dict** (lines 25–42):
```python
    return {
        "userId": str(current_user.id),
        "plan": current_user.plan_tier,
        "creditsUsed": current_user.credits_used,
        "creditsLimit": get_credits_limit(current_user.plan_tier),
        "creditsResetAt": (
            current_user.credits_reset_at.isoformat()
            if current_user.credits_reset_at
            else None
        ),
        "currentPeriodEnd": (
            current_user.current_period_end.isoformat()
            if current_user.current_period_end
            else None
        ),
        "hasCreditsRemaining": has_credits_remaining(current_user),
        "customerPortalUrl": current_user.lemon_customer_portal_url,
    }
```

**Addition** — append before the closing `}`:
```python
        "proWaitlist": current_user.pro_waitlist,
```

**Key naming convention:** camelCase for JSON response keys (matches all existing keys in this file). SQLAlchemy column is `pro_waitlist` (snake_case); JSON key is `proWaitlist` (camelCase).

---

### `api/app/routers/admin_users.py` — Two changes (controller, CRUD)

**Analog:** Self. Two separate modifications.

#### Change 1: `_user_to_dict` extension

**Existing `_user_to_dict`** (lines 45–57):
```python
def _user_to_dict(user: User) -> dict:
    """Serialise a User row to a dict safe for JSON responses (no password_hash)."""
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "plan_tier": user.plan_tier,
        "credits_used": user.credits_used,
        "email_verified": user.email_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }
```

**Addition** — append `pro_waitlist` before closing `}`:
```python
        "pro_waitlist": user.pro_waitlist,
```

#### Change 2: `list_users` filter parameter

**Existing filter pattern** (lines 80–105):
```python
@router.get("/admin/users")
def list_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    plan_tier: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin_user: User = Depends(get_current_user_admin),
    db: Session = Depends(get_db),
):
    ...
    if role:
        query = query.filter(User.role == role)

    if plan_tier:
        query = query.filter(User.plan_tier == plan_tier)
```

**Additions** — new query param and filter block, following the same pattern as `role` and `plan_tier`:
```python
# In function signature, after plan_tier param:
    pro_waitlist: Optional[bool] = None,

# In filter block, after plan_tier filter:
    if pro_waitlist is not None:
        query = query.filter(User.pro_waitlist == pro_waitlist)
```

---

### `api/app/routers/admin_analytics.py` — Response augmentation (controller, CRUD)

**Analog:** Self. Add one aggregate query and one response key.

**Existing aggregate pattern** (lines 45, 64, 97 — three examples):
```python
# Scalar count pattern (line 45):
total_users = db.query(func.count(User.id)).scalar() or 0

# Filtered count pattern (line 64):
total_scans = db.query(func.count(ProductAnalysis.id)).scalar() or 0

# Sum pattern (line 97):
total_credits_used = db.query(func.sum(User.credits_used)).scalar() or 0
```

**New aggregate to add** (before the `return` statement):
```python
    # --- Waitlist count ---
    waitlist_count = (
        db.query(func.count(User.id))
        .filter(User.pro_waitlist == True)
        .scalar()
    ) or 0
```

**Existing return dict** (lines 99–106):
```python
    return {
        "total_users": total_users,
        "signups_over_time": signups_over_time,
        "total_scans": total_scans,
        "scans_over_time": scans_over_time,
        "plan_distribution": plan_distribution,
        "total_credits_used": total_credits_used,
    }
```

**Addition** — append before closing `}`:
```python
        "waitlistCount": waitlist_count,
```

**Key naming note:** Existing keys use `snake_case`. New `waitlistCount` uses camelCase per D-13 spec. Either convention is defensible — match D-13 exactly to avoid frontend/backend mismatch.

---

### `webapp/src/app/pricing/_components/PricingActions.tsx` (component, request-response)

**Analog:** `webapp/src/app/scan/[domain]/page.tsx` for `useSearchParams` + `router.replace` pattern; self for existing state/JSX structure.

**Existing imports** (lines 1–11):
```typescript
"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import dynamic from "next/dynamic";
import Link from "next/link";
import Button from "@/components/ui/Button";

const AuthModal = dynamic(() => import("@/components/AuthModal"), {
  ssr: false,
});
```

**New imports to add** (extend the import block):
```typescript
import { useEffect } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { authFetch } from "@/lib/auth-fetch";
import { API_URL } from "@/lib/api";
```

**Note:** Replace `import { useState }` with `import { useState, useEffect }`.

**Existing hook setup** (lines 27–31):
```typescript
  const { data: session } = useSession();
  const isSignedIn = !!session?.user;

  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [waitlistConfirmed, setWaitlistConfirmed] = useState(false);
```

**New hooks to add** after existing hook setup:
```typescript
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
```

**Effect 1 — on-mount status check pattern** (modeled on admin/page.tsx `fetchAnalytics` useEffect + authFetch pattern, lines 35–55):
```typescript
  // On mount: check /user/plan for existing waitlist status
  useEffect(() => {
    if (tier.key !== "pro-waitlist" || !isSignedIn) return;
    authFetch(`${API_URL}/user/plan`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d?.proWaitlist) setWaitlistConfirmed(true);
      })
      .catch(() => {});
  }, [tier.key, isSignedIn]);
```

**Effect 2 — query-param auto-enroll pattern** (modeled on `scan/[domain]/page.tsx` lines 40–46, router.replace pattern):
```typescript
  // On mount: auto-enroll when redirected back with ?waitlist=1 after signup
  useEffect(() => {
    if (tier.key !== "pro-waitlist" || !isSignedIn) return;
    if (searchParams.get("waitlist") !== "1") return;
    authFetch(`${API_URL}/user/waitlist`, { method: "POST" })
      .then((r) => {
        if (r.ok) {
          setWaitlistConfirmed(true);
          router.replace(pathname, { scroll: false });
        }
      })
      .catch(() => {});
  }, [isSignedIn, searchParams, pathname, router, tier.key]);
```

**Button onClick replacement** (lines 58–65 — replace the stub comment):
```typescript
          onClick={() => {
            if (!isSignedIn) {
              setAuthModalOpen(true);
              return;
            }
            // Replace Phase 3 stub: fire real API call
            authFetch(`${API_URL}/user/waitlist`, { method: "POST" })
              .then((r) => {
                if (r.ok) setWaitlistConfirmed(true);
              })
              .catch(() => {});
          }}
```

**AuthModal callbackUrl change** (line 75 — change from `/pricing` to `/pricing?waitlist=1`):
```typescript
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        callbackUrl="/pricing?waitlist=1"
      />
```

**Suspense boundary note:** `useSearchParams` in Next.js App Router requires the component to be wrapped in `<Suspense>`. In `pricing/page.tsx` line 148, wrap the `<PricingActions>` usage:
```tsx
import { Suspense } from "react";
// ...
<Suspense fallback={null}>
  <PricingActions tier={{ key: tier.key, ctaLabel: tier.ctaLabel }} />
</Suspense>
```

---

### `webapp/src/app/admin/users/page.tsx` — Three changes (component, request-response)

**Analog:** Self. Three modifications following existing patterns.

#### Change 1: `AdminUser` interface extension

**Existing interface** (lines 19–29):
```typescript
interface AdminUser {
  id: string;
  email: string;
  name: string | null;
  role: string;
  plan_tier: string;
  credits_used: number;
  email_verified: boolean;
  created_at: string | null;
  updated_at: string | null;
}
```

**Addition** — append before closing `}`:
```typescript
  pro_waitlist: boolean;
```

#### Change 2: Filter Select for waitlist

**Existing filter constants and Select pattern** (lines 38–39, 137–148):
```typescript
const PLAN_OPTIONS = ["all", "free", "pro"] as const;
// ...
<Select
  value={planFilter}
  onChange={(e) => setPlanFilter(e.target.value)}
  aria-label="Filter by plan"
>
  {PLAN_OPTIONS.map((p) => (
    <option key={p} value={p}>
      {p === "all" ? "All plans" : p.charAt(0).toUpperCase() + p.slice(1)}
    </option>
  ))}
</Select>
```

**New constant and state** (add after `PLAN_OPTIONS` line 39):
```typescript
const WAITLIST_OPTIONS = ["all", "waitlisted"] as const;
```

**New state** (add after `planFilter` state line 49):
```typescript
  const [waitlistFilter, setWaitlistFilter] = useState<string>("all");
```

**New Select** (add after the plan `Select` block, lines 137–148):
```typescript
<Select
  value={waitlistFilter}
  onChange={(e) => setWaitlistFilter(e.target.value)}
  aria-label="Filter by waitlist"
>
  {WAITLIST_OPTIONS.map((w) => (
    <option key={w} value={w}>
      {w === "all" ? "All users" : "Waitlisted"}
    </option>
  ))}
</Select>
```

**fetchUsers params addition** (add alongside existing filter params at lines 74–76):
```typescript
      if (waitlistFilter === "waitlisted") params.set("pro_waitlist", "true");
```

**useEffect dependency** — add `waitlistFilter` to the reset effect (lines 63–65):
```typescript
  useEffect(() => {
    setPage(1);
  }, [roleFilter, planFilter, waitlistFilter]);
```

**fetchUsers useCallback dependency** — add `waitlistFilter` to deps array (line 90).

#### Change 3: Waitlisted badge in user table rows

**Existing Badge pattern** (lines 217–224):
```typescript
                    <td className="px-4 py-3">
                      <Badge role={user.role}>
                        {user.role}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge plan={user.plan_tier}>
                        {user.plan_tier}
                      </Badge>
                    </td>
```

**New column header** (add to `<thead>` after "Plan" th, lines 192–194):
```tsx
                  <th className="text-left px-4 py-3 font-semibold text-[var(--text-secondary)]">
                    Waitlist
                  </th>
```

**New column cell** (add to `<tr>` after plan Badge cell):
```tsx
                    <td className="px-4 py-3">
                      {user.pro_waitlist && (
                        <Badge>Waitlisted</Badge>
                      )}
                    </td>
```

---

## Shared Patterns

### Authentication Dependency
**Source:** `api/app/routers/user_plan.py` lines 19–22 and `api/app/routers/auth_routes.py` line 10
**Apply to:** `user_waitlist.py` (new file)
```python
from app.auth import get_current_user_required
# ...
current_user: User = Depends(get_current_user_required)
```
Returns 401 automatically if no valid JWT — no explicit error handling needed in the endpoint body.

### Admin Authentication Dependency
**Source:** `api/app/routers/admin_users.py` lines 22, 86
**Apply to:** All admin endpoint modifications (already present — no change needed)
```python
from app.auth import get_current_user_admin
# ...
admin_user: User = Depends(get_current_user_admin)
```

### SQLAlchemy Commit Pattern
**Source:** `api/app/routers/auth_routes.py` lines 119, 178–181
**Apply to:** `user_waitlist.py`
```python
# Mutate the ORM object, then commit — no explicit flush needed
user.some_field = new_value
db.commit()
```
No `db.refresh()` needed when you only return a simple dict (not the ORM object).

### authFetch Pattern
**Source:** `webapp/src/lib/auth-fetch.ts` lines 56–79
**Apply to:** `PricingActions.tsx` (all three call sites)
```typescript
// POST call — method must be explicit, body optional
authFetch(`${API_URL}/user/waitlist`, { method: "POST" })
  .then((r) => { if (r.ok) { /* success path */ } })
  .catch(() => { /* silent fallback — degrade gracefully */ });

// GET call — no method needed
authFetch(`${API_URL}/user/plan`)
  .then((r) => r.ok ? r.json() : null)
  .then((d) => { /* use data */ })
  .catch(() => {});
```

### Router Registration
**Source:** `api/app/main.py` lines 16–26, 73–86
**Apply to:** `main.py` for `user_waitlist_router`
```python
# Import line (add with other user_ routers, lines 24–25):
from app.routers.user_waitlist import router as user_waitlist_router

# Registration line (add after user_plan_router, line 81):
app.include_router(user_waitlist_router)
```

### Admin `func.count` Scalar Pattern
**Source:** `api/app/routers/admin_analytics.py` line 45
**Apply to:** `admin_analytics.py` `waitlistCount` addition
```python
# Always use `.scalar() or 0` — scalar() returns None when table is empty
total_users = db.query(func.count(User.id)).scalar() or 0
```

---

## No Analog Found

None — all files have exact or role-match analogs within the codebase.

---

## Metadata

**Analog search scope:** `api/app/routers/`, `api/alembic/versions/`, `api/app/models.py`, `api/app/main.py`, `webapp/src/app/pricing/`, `webapp/src/app/admin/`, `webapp/src/app/scan/`, `webapp/src/lib/`
**Files read:** 14 source files
**Pattern extraction date:** 2026-04-16
