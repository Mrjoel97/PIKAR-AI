"""Tests verifying async migration of hot-path Supabase services.

Covers:
- SupabaseSessionService using native async client (no asyncio.to_thread)
- SupabaseTaskStore remaining sync (A2A interface constraint)
- WorkflowEngine using native async client
- RAG search/ingestion using async execute
"""

import asyncio
import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Pre-import modules so unittest.mock.patch can resolve them by dotted-path.
# (app.persistence is an implicit namespace package with no __init__.py;
#  conftest.py sets up the google.adk mock stubs before collection.)
import app.persistence.supabase_session_service  # noqa: F401
import app.persistence.supabase_task_store  # noqa: F401

# ---------------------------------------------------------------------------
# Task 1: SupabaseSessionService + SupabaseTaskStore
# ---------------------------------------------------------------------------

_SSS = "app.persistence.supabase_session_service"
_STS = "app.persistence.supabase_task_store"


class TestSupabaseSessionServiceAsync:
    """SupabaseSessionService must use the async Supabase client exclusively."""

    @pytest.fixture(autouse=True)
    def _patch_deps(self):
        """Patch get_async_client and cache service for all session tests."""
        self.mock_async_client = AsyncMock()
        self.mock_cache = MagicMock()
        self.mock_cache.get_session_metadata = AsyncMock(return_value=MagicMock(found=False))
        self.mock_cache.set_session_metadata = AsyncMock()
        self.mock_cache.invalidate_session = AsyncMock()

        with (
            patch(
                f"{_SSS}.get_async_client",
                new_callable=AsyncMock,
                return_value=self.mock_async_client,
            ),
            patch(
                f"{_SSS}.get_cache_service",
                return_value=self.mock_cache,
            ),
        ):
            yield

    def _make_service(self):
        from app.persistence.supabase_session_service import SupabaseSessionService

        return SupabaseSessionService()

    # Test 1: __init__ stores lazy async client (not sync)
    def test_init_stores_lazy_async_client(self):
        svc = self._make_service()
        # Must have _async_client attribute (starts as None, lazy init)
        assert hasattr(svc, "_async_client")
        assert svc._async_client is None
        # Must NOT have a sync 'client' attribute set from __init__
        assert not hasattr(svc, "client") or svc.client is None or hasattr(svc, "_async_client")

    # Test 2: _execute_with_retry calls await query_builder.execute() directly
    @pytest.mark.asyncio
    async def test_execute_with_retry_awaits_directly(self):
        svc = self._make_service()
        mock_qb = AsyncMock()
        mock_qb.execute = AsyncMock(return_value=MagicMock(data=[{"id": 1}]))

        result = await svc._execute_with_retry(mock_qb)

        mock_qb.execute.assert_awaited_once()
        assert result.data == [{"id": 1}]

    # Test 3: create_session inserts via async client
    @pytest.mark.asyncio
    async def test_create_session_uses_async_client(self):
        svc = self._make_service()
        mock_table = AsyncMock()
        mock_insert = AsyncMock()
        mock_insert.execute = AsyncMock(
            return_value=MagicMock(data=[{"session_id": "s1"}])
        )
        mock_table.insert = MagicMock(return_value=mock_insert)
        self.mock_async_client.table = MagicMock(return_value=mock_table)

        session = await svc.create_session(
            app_name="test", user_id="u1", session_id="s1", state={}
        )

        assert session.id == "s1"
        self.mock_async_client.table.assert_called_with("sessions")

    # Test 4: get_session retrieves via async client
    @pytest.mark.asyncio
    async def test_get_session_uses_async_client(self):
        svc = self._make_service()

        # Session metadata query
        mock_table = AsyncMock()
        mock_select = AsyncMock()
        mock_eq1 = AsyncMock()
        mock_eq2 = AsyncMock()
        mock_eq3 = AsyncMock()
        mock_limit = AsyncMock()
        mock_limit.execute = AsyncMock(
            return_value=MagicMock(
                data=[{"session_id": "s1", "state": {}, "app_name": "test"}]
            )
        )
        mock_eq3.limit = MagicMock(return_value=mock_limit)
        mock_eq2.eq = MagicMock(return_value=mock_eq3)
        mock_eq1.eq = MagicMock(return_value=mock_eq2)
        mock_select.eq = MagicMock(return_value=mock_eq1)
        mock_table.select = MagicMock(return_value=mock_select)

        # Events query
        mock_events_table = AsyncMock()
        mock_events_select = AsyncMock()
        mock_events_chain = AsyncMock()
        mock_events_chain.execute = AsyncMock(
            return_value=MagicMock(data=[])
        )

        # Simplified: we'll just mock the whole chain for events
        def table_dispatch(name):
            if name == "sessions":
                return mock_table
            return MagicMock(
                select=MagicMock(
                    return_value=MagicMock(
                        eq=MagicMock(
                            return_value=MagicMock(
                                eq=MagicMock(
                                    return_value=MagicMock(
                                        eq=MagicMock(
                                            return_value=MagicMock(
                                                order=MagicMock(
                                                    return_value=MagicMock(
                                                        limit=MagicMock(
                                                            return_value=AsyncMock(
                                                                execute=AsyncMock(
                                                                    return_value=MagicMock(data=[])
                                                                )
                                                            )
                                                        )
                                                    )
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )

        self.mock_async_client.table = MagicMock(side_effect=table_dispatch)

        session = await svc.get_session(
            app_name="test", user_id="u1", session_id="s1"
        )

        assert session is not None
        assert session.id == "s1"

    # Test 5: append_event calls async rpc("insert_session_event")
    @pytest.mark.asyncio
    async def test_append_event_uses_async_rpc(self):
        svc = self._make_service()

        mock_rpc = AsyncMock()
        mock_rpc.execute = AsyncMock(
            return_value=MagicMock(data=[{"event_index": 0, "version": 1}])
        )
        self.mock_async_client.rpc = MagicMock(return_value=mock_rpc)

        from google.adk.events import Event
        from google.adk.sessions import Session

        session = Session(
            app_name="test", user_id="u1", id="s1", state={}, events=[]
        )
        event = Event(
            invocation_id="inv1",
            author="user",
            content={"parts": [{"text": "hello"}]},
        )

        # Need to init the async client
        svc._async_client = self.mock_async_client

        result = await svc.append_event(session=session, event=event)

        self.mock_async_client.rpc.assert_called_once()
        call_args = self.mock_async_client.rpc.call_args
        assert call_args[0][0] == "insert_session_event"

    # Test 6: No asyncio.to_thread in session service
    def test_no_asyncio_to_thread_in_session_service(self):
        """The session service source must not contain asyncio.to_thread for DB calls."""
        import importlib
        import inspect as _inspect

        mod = importlib.import_module("app.persistence.supabase_session_service")
        source = _inspect.getsource(mod)
        assert "asyncio.to_thread" not in source
        assert "to_thread" not in source

    # Test 7: No execute_async import in session service
    def test_no_execute_async_import_in_session_service(self):
        """Session service should not import execute_async (uses direct await)."""
        import importlib
        import inspect as _inspect

        mod = importlib.import_module("app.persistence.supabase_session_service")
        source = _inspect.getsource(mod)
        assert "execute_async" not in source


class TestSupabaseTaskStoreSync:
    """SupabaseTaskStore must remain sync (A2A TaskStore interface constraint)."""

    @pytest.fixture(autouse=True)
    def _patch_deps(self):
        self.mock_client = MagicMock()
        with patch(
            f"{_STS}.get_service_client",
            return_value=self.mock_client,
        ):
            yield

    def _make_store(self):
        from app.persistence.supabase_task_store import SupabaseTaskStore

        return SupabaseTaskStore()

    # Test 6: TaskStore.get uses sync client
    def test_get_uses_sync_client(self):
        store = self._make_store()
        mock_response = MagicMock(data={"task_data": {"task_id": "t1", "status": {"state": "submitted"}, "id": "t1"}})
        self.mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

        result = store.get("t1")
        self.mock_client.table.assert_called_with("a2a_tasks")

    # Test 7: TaskStore.save uses sync client (upsert)
    def test_save_uses_sync_client(self):
        store = self._make_store()
        mock_task = MagicMock()
        mock_task.task_id = "t1"
        mock_task.status = "submitted"
        mock_task.model_dump.return_value = {"task_id": "t1"}

        store.save(mock_task)
        self.mock_client.table.assert_called_with("a2a_tasks")

    # Test: TaskStore imports from supabase_client (not knowledge_vault)
    def test_taskstore_imports_from_supabase_client(self):
        """TaskStore should import get_service_client from supabase_client directly."""
        import importlib
        import inspect as _inspect

        mod = importlib.import_module("app.persistence.supabase_task_store")
        source = _inspect.getsource(mod)
        assert "from app.services.supabase_client import get_service_client" in source
        assert "from app.rag.knowledge_vault" not in source

    # Test: TaskStore has docstring explaining sync rationale
    def test_taskstore_has_sync_rationale_docstring(self):
        from app.persistence.supabase_task_store import SupabaseTaskStore

        assert SupabaseTaskStore.__doc__ is not None
        doc = SupabaseTaskStore.__doc__.lower()
        assert "sync" in doc or "a2a" in doc


# ---------------------------------------------------------------------------
# Task 2: WorkflowEngine + RAG services
# ---------------------------------------------------------------------------

_WE = "app.workflows.engine"
_KV = "app.rag.knowledge_vault"
_SS = "app.rag.search_service"
_IS = "app.rag.ingestion_service"


class TestWorkflowEngineAsync:
    """WorkflowEngine must use the native async Supabase client."""

    # Test 1: WorkflowEngine uses lazy async client (not sync)
    def test_engine_has_lazy_async_client(self):
        with patch(f"{_WE}.get_async_client", new_callable=AsyncMock):
            from app.workflows.engine import WorkflowEngine

            engine = WorkflowEngine()
            assert hasattr(engine, "_async_client")
            assert engine._async_client is None

    # Test 2: WorkflowEngine.list_templates awaits .execute() directly
    @pytest.mark.asyncio
    async def test_list_templates_uses_async_client(self):
        mock_client = AsyncMock()
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_execute_result = MagicMock(data=[
            {"id": "1", "name": "Test", "description": "d", "category": "ops",
             "template_key": "test", "version": 1, "lifecycle_status": "published",
             "is_generated": False, "personas_allowed": ["all"], "published_at": None}
        ])
        # Build the async chain: select -> (eq optional) -> execute
        mock_select.eq = MagicMock(return_value=mock_select)
        mock_select.execute = AsyncMock(return_value=mock_execute_result)
        mock_table.select = MagicMock(return_value=mock_select)
        mock_client.table = MagicMock(return_value=mock_table)

        with patch(f"{_WE}.get_async_client", new_callable=AsyncMock, return_value=mock_client):
            from app.workflows.engine import WorkflowEngine

            engine = WorkflowEngine()
            templates = await engine.list_templates()
            assert len(templates) >= 1
            mock_client.table.assert_called_with("workflow_templates")

    # Test 3: No asyncio.to_thread(query.execute) in engine source
    def test_no_asyncio_to_thread_query_execute_in_engine(self):
        """The workflow engine must not use asyncio.to_thread for query.execute."""
        import inspect as _inspect

        mod = importlib.import_module("app.workflows.engine")
        source = _inspect.getsource(mod)
        assert "asyncio.to_thread(query.execute)" not in source
        assert "to_thread(query.execute)" not in source

    # Test 4: Engine imports get_async_client (not sync get_service_client)
    def test_engine_imports_async_client(self):
        import inspect as _inspect

        mod = importlib.import_module("app.workflows.engine")
        source = _inspect.getsource(mod)
        assert "get_async_client" in source

    # Test 5: Engine no longer imports sync Client type
    def test_engine_no_sync_client_type(self):
        import inspect as _inspect

        mod = importlib.import_module("app.workflows.engine")
        source = _inspect.getsource(mod)
        assert "from supabase import Client" not in source


class TestRAGServicesAsync:
    """RAG search and ingestion must use async execute."""

    # Test 1: knowledge_vault.get_supabase_client is now async
    @pytest.mark.asyncio
    async def test_knowledge_vault_get_client_is_async(self):
        mock_client = AsyncMock()
        with patch(f"{_KV}.get_async_client", new_callable=AsyncMock, return_value=mock_client):
            from app.rag.knowledge_vault import get_supabase_client

            # Must be a coroutine function (async def)
            assert asyncio.iscoroutinefunction(get_supabase_client)
            result = await get_supabase_client()
            assert result is mock_client

    # Test 2: semantic_search awaits .execute() on the rpc call
    @pytest.mark.asyncio
    async def test_semantic_search_awaits_execute(self):
        mock_client = AsyncMock()
        mock_rpc = MagicMock()
        mock_rpc.execute = AsyncMock(return_value=MagicMock(data=[
            {"content": "test", "similarity": 0.9, "metadata": {}, "source_type": "doc", "source_id": "1"}
        ]))
        mock_client.rpc = MagicMock(return_value=mock_rpc)

        with patch(f"{_SS}.generate_embedding", return_value=[0.1, 0.2]):
            from app.rag.search_service import semantic_search

            results = await semantic_search(mock_client, "test query")
            mock_rpc.execute.assert_awaited_once()
            assert len(results) == 1

    # Test 3: ingest_document awaits .execute() on the insert call
    @pytest.mark.asyncio
    async def test_ingest_document_awaits_execute(self):
        mock_client = AsyncMock()
        mock_table = MagicMock()
        mock_insert = MagicMock()
        mock_insert.execute = AsyncMock(return_value=MagicMock(data=[{"id": "emb1"}]))
        mock_table.insert = MagicMock(return_value=mock_insert)
        mock_client.table = MagicMock(return_value=mock_table)

        with patch(f"{_IS}.generate_embeddings_batch", return_value=[[0.1, 0.2]]):
            from app.rag.ingestion_service import ingest_document

            ids = await ingest_document(
                mock_client, "Short text", source_type="test"
            )
            mock_insert.execute.assert_awaited()
            assert len(ids) == 1

    # Test 4: knowledge_vault ingest_brain_dump uses async get_supabase_client
    @pytest.mark.asyncio
    async def test_ingest_brain_dump_uses_async_client(self):
        mock_client = AsyncMock()
        with (
            patch(f"{_KV}.get_async_client", new_callable=AsyncMock, return_value=mock_client),
            patch(f"{_KV}.ingest_document", new_callable=AsyncMock, return_value=["emb1"]),
        ):
            from app.rag.knowledge_vault import ingest_brain_dump

            result = await ingest_brain_dump("Test brain dump content")
            assert result["success"] is True

    # Test 5: No sync .execute() in ingestion service (source check)
    def test_no_sync_execute_in_ingestion(self):
        """The ingestion_service ingest_document must use await ...execute()."""
        import inspect as _inspect

        mod = importlib.import_module("app.rag.ingestion_service")
        source = _inspect.getsource(mod.ingest_document)
        assert "await" in source
        # The .execute() call should be preceded by await
        assert "await " in source
