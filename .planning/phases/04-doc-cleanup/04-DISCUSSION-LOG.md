# Phase 4: Doc Cleanup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 04-doc-cleanup
**Areas discussed:** README scope, MARKETING.md fate, DASHBOARD.md & credentials, status.json purpose

---

## README scope

| Option | Description | Selected |
|--------|-------------|----------|
| Dev setup guide | Product name + one-line description, focused on setup/deploy | |
| Product overview + setup | Detailed product description + dev setup guide | ✓ |
| Minimal stub | Just name, one-liner, link to docs | |

**User's choice:** Product overview + setup
**Notes:** Standard open-source README with product overview at top, then dev setup

| Option | Description | Selected |
|--------|-------------|----------|
| Current product only | Describe what's live: free analyzer, 18 dimensions, revenue leaks | ✓ |
| Include business context | Mention free tier + Pro waitlist, target customer, direction | |

**User's choice:** Current product only
**Notes:** No mention of Pro/waitlist/business model in README

| Option | Description | Selected |
|--------|-------------|----------|
| You decide | Claude reads codebase to determine current env vars | ✓ |
| I'll specify | User lists which env vars to include | |

**User's choice:** You decide (Claude's discretion)
**Notes:** Read actual codebase to determine which environment variables are needed

---

## MARKETING.md fate

| Option | Description | Selected |
|--------|-------------|----------|
| Delete entirely | Remove the file. No launch campaign exists yet. | ✓ |
| Rewrite with new framing | Replace with Shopify-focused messaging | |
| Stub it | Replace with placeholder noting content TBD | |

**User's choice:** Delete entirely
**Notes:** Fresh marketing content will be created when ready to distribute

---

## DASHBOARD.md & credentials

| Option | Description | Selected |
|--------|-------------|----------|
| Delete entirely | Remove file. Credentials should never be in repo. | ✓ |
| Keep without credentials | Strip passwords, update metrics | |
| Replace with clean stub | Minimal template, no credentials | |

**User's choice:** Delete entirely
**Notes:** Contains plaintext passwords — security concern

| Option | Description | Selected |
|--------|-------------|----------|
| Just delete, move on | Delete file, deal with rotation separately | |
| Flag for follow-up | Delete + add note to rotate exposed credentials | ✓ |

**User's choice:** Flag for follow-up
**Notes:** Credentials are in git history — rotation needed as follow-up task

---

## status.json purpose

| Option | Description | Selected |
|--------|-------------|----------|
| Delete entirely | Remove from webapp/public/. Nothing consumes it. | ✓ |
| Rewrite as product status | Replace with current product status | |
| Move out of public/ | Keep tracking but don't serve publicly | |

**User's choice:** Delete entirely
**Notes:** Manual tracking artifact from old product, publicly served but unused

---

## Claude's Discretion

- README env vars: determine from codebase which are currently needed
- README structure and section organization
- Checking if any code references the deleted files

## Deferred Ideas

- Rotate credentials exposed in DASHBOARD.md git history
- Consider git history rewrite if repo becomes public
