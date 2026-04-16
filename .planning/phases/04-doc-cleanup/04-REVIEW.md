---
phase: 04-doc-cleanup
reviewed: 2026-04-16T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - README.md
  - .env.local.example
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-04-16
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Two documentation files were reviewed: the top-level `README.md` (full rewrite) and `.env.local.example` (comment update). No critical issues were found. Three warnings require attention before the phase is complete: two are correctness issues (a CORS port mismatch that will break local dev, and a missing required env var in the template) and one is a section-ordering issue in the README that puts environment variable setup before installation. Four info-level items are noted for polish.

Findings were validated against verified facts in `04-PATTERNS.md`, `webapp/package.json`, and `.env.production.template`.

---

## Warnings

### WR-01: CORS default port does not match webapp dev port

**File:** `.env.local.example:15`
**Issue:** `CORS_ORIGINS` is set to `http://localhost:3000`, but the webapp runs on port `3005` (confirmed in `webapp/package.json` `dev` script: `next dev --port 3005`). A developer who copies this file verbatim will get CORS rejections when the webapp calls the FastAPI backend locally.
**Fix:**
```bash
# --- CORS -- allowed origins for the FastAPI backend ---
CORS_ORIGINS=http://localhost:3005
```

---

### WR-02: `NEXT_PUBLIC_BASE_URL` declared required in README but absent from `.env.local.example`

**File:** `.env.local.example` (missing entry); cross-reference `README.md:68`
**Issue:** `README.md` lists `NEXT_PUBLIC_BASE_URL` as a required variable in the environment variable table. The `.env.local.example` does not include this variable at all. Developers following the standard "copy example file, fill in values" workflow will miss a required variable, leading to runtime errors.
**Fix:** Add the variable to `.env.local.example`:
```bash
# --- Base URL -- public-facing base URL for the webapp ---
NEXT_PUBLIC_BASE_URL=http://localhost:3005
```
If the variable is genuinely not required for local dev (e.g., only needed in production), it should be removed from the `Required: Yes` row in the README table or moved to a "production-only" note.

---

### WR-03: `Environment Variables` section appears before `Installation` in README

**File:** `README.md:56` (Environment Variables), `README.md:72` (Installation)
**Issue:** Within `## Getting Started`, `### Environment Variables` precedes `### Installation`. This is a logic ordering problem: the env var table references variables the reader should fill into `.env`, but the `Installation` section (which includes `cp .env.production.template .env`) has not yet told the reader to create that file. Standard setup docs order these as: Prerequisites → Installation → (then) Environment Variables.
**Fix:** Swap the two subsections so `### Installation` appears at line 56 and `### Environment Variables` follows it. No content changes needed — only the order of the two `###` blocks.

---

## Info

### IN-01: `(Vercel)` embedded in tech-stack framework cell conflates framework with host

**File:** `README.md:20`
**Issue:** The tech stack table entry reads `Next.js 16 + React 19 (Vercel)`. Vercel is the deployment platform, not part of the frontend framework. This could mislead a developer to believe Vercel is a required dependency or that the app cannot be deployed elsewhere.
**Fix:** Either remove `(Vercel)` from the Frontend cell, or add a dedicated "Deployment" row:
```markdown
| Frontend    | Next.js 16 + React 19          |
| Deployment  | Vercel                         |
```

---

### IN-02: `git clone <repo-url>` placeholder left unreplaced

**File:** `README.md:75`
**Issue:** The installation code block contains `git clone <repo-url>`. This is a non-functional command. If the repository is or will be public, the actual URL should replace this placeholder so `README.md` works as a copy-paste setup guide.
**Fix:** Replace with the real repository URL, or add a note like:
```bash
git clone https://github.com/your-org/alpo  # replace with actual repo URL
```

---

### IN-03: `NEXT_PUBLIC_LEMONSQUEEZY_CHECKOUT_URL` in `.env.local.example` has no analog in `.env.production.template`

**File:** `.env.local.example:5`
**Issue:** `.env.local.example` includes `NEXT_PUBLIC_LEMONSQUEEZY_CHECKOUT_URL` under the LemonSqueezy block. This variable does not appear in `.env.production.template` (the declared analog). Its purpose (local-only vs. unused vs. intentionally omitted from prod) is undocumented. If it is genuinely local-only or unused, a comment should say so; if it belongs in the prod template too, it should be added there.
**Fix:** Add an inline clarification comment:
```bash
# --- LemonSqueezy (payment webhooks -- dormant, no paid tier at launch) ---
NEXT_PUBLIC_LEMONSQUEEZY_CHECKOUT_URL=https://yourstore.lemonsqueezy.com/buy/xxx  # local-only, not in prod template
LEMONSQUEEZY_WEBHOOK_SECRET=your-webhook-secret
```

---

### IN-04: Inline comment separator style inconsistency in README bash block

**File:** `README.md:90`
**Issue:** The bash code block comment reads `# Backend (api/) -- start Postgres first`. The double-hyphen `--` is an informal text separator. The project's documented comment style (from `.env.production.template` and `docs/cloudflare-setup.md`) uses `—` (em dash) for inline separators in prose, and plain `#` comment lines in code blocks. This is cosmetic but creates a small inconsistency with surrounding style.
**Fix:** Use a plain comment line without separator punctuation:
```bash
# Backend (api/) — start Postgres first
```
or simply:
```bash
# Backend (api/): start Postgres first
```

---

_Reviewed: 2026-04-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
