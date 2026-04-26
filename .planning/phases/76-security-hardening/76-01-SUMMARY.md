---
phase: 76-security-hardening
plan: "01"
subsystem: security
tags: [security, webhooks, auth, hardening]
dependency_graph:
  requires: []
  provides: [SEC-01, SEC-03]
  affects: [app/routers/webhooks.py, app/app_utils/auth.py, app/fast_api_app.py]
tech_stack:
  added: []
  patterns: [fail-closed webhook enforcement, secure-by-default auth parameter]
key_files:
  created:
    - tests/unit/test_webhook_auth.py
  modified:
    - app/routers/webhooks.py
    - app/app_utils/auth.py
    - app/fast_api_app.py
    - tests/unit/app/test_auth_utils.py
decisions:
  - "Fail-closed (HTTP 500) rather than fail-open when webhook secrets are absent — matches existing Shopify/Stripe pattern already in the codebase"
  - "Changed allow_header_fallback default to False — no callers in production code use the default, so zero runtime impact; future callers get the secure default"
  - "Telemetry comment added to middleware rather than changing the middleware behavior — request.state.user_id serves a legitimate tracing purpose"
metrics:
  duration_seconds: 626
  completed_date: "2026-04-26"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 4
---

# Phase 76 Plan 01: Security Hardening — Webhook Secret Enforcement and Auth Header Hardening Summary

**One-liner:** Fail-closed webhook secret enforcement for Linear/Asana (HTTP 500 when unconfigured) and secure-by-default `allow_header_fallback=False` to block x-user-id header spoofing.

## What Was Built

Two targeted security fixes closing gaps identified in the v10.0 audit:

**Fix 1 — Webhook secret enforcement (SEC-01)**

Both Linear and Asana webhook handlers previously used a "skip verification" pattern when their signing secrets were absent, silently processing unauthenticated payloads. They now match the existing Shopify/Stripe pattern: if the secret is unset or empty, the handler immediately raises `HTTPException(status_code=500)` before reading the body. The HMAC verification block no longer needs a conditional guard since the secret is guaranteed non-empty at that point.

**Fix 2 — Auth header default hardening (SEC-03)**

`resolve_request_user_id` defaulted to `allow_header_fallback=True`, meaning a caller that forgot to pass the flag would silently trust the `x-user-id` header as an authoritative user identity. The default is now `False`. No production callers use the function with the default (confirmed by grep), so there is zero runtime impact. The logging middleware that reads `x-user-id` for telemetry now carries a clear comment documenting that `request.state.user_id` is not authenticated.

## Tasks

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Enforce webhook secret for Linear and Asana endpoints | `7a856003` | `app/routers/webhooks.py`, `tests/unit/test_webhook_auth.py` |
| 2 | Default allow_header_fallback=False and add telemetry comment | `1475e92c` | `app/app_utils/auth.py`, `app/fast_api_app.py`, `tests/unit/app/test_auth_utils.py` |

## Test Coverage

13 tests total (5 new webhook tests + 3 new/updated auth tests + 5 pre-existing):

- `test_linear_returns_500_when_secret_missing` — empty string env var
- `test_linear_returns_500_when_secret_unset` — env var completely absent
- `test_linear_proceeds_to_verify_when_secret_set` — reaches HMAC (gets 403, not 500)
- `test_asana_returns_500_when_hook_secret_empty` — mock returns ""
- `test_asana_proceeds_to_verify_when_hook_secret_set` — reaches HMAC (gets 403, not 500)
- `test_resolve_request_user_id_default_rejects_header_without_bearer` — new default behavior
- `test_resolve_request_user_id_default_returns_jwt_user_with_valid_bearer` — JWT path unaffected
- `test_resolve_request_user_id_uses_header_fallback_without_bearer` — updated to pass explicit `allow_header_fallback=True`

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **Fail-closed on HTTP 500 for missing webhook secrets** — matches the existing Shopify/Stripe pattern already in `webhooks.py`. Consistent behavior across all webhook providers.

2. **allow_header_fallback=False as new secure default** — grep confirmed no production callers invoke `resolve_request_user_id` without explicit arguments, making this a zero-risk change with significant security benefit for future callers.

3. **Comment-only change to logging middleware** — the middleware behavior is correct (telemetry is a legitimate use of the header); only the documentation was missing.

## Self-Check: PASSED

All key files exist. Both task commits (`7a856003`, `1475e92c`) confirmed in git log.
