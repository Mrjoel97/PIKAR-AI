---
phase: 76-security-hardening
plan: 02
subsystem: api
tags: [ssrf, xss, dompurify, slack, webhooks, security, ssr]

# Dependency graph
requires: []
provides:
  - Slack response_url SSRF prevention via domain allowlist
  - SSR-safe DOMPurify wrapper with explicit direct dependency
  - 9 automated tests covering SSRF scenarios
affects:
  - app/routers/webhooks.py
  - frontend/src/lib/sanitize.ts

# Tech tracking
tech-stack:
  added:
    - dompurify ^3.2.6 (frontend direct dependency)
    - "@types/dompurify ^3.2.0 (frontend devDependency)"
  patterns:
    - URL allowlist validation before outbound HTTP requests
    - Lazy-initialized SSR-safe module loading with typeof window guard

key-files:
  created:
    - tests/unit/test_slack_ssrf.py
  modified:
    - app/routers/webhooks.py
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/src/lib/sanitize.ts

key-decisions:
  - "Slack allowlist uses frozenset for O(1) lookup: hooks.slack.com and api.slack.com as explicit entries, plus *.slack.com subdomain pattern"
  - "Non-HTTPS Slack URLs rejected to prevent downgrade attacks even to legitimate Slack domains"
  - "DOMPurify loaded via require() inside getPurify() to avoid top-level import crash on SSR; empty string returned server-side"
  - "TDD order: failing tests committed first (c56ac10b), then implementation (bcab2366) to preserve audit trail"

patterns-established:
  - "SSRF guard: validate any user-controlled URL against an allowlist before passing to httpx"
  - "SSR-safe lazy import: use typeof window guard + module-level cache for DOM-dependent libraries"

requirements-completed:
  - SEC-02
  - SEC-04

# Metrics
duration: 18min
completed: 2026-04-26
---

# Phase 76 Plan 02: SSRF Prevention and SSR-Safe DOMPurify Summary

**Slack response_url SSRF closed via domain allowlist + DOMPurify pinned as direct dependency with SSR-safe lazy-import wrapper**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-04-26T00:00:00Z
- **Completed:** 2026-04-26
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `_is_valid_slack_response_url()` helper that enforces HTTPS and restricts outbound POSTs to `*.slack.com` — attacker-controlled `response_url` values are logged and discarded before reaching `httpx.AsyncClient.post`
- Promoted `dompurify` from transitive to explicit direct dependency (`^3.2.6`) and added `@types/dompurify` as a devDependency; `npm ls` now shows it as a top-level package
- Replaced the SSR-crashing static DOMPurify import with a `getPurify()` lazy-loader guarded by `typeof window !== 'undefined'`; server-side calls return empty string safely
- 9 automated tests (7 unit + 2 integration) covering valid Slack URLs, evil domains, subdomain spoofing (`hooks.slack.com.evil.com`), non-HTTPS, empty URL, and end-to-end mock verifying `httpx` is never called for evil URLs

## Task Commits

Each task was committed atomically:

1. **Task 1 RED — Failing SSRF tests** - `c56ac10b` (test)
2. **Task 1 GREEN — Slack response_url allowlist** - `bcab2366` (feat)
3. **Task 2 — dompurify explicit dep + SSR-safe sanitize.ts** - `2a5e24eb` (feat)

## Files Created/Modified

- `app/routers/webhooks.py` — Added `_SLACK_RESPONSE_URL_ALLOWLIST`, `_is_valid_slack_response_url()`, and validation guard in `_process_slack_block_action`
- `tests/unit/test_slack_ssrf.py` — 9 tests for SSRF prevention (created)
- `frontend/package.json` — Added `dompurify` to dependencies, `@types/dompurify` to devDependencies
- `frontend/package-lock.json` — Updated lockfile after `npm install`
- `frontend/src/lib/sanitize.ts` — Rewrote with lazy `getPurify()` pattern and `typeof window` SSR guard

## Decisions Made

- Used `frozenset` for the allowlist (O(1) lookup) with both `hooks.slack.com` and `api.slack.com` as explicit entries plus a `*.slack.com` suffix pattern for future Slack subdomains
- Non-HTTPS URLs rejected even for legitimate Slack domains — prevents protocol downgrade attacks
- DOMPurify loaded with `require()` inside a cached getter function (not `await import()`) to keep `sanitizeHtml` synchronous — compatible with current call sites in page.tsx
- TDD followed strictly: failing tests committed before implementation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all verification steps passed on first attempt. Pre-existing ruff lint warnings (B904, RUF100, RUF006) in webhooks.py are out-of-scope pre-existing issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- SEC-02 (SSRF via Slack response_url) and SEC-04 (DOMPurify explicit dependency) are closed
- Remaining security hardening tasks in Phase 76 can proceed independently
- No blockers

---
*Phase: 76-security-hardening*
*Completed: 2026-04-26*
