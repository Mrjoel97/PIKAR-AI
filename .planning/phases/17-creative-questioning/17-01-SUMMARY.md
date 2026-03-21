---
phase: 17-creative-questioning
plan: "01"
subsystem: api
tags: [fastapi, pydantic, supabase, pytest, app-builder, tdd]

# Dependency graph
requires:
  - phase: 16-foundation
    provides: app_projects and build_sessions schema migrations, DB tables with stage CHECK constraints
provides:
  - FastAPI router (app/routers/app_builder.py) with POST /app-builder/projects, GET /app-builder/projects/{id}, PATCH /app-builder/projects/{id}/stage
  - app_builder_router registered in fast_api_app.py
  - 7 unit tests with mocked Supabase covering all three endpoints and auth rejection
affects:
  - 17-creative-questioning (subsequent plans adding wizard UI, AI agent integration)
  - Any phase consuming app-builder project state

# Tech tracking
tech-stack:
  added: []
  patterns:
    - FastAPI dependency_overrides for unit testing HTTPBearer-gated routes without real JWT
    - Dual-table write pattern: create app_projects row then linked build_sessions row in same request handler
    - Literal type alias for stage enum validation via Pydantic (no separate Enum class needed)

key-files:
  created:
    - app/routers/app_builder.py
    - tests/unit/app_builder/test_app_builder_router.py
  modified:
    - app/fast_api_app.py

key-decisions:
  - "Use FastAPI dependency_overrides (not unittest.mock.patch) to bypass HTTPBearer in unit tests — patch cannot intercept security dependencies that fire before the function"
  - "HTTPBearer returns 403 (not 401) for missing Authorization header — this is the established project auth pattern; test asserts actual behavior"
  - "build_sessions row created atomically in same POST handler — state.answers seeded from creative_brief at creation"

patterns-established:
  - "Dependency override pattern: app.dependency_overrides[get_current_user_id] = async_stub for all app-builder unit tests"
  - "Dual-table write: insert into app_projects first (captures project_id), then insert into build_sessions with that project_id"

requirements-completed:
  - FLOW-01

# Metrics
duration: 7min
completed: 2026-03-21
---

# Phase 17 Plan 01: App Builder Router Summary

**FastAPI router for GSD creative workflow — 3 CRUD endpoints backed by mocked-Supabase unit tests, wired into fast_api_app.py**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-21T17:45:56Z
- **Completed:** 2026-03-21T17:52:46Z
- **Tasks:** 2 (TDD: RED scaffold + GREEN implementation)
- **Files modified:** 3

## Accomplishments

- Created `app/routers/app_builder.py` with three endpoints: POST creates project + linked build session at `stage='questioning'`; GET fetches by id+user_id with 404 guard; PATCH advances stage on both `app_projects` and `build_sessions`
- Wired `app_builder_router` into `app/fast_api_app.py` with `tags=["App Builder"]` adjacent to the pages router
- All 7 unit tests pass with mocked Supabase and proper FastAPI `dependency_overrides` auth bypass pattern

## Task Commits

Each task was committed atomically:

1. **Task 1: Write test scaffold for app_builder router** - `73ff7f6` (test — RED state confirmed)
2. **Task 2: Implement app_builder router and register in FastAPI app** - `d9fc802` (feat — GREEN, all 7 pass)

_Note: TDD tasks — test commit first (RED), then implementation commit (GREEN)._

## Files Created/Modified

- `app/routers/app_builder.py` — FastAPI router with POST /app-builder/projects, GET /app-builder/projects/{id}, PATCH /app-builder/projects/{id}/stage; Pydantic Literal stage validation; dual-table writes
- `app/fast_api_app.py` — Added import and `app.include_router(app_builder_router, tags=["App Builder"])` after pages_router line
- `tests/unit/app_builder/test_app_builder_router.py` — 7 unit tests using TestClient + dependency_overrides + MagicMock Supabase chain

## Decisions Made

- Used `app.dependency_overrides` instead of `unittest.mock.patch` for auth mocking — the `HTTPBearer` security dependency fires in the FastAPI middleware layer before the handler function, making patch ineffective
- HTTPBearer returns 403 for missing `Authorization` header (not 401) — this is the existing project pattern from `app/routers/onboarding.py`; the test name retains "401" wording but asserts 403 with an inline docstring explaining the discrepancy

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Auth mock: `patch()` cannot bypass FastAPI's HTTPBearer security dependency**
- **Found during:** Task 2 (implement app_builder router)
- **Issue:** Plan specified `patch("app.routers.app_builder.get_current_user_id")` but HTTPBearer runs in the Starlette dependency graph before the patched function; all requests returned 403 even with patch active
- **Fix:** Replaced `patch` approach with `app.dependency_overrides[get_current_user_id] = async_stub` — the correct FastAPI mechanism for replacing dependencies in tests
- **Files modified:** `tests/unit/app_builder/test_app_builder_router.py`
- **Verification:** All 7 tests pass GREEN after fix
- **Committed in:** `d9fc802` (Task 2 commit)

**2. [Rule 1 - Bug] Auth test status code: HTTPBearer returns 403, not 401**
- **Found during:** Task 2 verification
- **Issue:** Plan said "endpoints without Authorization header return 401" but FastAPI's HTTPBearer returns 403 `{"detail": "Not authenticated"}` by default
- **Fix:** Updated `test_unauthenticated_returns_401` to assert `resp.status_code == 403` with explanatory docstring; no change to production code (existing project behavior)
- **Files modified:** `tests/unit/app_builder/test_app_builder_router.py`
- **Verification:** Test passes; matches behavior of all other router tests in the project
- **Committed in:** `d9fc802` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bug)
**Impact on plan:** Both fixes necessary for correctness. No scope creep. Production router code unchanged from plan spec.

## Issues Encountered

- `test_schema_smoke.py` (pre-existing integration test) fails when `SKIP_INTEGRATION` env var is unset — requires live Supabase credentials. Not caused by this plan's changes; out of scope per scope boundary rules.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `app/routers/app_builder.py` is live and importable; all three endpoints are ready for frontend integration
- Stage transition endpoint (`PATCH /app-builder/projects/{id}/stage`) is the state machine backbone for the GSD creative wizard
- Next plan in Phase 17 should build the frontend questioning wizard that calls these endpoints

---
*Phase: 17-creative-questioning*
*Completed: 2026-03-21*
