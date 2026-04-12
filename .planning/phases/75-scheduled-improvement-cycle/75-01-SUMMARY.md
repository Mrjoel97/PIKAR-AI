---
phase: 75-scheduled-improvement-cycle
plan: 01
subsystem: api, database
tags: [fastapi, supabase, cloud-scheduler, self-improvement, risk-tiers]

requires:
  - phase: 72-skill-refinement-persistence
    provides: SelfImprovementEngine with skill version persistence and write-through
provides:
  - POST /scheduled/self-improvement-cycle endpoint for Cloud Scheduler
  - self_improvement_settings table and settings service for admin configuration
  - Risk-tiered auto_execute gating (low-risk auto-execute, high-risk pending_approval)
  - Expanded improvement_actions constraints (pattern_extract, investigate, pending_approval, declined)
  - Cloud Scheduler runbook for daily 03:00 UTC trigger
affects: [75-02-scheduled-improvement-cycle, admin-panel]

tech-stack:
  added: []
  patterns: [risk-tiered execution gating, admin settings table pattern]

key-files:
  created:
    - supabase/migrations/20260412200000_scheduled_improvement_cycle.sql
    - app/services/self_improvement_settings.py
    - docs/runbooks/self-improvement-scheduler.md
  modified:
    - app/services/self_improvement_engine.py
    - app/services/scheduled_endpoints.py
    - tests/unit/test_scheduled_improvement_cycle.py

key-decisions:
  - "Risk-tier gating replaces priority-based auto_execute: action_type determines execution eligibility, not priority level"
  - "Settings stored as individual JSONB rows keyed by setting name for simple upsert pattern"
  - "auto_execute_enabled defaults to false; admin must explicitly enable after reviewing risk tiers"

patterns-established:
  - "Admin settings table pattern: key-value JSONB rows with updated_by audit trail"
  - "Risk-tier gating: action types in configurable list auto-execute, others queue for approval"

requirements-completed: [SCH-01, SCH-02, SCH-03, SCH-04]

duration: 9min
completed: 2026-04-12
---

# Phase 75 Plan 01: Scheduled Improvement Cycle Summary

**Risk-tiered scheduled endpoint with admin settings controlling which self-improvement actions auto-execute vs queue for approval**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-12T17:52:38Z
- **Completed:** 2026-04-12T18:01:51Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Scheduled endpoint POST /scheduled/self-improvement-cycle with X-Scheduler-Secret gating
- Risk-tiered execution: skill_demoted and pattern_extract auto-execute, skill_refined and skill_created queue as pending_approval
- Admin settings service with get/update for auto_execute_enabled and risk_tiers configuration
- Migration expanding improvement_actions constraints and adding approval tracking columns
- Cloud Scheduler runbook with gcloud setup, monitoring, and troubleshooting

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration + settings service + risk-tiered engine** - `1d0de82d` (test: RED), `88545ffc` (feat: GREEN)
2. **Task 2: Scheduled endpoint + Cloud Scheduler runbook** - `31314585` (feat)

## Files Created/Modified
- `supabase/migrations/20260412200000_scheduled_improvement_cycle.sql` - New table + constraint expansions + approval columns
- `app/services/self_improvement_settings.py` - Settings read/write service with defaults fallback
- `app/services/self_improvement_engine.py` - Risk-tiered run_improvement_cycle replacing priority-based gating
- `app/services/scheduled_endpoints.py` - POST /scheduled/self-improvement-cycle endpoint
- `tests/unit/test_scheduled_improvement_cycle.py` - 5 tests covering all risk-tier behaviors
- `docs/runbooks/self-improvement-scheduler.md` - Cloud Scheduler configuration and operations runbook

## Decisions Made
- Risk-tier gating replaces priority-based auto_execute: action_type determines execution eligibility, not priority level
- Settings stored as individual JSONB rows keyed by setting name for simple upsert pattern
- auto_execute_enabled defaults to false; admin must explicitly enable after reviewing risk tiers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Cloud Scheduler job creation is documented in the runbook for when deployment is ready.

## Next Phase Readiness
- Risk-tiered execution is live; Plan 75-02 can build the circuit breaker that auto-disables on regression
- Settings service is ready for admin panel integration
- pending_approval and declined statuses are available for approval workflow in future plans

---
*Phase: 75-scheduled-improvement-cycle*
*Completed: 2026-04-12*
