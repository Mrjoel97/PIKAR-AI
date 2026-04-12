---
phase: 72-skill-refinement-persistence
plan: 02
subsystem: api
tags: [skills, hydration, versioning, cold-start, fastapi]

# Dependency graph
requires:
  - phase: 72-skill-refinement-persistence/01
    provides: skill_versions table with unique partial index, write-through on refinement
provides:
  - hydrate_skills_from_db function that patches in-memory registry from DB on startup
  - GET /self-improvement/skills/{name}/history endpoint with diff summaries
affects: [72-03, 72-04, self-improvement-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns: [startup-hydration-from-db, version-chain-diff-summary]

key-files:
  created:
    - app/skills/skill_hydration.py
    - tests/unit/test_skill_hydration.py
  modified:
    - app/fast_api_app.py
    - app/routers/self_improvement.py

key-decisions:
  - "Hydration runs synchronously (awaited) in lifespan because skills must be correct before accepting requests; unlike embedding warmup which is fire-and-forget"
  - "Lazy imports inside hydrate_skills_from_db; tests patch at source module (app.services.supabase_client) not at hydration module namespace"
  - "Starlette Request mock required for slowapi rate limiter compatibility in direct endpoint tests"

patterns-established:
  - "Startup hydration pattern: await DB read in lifespan, patch singleton registry, log count, catch-all exception returns 0"
  - "Version chain diff: build by_id lookup, compare knowledge lengths + version strings for diff_summary"

requirements-completed: [SIE-04, SIE-05]

# Metrics
duration: 14min
completed: 2026-04-12
---

# Phase 72 Plan 02: Startup Hydration & Version History API Summary

**Startup skill hydration from skill_versions DB so refined knowledge survives Cloud Run cold starts, plus admin version history endpoint with diff summaries**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-12T14:39:28Z
- **Completed:** 2026-04-12T14:53:01Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Startup hydration reads active skill_versions rows and patches in-memory SkillsRegistry before server accepts requests
- DB failure during hydration is non-fatal (logs warning, returns 0, skills keep built-in knowledge)
- GET /self-improvement/skills/{name}/history returns ordered version chain newest-first with diff_summary between consecutive versions
- 9 unit tests covering hydration logic (5) and history endpoint (4)

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Create skill_hydration module and startup wiring**
   - `40ce970e` (test: failing tests for hydration)
   - `169725da` (feat: implement hydration module + lifespan wiring)
2. **Task 2: Add skill version history API endpoint**
   - `e1af00b0` (test: failing tests for history endpoint)
   - `a74b297b` (feat: implement history endpoint + response model)

## Files Created/Modified
- `app/skills/skill_hydration.py` - hydrate_skills_from_db reads active versions and patches registry
- `app/fast_api_app.py` - Lifespan calls hydrate_skills_from_db after embedding warmup
- `app/routers/self_improvement.py` - SkillVersionResponse model + GET /skills/{name}/history endpoint
- `tests/unit/test_skill_hydration.py` - 9 tests for hydration + history

## Decisions Made
- Hydration awaited synchronously in lifespan (fast single DB query, correctness-critical) vs fire-and-forget embedding warmup
- Tests patch source modules (app.services.supabase_client, app.services.supabase_async) because hydration uses lazy imports inside function body
- StarletteRequest mock with ASGI scope for slowapi rate limiter compatibility (MagicMock fails isinstance check)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed test mock targets for lazy imports**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Plan specified patching app.skills.skill_hydration.get_service_client but lazy imports inside function don't bind to module namespace
- **Fix:** Changed patch targets to source modules: app.services.supabase_client.get_service_client and app.services.supabase_async.execute_async
- **Files modified:** tests/unit/test_skill_hydration.py
- **Verification:** All 5 hydration tests pass
- **Committed in:** 169725da

**2. [Rule 3 - Blocking] Fixed Starlette Request mock for slowapi**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** slowapi limiter validates isinstance(request, Request) so MagicMock fails
- **Fix:** Added _make_mock_request() helper creating minimal StarletteRequest with ASGI scope
- **Files modified:** tests/unit/test_skill_hydration.py
- **Verification:** All 9 tests pass
- **Committed in:** a74b297b

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for test correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Hydration module and history endpoint are complete and tested
- Phase 72 Plan 03 (if exists) can build on the version chain for rollback UI or scheduled improvement triggers

---
*Phase: 72-skill-refinement-persistence*
*Completed: 2026-04-12*
