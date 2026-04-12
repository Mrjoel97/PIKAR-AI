---
phase: 65-hr-agent-enhancement
plan: 04
subsystem: api
tags: [hr, training, recruitment, degraded-tool-replacement, supabase, rls]

# Dependency graph
requires:
  - phase: 65-01
    provides: HR tools infrastructure (generate_job_description, generate_interview_questions)
provides:
  - Real assign_training tool backed by TrainingService + training_assignments table
  - Real post_job_board tool backed by RecruitmentService (draft-match + publish)
  - Registry entries pointing to real implementations instead of degraded placeholders
affects: [70-degraded-tool-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns: [degraded-to-real tool replacement with registry swap, TDD for tool implementations]

key-files:
  created:
    - app/services/training_service.py
    - supabase/migrations/20260409200002_training_assignments.sql
    - tests/unit/test_hr_real_tools.py
  modified:
    - app/agents/hr/tools.py
    - app/agents/tools/registry.py
    - app/agents/tools/degraded_tools.py
    - app/agents/hr/agent.py

key-decisions:
  - "assign_training creates durable DB record via TrainingService, matching degraded tool's audit-event pattern"
  - "post_job_board searches drafts by case-insensitive title match before creating new published jobs"
  - "Degraded stubs kept with deprecation docstrings for backward compat until Phase 70 cleanup"

patterns-established:
  - "HR tool replacement: lazy service imports inside tool functions for testability"
  - "Registry swap: comment out degraded import + add real import + update dict entry + add HR-06 comment"

requirements-completed: [HR-06]

# Metrics
duration: 11min
completed: 2026-04-12
---

# Phase 65 Plan 04: Degraded Tool Replacement Summary

**Real assign_training (TrainingService + training_assignments table) and post_job_board (draft-match publishing) replacing degraded HR placeholders in tool registry**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-12T21:16:46Z
- **Completed:** 2026-04-12T21:28:04Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created training_assignments table with RLS policies and indexes
- Implemented TrainingService with assign_training, list_assignments, complete_assignment methods
- Built real assign_training tool that creates durable DB records (status="completed" not "degraded_completed")
- Built real post_job_board tool with draft-matching logic and fallback to new job creation
- Swapped registry entries from degraded to real implementations
- Added deprecation docstrings to degraded stubs for Phase 70 cleanup visibility
- Wired both tools into HR agent instruction and tools list
- 7 unit tests covering all tool behaviors

## Task Commits

Each task was committed atomically:

1. **Task 1: TrainingService + migration + real tools + tests (TDD)** - `9db2e6c3` (feat)
2. **Task 2: Registry swap + agent wiring + degraded deprecation** - `db2fb2ac` (feat, co-committed with parallel 64-04 registry changes)

_Note: Task 2 changes were committed alongside parallel 64-04 execution due to shared registry.py file. All HR-06 changes are verified present in the committed state._

## Files Created/Modified
- `supabase/migrations/20260409200002_training_assignments.sql` - training_assignments table with RLS and indexes
- `app/services/training_service.py` - TrainingService with assign/list/complete operations
- `app/agents/hr/tools.py` - Real assign_training and post_job_board tool implementations
- `tests/unit/test_hr_real_tools.py` - 7 tests covering both tools and TrainingService
- `app/agents/tools/registry.py` - Registry entries point to real_assign_training/real_post_job_board
- `app/agents/tools/degraded_tools.py` - Deprecation docstrings on assign_training and post_job_board
- `app/agents/hr/agent.py` - Tools and instructions for assign_training and post_job_board

## Decisions Made
- assign_training creates durable DB record via TrainingService, matching degraded tool's audit-event pattern via track_event
- post_job_board searches drafts by case-insensitive title match before creating new published jobs -- gives existing draft jobs priority over blind creation
- Degraded stubs kept with deprecation docstrings for backward compat until Phase 70 cleanup
- Both tools use lazy imports (import inside function body) for testability without Supabase chain

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Task 2 registry/agent changes were absorbed into parallel 64-04 commit (db2fb2ac) due to shared file modification. Verified all HR-06 changes are present in committed state. No data loss.

## User Setup Required

None - no external service configuration required. Migration is committed as SQL artifact only (not applied to live DB).

## Next Phase Readiness
- HR agent now has 6 real tools: generate_job_description, generate_interview_questions, get_hiring_funnel, assign_training, post_job_board, plus auto_generate_onboarding (from 65-03)
- Phase 70 degraded tool cleanup can now remove assign_training and post_job_board from degraded_tools.py
- Training assignments available for workflow engine use via registry

## Self-Check: PASSED

- All 7 created/modified files verified present on disk
- Commit 9db2e6c3 (Task 1) verified in git log
- Commit db2fb2ac (Task 2 co-commit) verified in git log
- TOOL_REGISTRY["assign_training"].__module__ == "app.agents.hr.tools"
- TOOL_REGISTRY["post_job_board"].__module__ == "app.agents.hr.tools"
- 7/7 tests pass

---
*Phase: 65-hr-agent-enhancement*
*Completed: 2026-04-12*
