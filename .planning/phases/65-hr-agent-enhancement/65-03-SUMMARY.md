---
phase: 65-hr-agent-enhancement
plan: 03
subsystem: api, database, agents
tags: [onboarding, org-chart, hr, recruitment, supabase, rls]

# Dependency graph
requires:
  - phase: 65-01
    provides: generate_job_description, generate_interview_questions, salary benchmarking in recruitment_service
provides:
  - auto_generate_onboarding tool with department-specific checklists
  - get_team_org_chart tool with reporting relationships and vacancy nodes
  - TeamOrgService with CRUD for team members and org chart aggregation
  - team_members table with RLS, reporting_to FK, candidate/job FKs
  - API endpoints for org chart and onboarding generation
affects: [65-hr-agent-enhancement, onboarding, org-chart]

# Tech tracking
tech-stack:
  added: []
  patterns: [department-specific equipment maps, seniority-milestone maps, vacancy-from-published-jobs]

key-files:
  created:
    - app/services/team_org_service.py
    - supabase/migrations/20260409200001_team_org_structure.sql
    - tests/unit/test_hr_onboarding_orgchart.py
  modified:
    - app/agents/hr/tools.py
    - app/agents/hr/agent.py
    - app/routers/recruitment.py

key-decisions:
  - "Department equipment maps are static lookup tables (not LLM) for determinism and testability"
  - "Seniority milestones span junior through executive with role-appropriate 30-60-90 day goals"
  - "Vacancy nodes derived from published jobs without a matching team_member record (filled_job_ids set difference)"
  - "Org chart department filter uses case-insensitive matching for resilience"

patterns-established:
  - "Department equipment maps: static dict keyed by dept name, combined with standard items for pre-boarding"
  - "Seniority milestone maps: static dict keyed by level (junior-executive) with 30/60/90 day goals"
  - "Vacancy detection: set difference between published job IDs and team_member.job_id values"

requirements-completed: [HR-04, HR-05]

# Metrics
duration: 14min
completed: 2026-04-12
---

# Phase 65 Plan 03: Auto-Onboarding & Team Org Chart Summary

**Department-specific onboarding checklists with 30-60-90 milestones, team org chart with reporting hierarchy and vacancy nodes from published jobs**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-12T21:15:31Z
- **Completed:** 2026-04-12T21:30:11Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Auto-onboarding generates department-specific checklists (Engineering gets IDE/monitors, Marketing gets design/analytics tools, etc.) with seniority-appropriate 30-60-90 milestones
- Team org chart shows human team members with reporting relationships and vacancy nodes from published recruitment jobs
- Three new API endpoints (org-chart, org-chart by department, onboarding generation) added to recruitment router
- HR agent instruction tells it to auto-trigger onboarding when a candidate is marked as hired

## Task Commits

Each task was committed atomically:

1. **Task 1: team_members migration + TeamOrgService + tools** (TDD)
   - `9833a70b` (test: add failing tests — RED)
   - `a70fc0a6` (feat: implement auto-onboarding checklist and team org chart — GREEN)
2. **Task 2: Wire tools + API endpoints** - `79bbecdd` (feat)

## Files Created/Modified
- `supabase/migrations/20260409200001_team_org_structure.sql` - team_members table with RLS, indexes, FK references
- `app/services/team_org_service.py` - TeamOrgService with add/get/update team members and org chart aggregation
- `app/agents/hr/tools.py` - auto_generate_onboarding and get_team_org_chart tools with department equipment/training maps
- `app/agents/hr/agent.py` - Import and wire both tools, add agent instruction for auto-onboarding on hire
- `app/routers/recruitment.py` - GET /org-chart, GET /org-chart/{dept}, POST /onboarding/{candidate_id}
- `tests/unit/test_hr_onboarding_orgchart.py` - 7 tests covering onboarding, org chart, and service layer

## Decisions Made
- Department equipment maps are static lookup tables (not LLM) for determinism and testability
- Seniority milestones span junior through executive with role-appropriate 30-60-90 day goals
- Vacancy nodes derived from published jobs without a matching team_member record (filled_job_ids set difference)
- Org chart department filter uses case-insensitive matching for resilience

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- HR agent now has 60 tools covering full recruitment lifecycle: JD generation, interview questions, hiring funnel, onboarding, and org chart
- team_members table migration ready for application via `supabase db push --local`
- Onboarding and org chart API endpoints available for frontend integration

## Self-Check: PASSED

All 6 files verified present. All 3 commits verified in git log.

---
*Phase: 65-hr-agent-enhancement*
*Completed: 2026-04-12*
