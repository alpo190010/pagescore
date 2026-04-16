# Phase 4: Doc Cleanup - Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 5 (1 rewrite, 1 discretionary update, 3 deletions)
**Analogs found:** 2 / 2 (rewrite targets only — deletions have no analog requirement)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `README.md` | doc (product overview + dev setup) | static content | `docs/cloudflare-setup.md` | role-match (structured runbook with numbered sections, tables, code blocks) |
| `.env.local.example` | config (env template) | static content | `.env.production.template` | exact (same purpose: env var reference with inline comments) |
| `MARKETING.md` | doc (deletion) | — | — | n/a — delete only |
| `DASHBOARD.md` | doc (deletion) | — | — | n/a — delete only |
| `webapp/public/status.json` | static asset (deletion) | — | — | n/a — delete only |

---

## Pattern Assignments

### `README.md` (doc, product overview + dev setup — full rewrite)

**Analog:** `docs/cloudflare-setup.md`

This is the closest structured doc in the repo. It uses numbered H2 sections, tables for reference data, fenced code blocks for commands, and blockquotes for callouts. The README should follow the same structural conventions at a higher level.

**Section structure pattern** (from `docs/cloudflare-setup.md`):

```markdown
# Title — One-line description

Brief intro (1–2 sentences of context/purpose)

---

## 1. First Major Section

Short lead sentence.

| Column A | Column B |
|----------|----------|
| row      | data     |

### Sub-section

Step-by-step content or prose.

```bash
command --flag value
```

> **Note:** Callout for important nuance or warning.

---

## 2. Next Section
```

**README section order** (standard open-source pattern confirmed by RESEARCH.md):

```markdown
# alpo.ai — One-line description

Brief product description (2–3 sentences).

## What It Does
## Tech Stack
## Getting Started
### Prerequisites
### Installation
### Environment Variables
## Development
### Running Locally
```

**Tech stack table pattern** — copy format from RESEARCH.md verified data:

```markdown
| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 + React 19 (Vercel) |
| Backend API | FastAPI + Python |
| Database | PostgreSQL |
| Page rendering | Playwright (headless browser) |
| Auth | NextAuth.js (email/password + Google OAuth) |
| Analytics | PostHog |
| Reverse proxy | Caddy |
| Containerization | Docker Compose |
```

**Startup commands** (verified from `webapp/package.json` scripts and `api/Dockerfile` CMD):

```bash
# Frontend (webapp/)
npm run dev          # starts Next.js on port 3005

# Backend (api/) — via Docker
docker compose -f docker-compose.dev.yml up db   # start Postgres only
uvicorn app.main:app --host 0.0.0.0 --port 8000  # start FastAPI directly

# Full stack (Docker Compose)
docker compose up    # starts db + api + webapp + caddy
```

**Env var table pattern** — use same format as the table already in RESEARCH.md (verified against `docker-compose.yml`, `.env.production.template`). Required-only vars for the README:

```markdown
| Variable | Required | Purpose |
|----------|----------|---------|
| `POSTGRES_USER` | Yes | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `POSTGRES_DB` | Yes | PostgreSQL database name |
| `DATABASE_URL` | Yes | Full PostgreSQL connection string |
| `AUTH_SECRET` | Yes | NextAuth.js signing secret |
| `AUTH_GOOGLE_ID` | Yes | Google OAuth client ID |
| `AUTH_GOOGLE_SECRET` | Yes | Google OAuth client secret |
| `NEXT_PUBLIC_API_URL` | Yes | URL the webapp uses to reach the FastAPI backend |
| `NEXT_PUBLIC_BASE_URL` | Yes | Public base URL for the webapp |
```

**Dormant vars callout pattern** (follow `docs/cloudflare-setup.md` optional-section convention):

```markdown
> **Dormant (not required to run core product):** `OPENAI_API_KEY` (OpenRouter key for
> optional AI features), `RESEND_API_KEY` (email, unused at launch),
> `LEMONSQUEEZY_WEBHOOK_SECRET` and `LEMONSQUEEZY_VARIANT_*` (payments, no paid tier yet).
```

**Content constraints** (from CONTEXT.md D-02 — hard rule):
- No mention of Pro waitlist, business model, or future plans
- No OpenAI, LemonSqueezy, or Resend as active services
- Describe only what is live today

---

### `.env.local.example` (config template — discretionary comment update)

**Analog:** `.env.production.template` (lines 1–37)

The production template uses `# --- Section header ---` comment style with inline descriptions on the line above each variable. The `.env.local.example` should match this convention and fix stale service descriptions.

**Current stale pattern** (`.env.local.example` lines 1–16 — replace all comments):

```bash
# OpenAI - powers the AI analysis          ← STALE: hits OpenRouter, not OpenAI
OPENAI_API_KEY=sk-...

# Lemon Squeezy - payment processing       ← STALE: dormant, no paid tier
NEXT_PUBLIC_LEMONSQUEEZY_CHECKOUT_URL=...
LEMONSQUEEZY_WEBHOOK_SECRET=...

# Resend - email delivery for paid reports ← STALE: dormant at launch
RESEND_API_KEY=re_...
```

**Correct pattern to copy from** (`.env.production.template` comment style):

```bash
# --- OpenRouter (optional AI features — env var named OPENAI_API_KEY but hits openrouter.ai) ---
OPENAI_API_KEY=sk-...

# --- LemonSqueezy (payment webhooks — dormant, no paid tier at launch) ---
LEMONSQUEEZY_WEBHOOK_SECRET=your-webhook-secret

# --- Resend (email delivery — dormant at launch) ---
RESEND_API_KEY=re_...

# --- API URL - points the webapp at the FastAPI backend ---
NEXT_PUBLIC_API_URL=http://localhost:8000

# --- CORS - allowed origins for the FastAPI backend ---
CORS_ORIGINS=http://localhost:3000
```

---

## Deletions (No Pattern Required)

These files are removed, not replaced. No code patterns apply.

| File | Path | Git Command |
|------|------|-------------|
| MARKETING.md | `/MARKETING.md` | `git rm MARKETING.md` |
| DASHBOARD.md | `/DASHBOARD.md` | `git rm DASHBOARD.md` |
| status.json | `/webapp/public/status.json` | `git rm webapp/public/status.json` |

**Git pattern for deletions** (from RESEARCH.md — use `git rm`, not `rm`):

```bash
git rm MARKETING.md DASHBOARD.md webapp/public/status.json
```

Stages and removes in one step, ensuring the deletion is tracked in the commit.

**Commit message guidance** (from RESEARCH.md security note): The commit touching DASHBOARD.md must not quote or reference any credential values found in that file. Use:

```
delete stale founder dashboard (security cleanup)
```

---

## Shared Patterns

### Markdown Table Formatting
**Source:** `docs/cloudflare-setup.md` (used throughout)
**Apply to:** README.md (tech stack table, env vars table), `.env.local.example` is not markdown
```markdown
| Column | Column |
|--------|--------|
| value  | value  |
```
Always include header separator row with dashes aligned to column width.

### Code Block Language Tags
**Source:** `docs/cloudflare-setup.md`
**Apply to:** README.md
Always tag fenced code blocks with a language identifier: ` ```bash `, ` ```yaml `, ` ```markdown `. Never use untagged ` ``` `.

### Blockquote Callouts
**Source:** `docs/cloudflare-setup.md`
**Apply to:** README.md (dormant vars note, any "why" explanations)
```markdown
> **Note:** Important context that doesn't fit inline.
```

---

## No Analog Found

None. All files either have a direct analog or are deletions with no analog requirement.

---

## Key Content Facts for README (Verified — Do Not Re-Derive)

These are sourced from live codebase files. The implementing agent must use these and not guess.

| Fact | Value | Source |
|------|-------|--------|
| Product name | alpo.ai | PROJECT.md |
| What it does | Shopify product page analyzer, scores 18 conversion dimensions, estimates revenue leaks | PROJECT.md |
| Who it's for | Small solo Shopify merchants (1–50 products) | PROJECT.md |
| Frontend framework | Next.js 16 + React 19 | webapp/package.json (`"next": "^16.2.1"`, `"react": "^19.2.4"`) |
| Frontend dev command | `npm run dev` (starts on port 3005) | webapp/package.json scripts |
| Backend framework | FastAPI + Python | api/Dockerfile |
| Backend startup | `uvicorn app.main:app --host 0.0.0.0 --port 8000` | api/Dockerfile CMD |
| Database | PostgreSQL 16 | docker-compose.yml image |
| Full stack local | `docker compose up` | docker-compose.yml |
| Dev DB only | `docker compose -f docker-compose.dev.yml up db` | docker-compose.dev.yml |
| Auth system | NextAuth.js v5 | webapp/package.json (`"next-auth": "^5.0.0-beta.30"`) |
| Analytics | PostHog | webapp/package.json (`"posthog-js"`) |
| OPENAI_API_KEY | Points to OpenRouter, not OpenAI | .env.production.template comment |

---

## Metadata

**Analog search scope:** `/Users/aleksandrephatsatsia/projects/alpo/docs/`, repo root docs
**Files scanned:** README.md (1 line), .env.local.example, .env.production.template, docker-compose.yml, docker-compose.dev.yml, webapp/package.json, api/Dockerfile, docs/cloudflare-setup.md, .planning/PROJECT.md
**Pattern extraction date:** 2026-04-16
