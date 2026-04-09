---
phase: 57-proactive-intelligence-layer
plan: 03
subsystem: monitoring, integrations
tags: [oauth, health-check, competitor-intelligence, proactive-alerts, cloud-scheduler]

# Dependency graph
requires:
  - phase: 57-01
    provides: ProactiveAlertService with dispatch_proactive_alert and proactive_alert_log dedup
provides:
  - IntegrationHealthMonitor for proactive OAuth token expiry detection
  - Connectivity health checks for Google, Slack, Stripe providers
  - Competitor change classification (pricing, launch, funding, acquisition, partnership)
  - Proactive alert dispatch wired into monitoring_job_service research pipeline
  - Cloud Scheduler endpoint /scheduled/integration-health-tick
affects: [57-04, 57-05, scheduled-endpoints, monitoring-jobs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Proactive health monitoring with per-provider connectivity checks"
    - "Keyword-based competitor change classification with metadata category override"
    - "Lazy-wrapper pattern for dispatch_proactive_alert in monitoring_job_service"

key-files:
  created:
    - app/services/integration_health_monitor.py
    - tests/unit/services/test_integration_health_monitor.py
    - tests/unit/services/test_monitoring_alert_dispatch.py
  modified:
    - app/services/monitoring_job_service.py
    - app/services/scheduled_endpoints.py

key-decisions:
  - "MVP connectivity checks limited to Google, Slack, Stripe -- providers with simple bearer-token health endpoints"
  - "Competitor change classification uses keyword matching (no LLM call) for low-latency inline classification"
  - "IntegrationHealthMonitor uses get_service_client directly (not AdminService inheritance) matching ProactiveAlertService pattern"

patterns-established:
  - "CONNECTIVITY_CHECK_PROVIDERS dict for extensible provider health-check URLs"
  - "_SIGNIFICANT_CATEGORIES frozenset for confidence-independent alert triggers"
  - "_CHANGE_TYPE_KEYWORDS ordered keyword list for first-match classification"

requirements-completed: [PROACT-03, PROACT-04]

# Metrics
duration: 13min
completed: 2026-04-09
---

# Phase 57 Plan 03: Competitor Monitoring Alerts and Integration Health Summary

**Competitor change classification with 5 alert types wired into monitoring pipeline, plus OAuth token expiry and connectivity health checks via IntegrationHealthMonitor**

## Performance

- **Duration:** 13 min
- **Started:** 2026-04-09T22:26:05Z
- **Completed:** 2026-04-09T22:39:22Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- IntegrationHealthMonitor detects OAuth tokens expiring within 3 days and dispatches WARNING alerts with provider name, days remaining, and reconnect link
- Connectivity checks for Google, Slack, Stripe endpoints dispatch ERROR alerts when provider connections fail
- Competitor monitoring research findings now trigger proactive alerts via dispatch_proactive_alert when confidence > 0.7 or category matches significant types
- Competitor changes classified into 5 types: pricing_change, product_launch, funding_round, acquisition, partnership
- Cloud Scheduler endpoint /scheduled/integration-health-tick for daily health checks
- 22 total tests passing (10 integration health + 12 monitoring alert dispatch)

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: IntegrationHealthMonitor** - `d9944b61` (test: RED), `fe5e4bea` (feat: GREEN)
2. **Task 2: Competitor alerts + Cloud Scheduler** - `1f4ab3f2` (test: RED), `3237c8a3` (feat: GREEN)

_TDD tasks have RED (failing test) then GREEN (implementation) commits._

## Files Created/Modified
- `app/services/integration_health_monitor.py` - Proactive token expiry and connectivity health monitoring
- `app/services/monitoring_job_service.py` - Added _classify_competitor_change, _dispatch_monitoring_alert, dispatch_proactive_alert lazy wrapper
- `app/services/scheduled_endpoints.py` - Added /scheduled/integration-health-tick endpoint, updated monitoring-tick to report alerts_dispatched
- `tests/unit/services/test_integration_health_monitor.py` - 10 tests for token expiry, connectivity, alert dispatch
- `tests/unit/services/test_monitoring_alert_dispatch.py` - 12 tests for change classification, confidence filtering, alert format

## Decisions Made
- MVP connectivity checks limited to Google, Slack, Stripe -- these have simple bearer-token health endpoints; Meta and HubSpot require specific scopes and complex auth flows
- Competitor change classification uses keyword matching (not LLM) -- fast, deterministic, and sufficient for the 5 core change types; LLM enrichment can be added later
- IntegrationHealthMonitor follows same pattern as ProactiveAlertService (direct get_service_client + execute_async) rather than inheriting AdminService

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed execute_async side_effect count in tests**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Tests provided 2 side_effect values for execute_async but check_connectivity calls it once per provider (3 providers = 4 total calls)
- **Fix:** Updated all run_integration_health_check tests to provide correct number of side_effect values
- **Files modified:** tests/unit/services/test_integration_health_monitor.py
- **Verification:** All 10 tests pass
- **Committed in:** fe5e4bea (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Test mock count correction, no scope creep.

## Issues Encountered
- `uv` command not directly available in bash shell; resolved by using `cmd.exe //c "uv run ..."` pattern for all test and lint commands

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Proactive alert infrastructure complete: daily briefings (Plan 01), anomaly detection (Plan 02), competitor monitoring + integration health (Plan 03)
- All alert dispatch goes through ProactiveAlertService with deduplication
- Ready for Plans 04-05 (stalled initiative nudges, scheduled digests, or other proactive alert types)

## Self-Check: PASSED

All 5 files verified present. All 4 commits verified in git log.

---
*Phase: 57-proactive-intelligence-layer*
*Completed: 2026-04-09*
