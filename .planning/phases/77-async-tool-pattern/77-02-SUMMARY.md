---
phase: 77-async-tool-pattern
plan: 02
subsystem: api
tags: [asyncio, python, adk, tools, performance, refactor, mcp]

# Dependency graph
requires:
  - phase: 77-async-tool-pattern
    plan: 01
    provides: "6 tool files converted from ThreadPoolExecutor/asyncio.run anti-pattern (Batch 1)"
provides:
  - "5 tool files converted from ThreadPoolExecutor/asyncio.run anti-pattern to native async def (Batch 2)"
  - "skills.py: 2 async custom skill tools (create_custom_skill, list_user_skills)"
  - "agent_skills.py: 4 async tool closures (create, list, update, deactivate custom skills)"
  - "app_builder.py: _run_async helper deleted; generate_app_screen, list_stitch_tools, enhance_description → async"
  - "mcp/agent_tools.py: 4 async MCP tools (web_search, web_scrape, generate_landing_page, stitch_landing_page)"
  - "mcp/tools/setup_wizard.py: mcp_test_integration → async def with direct await"
  - "Codebase-wide verification: zero ThreadPoolExecutor/asyncio.run in all 11 converted tool files"
affects: [78-db-cache-performance, 79-architectural-resilience, 82-agent-restructuring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Native async def for ADK tool functions — direct await replaces ThreadPoolExecutor+asyncio.run (all 11 files now converted)"
    - "Factory-function-wrapped tools (agent_tool decorator with closures) support async def identically to plain functions"
    - "Module-level asyncio and concurrent.futures imports removed from all converted tool wrappers"

key-files:
  created: []
  modified:
    - app/agents/tools/skills.py
    - app/agents/tools/agent_skills.py
    - app/agents/tools/app_builder.py
    - app/mcp/agent_tools.py
    - app/mcp/tools/setup_wizard.py

key-decisions:
  - "app_builder.py: deleted _run_async centralized helper entirely rather than keeping as deprecated — same decision as self_improve.py in plan 01; cleaner and prevents future misuse"
  - "mcp/tools/setup_wizard.py: only mcp_test_integration converted — the other 6 functions (mcp_list_available_integrations, mcp_validate_api_key, mcp_save_integration, etc.) call synchronous services and need no conversion"
  - "agent_tools.py: module-level asyncio import removed entirely since all 4 wrapper functions are now async def with direct await"

patterns-established:
  - "All ADK tool files in app/agents/tools/ and app/mcp/ are now consistently async def — no exceptions"
  - "ThreadPoolExecutor+asyncio.run is fully eliminated from tool layer; only legitimate uses remain in fast_api_app.py, intelligence_worker.py, worker.py"

requirements-completed: [PERF-01]

# Metrics
duration: 17min
completed: 2026-04-26
---

# Phase 77 Plan 02: Async Tool Pattern (Batch 2) Summary

**Eliminated ThreadPoolExecutor+asyncio.run anti-pattern from 5 remaining tool files (14 functions) completing the codebase-wide async migration; zero anti-pattern occurrences remain outside the 3 legitimate infrastructure files**

## Performance

- **Duration:** 17 min
- **Started:** 2026-04-26T22:42:43Z
- **Completed:** 2026-04-26T22:59:08Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Converted 14 tool functions across 5 files from sync ThreadPoolExecutor/asyncio.run wrappers to native `async def` with direct `await`
- Deleted `_run_async` helper from `app_builder.py` entirely (same pattern as `self_improve.py` in plan 01)
- Removed all `import asyncio` and `import concurrent.futures` from converted files
- Codebase-wide grep confirmed zero remaining anti-pattern occurrences in any tool file
- 24 existing unit tests pass after conversion

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert skills.py, agent_skills.py, app_builder.py to async** - `d7cfa266` (refactor)
2. **Task 2: Convert mcp/agent_tools.py and mcp/tools/setup_wizard.py, codebase-wide verification** - `55a34bbd` (refactor)

## Files Created/Modified

- `app/agents/tools/skills.py` - `create_custom_skill` and `list_user_skills` → async def; removed asyncio + concurrent.futures inline imports
- `app/agents/tools/agent_skills.py` - 4 factory closures: `create_custom_skill`, `list_user_skills`, `update_custom_skill`, `deactivate_custom_skill` → async def; removed inline asyncio imports and RuntimeError fallback blocks
- `app/agents/tools/app_builder.py` - Deleted `_run_async` helper; removed `asyncio` and `concurrent.futures` module-level imports; `generate_app_screen`, `list_stitch_tools`, `enhance_description` → async def with direct await
- `app/mcp/agent_tools.py` - `mcp_web_search`, `mcp_web_scrape`, `mcp_generate_landing_page`, `mcp_stitch_landing_page` → async def; removed module-level `import asyncio` and all inline concurrent.futures imports
- `app/mcp/tools/setup_wizard.py` - `mcp_test_integration` → async def with direct `await tester(config)`; removed module-level `import asyncio`

## Decisions Made

- `app_builder.py` had three callers of `_run_async` (`generate_app_screen`, `list_stitch_tools`, `enhance_description`). All three were converted to `async def` and `_run_async` deleted entirely — no partial migration.
- `setup_wizard.py` has 7 tool functions. Only `mcp_test_integration` used the anti-pattern (called async testers via ThreadPoolExecutor). The remaining 6 call synchronous service methods and require no changes.
- `agent_skills.py` factory closures: all 4 affected closures wrap `custom_skills_service` which is fully async. The non-affected closures (`_create_list_skills`, `_create_use_skill`, `_create_search_skills`, `_create_get_skills_summary`) operate synchronously on the registry and were correctly left as-is.

## Deviations from Plan

None - plan executed exactly as written. The 4 ThreadPoolExecutor occurrences in `agent_skills.py` matched the plan's description of `create_custom_skill` (~379), `list_user_skills` (~480), `update_custom_skill` (~636), and `deactivate_custom_skill` (~715) — actual function names confirmed the plan's "likely" labels.

## Issues Encountered

- Pre-existing import errors in `tests/integration/test_a2a_protocol.py` (rate_limiter) and several unit test files (missing modules) prevented running the full test suite. These failures pre-date this plan and are unrelated to the async conversion. Targeted test run of the 24 directly-relevant unit tests confirms all pass.
- `uv` not on bash PATH — resolved with `export PATH` prefix (same as plan 01).

## User Setup Required

None - no external service configuration required. Pure refactor with no new dependencies or environment variables.

## Next Phase Readiness

- All 11 tool files (Batch 1 + Batch 2) are now native async def — PERF-01 fully complete.
- Zero ThreadPoolExecutor/asyncio.run in any tool file. Only legitimate uses remain in fast_api_app.py, intelligence_worker.py, worker.py.
- No blockers for phases 78, 79, 80, 81, 82.

---
*Phase: 77-async-tool-pattern*
*Completed: 2026-04-26*
