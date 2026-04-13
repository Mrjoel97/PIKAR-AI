---
phase: 68-data-analytics-enhancement
plan: "02"
subsystem: api
tags: [weekly-report, data-catalog, gemini, supabase, fastapi, analytics]

requires:
  - phase: 68-01
    provides: nl_data_query tool and DataQueryService foundation for Data Agent

provides:
  - WeeklyReportService with Monday-cadence weekly business report generation
  - GET /briefing/weekly-report endpoint returning formatted briefing card
  - suggest_data_reports tool for integration-aware data catalog suggestions
  - generate_weekly_report tool for on-demand weekly report in Data Agent

affects:
  - 68-03
  - briefing frontend (weekly report card display)
  - data-agent consumers

tech-stack:
  added: []
  patterns:
    - AdminService inheritance for service-role DB access in report services
    - Gemini Flash executive summary with template fallback pattern
    - Provider-specific data catalog via static lookup dict (_CATALOG)
    - Lazy WeeklyReportService import inside tool functions (consistent with existing tools pattern)

key-files:
  created:
    - app/services/weekly_report_service.py
    - tests/unit/services/test_weekly_report_service.py
  modified:
    - app/routers/briefing.py
    - app/agents/data/tools.py
    - app/agents/data/agent.py

key-decisions:
  - "WeeklyReportService inherits AdminService (not BaseService) for service-role DB access across all user data"
  - "Anomaly threshold set at 25% WoW change; severity high above 50%"
  - "Gemini Flash used for executive summary with template-based fallback on API failure"
  - "Windows-safe strftime: use curr_start.day integer instead of %-d format directive"
  - "Pre-existing RUF013 lint violations in tools.py not touched (out-of-scope per deviation rules)"

patterns-established:
  - "Provider catalog pattern: _CATALOG dict with fallback to _DEFAULT_CATALOG for unknown providers"
  - "Week boundary calculation: Monday-start using weekday() offset, isolated in _week_boundaries()"

requirements-completed: [DATA-02, DATA-03]

duration: 14min
completed: 2026-04-13
---

# Phase 68 Plan 02: Data Analytics Enhancement — Weekly Reports and Data Catalog Summary

**WeeklyReportService generating Mon-start weekly reports with WoW anomaly detection plus Gemini Flash executive summaries, surfaced via /briefing/weekly-report and two new Data Agent tools**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-13T10:35:47Z
- **Completed:** 2026-04-13T10:49:47Z
- **Tasks:** 2 (TDD: RED + GREEN for Task 1; standard for Task 2)
- **Files modified:** 5

## Accomplishments

- WeeklyReportService aggregates financial_records (current + prior week), computes WoW % changes, flags anomalies >25%, and calls Gemini Flash for a 3-sentence executive summary with template fallback
- GET /briefing/weekly-report endpoint returns a typed briefing card (type, title, summary, sections) ready for frontend display
- suggest_data_reports and generate_weekly_report tools wired into DATA_AGENT_TOOLS with updated CAPABILITIES and BEHAVIOR instruction blocks

## Task Commits

Each task was committed atomically:

1. **Task 1: RED (failing tests)** - `b7369d77` (test)
2. **Task 1: GREEN (WeeklyReportService implementation)** - `fe25d3fd` (feat)
3. **Task 2: briefing endpoint + data tools + agent wiring** - `8bc107bd` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 1 used TDD — separate test commit then implementation commit_

## Files Created/Modified

- `app/services/weekly_report_service.py` — WeeklyReportService(AdminService): generate_weekly_report, get_data_catalog_suggestions, get_available_integrations, format_report_as_briefing_card
- `tests/unit/services/test_weekly_report_service.py` — 9 unit tests covering all public methods and edge cases
- `app/routers/briefing.py` — Added GET /briefing/weekly-report endpoint
- `app/agents/data/tools.py` — Added suggest_data_reports and generate_weekly_report tool functions
- `app/agents/data/agent.py` — Imported both tools, added to DATA_AGENT_TOOLS, updated CAPABILITIES and BEHAVIOR

## Decisions Made

- WeeklyReportService inherits `AdminService` (service-role client) rather than `BaseService` — the service aggregates data across a user's financial records and needs the service-role key for cross-table queries.
- Anomaly threshold: >25% WoW change is flagged; severity is "high" above 50% and "medium" otherwise.
- Gemini Flash selected for executive summary (fast, cheap); graceful degradation to a template-built 3-sentence summary when the API is unavailable.
- Windows-safe strftime: `%-d` (Linux-only) replaced with `curr_start.day` integer interpolation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Windows strftime %-d format not supported**
- **Found during:** Task 1 (GREEN phase — first test run)
- **Issue:** `strftime('%b %-d')` raises ValueError on Windows; %-d is Linux-only
- **Fix:** Changed to `f"{curr_start.strftime('%b')} {curr_start.day}"` for cross-platform compatibility
- **Files modified:** app/services/weekly_report_service.py
- **Verification:** All 9 tests pass after fix
- **Committed in:** fe25d3fd (Task 1 feat commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — platform bug)
**Impact on plan:** Single-line fix, no scope change, no architectural impact.

## Issues Encountered

- Pre-existing RUF013 lint violations in tools.py (implicit `Optional` on existing functions `track_event`, `query_events`, `create_report`, `list_reports`) — these are out of scope per deviation rules; only the new `suggest_data_reports` parameter was fixed.
- Agent instantiation memory limit on Windows venv prevented full `data_agent` object verification; confirmed via `bvisf764h` background task output that tools import correctly and via direct code inspection that both tools appear in DATA_AGENT_TOOLS.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- WeeklyReportService is ready; 68-03 can build on it for scheduled Monday triggers or additional metric sources
- /briefing/weekly-report endpoint is live and returns a typed card — frontend can render immediately
- Data Agent now has both suggest_data_reports and generate_weekly_report tools available
