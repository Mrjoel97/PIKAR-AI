---
phase: 16-foundation
plan: "02"
subsystem: api
tags: [mcp, stitch, fastapi, lifespan, asyncio, subprocess, adk]

# Dependency graph
requires:
  - phase: 16-01
    provides: App Builder schema tables and stitch-assets Supabase bucket
provides:
  - StitchMCPService singleton (app/services/stitch_mcp.py) — persistent MCP stdio subprocess
  - FastAPI lifespan wiring for Stitch MCP startup/shutdown
  - Windows ProactorEventLoop policy guard in fast_api_app.py
  - ADK-compatible tool wrappers (app/agents/tools/app_builder.py)
  - APP_BUILDER_TOOLS list for agent registration
affects: [16-03, 16-04, 16-05, app-builder-agent, stitch-integration]

# Tech tracking
tech-stack:
  added: [mcp 1.25.0 (stdio_client + ClientSession), anyio.Event for ready signaling]
  patterns:
    - Persistent subprocess via asyncio background task (create_task + cancel at shutdown)
    - anyio.Event for cross-coroutine ready signaling
    - asyncio.Lock serializing MCP tool calls through a single session
    - Sync ADK tool wrappers using ThreadPoolExecutor when event loop is running

key-files:
  created:
    - app/services/stitch_mcp.py
    - app/agents/tools/app_builder.py
    - tests/unit/app_builder/test_stitch_mcp_service.py
  modified:
    - app/fast_api_app.py

key-decisions:
  - "noqa: BLE001 directives removed — BLE001 not enabled in project ruff config"
  - "asyncio alias (_asyncio_lifespan) used in lifespan to avoid shadowing stdlib asyncio at module level"
  - "StitchMCPService has no start()/stop() methods — lifecycle managed externally from lifespan for clean separation"

patterns-established:
  - "Singleton pattern: module-level _stitch_service var + get_stitch_service() accessor raises if None"
  - "Lifespan guard: BYPASS_IMPORT + os.environ.get(KEY) — service only starts when key present"
  - "Sync wrapper pattern: ThreadPoolExecutor(asyncio.run) when loop.is_running(), else loop.run_until_complete()"

requirements-completed: [FOUN-01]

# Metrics
duration: 18min
completed: 2026-03-21
---

# Phase 16 Plan 02: StitchMCP Service Singleton Summary

**StitchMCPService singleton holding a persistent MCP stdio subprocess for the FastAPI process lifetime, wired into FastAPI lifespan with 30s readiness timeout and clean cancellation shutdown, plus ADK-compatible sync tool wrappers.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-21T13:17:30Z
- **Completed:** 2026-03-21T13:35:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `StitchMCPService` singleton: asyncio background task holds `stdio_client` + `ClientSession` open for process lifetime, with `anyio.Event` for ready signaling and `asyncio.Lock` for call serialization
- FastAPI lifespan wired: Stitch MCP starts after Redis prewarm with 30s `wait_for` timeout; shutdown cancels task and awaits `CancelledError`
- Windows ProactorEventLoop policy guard added at top of `fast_api_app.py` (required for asyncio subprocess on Windows)
- ADK tool wrappers `generate_app_screen` and `list_stitch_tools` following existing `app/mcp/agent_tools.py` sync-wrapper pattern; `APP_BUILDER_TOOLS` list exported
- 5 unit tests covering all service behaviors (ready state, error propagation, JSON parsing) — all green

## Task Commits

Each task was committed atomically:

1. **Task 1: Create StitchMCPService singleton** - `95b83eb` (feat)
2. **Task 1 (TDD test file)** - `879299f` (test)
3. **Task 2: Wire lifespan + create ADK tool wrappers** - `b202bc4` (feat)

## Files Created/Modified

- `app/services/stitch_mcp.py` — StitchMCPService class + get_stitch_service() accessor
- `app/agents/tools/app_builder.py` — generate_app_screen, list_stitch_tools, APP_BUILDER_TOOLS
- `app/fast_api_app.py` — Windows ProactorEventLoop guard + Stitch MCP lifespan blocks
- `tests/unit/app_builder/test_stitch_mcp_service.py` — 5 unit tests (no real subprocess)
- `tests/unit/app_builder/__init__.py` — package init

## Decisions Made

- `noqa: BLE001` directives removed from `stitch_mcp.py` — BLE001 (blind exception) is not enabled in this project's ruff config, making the directives unused violations
- `asyncio` aliased as `_asyncio_lifespan` inside the lifespan function to avoid shadowing the stdlib module in module-level scope
- `StitchMCPService` has no `start()`/`stop()` methods — lifecycle managed externally from `fast_api_app.py` lifespan to keep the service class free of asyncio task management complexity

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused noqa directives in stitch_mcp.py**
- **Found during:** Task 2 (ruff verification)
- **Issue:** `# noqa: BLE001` on two except clauses triggered `RUF100` (unused noqa) because BLE001 is not in the project's enabled ruff ruleset
- **Fix:** Removed both `# noqa: BLE001` comments
- **Files modified:** `app/services/stitch_mcp.py`
- **Verification:** `ruff check app/services/stitch_mcp.py` exits 0
- **Committed in:** b202bc4 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - minor ruff compliance fix)
**Impact on plan:** Trivial cleanup — no behavioral change. Noqa directives in the plan spec referenced a rule not active in this project.

## Issues Encountered

- `LOCAL_DEV_BYPASS=1 python -c "from app.fast_api_app import app"` fails with `ModuleNotFoundError: No module named 'google.adk'` — confirmed pre-existing (same error on unmodified codebase). Not caused by this plan's changes. The `google-adk` package is not installed in the local dev environment; it's only available in the deployed Cloud Run environment.

## User Setup Required

None — no external service configuration required at this stage. `STITCH_API_KEY` must be set in `.env` for the service to start at runtime, but this is already documented in `.env.example` (from Phase 16-01).

## Next Phase Readiness

- `StitchMCPService` singleton is ready for Phase 16-03 (screen generation workflow)
- `APP_BUILDER_TOOLS` list is ready for agent registration in the AppBuilderAgent
- The `list_stitch_tools` function will log actual tool names at startup — check logs to verify `generate_screen_from_text` is the correct camelCase name before Phase 16-03 integration
- Windows ProactorEventLoop guard ensures local dev works on Windows without `--no-reload` for subprocess support

---
*Phase: 16-foundation*
*Completed: 2026-03-21*

## Self-Check: PASSED

- FOUND: app/services/stitch_mcp.py
- FOUND: app/agents/tools/app_builder.py
- FOUND: tests/unit/app_builder/test_stitch_mcp_service.py
- FOUND: .planning/phases/16-foundation/16-02-SUMMARY.md
- FOUND: commit 95b83eb (feat: StitchMCPService singleton)
- FOUND: commit 879299f (test: unit tests)
- FOUND: commit b202bc4 (feat: lifespan wiring + ADK tools)
