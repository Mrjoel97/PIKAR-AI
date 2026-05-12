"""Branching execution integration test — ROADMAP criterion #1 for Phase 111.

Task 03-03 deliverable: dispatcher-primitive coverage. Task 03-06 will
extend this file with end-to-end tests through the production wire
(start_workflow -> _advance_workflow -> _enqueue_graph_node_step ->
workflow_steps INSERT).

This file mirrors Phase 110 Plan 02's ``test_linear_workflow_execution_post_versioning.py``
test pattern:

1. SKIP cleanly when SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are absent.
2. Create a fresh test template directly in the DB (workflow_templates row +
   workflow_template_versions v1 with a branching graph).
3. Insert a workflow_executions row pinned to that template_version_id.
4. Insert seed workflow_steps rows representing completed upstream steps
   with ``output_data._execution_meta.graph_node_id`` set + the
   condition-expression's input fields populated.
5. Call ``WorkflowEngine().decide_next_graph_nodes(execution_id)`` and
   assert the returned list contains the correct branch's target node id.
6. Cleanup: DELETE the test rows in try/finally.

Run requirements
----------------
    supabase start
    supabase db reset --local   # apply Phase 109 + 110 + 111 migrations
    export SUPABASE_URL=...
    export SUPABASE_SERVICE_ROLE_KEY=...
    uv run pytest tests/integration/test_branching_workflow_execution.py -v

Without creds the suite SKIPS cleanly.
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from typing import Any

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not all(
            os.environ.get(var)
            for var in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
        ),
        reason="Supabase credentials not provided in environment variables.",
    ),
]


# ---------------------------------------------------------------------------
# Helpers — synthetic branching template fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def supabase_client() -> Any:
    """Service-role client for setup, cleanup, and direct row inspection."""
    try:
        from app.services.supabase_client import get_client

        return get_client()
    except Exception:
        pytest.skip("Supabase not available")


def _build_branching_graph() -> tuple[
    str, str, str, str, str, list[dict[str, Any]], list[dict[str, Any]]
]:
    """Build a 2-branch conditional graph.

    Returns a tuple of (t1_id, a1_id, c1_id, t_out_id, f_out_id, nodes, edges).

    Topology:
        t1 (trigger) -> a1 (agent-action, lead_score producer)
                       -> c1 (condition: lead_score > 50?)
                              --[true]--> t-out (output)
                              --[false]--> f-out (output)

    The condition uses the dotted-path JSONLogic var form which Plan 01's
    graph_executor supports: previous_outcomes.<a1_id>.lead_score.
    """
    t1 = str(uuid.uuid4())
    a1 = str(uuid.uuid4())
    c1 = str(uuid.uuid4())
    t_out = str(uuid.uuid4())
    f_out = str(uuid.uuid4())

    nodes = [
        {"id": t1, "kind": "trigger", "label": "Start"},
        {
            "id": a1,
            "kind": "agent-action",
            "label": "Score lead",
            "config": {"tool_name": "score_lead"},
        },
        {
            "id": c1,
            "kind": "condition",
            "label": "Score > 50?",
            "config": {
                "expression": {
                    ">": [
                        {"var": f"previous_outcomes.{a1}.lead_score"},
                        50,
                    ]
                }
            },
        },
        {"id": t_out, "kind": "output", "label": "Hot lead"},
        {"id": f_out, "kind": "output", "label": "Cold lead"},
    ]
    edges = [
        {"id": str(uuid.uuid4()), "source": t1, "target": a1},
        {"id": str(uuid.uuid4()), "source": a1, "target": c1},
        {
            "id": str(uuid.uuid4()),
            "source": c1,
            "target": t_out,
            "source_handle": "true",
        },
        {
            "id": str(uuid.uuid4()),
            "source": c1,
            "target": f_out,
            "source_handle": "false",
        },
    ]
    return t1, a1, c1, t_out, f_out, nodes, edges


def _seed_branching_template(
    client: Any,
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> tuple[str, str]:
    """INSERT a workflow_templates row + workflow_template_versions v1 row.

    Returns the (template_id, version_id) UUIDs.
    """
    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    # workflow_templates: minimal valid row.
    client.table("workflow_templates").insert(
        {
            "id": template_id,
            "name": f"phase111-branch-{template_id[:8]}",
            "description": "Phase 111 Task 03-03 synthetic branching template",
            "category": "test",
            "lifecycle_status": "published",
            "phases": [],
            "graph_nodes": nodes,
            "graph_edges": edges,
            "current_version_id": version_id,
        }
    ).execute()

    # workflow_template_versions v1 pinned to this template.
    client.table("workflow_template_versions").insert(
        {
            "id": version_id,
            "template_id": template_id,
            "version_number": 1,
            "graph_nodes": nodes,
            "graph_edges": edges,
            "graph_layout": {},
            "saved_by_user_id": None,
            "comment": "Phase 111 Task 03-03 synthetic v1",
        }
    ).execute()

    return template_id, version_id


def _seed_execution(
    client: Any,
    *,
    template_id: str,
    version_id: str,
    user_context: dict[str, Any] | None = None,
) -> str:
    """INSERT a workflow_executions row pinned to template_version_id.

    Returns the execution UUID.
    """
    execution_id = str(uuid.uuid4())
    client.table("workflow_executions").insert(
        {
            "id": execution_id,
            "template_id": template_id,
            "template_version_id": version_id,
            "user_id": "phase111-task-03-03-test-user",
            "status": "running",
            "context": user_context or {},
        }
    ).execute()
    return execution_id


def _seed_completed_step(
    client: Any,
    *,
    execution_id: str,
    step_index: int,
    graph_node_id: str,
    output_data: dict[str, Any],
) -> str:
    """INSERT a workflow_steps row with status='completed' and the given
    output_data dict (must include the _execution_meta.graph_node_id key).
    """
    step_id = str(uuid.uuid4())
    output_data = dict(output_data)
    meta = dict(output_data.get("_execution_meta") or {})
    meta["graph_node_id"] = graph_node_id
    output_data["_execution_meta"] = meta

    client.table("workflow_steps").insert(
        {
            "id": step_id,
            "execution_id": execution_id,
            "step_index": step_index,
            "phase_index": 0,
            "phase_name": "graph",
            "step_name": f"node-{graph_node_id[:8]}",
            "status": "completed",
            "started_at": "2026-05-12T00:00:00Z",
            "completed_at": "2026-05-12T00:00:01Z",
            "input_data": {},
            "output_data": output_data,
        }
    ).execute()
    return step_id


def _cleanup_template(
    client: Any,
    *,
    template_id: str,
    execution_ids: list[str],
) -> None:
    """Delete in dependency order: steps -> executions -> versions -> template."""
    for exec_id in execution_ids:
        client.table("workflow_steps").delete().eq(
            "execution_id", exec_id
        ).execute()
    for exec_id in execution_ids:
        client.table("workflow_executions").delete().eq(
            "id", exec_id
        ).execute()
    client.table("workflow_template_versions").delete().eq(
        "template_id", template_id
    ).execute()
    client.table("workflow_templates").delete().eq(
        "id", template_id
    ).execute()


@pytest.fixture()
def branching_template(supabase_client: Any) -> Iterator[dict[str, Any]]:
    """Per-test fixture: seed a fresh branching template + cleanup.

    Yields a dict with: template_id, version_id, t1, a1, c1, t_out, f_out.
    """
    t1, a1, c1, t_out, f_out, nodes, edges = _build_branching_graph()
    template_id, version_id = _seed_branching_template(
        supabase_client, nodes=nodes, edges=edges
    )
    created_executions: list[str] = []
    bundle = {
        "template_id": template_id,
        "version_id": version_id,
        "t1": t1,
        "a1": a1,
        "c1": c1,
        "t_out": t_out,
        "f_out": f_out,
        "created_executions": created_executions,
    }
    try:
        yield bundle
    finally:
        _cleanup_template(
            supabase_client,
            template_id=template_id,
            execution_ids=created_executions,
        )


# ---------------------------------------------------------------------------
# Task 03-03 Tests: dispatcher-primitive coverage (ROADMAP criterion 1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatcher_routes_to_true_branch_when_expression_truthy(
    supabase_client: Any, branching_template: dict[str, Any]
) -> None:
    """Seed a completed agent-action with lead_score=75 and an immediately
    self-completed condition step; assert decide_next_graph_nodes returns
    the 'true' branch's output node id.

    Closes ROADMAP criterion 1 at the dispatcher-primitive level. The full
    end-to-end production-wire variant lives in Task 03-06.
    """
    from app.workflows.engine import WorkflowEngine

    bundle = branching_template
    execution_id = _seed_execution(
        supabase_client,
        template_id=bundle["template_id"],
        version_id=bundle["version_id"],
    )
    bundle["created_executions"].append(execution_id)

    # Seed: agent-action a1 completed with lead_score=75
    _seed_completed_step(
        supabase_client,
        execution_id=execution_id,
        step_index=0,
        graph_node_id=bundle["a1"],
        output_data={"lead_score": 75},
    )
    # Seed: condition c1 has been "evaluated" (its row exists). This is what
    # the Phase 111 design's immediate-self-complete pattern looks like.
    _seed_completed_step(
        supabase_client,
        execution_id=execution_id,
        step_index=1,
        graph_node_id=bundle["c1"],
        output_data={},
    )

    engine = WorkflowEngine()
    result = await engine.decide_next_graph_nodes(execution_id)

    assert result == [bundle["t_out"]], (
        f"Expected 'true' branch -> {bundle['t_out']}, got {result}"
    )


@pytest.mark.asyncio
async def test_dispatcher_routes_to_false_branch_when_expression_falsy(
    supabase_client: Any, branching_template: dict[str, Any]
) -> None:
    """Same graph as above, but seed lead_score=25 -> 'false' branch.

    Closes ROADMAP criterion 1 at the dispatcher-primitive level (falsy
    side). The full end-to-end production-wire variant lives in Task 03-06.
    """
    from app.workflows.engine import WorkflowEngine

    bundle = branching_template
    execution_id = _seed_execution(
        supabase_client,
        template_id=bundle["template_id"],
        version_id=bundle["version_id"],
    )
    bundle["created_executions"].append(execution_id)

    _seed_completed_step(
        supabase_client,
        execution_id=execution_id,
        step_index=0,
        graph_node_id=bundle["a1"],
        output_data={"lead_score": 25},
    )
    _seed_completed_step(
        supabase_client,
        execution_id=execution_id,
        step_index=1,
        graph_node_id=bundle["c1"],
        output_data={},
    )

    engine = WorkflowEngine()
    result = await engine.decide_next_graph_nodes(execution_id)

    assert result == [bundle["f_out"]], (
        f"Expected 'false' branch -> {bundle['f_out']}, got {result}"
    )
