# Phase 3: Async Safety - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove event-loop blocking from async persistence and cache paths. Convert live async service methods away from direct Supabase `.execute()` calls, stop cache-layer private access from `DatabaseSkillLoader`, and make `CacheService` initialization safe under concurrent async callers. No schema changes, no new product features, and no intentional API contract changes.

</domain>

<decisions>
## Implementation Decisions

### Shared Supabase execution path
- Reuse `app/services/supabase_async.py::execute_async()` as the canonical wrapper for blocking Supabase client calls
- Prefer shared helper methods and base-class affordances over ad-hoc `asyncio.to_thread(...)` sprinkled through service files
- Update `BaseService` examples/docs so async methods no longer advertise raw `.execute()` usage

### Scope of conversion
- Required service set is the roadmap list: analytics, campaign, compliance, task, support_ticket, recruitment, financial, content, initiative, onboarding, report_scheduler, and journey_audit
- Include adjacent async persistence paths that still call blocking `.execute()` from async code, especially `app/persistence/supabase_session_service.py` and `app/skills/database_loader.py`
- Preserve existing return shapes, filters, pagination, and error behavior while swapping execution model

### Cache boundary
- `DatabaseSkillLoader` must stop reaching into `CacheService._redis`
- Prefer adding or using public cache helpers over duplicating Redis key logic in callers
- Keep the Redis circuit breaker intact while removing private bypasses

### CacheService concurrency
- Add async-safe locking around singleton and connection initialization, plus close/reset transitions
- Prevent concurrent coroutines from double-creating Redis clients or racing `_redis` / `_connected` mutation
- Keep cache failures fail-soft so primary request flows continue when Redis is unavailable

### Test strategy
- Add focused async tests around converted services where coverage already exists
- Repair outdated cache tests that still assert old return contracts instead of `CacheResult`
- Favor targeted regression coverage over broad integration churn

</decisions>

<specifics>
## Specific Ideas

- This phase is about latency safety and correctness under load, not feature work
- The 500k+ user target makes event-loop blocking and cache connection races production issues even if local smoke tests pass
- Favor reviewable conversion clusters: shared CRUD services first, then deep multi-query services, then cache/session-adjacent edges

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/supabase_async.py`: existing `execute_async()` wrapper around blocking `query_builder.execute()`
- `app/services/base_service.py`: shared service base that still documents raw `.execute()` usage in async methods
- `app/services/cache.py`: singleton/cache connection lifecycle and circuit breaker behavior
- `app/skills/database_loader.py`: async loader methods still use sync `.execute()` and private `_redis` writes
- `app/persistence/supabase_session_service.py`: already has executor-based retry helpers but still contains raw `.execute()` sites

### Hotspots
- Shared CRUD-style services with direct `.execute()`: `analytics_service.py`, `campaign_service.py`, `compliance_service.py`, `task_service.py`, `support_ticket_service.py`, `recruitment_service.py`, `financial_service.py`, and `content_service.py`
- Deep refactor services with many async DB calls: `initiative_service.py`, `user_onboarding_service.py`, and `report_scheduler.py`
- Smaller async leak: `journey_audit.py`
- Async persistence still contains raw `.execute()` calls in `app/persistence/supabase_session_service.py`
- `app/routers/workflows.py` and `app/fast_api_app.py` already show the target pattern: `await execute_async(...)`

### Established Patterns
- The Supabase Python client remains sync; async safety comes from central wrappers rather than swapping libraries
- Cache reads return `CacheResult`, while cache writes/invalidation return booleans
- Redis cache uses circuit-breaker semantics and must remain optional/fail-soft

### Integration Points
- The affected services are used by API routes and workflows running in async contexts
- `tests/unit/test_user_workflow_storage.py` and `tests/unit/test_workflow_execution_contracts.py` cover session/workflow persistence expectations
- `tests/unit/test_database_skill_loader.py` plus cache tests need to enforce the public cache boundary and concurrency behavior

</code_context>

<deferred>
## Deferred Ideas

- Replacing the Supabase Python client or adding a full repository abstraction
- Broad cache API redesign beyond what is needed to remove private `_redis` access and add async-safe initialization
- Performance benchmarking and observability work beyond regression checks for blocking calls

</deferred>

---

*Phase: 03-async-safety*
*Context gathered: 2026-03-13*
