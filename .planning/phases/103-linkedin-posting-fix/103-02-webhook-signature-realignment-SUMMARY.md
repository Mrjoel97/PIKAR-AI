---
phase: 103-linkedin-posting-fix
plan: 02
subsystem: auth
tags: [linkedin, webhook, hmac-sha256, fastapi, security]

# Dependency graph
requires:
  - phase: 103-linkedin-posting-fix-01
    provides: "LinkedIn URN capture + Posts API migration (unrelated path; signature work is independent)"
provides:
  - "verify_signature realigned to LinkedIn spec (X-LI-Signature header, LINKEDIN_CLIENT_SECRET env, hmacsha256= prefix)"
  - "POST /webhooks/linkedin returns 401 on invalid signature (was 403) and 500 fail-closed on missing secret"
  - "LINKEDIN_WEBHOOK_SECRET deprecation comment in .env.example"
  - "8-test regression net for LinkedIn webhook auth, including GET-challenge preservation"
affects: [104, 105, 106, 107, 108]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Webhook secret guard pattern: 500 on missing secret BEFORE body read; 401 on signature mismatch"
    - "TestClient + monkeypatch pattern for webhook signature unit tests with raw body bytes"

key-files:
  created:
    - tests/unit/test_linkedin_webhook_signature.py
  modified:
    - app/social/linkedin_webhook.py
    - app/routers/webhooks.py
    - .env.example

key-decisions:
  - "Status code split mirrors Linear/Asana/Stripe: 500 fail-closed for missing secret, 401 for invalid signature (audit-mandated upgrade from 403)"
  - "Legacy LINKEDIN_WEBHOOK_SECRET kept commented in .env.example so existing deployments don't break on env-var validation; runtime no longer reads it"
  - "TODO note added to resolve_user_from_event for URN-vs-bare-sub follow-up (out of scope for Phase 103)"

patterns-established:
  - "LinkedIn signature verification: hmac.compare_digest after stripping the 'hmacsha256=' prefix from the X-LI-Signature header"
  - "Pre-body env-var guard: any future provider with a separate signing secret should fail-closed with 500 BEFORE await request.body() so configuration bugs are observable"

requirements-completed: [POST-03]

# Metrics
duration: 22min
completed: 2026-05-09
---

# Phase 103 Plan 02: LinkedIn Webhook Signature Realignment Summary

**Realigned LinkedIn webhook verification to spec: X-LI-Signature header + LINKEDIN_CLIENT_SECRET + hmacsha256= prefix, 401 on invalid, 500 fail-closed on missing secret.**

## Performance

- **Duration:** ~22 min
- **Started:** 2026-05-09 (post 103-01 ship at 64ff9f1b)
- **Completed:** 2026-05-09
- **Tasks:** 2 (TDD pair)
- **Files modified:** 4 (1 created, 3 edited)

## Accomplishments

- Fixed 3 concrete bugs that caused 100% rejection of real LinkedIn webhooks: wrong header name (`X-LinkedIn-Signature` -> `X-LI-Signature`), wrong env var (`LINKEDIN_WEBHOOK_SECRET` -> `LINKEDIN_CLIENT_SECRET`), and missing `hmacsha256=` prefix strip.
- Added a fail-closed 500 guard for missing `LINKEDIN_CLIENT_SECRET` (matches Linear/Asana/Stripe pattern) BEFORE reading the request body — operators see a config bug instead of a silent reject loop.
- Status code on invalid signature upgraded from 403 to 401 per the audit-mandated success criterion.
- 8-test regression net committed to lock the spec: valid sig accepted, invalid sig rejected, missing header rejected, bare hex (no prefix) rejected, old `X-LinkedIn-Signature` header ignored, missing `LINKEDIN_CLIENT_SECRET` -> 500, legacy `LINKEDIN_WEBHOOK_SECRET` alone does not verify, GET challenge handler unchanged.
- All 5 existing `test_webhook_auth.py` tests (Linear/Asana) still GREEN — no collateral damage.

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — failing tests for X-LI-Signature + LINKEDIN_CLIENT_SECRET + 401** — `2cf76193` (test)
2. **Task 2: GREEN — verify_signature realignment + router header/status fix + .env.example deprecation** — `17484330` (fix)

(A `test(102-02)` commit `1db9e340` from a parallel plan landed in between Task 1 and Task 2 — disjoint files, no merge conflict.)

## Files Created/Modified

- `tests/unit/test_linkedin_webhook_signature.py` (CREATED, 254 lines, 8 tests)
- `app/social/linkedin_webhook.py` (MODIFIED): replaced `LINKEDIN_WEBHOOK_SECRET_ENV` with `LINKEDIN_CLIENT_SECRET_ENV` + `_LINKEDIN_SIG_PREFIX = "hmacsha256="`; renamed `_get_webhook_secret` to `_get_client_secret`; rewrote `verify_signature` to take a `signature_header` arg, strip the prefix, and HMAC-compare; added a TODO above `resolve_user_from_event` flagging the URN-vs-bare-sub follow-up.
- `app/routers/webhooks.py` (MODIFIED): added pre-body fail-closed guard for `LINKEDIN_CLIENT_SECRET` (raises 500); changed header lookup from `X-LinkedIn-Signature` to `X-LI-Signature`; changed `HTTPException(status_code=403)` to `401`; expanded the docstring to describe both failure modes. The GET handler at lines 45-86 is byte-for-byte unchanged.
- `.env.example` (MODIFIED): line 97-101 — replaced the bare `LINKEDIN_WEBHOOK_SECRET` example with a 4-line note pointing operators at `LINKEDIN_CLIENT_SECRET` and a `# DEPRECATED -- unused` tag on the legacy var (kept commented for backward compat).

## Decisions Made

- **500 vs 401 split for missing secret:** matched the Linear/Asana/Stripe pattern already in this file. Operator config errors should be loud (500), not silently rejected (401).
- **Legacy env var kept commented in .env.example:** removing it entirely would break existing deployments that template-validate the file. The `# DEPRECATED -- unused` tag makes the intent clear.
- **`X-LinkedIn-Signature` rejection codified as a test:** the legacy header name is a real footgun — pinning it as "must NOT be accepted" prevents a future "be liberal in what you accept" regression.
- **TODO note instead of fix for URN normalization:** `resolve_user_from_event` queries `connected_accounts.platform_user_id` with the full `urn:li:person:ABC` while Phase 103 POST-01 stores the bare sub `ABC`. Out of scope per CONTEXT — added as a TODO follow-up.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Three pre-existing ruff warnings in `app/routers/webhooks.py` surfaced during lint (B904 ×2 on `except Exception: raise HTTPException` blocks, RUF006 on the Slack `asyncio.create_task` call). All three are in code paths I did not touch (unchanged `git diff` for those line ranges); per the executor scope-boundary rule, pre-existing lint issues in unrelated code are out of scope. No deferred-items.md entry needed (these existed before 103-02 ran).
- `uv run ty check` is not invocable on this Windows workstation (`'"ty"' is not recognized`). Tests + ruff serve as the verification gate; the type-check command is left for CI.

## User Setup Required

None — `LINKEDIN_CLIENT_SECRET` is already documented in `.env.example` (line 68) and required for the OAuth flow that 101-03 already shipped. No new env vars introduced.

## Next Phase Readiness

- POST-03 success criterion (valid `X-LI-Signature: hmacsha256=<correct-hex>` accepted; invalid -> 401; missing secret -> 500) verified by 8 tests.
- Manual UAT (configure a real LinkedIn webhook subscription, like a member post, observe a row in `social_webhook_events` and a 200 in the logs) is queued for phase-level UAT — independent of this plan.
- Follow-up tracked: `resolve_user_from_event` URN normalization (URN vs bare OIDC sub from 103-01). Add a one-line strip of `urn:li:person:` or denormalize at write time. Low priority — only fires if the user's LinkedIn webhooks hit Pikar before 108 hygiene work.

## Self-Check

**Files claimed:**
- `tests/unit/test_linkedin_webhook_signature.py` — FOUND
- `app/social/linkedin_webhook.py` — MODIFIED (verified by `git diff` showing `LINKEDIN_CLIENT_SECRET_ENV` + `_LINKEDIN_SIG_PREFIX`)
- `app/routers/webhooks.py` — MODIFIED (verified: `X-LI-Signature` present, `X-LinkedIn-Signature` absent, status 401)
- `.env.example` — MODIFIED (verified: `DEPRECATED -- unused` present)

**Commits claimed:**
- `2cf76193` (test RED) — FOUND in `git log`
- `17484330` (fix GREEN) — FOUND in `git log`

**Test counts:**
- Before: 0 LinkedIn webhook signature tests, 5 webhook_auth tests
- After: 8 + 5 = 13 GREEN

**Grep verifications:**
- `X-LinkedIn-Signature` in `app/` — 0 matches (PASS)
- `LINKEDIN_WEBHOOK_SECRET` in `app/social/` + `app/routers/` — only the docstring deprecation comment in `linkedin_webhook.py:30` (no runtime read; PASS)
- `hmacsha256=` in `app/social/linkedin_webhook.py` — 3 matches (PASS, prefix constant + 2 docstring refs)
- `X-LI-Signature` in `app/routers/webhooks.py` — 4 matches (PASS, 1 runtime + 3 docstring/comment)

## Self-Check: PASSED

---
*Phase: 103-linkedin-posting-fix*
*Completed: 2026-05-09*
