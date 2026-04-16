# Phase 2: Paywall Gates - Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 7 files to modify + 1 to delete
**Analogs found:** 7 / 7 (all files are self-analogs — this phase modifies existing files, not creates new ones)

---

## File Classification

| File | Action | Role | Data Flow | Closest Analog | Match Quality |
|------|--------|------|-----------|----------------|---------------|
| `webapp/src/app/analyze/page.tsx` | modify | page/controller | request-response + event-driven | itself (self-modification) | exact |
| `webapp/src/lib/analysis/conversion-model.ts` | modify | utility | transform | itself (single-function change) | exact |
| `webapp/src/lib/analysis/__tests__/tier-gating.test.ts` | modify | test | transform | itself (assertion flip) | exact |
| `webapp/src/components/analysis/IssueCard.tsx` | modify | component | request-response | itself (locked branch redesign) | exact |
| `webapp/src/components/analysis/CTACard.tsx` | modify | component | request-response | itself (copy + prop changes) | exact |
| `webapp/src/components/AuthModal.tsx` | modify | component | request-response | itself (add `initialMode` prop) | exact |
| `webapp/src/components/PaywallModal.tsx` | delete | component | — | `AuthModal.tsx` (replacement) | role-match |
| `api/app/routers/analyze.py` | modify | router/controller | request-response | itself (rate limit addition) | exact |

---

## Pattern Assignments

### `webapp/src/app/analyze/page.tsx` (page, request-response + event-driven)

**Analog:** itself — the authenticated branch (lines 93–157) is the pattern to extend to anonymous users.

**Imports to clean up** (lines 9–31 — remove `PaywallModal`, `SAMPLE_SCAN`; keep everything else):
```typescript
// REMOVE these two lines:
const PaywallModal = dynamic(() => import("@/components/PaywallModal"), { ssr: false });
import { SAMPLE_SCAN } from "@/lib/sample-data";

// KEEP: AuthModal dynamic import (line 9)
const AuthModal = dynamic(() => import("@/components/AuthModal"), { ssr: false });
```

**State to remove** (lines 67–68, 198–201):
```typescript
// REMOVE — PaywallModal state (lines 67-68):
const [paywallOpen, setPaywallOpen] = useState(false);
const [paywallLeakKey, setPaywallLeakKey] = useState<string | null>(null);

// REMOVE — closePaywall callback (lines 198-201):
const closePaywall = useCallback(() => {
  setPaywallOpen(false);
  setPaywallLeakKey(null);
}, []);
```

**Derived state to simplify** (lines 80–86 — `isShallow`/`hasFullAccess` become `isAnonymous`):
```typescript
// CURRENT (lines 80-86):
const planTier: PlanTier = (planData?.plan as PlanTier) ?? "free";
const isShallow = planTier === "free";
const hasFullAccess = planTier === "pro";

// TARGET: replace isShallow/hasFullAccess with single auth-based flag
const planTier: PlanTier = (planData?.plan as PlanTier) ?? "free";
const isAnonymous = status === "unauthenticated";
// hasFullAccess: all authenticated users unlock everything (D-07)
```

**Anonymous scan path** — replace lines 159–173 (SAMPLE_SCAN timer) with real fetch:
```typescript
// TARGET anonymous branch (replaces lines 159-173)
// Pattern: mirrors authenticated branch structure (lines 93-157) but without authFetch
if (status === "unauthenticated") {
  const controller = new AbortController();
  abortRef.current = controller;

  fetch(`${API_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (res.status === 429) throw new Error(getUserFriendlyError(429));
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error((d as { error?: string }).error || `Analysis failed (${res.status})`);
      }
      return res.json();
    })
    .then((data) => {
      setResult(parseAnalysisResponse(data as Record<string, unknown>));
      setLoading(false);
      captureEvent("anon_scan_completed", { url });
    })
    .catch((err: unknown) => {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : getUserFriendlyError(0));
      setLoading(false);
    });

  return () => { controller.abort(); };
}
```

**dimAccess calculation** — update line 352 (replace `isTeaser` with `isAnonymous`):
```typescript
// CURRENT (line 352):
const dimAccess = isTeaser ? "locked" as const : getDimensionAccess(planTier, leak.key);

// TARGET:
const dimAccess = isAnonymous ? "locked" as const : getDimensionAccess(planTier, leak.key);
```

**CTACard render** — update lines 367–385 (anonymous-only, remove isShallow branch):
```typescript
// TARGET: only show CTACard for anonymous users (D-08)
{isAnonymous && (
  <CTACard
    variant="full"
    leaksCount={leaks.length}
    animationDelay={leaks.length * 80}
    onClick={() => setAuthModalOpen(true)}
  />
)}
```

**Bottom banner section** — remove lines 391–418 entirely (D-10: delete the gradient banner for anonymous). The "Scan Another" section for authenticated users (lines 420–428) stays intact.

**Credit exhaustion screen** — update lines 258–269 (D-14: replace PaywallModal open with /pricing link):
```typescript
// CURRENT (lines 259-269): onClick opens setPaywallOpen(true)
// TARGET: direct link to /pricing
<Button
  variant="gradient"
  size="md"
  shape="pill"
  onClick={() => router.push("/pricing")}
  className="text-sm"
>
  Join Pro Waitlist
</Button>
```

**PaywallModal JSX** — remove both instances:
- Lines 281–285: `<PaywallModal isOpen={paywallOpen} onClose={closePaywall} />` inside credit exhaustion screen
- Lines 469–472: `<PaywallModal isOpen={paywallOpen} onClose={closePaywall} />` at bottom of main render

**openIssueModal callback** — update lines 208–223 (replace `isTeaser` + PaywallModal path with AuthModal):
```typescript
// TARGET: anonymous → AuthModal, authenticated → expandable (no paywall)
const openIssueModal = useCallback((leak: LeakCard) => {
  if (isAnonymous) {
    setAuthModalOpen(true);
    captureEvent("locked_card_clicked", { category: leak.key, trigger: "issue_card" });
    return;
  }
  captureEvent("issue_clicked", { category: leak.key, impact: leak.impact, plan: planTier });
}, [isAnonymous, planTier]);
```

**AuthModal** — update props to pass `initialMode="signup"` for anonymous entry points:
```typescript
// TARGET (was lines 475-479):
<AuthModal
  isOpen={authModalOpen}
  onClose={() => setAuthModalOpen(false)}
  callbackUrl={authCallbackUrl}
  initialMode="signup"
/>
```

---

### `webapp/src/lib/analysis/conversion-model.ts` (utility, transform)

**Analog:** itself — single function change at lines 51–54.

**Core pattern — the function to change** (lines 51–54):
```typescript
// CURRENT:
export function getDimensionAccess(plan: PlanTier, _dimensionKey: string): DimensionAccess {
  if (plan === "pro") return "unlocked";
  return "locked";
}

// TARGET (D-07): all authenticated users unlock everything
export function getDimensionAccess(plan: PlanTier, _dimensionKey: string): DimensionAccess {
  // All authenticated users (free or pro) see full recommendations.
  // Anonymous gate is enforced at call sites via isAnonymous flag, not here.
  return "unlocked";
}
```

Note: `plan` parameter kept in signature to avoid breaking call sites. The anonymous gate lives in `analyze/page.tsx` line 352, not in this function.

---

### `webapp/src/lib/analysis/__tests__/tier-gating.test.ts` (test, transform)

**Analog:** itself — assertions flip from `"locked"` to `"unlocked"` for free plan.

**Full file pattern** (lines 1–39) — all three assertion changes:
```typescript
// CHANGE line 15: describe text update
it("returns unlocked for all 18 active dimensions", () => {   // was "returns locked..."

// CHANGE line 17: assertion inversion
expect(getDimensionAccess("free", key)).toBe("unlocked" satisfies DimensionAccess);  // was "locked"

// CHANGE line 31: unknown key free plan assertion
it("returns unlocked for free plan", () => {                  // was "returns locked..."
  expect(getDimensionAccess("free", "nonexistent")).toBe("unlocked");  // was "locked"
});
```

Run command to validate immediately after change:
```bash
cd webapp && npx vitest run src/lib/analysis/__tests__/tier-gating.test.ts
```

---

### `webapp/src/components/analysis/IssueCard.tsx` (component, request-response)

**Analog:** itself — the locked branch within the existing card (lines 1337–1433).

**Props interface** (lines 61–72) — no changes needed, `locked` prop already exists:
```typescript
interface IssueCardProps {
  leak: LeakCard;
  index: number;
  onClick: () => void;
  variant?: "compact" | "full";
  expandable?: boolean;
  locked?: boolean;      // already exists
  signals?: DimensionSignals;
}
```

**Outer wrapper div** (line 1364) — MUST be preserved identically for grid layout:
```typescript
// DO NOT change this div — grid layout depends on it
<div
  className={`contain-card group text-left bg-[var(--surface)] rounded-2xl ${full ? "p-6 sm:p-7" : "p-5 sm:p-6"} flex flex-col border border-[var(--outline-variant)]/20 ${expanded ? "border-[var(--brand)]/40" : "hover:border-[var(--brand)]/40"} transition-all duration-300 ${expanded ? "" : "hover:-translate-y-1"} hover:shadow-[var(--shadow-card-hover)]`}
  style={{
    boxShadow: "var(--shadow-subtle)",
    animation: `fade-in-up 400ms var(--ease-out-quart) ${index * 80}ms both`,
  }}
>
```

**Current locked rendering** (lines 1380–1433) — the `Button` wrapping the card body shows full content + lock icon only at the bottom. Target redesign collapses to score + name + impact + lock only:

```typescript
// CURRENT: locked card renders full space-y-5 layout (Icon+Score, Category+Problem, Revenue+Lock)
// TARGET: locked card renders collapsed view (Name+Score header, impact badge, lock + CTA text)
// Replace the Button contents when locked=true with:
{locked ? (
  <div className={full ? "space-y-4" : "space-y-3"}>
    {/* Icon + Score (keep identical to unlocked) */}
    <div className="flex justify-between items-start">
      <div className={`${full ? "w-12 h-12" : "w-11 h-11"} bg-[var(--surface-container-high)] rounded-2xl flex items-center justify-center text-[var(--on-surface-variant)] group-hover:text-[var(--brand)] group-hover:scale-110 transition-all duration-300`}>
        {CATEGORY_SVG[leak.key] || CATEGORY_SVG.title}
      </div>
      <div className="text-right">
        <div className="text-[9px] font-bold text-[var(--on-surface-variant)] tracking-[0.15em] uppercase">Score</div>
        <div
          className="text-xl font-extrabold font-display"
          style={{ color: impactStyle.textColor, fontVariantNumeric: "tabular-nums" }}
        >
          {leak.catScore}<span className="text-xs font-semibold opacity-50">/100</span>
        </div>
      </div>
    </div>

    {/* Dimension name only (no problem text) */}
    <h3 className={`${full ? "text-lg sm:text-xl" : "text-base sm:text-lg"} font-bold text-[var(--on-surface)] tracking-tight leading-snug font-display`}>
      {leak.category}
    </h3>

    {/* Impact badge */}
    <div className="text-xs font-bold uppercase tracking-wider" style={{ color: impactStyle.textColor }}>
      {leak.impact} Impact
    </div>

    {/* Lock footer */}
    <div className={`${full ? "mt-4 pt-4" : "mt-3 pt-3"} border-t border-[var(--surface-container)] flex justify-between items-center`}>
      <span className="text-sm text-[var(--on-surface-variant)]">Sign up to see fixes</span>
      <LockKeyIcon
        className="w-5 h-5 text-[var(--on-surface-variant)] group-hover:text-[var(--brand)] transition-all duration-200"
        weight="regular"
      />
    </div>
  </div>
) : (
  // existing unlocked layout (lines 1380-1432) unchanged
  <div className={full ? "space-y-5" : "space-y-4"}>
    ...
  </div>
)}
```

**Expandable panel** (lines 1436–end) — only rendered when `expandable` is true; locked cards are never expandable, so this block needs no change.

---

### `webapp/src/components/analysis/CTACard.tsx` (component, request-response)

**Analog:** itself — prop additions + copy changes for anonymous mode.

**Current props interface** (lines 6–15):
```typescript
interface CTACardProps {
  leaksCount: number;
  animationDelay: number;
  onClick: () => void;
  variant?: "compact" | "full";
  label?: string;
  buttonLabel?: string;
}
```

**Target changes** — D-08/D-09 require anonymous-specific copy. Simplest approach: the existing `label`/`buttonLabel` override props are already in the interface. The call site in `analyze/page.tsx` drives the copy. No interface changes needed unless adding an `isAnonymous` prop for internal copy branching.

**Current copy** (lines 56–63) to target for anonymous mode:
```typescript
// CURRENT default label/buttonLabel:
{label ?? "Get All Fixes"}
// body: "Step-by-step recommendations for all {leaksCount} issues..."
// button: {buttonLabel ?? "Get Free Report"}

// TARGET for anonymous (D-09): personalized to issue count
// "Your page has {N} issues. Sign up free to see how to fix them."
// button: "Sign Up Free"
```

**Preferred approach:** Add `isAnonymous?: boolean` prop and branch the copy internally, keeping the call site simple:
```typescript
interface CTACardProps {
  leaksCount: number;
  animationDelay: number;
  onClick: () => void;
  variant?: "compact" | "full";
  isAnonymous?: boolean;   // NEW: drives anonymous-specific copy (D-09)
  label?: string;
  buttonLabel?: string;
}
```

---

### `webapp/src/components/AuthModal.tsx` (component, request-response)

**Analog:** itself — add `initialMode` prop (open question from RESEARCH.md, discretion area).

**Current props interface** (lines 22–27):
```typescript
interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  callbackUrl?: string;
}
```

**Target addition** — one prop, one `useState` default change:
```typescript
interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  callbackUrl?: string;
  initialMode?: "signin" | "signup";   // NEW (D-11 open question)
}

export default function AuthModal({ isOpen, onClose, callbackUrl, initialMode = "signin" }: AuthModalProps) {
  const [mode, setMode] = useState<AuthMode>(initialMode);

  // useEffect reset (line 46) must also apply initialMode:
  useEffect(() => {
    if (isOpen) {
      setMode(initialMode ?? "signin");
      // ... rest of reset unchanged
    }
  }, [isOpen, initialMode]);
```

---

### `webapp/src/components/PaywallModal.tsx` (DELETE)

**Deletion procedure** (must be in this order to avoid TypeScript errors):
1. Remove `const PaywallModal = dynamic(...)` import — `analyze/page.tsx` line 10
2. Remove `paywallOpen`, `paywallLeakKey` state — `analyze/page.tsx` lines 67–68
3. Remove `closePaywall` callback — `analyze/page.tsx` lines 198–201
4. Remove `<PaywallModal .../>` at line 281–285 (credit exhaustion screen)
5. Remove `<PaywallModal .../>` at lines 469–472 (main render)
6. Delete `webapp/src/components/PaywallModal.tsx`

Verify no remaining references:
```bash
grep -r "PaywallModal\|paywallOpen\|paywallLeakKey\|closePaywall" webapp/src/
```
Expected: zero results after deletion.

---

### `api/app/routers/analyze.py` (router, request-response)

**Analog:** itself — rate limit decorator pattern at lines 126–127.

**Current rate limit setup** (lines 69, 126–127):
```python
# rate_limit.py (line 44) — Cloudflare-aware IP extraction already wired:
limiter = Limiter(key_func=get_client_ip, headers_enabled=False)

# analyze.py (lines 126-128) — current global limit:
@router.post("/analyze")
@limiter.limit("5/minute")
async def analyze(request: Request, body: AnalyzeRequest, db: Session = Depends(get_db),
                  current_user: User | None = Depends(get_current_user_optional)):
```

**Target: anon-scoped 3/day limit** using a custom key function (Option A from RESEARCH.md):

```python
# Add to analyze.py — custom key function for anonymous-only daily limit
def _anon_rate_limit_key(request: Request) -> str:
    """Return real IP key for anonymous requests; fixed bucket for authenticated.

    slowapi applies the limit to all requests sharing the same key string.
    Authenticated users all share one fixed bucket with a ceiling they'll
    never reach — effectively bypassing the daily limit.
    """
    # Check Authorization header: if present, user is (or will be) authenticated
    if request.headers.get("authorization"):
        return "authenticated:unlimited"
    return f"anon:{get_client_ip(request)}"

# Updated endpoint:
@router.post("/analyze")
@limiter.limit("5/minute")                         # keep: global per-minute
@limiter.limit("3/day", key_func=_anon_rate_limit_key)  # NEW: 3/day for anon only
async def analyze(
    request: Request,
    body: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
```

**Import addition needed** — `get_client_ip` is already imported from `app.rate_limit`:
```python
from app.rate_limit import limiter  # line 69 — already present
# get_client_ip needed in _anon_rate_limit_key — add to import:
from app.rate_limit import limiter, get_client_ip
```

---

## Shared Patterns

### Dynamic modal import pattern
**Source:** `webapp/src/app/analyze/page.tsx` lines 9–10
**Apply to:** Any new modal additions (AuthModal is the survivor)
```typescript
const AuthModal = dynamic(() => import("@/components/AuthModal"), { ssr: false });
```

### Error handling in fetch chains
**Source:** `webapp/src/app/analyze/page.tsx` lines 133–155 (authenticated branch)
**Apply to:** Anonymous fetch branch (must be identical in structure)
```typescript
.catch((err: unknown) => {
  if (err instanceof DOMException && err.name === "AbortError") return;
  setError(err instanceof Error ? err.message : getUserFriendlyError(0));
  setLoading(false);
});
```

### AbortController cleanup pattern
**Source:** `webapp/src/app/analyze/page.tsx` lines 97, 156
**Apply to:** Anonymous fetch branch (prevent memory leaks on status change during scan)
```typescript
const controller = new AbortController();
abortRef.current = controller;
// ... fetch with signal: controller.signal
return () => { controller.abort(); };
```

### captureEvent analytics pattern
**Source:** `webapp/src/app/analyze/page.tsx` lines 130, 149, 171
**Apply to:** All new user interaction points (locked card clicks, anon scan completion)
```typescript
captureEvent("anon_scan_completed", { url });
captureEvent("locked_card_clicked", { category: leak.key, trigger: "issue_card" });
captureEvent("cta_card_clicked", { url, trigger: "inline_cta" });
```

### CSS custom property theming
**Source:** Throughout `IssueCard.tsx`, `CTACard.tsx`, `analyze/page.tsx`
**Apply to:** Any new locked card styling elements
```typescript
// Colors — use CSS vars, not hardcoded hex:
color: "var(--brand)"
color: "var(--on-surface-variant)"
background: "var(--surface-container-high)"
// Spacing — use Tailwind with sm: breakpoint variants for responsive
```

### Reveal animation pattern
**Source:** `webapp/src/app/analyze/page.tsx` lines 177–186
**Apply to:** No new reveals needed, but locked→unlocked transition reuses existing `result` state update
```typescript
// Animation class for new elements entering the DOM:
style={{ animation: "fade-in-up 400ms var(--ease-out-quart) both" }}
// With stagger via index:
style={{ animation: `fade-in-up 400ms var(--ease-out-quart) ${index * 80}ms both` }}
```

### FastAPI conditional logic pattern
**Source:** `api/app/routers/analyze.py` lines 142–151, 153–162
**Apply to:** Rate limit key function — same `current_user is None` guard used for credit check and dedup:
```python
# Pattern: branch on current_user presence, not on request auth header
if current_user is None:
    # apply anonymous-only behavior
```

---

## No Analog Found

No files in this phase lack an analog — all changes are modifications to existing files.

| File | Role | Data Flow | Note |
|------|------|-----------|------|
| — | — | — | All 7 modified files serve as their own analog |

---

## Pre-Implementation Checklist

Derived from RESEARCH.md pitfalls — planner should encode these as task-level guards:

| Check | Pitfall avoided |
|-------|-----------------|
| `isTeaser` has zero remaining references after page.tsx edit | Pitfall 1: stale isTeaser checks |
| `isShallow` / `hasFullAccess` removed or redefined as auth-based | Pitfall 1 (corollary) |
| Rate limit `_anon_rate_limit_key` returns fixed key for authenticated requests | Pitfall 2: auth users rate limited |
| `paywallOpen` / `paywallLeakKey` / `closePaywall` have zero remaining references | Pitfall 3: dangling PaywallModal state |
| Locked IssueCards receive `signals={undefined}` (not `result?.signals`) | Pitfall 4: signals visible in locked cards |
| AuthModal opened with `initialMode="signup"` from locked card / CTACard clicks | Pitfall 5: signin mode for new users |
| `if (status === "loading") return` guard present before anonymous branch | Pitfall 6: double-fire during signup |
| `result` state reset at start of useEffect when status changes from unauth→auth | Pitfall 6: old locked view persists briefly |

---

## Metadata

**Analog search scope:** `webapp/src/`, `api/app/routers/`, `api/app/`
**Files read:** 10 source files
**Pattern extraction date:** 2026-04-16
