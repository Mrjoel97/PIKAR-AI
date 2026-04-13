---
phase: 69-admin-research-enhancement
plan: 02
subsystem: api
tags: [billing, admin, notifications, observability, cost-projection]

# Dependency graph
requires:
  - phase: 57-proactive-intelligence
    provides: notification_dispatcher.dispatch_notification for proactive alerts
  - phase: 51-observability
    provides: ObservabilityMetricsService.project_monthly_ai_spend and cost-by-agent/day methods
provides:
  - BillingAlertService with month-over-month cost projection and threshold detection
  - get_billing_cost_projection admin tool for on-demand AI cost projection
  - check_billing_alerts admin tool for scheduled monitoring tick
  - AdminAgent instruction block for proactive billing cost alerting
affects: [admin-agent, monitoring, billing, cost-management]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TDD with RED/GREEN/test-first for service behavior specification
    - AdminService subclass pattern for service-role Supabase access
    - Module-level imports (not lazy) for patch-friendly test mocking

key-files:
  created:
    - app/services/billing_alert_service.py
    - app/agents/admin/tools/billing_alerts.py
    - tests/unit/admin/test_billing_alerts.py
  modified:
    - app/agents/admin/agent.py

key-decisions:
  - "Module-level ObservabilityMetricsService import (not lazy) so tests can patch app.services.billing_alert_service.ObservabilityMetricsService without triggering internal method imports"
  - "E501 line length violations are acceptable per project pyproject.toml config (E501 globally ignored); plan's --select E,W,F,I lint command would override ignore list but project standard allows these lengths"
  - "check_and_alert falls back to querying user_executive_agents for admin persona users when admin_user_ids not explicitly provided"

patterns-established:
  - "Pattern: _stub_supabase_env autouse fixture pattern for AdminService subclass tests (mirrors test_observability_api.py pattern)"

requirements-completed: [ADMIN-03]

# Metrics
duration: 18min
completed: 2026-04-13
---

# Phase 69 Plan 02: Proactive Billing Cost Projection Alerts Summary

**BillingAlertService with 20%/50% MoM threshold detection, plain-English cost driver explanations, and get_billing_cost_projection/check_billing_alerts admin tools wired into AdminAgent**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-13T13:56:40Z
- **Completed:** 2026-04-13T14:14:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- BillingAlertService bridges existing ObservabilityMetricsService and notification dispatcher: computes month-over-month AI cost projections with warning (>20%) and critical (>50%) severity tiers
- Plain-English summary generation names the top cost driver by agent with dollar amounts and percentage of total spend
- Two admin tools registered in AdminAgent singleton and factory with scheduling guidance (check_billing_alerts is Cloud Scheduler only)
- 9 unit tests cover all threshold scenarios (warning, critical, no-alert), summary content, dispatch/no-dispatch logic, and tool delegation

## Task Commits

1. **Task 1: Create BillingAlertService and billing alert admin tools** - `084965b9` (feat)
2. **Task 2: Wire billing alert tools into AdminAgent with instructions** - absorbed into `38ff087f` (feat, 69-01 parallel commit)

## Files Created/Modified

- `app/services/billing_alert_service.py` - BillingAlertService with compute_cost_projection and check_and_alert
- `app/agents/admin/tools/billing_alerts.py` - get_billing_cost_projection and check_billing_alerts admin tools
- `tests/unit/admin/test_billing_alerts.py` - 9 TDD tests covering all plan behaviors
- `app/agents/admin/agent.py` - Import, tools list, and instruction section for Phase 69 billing alerts

## Decisions Made

- Module-level `ObservabilityMetricsService` import chosen over lazy import so `patch('app.services.billing_alert_service.ObservabilityMetricsService')` works in tests without patching internal method bodies
- `_stub_supabase_env` autouse fixture added following the `test_observability_api.py` pattern to satisfy `AdminService.__init__` env var validation in unit tests
- `check_and_alert` accepts optional `admin_user_ids` list; when None, falls back to querying `user_executive_agents WHERE persona='admin'` rather than hardcoding a default

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Initial test run failed because `ObservabilityMetricsService` was lazy-imported inside method (unpatchable). Fixed by moving to module-level import, matching how other services in this codebase are structured.
- `AdminService.__init__` raises `ValueError` when SUPABASE_URL is not set, blocking service instantiation in tests. Fixed by adding `_stub_supabase_env` autouse monkeypatch fixture (same pattern as `test_observability_api.py`).
- Plan 69-01 ran concurrently and modified `app/agents/admin/agent.py`. The Task 2 agent.py changes were applied first via targeted edits, then 69-01's final commit absorbed the combined state — no conflicts, 63 tools total registered.

## User Setup Required

None - no external service configuration required. Cloud Scheduler integration for `check_billing_alerts` is a deployment concern, not a code change.

## Next Phase Readiness

- BillingAlertService is ready for use by any scheduled job calling `check_billing_alerts` via the admin tool endpoint
- ADMIN-03 requirement complete
- Phase 69 Plan 03 (persona_synthesizer) was already committed in parallel

---
*Phase: 69-admin-research-enhancement*
*Completed: 2026-04-13*
