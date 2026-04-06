---
phase: 46-analytics-continuous-intelligence
plan: "01"
subsystem: database
tags: [postgresql, bigquery, external-db, nl-to-sql, agent-tools, read-only, psycopg2]

requires: []
provides:
  - "ExternalDbQueryService with read-only PostgreSQL and BigQuery query execution"
  - "EXTERNAL_DB_TOOLS agent tools list (external_db_query, confirm_and_run_query, list_db_connections)"
  - "postgresql ProviderConfig entry in PROVIDER_REGISTRY"
  - "monitoring_jobs migration table with RLS policies"
affects:
  - 46-analytics-continuous-intelligence
  - data-agent
  - integration-providers

tech-stack:
  added: [psycopg2 (lazy), google.cloud.bigquery (lazy), google.oauth2.service_account (lazy)]
  patterns:
    - "Lazy imports inside method bodies to prevent import-time failures"
    - "asyncio.to_thread wrapping sync DB drivers for async compatibility"
    - "asyncio.wait_for outer timeout + server-side statement_timeout double guard"
    - "sys.modules stub injection for unavailable C-extension libraries in tests"
    - "Patch at service module level (not tool module) for lazy-import tools"

key-files:
  created:
    - app/services/external_db_service.py
    - app/agents/tools/external_db_tools.py
    - supabase/migrations/20260406000000_external_db_monitoring.sql
    - tests/unit/test_external_db_service.py
    - tests/unit/tools/test_external_db_tools.py
    - tests/unit/tools/__init__.py
  modified:
    - app/config/integration_providers.py

key-decisions:
  - "postgresql registered as api_key provider (no OAuth) — connection string passed directly as credential"
  - "asyncio.wait_for(timeout=timeout_sec+2) outer guard supplements server-side statement_timeout for hung connections"
  - "classify_sql uses regex keyword heuristics — multiple SELECT count for subquery detection"
  - "date keyword 'at' removed from heuristic — caused false-positive line chart for column named 'category'"
  - "ExternalDbQueryService lazy-imported in tools; tests patch app.services.external_db_service.ExternalDbQueryService not the tool module"
  - "SQL generation fallback returns error comment string rather than raising — agent surfaces to user gracefully"
  - "monitoring_jobs migration created here (Plan 01) since it runs before Plan 03 which also needs the table"

patterns-established:
  - "sys.modules stub injection at test file load time for C-extension libraries (psycopg2, google.cloud)"
  - "ExternalDbQueryService as thin safety wrapper: read-only, timeout, row-cap, password sanitization"
  - "NL-to-SQL via _generate_sql helper with SQL-only system prompt, markdown fence stripping"

requirements-completed: [XDATA-01, XDATA-02, XDATA-03, XDATA-04, XDATA-05, XDATA-06]

duration: 16min
completed: "2026-04-06"
---

# Phase 46 Plan 01: External DB Query Backend Summary

**Read-only PostgreSQL/BigQuery query service with NL-to-SQL agent tools, SQL complexity gate, and monitoring_jobs migration**

## Performance

- **Duration:** 16 min
- **Started:** 2026-04-05T23:57:14Z
- **Completed:** 2026-04-06T00:13:10Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- ExternalDbQueryService enforces read-only sessions, 30-second double-timeout (server + asyncio), and 1000-row cap on both PostgreSQL and BigQuery
- Agent tools translate natural language to SQL via Gemini, gate complex queries (JOIN/GROUP BY/CTE) on user confirmation, and return NL summary + chart suggestion
- postgresql registered as api_key analytics provider in PROVIDER_REGISTRY
- monitoring_jobs table migration with RLS policies created (shared with Plan 03 INTEL track)
- 29 unit tests total, all passing, ruff-clean

## Task Commits

1. **test(46-01): failing tests for ExternalDbQueryService and provider registry** - `302e7c0`
2. **feat(46-01): ExternalDbQueryService + PostgreSQL provider + monitoring_jobs migration** - `a5e3157`
3. **test(46-01): failing tests for external_db_tools agent tools** - `dd54e07`
4. **feat(46-01): external_db_tools agent tools with NL-to-SQL and confirmation gate** - `375c16d`

## Files Created/Modified

- `app/services/external_db_service.py` — ExternalDbQueryService: classify_sql, query_postgres, query_bigquery, suggest_chart_type
- `app/agents/tools/external_db_tools.py` — external_db_query, confirm_and_run_query, list_db_connections, EXTERNAL_DB_TOOLS
- `app/config/integration_providers.py` — postgresql ProviderConfig entry added
- `supabase/migrations/20260406000000_external_db_monitoring.sql` — monitoring_jobs table + RLS
- `tests/unit/test_external_db_service.py` — 21 tests for service layer
- `tests/unit/tools/test_external_db_tools.py` — 8 tests for agent tools
- `tests/unit/tools/__init__.py` — new tools test package

## Decisions Made

- postgresql registered as `api_key` auth type — users provide a connection string directly, no OAuth flow needed
- Outer `asyncio.wait_for(timeout=timeout_sec+2)` supplements `SET statement_timeout` to handle hung TCP connections that ignore server-side timeout
- `classify_sql` uses regex keyword heuristics; subquery detection counts `SELECT` occurrences (>1 = complex)
- Date keyword `"at"` removed from suggest_chart_type heuristic — caused false-positive `"line"` chart for columns named `"category"` or `"data"`
- Tests patch `app.services.external_db_service.ExternalDbQueryService` rather than the tool module because `ExternalDbQueryService` is lazy-imported and never a module-level attribute of the tools file
- monitoring_jobs migration placed in Plan 01 (not Plan 03) since Plan 01 runs first in the wave

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed date keyword false-positive in suggest_chart_type**
- **Found during:** Task 1 (test_string_plus_numeric_suggests_bar failure)
- **Issue:** "at" in `_DATE_KEYWORDS` caused "category" column to match as date-like, returning "line" instead of "bar"
- **Fix:** Removed "at" from the keyword set; remaining keywords (date, time, created, updated, day, month, year, week) are unambiguous
- **Files modified:** app/services/external_db_service.py
- **Verification:** test_string_plus_numeric_suggests_bar passes; all 21 service tests pass
- **Committed in:** a5e3157

**2. [Rule 1 - Bug] Fixed noqa directive mismatch (PLC0415, BLE001 not enabled)**
- **Found during:** Task 1 and Task 2 (ruff check)
- **Issue:** Noqa comments referenced rule codes not enabled in project ruff config
- **Fix:** `ruff check --fix` removed 6 unused noqa directives across both files
- **Files modified:** app/services/external_db_service.py, app/agents/tools/external_db_tools.py
- **Verification:** ruff check passes with zero errors
- **Committed in:** a5e3157, 375c16d

**3. [Rule 1 - Bug] Test patch path for lazy-imported ExternalDbQueryService**
- **Found during:** Task 2 (AttributeError on patch)
- **Issue:** Tests patched `app.agents.tools.external_db_tools.ExternalDbQueryService` which doesn't exist as module-level attribute since it's lazy-imported inside function body
- **Fix:** Updated three test patch targets to `app.services.external_db_service.ExternalDbQueryService`
- **Files modified:** tests/unit/tools/test_external_db_tools.py
- **Verification:** All 8 tool tests pass
- **Committed in:** 375c16d

---

**Total deviations:** 3 auto-fixed (2 Rule 1 bugs, 1 Rule 1 test issue)
**Impact on plan:** All fixes necessary for correctness. No scope creep.

## Issues Encountered

- psycopg2 not installed in dev environment — tests injected sys.modules stubs at load time (same pattern as Slack tests in Phase 45) to avoid ModuleNotFoundError during `patch()` target resolution

## User Setup Required

None — no external service configuration required at this step. Users connect PostgreSQL/BigQuery databases through the Configuration page using the postgresql/bigquery providers now registered in PROVIDER_REGISTRY.

## Next Phase Readiness

- ExternalDbQueryService ready for Plan 02 (DataAnalysisAgent wiring)
- EXTERNAL_DB_TOOLS ready to be added to the DataAnalysisAgent tools list
- monitoring_jobs table migration ready for Plan 03 (INTEL track) to build on
- postgresql provider visible in PROVIDER_REGISTRY for the integrations UI

---
*Phase: 46-analytics-continuous-intelligence*
*Completed: 2026-04-06*
