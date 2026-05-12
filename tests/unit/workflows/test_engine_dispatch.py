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
