---
phase: 07-foundation
plan: 01
subsystem: auth
tags: [fastapi, supabase, fernet, encryption, jwt, rls, postgresql, pytest]

# Dependency graph
requires: []
provides:
  - "require_admin FastAPI dependency with OR-logic (env allowlist + DB role)"
  - "9 admin tables with RLS + is_admin() SECURITY DEFINER function"
  - "MultiFernet encrypt_secret/decrypt_secret with key rotation support"
  - "GET /admin/check-access endpoint for frontend AdminGuard"
  - "admin_router wired into fast_api_app.py under /admin prefix"
affects:
  - 07-02
  - 07-03
  - 07-04
  - 07-05
  - 08-foundation
  - 09-foundation
  - 10-foundation
  - 11-foundation
  - 12-foundation
  - 13-foundation
  - 14-foundation
  - 15-foundation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "require_admin FastAPI Depends with two-layer OR auth (env allowlist + is_admin() RPC)"
    - "MultiFernet with comma-separated ADMIN_ENCRYPTION_KEY for zero-downtime key rotation"
    - "RLS enabled on admin tables with no policies — service role bypasses, anon denied"
    - "B008 noqa suppression for Depends() in FastAPI function signatures"
    - "TDD RED/GREEN workflow: tests written before implementation"

key-files:
  created:
    - supabase/migrations/20260321300000_admin_panel_foundation.sql
    - app/middleware/admin_auth.py
    - app/services/encryption.py
    - app/routers/admin/__init__.py
    - app/routers/admin/auth.py
    - tests/unit/admin/__init__.py
    - tests/unit/admin/conftest.py
    - tests/unit/admin/test_admin_auth.py
    - tests/unit/admin/test_encryption.py
    - tests/integration/admin/__init__.py
  modified:
    - app/fast_api_app.py

key-decisions:
  - "require_admin uses OR logic: ADMIN_EMAILS env allowlist checked first (fast path, no DB), falls back to is_admin() RPC — env check short-circuits DB call"
  - "ADMIN_EMAILS is server-side only (no NEXT_PUBLIC_ prefix) — frontend AdminGuard calls GET /admin/check-access, never reads env directly"
  - "admin_audit_log.impersonation_session_id is nullable UUID column included now (schema-ready for Phase 13 AUDT-04) but not populated in Phase 7"
  - "MultiFernet wraps comma-separated ADMIN_ENCRYPTION_KEY keys from day one — first key encrypts, all keys try decryption"
  - "RLS enabled on all 9 admin tables with no policies — service role bypasses RLS, anonymous access is denied by default"

patterns-established:
  - "Pattern: require_admin — import and use as Depends(require_admin) on all /admin/* endpoints"
  - "Pattern: encrypt_secret/decrypt_secret — call directly; no caching, each call reads env"
  - "Pattern: admin_router in app/routers/admin/__init__.py — add sub-routers with admin_router.include_router()"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUDT-02]

# Metrics
duration: 11min
completed: 2026-03-21
---

# Phase 7 Plan 1: Admin Foundation Summary

**Two-layer admin auth (ADMIN_EMAILS OR user_roles DB), 9 Supabase tables with RLS, MultiFernet secret encryption, and GET /admin/check-access endpoint wired into FastAPI**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-21T11:20:17Z
- **Completed:** 2026-03-21T11:31:00Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- `require_admin` FastAPI dependency with OR logic: env allowlist fast-path, DB role fallback, returns `admin_source` field for audit coverage
- Supabase migration with all 9 admin tables, `is_admin()` SECURITY DEFINER function, RLS enabled with no policies, and 4 seeded `admin_agent_permissions` rows
- `MultiFernet` encryption service (`encrypt_secret`/`decrypt_secret`) with comma-separated key rotation support from day one
- `GET /admin/check-access` rate-limited endpoint returning `{access, email, admin_source}`, wired into `fast_api_app.py`
- 9 unit tests covering all auth paths and encryption cases — all green

## Task Commits

1. **Task 1: DB migration + require_admin + encryption (TDD GREEN)** - `43ea0cb` (feat)
2. **Task 2: Admin auth router + check-access + FastAPI wiring** - `c0d4207` (feat)

## Files Created/Modified

- `supabase/migrations/20260321300000_admin_panel_foundation.sql` — 9 admin tables, is_admin() SECURITY DEFINER, RLS on all, 4 seeded permission rows, nullable impersonation_session_id for Phase 13
- `app/middleware/admin_auth.py` — require_admin FastAPI dependency with OR-logic auth
- `app/services/encryption.py` — MultiFernet encrypt_secret/decrypt_secret
- `app/routers/admin/__init__.py` — admin_router with /admin prefix
- `app/routers/admin/auth.py` — GET /check-access endpoint, rate-limited 120/min
- `app/fast_api_app.py` — import and register admin_router after api_credentials_router
- `tests/unit/admin/__init__.py` — package marker
- `tests/unit/admin/conftest.py` — shared fixtures (mock_supabase_client, admin_user_dict, etc.)
- `tests/unit/admin/test_admin_auth.py` — 5 tests for require_admin
- `tests/unit/admin/test_encryption.py` — 4 tests for encrypt/decrypt
- `tests/integration/admin/__init__.py` — package marker

## Decisions Made

- OR logic implemented by checking env first, returning early (short-circuits DB call). Neither path requires the other to pass — satisfying either grants access.
- `admin_audit_log.impersonation_session_id` added as nullable UUID now to avoid a future migration when Phase 13 implements interactive impersonation (AUDT-04).
- B008 ruff suppression (`# noqa: B008`) applied to `Depends()` calls — consistent with FastAPI convention throughout the codebase.

## Deviations from Plan

**1. [Rule 1 - Bug] Added `# noqa: B008` suppression to Depends() calls**
- **Found during:** Task 2 (ruff lint check)
- **Issue:** Ruff B008 flags `Depends()` in function argument defaults, but this is standard FastAPI usage required by the framework
- **Fix:** Added `# noqa: B008` comments on two `Depends()` calls in `admin_auth.py` and `routers/admin/auth.py`
- **Files modified:** `app/middleware/admin_auth.py`, `app/routers/admin/auth.py`
- **Verification:** `ruff check` returns "All checks passed!"
- **Committed in:** `c0d4207` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — lint fix)
**Impact on plan:** Lint-only fix, no behavior change. Standard FastAPI pattern used throughout the codebase.

## Issues Encountered

- Pre-existing untracked test files (`test_confirmation.py`, `test_audit.py`) in the admin test directory reference `app.services.confirmation_tokens` and `app.services.admin_audit` — modules from future plans. These failures are out-of-scope and pre-date this plan. The plan's scoped tests (`test_admin_auth.py`, `test_encryption.py`) pass cleanly.

## User Setup Required

Two environment variables must be configured before admin features are usable:

- `ADMIN_EMAILS` — comma-separated list of bootstrap admin emails (e.g., `admin@company.com`). Never use `NEXT_PUBLIC_` prefix.
- `ADMIN_ENCRYPTION_KEY` — Fernet key for secret encryption. Generate with:
  ```
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

The Supabase migration (`20260321300000_admin_panel_foundation.sql`) must be applied before any admin endpoints are called. Run `supabase db push --local` for local dev.

## Next Phase Readiness

- All downstream plans (07-02 through 15) can now `from app.middleware.admin_auth import require_admin` to gate their endpoints
- `admin_router` in `app/routers/admin/__init__.py` accepts new sub-routers via `admin_router.include_router()`
- `encrypt_secret`/`decrypt_secret` ready for Phase 11 (Integrations) to store API keys
- All 9 DB tables exist with RLS — Phase 07-02 (AdminAgent + chat) can write to `admin_chat_sessions` and `admin_chat_messages` immediately

---
*Phase: 07-foundation*
*Completed: 2026-03-21*
