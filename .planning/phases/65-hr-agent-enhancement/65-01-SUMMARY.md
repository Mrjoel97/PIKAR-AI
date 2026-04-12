---
phase: 65-hr-agent-enhancement
plan: 01
subsystem: agents
tags: [hr, recruitment, job-description, interview-questions, salary-benchmarking, star-method]

# Dependency graph
requires:
  - phase: 0003_complete_schema
    provides: recruitment_jobs table structure
provides:
  - generate_job_description tool with salary benchmarking
  - generate_interview_questions tool with STAR behavioral format and scoring rubric
  - salary_min, salary_max, seniority_level, responsibilities columns on recruitment_jobs
  - RecruitmentService extended with salary field CRUD
affects: [65-hr-agent-enhancement, hr-agent, recruitment-workflows]

# Tech tracking
tech-stack:
  added: []
  patterns: [seniority-based salary bands with department modifiers, STAR behavioral question templates by seniority, department-specific technical question generation]

key-files:
  created:
    - supabase/migrations/20260409200000_recruitment_salary_fields.sql
    - tests/unit/test_hr_job_description_generator.py
  modified:
    - app/agents/hr/tools.py
    - app/agents/hr/agent.py
    - app/services/recruitment_service.py

key-decisions:
  - "Salary bands are computed statically from seniority tier lookup + department modifier rather than LLM-generated, ensuring determinism and testability"
  - "Department modifiers: Engineering/Data +15%, Sales/Marketing +5%, Operations/HR base, Support -10% -- derived from compensation_benchmarking skill framework"
  - "Interview question seniority adjustment: junior=foundational, mid=independent, senior=leadership impact, lead/executive=strategic organizational change"
  - "_build_responsibilities and _build_requirements_must use department-specific template maps rather than LLM generation for consistency across all candidates for a role"

patterns-established:
  - "Salary benchmarking helper (_compute_salary_band): seniority base band * department modifier for deterministic compensation ranges"
  - "Interview question generator pattern: parse competencies from requirements, generate per-competency STAR behavioral + department technical, attach 1/3/5 scoring rubric"

requirements-completed: [HR-01, HR-03]

# Metrics
duration: 15min
completed: 2026-04-12
---

# Phase 65 Plan 01: Job Description Generator & Interview Questions Summary

**Two HR agent tools: generate_job_description with seniority/department salary benchmarking, and generate_interview_questions with STAR behavioral format, department-specific technical questions, and per-competency scoring rubric**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-12T20:54:24Z
- **Completed:** 2026-04-12T21:10:14Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- generate_job_description produces structured JDs with overview, responsibilities (5-8 bullets), requirements (must-haves + nice-to-haves), compensation range, benefits, and application instructions
- Salary ranges are deterministic: seniority base bands (junior $50-75k through executive $180-300k) multiplied by department modifiers (Engineering +15%, Support -10%)
- generate_interview_questions creates STAR behavioral questions per competency with seniority-adjusted complexity, plus department-specific technical questions
- Scoring rubric with 1 (poor), 3 (meets), 5 (excellent) criteria per competency for consistent candidate evaluation
- Both tools wired into HR_AGENT_TOOLS and documented in agent instructions
- 12 dedicated tests plus 7 existing recruitment service tests all passing

## Task Commits

Each task was committed atomically (TDD: test then feat):

1. **Task 1: Job description generator + salary fields** - `7d92f278` (test: RED), `5dd93b64` (feat: GREEN)
2. **Task 2: Interview question generator + agent wiring** - `566bdb39` (test: RED), `ba4082ee` (feat: GREEN)

## Files Created/Modified
- `supabase/migrations/20260409200000_recruitment_salary_fields.sql` - Adds salary_min, salary_max, seniority_level, responsibilities columns
- `app/services/recruitment_service.py` - Extended create_job and update_job with salary field kwargs
- `app/agents/hr/tools.py` - Added generate_job_description, generate_interview_questions, _compute_salary_band, and helper builders
- `app/agents/hr/agent.py` - Wired both new tools into HR_AGENT_TOOLS and updated instruction capabilities
- `tests/unit/test_hr_job_description_generator.py` - 12 tests covering salary computation, JD structure, interview questions, rubric, and department specificity

## Decisions Made
- Salary bands computed statically from seniority tier lookup + department modifier (not LLM-generated) for determinism and testability
- Department modifiers: Engineering/Data +15%, Sales/Marketing +5%, Operations/HR base, Support -10%
- Interview question seniority adjustment: junior=foundational, mid=independent, senior=leadership impact, lead/executive=strategic
- Responsibilities and requirements use department-specific template maps for consistency across all candidates for a role

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Test mock path needed adjustment: tools use lazy `from app.services.request_context import get_current_user_id` inside function bodies, so mock target must be `app.services.request_context.get_current_user_id` not `app.agents.hr.tools.get_current_user_id`. Fixed during GREEN phase.

## User Setup Required

None - no external service configuration required. Migration is SQL artifact only (not applied to live DB automatically).

## Next Phase Readiness
- HR agent now has JD generation and interview question tools ready for 65-02 (hiring funnel visualization)
- Salary fields in recruitment_jobs support future compensation analysis features
- Scoring rubric format established for candidate evaluation pipeline

---
*Phase: 65-hr-agent-enhancement*
*Completed: 2026-04-12*
