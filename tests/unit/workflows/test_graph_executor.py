"""Tests for app/workflows/graph_executor.py (Phase 111-01).

Pure-functional graph executor. No DB, no async, no IO. Two public surfaces:

  - ``_template_requires_graph_executor(graph_nodes) -> bool``: dispatch
    helper (Discretion #5 Option A). Returns True iff any node has kind in
    ``NON_LINEAR_KINDS = {'condition', 'parallel', 'merge', 'human-approval'}``.

  - ``decide_next_nodes(graph_nodes, graph_edges, *, current_node_id,
    execution_context, completed_node_ids) -> list[str]``: returns next-node
    ids given current graph state. For linear kinds, returns all outgoing
    edge targets. For condition kinds, evaluates the JSONLogic expression
    in node.config and routes to the 'true' or 'false' source_handle edge.
    For parallel/merge/human-approval, raises NotImplementedError (Phase 4).

Coverage:
  - Dispatch helper: 5 tests (linear, condition, parallel, human-approval, empty)
  - decide_next_nodes linear: 1 test (trigger → agent-action → output chain)
  - decide_next_nodes condition: 5 tests (true, false, missing-var-is-false,
    previous_outcomes resolution via dotted-path, handle-mismatch raises)
  - decide_next_nodes errors: 4 tests (missing expression, malformed JSONLogic,
    parallel kind raises NotImplementedError, unknown kind raises)

ROADMAP criteria addressed:
  - criterion 1 (condition routing) — partial, completed end-to-end by Plan 03
  - criterion 2 (dispatch) — fully shipped here
  - criterion 7 (ExecutionContext shape) — locked here via TypedDict
  - criterion 11 (defense-in-depth) — raises on missing/invalid configurations
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

import pytest

from app.workflows.graph_executor import (
    NON_LINEAR_KINDS,
    ExecutionContext,
    GraphExecutorError,
    _template_requires_graph_executor,
    decide_next_nodes,
)

# ---------- Test fixtures: small synthetic graphs ---------------------------


def _empty_context() -> ExecutionContext:
    """Build an empty ExecutionContext (all three keys present, all empty)."""
    return {"previous_outcomes": {}, "current_step": {}, "user_context": {}}


def _linear_graph() -> tuple[list[dict], list[dict]]:
    """trigger(t1) → agent-action(a1) → output(o1)."""
    nodes = [
        {"id": "t1", "kind": "trigger", "label": "Trigger", "config": {}},
        {
            "id": "a1",
            "kind": "agent-action",
            "label": "Action",
            "config": {"tool_name": "noop"},
        },
        {"id": "o1", "kind": "output", "label": "Output", "config": {}},
    ]
    edges = [
        {"id": "e1", "source": "t1", "target": "a1", "source_handle": None},
        {"id": "e2", "source": "a1", "target": "o1", "source_handle": None},
    ]
    return nodes, edges


def _condition_graph(
    expression: dict | None,
) -> tuple[list[dict], list[dict]]:
    """trigger → condition(c1, expr) → true→t_out, false→f_out."""
    config = {"expression": expression} if expression is not None else {}
    nodes = [
        {"id": "trig", "kind": "trigger", "label": "T", "config": {}},
        {"id": "c1", "kind": "condition", "label": "C", "config": config},
        {"id": "t_out", "kind": "output", "label": "True", "config": {}},
        {"id": "f_out", "kind": "output", "label": "False", "config": {}},
    ]
    edges = [
        {"id": "e_in", "source": "trig", "target": "c1", "source_handle": None},
        {"id": "e_t", "source": "c1", "target": "t_out", "source_handle": "true"},
        {"id": "e_f", "source": "c1", "target": "f_out", "source_handle": "false"},
    ]
    return nodes, edges


# ============================================================================
# _template_requires_graph_executor — dispatch helper (Discretion #5 Option A)
# ============================================================================


def test_dispatch_linear_only_returns_false() -> None:
    """Trigger → agent-action → output is linear; no dispatch needed."""
    nodes, _ = _linear_graph()
    assert _template_requires_graph_executor(nodes) is False


def test_dispatch_with_condition_returns_true() -> None:
    """Any condition node anywhere flips dispatch on."""
    nodes, _ = _condition_graph({"==": [1, 1]})
    assert _template_requires_graph_executor(nodes) is True


def test_dispatch_with_parallel_returns_true() -> None:
    """Parallel kind also triggers graph_executor dispatch."""
    nodes = [
        {"id": "t", "kind": "trigger", "label": "T", "config": {}},
        {"id": "p", "kind": "parallel", "label": "P", "config": {}},
        {"id": "o", "kind": "output", "label": "O", "config": {}},
    ]
    assert _template_requires_graph_executor(nodes) is True


def test_dispatch_with_human_approval_returns_true() -> None:
    """Human-approval kind triggers dispatch (Phase 4 will execute it)."""
    nodes = [
        {"id": "t", "kind": "trigger", "label": "T", "config": {}},
        {
            "id": "h",
            "kind": "human-approval",
            "label": "H",
            "config": {},
        },
        {"id": "o", "kind": "output", "label": "O", "config": {}},
    ]
    assert _template_requires_graph_executor(nodes) is True


def test_dispatch_empty_graph_returns_false() -> None:
    """Empty graph defaults to linear dispatch."""
    assert _template_requires_graph_executor([]) is False


def test_non_linear_kinds_covers_all_four() -> None:
    """The exported frozenset MUST list exactly condition/parallel/merge/human-approval."""
    assert NON_LINEAR_KINDS == frozenset(
        {"condition", "parallel", "merge", "human-approval"}
    )


# ============================================================================
# decide_next_nodes — linear kinds
# ============================================================================


def test_decide_linear_trigger_returns_outgoing() -> None:
    """Trigger node with 1 outgoing edge returns the single target."""
    nodes, edges = _linear_graph()
    result = decide_next_nodes(
        nodes,
        edges,
        current_node_id="t1",
        execution_context=_empty_context(),
        completed_node_ids=set(),
    )
    assert result == ["a1"]


def test_decide_linear_output_no_outgoing() -> None:
    """Output node with zero outgoing edges returns []."""
    nodes, edges = _linear_graph()
    result = decide_next_nodes(
        nodes,
        edges,
        current_node_id="o1",
        execution_context=_empty_context(),
        completed_node_ids={"t1", "a1"},
    )
    assert result == []


# ============================================================================
# decide_next_nodes — condition kind, JSONLogic-driven routing
# ============================================================================


def test_decide_condition_true_branch() -> None:
    """Score > 50 with score=75 routes to 'true' edge target."""
    nodes, edges = _condition_graph({">": [{"var": "score"}, 50]})
    ctx: ExecutionContext = {
        "previous_outcomes": {},
        "current_step": {},
        "user_context": {"score": 75},
    }
    result = decide_next_nodes(
        nodes,
        edges,
        current_node_id="c1",
        execution_context=ctx,
        completed_node_ids={"trig"},
    )
    assert result == ["t_out"]


def test_decide_condition_false_branch() -> None:
    """Score > 50 with score=25 routes to 'false' edge target."""
    nodes, edges = _condition_graph({">": [{"var": "score"}, 50]})
    ctx: ExecutionContext = {
        "previous_outcomes": {},
        "current_step": {},
        "user_context": {"score": 25},
    }
    result = decide_next_nodes(
        nodes,
        edges,
        current_node_id="c1",
        execution_context=ctx,
        completed_node_ids={"trig"},
    )
    assert result == ["f_out"]


def test_decide_condition_missing_var_is_false_branch() -> None:
    """Missing var → falsy → 'false' branch (no exception)."""
    nodes, edges = _condition_graph({">": [{"var": "absent"}, 0]})
    result = decide_next_nodes(
        nodes,
        edges,
        current_node_id="c1",
        execution_context=_empty_context(),
        completed_node_ids={"trig"},
    )
    assert result == ["f_out"]


def test_decide_condition_with_previous_outcomes_dotted_path() -> None:
    """JSONLogic's dotted-path var resolves into previous_outcomes."""
    nodes, edges = _condition_graph(
        {">": [{"var": "previous_outcomes.upstream.lead_score"}, 50]}
    )
    ctx: ExecutionContext = {
        "previous_outcomes": {"upstream": {"lead_score": 90}},
        "current_step": {},
        "user_context": {},
    }
    result = decide_next_nodes(
        nodes,
        edges,
        current_node_id="c1",
        execution_context=ctx,
        completed_node_ids={"trig", "upstream"},
    )
    assert result == ["t_out"]


# ============================================================================
# decide_next_nodes — defense-in-depth error paths (ROADMAP criterion 11)
# ============================================================================


def test_decide_condition_missing_expression_raises() -> None:
    """Condition node with empty config raises GraphExecutorError (node_id in msg)."""
    nodes, edges = _condition_graph(expression=None)
    with pytest.raises(GraphExecutorError, match="c1"):
        decide_next_nodes(
            nodes,
            edges,
            current_node_id="c1",
            execution_context=_empty_context(),
            completed_node_ids={"trig"},
        )


def test_decide_condition_malformed_jsonlogic_raises() -> None:
    """An unknown JSONLogic operator surfaces as GraphExecutorError."""
    nodes, edges = _condition_graph({"INVALID_OP": [1, 2]})
    with pytest.raises(GraphExecutorError):
        decide_next_nodes(
            nodes,
            edges,
            current_node_id="c1",
            execution_context=_empty_context(),
            completed_node_ids={"trig"},
        )


def test_decide_condition_handle_mismatch_raises() -> None:
    """If a condition's outgoing edges don't carry 'true'/'false' handles,
    decide_next_nodes raises GraphExecutorError (defense-in-depth: Plan 02
    rule 4 validation catches this at save time, but the engine must not
    silently no-op at runtime).
    """
    nodes = [
        {"id": "trig", "kind": "trigger", "label": "T", "config": {}},
        {
            "id": "c1",
            "kind": "condition",
            "label": "C",
            "config": {"expression": {"==": [1, 1]}},
        },
        {"id": "out_left", "kind": "output", "label": "L", "config": {}},
        {"id": "out_right", "kind": "output", "label": "R", "config": {}},
    ]
    edges = [
        {"id": "e_in", "source": "trig", "target": "c1", "source_handle": None},
        {
            "id": "e_l",
            "source": "c1",
            "target": "out_left",
            "source_handle": "left",
        },
        {
            "id": "e_r",
            "source": "c1",
            "target": "out_right",
            "source_handle": "right",
        },
    ]
    with pytest.raises(GraphExecutorError):
        decide_next_nodes(
            nodes,
            edges,
            current_node_id="c1",
            execution_context=_empty_context(),
            completed_node_ids={"trig"},
        )


def test_decide_parallel_raises_not_implemented() -> None:
    """Phase 4 work — parallel must raise NotImplementedError, not silently route."""
    nodes = [
        {"id": "t", "kind": "trigger", "label": "T", "config": {}},
        {"id": "p", "kind": "parallel", "label": "P", "config": {}},
    ]
    edges = [
        {"id": "e", "source": "t", "target": "p", "source_handle": None},
    ]
    with pytest.raises(NotImplementedError, match="Phase 4"):
        decide_next_nodes(
            nodes,
            edges,
            current_node_id="p",
            execution_context=_empty_context(),
            completed_node_ids={"t"},
        )


def test_decide_unknown_kind_raises() -> None:
    """Unknown node kind (not in the 7 NodeKind variants) raises GraphExecutorError."""
    nodes = [
        {"id": "trig", "kind": "trigger", "label": "T", "config": {}},
        {"id": "x", "kind": "custom", "label": "X", "config": {}},
    ]
    edges = [
        {"id": "e", "source": "trig", "target": "x", "source_handle": None},
    ]
    with pytest.raises(GraphExecutorError, match="Unknown node kind"):
        decide_next_nodes(
            nodes,
            edges,
            current_node_id="x",
            execution_context=_empty_context(),
            completed_node_ids={"trig"},
        )


def test_decide_current_node_not_found_raises() -> None:
    """If current_node_id doesn't exist in graph_nodes, raise GraphExecutorError.

    Defense-in-depth — Plan 03's engine dispatch shouldn't ever call us with
    a phantom node_id, but if it does the failure must be loud, not silent.
    """
    nodes, edges = _linear_graph()
    with pytest.raises(GraphExecutorError, match="phantom"):
        decide_next_nodes(
            nodes,
            edges,
            current_node_id="phantom",
            execution_context=_empty_context(),
            completed_node_ids=set(),
        )
