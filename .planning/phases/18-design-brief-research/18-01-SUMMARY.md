---
phase: 18-design-brief-research
plan: "01"
subsystem: api
tags: [fastapi, gemini, tavily, supabase, sse, async-generator, design-system]

requires:
  - phase: 17-creative-questioning
    provides: creative_brief stored on app_projects; build_sessions row at stage=questioning
  - phase: 16-foundation
    provides: app_projects/design_systems/build_sessions DB schema; app_builder router scaffold

provides:
  - Gemini-powered design research service (run_design_research async generator)
  - Tavily parallel web search feeding design synthesis
  - _parse_design_response: structured color/typography/spacing/sitemap extraction
  - _generate_build_plan: phased JSON build plan with fallback
  - POST /app-builder/projects/{id}/research — SSE streaming endpoint
  - POST /app-builder/projects/{id}/approve-brief — design lock + stage advance
  - UNIQUE constraint on design_systems(project_id) enabling upsert pattern

affects:
  - 18-02 (frontend research page — consumes the SSE endpoint)
  - 19-screen-generation (uses build_plan + locked design_system)
  - any phase that reads design_systems or build_plan from app_projects

tech-stack:
  added: []
  patterns:
    - "AsyncGenerator streaming: run_design_research yields step events consumed by SSE endpoint"
    - "Parallel Tavily search via asyncio.gather — competitor + inspiration tracks simultaneously"
    - "Structured Gemini response parsing: section markers (PALETTE:, TYPOGRAPHY:, etc.) with JSON extraction"
    - "Upsert on_conflict='project_id' pattern for idempotent design_systems writes"
    - "response_mime_type=application/json in GenerateContentConfig for structured build plan output"

key-files:
  created:
    - supabase/migrations/20260322000000_design_brief_unique.sql
    - app/services/design_brief_service.py
    - tests/unit/app_builder/test_design_brief_service.py
  modified:
    - app/routers/app_builder.py
    - tests/unit/app_builder/test_app_builder_router.py

key-decisions:
  - "Migration timestamp 20260322000000 used (20260321700000 was already taken by analytics_summary_tables)"
  - "run_design_research is an async generator — SSE endpoint consumes it directly via async for, no intermediate buffering"
  - "Tavily calls run in parallel (asyncio.gather) across competitor and inspiration query tracks"
  - "Section markers (PALETTE:, TYPOGRAPHY:, SPACING:, SITEMAP_JSON:) used for structured Gemini response parsing — avoids JSON schema enforcement at top level"
  - "BUILD_PLAN_PROMPT uses response_mime_type=application/json for reliable JSON-only output from Gemini"
  - "_generate_build_plan has a deterministic fallback (one phase per sitemap page, sequential deps) for Gemini unavailability or parse errors"
  - "Non-fatal _persist_design_draft: SSE still yields ready event even if Supabase write fails"
  - "test_schema_smoke.py excluded from task verification — pre-existing integration test requiring live Supabase credentials, unrelated to this plan"

patterns-established:
  - "SSE streaming: StreamingResponse(async_generator, media_type=text/event-stream) with Cache-Control: no-cache + X-Accel-Buffering: no"
  - "AsyncGenerator service consumed by router: service yields dicts, router JSON-serialises to SSE data lines"
  - "Design locking gate: approve-brief updates design_systems.locked=True, then updates app_projects + build_sessions atomically"

requirements-completed: [FLOW-02, FLOW-03, FLOW-04]

duration: 14min
completed: 2026-03-22
---

# Phase 18 Plan 01: Design Brief Research Backend Summary

**Gemini Flash design research service with parallel Tavily search, SSE progress streaming, and approve-brief lock endpoint advancing projects to 'building' stage**

## Performance

- **Duration:** 14 min
- **Started:** 2026-03-22T02:00:57Z
- **Completed:** 2026-03-22T02:15:43Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Design brief service (`design_brief_service.py`) with async generator orchestrating Tavily parallel search + Gemini synthesis + Supabase persistence
- POST `/app-builder/projects/{id}/research` endpoint streaming SSE events: searching → synthesizing → saving → ready
- POST `/app-builder/projects/{id}/approve-brief` endpoint locking design system, generating phased build plan, advancing stage to "building"
- DB migration adding UNIQUE(project_id) on design_systems enabling reliable upsert
- 15 unit tests all passing (4 service + 11 router), all mocked — no live dependencies required

## Task Commits

Each task was committed atomically:

1. **Task 1: Design brief service with TDD tests** - `765a0ad` (feat)
2. **Task 2: Research SSE and approve-brief endpoints** - `966213e` (feat)

**Plan metadata:** (docs commit below)

_Note: Both tasks followed TDD — RED tests written first, then implementation (GREEN), then lint._

## Files Created/Modified

- `supabase/migrations/20260322000000_design_brief_unique.sql` — UNIQUE constraint on design_systems(project_id)
- `app/services/design_brief_service.py` — Research orchestration service: run_design_research, _parse_design_response, _generate_build_plan, _persist_design_draft
- `app/routers/app_builder.py` — Extended with POST /research (SSE) and POST /approve-brief endpoints + ApproveBriefRequest model
- `tests/unit/app_builder/test_design_brief_service.py` — 4 unit tests for service functions
- `tests/unit/app_builder/test_app_builder_router.py` — 4 new router tests added (SSE steps, 404, lock+advance, build_plan response)

## Decisions Made

- Migration timestamp 20260322000000 used because 20260321700000 was already taken by the analytics_summary_tables migration (auto-resolved, Rule 3)
- `run_design_research` is a true async generator so the router can stream events without buffering
- Tavily competitor + inspiration queries run in parallel via `asyncio.gather` for reduced latency
- Section marker parsing (PALETTE:, TYPOGRAPHY:, etc.) for Gemini responses — each section extracted by string position, JSON-parsed independently with fallback to empty defaults
- `response_mime_type="application/json"` used for `_generate_build_plan` to get clean JSON-only output
- `_persist_design_draft` failures are non-fatal — the SSE "ready" event is still emitted so the frontend is not blocked by transient Supabase issues

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Migration filename conflict resolved**
- **Found during:** Task 1 (DB Migration step)
- **Issue:** Plan specified `20260321700000_design_brief_unique.sql` but that timestamp is already used by `20260321700000_analytics_summary_tables.sql`
- **Fix:** Used `20260322000000_design_brief_unique.sql` instead — next available timestamp
- **Files modified:** `supabase/migrations/20260322000000_design_brief_unique.sql` (created with new name)
- **Verification:** File created successfully, contains UNIQUE constraint
- **Committed in:** 765a0ad (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — filename conflict)
**Impact on plan:** The migration delivers identical functionality under a different timestamp. No scope creep.

## Issues Encountered

- `test_schema_smoke.py` requires live Supabase credentials and fails in the dev environment — this is a pre-existing condition unrelated to this plan. Excluded from verification scope.
- Ruff flagged an unused `section_markers` list variable in `_parse_design_response` — removed in the same task commit.

## User Setup Required

None — no external service configuration required beyond what is already in place (Tavily and Gemini credentials).

## Next Phase Readiness

- Backend research API is complete and tested
- Frontend research page (`18-02`) can now connect to `POST /research` SSE endpoint and `POST /approve-brief`
- Screen generation phase (Phase 19) can read `build_plan` and locked `design_system` from `app_projects`
- No blockers

## Self-Check: PASSED

All files verified present on disk. Both task commits verified in git log.

- FOUND: supabase/migrations/20260322000000_design_brief_unique.sql
- FOUND: app/services/design_brief_service.py
- FOUND: app/routers/app_builder.py
- FOUND: tests/unit/app_builder/test_design_brief_service.py
- FOUND: tests/unit/app_builder/test_app_builder_router.py
- FOUND: .planning/phases/18-design-brief-research/18-01-SUMMARY.md
- COMMIT 765a0ad: feat(18-01): design brief service with TDD tests and DB migration
- COMMIT 966213e: feat(18-01): add research SSE and approve-brief endpoints to app_builder router

---
*Phase: 18-design-brief-research*
*Completed: 2026-03-22*
