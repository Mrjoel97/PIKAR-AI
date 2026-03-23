---
phase: 22-react-conversion-output
plan: 03
subsystem: api
tags: [remotion, ship-service, sse, zipfile, beautifulsoup4, supabase, fastapi, react-converter, pwa, capacitor]

# Dependency graph
requires:
  - phase: 22-01
    provides: convert_html_to_react_zip async function for React/TS component ZIP generation
  - phase: 22-02
    provides: generate_pwa_zip and generate_capacitor_zip async functions

provides:
  - ship_project async generator (SSE orchestrator) in app/services/ship_service.py
  - render_scenes_direct_to_mp4 (pre-built scenes overload) in app/services/remotion_render_service.py
  - POST /app-builder/projects/{id}/ship SSE endpoint in app/routers/app_builder.py
  - supabase/migrations/20260324000000_stitch_assets_allow_video.sql — video/mp4 MIME allowed in stitch-assets
  - beautifulsoup4>=4.12.0 added as project dependency

affects: [22-04, frontend-shipping-ui, video-walkthrough-feature]

# Tech tracking
tech-stack:
  added: [beautifulsoup4>=4.12.0,<5.0.0]
  patterns:
    - Sequential async generator SSE pattern — ship_project iterates targets one-by-one, yields started/complete/failed per target
    - Multi-screen ZIP merge — per-screen ZIPs extracted into master ZIP under {screen_name}/ subdirectory prefix
    - asyncio.to_thread wrapping synchronous Remotion render for non-blocking video generation
    - render_scenes_direct_to_mp4 structured overload — accepts pre-built scene list, bypasses _scenes_from_prompt

key-files:
  created:
    - app/services/ship_service.py
    - supabase/migrations/20260324000000_stitch_assets_allow_video.sql
    - tests/unit/app_builder/test_ship_service.py
  modified:
    - app/services/remotion_render_service.py
    - app/routers/app_builder.py
    - pyproject.toml

key-decisions:
  - "render_scenes_direct_to_mp4 added as structured overload of render_scenes_to_mp4 — accepts pre-built scene list directly, bypassing _scenes_from_prompt; prevents single-scene wrapping bug when passing multi-screen walkthrough scenes"
  - "Ship targets processed sequentially in ship_project (not asyncio.gather) — Remotion subprocess is CPU-intensive; sequential ensures no concurrent subprocess contention"
  - "Individual target failures yield target_failed events (not exceptions) — other targets continue processing; ship_complete always yielded at the end with partial downloads dict"
  - "Multi-screen React export merges per-screen ZIPs into one master ZIP under {screen_name}/ subdirectory prefix — prevents filename collisions across screens"
  - "beautifulsoup4 installed directly via pip into .venv (uv CLI unavailable on Windows bash); pyproject.toml updated so future uv sync will include it"

patterns-established:
  - "Ship SSE pattern: yield target_started → await _ship_{target}() → yield target_complete/target_failed → yield ship_complete"
  - "Walkthrough scene structure: intro(3s) + N screens with imageUrl+fade transition(4s each) + outro(2s)"
  - "ZIP merge pattern: iterate per-screen ZIPs, prefix each entry with safe screen name subdirectory in master ZipFile"

requirements-completed: [OUTP-04, FLOW-07]

# Metrics
duration: 8min
completed: 2026-03-23
---

# Phase 22 Plan 03: Ship Stage Orchestrator Summary

**Sequential SSE ship orchestrator generating React/PWA/Capacitor/Remotion-video output targets with per-target failure isolation and multi-screen ZIP merging**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-23T04:14:00Z
- **Completed:** 2026-03-23T04:22:00Z
- **Tasks:** 2 (Task 1: deps+migration+render overload, Task 2: TDD ship_service+endpoint)
- **Files modified:** 5

## Accomplishments

- Created `ship_service.py` with `ship_project` async generator yielding `target_started`, `target_complete` (with URL), `target_failed` (with error string), and `ship_complete` (with downloads dict) — individual failures never abort remaining targets
- Added `render_scenes_direct_to_mp4` to `remotion_render_service.py` — accepts pre-built scene dicts directly, bypasses `_scenes_from_prompt`, called via `asyncio.to_thread` for non-blocking video generation
- Multi-screen React export merges all per-screen ZIPs into one master ZIP under `{screen_name}/` subdirectories; POST /ship SSE endpoint wired into app_builder router matching the build-all pattern
- All 9 unit tests pass covering scene structure, durations, SSE event sequence, URL field, failure isolation, ship_complete downloads, asyncio.to_thread usage, stage advancement, and multi-screen merge

## Task Commits

Each task was committed atomically:

1. **Task 1: Add beautifulsoup4 dep, video/mp4 migration, render_scenes_direct_to_mp4** - `92a854f` (feat)
2. **Task 2 RED: Failing tests for ship_service** - `7adecb5` (test)
3. **Task 2 GREEN: ship_service orchestrator and POST /ship endpoint** - `753d237` (feat)

## Files Created/Modified

- `app/services/ship_service.py` — Ship orchestrator: `ship_project` async generator, `_build_walkthrough_scenes`, `_upload_output_bytes`, `_fetch_approved_screens`, `_ship_react/pwa/capacitor/video` helpers
- `app/services/remotion_render_service.py` — Appended `render_scenes_direct_to_mp4` (pre-built scene dict overload, synchronous, call via asyncio.to_thread)
- `app/routers/app_builder.py` — Added `ShipRequest` model and `POST /app-builder/projects/{id}/ship` SSE endpoint
- `supabase/migrations/20260324000000_stitch_assets_allow_video.sql` — UPDATE storage.buckets to allow video/mp4 in stitch-assets
- `pyproject.toml` — Added `beautifulsoup4>=4.12.0,<5.0.0` dependency
- `tests/unit/app_builder/test_ship_service.py` — 9 unit tests (all passing)

## Decisions Made

- `render_scenes_direct_to_mp4` added as a structured overload rather than modifying `render_scenes_to_mp4` — passing `json.dumps(scenes)` as the prompt to the original function would wrap the entire JSON string as a single scene's text, producing an incorrect single-scene video instead of the intended multi-screen walkthrough.
- Ship targets are processed sequentially (not `asyncio.gather`) — Remotion subprocess is CPU-intensive; concurrent renders would contend on CPU and temp directories.
- Individual target failures yield `target_failed` and continue — a failed React conversion should not block the PWA or video targets.
- Multi-screen ZIP entries prefixed under `{screen_name}/` subdirectories to prevent `src/index.tsx` and similar common filenames from colliding across screens.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed two ruff lint errors in ship_service.py**
- **Found during:** Task 2 (after GREEN phase)
- **Issue:** `AsyncIterator` imported from `typing` (UP035 — should be `collections.abc`) and unused `# noqa: BLE001` directive on bare-except (BLE001 not enabled in project ruff config per decision 16-02)
- **Fix:** Ran `ruff check --fix` to auto-apply both fixes
- **Files modified:** `app/services/ship_service.py`
- **Verification:** `ruff check` passes with "All checks passed!"
- **Committed in:** `753d237` (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking lint)
**Impact on plan:** Minimal. Auto-fixable lint corrections only, no logic changes.

## Issues Encountered

- `uv` CLI is unavailable in the bash shell on this Windows environment. beautifulsoup4 was installed directly via `.venv/Scripts/python.exe -m pip install` and added to `pyproject.toml` manually so `uv sync` will pick it up in future runs. This matches the established approach from prior phases.

## Next Phase Readiness

- Ship service complete: all four output targets (react, pwa, capacitor, video) wired and tested
- Frontend ShippingPage can consume `POST /ship` SSE events matching the existing `MultiPageProgress` pattern
- `render_scenes_direct_to_mp4` is available for any future caller needing pre-built scene rendering
- Requirements OUTP-04 and FLOW-07 fully satisfied

---
*Phase: 22-react-conversion-output*
*Completed: 2026-03-23*

## Self-Check: PASSED

- `app/services/ship_service.py` — FOUND
- `supabase/migrations/20260324000000_stitch_assets_allow_video.sql` — FOUND
- `tests/unit/app_builder/test_ship_service.py` — FOUND
- `.planning/phases/22-react-conversion-output/22-03-SUMMARY.md` — FOUND
- Commit `92a854f` — FOUND
- Commit `7adecb5` — FOUND
- Commit `753d237` — FOUND
