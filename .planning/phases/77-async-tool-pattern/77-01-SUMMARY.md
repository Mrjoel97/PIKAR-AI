---
phase: 77-async-tool-pattern
plan: 01
subsystem: api
tags: [asyncio, python, adk, tools, performance, refactor]

# Dependency graph
requires: []
provides:
  - "6 tool files converted from ThreadPoolExecutor/asyncio.run anti-pattern to native async def"
  - "google_seo.py: 5 async SEO tool functions"
  - "social_analytics.py: 2 async social analytics tools"
  - "social_listening.py: 2 async social listening tools"
  - "sitemap_crawler.py: 2 async sitemap tools"
  - "report_scheduling.py: 6 async report scheduling tools"
  - "self_improve.py: _run_async helper removed, all tool closures async"
affects: [78-db-cache-performance, 79-architectural-resilience, 82-agent-restructuring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Native async def for ADK tool functions — direct await replaces ThreadPoolExecutor+asyncio.run"
    - "No module-level asyncio/concurrent.futures imports in tool wrappers"
    - "Inner tool factory closures (agent_tool decorator) support async def"

key-files:
  created: []
  modified:
    - app/agents/tools/google_seo.py
    - app/agents/tools/social_analytics.py
    - app/agents/tools/social_listening.py
    - app/agents/tools/sitemap_crawler.py
    - app/agents/tools/report_scheduling.py
    - app/agents/tools/self_improve.py
    - tests/unit/test_reporting_connection_alignment.py

key-decisions:
  - "social_analytics.py get_all_platform_analytics: replaced nested _fetch_all async inner fn with simple sequential await loop — simpler, no asyncio.gather needed for this use case"
  - "self_improve.py: deleted centralized _run_async helper entirely rather than keeping as deprecated; each call site got direct await"
  - "_resolve_connection_id in report_scheduling.py kept as sync def — SpreadsheetConnectionService.get_connection() is synchronous"

patterns-established:
  - "ADK tool functions should always be async def with direct await — never use ThreadPoolExecutor or asyncio.run() as bridge"
  - "Tests calling async tool functions must use @pytest.mark.asyncio and await"

requirements-completed: [PERF-01]

# Metrics
duration: 22min
completed: 2026-04-26
---

# Phase 77 Plan 01: Async Tool Pattern (Batch 1) Summary

**Eliminated ThreadPoolExecutor+asyncio.run anti-pattern from 6 tool files (17 functions) by converting to native async def with direct await, preventing RuntimeError and per-invocation thread overhead**

## Performance

- **Duration:** 22 min
- **Started:** 2026-04-26T22:23:47Z
- **Completed:** 2026-04-26T22:45:30Z
- **Tasks:** 2
- **Files modified:** 7 (6 tool files + 1 test)

## Accomplishments

- Converted 17 tool functions across 6 files from sync ThreadPoolExecutor/asyncio.run wrappers to native `async def` with direct `await`
- Removed `_run_async` centralized helper from `self_improve.py` entirely (5 call sites converted)
- Removed all `import asyncio` and `import concurrent.futures` from converted files
- All 21 existing unit tests pass (1 skipped pre-existing), including test updated for async

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert google_seo.py, social_analytics.py, social_listening.py, sitemap_crawler.py** - `7f740b70` (refactor)
2. **Task 2: Convert report_scheduling.py and self_improve.py** - `86f53d8f` (refactor)

## Files Created/Modified

- `app/agents/tools/google_seo.py` - 5 functions: get_seo_performance, get_top_search_queries, get_top_pages, get_indexing_status, get_website_traffic → all async def
- `app/agents/tools/social_analytics.py` - 2 functions: get_social_analytics, get_all_platform_analytics → async def; inner _fetch_all helper inlined as sequential awaits
- `app/agents/tools/social_listening.py` - 2 functions: monitor_brand, compare_share_of_voice → async def
- `app/agents/tools/sitemap_crawler.py` - 2 functions: crawl_website, map_website → async def; docstring updated to remove "sync" reference
- `app/agents/tools/report_scheduling.py` - 6 functions: schedule_report, list_report_schedules, update_report_schedule, pause_report_schedule, resume_report_schedule, delete_report_schedule → async def; inline asyncio imports removed
- `app/agents/tools/self_improve.py` - _run_async helper deleted; asyncio + concurrent.futures module-level imports removed; all 5 inner tool closures (report_interaction, report_skill_gap, check_my_performance, get_improvement_suggestions, trigger_improvement_cycle) → async def
- `tests/unit/test_reporting_connection_alignment.py` - Updated test_schedule_report_uses_resolved_connection_id to use @pytest.mark.asyncio and await (Rule 1 auto-fix)

## Decisions Made

- `get_all_platform_analytics` in social_analytics.py had a nested `_fetch_all` async inner function used as a bridge. Replaced with a simple sequential `await` loop — no `asyncio.gather` needed since the outer function is now itself async.
- `_resolve_connection_id` in report_scheduling.py intentionally kept as sync `def` — it calls `SpreadsheetConnectionService().get_connection()` which is synchronous. No change needed.
- Deleted `_run_async` in self_improve.py entirely rather than leaving as deprecated dead code — cleaner and prevents future misuse.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test to await async schedule_report**
- **Found during:** Task 2 verification (test run)
- **Issue:** `test_schedule_report_uses_resolved_connection_id` called `schedule_report(...)` without `await`, receiving a coroutine object instead of a dict — `TypeError: 'coroutine' object is not subscriptable`
- **Fix:** Added `import pytest`, decorated test with `@pytest.mark.asyncio`, added `await` to the `schedule_report(...)` call
- **Files modified:** `tests/unit/test_reporting_connection_alignment.py`
- **Verification:** `uv run pytest tests/unit/test_reporting_connection_alignment.py -x -q` → PASSED
- **Committed in:** `86f53d8f` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test caused by the planned conversion)
**Impact on plan:** Necessary correctness fix — test was directly broken by the async conversion. No scope creep.

## Issues Encountered

- `uv` not on bash PATH in this environment — located at `/c/Users/expert/AppData/Roaming/Python/Python313/Scripts/uv.exe`. Used `export PATH` prefix for all `uv run` commands.

## User Setup Required

None - no external service configuration required. This is a pure refactor with no new dependencies or environment variables.

## Next Phase Readiness

- Batch 1 (6 files) complete. All 17 functions now native async.
- Remaining async conversions (Batch 2 files per PERF-01) can proceed in plan 77-02 if planned.
- No blockers for phases 78, 79, 81, 82 — these changes are internal tool layer only.

---
*Phase: 77-async-tool-pattern*
*Completed: 2026-04-26*
