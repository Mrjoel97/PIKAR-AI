---
phase: 46-analytics-continuous-intelligence
plan: "05"
subsystem: external-db-integration, calendar-tools, requirements
tags: [gap-closure, test-connection, calendar, recurring-tasks, tdd]
dependency_graph:
  requires: [46-01, 46-02, 46-04]
  provides: [POST /integrations/{provider}/test, ExternalDbQueryService.test_connection, generate_recurring_tasks, CALENDAR_TOOLS[9]]
  affects: [frontend-test-connection-button, synced_tasks-table, REQUIREMENTS.md]
tech_stack:
  added: []
  patterns: [asyncio.to_thread for sync psycopg2, DSN password sanitization, lazy-import AdminService per-pattern, TDD red-green]
key_files:
  created: []
  modified:
    - app/services/external_db_service.py
    - app/routers/integrations.py
    - app/agents/tools/calendar_tool.py
    - tests/unit/test_external_db_service.py
    - tests/unit/test_calendar_tools.py
    - .planning/REQUIREMENTS.md
decisions:
  - "test_connection returns {ok, server_version, database} shape — caller-agnostic dict, not exception"
  - "generate_recurring_tasks continues per-pattern on DB insert failure — partial success preferred over full abort"
  - "CALENDAR_TOOLS grows to 9 entries; existing test count assertion updated to match"
  - "CAL-02 wording changed from auto-schedule to suggest + user-confirms — aligns with CONTEXT.md decision"
metrics:
  duration: "14min"
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_modified: 6
---

# Phase 46 Plan 05: Gap Closure — Test Connection + Recurring Tasks Summary

**One-liner:** PostgreSQL/BigQuery test_connection endpoint (password-sanitized), generate_recurring_tasks synced_tasks creator, and REQUIREMENTS.md CAL-02 accuracy fix closing all 3 Phase 46 verification gaps.

## What Was Built

### Task 1: test_connection + POST /integrations/{provider}/test (commit: 60d6d69)

**ExternalDbQueryService.test_connection(provider, connection_string):**
- `provider="postgresql"`: opens read-only psycopg2 connection, `set_session(readonly=True)`, runs `SELECT version()`, returns `{"ok": True, "server_version": ..., "database": ...}`
- `provider="bigquery"`: parses service-account JSON, runs `SELECT 1`, returns `{"ok": True, "project_id": ...}`
- Any failure returns `{"ok": False, "error": "...sanitized..."}` — password is never in the response
- 10-second probe timeout (shorter than the 30s query timeout), 12s asyncio outer guard
- Unsupported providers return `{"ok": False, "error": "Unsupported provider: ..."}` gracefully

**POST /integrations/{provider}/test endpoint:**
- Added `_DB_PROVIDERS = frozenset({"postgresql", "bigquery"})` alongside existing `_NOTIF_PROVIDERS`
- Added `TestDbConnectionBody(BaseModel)` with `connection_string: str`
- `test_db_connection()` guards with HTTPException 400 for unsupported providers
- Placed BEFORE `/{provider}/test-notification` to avoid FastAPI route shadowing
- Frontend `handleTestConnection` at line 1783 calling `POST /integrations/postgresql/test` now gets 200 instead of 404

**3 new unit tests in tests/unit/test_external_db_service.py:**
- `test_test_connection_postgres_success`: mocks psycopg2, verifies `set_session(readonly=True)` called, `ok=True` returned
- `test_test_connection_postgres_failure`: injects password into OperationalError, asserts password stripped from `result["error"]`
- `test_test_connection_unsupported_provider`: verifies `ok=False` or ValueError for unknown provider

### Task 2: generate_recurring_tasks + REQUIREMENTS.md CAL-02 fix (commit: acc4c2a)

**_get_user_id() helper added to calendar_tool.py:**
- Lazy-imports `get_current_user_id` from `app.services.request_context`
- Follows identical pattern as `pm_task_tools.py`

**generate_recurring_tasks(tool_context, days_back=30):**
- Calls `detect_calendar_patterns()` to get patterns list
- For each pattern, inserts a `synced_tasks` row via lazy-imported `AdminService`:
  - `title`: `"Recurring: {meeting_title}"`
  - `description`: `"Detected {frequency} meeting on {typical_day}s at {typical_time} ({occurrences} occurrences in last {days_back} days)"`
  - `status`: `"active"`, `source`: `"calendar_pattern"`
- Continues on per-pattern DB failure (logs warning, appends error to task dict)
- Returns `{"status": "success", "tasks_created": [...], "patterns_found": N}`
- Added to `CALENDAR_TOOLS` export — list now has 9 tools

**3 new unit tests in tests/unit/test_calendar_tools.py:**
- `test_generate_recurring_tasks_creates_tasks`: mocks detect_calendar_patterns (2 patterns), verifies 2 tasks created with "Recurring:" prefix titles
- `test_generate_recurring_tasks_no_patterns`: empty patterns list produces `tasks_created=[]`
- `test_generate_recurring_tasks_in_calendar_tools`: asserts function is in CALENDAR_TOOLS

**REQUIREMENTS.md CAL-02 updated:**
- From: `Agent can auto-schedule follow-up meetings after sales calls`
- To: `Agent can suggest optimal follow-up meeting times after sales calls (user confirms before booking)`

## Requirements Closed

| Requirement | Status Before | Status After |
|-------------|--------------|--------------|
| XDATA-01 | PARTIAL (404 on test) | SATISFIED |
| XDATA-02 | PARTIAL (404 on test) | SATISFIED |
| CAL-02 | PARTIAL (wording mismatch) | SATISFIED |
| CAL-03 | FAILED (no task creation) | SATISFIED |

Phase 46 now: **15/15 requirements satisfied**.

## Verification

- `uv run pytest tests/unit/test_external_db_service.py -q` — 24 passed
- `uv run pytest tests/unit/test_calendar_tools.py -q` — 23 passed
- `uv run ruff check app/routers/integrations.py app/services/external_db_service.py app/agents/tools/calendar_tool.py` — All checks passed
- `POST /{provider}/test` route confirmed in integrations.py at line 1305
- `generate_recurring_tasks` confirmed in CALENDAR_TOOLS at line 699
- REQUIREMENTS.md CAL-02 confirmed to say "suggest" not "auto-schedule"

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated CALENDAR_TOOLS count assertion from 8 to 9**
- **Found during:** Task 2 full test suite run
- **Issue:** Existing `test_calendar_tools_has_eight_entries` test hardcoded count=8; adding `generate_recurring_tasks` to CALENDAR_TOOLS caused it to fail
- **Fix:** Updated assertion to count=9, renamed test to `test_calendar_tools_has_nine_entries`
- **Files modified:** tests/unit/test_calendar_tools.py
- **Commit:** acc4c2a (bundled with Task 2)

### Out-of-scope Pre-existing Issues

**Cross-test stub pollution:** When `test_external_db_service.py` and `test_calendar_tools.py` run together in the same pytest session, the BigQuery stub injected into `sys.modules["google.oauth2"]` prevents `google.oauth2.credentials` from loading normally — causing 1 pre-existing `TestGoogleCalendarServiceFreebusy` test to fail only in combined runs. Each file passes independently with 24 and 23 tests respectively. Logged to deferred-items — not caused by this plan's changes.

## Self-Check

### Files exist:
- app/services/external_db_service.py — contains `test_connection`
- app/routers/integrations.py — contains `test_db_connection` at line 1305
- app/agents/tools/calendar_tool.py — contains `generate_recurring_tasks` at line 608
- tests/unit/test_external_db_service.py — contains `TestTestConnection` class
- tests/unit/test_calendar_tools.py — contains `TestGenerateRecurringTasks` class
- .planning/REQUIREMENTS.md — CAL-02 says "suggest"
