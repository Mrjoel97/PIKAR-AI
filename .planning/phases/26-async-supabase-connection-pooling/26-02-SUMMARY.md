---
phase: 26-async-supabase-connection-pooling
plan: 02
subsystem: database
tags: [supabase, asyncio, httpx, connection-pooling, session-service, workflow-engine, rag]

# Dependency graph
requires:
  - phase: 26-async-supabase-connection-pooling
    provides: AsyncSupabaseService singleton, get_async_client(), async execute_async dual-path
provides:
  - Session service using native async Supabase client (zero asyncio.to_thread)
  - Workflow engine using native async Supabase client (~30 table operations)
  - RAG search/ingestion using async .execute() calls
  - Task store cleaned up with direct supabase_client import
affects: [26-03-PLAN, all-callers-of-knowledge-vault-get_supabase_client, all-callers-of-search_knowledge]

# Tech tracking
tech-stack:
  added: []
  patterns: [lazy-async-client-per-service, client-await-self-get-client-pattern, await-chain-execute]

key-files:
  created:
    - tests/unit/test_async_hot_path_migration.py
  modified:
    - app/persistence/supabase_session_service.py
    - app/persistence/supabase_task_store.py
    - app/workflows/engine.py
    - app/rag/knowledge_vault.py
    - app/rag/search_service.py
    - app/rag/ingestion_service.py
    - tests/unit/conftest.py

key-decisions:
  - "SupabaseSessionService uses lazy async client via _get_client() pattern -- avoids async in __init__"
  - "SupabaseTaskStore remains sync because A2A TaskStore interface mandates sync methods (get/save/delete)"
  - "WorkflowEngine._get_workflow_readiness converted from sync def to async def to support await client"
  - "knowledge_vault.get_supabase_client is now async -- all downstream callers must await it"
  - "search_knowledge converted from sync to async, uses semantic_search directly instead of search_knowledge_sync wrapper"
  - "conftest.py updated with BaseSessionService, Session, and Event stubs for session service unit tests"

patterns-established:
  - "lazy-async-client: Store _async_client = None in __init__, populate via async _get_client() on first use"
  - "client-local-var: Each method calls client = await self._get_client() then uses local 'client' reference"
  - "await-chain-execute: Multi-line query chains use await( client.table(...).select(...).execute() )"

requirements-completed: []

# Metrics
duration: 58min
completed: 2026-03-26
---

# Phase 26 Plan 02: Async Hot-Path Migration Summary

**Session service, workflow engine, and RAG services migrated to native async Supabase client -- zero asyncio.to_thread for DB calls in hot-path services**

## Performance

- **Duration:** 58 min
- **Started:** 2026-03-26T19:57:28Z
- **Completed:** 2026-03-26T20:55:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- SupabaseSessionService uses native async client for all 17 DB-touching methods (create/get/delete/list sessions, append_event, versioning, fork, rollback)
- WorkflowEngine uses native async client for all ~30 table operations across templates, executions, steps, and audit writes
- RAG search_service.semantic_search and ingestion_service.ingest_document use await on .execute()
- knowledge_vault.get_supabase_client is now async, search_knowledge/get_content_by_id/list_agent_content all converted to async
- SupabaseTaskStore cleaned to import from supabase_client directly with documented A2A sync rationale
- 21 unit tests covering async migration of all four subsystems

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Migrate SupabaseSessionService and SupabaseTaskStore** (TDD)
   - `e030cbd` test(26-02): add failing tests for async hot-path session and task store migration
   - `5ffd7d3` feat(26-02): migrate session service to native async, clean task store imports

2. **Task 2: Migrate WorkflowEngine and RAG services** (TDD)
   - `0a8fa6b` test(26-02): add failing tests for async workflow engine and RAG migration
   - `7098940` feat(26-02): migrate workflow engine and RAG services to native async client

## Files Created/Modified
- `app/persistence/supabase_session_service.py` - Lazy async client, direct await in _execute_with_retry, removed execute_async import
- `app/persistence/supabase_task_store.py` - Clean import from supabase_client.get_service_client, A2A sync docstring
- `app/workflows/engine.py` - Async client, all .execute() awaited, removed asyncio.to_thread and sync Client import
- `app/rag/knowledge_vault.py` - get_supabase_client now async, search_knowledge/get_content_by_id/list_agent_content async
- `app/rag/search_service.py` - semantic_search uses await on rpc.execute()
- `app/rag/ingestion_service.py` - ingest_document uses await on table.insert.execute()
- `tests/unit/test_async_hot_path_migration.py` - 21 tests covering all four subsystems
- `tests/unit/conftest.py` - Added BaseSessionService, Session, Event stubs for google.adk.sessions mocking

## Decisions Made
- SupabaseSessionService uses `_async_client = None` in `__init__` with lazy `_get_client()` because async operations cannot run in constructors
- SupabaseTaskStore remains sync with documented rationale: A2A TaskStore interface mandates sync `get`/`save`/`delete` methods, and task operations are low-frequency (per-A2A-call not per-message)
- WorkflowEngine `_get_workflow_readiness` converted from `def` to `async def` since it now uses the async client
- knowledge_vault `search_knowledge` changed from sync wrapper calling `search_knowledge_sync` to async function calling `semantic_search` directly
- conftest.py Session mock uses proper `__init__` with `setattr` loop (not list comprehension which returns non-None)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated conftest.py with BaseSessionService, Session, and Event stubs**
- **Found during:** Task 1 (session service tests)
- **Issue:** conftest.py mocked google.adk.sessions but didn't include BaseSessionService or Session, causing ImportError during test collection
- **Fix:** Added BaseSessionService type stub, Session class with kwargs init, Event class with model_dump/model_validate
- **Files modified:** tests/unit/conftest.py
- **Verification:** All 21 tests collect and pass
- **Committed in:** 5ffd7d3 (Task 1 commit)

**2. [Rule 3 - Blocking] WorkflowEngine._get_workflow_readiness converted to async**
- **Found during:** Task 2 (engine async migration)
- **Issue:** Sync `def _get_workflow_readiness` used `self.client.table(...)` which is now an async client requiring `await`
- **Fix:** Changed to `async def`, added `client = await self._get_client()`, updated caller `start_workflow` to `await self._get_workflow_readiness(template)`
- **Files modified:** app/workflows/engine.py
- **Verification:** Syntax validation passes
- **Committed in:** 7098940 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking issues from async conversion)
**Impact on plan:** Both necessary for correctness after async migration. No scope creep.

## Issues Encountered
- Multi-line `.execute()` chains in engine.py (30+ occurrences) required systematic `await` insertion -- the `await` must wrap the entire chain expression, not individual method calls like `.table()` which are synchronous
- python `unittest.mock.patch` cannot resolve implicit namespace package `app.persistence` without explicit module pre-import in the test file

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All four hot-path subsystems (session, task store, workflow engine, RAG) are migrated to native async
- Plan 03 can proceed with remaining service migrations and thread pool right-sizing
- Callers of `knowledge_vault.get_supabase_client()` and `search_knowledge()` that aren't already async will need updating (Plan 03 scope)

## Self-Check: PASSED

All 8 files verified present. All 4 commits verified in git log.

---
*Phase: 26-async-supabase-connection-pooling*
*Completed: 2026-03-26*
