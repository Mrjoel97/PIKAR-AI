---
phase: 21-multi-page-builder
plan: 02
subsystem: api
tags: [fastapi, sse, multi-page, supabase, streaming, router]

requires:
  - phase: 21-01
    provides: build_all_pages async generator, inject_navigation_links post-processor, NavLinkRewriter

provides:
  - POST /app-builder/projects/{id}/build-all SSE endpoint streaming baton-loop page events
  - GET /app-builder/projects/{id}/screens listing screens with selected variant html_url
  - PATCH /app-builder/projects/{id}/sitemap updating sitemap JSONB and clearing build_plan

affects: [22-shipping, frontend multi-page verification page, FLOW-06 verification flow]

tech-stack:
  added: []
  patterns:
    - "build_all SSE: captures last build_complete event after loop, calls inject_navigation_links — ensures nav injection is post-loop, not inline"
    - "list_project_screens: two sequential queries (screens + variants) merged Python-side — Supabase REST has no cross-table joins"
    - "UpdateSitemapRequest: clears build_plan to [] on every sitemap mutation — forces rebuild on next /build-all call"

key-files:
  created: []
  modified:
    - app/routers/app_builder.py
    - tests/unit/app_builder/test_app_builder_router.py

key-decisions:
  - "21-02: build_all captures build_complete event after async-for loop completes; inject_navigation_links called outside the generator body — non-fatal exception swallowed with warning log"
  - "21-02: list_project_screens fetches screen_variants with single .eq(is_selected, True) (no user_id scope) then Python-side filters to current project's screen_ids — avoids multi-eq chain complexity"
  - "21-02: update_sitemap returns 404 when supabase update returns empty data — consistent with existing project ownership enforcement pattern"
  - "21-02: mock_supabase_multi uses .eq().eq().order().execute() chain for screens (double-eq then order) and .eq().execute() (single-eq) for variants — two distinct chain depths to differentiate query types"

patterns-established:
  - "Post-loop async post-processing: capture last event before generator body ends; await post-processor with try/except after generator exhausted"

requirements-completed: [PAGE-01, PAGE-04, FLOW-06]

duration: 4min
completed: 2026-03-23
---

# Phase 21 Plan 02: Multi-Page Builder Router Summary

**Three new FastAPI SSE and REST endpoints wiring multi_page_service into the app_builder router: build-all stream, screens list with html_url, and sitemap mutation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-23T04:05:18Z
- **Completed:** 2026-03-23T04:09:26Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- POST /build-all SSE endpoint consumes `build_all_pages` async generator and calls `inject_navigation_links` after `build_complete` event with non-fatal error handling
- GET /screens returns all `app_screens` for a project merged with selected variant `html_url` via two sequential Supabase queries
- PATCH /sitemap updates `app_projects.sitemap` JSONB and resets `build_plan` to `[]` to invalidate any stale phased build plan
- 4 new unit tests added (build_all_streams_events, list_project_screens, update_sitemap, build_all_requires_auth) — all pass; full 25-test router suite green

## Task Commits

1. **Task 1: Build-all SSE endpoint, list-screens endpoint, update-sitemap endpoint with tests** — `8a14dd6` (feat)

## Files Created/Modified

- `app/routers/app_builder.py` — added `UpdateSitemapRequest` model and 3 new endpoints (`build_all`, `list_project_screens`, `update_sitemap`); added `build_all_pages` and `inject_navigation_links` imports from `multi_page_service`
- `tests/unit/app_builder/test_app_builder_router.py` — added 4 new tests with `mock_supabase_multi` and `multi_client` fixtures

## Decisions Made

- `inject_navigation_links` called after the async-for loop (outside the generator body), capturing the `screens` list from the last `build_complete` event. This ensures nav injection is a post-processing step rather than inline with the stream.
- `list_project_screens` uses a single `.eq("is_selected", True)` query for variants (not scoped by user_id) then filters Python-side by the current project's screen IDs — keeps the query chain simple and consistent with the existing mock depth convention.
- Mock chain `mock_supabase_multi` distinguishes screens fetch (`.eq().eq().order().execute()`) from variants fetch (`.eq().execute()`) by chain depth — reliable differentiation without table-name introspection at mock setup time.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `noqa: BLE001` directive**
- **Found during:** Task 1 (GREEN phase, ruff lint check)
- **Issue:** `# noqa: BLE001` on the `except Exception` clause caused a ruff RUF100 error — BLE001 is not enabled in this project's ruff config (consistent with 16-02 decision)
- **Fix:** Removed the `noqa: BLE001` comment; bare `except Exception` is acceptable here per project config
- **Files modified:** `app/routers/app_builder.py`
- **Verification:** `uv run ruff check app/routers/app_builder.py` — All checks passed
- **Committed in:** `8a14dd6` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — lint correctness)
**Impact on plan:** Trivial one-line fix; no scope change.

## Issues Encountered

- TDD RED: first test run showed `AttributeError: module has no attribute 'build_all_pages'` — expected RED failure confirming tests were written before implementation.
- GREEN iteration 1: `test_list_project_screens` failed (returned empty list) because `mock_supabase_multi` used `.select().eq().eq().execute()` for screens but the endpoint chains `.order()` before `.execute()`. Fixed by updating mock to `.select().eq().eq().order().execute()`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 21 Wave 2 (Plan 02) complete. Both `multi_page_service.py` (21-01) and the three router endpoints (21-02) are implemented and tested.
- Frontend multi-page verification page (FLOW-06 depends on GET /screens) can now be built.
- Phase 22 (Shipping) can reference POST /build-all for the build trigger and GET /screens for the verification screen list.

---
*Phase: 21-multi-page-builder*
*Completed: 2026-03-23*
