---
phase: 24
plan: "03"
title: "Database & Auth Scaling"
status: complete
started: "2026-03-25"
completed: "2026-03-25"
duration_minutes: 12
---

## What Was Built

Sized asyncio thread pool to 200 workers for Supabase blocking calls, documented Supabase connection pool constant at 200, and added 60-second in-process JWT LRU cache to eliminate per-request supabase.auth.get_user() network calls.

## Key Files

### Modified
- `app/fast_api_app.py` — ThreadPoolExecutor(200) in lifespan, shutdown in cleanup
- `app/services/supabase_async.py` — SUPABASE_DEFAULT_MAX_CONNECTIONS constant (200)
- `app/app_utils/auth.py` — _token_cache dict, _cache_get/_cache_set/_cache_invalidate, verify_token uses cache

## Requirements Covered

- DBSC-01: ThreadPoolExecutor(200) set as default executor via set_default_executor()
- DBSC-02: SUPABASE_DEFAULT_MAX_CONNECTIONS=200 documented and exported
- DBSC-03: JWT cache with 60s TTL, 10K max entries, thread-safe via threading.Lock
- DBSC-04: thread_pool_size exposed via app.state for health endpoint access

## Decisions

- In-process dict cache (not Redis) for JWT — simple, zero-dependency, correct for Phase 24
- Cache keyed by full token string, not sub claim — prevents cross-token collision
- 10K cap with oldest-entry eviction prevents unbounded growth
- time.monotonic() for TTL — immune to system clock changes
