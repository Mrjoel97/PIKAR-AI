"""Unit tests for WorkflowEngine dispatch helpers (Phase 111 Plan 03).

Covers Task 03-01 of `111-03-engine-dispatch-PLAN.md`:
- ``WorkflowEngine.requires_graph_executor`` - thin proxy onto
  :func:`app.workflows.graph_executor._template_requires_graph_executor`
  (Discretion #5 Option A: any non-linear kind in graph_nodes triggers
  the graph executor codepath).
- ``WorkflowEngine._load_template_graph`` - fetches graph_nodes +
  graph_edges from ``workflow_template_versions`` for the pinned
  version_id (Phase 110 Plan 02 pinning column on workflow_executions).

Task 03-02 extends this file with tests for ``decide_next_graph_nodes``.

All tests use AsyncMock to stub the supabase async client. No real DB hit.
Mock chain mirrors the pattern from
``tests/unit/workflows/test_template_versions_engine.py`` (Phase 110 Plan 02).
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
# Helpers (mirror Phase 110 Plan 02 test patterns)
# ---------------------------------------------------------------------------


def _make_table_mock(select_data: Any = None) -> tuple[MagicMock, MagicMock]:
    """Return a (client, builder) MagicMock pair where every fluent method
    on the table chain returns the builder, and ``.execute()`` returns a
    response with ``.data = select_data``.
    """
    response = MagicMock()
    response.data = select_data

    builder = MagicMock()
    builder.execute = AsyncMock(return_value=response)
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
        setattr(builder, method, MagicMock(return_value=builder))

    client = MagicMock()
    client.table = MagicMock(return_value=builder)
    return client, builder


# ---------------------------------------------------------------------------
# Task 03-01 Tests: requires_graph_executor + _load_template_graph
# ---------------------------------------------------------------------------


class TestRequiresGraphExecutor:
    """Dispatch predicate tests — pure sync, no DB access."""

    def test_requires_graph_executor_linear_returns_false(self) -> None:
        """Linear graph (trigger/agent-action/output only) -> False."""
        engine = WorkflowEngine()
        graph = [
            {"id": "t1", "kind": "trigger"},
            {"id": "a1", "kind": "agent-action"},
            {"id": "o1", "kind": "output"},
        ]
        assert engine.requires_graph_executor(graph) is False

    def test_requires_graph_executor_with_condition_returns_true(self) -> None:
        """A single ``condition`` node flips dispatch on."""
        engine = WorkflowEngine()
        graph = [
            {"id": "t1", "kind": "trigger"},
            {"id": "c1", "kind": "condition"},
            {"id": "o1", "kind": "output"},
        ]
        assert engine.requires_graph_executor(graph) is True

    def test_requires_graph_executor_with_parallel_returns_true(self) -> None:
        """A ``parallel`` node (Phase 4) still flips dispatch on at the
        helper level — execution will raise NotImplementedError downstream."""
        engine = WorkflowEngine()
        graph = [{"id": "p1", "kind": "parallel"}]
        assert engine.requires_graph_executor(graph) is True

    def test_requires_graph_executor_with_merge_returns_true(self) -> None:
        """Phase 4 ``merge`` kind."""
        engine = WorkflowEngine()
        graph = [{"id": "m1", "kind": "merge"}]
        assert engine.requires_graph_executor(graph) is True

    def test_requires_graph_executor_with_human_approval_returns_true(
        self,
    ) -> None:
        """Phase 4 ``human-approval`` kind."""
        engine = WorkflowEngine()
        graph = [{"id": "h1", "kind": "human-approval"}]
        assert engine.requires_graph_executor(graph) is True

    def test_requires_graph_executor_empty_graph_returns_false(self) -> None:
        """Empty list -> linear fallback (False)."""
        engine = WorkflowEngine()
        assert engine.requires_graph_executor([]) is False


class TestLoadTemplateGraph:
    """Tests for _load_template_graph — async, mocks the supabase client."""

    @pytest.mark.asyncio
    async def test_load_template_graph_fetches_from_versions_table(
        self,
    ) -> None:
        """Helper calls .table("workflow_template_versions") (NOT
        workflow_templates) and filters by id == template_version_id."""
        version_row = {
            "graph_nodes": [{"id": "t1", "kind": "trigger"}],
            "graph_edges": [],
        }
        client, builder = _make_table_mock(select_data=version_row)
        engine = WorkflowEngine()
        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            await engine._load_template_graph("ver-123")

        # Asserts the right table was queried, with the right filter.
        client.table.assert_called_once_with("workflow_template_versions")
        builder.select.assert_called_with("graph_nodes, graph_edges")
        builder.eq.assert_called_with("id", "ver-123")
        builder.single.assert_called_once()
        builder.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_load_template_graph_returns_nodes_and_edges(self) -> None:
        """Returns (graph_nodes_list, graph_edges_list) tuple."""
        nodes = [
            {"id": "t1", "kind": "trigger"},
            {"id": "c1", "kind": "condition"},
        ]
        edges = [{"id": "e1", "source": "t1", "target": "c1"}]
        client, _builder = _make_table_mock(
            select_data={"graph_nodes": nodes, "graph_edges": edges}
        )
        engine = WorkflowEngine()
        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            result_nodes, result_edges = await engine._load_template_graph(
                "ver-123"
            )

        assert result_nodes == nodes
        assert result_edges == edges

    @pytest.mark.asyncio
    async def test_load_template_graph_returns_empty_when_version_not_found(
        self,
    ) -> None:
        """Mock returns no data -> graceful ([], []) for legacy executions
        with NULL current_version_id."""
        client, _builder = _make_table_mock(select_data=None)
        engine = WorkflowEngine()
        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            nodes, edges = await engine._load_template_graph("ver-missing")
        assert nodes == []
        assert edges == []

    @pytest.mark.asyncio
    async def test_load_template_graph_handles_null_graph_fields(self) -> None:
        """Version row exists but graph_nodes/graph_edges are NULL -> ([], [])."""
        client, _builder = _make_table_mock(
            select_data={"graph_nodes": None, "graph_edges": None}
        )
        engine = WorkflowEngine()
        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            nodes, edges = await engine._load_template_graph("ver-with-null")
        assert nodes == []
        assert edges == []

    @pytest.mark.asyncio
    async def test_load_template_graph_returns_empty_for_none_version_id(
        self,
    ) -> None:
        """Passing template_version_id=None (legacy execution) -> ([], [])
        WITHOUT any DB call."""
        client = MagicMock()
        client.table = MagicMock()
        engine = WorkflowEngine()
        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            nodes, edges = await engine._load_template_graph(None)
        assert nodes == []
        assert edges == []
        client.table.assert_not_called()


# ---------------------------------------------------------------------------
# Helper: layered client (for decide_next_graph_nodes tests below)
# ---------------------------------------------------------------------------


def _make_layered_client(
    *,
    version_row: dict[str, Any] | None,
    execution_row: dict[str, Any] | None = None,
    completed_steps: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Build a supabase client mock where ``.table(name)`` returns a builder
    whose ``.execute()`` produces the right rows based on the table name.

    Workflow:
      * ``workflow_executions`` -> execution_row (single row)
      * ``workflow_template_versions`` -> version_row (single row)
      * ``workflow_steps`` -> completed_steps list (multi-row)
    """
    client = MagicMock()
    builders: dict[str, MagicMock] = {}

    def _build_for(table_name: str) -> MagicMock:
        b = MagicMock()
        response = MagicMock()
        response.data = None
        if table_name == "workflow_executions":
            response.data = execution_row
        elif table_name == "workflow_template_versions":
            response.data = version_row
        elif table_name == "workflow_steps":
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
    return client


# ---------------------------------------------------------------------------
# Task 03-02 Tests: decide_next_graph_nodes
# ---------------------------------------------------------------------------


class TestDecideNextGraphNodes:
    """Tests for the engine-level decide_next_graph_nodes method.

    Verify the engine builds the ExecutionContext correctly from
    workflow_steps + workflow_executions rows AND delegates to
    graph_executor.decide_next_nodes.
    """

    @pytest.mark.asyncio
    async def test_decide_next_graph_nodes_linear_returns_empty(self) -> None:
        """Linear template -> [] (caller routes to step_executor)."""
        execution_row = {
            "id": "exec-1",
            "template_version_id": "ver-1",
            "context": {},
        }
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "a1", "kind": "agent-action"},
                {"id": "o1", "kind": "output"},
            ],
            "graph_edges": [],
        }
        client = _make_layered_client(
            version_row=version_row,
            execution_row=execution_row,
            completed_steps=[],
        )
        engine = WorkflowEngine()
        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            result = await engine.decide_next_graph_nodes("exec-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_decide_next_graph_nodes_no_steps_starts_from_trigger(
        self,
    ) -> None:
        """No completed steps -> current_node_id auto-resolves to the
        trigger node; returns trigger's outgoing edges."""
        execution_row = {
            "id": "exec-1",
            "template_version_id": "ver-1",
            "context": {},
        }
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "c1", "kind": "condition", "config": {}},
                {"id": "a1", "kind": "agent-action"},
            ],
            "graph_edges": [
                {"id": "e1", "source": "t1", "target": "a1"},
            ],
        }
        client = _make_layered_client(
            version_row=version_row,
            execution_row=execution_row,
            completed_steps=[],
        )
        engine = WorkflowEngine()
        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            result = await engine.decide_next_graph_nodes("exec-1")
        # Trigger's only outgoing edge points to a1
        assert result == ["a1"]

    @pytest.mark.asyncio
    async def test_decide_next_graph_nodes_condition_true_branch(self) -> None:
        """Condition node evaluates truthy -> routes via 'true' source_handle."""
        execution_row = {
            "id": "exec-1",
            "template_version_id": "ver-1",
            "context": {},
        }
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "a1", "kind": "agent-action"},
                {
                    "id": "c1",
                    "kind": "condition",
                    "config": {
                        "expression": {
                            "==": [
                                {"var": "previous_outcomes.a1.lead_score"},
                                75,
                            ]
                        }
                    },
                },
                {"id": "t-out", "kind": "output"},
                {"id": "f-out", "kind": "output"},
            ],
            "graph_edges": [
                {"id": "e1", "source": "t1", "target": "a1"},
                {"id": "e2", "source": "a1", "target": "c1"},
                {
                    "id": "e3",
                    "source": "c1",
                    "target": "t-out",
                    "source_handle": "true",
                },
                {
                    "id": "e4",
                    "source": "c1",
                    "target": "f-out",
                    "source_handle": "false",
                },
            ],
        }
        completed_steps = [
            {
                "id": "step-a1",
                "status": "completed",
                "completed_at": "2026-05-12T01:00:00Z",
                "output_data": {
                    "lead_score": 75,
                    "_execution_meta": {"graph_node_id": "a1"},
                },
            },
            {
                "id": "step-c1",
                "status": "completed",
                "completed_at": "2026-05-12T01:00:01Z",
                "output_data": {
                    "_execution_meta": {"graph_node_id": "c1"},
                },
            },
        ]
        client = _make_layered_client(
            version_row=version_row,
            execution_row=execution_row,
            completed_steps=completed_steps,
        )
        engine = WorkflowEngine()
        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            result = await engine.decide_next_graph_nodes("exec-1")
        # Condition truthy -> 'true' handle -> t-out
        assert result == ["t-out"]

    @pytest.mark.asyncio
    async def test_decide_next_graph_nodes_condition_false_branch(self) -> None:
        """Condition node evaluates falsy -> routes via 'false' source_handle."""
        execution_row = {
            "id": "exec-1",
            "template_version_id": "ver-1",
            "context": {},
        }
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "a1", "kind": "agent-action"},
                {
                    "id": "c1",
                    "kind": "condition",
                    "config": {
                        "expression": {
                            ">": [
                                {"var": "previous_outcomes.a1.lead_score"},
                                100,
                            ]
                        }
                    },
                },
                {"id": "t-out", "kind": "output"},
                {"id": "f-out", "kind": "output"},
            ],
            "graph_edges": [
                {"id": "e1", "source": "t1", "target": "a1"},
                {"id": "e2", "source": "a1", "target": "c1"},
                {
                    "id": "e3",
                    "source": "c1",
                    "target": "t-out",
                    "source_handle": "true",
                },
                {
                    "id": "e4",
                    "source": "c1",
                    "target": "f-out",
                    "source_handle": "false",
                },
            ],
        }
        completed_steps = [
            {
                "id": "step-a1",
                "status": "completed",
                "completed_at": "2026-05-12T01:00:00Z",
                "output_data": {
                    "lead_score": 25,
                    "_execution_meta": {"graph_node_id": "a1"},
                },
            },
            {
                "id": "step-c1",
                "status": "completed",
                "completed_at": "2026-05-12T01:00:01Z",
                "output_data": {
                    "_execution_meta": {"graph_node_id": "c1"},
                },
            },
        ]
        client = _make_layered_client(
            version_row=version_row,
            execution_row=execution_row,
            completed_steps=completed_steps,
        )
        engine = WorkflowEngine()
        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            result = await engine.decide_next_graph_nodes("exec-1")
        # Condition falsy -> 'false' handle -> f-out
        assert result == ["f-out"]

    @pytest.mark.asyncio
    async def test_decide_next_graph_nodes_missing_template_version_id_returns_empty(
        self,
    ) -> None:
        """Execution with template_version_id=None (legacy pre-Phase-110)
        -> [] (caller delegates to EF)."""
        execution_row = {
            "id": "exec-1",
            "template_version_id": None,
            "context": {},
        }
        client = _make_layered_client(
            version_row=None,
            execution_row=execution_row,
            completed_steps=[],
        )
        engine = WorkflowEngine()
        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            result = await engine.decide_next_graph_nodes("exec-1")
        assert result == []

    @pytest.mark.asyncio
    async def test_decide_next_graph_nodes_user_context_propagated(
        self,
    ) -> None:
        """user_context from workflow_executions.context reaches JSONLogic
        var resolution (ROADMAP criterion 7)."""
        execution_row = {
            "id": "exec-1",
            "template_version_id": "ver-1",
            "context": {"user_var": 42},
        }
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {
                    "id": "c1",
                    "kind": "condition",
                    "config": {
                        "expression": {">=": [{"var": "user_var"}, 40]}
                    },
                },
                {"id": "t-out", "kind": "output"},
                {"id": "f-out", "kind": "output"},
            ],
            "graph_edges": [
                {"id": "e1", "source": "t1", "target": "c1"},
                {
                    "id": "e2",
                    "source": "c1",
                    "target": "t-out",
                    "source_handle": "true",
                },
                {
                    "id": "e3",
                    "source": "c1",
                    "target": "f-out",
                    "source_handle": "false",
                },
            ],
        }
        completed_steps = [
            {
                "id": "step-c1",
                "status": "completed",
                "completed_at": "2026-05-12T01:00:00Z",
                "output_data": {
                    "_execution_meta": {"graph_node_id": "c1"},
                },
            },
        ]
        client = _make_layered_client(
            version_row=version_row,
            execution_row=execution_row,
            completed_steps=completed_steps,
        )
        engine = WorkflowEngine()
        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            result = await engine.decide_next_graph_nodes("exec-1")
        # user_var=42 >= 40 is truthy -> 'true' handle -> t-out
        assert result == ["t-out"]

    @pytest.mark.asyncio
    async def test_decide_next_graph_nodes_previous_outcomes_keyed_by_graph_node_id(
        self,
    ) -> None:
        """Two completed steps with distinct graph_node_id values both
        appear in previous_outcomes — verified by reading both via the
        dotted-path expression."""
        execution_row = {
            "id": "exec-1",
            "template_version_id": "ver-1",
            "context": {},
        }
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                {"id": "a1", "kind": "agent-action"},
                {"id": "a2", "kind": "agent-action"},
                {
                    "id": "c1",
                    "kind": "condition",
                    "config": {
                        "expression": {
                            "and": [
                                {">=": [{"var": "previous_outcomes.a1.score"}, 10]},
                                {">=": [{"var": "previous_outcomes.a2.score"}, 10]},
                            ]
                        }
                    },
                },
                {"id": "t-out", "kind": "output"},
                {"id": "f-out", "kind": "output"},
            ],
            "graph_edges": [
                {
                    "id": "e1",
                    "source": "c1",
                    "target": "t-out",
                    "source_handle": "true",
                },
                {
                    "id": "e2",
                    "source": "c1",
                    "target": "f-out",
                    "source_handle": "false",
                },
            ],
        }
        completed_steps = [
            {
                "id": "step-a1",
                "status": "completed",
                "completed_at": "2026-05-12T01:00:00Z",
                "output_data": {
                    "score": 15,
                    "_execution_meta": {"graph_node_id": "a1"},
                },
            },
            {
                "id": "step-a2",
                "status": "completed",
                "completed_at": "2026-05-12T01:00:01Z",
                "output_data": {
                    "score": 20,
                    "_execution_meta": {"graph_node_id": "a2"},
                },
            },
            {
                "id": "step-c1",
                "status": "completed",
                "completed_at": "2026-05-12T01:00:02Z",
                "output_data": {
                    "_execution_meta": {"graph_node_id": "c1"},
                },
            },
        ]
        client = _make_layered_client(
            version_row=version_row,
            execution_row=execution_row,
            completed_steps=completed_steps,
        )
        engine = WorkflowEngine()
        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            result = await engine.decide_next_graph_nodes("exec-1")
        # Both scores satisfy AND -> truthy -> 'true' handle -> t-out
        assert result == ["t-out"]

    @pytest.mark.asyncio
    async def test_decide_next_graph_nodes_raises_on_malformed_condition(
        self,
    ) -> None:
        """Condition node missing config.expression -> GraphExecutorError
        propagates up out of decide_next_graph_nodes."""
        execution_row = {
            "id": "exec-1",
            "template_version_id": "ver-1",
            "context": {},
        }
        version_row = {
            "graph_nodes": [
                {"id": "t1", "kind": "trigger"},
                # condition with no 'expression' key -> malformed
                {"id": "c1", "kind": "condition", "config": {}},
                {"id": "t-out", "kind": "output"},
                {"id": "f-out", "kind": "output"},
            ],
            "graph_edges": [
                {
                    "id": "e1",
                    "source": "c1",
                    "target": "t-out",
                    "source_handle": "true",
                },
                {
                    "id": "e2",
                    "source": "c1",
                    "target": "f-out",
                    "source_handle": "false",
                },
            ],
        }
        completed_steps = [
            {
                "id": "step-c1",
                "status": "completed",
                "completed_at": "2026-05-12T01:00:00Z",
                "output_data": {
                    "_execution_meta": {"graph_node_id": "c1"},
                },
            },
        ]
        client = _make_layered_client(
            version_row=version_row,
            execution_row=execution_row,
            completed_steps=completed_steps,
        )
        engine = WorkflowEngine()
        with patch.object(
            engine, "_get_client", new=AsyncMock(return_value=client)
        ):
            with pytest.raises(GraphExecutorError):
                await engine.decide_next_graph_nodes("exec-1")
