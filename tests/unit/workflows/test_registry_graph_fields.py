"""Tests for the graph-projection Pydantic models on WorkflowTemplateResponse.

Phase 109 (Spec B Phase 1) adds three optional fields to the workflow template
API response — `graph_nodes`, `graph_edges`, `graph_layout` — backed by the
sub-models `GraphNode`, `GraphEdge`, `NodePosition`. These tests pin down:

- The defaults are None on a freshly-constructed WorkflowTemplateResponse
- GraphNode rejects an invalid `kind` value (Pydantic Literal enforcement)
- NodePosition requires int x/y (Pydantic int coercion / rejection)
- GraphEdge.source_handle / label default to None
- graph_layout is keyed by string node id

NOTE: The plan's `files_modified` referenced `app/workflows/registry.py`, but
the Pydantic response model actually lives in `app/routers/workflows.py`.
The four sub-models (NodePosition, NodeKind, GraphNode, GraphEdge) and the
widened WorkflowTemplateResponse all live there. See plan 109-02 SUMMARY for
the Rule 3 deviation note.
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.routers.workflows import (
    GraphEdge,
    GraphNode,
    NodePosition,
    WorkflowTemplateResponse,
)

# ---------- WorkflowTemplateResponse ----------------------------------------


def test_workflow_template_response_accepts_graph_nodes():
    """Round-trip a populated graph through the response model."""
    nodes = [
        GraphNode(id="trigger", kind="trigger", label="Start"),
        GraphNode(
            id="step-0",
            kind="agent-action",
            label="Research",
            config={"tool": "deep_research"},
        ),
        GraphNode(id="output", kind="output", label="End"),
    ]
    edges = [
        GraphEdge(id="e0", source="trigger", target="step-0"),
        GraphEdge(id="e1", source="step-0", target="output"),
    ]
    layout = {
        "trigger": NodePosition(x=0, y=0),
        "step-0": NodePosition(x=200, y=0),
        "output": NodePosition(x=400, y=0),
    }

    template = WorkflowTemplateResponse(
        id="abc",
        name="Test",
        description="desc",
        category="custom",
        graph_nodes=nodes,
        graph_edges=edges,
        graph_layout=layout,
    )

    assert template.graph_nodes is not None
    assert len(template.graph_nodes) == 3
    assert template.graph_nodes[1].kind == "agent-action"
    assert template.graph_edges is not None and len(template.graph_edges) == 2
    assert template.graph_layout is not None
    assert template.graph_layout["step-0"].x == 200


def test_workflow_template_response_defaults_graph_fields_to_none():
    """Existing callers that don't pass graph fields get None back."""
    template = WorkflowTemplateResponse(
        id="abc",
        name="Test",
        description="desc",
        category="custom",
    )
    assert template.graph_nodes is None
    assert template.graph_edges is None
    assert template.graph_layout is None


def test_workflow_template_response_round_trips_through_dict():
    """model_dump preserves graph fields when they are populated."""
    template = WorkflowTemplateResponse(
        id="abc",
        name="Test",
        description="desc",
        category="custom",
        graph_nodes=[GraphNode(id="trigger", kind="trigger", label="Start")],
        graph_edges=[],
        graph_layout={"trigger": NodePosition(x=0, y=0)},
    )
    dumped = template.model_dump()
    assert dumped["graph_nodes"] == [
        {"id": "trigger", "kind": "trigger", "label": "Start", "config": None}
    ]
    assert dumped["graph_edges"] == []
    assert dumped["graph_layout"] == {"trigger": {"x": 0, "y": 0}}


def test_workflow_template_response_accepts_raw_dict_for_graph_nodes():
    """JSONB rows from Supabase come back as plain dicts; Pydantic coerces."""
    template = WorkflowTemplateResponse.model_validate(
        {
            "id": "abc",
            "name": "Test",
            "description": "desc",
            "category": "custom",
            "graph_nodes": [{"id": "trigger", "kind": "trigger", "label": "Start"}],
            "graph_edges": [{"id": "e0", "source": "trigger", "target": "output"}],
            "graph_layout": {"trigger": {"x": 0, "y": 0}},
        }
    )
    assert isinstance(template.graph_nodes[0], GraphNode)
    assert template.graph_nodes[0].kind == "trigger"
    assert template.graph_edges[0].source == "trigger"
    assert template.graph_layout["trigger"].y == 0


# ---------- GraphNode --------------------------------------------------------


def test_graph_node_rejects_invalid_kind():
    """Pydantic must reject kind values outside the Literal union."""
    with pytest.raises(ValidationError):
        GraphNode(id="x", kind="invalid-kind", label="X")  # type: ignore[arg-type]


def test_graph_node_accepts_every_canonical_kind():
    """All 7 NodeKind variants are accepted (forward-compat with Phases 3-4)."""
    for kind in (
        "trigger",
        "agent-action",
        "condition",
        "parallel",
        "merge",
        "human-approval",
        "output",
    ):
        node = GraphNode(id=f"{kind}-1", kind=kind, label=kind)
        assert node.kind == kind


def test_graph_node_config_defaults_to_none():
    node = GraphNode(id="x", kind="agent-action", label="X")
    assert node.config is None


# ---------- GraphEdge --------------------------------------------------------


def test_graph_edge_optional_source_handle_default_none():
    edge = GraphEdge(id="e0", source="a", target="b")
    assert edge.source_handle is None
    assert edge.label is None


def test_graph_edge_accepts_source_handle_and_label():
    edge = GraphEdge(
        id="e0",
        source="branch-1",
        target="merge-1",
        source_handle="true",
        label="when condition holds",
    )
    assert edge.source_handle == "true"
    assert edge.label == "when condition holds"


# ---------- NodePosition -----------------------------------------------------


def test_node_position_requires_int_xy():
    """x and y are int — strings that cannot coerce raise."""
    with pytest.raises(ValidationError):
        NodePosition(x="not-a-number", y=0)  # type: ignore[arg-type]


def test_node_position_coerces_numeric_strings():
    """Pydantic int field coerces clean numeric strings (lax mode default)."""
    pos = NodePosition(x="120", y="40")  # type: ignore[arg-type]
    assert pos.x == 120
    assert pos.y == 40


# ---------- graph_layout dict shape ------------------------------------------


def test_graph_layout_dict_key_is_node_id():
    """Layout is dict[str, NodePosition] — string keys, NodePosition values."""
    layout = {
        "trigger": NodePosition(x=0, y=0),
        "step-0": NodePosition(x=200, y=0),
    }
    template = WorkflowTemplateResponse(
        id="abc",
        name="Test",
        description="desc",
        category="custom",
        graph_layout=layout,
    )
    assert template.graph_layout is not None
    assert set(template.graph_layout.keys()) == {"trigger", "step-0"}
    assert all(isinstance(v, NodePosition) for v in template.graph_layout.values())
