---
phase: 37-sme-department-coordination
plan: "01"
subsystem: database, api
tags: [supabase, postgres, fastapi, pydantic, rls, department-tasks, health-metrics]

# Dependency graph
requires:
  - phase: 36-enterprise-governance
    provides: _governance_set_updated_at trigger function used by department_tasks updated_at trigger
  - phase: 32-feature-gating
    provides: persona-based access control patterns used in SME task write gate
provides:
  - department_tasks Postgres table with cross-department handoff schema
  - department_health_summary SQL view (green/yellow/red per 30-day completion rate)
  - DepartmentTaskService with CRUD and health computation
  - 4 REST endpoints on departments router for task management and health
affects:
  - 37-02 (if exists - any frontend plan consuming these endpoints)
  - 37-03 (SME department dashboard frontend)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Singleton service pattern (same as KpiService, DepartmentRunner)
    - execute_async for all DB calls with op_name for tracing
    - Persona gate via synchronous user table lookup before async operations
    - Partial index strategy: WHERE status IN ('pending', 'in_progress') for active-task queries

key-files:
  created:
    - supabase/migrations/20260403400000_department_tasks.sql
    - app/services/department_task_service.py
  modified:
    - app/routers/departments.py

key-decisions:
  - "department_tasks is distinct from inter_dept_requests: user-initiated handoffs vs autonomous coordination"
  - "Health view lives in SQL (not Python) for correctness at query time without caching"
  - "SME persona allowed alongside enterprise/startup for task creation (plan requirement)"
  - "Partial indexes on status IN ('pending', 'in_progress') to keep active-task queries fast as table grows"

patterns-established:
  - "Partial index pattern: idx on (col, status) WHERE status IN (...active...) — copy for future task-like tables"
  - "Singleton service: _instance variable + get_X_service() factory — matches KpiService, DepartmentRunner"
  - "Department name enrichment: collect dept UUIDs, single .in_() lookup, map into rows — matches existing requests endpoint"

requirements-completed: [DEPT-01, DEPT-02]

# Metrics
duration: 9min
completed: 2026-04-03
---

# Phase 37 Plan 01: SME Department Coordination Backend Summary

**department_tasks table with RLS/indexes, department_health_summary SQL view, DepartmentTaskService singleton, and 4 REST endpoints enabling cross-department handoffs with green/yellow/red health computation**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-03T19:46:39Z
- **Completed:** 2026-04-03T19:56:29Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- SQL migration creates department_tasks table with CHECK constraints on status/priority, 4 targeted indexes (including 2 partial), RLS policies, and auto-updated_at trigger reusing _governance_set_updated_at from Phase 36
- department_health_summary view computes per-department health in pure SQL using FILTER aggregates — green (>80% or no tasks), yellow (50-80%), red (<50%) based on 30-day window
- DepartmentTaskService singleton (5 methods: create_task, list_tasks, get_task, update_task_status, get_department_health) follows KpiService/DepartmentRunner patterns with execute_async and op_name tracing
- 4 new endpoints on departments router with rate limiting, auth, persona gate (SME/enterprise/startup for writes), Pydantic request models, and full docstrings

## Task Commits

Each task was committed atomically:

1. **Task 1: Create department_tasks migration** - `7ba2466` (feat)
2. **Task 2: DepartmentTaskService and API endpoints** - `74ebebf` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `supabase/migrations/20260403400000_department_tasks.sql` - department_tasks table, 4 indexes, RLS, updated_at trigger, department_health_summary view
- `app/services/department_task_service.py` - DepartmentTaskService singleton with CRUD + health methods
- `app/routers/departments.py` - Added CreateDepartmentTaskRequest, UpdateTaskStatusRequest Pydantic models + 4 new endpoints

## Decisions Made
- **department_tasks vs inter_dept_requests**: Kept them separate — inter_dept_requests is for autonomous department-to-department coordination; department_tasks is for user-visible SME dashboard handoffs. Different lifecycle, different consumers.
- **Health view in SQL not Python**: The view computes health at query time using SQL FILTER aggregates, avoiding stale cached values. No Python computation layer needed.
- **SME persona included in write gate**: Plan required SME users to create tasks (alongside enterprise/startup), so `_ALLOWED_TASK_PERSONAS = {"sme", "enterprise", "startup"}` — different from the existing toggle_department gate which only allows enterprise/startup.
- **Partial indexes**: `idx_dept_tasks_to_dept_status` and `idx_dept_tasks_due_date` use WHERE predicates filtering to active statuses only, keeping index small as completed/cancelled tasks accumulate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed EN DASH characters in docstrings (RUF002)**
- **Found during:** Task 2 (after running ruff check)
- **Issue:** Two docstrings used EN DASH (–) instead of HYPHEN-MINUS (-), triggering RUF002
- **Fix:** Replaced both EN DASH characters with standard hyphens in departments.py docstrings
- **Files modified:** app/routers/departments.py
- **Verification:** `ruff check` reports "All checks passed!"
- **Committed in:** 74ebebf (Task 2 commit — fixed before commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - lint/formatting)
**Impact on plan:** Trivial character fix. No scope creep.

## Issues Encountered
- `uv` not on default PATH in shell environment — located at `/c/Users/expert/AppData/Roaming/Python/Python313/Scripts/uv.exe`. Used extended PATH for all subsequent uv commands.
- Router import verification failed with UnicodeDecodeError (pre-existing: rate limiter reads .env with cp1252 codec). Used static AST/regex analysis to confirm all 4 routes were correctly registered — verified via `re.findall` on router source.

## User Setup Required
None - no external service configuration required. Migration will be applied via `supabase db push` as part of normal deployment.

## Next Phase Readiness
- Backend data layer complete: table, view, service, and endpoints are ready for frontend consumption
- Plan 03 (SME department dashboard frontend) can now build against:
  - `POST /departments/tasks` — create handoffs
  - `GET /departments/{dept_id}/tasks` — list with inbound/outbound direction
  - `PATCH /departments/tasks/{task_id}/status` — status transitions
  - `GET /departments/health` — health summary for all departments
- No blockers

---
*Phase: 37-sme-department-coordination*
*Completed: 2026-04-03*
