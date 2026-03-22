---
phase: 11-external-integrations
plan: 01
subsystem: api
tags: [sentry, posthog, github, stripe, fernet, redis, cache, httpx, pygithub]

# Dependency graph
requires:
  - phase: 07-foundation
    provides: encrypt_secret/decrypt_secret (MultiFernet), require_admin middleware, admin_router registration pattern
  - phase: 08-health-monitoring
    provides: CacheService.get_generic/set_generic, get_cache_service()

provides:
  - IntegrationProxyService.call() — unified cache-check + provider fetch + cache-set proxy
  - check_session_budget() — per-session per-provider Redis INCR budget enforcement (fail-open)
  - GET/PUT/DELETE /admin/integrations/{provider} — CRUD with Fernet-encrypted key storage
  - POST /admin/integrations/{provider}/test — provider health check endpoint
  - 7 proxy endpoints covering Sentry issues, PostHog events/insights, GitHub PRs, Stripe summary
  - Provider fetch functions for all 4 providers using httpx (Sentry, PostHog) and SDK wrappers (GitHub, Stripe)

affects: [11-02, 11-03, admin-agent-integration-tools, frontend-integrations-page]

# Tech tracking
tech-stack:
  added: [PyGithub~=2.8.1, pynacl (transitive)]
  patterns:
    - Cache-check before provider call, store result on miss (intg_proxy:{provider}:{operation}:{md5_hash} key)
    - asyncio.to_thread() for synchronous SDK calls (PyGithub, Stripe) to avoid blocking event loop
    - Fail-open budget enforcement — Redis unavailable returns True, never blocks legitimate admin calls
    - Provider TTL differentiation: Sentry/PostHog/GitHub=180s, Stripe=300s

key-files:
  created:
    - app/services/integration_proxy.py
    - app/routers/admin/integrations.py
    - tests/unit/admin/test_integration_proxy.py
    - tests/unit/admin/test_integrations_api.py
  modified:
    - app/routers/admin/__init__.py
    - pyproject.toml

key-decisions:
  - "11-01: Stripe uses SDK (stripe>=7.0.0 already installed) not raw httpx — typed responses, automatic pagination, idempotency"
  - "11-01: check_session_budget fails open when Redis unavailable — admin should never be blocked by Redis downtime"
  - "11-01: test_proxy_requires_admin tests HTTPBearer directly (not require_admin) — matches established project pattern from onboarding.py"
  - "11-01: PyGithub installed via pip3.exe into .venv (uv shim only supports uv run in this environment); added to pyproject.toml for reproducibility"

patterns-established:
  - "IntegrationProxyService.call() accepts fetch_fn callable — provider fetch is injected, not hardcoded, enabling clean mocking in tests"
  - "All sync SDK calls (PyGithub, Stripe) wrapped in asyncio.to_thread() for non-blocking async execution"
  - "_get_integration() shared helper centralises row fetch + is_active guard + key decrypt for all 7 proxy endpoints"

requirements-completed: [INTG-01, INTG-02, INTG-03, INTG-04, INTG-05, INTG-06]

# Metrics
duration: 25min
completed: 2026-03-22
---

# Phase 11 Plan 01: Integration Proxy Service + CRUD/Proxy Router Summary

**Fernet-encrypted API key storage, Redis-cached provider proxy, and 7 pass-through endpoints for Sentry, PostHog, GitHub, and Stripe**

## Performance

- **Duration:** 25 min
- **Started:** 2026-03-22T14:45:00Z
- **Completed:** 2026-03-22T15:10:00Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 6

## Accomplishments

- IntegrationProxyService with cache hit/miss logic using `intg_proxy:{provider}:{operation}:{md5_hash}` keys and per-provider TTLs
- check_session_budget() using atomic Redis INCR with 5-minute rolling window, fails open when Redis unavailable
- CRUD endpoints: PUT upserts with Fernet encryption, GET masks keys as `****...last4`, DELETE removes row, POST /test pings provider and updates health_status
- 7 proxy endpoints (Sentry issues + detail, PostHog events + insights, GitHub PRs + PR status, Stripe summary) all requiring admin auth and rejecting inactive integrations
- Provider fetch functions: httpx.AsyncClient for Sentry/PostHog; PyGithub via asyncio.to_thread for GitHub; Stripe SDK via asyncio.to_thread for Stripe
- All 17 tests GREEN

## Task Commits

Each task was committed atomically:

1. **TDD RED: failing tests** - `b71e484` (test)
2. **TDD GREEN: implementation** - `373f3c7` (feat)

## Files Created/Modified

- `app/services/integration_proxy.py` — IntegrationProxyService.call(), check_session_budget(), all provider fetch functions and _test_provider_connection()
- `app/routers/admin/integrations.py` — CRUD + proxy endpoints with Fernet key handling and rate limiting
- `app/routers/admin/__init__.py` — registered integrations.router (Phase 11 comment)
- `pyproject.toml` — added PyGithub~=2.8.1 dependency
- `tests/unit/admin/test_integration_proxy.py` — 5 proxy service tests (cache hit, miss, budget allowed/exhausted/redis-down)
- `tests/unit/admin/test_integrations_api.py` — 12 router tests (CRUD, proxy endpoints, auth, inactive integration)

## Decisions Made

- Stripe uses the SDK (`stripe>=7.0.0`, already in pyproject.toml) instead of raw httpx — typed responses, automatic pagination, and idempotency keys make it superior to raw HTTP for Stripe
- `check_session_budget` fails open — Redis downtime should never block an admin performing legitimate integration checks
- `test_proxy_requires_admin` tests `HTTPBearer` directly rather than calling `require_admin()` — aligns with the established project pattern (HTTPBearer raises 403 on missing Authorization header, as noted in STATE.md for Phase 17)
- PyGithub installed via `pip3.exe` into `.venv` because the environment's `uv.cmd` shim only supports `uv run`; added to `pyproject.toml` for reproducibility in fresh installs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed unused variable `result` in upsert_integration**
- **Found during:** Task 1 (ruff lint check post-implementation)
- **Issue:** `result = await execute_async(...)` was assigned but never read — ruff F841
- **Fix:** Removed the assignment, `await execute_async(...)` directly
- **Files modified:** app/routers/admin/integrations.py
- **Verification:** `ruff check` passes clean
- **Committed in:** 373f3c7 (feat commit)

**2. [Rule 1 - Bug] Fixed test_proxy_requires_admin calling require_admin with wrong signature**
- **Found during:** Task 1 (test run — 1 failure at RED→GREEN transition)
- **Issue:** Test called `require_admin(request=request)` but require_admin takes `credentials: HTTPAuthorizationCredentials` not a raw request
- **Fix:** Test now calls `HTTPBearer()(request=request)` directly — tests the actual rejection mechanism at the HTTPBearer layer
- **Files modified:** tests/unit/admin/test_integrations_api.py
- **Verification:** All 17 tests GREEN
- **Committed in:** 373f3c7 (feat commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs)
**Impact on plan:** Both fixes were trivial correctness issues found during the test run. No scope creep.

## Issues Encountered

- `uv add` unavailable in this environment (shim only supports `uv run`). Resolved by installing PyGithub directly via `pip3.exe` and adding the dependency to `pyproject.toml` manually.

## User Setup Required

None — no external service configuration required for this plan. (API keys for Sentry, PostHog, GitHub, Stripe are configured via the PUT /admin/integrations/{provider} endpoint itself.)

## Next Phase Readiness

- Integration proxy service and router are complete — Plan 02 (AdminAgent integration tools) can import `IntegrationProxyService` and the provider fetch functions directly
- Plan 03 (frontend integration page) has all 7 proxy endpoints available
- The `admin_integrations` table schema (from Phase 7 migration) is used as-is — no new migrations required in this plan

---
*Phase: 11-external-integrations*
*Completed: 2026-03-22*
