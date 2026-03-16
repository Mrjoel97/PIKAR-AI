# Plan: Phase 3 - Async Safety

**Objective:** Remove blocking Supabase and Redis calls from async execution paths, then harden cache initialization so async services remain safe under concurrency.

## Scope Rules
- No new product features or schema changes.
- Preserve current service interfaces, return shapes, and error semantics.
- Use shared async wrappers instead of ad-hoc thread offloads.
- Keep cache fail-soft behavior and circuit-breaker semantics intact.
- Prefer clustered, reviewable refactors over repo-wide churn.

## 1. Standardize Shared Async Execution
**Goal:** make the correct async Supabase pattern easy and consistent.

**Tasks:**
- Treat `app/services/supabase_async.py::execute_async()` as the canonical wrapper for blocking Supabase client calls.
- Add or reuse shared helper methods so `BaseService` / `AdminService` consumers can await Supabase operations without calling `.execute()` directly in async methods.
- Update `app/services/base_service.py` examples and docs so they stop teaching the blocking pattern.
- Audit raw `.execute()` hits in async code and bucket them into required Phase 3 edits versus clearly sync-only code.

**Files:**
- `app/services/supabase_async.py`
- `app/services/base_service.py`
- any shared helpers introduced to reduce repeated conversion logic

## 2. Convert the Shared CRUD Service Cluster
**Goal:** close most of ASYNC-01 and ASYNC-02 with mechanical refactors.

**Tasks:**
- Convert every direct Supabase `.execute()` call in:
  - `app/services/analytics_service.py`
  - `app/services/campaign_service.py`
  - `app/services/compliance_service.py`
  - `app/services/task_service.py`
  - `app/services/support_ticket_service.py`
  - `app/services/recruitment_service.py`
  - `app/services/financial_service.py`
  - `app/services/content_service.py`
- Preserve filtering, pagination, insert/update behavior, and existing return types.
- Add or adjust focused tests for representative create/read/list flows where current coverage is thin.

## 3. Refactor Multi-Query Async Hotpaths
**Goal:** remove blocking calls from the services most likely to stall the event loop under production load.

**Tasks:**
- Convert `app/services/initiative_service.py`, `app/services/user_onboarding_service.py`, `app/services/report_scheduler.py`, and `app/services/journey_audit.py`.
- Review helper methods that chain these services so no blocking `.execute()` remains in the async call path.
- Fold in `app/persistence/supabase_session_service.py` raw async `.execute()` sites so session persistence matches the phase goal.
- Preserve retry, rollback, and compensation behavior where existing persistence code already implements it.

## 4. Harden Cache and Skill Loading Boundaries
**Goal:** satisfy ASYNC-03 and ASYNC-04 without weakening the existing cache resilience work.

**Tasks:**
- Add public cache helper(s) needed by `DatabaseSkillLoader` to store and retrieve serialized skill lists without private `_redis` access.
- Convert all `DatabaseSkillLoader` Supabase operations to async-safe execution.
- Add async-safe locking in `CacheService` around singleton creation, `_ensure_connection()`, and close/reset transitions.
- Verify circuit breaker metrics and `CacheResult` contracts stay stable after the refactor.
- Repair outdated cache tests that still assume pre-`CacheResult` read semantics.

## 5. Verification
**Static and grep checks:**
- Run `rg -n "\.execute\(" app/services app/skills app/persistence` and confirm remaining hits are either sync-only, inside the shared wrapper, or in comments/docstrings that should be updated.
- Confirm `DatabaseSkillLoader` no longer references `_redis` directly.

**Targeted tests:**
- `uv run pytest tests/unit/test_database_skill_loader.py -q`
- `uv run pytest tests/unit/test_user_workflow_storage.py -q`
- `uv run pytest tests/unit/test_workflow_execution_contracts.py -q`
- `uv run pytest tests/test_cache_service.py -q`
- `uv run pytest tests/test_cache_integration.py -q`
- Add or update focused tests for converted service clusters, especially onboarding and report scheduling if current coverage does not exercise the changed async paths.

**Async and concurrency checks:**
- Add a focused test that concurrent cache access does not create multiple Redis clients or race `_ensure_connection()`.
- Add a regression test ensuring the skill loader cache write path goes through public `CacheService` methods.
- Smoke-test representative async service methods under `pytest.mark.asyncio` to ensure awaited Supabase calls still return current shapes.

## Execution Order
1. Lock the shared async execution pattern and update base helpers/docs.
2. Convert the shared CRUD service cluster.
3. Refactor the deep multi-query services and session persistence edges.
4. Harden cache initialization and `DatabaseSkillLoader` cache boundaries.
5. Run grep-based audits and targeted pytest slices, then update planning/state artifacts.

## Risks
- Some services mix sync helper assumptions into async methods, so purely mechanical replacement may miss chained blocking calls.
- `app/persistence/supabase_session_service.py` already has partial async wrappers, so inconsistent patterns could survive unless every async path is audited.
- Existing cache tests appear out of sync with the current `CacheResult` contract and may need correction before they provide signal.
- Cache locking changes can introduce deadlocks or stale-connection bugs if close/reset flows are not exercised.
