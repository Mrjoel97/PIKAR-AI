---
phase: 71-engine-runtime-fixes
plan: 02
subsystem: embeddings
tags: [asyncio, embeddings, cosine-similarity, startup, skill-cache]

# Dependency graph
requires:
  - phase: 71-engine-runtime-fixes
    provides: "skill_embeddings module with sync warmup and cosine_similarity"
provides:
  - "async build_index() for non-blocking embedding warmup at startup"
  - "search_similar() for cosine-ranked skill lookup from cache"
  - "add_skill_embedding_async() for incremental cache updates"
  - "FastAPI lifespan hook that fires build_index on boot"
affects: [skill_creator, semantic_search, registry]

# Tech tracking
tech-stack:
  added: []
  patterns: [asyncio.to_thread for sync-to-async offload, fire-and-forget create_task in lifespan]

key-files:
  created:
    - tests/unit/test_skill_embeddings.py
  modified:
    - app/skills/skill_embeddings.py
    - app/fast_api_app.py

key-decisions:
  - "build_index wraps existing warmup_skill_embeddings in asyncio.to_thread rather than reimplementing async embedding generation"
  - "Lifespan uses create_task (fire-and-forget) so embedding warmup never delays server startup"
  - "search_similar is sync because generate_embedding is sync; async callers use search_similar_async via to_thread"

patterns-established:
  - "asyncio.to_thread wrapping for sync embedding service calls"
  - "Fire-and-forget background task with done_callback for error logging in lifespan"

requirements-completed: [FIX-04]

# Metrics
duration: 5min
completed: 2026-04-12
---

# Phase 71 Plan 02: Skill Embedding Startup Index Summary

**Async build_index with fire-and-forget lifespan hook, cosine-ranked search_similar, and 6 unit tests**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-12T04:13:01Z
- **Completed:** 2026-04-12T04:18:51Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- async build_index() offloads warmup_skill_embeddings to asyncio.to_thread for non-blocking startup
- search_similar() returns cosine-similarity-ranked (skill_name, score) tuples from the in-memory cache
- FastAPI lifespan fires build_index as a background task after Supabase pre-warm, before A2A init
- 6 unit tests covering build_index, to_thread usage, sorted search, empty-cache degradation, async add, and no-skills edge case

## Task Commits

Each task was committed atomically:

1. **Task 1: Add async build_index and search_similar to skill_embeddings** (TDD)
   - `65cf5e62` test(71-02): add failing tests (RED)
   - `975af011` feat(71-02): implement build_index, search_similar, async wrappers (GREEN)
2. **Task 2: Wire build_index into FastAPI lifespan startup** - `64889ee8` (feat)

## Files Created/Modified
- `app/skills/skill_embeddings.py` - Added async build_index, search_similar, add_skill_embedding_async, search_similar_async
- `app/fast_api_app.py` - Added fire-and-forget create_task(build_index()) in lifespan
- `tests/unit/test_skill_embeddings.py` - 6 tests for all new functions

## Decisions Made
- Wrapped existing sync warmup_skill_embeddings rather than reimplementing async embedding generation -- reuses proven code path
- Used create_task (fire-and-forget) in lifespan so embedding warmup never blocks server readiness
- search_similar is synchronous because generate_embedding is synchronous; async wrapper delegates via to_thread

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mock target path for search_similar test**
- **Found during:** Task 1 (TDD GREEN)
- **Issue:** Plan's test mocked `app.skills.skill_embeddings.generate_embedding` but the function is imported lazily from `app.rag.embedding_service` inside search_similar
- **Fix:** Changed mock target to `app.rag.embedding_service.generate_embedding`
- **Files modified:** tests/unit/test_skill_embeddings.py
- **Verification:** All 6 tests pass
- **Committed in:** 975af011 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Corrected mock target for test accuracy. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- build_index is ready for downstream consumers (skill_creator semantic similarity in FIX-03)
- search_similar/search_similar_async provide the ranking API that skill_creator will call
- Embedding cache is populated automatically on server boot

---
## Self-Check: PASSED

All 3 files verified present. All 3 commit hashes verified in git log.

---
*Phase: 71-engine-runtime-fixes*
*Completed: 2026-04-12*
