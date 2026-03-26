---
phase: 27-production-deployment-hardening
plan: 02
subsystem: infra
tags: [docker, cloud-run, redis, gunicorn, scaling, persona-cache]

# Dependency graph
requires:
  - phase: 25-sse-streaming-distributed-rate-limiting
    provides: Redis sliding-window rate limiting and CacheService._ensure_connection pattern
provides:
  - docker-compose.prod.yml production override (gunicorn, no hot-reload)
  - cloudrun.yaml declarative Cloud Run scaling (min 2, max 20, concurrency 250)
  - Makefile deploy target with production scaling flags
  - Redis-backed persona cache (L1 local dict + L2 Redis) shared across replicas
  - warm_persona_cache async entry point for SSE/middleware callers
affects: [28-persona-ux, deployment, scaling]

# Tech tracking
tech-stack:
  added: []
  patterns: [L1-L2-cache-layering, redis-persona-shared-cache, docker-compose-override]

key-files:
  created:
    - docker-compose.prod.yml
    - cloudrun.yaml
    - tests/unit/test_redis_persona_cache.py
  modified:
    - Makefile
    - app/middleware/rate_limiter.py

key-decisions:
  - "docker-compose.prod.yml uses explicit gunicorn command (not command: []) for maximum Docker Compose version compatibility"
  - "L1/L2 cache layering: sync get_user_persona_limit reads L1 (local dict); async warm_persona_cache populates both L1 and L2 (Redis)"
  - "Redis persona key pattern pikar:persona:{user_id} matches REDIS_KEY_PREFIXES in cache.py (RDSC-04)"

patterns-established:
  - "L1/L2 cache pattern: sync callers read local dict, async callers populate both layers via _set_cached_persona_async"
  - "Docker Compose override pattern: docker-compose.prod.yml overrides dev settings without modifying base file"

requirements-completed: []

# Metrics
duration: 8min
completed: 2026-03-26
---

# Phase 27 Plan 02: Production Docker, Cloud Run Scaling, and Redis Persona Cache Summary

**Docker production compose with gunicorn, Cloud Run YAML for 1000+ user scaling, and L1/L2 Redis-backed persona cache shared across replicas**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-26T21:35:19Z
- **Completed:** 2026-03-26T21:43:15Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created docker-compose.prod.yml overriding dev uvicorn --reload with gunicorn from Dockerfile CMD
- Created cloudrun.yaml with minScale 2, maxScale 20, containerConcurrency 250, startup/liveness probes
- Updated Makefile deploy target with min-instances 2, max-instances 20, concurrency 250, cpu 2, timeout 600
- Replaced per-process in-memory persona cache with L1 (local dict) + L2 (Redis) layered cache
- Added warm_persona_cache async entry point for SSE endpoint / middleware callers
- All 10 unit tests pass covering Redis reads, writes, fallback, backfill, and cleanup

## Task Commits

Each task was committed atomically:

1. **Task 1: Docker production compose and Cloud Run service YAML** - `203672c` (feat)
2. **Task 2 RED: Failing tests for Redis persona cache** - `195714b` (test)
3. **Task 2 GREEN: Redis-backed persona cache implementation** - `cfdc747` (feat)

## Files Created/Modified
- `docker-compose.prod.yml` - Production Docker Compose override (gunicorn, no volumes, no watch)
- `cloudrun.yaml` - Cloud Run service YAML with scaling parameters and health probes
- `Makefile` - Deploy target updated with min-instances 2, max-instances 20, concurrency 250
- `app/middleware/rate_limiter.py` - Added _REDIS_PERSONA_PREFIX, _get_cached_persona_async, _set_cached_persona_async, warm_persona_cache
- `tests/unit/test_redis_persona_cache.py` - 10 async tests covering L1/L2 cache behavior

## Decisions Made
- Used explicit gunicorn command in docker-compose.prod.yml rather than `command: []` for Docker Compose version compatibility
- L1/L2 cache layering keeps the sync get_user_persona_limit reading only the local dict (L1); the async warm_persona_cache populates both layers
- Redis key pattern `pikar:persona:{user_id}` follows the established REDIS_KEY_PREFIXES convention from cache.py (RDSC-04)
- _ensure_connection used instead of _get_redis to match the Phase 25 established pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed line-length lint violation in new code**
- **Found during:** Task 2 (Redis persona cache implementation)
- **Issue:** Line 91 exceeded 88-char limit (persona decode ternary)
- **Fix:** Wrapped ternary expression in parentheses across multiple lines
- **Files modified:** app/middleware/rate_limiter.py
- **Verification:** `ruff check app/middleware/rate_limiter.py` passes
- **Committed in:** cfdc747 (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial formatting fix, no scope change.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Production Docker and Cloud Run infrastructure ready for deployment
- Persona cache shared across replicas via Redis -- SSE endpoints or auth middleware should call warm_persona_cache when persona is resolved from DB
- Phase 28 (persona UX) can rely on consistent persona lookups across all backend instances

---
*Phase: 27-production-deployment-hardening*
*Completed: 2026-03-26*
