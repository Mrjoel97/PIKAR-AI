"""Unit tests verifying batch write behavior for workflow engine and session service.

Tests ensure that N+1 sequential DB writes are replaced with single batch operations:
- resume_execution: single .in_() UPDATE for failed/skipped/cancelled steps
- rollback_session: single .in_() UPDATE for superseded events
- fork_session: single bulk .insert() for all copied events
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

async def _exec_with_retry(query):
    """Async helper that mimics _execute_with_retry by awaiting query.execute()."""
    return await query.execute()


def _make_step(step_id: str, status: str) -> dict:
    return {
        "id": step_id,
        "status": status,
        "phase_index": 0,
        "step_index": 0,
    }


# ---------------------------------------------------------------------------
# Tests for engine.resume_execution — batch step reset
# ---------------------------------------------------------------------------

class TestResumeExecutionBatchUpdate:
    """resume_execution must reset failed/skipped/cancelled steps in one UPDATE."""

    @pytest.mark.asyncio
    async def test_five_failed_steps_issues_one_update(self):
        """Test 1: 5 failed steps -> one .update().in_() call, not 5."""
        from app.workflows.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        engine._async_client = None

        # 5 failed steps; none are completed so last_completed_idx = -1
        steps = [_make_step(f"step-{i}", "failed") for i in range(5)]
        expected_ids = [s["id"] for s in steps]

        # Tracked update chain for workflow_steps
        update_chain = MagicMock()
        update_chain.in_.return_value = update_chain
        update_chain.eq.return_value = update_chain
        update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))

        # steps select chain
        steps_select = MagicMock()
        steps_select.select.return_value = steps_select
        steps_select.eq.return_value = steps_select
        steps_select.order.return_value = steps_select
        steps_select.execute = AsyncMock(return_value=MagicMock(data=steps))

        steps_table = MagicMock()
        steps_table.select.return_value = steps_select
        steps_table.update.return_value = update_chain

        # workflow_executions chain
        exec_data = [{"id": "exec-1", "status": "failed", "workflow_id": "wf-1", "user_id": "user-1"}]
        exec_chain = MagicMock()
        exec_chain.select.return_value = exec_chain
        exec_chain.eq.return_value = exec_chain
        exec_chain.order.return_value = exec_chain
        exec_chain.limit.return_value = exec_chain
        exec_chain.update.return_value = exec_chain
        exec_chain.execute = AsyncMock(return_value=MagicMock(data=exec_data))

        def table_router(name: str) -> MagicMock:
            if name == "workflow_steps":
                return steps_table
            if name == "workflow_executions":
                return exec_chain
            m = MagicMock()
            m.select.return_value = m
            m.update.return_value = m
            m.insert.return_value = m
            m.eq.return_value = m
            m.execute = AsyncMock(return_value=MagicMock(data=[]))
            return m

        client = MagicMock()
        client.table = MagicMock(side_effect=table_router)

        engine._get_client = AsyncMock(return_value=client)
        engine._audit_execution_action = AsyncMock()
        engine.get_execution_status = AsyncMock(
            return_value={
                "execution": {
                    "id": "exec-1",
                    "status": "failed",
                    "user_id": "user-1",
                    "workflow_id": "wf-1",
                },
                "steps": steps,
            }
        )

        with patch("app.workflows.engine.edge_function_client") as mock_edge:
            mock_edge.execute_workflow = AsyncMock(return_value={"status": "ok"})
            try:
                await engine.resume_execution(execution_id="exec-1", user_id="user-1")
            except Exception:
                pass  # Full success not required -- only call count matters

        # Single .in_() must have been called once with all 5 IDs
        assert update_chain.in_.call_count == 1, (
            f"Expected 1 batch .in_() UPDATE, got {update_chain.in_.call_count}"
        )
        args = update_chain.in_.call_args[0]
        assert args[0] == "id", f"First arg should be 'id', got {args[0]!r}"
        assert set(args[1]) == set(expected_ids), (
            f"Batch should include all 5 IDs; got {args[1]}"
        )

    @pytest.mark.asyncio
    async def test_zero_failed_steps_issues_no_update(self):
        """Test 4: 0 failed steps (all completed) -> no UPDATE issued at all."""
        from app.workflows.engine import WorkflowEngine

        engine = WorkflowEngine.__new__(WorkflowEngine)
        engine._async_client = None

        steps = [_make_step(f"step-{i}", "completed") for i in range(3)]

        update_chain = MagicMock()
        update_chain.in_.return_value = update_chain
        update_chain.eq.return_value = update_chain
        update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))

        steps_select = MagicMock()
        steps_select.select.return_value = steps_select
        steps_select.eq.return_value = steps_select
        steps_select.order.return_value = steps_select
        steps_select.execute = AsyncMock(return_value=MagicMock(data=steps))

        steps_table = MagicMock()
        steps_table.select.return_value = steps_select
        steps_table.update.return_value = update_chain

        exec_data = [{"id": "exec-1", "status": "failed", "user_id": "user-1", "workflow_id": "wf-1"}]
        exec_chain = MagicMock()
        exec_chain.select.return_value = exec_chain
        exec_chain.eq.return_value = exec_chain
        exec_chain.order.return_value = exec_chain
        exec_chain.limit.return_value = exec_chain
        exec_chain.update.return_value = exec_chain
        exec_chain.execute = AsyncMock(return_value=MagicMock(data=exec_data))

        def table_router(name: str) -> MagicMock:
            if name == "workflow_steps":
                return steps_table
            if name == "workflow_executions":
                return exec_chain
            m = MagicMock()
            m.select.return_value = m
            m.update.return_value = m
            m.eq.return_value = m
            m.execute = AsyncMock(return_value=MagicMock(data=[]))
            return m

        client = MagicMock()
        client.table = MagicMock(side_effect=table_router)

        engine._get_client = AsyncMock(return_value=client)
        engine._audit_execution_action = AsyncMock()
        engine.get_execution_status = AsyncMock(
            return_value={
                "execution": {
                    "id": "exec-1",
                    "status": "failed",
                    "user_id": "user-1",
                    "workflow_id": "wf-1",
                },
                "steps": steps,
            }
        )

        with patch("app.workflows.engine.edge_function_client") as mock_edge:
            mock_edge.execute_workflow = AsyncMock(return_value={"status": "ok"})
            try:
                await engine.resume_execution(execution_id="exec-1", user_id="user-1")
            except Exception:
                pass

        assert update_chain.in_.call_count == 0, (
            f"Expected 0 .in_() calls for all-completed steps, got {update_chain.in_.call_count}"
        )


# ---------------------------------------------------------------------------
# Tests for supabase_session_service.rollback_session -- batch supersede
# ---------------------------------------------------------------------------

class TestRollbackSessionBatchUpdate:
    """rollback_session must supersede events in a single .in_() UPDATE."""

    def _make_service(self):
        """Instantiate SupabaseSessionService without real connections."""
        from app.persistence.supabase_session_service import SupabaseSessionService

        svc = SupabaseSessionService.__new__(SupabaseSessionService)
        svc.sessions_table = "sessions"
        svc.events_table = "session_events"
        svc._cache = MagicMock()
        svc._cache.invalidate_session = AsyncMock()
        svc._supabase_client = None
        return svc

    @pytest.mark.asyncio
    async def test_three_superseded_events_issues_one_update(self):
        """Test 2: 3 events to supersede -> one .update().in_() call, not 3."""
        svc = self._make_service()

        event_ids = ["evt-a", "evt-b", "evt-c"]
        events_data = [{"id": eid} for eid in event_ids]

        # Tracked update chain
        update_chain = MagicMock()
        update_chain.in_.return_value = update_chain
        update_chain.eq.return_value = update_chain
        update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))

        # insert chain for rollback marker
        insert_chain = MagicMock()
        insert_chain.execute = AsyncMock(
            return_value=MagicMock(data=[{"id": "rollback-evt-id"}])
        )

        # select chain: version query then events_to_supersede
        select_chain = MagicMock()
        select_chain.eq.return_value = select_chain
        select_chain.gt.return_value = select_chain
        select_chain.is_.return_value = select_chain
        select_chain.order.return_value = select_chain
        select_chain.limit.return_value = select_chain
        select_chain.execute = AsyncMock(
            side_effect=[
                MagicMock(data=[{"version": 5}]),  # version query
                MagicMock(data=events_data),         # events_to_supersede
            ]
        )

        sessions_update = MagicMock()
        sessions_update.eq.return_value = sessions_update
        sessions_update.execute = AsyncMock(return_value=MagicMock(data=[]))

        def table_router(name: str) -> MagicMock:
            if name == "session_events":
                m = MagicMock()
                m.select.return_value = select_chain
                m.insert.return_value = insert_chain
                m.update.return_value = update_chain
                return m
            if name == "sessions":
                m = MagicMock()
                m.update.return_value = sessions_update
                return m
            m = MagicMock()
            m.select.return_value = m
            m.update.return_value = m
            m.eq.return_value = m
            m.execute = AsyncMock(return_value=MagicMock(data=[]))
            return m

        client = MagicMock()
        client.table = MagicMock(side_effect=table_router)

        mock_target = MagicMock()
        mock_target.events = []

        svc._get_client = AsyncMock(return_value=client)
        svc._execute_with_retry = _exec_with_retry
        svc.get_session_at_version = AsyncMock(return_value=mock_target)
        svc.get_session = AsyncMock(return_value=mock_target)
        svc._ensure_uuid_str = lambda x: str(x)

        await svc.rollback_session(
            app_name="test-app",
            user_id="user-1",
            session_id="sess-1",
            to_version=2,
        )

        assert update_chain.in_.call_count == 1, (
            f"Expected 1 batch .in_() UPDATE, got {update_chain.in_.call_count}"
        )
        args = update_chain.in_.call_args[0]
        assert args[0] == "id", f"Expected filter on 'id', got {args[0]!r}"
        assert set(args[1]) == set(event_ids), (
            f"Expected IDs {event_ids}, got {args[1]}"
        )

    @pytest.mark.asyncio
    async def test_zero_superseded_events_issues_no_update(self):
        """Test 5: 0 events to supersede -> no UPDATE issued at all."""
        svc = self._make_service()

        update_chain = MagicMock()
        update_chain.in_.return_value = update_chain
        update_chain.eq.return_value = update_chain
        update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))

        insert_chain = MagicMock()
        insert_chain.execute = AsyncMock(
            return_value=MagicMock(data=[{"id": "rollback-evt-id"}])
        )

        select_chain = MagicMock()
        select_chain.eq.return_value = select_chain
        select_chain.gt.return_value = select_chain
        select_chain.is_.return_value = select_chain
        select_chain.order.return_value = select_chain
        select_chain.limit.return_value = select_chain
        select_chain.execute = AsyncMock(
            side_effect=[
                MagicMock(data=[{"version": 3}]),  # version query
                MagicMock(data=[]),                  # no events to supersede
            ]
        )

        sessions_update = MagicMock()
        sessions_update.eq.return_value = sessions_update
        sessions_update.execute = AsyncMock(return_value=MagicMock(data=[]))

        def table_router(name: str) -> MagicMock:
            if name == "session_events":
                m = MagicMock()
                m.select.return_value = select_chain
                m.insert.return_value = insert_chain
                m.update.return_value = update_chain
                return m
            if name == "sessions":
                m = MagicMock()
                m.update.return_value = sessions_update
                return m
            m = MagicMock()
            m.select.return_value = m
            m.update.return_value = m
            m.eq.return_value = m
            m.execute = AsyncMock(return_value=MagicMock(data=[]))
            return m

        client = MagicMock()
        client.table = MagicMock(side_effect=table_router)

        mock_target = MagicMock()
        mock_target.events = []

        svc._get_client = AsyncMock(return_value=client)
        svc._execute_with_retry = _exec_with_retry
        svc.get_session_at_version = AsyncMock(return_value=mock_target)
        svc.get_session = AsyncMock(return_value=mock_target)
        svc._ensure_uuid_str = lambda x: str(x)

        await svc.rollback_session(
            app_name="test-app",
            user_id="user-1",
            session_id="sess-1",
            to_version=2,
        )

        assert update_chain.in_.call_count == 0, (
            f"Expected 0 .in_() calls for empty supersede list, got {update_chain.in_.call_count}"
        )


# ---------------------------------------------------------------------------
# Tests for supabase_session_service.fork_session -- bulk insert
# ---------------------------------------------------------------------------

class TestForkSessionBulkInsert:
    """fork_session must copy events via a single bulk INSERT, not N append_event calls."""

    def _make_service(self):
        from app.persistence.supabase_session_service import SupabaseSessionService

        svc = SupabaseSessionService.__new__(SupabaseSessionService)
        svc.sessions_table = "sessions"
        svc.events_table = "session_events"
        svc._cache = MagicMock()
        svc._cache.invalidate_session = AsyncMock()
        svc._supabase_client = None
        return svc

    def _make_mock_event(self, content: str) -> MagicMock:
        evt = MagicMock()
        evt.model_dump.return_value = {"content": content}
        return evt

    @pytest.mark.asyncio
    async def test_four_events_issues_one_bulk_insert(self):
        """Test 3: 4 source events -> single .insert(bulk_rows) call, not 4 appends."""
        svc = self._make_service()

        source_events = [self._make_mock_event(f"msg-{i}") for i in range(4)]

        source_session = MagicMock()
        source_session.events = source_events
        source_session.state = {"last_topic": "testing"}
        source_session.id = "src-sess"

        new_session = MagicMock()
        new_session.id = "new-sess"
        new_session.app_name = "test-app"
        new_session.user_id = "user-1"
        new_session.events = []

        # Track insert arguments
        captured_insert_args: list = []

        insert_chain = MagicMock()
        insert_chain.execute = AsyncMock(return_value=MagicMock(data=[]))

        def capture_insert(rows):
            captured_insert_args.append(rows)
            return insert_chain

        events_table = MagicMock()
        events_table.insert = MagicMock(side_effect=capture_insert)

        sessions_update = MagicMock()
        sessions_update.eq.return_value = sessions_update
        sessions_update.execute = AsyncMock(return_value=MagicMock(data=[]))

        def table_router(name: str) -> MagicMock:
            if name == "session_events":
                return events_table
            if name == "sessions":
                m = MagicMock()
                m.update.return_value = sessions_update
                return m
            m = MagicMock()
            m.select.return_value = m
            m.eq.return_value = m
            m.execute = AsyncMock(return_value=MagicMock(data=[]))
            return m

        client = MagicMock()
        client.table = MagicMock(side_effect=table_router)

        svc._get_client = AsyncMock(return_value=client)
        svc._execute_with_retry = _exec_with_retry
        svc.get_session = AsyncMock(return_value=source_session)
        svc.get_session_at_version = AsyncMock(return_value=source_session)
        svc.create_session = AsyncMock(return_value=new_session)
        svc._ensure_uuid_str = lambda x: str(x)
        svc.append_event = AsyncMock()

        await svc.fork_session(
            app_name="test-app",
            user_id="user-1",
            source_session_id="src-sess",
            new_session_id="new-sess",
        )

        # append_event must not be called at all
        assert svc.append_event.call_count == 0, (
            f"append_event was called {svc.append_event.call_count} times; "
            "expected 0 (bulk insert should be used instead)"
        )

        # events_table.insert must be called exactly once
        assert events_table.insert.call_count == 1, (
            f"Expected 1 bulk .insert() call, got {events_table.insert.call_count}"
        )

        # The single insert must receive a list of 4 dicts
        assert len(captured_insert_args) == 1
        bulk_rows = captured_insert_args[0]
        assert isinstance(bulk_rows, list), (
            f"insert() arg should be a list, got {type(bulk_rows)}"
        )
        assert len(bulk_rows) == 4, (
            f"Expected 4 rows in bulk insert, got {len(bulk_rows)}"
        )

    @pytest.mark.asyncio
    async def test_zero_events_issues_no_insert(self):
        """Test 6: 0 source events -> no INSERT issued at all."""
        svc = self._make_service()

        source_session = MagicMock()
        source_session.events = []
        source_session.state = {}
        source_session.id = "src-sess"

        new_session = MagicMock()
        new_session.id = "new-sess"
        new_session.app_name = "test-app"
        new_session.user_id = "user-1"
        new_session.events = []

        events_table = MagicMock()
        events_table.insert = MagicMock(
            return_value=MagicMock(
                execute=AsyncMock(return_value=MagicMock(data=[]))
            )
        )

        def table_router(name: str) -> MagicMock:
            if name == "session_events":
                return events_table
            m = MagicMock()
            m.select.return_value = m
            m.update.return_value = m
            m.eq.return_value = m
            m.execute = AsyncMock(return_value=MagicMock(data=[]))
            return m

        client = MagicMock()
        client.table = MagicMock(side_effect=table_router)

        svc._get_client = AsyncMock(return_value=client)
        svc._execute_with_retry = _exec_with_retry
        svc.get_session = AsyncMock(return_value=source_session)
        svc.get_session_at_version = AsyncMock(return_value=source_session)
        svc.create_session = AsyncMock(return_value=new_session)
        svc._ensure_uuid_str = lambda x: str(x)
        svc.append_event = AsyncMock()

        await svc.fork_session(
            app_name="test-app",
            user_id="user-1",
            source_session_id="src-sess",
            new_session_id="new-sess",
        )

        assert svc.append_event.call_count == 0, (
            f"append_event should not be called for 0 events, got {svc.append_event.call_count}"
        )
        assert events_table.insert.call_count == 0, (
            f"No bulk insert should happen for 0 events, got {events_table.insert.call_count}"
        )
