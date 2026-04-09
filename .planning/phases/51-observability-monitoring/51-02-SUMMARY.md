---
phase: 51-observability-monitoring
plan: 02
subsystem: api
tags: [health-checks, fastapi, httpx, canonical-json, observability, monitoring]

requires:
  - phase: 51-observability-monitoring
    provides: Phase 51-01 Sentry integration — health endpoints existed but returned bespoke shapes

provides:
  - Canonical versioned health response helper _health_response() in fast_api_app.py
  - All five /health/* endpoints return {status, version, service, latency_ms, details, checked_at}
  - /health/connections includes integrations subkey sourced from integration_sync_state table
  - health_checker._check_one maps canonical ok/degraded/down to healthy/degraded/unhealthy
  - 12 unit tests validating canonical shape contract, version="1", service field, optional integrations

affects: [52-gating, 55-load-testing, admin-panel, health-checker, monitoring-router]

tech-stack:
  added: []
  patterns:
    - Canonical versioned JSON envelope pattern for all health endpoints (version=1, status/service/latency_ms/details/checked_at)
    - Integration health sourced from cached integration_sync_state (zero extra API calls)
    - health_checker maps canonical status to internal DB status before write (translator pattern)

key-files:
  created:
    - tests/unit/test_health_endpoints.py
  modified:
    - app/fast_api_app.py (previously committed in a949a10)
    - app/services/health_checker.py
    - app/routers/admin/monitoring.py

key-decisions:
  - "health_checker._check_one reads canonical JSON body status field and maps ok->healthy, degraded->degraded, down->unhealthy before writing to api_health_checks; falls back to HTTP status code check if JSON parse fails (defensive)"
  - "monitoring.py reads only from api_health_checks table (not from health endpoints directly) so it requires no structural changes — only a docstring update noting Phase 51 canonical shape adoption"
  - "version string set to '1' not integer 1 to allow non-integer versioning in future (v1.1, v2)"

patterns-established:
  - "All /health/* endpoints use _health_response() helper for uniform canonical envelope — never return raw dicts"
  - "Health consumers (health_checker) translate canonical statuses to domain-specific values — they do not store canonical values directly"

requirements-completed: [OBS-05]

duration: 25min
completed: 2026-04-09
---

# Phase 51 Plan 02: Health Endpoints Canonical JSON Summary

**All five /health/* endpoints now return a versioned canonical envelope {status, version, service, latency_ms, details, checked_at} with integration health from integration_sync_state, and health_checker maps canonical status to DB-stored status**

## Performance

- **Duration:** 25 min
- **Started:** 2026-04-09T15:20:00Z
- **Completed:** 2026-04-09T15:45:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- All five /health/* endpoints return canonical versioned JSON envelope — uniform shape regardless of endpoint
- /health/connections includes integrations subkey queried from integration_sync_state (no extra API calls, uses cached sync state)
- health_checker._check_one reads canonical body status field and maps to internal DB status with fallback to HTTP-status-only check
- 12 unit tests covering: all required fields present, version="1", correct service field, status constraints, optional integrations, checked_at ISO format, and canonical-to-internal status mapping
- ruff linting passes on all modified Python files

## Task Commits

1. **Task 1: Refactor /health/* endpoints to canonical JSON** - `a949a10` (feat) — committed by prior agent
2. **Task 2: Update health checker + monitoring + tests** - `59dba64` (feat)

## Files Created/Modified

- `app/fast_api_app.py` — _health_response() helper + all 5 /health/* endpoints refactored (a949a10)
- `app/services/health_checker.py` — _check_one() now parses canonical body status field
- `app/routers/admin/monitoring.py` — docstring updated noting Phase 51 canonical shape adoption
- `tests/unit/test_health_endpoints.py` — 12 unit tests for canonical shape contract (created)

## Decisions Made

- health_checker maps canonical "ok" -> "healthy", "degraded" -> "degraded", "down" -> "unhealthy" before writing to api_health_checks. This preserves backward compatibility with the DB schema CHECK constraint (status IN ('healthy', 'unhealthy', 'degraded')) while adopting the canonical shape at the endpoint level.
- monitoring.py reads from api_health_checks only (not from health endpoints directly), so it requires no structural changes — only a docstring update to note Phase 51 adoption.
- version is the string "1" (not integer) to allow non-integer future versions.
- JSON parse fallback in health_checker: if body parsing fails, falls back to HTTP status code check (defensive — should not occur but safe).

## Deviations from Plan

None - plan executed exactly as written. health_checker update and monitoring.py docstring update matched plan Task 2 specification precisely.

## Issues Encountered

- 4 ruff lint errors in the test file (RUF012 mutable class attributes, RUF100 unused noqa directive) — fixed by adding ClassVar annotations and removing unused noqa directive. All 12 tests pass after fix.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All five /health/* endpoints now have a stable canonical shape consumable by monitors, dashboards, and load tests
- health_checker writes correctly translated statuses to api_health_checks — monitoring dashboard in Phase 51-03/04 reads from this table and is unaffected
- Ready for Phase 52 gating and Phase 55 load testing

---
*Phase: 51-observability-monitoring*
*Completed: 2026-04-09*
