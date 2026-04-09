---
phase: 51-observability-monitoring
plan: 03
subsystem: api
tags: [observability, telemetry, metrics, fastapi, supabase, percentiles, ai-cost]

# Dependency graph
requires:
  - phase: 51-observability-monitoring
    provides: agent_telemetry table (20260320400000_telemetry_schema.sql), AdminService base class
  - phase: 50-billing-payments
    provides: BillingMetricsService pattern (AdminService inheritance, execute_async queries)
provides:
  - agent_latency_rollups Supabase table with hourly pre-computed percentiles
  - ObservabilityMetricsService with p50/p95/p99 latency, error rate, AI cost, monthly projection, rollup job, threshold alerting
  - GET /admin/observability/summary — hero metrics (error rate 24h, MTD AI spend, p95 latency)
  - GET /admin/observability/latency — percentiles by agent and window
  - GET /admin/observability/errors — error rate by agent and window
  - GET /admin/observability/cost — AI token cost by agent/user/day
  - POST /admin/observability/run-rollup — Cloud Scheduler hourly rollup entry point
affects: [51-04-frontend-dashboard, 52-persona-gating, 55-load-testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hybrid 24h live/rollup latency strategy: direct agent_telemetry for <= 24h, pre-computed agent_latency_rollups for > 24h"
    - "Python-side percentile_cont: linear interpolation over sorted duration_ms list (same semantics as PostgreSQL percentile_cont)"
    - "AI cost approximation: gemini-2.5-pro pricing applied to all agents (agent_telemetry lacks model-name column)"
    - "Error threshold alerting: monitoring_loop source writes observability.threshold_breach to admin_audit_log"
    - "Service-role-only rollup: run-rollup gated by verify_service_auth (X-Service-Secret), not require_admin"

key-files:
  created:
    - supabase/migrations/20260409000000_agent_latency_rollups.sql
    - app/services/observability_metrics_service.py
    - app/routers/admin/observability.py
    - tests/unit/services/test_observability_metrics_service.py
    - tests/unit/admin/test_observability_api.py
  modified:
    - app/routers/admin/__init__.py

key-decisions:
  - "Hybrid latency strategy: <= 24h uses live agent_telemetry (Python percentile computation), > 24h uses pre-computed agent_latency_rollups — keeps dashboard fast at solopreneur scale without full table scans"
  - "Python-side percentile computation: Supabase Python SDK does not support raw SQL; sorting duration_ms and using linear interpolation produces identical results to percentile_cont at current data volumes"
  - "gemini-2.5-pro default pricing for all agents: agent_telemetry lacks model-name column; primary model is 2.5-pro (CLAUDE.md), approximation documented in module docstring and class docstring"
  - "run-rollup uses verify_service_auth (not require_admin): Cloud Scheduler calls this as a service-to-service job, same pattern as /admin/monitoring/run-check"
  - "Error threshold breach writes to admin_audit_log with source=monitoring_loop (not manual): consistent with existing audit log conventions"

patterns-established:
  - "ObservabilityMetricsService follows BillingMetricsService: AdminService inheritance, ClassVar constants, all-async public methods, execute_async for every Supabase call"
  - "TDD RED/GREEN: write failing test file first, then implement service/router, then fix test issues (verify_service_auth signature discovery)"
  - "Windows-safe test stub: sys.modules stub for app.middleware.rate_limiter before importing routers (established Phase 49-05, applied here)"

requirements-completed: [OBS-02, OBS-03, OBS-04]

# Metrics
duration: 24min
completed: 2026-04-09
---

# Phase 51 Plan 03: ObservabilityMetricsService and Admin API Summary

**ObservabilityMetricsService with hybrid latency percentiles (p50/p95/p99), error rate tracking, AI token cost by agent/user/day with monthly projection, and 5-endpoint admin API — backend data layer for Plan 51-04 dashboard.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-04-09T08:55:32Z
- **Completed:** 2026-04-09T09:19:19Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Created `agent_latency_rollups` migration with unique index for upsert idempotency and service-role-only RLS policy
- Built `ObservabilityMetricsService(AdminService)` with 8 async methods: `compute_latency_percentiles`, `compute_error_rate`, `compute_ai_cost_by_agent`, `compute_ai_cost_by_user`, `compute_ai_cost_by_day`, `project_monthly_ai_spend`, `run_hourly_rollup`, `check_error_threshold`
- Delivered 5-endpoint admin observability router (all GET routes gated by `require_admin`, POST run-rollup gated by `verify_service_auth`), registered in `admin_router`
- 19 unit tests pass: 14 service tests (percentile helper, latency, error rate, AI cost, monthly projection, AdminService inheritance) and 5 router tests (import, route paths, auth gates, summary fields)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create rollup migration and ObservabilityMetricsService** - `912bffd` (feat)
2. **Task 2: Create admin observability router, register it, and add tests** - `c2641f3` (feat + TDD)

## Files Created/Modified

- `supabase/migrations/20260409000000_agent_latency_rollups.sql` - Hourly pre-computed percentile table with unique index and RLS
- `app/services/observability_metrics_service.py` - ObservabilityMetricsService extending AdminService (8 compute methods, AI_MODEL_PRICING constant, _percentile helper)
- `app/routers/admin/observability.py` - 5 admin endpoints (summary, latency, errors, cost, run-rollup) with correct auth gates
- `app/routers/admin/__init__.py` - Added observability router registration (Phase 51 comment)
- `tests/unit/services/test_observability_metrics_service.py` - 14 tests (358 lines)
- `tests/unit/admin/test_observability_api.py` - 5 tests (234 lines)

## Decisions Made

- **Hybrid latency strategy**: windows <= 24h query live `agent_telemetry` (Python-side percentile computation); windows > 24h query pre-computed `agent_latency_rollups`; windows spanning the boundary union both. Keeps dashboard responsive at solopreneur scale.
- **Python-side percentile computation**: Supabase Python SDK cannot execute raw SQL; sorting `duration_ms` rows and applying linear interpolation (`_percentile`) produces identical results to PostgreSQL `percentile_cont` at current data volumes.
- **gemini-2.5-pro default for AI cost**: `agent_telemetry` does not store the model name per event. Primary model is `gemini-2.5-pro` (per CLAUDE.md). Approximation documented in module docstring, class docstring, and this summary.
- **`run-rollup` uses `verify_service_auth` not `require_admin`**: Cloud Scheduler calls this as a service-to-service job. Mirrors the `/admin/monitoring/run-check` pattern from Phase 8.
- **Error threshold writes to `admin_audit_log` with `source="monitoring_loop"`**: Consistent with existing audit conventions. `admin_user_id=None` for automated checks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test asserting `isinstance(result, float)` for `mtd_actual`**
- **Found during:** Task 2 (TDD GREEN phase)
- **Issue:** `sum([])` returns Python `int(0)`, not `float(0.0)`; test was too strict
- **Fix:** Changed assertion to `isinstance(result, (int, float))` — semantically correct
- **Files modified:** `tests/unit/services/test_observability_metrics_service.py`
- **Verification:** Test passes with both 0 (int) and 0.0 (float) return values
- **Committed in:** `c2641f3` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed `verify_service_auth` test using wrong call signature**
- **Found during:** Task 2 (TDD GREEN phase, router auth test)
- **Issue:** Test called `verify_service_auth(request=request)` but the function uses `Header` dependency (`x_service_secret` parameter), not `Request`
- **Fix:** Changed test to call `verify_service_auth(x_service_secret=None)` directly to simulate missing header
- **Files modified:** `tests/unit/admin/test_observability_api.py`
- **Verification:** Test correctly raises `HTTPException(401)` on missing secret
- **Committed in:** `c2641f3` (Task 2 commit)

**3. [Rule 1 - Bug] Fixed ruff RUF003 (EN DASH in comment)**
- **Found during:** Lint check after Task 1
- **Issue:** Comment contained EN DASH character (`–`) instead of HYPHEN-MINUS (`-`)
- **Fix:** Replaced `13:00–14:00` with `13:00-14:00` in service module comment
- **Files modified:** `app/services/observability_metrics_service.py`
- **Verification:** `ruff check` reports "All checks passed!"
- **Committed in:** `c2641f3` (part of Task 2 lint-clean commit)

---

**Total deviations:** 3 auto-fixed (Rule 1 — all correctness fixes in test code and lint)
**Impact on plan:** All three fixes are correctness issues in test assertions and style. No scope creep. Implementation matches plan spec exactly.

## Issues Encountered

- `uv` is not on the Git Bash PATH on this Windows machine; used `.venv/Scripts/python.exe` directly for all Python invocations. Same pattern as prior phases — not a blocker.

## User Setup Required

None — no external service configuration required. The `run-rollup` endpoint connects to Cloud Scheduler via existing `WORKFLOW_SERVICE_SECRET` (already configured in Phase 8).

## Next Phase Readiness

- Backend data layer for OBS-02/OBS-03/OBS-04 is complete
- Plan 51-04 (frontend observability dashboard) can now consume all 5 `/admin/observability/*` endpoints
- `run-rollup` endpoint is ready for Cloud Scheduler registration (same pattern as `/admin/monitoring/run-check`)
- Error threshold alerting is live; any agent error spike > 5% over 10 min writes to `admin_audit_log`

---
*Phase: 51-observability-monitoring*
*Completed: 2026-04-09*
