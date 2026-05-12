"""Unit tests for WorkflowEngine._advance_workflow dispatch wiring + _enqueue_graph_node_step.

Covers Task 03-05 of `111-03-engine-dispatch-PLAN.md` — the LOAD-BEARING
production wire that closes ROADMAP criterion 1:

After this task, ``_advance_workflow`` dispatches on the pinned template's
graph_nodes:
- LINEAR templates -> delegates to ``edge_function_client.execute_workflow``
  unchanged (Phase 110 path).
- GRAPH templates -> calls ``decide_next_graph_nodes`` and inserts the next
  workflow_steps row(s) via ``_enqueue_graph_node_step``. Python owns the
  graph dispatch path; EF is NOT called for graph templates.

``_enqueue_graph_node_step`` is the new helper that maps a graph node id
to a workflow_steps row. For:
- ``agent-action`` nodes: inserts with status='running' (worker picks up).
- ``condition`` nodes: inserts with status='completed' (self-complete).
- ``output`` nodes: inserts with status='completed' AND marks the parent
  execution status='completed' (terminal).
- ``trigger`` nodes: no-op (entry points).
- ``parallel`` / ``merge`` / ``human-approval`` nodes: NotImplementedError
  (Phase 4 work).

All tests use AsyncMock to stub the supabase client + the
``edge_function_client`` import. No real DB hit.
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workflows.engine import WorkflowEngine
from app.workflows.graph_executor import GraphExecutorError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_layered_client(
    *,
    version_row: dict[str, Any] | None = None,
    execution_row: dict[str, Any] | None = None,
    completed_steps: list[dict[str, Any]] | None = None,
    max_step_row: dict[str, Any] | None = None,
) -> MagicMock:
    """Build a supabase client mock layered by table name.

    For each table, the same builder is reused across .table(name) calls
    so test assertions on insert/update calls work consistently.

    Tables supported:
      * workflow_executions -> execution_row (single)
      * workflow_template_versions -> version_row (single)
      * workflow_steps -> completed_steps (list for SELECT;
                         max_step_row for the MAX step_index query)
    """
    client = MagicMock()
    builders: dict[str, MagicMock] = {}

    # Tracker for which "shape" of query is being run on workflow_steps —
    # the dispatcher uses SELECT and the enqueue helper uses INSERT.
    workflow_steps_call_idx: dict[str, int] = {"i": 0}

    def _build_for(table_name: str) -> MagicMock:
        b = MagicMock()
        response = MagicMock()
        response.data = None
        if table_name == "workflow_executions":
            response.data = execution_row
        elif table_name == "workflow_template_versions":
            response.data = version_row
        elif table_name == "workflow_steps":
            # Default response for any chained call. Specific call sites
            # can be overridden in tests by re-setting builder.execute.
            response.data = completed_steps or []
        b.execute = AsyncMock(return_value=response)
        for method in (
            "select",
            "eq",
            "neq",
            "is_",
            "in_",
            "order",
            "limit",
            "single",
            "maybe_single",
            "insert",
            "update",
            "upsert",
            "delete",
        ):
            setattr(b, method, MagicMock(return_value=b))
        return b

    def _table(name: str) -> MagicMock:
        if name not in builders:
            builders[name] = _build_for(name)
        return builders[name]

    client.table = MagicMock(side_effect=_table)
    client._builders = builders  # type: ignore[attr-defined]
    client._workflow_steps_idx = workflow_steps_call_idx  # type: ignore[attr-defined]
    return client


def _exec_row(template_version_id: str | None) -> dict[str, Any]:
    return {
        "id": "exec-1",
        "template_version_id": template_version_id,
        "context": {},
        "status": "running",
        "current_step_index": None,
    }


# ---------------------------------------------------------------------------
# Task 03-05 Tests: _advance_workflow dispatch + _enqueue_graph_node_step
# ---------------------------------------------------------------------------


class TestAdvanceWorkflowDispatch:
    """The wired ``_advance_workflow`` decides graph vs. linear dispatch."""

    @pytest.mark.asyncio
    async def test_advance_workflow_linear_template_delegates_to_edge_function(
        self,
    ) -> None:
        """Linear template -> EF call fires exactly once; _enqueue is NOT called."""
        execution_row = _exec_row("ver-1")
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "a1", "kind": "agent-action"},
                {"id": "o1", "kind": "output"},
            ],
            "graph_edges": [],
        }
        client = _make_layered_client(
            version_row=version_row, execution_row=execution_row
        )
        engine = WorkflowEngine()

        with (
            patch.object(
                engine, "_get_client", new=AsyncMock(return_value=client)
            ),
            patch(
                "app.workflows.engine.edge_function_client"
            ) as mock_ef,
            patch.object(
                engine,
                "_enqueue_graph_node_step",
                new=AsyncMock(return_value={}),
            ) as mock_enqueue,
        ):
            mock_ef.execute_workflow = AsyncMock(return_value={"ok": True})
            await engine._advance_workflow(execution_row, [])
            mock_ef.execute_workflow.assert_awaited_once_with(
                "exec-1", action="advance"
            )
            mock_enqueue.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_advance_workflow_legacy_null_version_delegates_to_edge_function(
        self,
    ) -> None:
        """Legacy execution (template_version_id=None) -> EF call fires,
        dispatch NOT invoked."""
        execution_row = _exec_row(None)
        client = _make_layered_client(execution_row=execution_row)
        engine = WorkflowEngine()

        with (
            patch.object(
                engine, "_get_client", new=AsyncMock(return_value=client)
            ),
            patch(
                "app.workflows.engine.edge_function_client"
            ) as mock_ef,
            patch.object(
                engine,
                "_enqueue_graph_node_step",
                new=AsyncMock(return_value={}),
            ) as mock_enqueue,
        ):
            mock_ef.execute_workflow = AsyncMock(return_value={"ok": True})
            await engine._advance_workflow(execution_row, [])
            mock_ef.execute_workflow.assert_awaited_once_with(
                "exec-1", action="advance"
            )
            mock_enqueue.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_advance_workflow_graph_template_calls_decide_next_graph_nodes(
        self,
    ) -> None:
        """Graph template -> decide_next_graph_nodes called; EF NOT called."""
        execution_row = _exec_row("ver-1")
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "c1", "kind": "condition"},
                {"id": "o1", "kind": "output"},
            ],
            "graph_edges": [],
        }
        client = _make_layered_client(
            version_row=version_row, execution_row=execution_row
        )
        engine = WorkflowEngine()

        with (
            patch.object(
                engine, "_get_client", new=AsyncMock(return_value=client)
            ),
            patch(
                "app.workflows.engine.edge_function_client"
            ) as mock_ef,
            patch.object(
                engine,
                "decide_next_graph_nodes",
                new=AsyncMock(return_value=[]),
            ) as mock_dispatch,
            patch.object(
                engine,
                "_enqueue_graph_node_step",
                new=AsyncMock(return_value={}),
            ),
        ):
            mock_ef.execute_workflow = AsyncMock(return_value={"ok": True})
            await engine._advance_workflow(execution_row, [])
            mock_dispatch.assert_awaited_with("exec-1")
            mock_ef.execute_workflow.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_advance_workflow_graph_template_enqueues_next_nodes(
        self,
    ) -> None:
        """When decide_next_graph_nodes returns a node id, _enqueue is called for it."""
        execution_row = _exec_row("ver-1")
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {
                    "id": "next-node-uuid",
                    "kind": "agent-action",
                    "config": {"tool_name": "do_thing"},
                },
                {"id": "c1", "kind": "condition"},
            ],
            "graph_edges": [],
        }
        client = _make_layered_client(
            version_row=version_row, execution_row=execution_row
        )
        engine = WorkflowEngine()

        with (
            patch.object(
                engine, "_get_client", new=AsyncMock(return_value=client)
            ),
            patch("app.workflows.engine.edge_function_client") as mock_ef,
            patch.object(
                engine,
                "decide_next_graph_nodes",
                new=AsyncMock(return_value=["next-node-uuid"]),
            ),
            patch.object(
                engine,
                "_enqueue_graph_node_step",
                new=AsyncMock(return_value={}),
            ) as mock_enqueue,
        ):
            mock_ef.execute_workflow = AsyncMock(return_value={"ok": True})
            await engine._advance_workflow(execution_row, [])
            mock_enqueue.assert_any_await("exec-1", "next-node-uuid")

    @pytest.mark.asyncio
    async def test_advance_workflow_graph_template_enqueues_multiple_when_dispatcher_returns_multiple(
        self,
    ) -> None:
        """Multiple next nodes -> _enqueue called for each (Phase 4 parallel forward-compat)."""
        execution_row = _exec_row("ver-1")
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "c1", "kind": "condition"},
                {"id": "n1", "kind": "agent-action", "config": {"tool_name": "t"}},
                {"id": "n2", "kind": "agent-action", "config": {"tool_name": "t"}},
            ],
            "graph_edges": [],
        }
        client = _make_layered_client(
            version_row=version_row, execution_row=execution_row
        )
        engine = WorkflowEngine()

        with (
            patch.object(
                engine, "_get_client", new=AsyncMock(return_value=client)
            ),
            patch("app.workflows.engine.edge_function_client"),
            patch.object(
                engine,
                "decide_next_graph_nodes",
                new=AsyncMock(return_value=["n1", "n2"]),
            ),
            patch.object(
                engine,
                "_enqueue_graph_node_step",
                new=AsyncMock(return_value={}),
            ) as mock_enqueue,
        ):
            await engine._advance_workflow(execution_row, [])
            assert mock_enqueue.await_count >= 2
            awaited_args = [c.args for c in mock_enqueue.await_args_list]
            assert ("exec-1", "n1") in awaited_args
            assert ("exec-1", "n2") in awaited_args

    @pytest.mark.asyncio
    async def test_advance_workflow_graph_template_handles_dispatcher_returning_empty(
        self,
    ) -> None:
        """Dispatcher returns [] -> no _enqueue calls; no EF call; returns
        a status dict (no exception)."""
        execution_row = _exec_row("ver-1")
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "c1", "kind": "condition"},
            ],
            "graph_edges": [],
        }
        client = _make_layered_client(
            version_row=version_row, execution_row=execution_row
        )
        engine = WorkflowEngine()

        with (
            patch.object(
                engine, "_get_client", new=AsyncMock(return_value=client)
            ),
            patch("app.workflows.engine.edge_function_client") as mock_ef,
            patch.object(
                engine,
                "decide_next_graph_nodes",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                engine,
                "_enqueue_graph_node_step",
                new=AsyncMock(return_value={}),
            ) as mock_enqueue,
        ):
            mock_ef.execute_workflow = AsyncMock(return_value={"ok": True})
            result = await engine._advance_workflow(execution_row, [])
            mock_enqueue.assert_not_awaited()
            mock_ef.execute_workflow.assert_not_awaited()
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_advance_workflow_propagates_graph_executor_error(
        self,
    ) -> None:
        """decide_next_graph_nodes raises GraphExecutorError -> _advance_workflow
        marks the execution failed and returns an error dict."""
        execution_row = _exec_row("ver-1")
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "c1", "kind": "condition"},
            ],
            "graph_edges": [],
        }
        client = _make_layered_client(
            version_row=version_row, execution_row=execution_row
        )
        engine = WorkflowEngine()

        with (
            patch.object(
                engine, "_get_client", new=AsyncMock(return_value=client)
            ),
            patch("app.workflows.engine.edge_function_client") as mock_ef,
            patch.object(
                engine,
                "decide_next_graph_nodes",
                new=AsyncMock(side_effect=GraphExecutorError("bad expression")),
            ),
            patch.object(
                engine,
                "_enqueue_graph_node_step",
                new=AsyncMock(return_value={}),
            ),
        ):
            mock_ef.execute_workflow = AsyncMock()
            result = await engine._advance_workflow(execution_row, [])
            assert isinstance(result, dict)
            assert "error" in result
            assert result.get("error_code") == "graph_executor_error"


# ---------------------------------------------------------------------------
# _enqueue_graph_node_step tests
# ---------------------------------------------------------------------------


class TestEnqueueGraphNodeStep:
    """The new helper that maps a graph node id to a workflow_steps row."""

    @pytest.mark.asyncio
    async def test_enqueue_graph_node_step_inserts_workflow_steps_row(
        self,
    ) -> None:
        """agent-action node -> INSERT a workflow_steps row with
        status='running', step_index set, output_data._execution_meta.graph_node_id,
        and step_definition carrying tool_name + graph_node_id."""
        execution_row = _exec_row("ver-1")
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {
                    "id": "node-uuid-123",
                    "kind": "agent-action",
                    "label": "Score lead",
                    "config": {"tool_name": "score_lead"},
                },
            ],
            "graph_edges": [],
        }
        client = _make_layered_client(
            version_row=version_row, execution_row=execution_row
        )
        # Make the workflow_steps SELECT return [] (no existing rows -> idx=0).
        # The insert will be invoked on the same builder; capture its arg.
        engine = WorkflowEngine()

        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            await engine._enqueue_graph_node_step("exec-1", "node-uuid-123")

        ws_builder = client._builders["workflow_steps"]
        # Insert was called at least once
        assert ws_builder.insert.call_count >= 1
        inserted = ws_builder.insert.call_args.args[0]
        assert inserted["status"] == "running"
        assert inserted["execution_id"] == "exec-1"
        assert (
            inserted["output_data"]["_execution_meta"]["graph_node_id"]
            == "node-uuid-123"
        )
        # step_definition carries tool + graph_node_id
        sd = inserted["step_definition"]
        assert sd["graph_node_id"] == "node-uuid-123"
        assert sd["tool"] == "score_lead"

    @pytest.mark.asyncio
    async def test_enqueue_graph_node_step_handles_condition_kind(
        self,
    ) -> None:
        """condition node -> INSERT with status='completed' (immediate self-complete)."""
        execution_row = _exec_row("ver-1")
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {
                    "id": "c1",
                    "kind": "condition",
                    "label": "Hot?",
                    "config": {"expression": {"==": [1, 1]}},
                },
            ],
            "graph_edges": [],
        }
        client = _make_layered_client(
            version_row=version_row, execution_row=execution_row
        )
        engine = WorkflowEngine()

        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            await engine._enqueue_graph_node_step("exec-1", "c1")

        ws_builder = client._builders["workflow_steps"]
        inserted = ws_builder.insert.call_args.args[0]
        assert inserted["status"] == "completed"
        assert inserted["output_data"]["_execution_meta"]["graph_node_id"] == "c1"
        assert inserted["output_data"]["_execution_meta"]["kind"] == "condition"

    @pytest.mark.asyncio
    async def test_enqueue_graph_node_step_handles_output_kind(self) -> None:
        """output node -> INSERT with status='completed' AND mark parent
        execution status='completed' (terminal node)."""
        execution_row = _exec_row("ver-1")
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "o1", "kind": "output", "label": "Done"},
            ],
            "graph_edges": [],
        }
        client = _make_layered_client(
            version_row=version_row, execution_row=execution_row
        )
        engine = WorkflowEngine()

        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            await engine._enqueue_graph_node_step("exec-1", "o1")

        ws_builder = client._builders["workflow_steps"]
        inserted = ws_builder.insert.call_args.args[0]
        assert inserted["status"] == "completed"
        # The execution should be updated to status='completed' (terminal)
        exec_builder = client._builders["workflow_executions"]
        update_calls = exec_builder.update.call_args_list
        # Last update payload should mark execution complete
        assert any(
            call.args[0].get("status") == "completed" for call in update_calls
        )

    @pytest.mark.asyncio
    async def test_enqueue_graph_node_step_raises_for_parallel_kind(
        self,
    ) -> None:
        """parallel / merge / human-approval -> NotImplementedError with Phase 4 message."""
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "p1", "kind": "parallel"},
                {"id": "m1", "kind": "merge"},
                {"id": "h1", "kind": "human-approval"},
            ],
            "graph_edges": [],
        }
        execution_row = _exec_row("ver-1")
        client = _make_layered_client(
            version_row=version_row, execution_row=execution_row
        )
        engine = WorkflowEngine()

        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            for node_id in ("p1", "m1", "h1"):
                with pytest.raises(NotImplementedError, match=r"Phase 4"):
                    await engine._enqueue_graph_node_step("exec-1", node_id)


# ---------------------------------------------------------------------------
# Loop / chaining tests for _advance_workflow
# ---------------------------------------------------------------------------


class TestAdvanceWorkflowLoop:
    """The graph dispatch loop runs internally until next is an agent-action
    OR the dispatcher returns empty OR max_iterations is exceeded."""

    @pytest.mark.asyncio
    async def test_advance_workflow_loops_until_agent_action_or_terminal(
        self,
    ) -> None:
        """Chain: a1 done -> next is c1 -> c1 enqueued -> next is o1 -> o1
        enqueued -> dispatcher returns [] -> loop exits. _enqueue called
        for BOTH c1 and o1 in a single _advance_workflow invocation."""
        execution_row = _exec_row("ver-1")
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "a1", "kind": "agent-action", "config": {"tool_name": "t"}},
                {"id": "c1", "kind": "condition", "config": {"expression": {"==": [1, 1]}}},
                {"id": "o1", "kind": "output"},
            ],
            "graph_edges": [],
        }
        client = _make_layered_client(
            version_row=version_row, execution_row=execution_row
        )
        engine = WorkflowEngine()

        # Sequence the dispatcher: first call -> [c1], second call -> [o1],
        # third call -> []
        dispatch_call_count = {"i": 0}

        async def fake_dispatch(_exec_id: str) -> list[str]:
            dispatch_call_count["i"] += 1
            if dispatch_call_count["i"] == 1:
                return ["c1"]
            if dispatch_call_count["i"] == 2:
                return ["o1"]
            return []

        with (
            patch.object(
                engine, "_get_client", new=AsyncMock(return_value=client)
            ),
            patch("app.workflows.engine.edge_function_client"),
            patch.object(
                engine,
                "decide_next_graph_nodes",
                new=AsyncMock(side_effect=fake_dispatch),
            ),
            patch.object(
                engine,
                "_enqueue_graph_node_step",
                new=AsyncMock(return_value={}),
            ) as mock_enqueue,
        ):
            await engine._advance_workflow(execution_row, [])
            awaited_args = [c.args for c in mock_enqueue.await_args_list]
            assert ("exec-1", "c1") in awaited_args
            assert ("exec-1", "o1") in awaited_args

    @pytest.mark.asyncio
    async def test_advance_workflow_stops_when_next_is_agent_action(
        self,
    ) -> None:
        """If next is an agent-action -> _enqueue called once and the loop
        terminates (worker takes over via get_runnable_steps poll)."""
        execution_row = _exec_row("ver-1")
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "a1", "kind": "agent-action", "config": {"tool_name": "t"}},
                {"id": "a2", "kind": "agent-action", "config": {"tool_name": "t"}},
            ],
            "graph_edges": [],
        }
        client = _make_layered_client(
            version_row=version_row, execution_row=execution_row
        )
        engine = WorkflowEngine()

        dispatch_call_count = {"i": 0}

        async def fake_dispatch(_exec_id: str) -> list[str]:
            dispatch_call_count["i"] += 1
            return ["a2"] if dispatch_call_count["i"] == 1 else []

        with (
            patch.object(
                engine, "_get_client", new=AsyncMock(return_value=client)
            ),
            patch("app.workflows.engine.edge_function_client"),
            patch.object(
                engine,
                "decide_next_graph_nodes",
                new=AsyncMock(side_effect=fake_dispatch),
            ),
            patch.object(
                engine,
                "_enqueue_graph_node_step",
                new=AsyncMock(return_value={}),
            ) as mock_enqueue,
        ):
            await engine._advance_workflow(execution_row, [])
            # After enqueuing a2 (agent-action), the loop should stop:
            # dispatcher called exactly ONCE.
            assert dispatch_call_count["i"] == 1
            mock_enqueue.assert_awaited_once_with("exec-1", "a2")

    @pytest.mark.asyncio
    async def test_advance_workflow_max_iterations_safety(self) -> None:
        """A dispatcher that perpetually returns a condition node should
        eventually be bounded by max_iterations and return an error."""
        execution_row = _exec_row("ver-1")
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {
                    "id": "c1",
                    "kind": "condition",
                    "config": {"expression": {"==": [1, 1]}},
                },
            ],
            "graph_edges": [],
        }
        client = _make_layered_client(
            version_row=version_row, execution_row=execution_row
        )
        engine = WorkflowEngine()

        with (
            patch.object(
                engine, "_get_client", new=AsyncMock(return_value=client)
            ),
            patch("app.workflows.engine.edge_function_client"),
            patch.object(
                engine,
                "decide_next_graph_nodes",
                new=AsyncMock(return_value=["c1"]),
            ),
            patch.object(
                engine,
                "_enqueue_graph_node_step",
                new=AsyncMock(return_value={}),
            ),
        ):
            result = await engine._advance_workflow(execution_row, [])
            # Loop bound exceeded -> result MUST be an error dict
            assert isinstance(result, dict)
            assert "error" in result
            assert "loop" in result.get("error", "").lower() or result.get(
                "error_code"
            ) in (
                "graph_executor_loop_exceeded",
                "graph_executor_error",
            )
