# Phase 4: Doc Cleanup - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Update all stale documentation to reflect current product positioning. alpo.ai is a Shopify product page analyzer with a free tier (3 scans/month, 18-dimension scoring, recommendations, revenue leak estimates) and a Pro waitlist. Remove all references to old "PageScore" branding, $7 one-time pricing, OpenAI/GPT usage, and LemonSqueezy checkout. Delete files that no longer serve a purpose.

</domain>

<decisions>
## Implementation Decisions

### README.md (DOCS-01)
- **D-01:** Rewrite as product overview + dev setup guide. Not minimal, not just setup — describe what the product does and who it's for, then how to set it up locally.
- **D-02:** Describe current product only — free Shopify product page analyzer, 18 dimensions, revenue leak estimates. No mention of Pro waitlist, business model, or future plans.
- **D-03:** Update tech stack section to reflect actual stack: Next.js 16 + React 19, FastAPI + PostgreSQL, Playwright. Remove OpenAI, LemonSqueezy, Resend references.

### MARKETING.md (DOCS-02)
- **D-04:** Delete the file entirely. All content is old PageScore/$7 copy-paste templates. Fresh marketing content will be created when ready to distribute.

### DASHBOARD.md (DOCS-03)
- **D-05:** Delete the file entirely. Contains plaintext account credentials (security concern), old $7 metrics, and irrelevant agent team tracking.
- **D-06:** Flag credential rotation as a follow-up action — passwords for Vercel, LemonSqueezy, Reddit, HN, PostHog are exposed in git history.

### status.json (DOCS-04)
- **D-07:** Delete the file entirely from `webapp/public/`. Nothing consumes it — it was a manual tracking artifact. Removes stale data from the publicly served directory.

### Claude's Discretion
- README env vars: read from codebase to determine which environment variables are currently needed and document those
- README structure/sections: organize product overview and setup in a clean, standard format
- Whether any other files reference the deleted files (imports, links) and need cleanup
- Git operations for file deletion (ensure clean removal)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Files to modify
- `README.md` — Current "PageScore — AI Landing Page Analyzer" content. Full rewrite needed.

### Files to delete
- `MARKETING.md` — Old PageScore marketing templates. Delete entirely.
- `DASHBOARD.md` — Old founder dashboard with plaintext credentials. Delete entirely.
- `webapp/public/status.json` — Old product status tracking. Delete entirely.

### Current product context (for README rewrite)
- `.planning/PROJECT.md` — Source of truth for current product positioning and tech stack
- `webapp/src/app/pricing/page.tsx` — Current pricing page (single free plan + Pro waitlist)
- `api/app/` — Backend structure for setup documentation

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.planning/PROJECT.md` — Contains accurate product description, tech stack, and constraints to draw README content from

### Established Patterns
- No other docs reference MARKETING.md, DASHBOARD.md, or status.json in imports or links — deletion should be clean

### Integration Points
- `webapp/public/status.json` is the only file inside the webapp — verify no frontend code fetches it
- README.md is repo root — no code imports but may be linked from other docs

</code_context>

<specifics>
## Specific Ideas

- README should feel like a proper open-source project README — product overview at top, then dev setup
- Only describe what's live today, not future plans
- Credential rotation flagged as follow-up (not in scope for this phase, but noted)

</specifics>

<deferred>
## Deferred Ideas

- Rotate credentials exposed in git history (Vercel, LemonSqueezy, Reddit, HN, PostHog passwords from DASHBOARD.md)
- Consider git history rewrite to remove credential exposure if repo becomes public

</deferred>

---

*Phase: 04-doc-cleanup*
*Context gathered: 2026-04-16*
