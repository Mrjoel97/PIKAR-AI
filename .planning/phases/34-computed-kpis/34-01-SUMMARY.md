---
phase: 34-computed-kpis
plan: "01"
subsystem: api
tags: [kpi, supabase, fastapi, persona, dashboard, computed-metrics]

# Dependency graph
requires:
  - phase: 33-backend-persona-awareness
    provides: resolve_request_persona, persona runtime, behavioral instructions pipeline
provides:
  - KpiService singleton with per-persona KPI computation from live Supabase tables
  - GET /kpis/persona endpoint returning { persona, kpis: [{label, value, unit}] }
  - 21 unit tests covering all 4 personas, label contracts, empty-data safety
affects: [35-teams-rbac, 36-enterprise-governance, 37-sme-dept-coordination, frontend-shell-headers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "KpiService singleton pattern matching DashboardSummaryService (_safe_rows, get_service_client)"
    - "Persona-dispatch via dict mapping to async methods, fallback to solopreneur"
    - "All Supabase queries wrapped in _safe_rows — never raises on empty tables"

key-files:
  created:
    - app/services/kpi_service.py
    - app/routers/kpis.py
    - tests/unit/services/__init__.py
    - tests/unit/services/test_kpi_service.py
  modified:
    - app/fast_api_app.py

key-decisions:
  - "KpiService falls back to solopreneur for unknown/empty personas — safest default"
  - "All percentage values as integer strings (e.g. '42%'), currency via _format_currency helper"
  - "Departments table is user-agnostic (no user_id filter) — reflects org-wide health"
  - "Portfolio Health uses score (0-100 int) unit, not percent, to differentiate from ratio KPIs"

patterns-established:
  - "KPI item shape: {label: str, value: str, unit: str} — uniform across all personas"
  - "Persona dispatch: dict[str, Callable] + fallback avoids if/elif chains"
  - "TDD approach: write 21 failing tests first, then service, verify RED then GREEN"

requirements-completed: [KPI-01, KPI-02, KPI-03, KPI-04, KPI-05]

# Metrics
duration: 9min
completed: 2026-04-03
---

# Phase 34 Plan 01: Computed KPIs Summary

**FastAPI /kpis/persona endpoint returning real Supabase-computed KPIs for all 4 personas — solopreneur (cash/pipeline/content), startup (MRR/conversion/velocity), SME (dept performance/cycle time/compliance), enterprise (portfolio health/risk coverage/reporting)**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-03T14:47:45Z
- **Completed:** 2026-04-03T14:56:28Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- KpiService with 12 persona-specific query methods computing 3 KPIs per persona from live Supabase tables
- GET /kpis/persona endpoint resolving persona from cookie/header and delegating to KpiService
- 21 unit tests covering all 4 personas, correct label contracts, key/value/unit structure, and empty-data edge cases
- Router wired into fast_api_app.py at /kpis prefix, lint and format clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Create KPI computation service (TDD)** - `ccba152` (feat)
2. **Task 2: Create KPI router and wire into FastAPI** - `5c8c455` (feat)

## Files Created/Modified
- `app/services/kpi_service.py` - KpiService class with get_kpi_service() singleton and per-persona compute methods
- `app/routers/kpis.py` - GET /kpis/persona endpoint with persona resolution and rate limiting
- `app/fast_api_app.py` - Added kpis_router import and include_router registration
- `tests/unit/services/__init__.py` - New services test subdirectory init
- `tests/unit/services/test_kpi_service.py` - 21 unit tests across 6 test classes

## Decisions Made
- KpiService falls back to solopreneur for unknown/empty personas — ensures frontend never gets an error for misconfigured persona headers
- Departments table queried without user_id filter (it has no user_id column) — reflects org-wide department health
- Portfolio Health uses "score" unit (0-100 integer) to differentiate from pure-ratio "percent" KPIs
- Currency fallback is "$0" not "No data" — safe numeric default for frontend consumption

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed invalid PLW0603 noqa directive**
- **Found during:** Task 2 (lint verification)
- **Issue:** `# noqa: PLW0603` on `global` statement was invalid — PLW0603 is not in the project's ruff ruleset, causing RUF100 (unused noqa) error
- **Fix:** Removed the noqa comment; the `global` statement passes lint without it
- **Files modified:** app/services/kpi_service.py
- **Verification:** `uv run ruff check` passes with zero errors
- **Committed in:** 5c8c455 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Trivial lint correctness fix. No scope creep.

## Issues Encountered
- `uv` binary not on the default PATH in the bash environment. Located at `/c/Users/expert/AppData/Roaming/Python/Python313/Scripts/uv.exe` and used via `export PATH=...` prefix on all test commands.

## User Setup Required
None - no external service configuration required. The endpoint reads from existing Supabase tables already in production.

## Next Phase Readiness
- GET /kpis/persona is live and returns persona-scoped KPI values from real Supabase tables
- Frontend shell headers can now call this endpoint to replace label-only placeholders with computed values
- Ready for Phase 35 (Teams & RBAC) — KpiService follows the same singleton pattern and can be extended

---
*Phase: 34-computed-kpis*
*Completed: 2026-04-03*
