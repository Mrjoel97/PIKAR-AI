---
phase: 20-iteration-loop
plan: 01
subsystem: api
tags: [stitch-mcp, screen-variants, fastapi, sse, iteration, tdd]

# Dependency graph
requires:
  - phase: 19-screen-generation
    provides: screen_variants table with stitch_screen_id and iteration columns; persist_screen_assets and get_stitch_service patterns
  - phase: 18-design-brief-research
    provides: design_systems table with locked and raw_markdown columns
provides:
  - iteration_service.py with edit_screen_variant async generator and _get_locked_design_markdown helper
  - 4 new router endpoints: POST iterate (SSE), GET history, POST rollback, POST approve
  - 7 unit tests for iteration service (TDD)
  - 4 new router tests extending test_app_builder_router.py
affects: [20-02-iteration-frontend, any phase consuming screen iteration API]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "edit_screen_variant async generator follows same sequential-await pattern as generate_screen_variants (no asyncio.gather — Lock constraint)"
    - "Fallback to get_screen when edit_screens response lacks html_url/htmlUrl"
    - "Design system injection: locked markdown prepended as '{markdown}\n\nEdits: {change_description}'; None = no injection"
    - "Deselect-all + select-one pattern reused from select_variant endpoint"
    - "Next iteration computed server-side: MAX(iteration)+1 from screen_variants, never from client"

key-files:
  created:
    - app/services/iteration_service.py
    - tests/unit/app_builder/test_iteration_service.py
  modified:
    - app/routers/app_builder.py
    - tests/unit/app_builder/test_app_builder_router.py

key-decisions:
  - "edit_screen_variant takes iteration_number as parameter — router computes MAX+1 server-side before calling the service"
  - "Approve endpoint sets app_screens.approved only — does NOT call advance_stage; stage advancement remains an explicit user action"
  - "selectedScreenIds passed as list [stitch_screen_id] always, never bare string — Stitch schema requires array"
  - "Fallback to get_screen when html_url absent from edit_screens response — not all Stitch responses include download URLs"
  - "persist_screen_assets called before any yield — callers receive permanent Supabase Storage URLs, not short-lived Stitch signed URLs"

patterns-established:
  - "TDD RED: write test importing non-existent module -> confirm ModuleNotFoundError -> proceed to GREEN"
  - "Router iteration pattern: fetch project, fetch selected variant, compute MAX+1, fetch design system, stream SSE"

requirements-completed: [ITER-01, ITER-02, ITER-03, ITER-04]

# Metrics
duration: 10min
completed: 2026-03-23
---

# Phase 20 Plan 01: Iteration Loop Backend Summary

**Stitch edit_screens integration with design system injection, iteration versioning, and 4 new SSE/REST endpoints for screen editing, history, rollback, and approval**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-23T02:04:06Z
- **Completed:** 2026-03-23T02:13:35Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `iteration_service.py` with `edit_screen_variant` async generator that calls Stitch `edit_screens` with correct array `selectedScreenIds`, handles missing `html_url` via `get_screen` fallback, persists assets before yielding, and inserts new `screen_variants` row with incremented iteration
- Created `_get_locked_design_markdown` helper that returns `raw_markdown` only when `design_systems.locked=true`, enabling design system injection gating
- Added 4 new endpoints to `app_builder.py`: POST `/iterate` (SSE), GET `/history`, POST `/rollback/{variantId}`, POST `/approve` — all with proper ownership verification
- 28 total tests passing: 7 iteration service tests + 21 router tests (17 existing + 4 new), all via TDD

## Task Commits

Each task was committed atomically:

1. **Task 1: Iteration service with TDD** - `0fbbc28` (feat)
2. **Task 2: Router endpoints for iterate, history, rollback, approve with TDD** - `766fe9a` (feat)

_Note: TDD tasks each had a single combined RED+GREEN commit per task_

## Files Created/Modified

- `app/services/iteration_service.py` — New service: `edit_screen_variant` async generator and `_get_locked_design_markdown` helper
- `tests/unit/app_builder/test_iteration_service.py` — 7 unit tests covering all iteration service behaviors
- `app/routers/app_builder.py` — Added `IterateScreenRequest` model and 4 new endpoints: iterate, history, rollback, approve
- `tests/unit/app_builder/test_app_builder_router.py` — Extended with 4 new endpoint tests plus shared fixtures

## Decisions Made

- `edit_screen_variant` receives `iteration_number` as a parameter rather than computing it internally — the router computes `MAX(iteration)+1` from the DB and passes it in, keeping the service stateless and easier to test
- `approve_screen` endpoint only sets `app_screens.approved=true` — stage advancement stays decoupled as an explicit user action via the existing PATCH `/stage` endpoint
- `selectedScreenIds` is always a list `[stitch_screen_id]` — Stitch schema requires array even for single-screen edits
- Fallback `get_screen` call when `edit_screens` response lacks `html_url`/`htmlUrl` — production Stitch behavior varies by version; defensive fallback prevents asset persistence failure

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `uv` binary not on PATH in the bash shell; resolved by locating `uv.exe` at `/c/Users/expert/AppData/Roaming/Python/Python313/Scripts/uv.exe`

## User Setup Required

None - no external service configuration required. All schema columns (`screen_variants.iteration`, `screen_variants.stitch_screen_id`, `app_screens.approved`, `design_systems.locked`, `design_systems.raw_markdown`) already exist per plan context.

## Next Phase Readiness

- Backend iteration API complete and tested — ready for Plan 02 (iteration frontend: SSE streaming UI, history panel, rollback controls, approve button)
- `edit_screen_variant` and `_get_locked_design_markdown` exported and importable by router; no further backend changes needed for Phase 20

---
*Phase: 20-iteration-loop*
*Completed: 2026-03-23*
