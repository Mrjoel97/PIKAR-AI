---
phase: 25-sse-streaming-distributed-rate-limiting
plan: "01"
subsystem: backend-streaming
tags:
  - sse
  - redis
  - rate-limiting
  - backpressure
  - async
dependency_graph:
  requires:
    - app/services/cache.py (CacheService._ensure_connection, get_cache_service)
  provides:
    - app/services/sse_connection_limits.py (Redis-backed async SSE tracking)
  affects:
    - app/fast_api_app.py (/a2a/app/run_sse endpoint, /health/connections)
    - app/routers/workflows.py (/executions/{id}/events SSE endpoint)
tech_stack:
  added:
    - SSEAcquireResult (tuple subclass with .reason attribute — backward compat)
    - SSERejectReason (str sentinel constants: SERVER_BACKPRESSURE, PER_USER_LIMIT, PER_USER_RATE)
  patterns:
    - Redis INCR/DECR with EXPIRE for distributed slot tracking
    - SCAN + GET sum for server-wide connection count
    - Fail-open on Redis downtime (SSE never blocked by Redis unavailability)
    - Async pipeline DELETE for test isolation reset
key_files:
  created:
    - app/services/sse_connection_limits.py (complete rewrite)
    - tests/unit/test_sse_connection_limits.py (16 async unit tests)
  modified:
    - app/fast_api_app.py (await callers, 503/429 distinction, health count)
    - app/routers/workflows.py (await callers, 503/429 distinction)
    - app/.env.example (SSE_MAX_NEW_CONN_PER_MINUTE, SSE_MAX_TOTAL_CONNECTIONS, SSE_CONN_TTL_SECONDS)
    - tests/unit/test_configuration_deployment.py (updated to async, uses mocked Redis)
decisions:
  - "SSEAcquireResult subclasses tuple: backward compat with existing tuple-unpack callers while adding .reason for 503/429 discrimination"
  - "Fail-open when Redis unavailable: SSE connections never blocked by Redis downtime; callers get (True, 0, limit)"
  - "INCR + EXPIRE (two commands, not Lua): simpler; race window acceptable for SSE slot management"
  - "Per-user rate key pikar:sse:rate:{user_id} with 60s window set on first INCR only (result==1)"
  - "HTTP 503 for server-wide backpressure (SSE_MAX_TOTAL_CONNECTIONS), HTTP 429 for per-user limits"
  - "SSERejectReason as str subclass (not enum): avoids Enum import overhead, identity comparison still works"
  - "test_configuration_deployment.py SSE tests: updated to async + mocked Redis; TestClient test uses AsyncMock patch on try_acquire"
metrics:
  duration: "16 min"
  completed_date: "2026-03-25"
  tasks_completed: 2
  files_changed: 6
---

# Phase 25 Plan 01: Redis-Backed Async SSE Connection Limits Summary

Redis-backed async SSE slot tracking using INCR/DECR/EXPIRE replacing per-process threading.Lock dict, with per-user rate limiting (RATE-02), server-wide backpressure HTTP 503 (SSES-03), TTL-based orphan cleanup (SSES-04), and health endpoint observability (SSES-05).

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 (RED) | TDD: failing async tests | 455699d | tests/unit/test_sse_connection_limits.py |
| 1 (GREEN) | Rewrite sse_connection_limits.py as Redis-backed async service | e981626 | app/services/sse_connection_limits.py, tests/unit/test_configuration_deployment.py |
| 2 | Update callers — await async functions, wire 503/429, add health count | 3d00fc9 | app/fast_api_app.py, app/routers/workflows.py, app/.env.example |

## What Was Built

### `app/services/sse_connection_limits.py` (complete rewrite)

Replaces the in-process `threading.Lock` / `_active_connection_counts` dict with Redis-backed async operations. The effective per-user limit is now global across all Cloud Run replicas instead of being multiplied by replica count.

**Redis key layout:**
- `pikar:sse:conn:{user_id}` — per-user slot counter (INCR/DECR, 5-min TTL for crash cleanup)
- `pikar:sse:rate:{user_id}` — per-user new connection rate (INCR, 60s sliding window)

**Public API (all async except `get_sse_connection_limit`):**
- `try_acquire_sse_connection(user_id, *, stream_name) -> SSEAcquireResult`
- `release_sse_connection(user_id, *, stream_name) -> int`
- `get_active_sse_connection_count(user_id) -> int`
- `get_total_active_sse_count() -> int`
- `get_sse_connection_limit() -> int` (sync, reads env)
- `reset_sse_connection_limits() -> None` (async test helper)

**`SSEAcquireResult`** subclasses `tuple` so existing callers unpacking `(acquired, active, limit)` continue to work unchanged. The `.reason` attribute (`SSERejectReason.SERVER_BACKPRESSURE | PER_USER_LIMIT | PER_USER_RATE | None`) lets callers select the correct HTTP status code.

**Acquisition order:** fail-open check → server backpressure → per-user rate → per-user slot → INCR + EXPIRE.

### `app/fast_api_app.py`

- `await try_acquire_sse_connection(...)` replaces sync call at `/a2a/app/run_sse`
- `await release_sse_connection(...)` in `finally` and outer `except`
- `SERVER_BACKPRESSURE` reason → HTTP 503; per-user limit/rate → HTTP 429
- `/health/connections` response includes `sse_connections: {total_active, per_user_limit, max_total}`

### `app/routers/workflows.py`

- Same async/await update for `/executions/{id}/events` SSE endpoint
- Ownership `release_sse_connection` calls on 404/403 are now `await`-ed
- `event_stream()` `finally` block uses `await release_sse_connection`
- `SERVER_BACKPRESSURE` → HTTP 503; per-user → HTTP 429

### `app/.env.example`

Three new env vars documented under "STREAMING AND UPLOAD GUARDRAILS":
- `SSE_MAX_NEW_CONN_PER_MINUTE=10`
- `SSE_MAX_TOTAL_CONNECTIONS=500`
- `SSE_CONN_TTL_SECONDS=300`

## Test Results

```
tests/unit/test_sse_connection_limits.py   — 16 passed
tests/unit/test_configuration_deployment.py — 6 passed (2 updated to async + mocked Redis)
Total: 22 passed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_configuration_deployment.py to async**
- **Found during:** Task 1 GREEN verification
- **Issue:** Two existing tests called `try_acquire_sse_connection`, `release_sse_connection`, `reset_sse_connection_limits` synchronously after they became async — producing `RuntimeWarning: coroutine never awaited` and test failures
- **Fix:** `test_sse_connection_limit_counts_all_user_streams` → `@pytest.mark.asyncio` async test with in-memory Redis mock tracking state; `test_run_sse_rejects_excess_active_connections` → mocks `app.fast_api_app.try_acquire_sse_connection` with `AsyncMock(return_value=SSEAcquireResult(False, 1, 1, reason=SSERejectReason.PER_USER_LIMIT))` so TestClient (sync) exercises the 429 path without needing real Redis
- **Files modified:** `tests/unit/test_configuration_deployment.py`
- **Commit:** e981626

## Requirements Satisfied

- SSES-01: Redis-backed SSE tracking (replaces per-process dict)
- SSES-02: Per-user slot limit enforced globally across replicas
- SSES-03: Server-wide backpressure HTTP 503 when total >= SSE_MAX_TOTAL_CONNECTIONS
- SSES-04: TTL-based stale cleanup — 5-min EXPIRE on conn keys covers process crashes
- SSES-05: `/health/connections` includes `sse_connections.total_active`
- RATE-02: Per-user new connection rate limit (HTTP 429, 60-second sliding window)

## Self-Check

```bash
[ -f "app/services/sse_connection_limits.py" ] → FOUND
[ -f "tests/unit/test_sse_connection_limits.py" ] → FOUND
git log: 455699d, e981626, 3d00fc9 → FOUND
grep "threading" app/services/sse_connection_limits.py → PASS: clean
grep "async def try_acquire" app/services/sse_connection_limits.py → FOUND line 197
grep "503" app/fast_api_app.py → FOUND line 1242
grep "sse_connections" via response["sse_connections"] → FOUND
```

## Self-Check: PASSED
