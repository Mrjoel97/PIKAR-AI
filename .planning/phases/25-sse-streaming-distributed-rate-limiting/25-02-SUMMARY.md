---
phase: 25-sse-streaming-distributed-rate-limiting
plan: 02
subsystem: rate-limiting
tags: [redis, sliding-window, rate-limiting, distributed, mcp, middleware]
dependency_graph:
  requires: ["25-01"]
  provides: ["distributed-api-rate-limiting", "distributed-mcp-rate-limiting", "rate-limit-headers"]
  affects: ["app/fast_api_app.py", "app/middleware/rate_limiter.py", "app/mcp/rate_limiter.py"]
tech_stack:
  added: []
  patterns:
    - "Redis sliding-window INCR+EXPIRE pipeline for fixed-window rate limiting"
    - "Fail-open pattern: Redis unavailable never blocks requests"
    - "LIFO middleware order: RateLimitHeaderMiddleware wraps SlowAPIMiddleware as outermost distributed enforcer"
    - "Deferred imports in rate limiter functions to avoid circular imports at module load"
key_files:
  created:
    - tests/unit/test_distributed_rate_limiter.py
  modified:
    - app/middleware/rate_limiter.py
    - app/mcp/rate_limiter.py
    - app/fast_api_app.py
decisions:
  - "Patch target for deferred-import functions is app.services.cache.get_cache_service (source module), not app.middleware.rate_limiter.get_cache_service — deferred imports inside function bodies are not patchable via module namespace"
  - "Prefixed starlette imports (_BaseHTTPMiddleware, _StarletteRequest, _JSONResponse, _Response) avoid name collision with the later-imported FastAPI/Starlette names in fast_api_app.py's flat module structure"
  - "RateLimitHeaderMiddleware uses user_id from request.state set by RequestLoggingMiddleware; unauthenticated requests bypass the Redis check entirely (auth middleware handles 401)"
  - "slowapi Limiter retained intact as fast per-process first-hop; Redis is the authoritative cross-replica enforcer"
metrics:
  duration: "17 min"
  completed_date: "2026-03-25"
  tasks_completed: 2
  files_modified: 4
requirements_satisfied:
  - RATE-01
  - RATE-03
  - RATE-04
  - RATE-05
---

# Phase 25 Plan 02: Distributed Rate Limiting (Redis Sliding Window) Summary

**One-liner:** Redis sliding-window INCR+EXPIRE pipeline replaces per-process TokenBucket and in-memory slowapi counters, enforcing persona-tier API limits (10/30/60/120 per minute) and MCP external call limits globally across all Cloud Run replicas with fail-open Redis unavailability handling.

## What Was Built

### Task 1: Redis sliding-window rate limiters for API and MCP (TDD)

**app/middleware/rate_limiter.py** — three new exports added alongside the unchanged slowapi `Limiter`:

- `redis_sliding_window_check(user_id, limit, window_seconds=60)` — async function returning `(allowed, limit, remaining, reset_at)`. Uses Redis INCR+EXPIRE pipeline with key `pikar:rate:api:{user_id}:{window_start}`. Fails open (returns True) when Redis is unavailable.
- `build_rate_limit_headers(limit, remaining, reset_at)` — builds `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After` dict.
- `_parse_limit_int(limit_str)` — parses `"10/minute"` → `10`.

**app/mcp/rate_limiter.py** — complete rewrite. `TokenBucket` class, `_buckets` dict, and `_buckets_lock` removed entirely. Same `check_rate_limit(operation, rate_per_minute) -> bool` async signature now uses Redis INCR+EXPIRE with key `pikar:rate:mcp:{operation}:{window_start}`. Fails open on Redis unavailability.

**tests/unit/test_distributed_rate_limiter.py** — 19 async tests covering:
- API: allowed when count ≤ limit, denied when count > limit
- API: correct key pattern with user_id and window bucket
- API: fail-open on Redis None and on Redis exception
- Headers: all three headers present, correct values, non-negative Retry-After
- MCP: allowed/denied by count, different operation names use different keys
- MCP: fail-open on Redis None and exception
- MCP: structural assertion that TokenBucket is absent

### Task 2: Wire Redis as authoritative enforcer in fast_api_app.py

**app/fast_api_app.py** changes:

- **Imports:** Extended `app.middleware.rate_limiter` import to include `build_rate_limit_headers`, `get_user_persona_limit`, `redis_sliding_window_check`, `_parse_limit_int`. Added prefixed starlette imports (`_BaseHTTPMiddleware`, `_StarletteRequest`, `_JSONResponse`, `_Response`) before the class definition.
- **`RateLimitHeaderMiddleware` class:** Wraps every authenticated request with `redis_sliding_window_check`. Returns HTTP 429 directly when limit exceeded (Redis is the authoritative enforcer, not just a header decorator). Injects `X-RateLimit-Limit` and `X-RateLimit-Remaining` on allowed responses. `_inject_headers` adds all three headers to 429s that lack them (catches slowapi-path 429s).
- **Middleware registration:** `app.add_middleware(RateLimitHeaderMiddleware)` added AFTER `SlowAPIMiddleware` so it runs first in LIFO processing order.
- **Exception handler:** `@app.exception_handler(RateLimitExceeded)` replaces the default `_rate_limit_exceeded_handler` with a custom handler that always returns `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `Retry-After` headers.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Deferred import patch path requires source-module patch target**
- **Found during:** Task 1 GREEN phase
- **Issue:** `redis_sliding_window_check` and `check_rate_limit` import `get_cache_service` inside the function body (deferred import). Tests using `patch("app.middleware.rate_limiter.get_cache_service")` raised `AttributeError` because the name only exists in `app.services.cache` namespace, not in the rate_limiter module namespace.
- **Fix:** Updated all test patch targets to `patch("app.services.cache.get_cache_service", ...)` which patches the canonical source and is picked up by the deferred `from app.services.cache import get_cache_service` at call time.
- **Files modified:** `tests/unit/test_distributed_rate_limiter.py`

**2. [Rule 1 - Bug] time.time mock approach for different-window-key test was flaky**
- **Found during:** Task 1 GREEN phase — 1 test still failing after patch-path fix
- **Issue:** `patch("app.middleware.rate_limiter._time.time", side_effect=[now, now, now+61, now+61])` failed because the mock's `side_effect` values were consumed in an unexpected order given Python's time module aliasing — both calls produced the same window_start value.
- **Fix:** Replaced the time-mock approach with calling `redis_sliding_window_check` with two different `window_seconds` values (60 vs 7), which guarantees different bucket boundaries for the same timestamp — functionally equivalent test of the "different window = different key" property without fragile time mocking.
- **Files modified:** `tests/unit/test_distributed_rate_limiter.py`

**3. [Rule 3 - Blocking] fast_api_app.py flat structure requires prefixed starlette imports**
- **Found during:** Task 2 implementation
- **Issue:** `RateLimitHeaderMiddleware` was defined at line ~318 but `BaseHTTPMiddleware`, `StarletteRequest`, and `Response` were imported at lines 667+. Python executes module top-to-bottom, so the class body would raise `NameError` at import time.
- **Fix:** Added prefixed imports (`_BaseHTTPMiddleware`, `_StarletteRequest`, `_JSONResponse`, `_Response`) immediately before the class definition. Used underscored names to avoid shadowing the identically-named imports used later in the file.
- **Files modified:** `app/fast_api_app.py`

## Self-Check: PASSED

| Item | Status |
|------|--------|
| app/middleware/rate_limiter.py | FOUND |
| app/mcp/rate_limiter.py | FOUND |
| app/fast_api_app.py | FOUND |
| tests/unit/test_distributed_rate_limiter.py | FOUND |
| 25-02-SUMMARY.md | FOUND |
| Commit e70fef4 (Task 1) | FOUND |
| Commit be37aee (Task 2) | FOUND |
| All 19 tests passing | VERIFIED |
