---
phase: 65-hr-agent-enhancement
plan: 02
subsystem: api
tags: [fastapi, supabase, hiring-funnel, recruitment, kanban, hr-agent]

# Dependency graph
requires:
  - phase: 65-hr-agent-enhancement
    provides: recruitment_candidates and recruitment_jobs tables
provides:
  - HiringFunnelService with get_funnel_for_job and get_funnel_summary
  - GET /api/recruitment/funnel/{job_id} and GET /api/recruitment/funnel endpoints
  - get_hiring_funnel agent tool for HR agent
affects: [65-hr-agent-enhancement, frontend-recruitment-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns: [funnel-stage-aggregation, conversion-rate-computation, lazy-service-import-in-router]

key-files:
  created:
    - app/services/hiring_funnel_service.py
    - app/routers/recruitment.py
    - tests/unit/test_hiring_funnel_service.py
  modified:
    - app/agents/hr/tools.py
    - app/agents/hr/agent.py
    - app/fast_api_app.py

key-decisions:
  - "Funnel stages ordered as applied -> screening -> interviewing -> offer -> hired; rejected tracked separately outside the funnel"
  - "Conversion rate = next_stage_count / current_stage_count (0 when denominator is 0)"

patterns-established:
  - "Funnel aggregation via in-memory counting from flat candidate list rather than SQL GROUP BY for simplicity and testability"
  - "Recruitment router uses lazy service imports to avoid Supabase init at import time"

requirements-completed: [HR-02]

# Metrics
duration: 9min
completed: 2026-04-13
---

# Phase 65 Plan 02: Hiring Funnel Visualization Summary

**HiringFunnelService aggregating candidate counts by 5 pipeline stages with conversion rates, exposed via recruitment API and HR agent tool**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-12T20:53:51Z
- **Completed:** 2026-04-12T21:03:04Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- HiringFunnelService with get_funnel_for_job (per-job stage counts + conversion rates) and get_funnel_summary (all open positions)
- Recruitment API router with GET /api/recruitment/funnel/{job_id} and GET /api/recruitment/funnel endpoints (auth + rate limiting)
- get_hiring_funnel agent tool wired into HR agent with Kanban widget rendering guidance
- 6 passing tests covering stage counting, conversion rates, zero candidates, multi-job summary, and tool integration

## Task Commits

Each task was committed atomically:

1. **Task 1: HiringFunnelService + API router + get_hiring_funnel tool** (TDD)
   - `3943fcd5` (test: add failing tests for hiring funnel service)
   - `cfa2123d` (feat: implement hiring funnel service, API router, and agent tool)
2. **Task 2: Wire recruitment router + funnel tool into app** - `91622a67` (feat)

## Files Created/Modified
- `app/services/hiring_funnel_service.py` - HiringFunnelService with funnel aggregation and conversion rate computation
- `app/routers/recruitment.py` - Recruitment API router with funnel endpoints
- `app/agents/hr/tools.py` - get_hiring_funnel tool appended to Hiring Funnel Tools section
- `app/agents/hr/agent.py` - get_hiring_funnel wired into HR_AGENT_TOOLS + instruction update
- `app/fast_api_app.py` - recruitment_router registered
- `tests/unit/test_hiring_funnel_service.py` - 6 unit tests for service and tool

## Decisions Made
- Funnel stages ordered as applied -> screening -> interviewing -> offer -> hired; rejected tracked separately (not a funnel progression stage)
- Conversion rate = next_stage_count / current_stage_count; returns 0 when current stage has zero candidates to avoid division by zero
- Used in-memory counting from flat candidate status list rather than SQL GROUP BY for simpler testing and fewer DB round-trips

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Hiring funnel API ready for frontend dashboard integration
- HR agent can render funnel data as Kanban board widget
- Coordinates cleanly with 65-01 which added job description and salary tools to the same tools.py file

---
*Phase: 65-hr-agent-enhancement*
*Completed: 2026-04-13*
