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


# ---------------------------------------------------------------------------
# Task 03-06 Tests: End-to-end through the production wire
# (ROADMAP criterion 1 — full closure)
# ---------------------------------------------------------------------------
#
# These tests exercise the FULL production call site:
#   _advance_workflow -> decide_next_graph_nodes -> _enqueue_graph_node_step
#       -> workflow_steps INSERT
#
# They DELIBERATELY bypass the EXISTING WorkflowEngine.start_workflow public
# method (which spins up persona resolution + EF trigger call). Per the
# planner's "simpler approach" guidance in Task 03-06, directly seeding the
# workflow_executions row with the right template_version_id and then
# invoking _advance_workflow is closer to Phase 110's integration test
# pattern and still hits the REAL production methods we ship in this plan
# (no monkey-patching of _advance_workflow / decide_next_graph_nodes /
# _enqueue_graph_node_step).


@pytest.fixture()
def linear_template(supabase_client: Any) -> Iterator[dict[str, Any]]:
    """Per-test fixture: seed a fresh LINEAR template + cleanup.

    Topology: trigger -> agent-action -> output (no branching kinds).
    Used by Test 5 (ROADMAP criterion 9 non-regression).
    """
    t1 = str(uuid.uuid4())
    a1 = str(uuid.uuid4())
    o1 = str(uuid.uuid4())
    nodes = [
        {"id": t1, "kind": "trigger", "label": "Start"},
        {
            "id": a1,
            "kind": "agent-action",
            "label": "Do work",
            "config": {"tool_name": "noop"},
        },
        {"id": o1, "kind": "output", "label": "Done"},
    ]
    edges = [
        {"id": str(uuid.uuid4()), "source": t1, "target": a1},
        {"id": str(uuid.uuid4()), "source": a1, "target": o1},
    ]
    template_id, version_id = _seed_branching_template(
        supabase_client, nodes=nodes, edges=edges
    )
    created_executions: list[str] = []
    bundle = {
        "template_id": template_id,
        "version_id": version_id,
        "t1": t1,
        "a1": a1,
        "o1": o1,
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


def _fetch_steps(
    client: Any, *, execution_id: str
) -> list[dict[str, Any]]:
    """Return all workflow_steps rows for an execution, ordered by step_index."""
    res = (
        client.table("workflow_steps")
        .select("*")
        .eq("execution_id", execution_id)
        .order("step_index")
        .execute()
    )
    return res.data or []


def _fetch_execution(
    client: Any, *, execution_id: str
) -> dict[str, Any]:
    """Return the workflow_executions row."""
    res = (
        client.table("workflow_executions")
        .select("*")
        .eq("id", execution_id)
        .single()
        .execute()
    )
    return res.data or {}


@pytest.mark.asyncio
async def test_e2e_start_workflow_routes_truthy_branch_via_advance_workflow(
    supabase_client: Any, branching_template: dict[str, Any]
) -> None:
    """End-to-end: seed a branching template + execution + completed a1
    with lead_score=75, then invoke the REAL _advance_workflow. Assert
    that the production wire (Python dispatch via
    decide_next_graph_nodes + _enqueue_graph_node_step) inserts the
    correct branch's workflow_steps row(s) and marks the execution
    completed when the output node fires.

    Closes ROADMAP criterion 1 through the production call site —
    NO monkey-patching of _advance_workflow / decide_next_graph_nodes /
    _enqueue_graph_node_step.
    """
    from unittest.mock import patch

    from app.workflows.engine import WorkflowEngine

    bundle = branching_template
    execution_id = _seed_execution(
        supabase_client,
        template_id=bundle["template_id"],
        version_id=bundle["version_id"],
    )
    bundle["created_executions"].append(execution_id)

    # Seed: a1 completed with lead_score=75 at the top level of output_data
    # so the JSONLogic dotted-path resolves
    # (previous_outcomes.<a1_id>.lead_score in the fixture).
    _seed_completed_step(
        supabase_client,
        execution_id=execution_id,
        step_index=0,
        graph_node_id=bundle["a1"],
        output_data={"lead_score": 75},
    )

    engine = WorkflowEngine()
    execution_row = _fetch_execution(supabase_client, execution_id=execution_id)

    # Mock the EF client so this test stays Python-only — if the linear
    # fallback was wrongly taken we'd see a failing EF call we can assert
    # against. The graph path should NOT touch the EF.
    with patch("app.workflows.engine.edge_function_client") as mock_ef:
        from unittest.mock import AsyncMock

        mock_ef.execute_workflow = AsyncMock(return_value={"ok": True})
        await engine._advance_workflow(execution_row, [])
        # Python owned the dispatch — EF must NOT have been called.
        mock_ef.execute_workflow.assert_not_called()

    # Verify the inserted rows match the expected branch
    rows = _fetch_steps(supabase_client, execution_id=execution_id)
    inserted_node_ids = {
        ((r.get("output_data") or {}).get("_execution_meta") or {}).get(
            "graph_node_id"
        )
        for r in rows
    }
    assert bundle["c1"] in inserted_node_ids, (
        f"Condition c1 row should have been enqueued; got {inserted_node_ids}"
    )
    assert bundle["t_out"] in inserted_node_ids, (
        f"True-branch output row should have been enqueued; got "
        f"{inserted_node_ids}"
    )
    assert bundle["f_out"] not in inserted_node_ids, (
        f"False-branch output row should NOT exist; got {inserted_node_ids}"
    )

    # Output node is terminal — execution should be marked completed.
    refreshed = _fetch_execution(supabase_client, execution_id=execution_id)
    assert refreshed.get("status") == "completed", (
        f"Execution should be completed after output enqueue; got "
        f"status={refreshed.get('status')!r}"
    )


@pytest.mark.asyncio
async def test_e2e_start_workflow_routes_falsy_branch_via_advance_workflow(
    supabase_client: Any, branching_template: dict[str, Any]
) -> None:
    """End-to-end: same as the truthy branch test but seed lead_score=25
    so the condition evaluates falsy. Assert the false-branch output row
    is enqueued and the true-branch row is NOT.
    """
    from unittest.mock import AsyncMock, patch

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

    engine = WorkflowEngine()
    execution_row = _fetch_execution(supabase_client, execution_id=execution_id)

    with patch("app.workflows.engine.edge_function_client") as mock_ef:
        mock_ef.execute_workflow = AsyncMock(return_value={"ok": True})
        await engine._advance_workflow(execution_row, [])
        mock_ef.execute_workflow.assert_not_called()

    rows = _fetch_steps(supabase_client, execution_id=execution_id)
    inserted_node_ids = {
        ((r.get("output_data") or {}).get("_execution_meta") or {}).get(
            "graph_node_id"
        )
        for r in rows
    }
    assert bundle["c1"] in inserted_node_ids
    assert bundle["f_out"] in inserted_node_ids, (
        f"False-branch output row should have been enqueued; got "
        f"{inserted_node_ids}"
    )
    assert bundle["t_out"] not in inserted_node_ids, (
        f"True-branch output row should NOT exist; got {inserted_node_ids}"
    )

    refreshed = _fetch_execution(supabase_client, execution_id=execution_id)
    assert refreshed.get("status") == "completed"


@pytest.mark.asyncio
async def test_e2e_advance_workflow_for_linear_template_delegates_to_ef_and_inserts_no_rows(
    supabase_client: Any, linear_template: dict[str, Any]
) -> None:
    """End-to-end ROADMAP criterion 9 non-regression: a linear template's
    _advance_workflow delegates to the Edge Function as before; the Python
    engine inserts ZERO workflow_steps rows.

    The EF (mocked here) owns linear orchestration. After this test:
       * edge_function_client.execute_workflow called exactly once with
         action='advance'.
       * No new workflow_steps rows inserted by the Python engine.
       * Return value matches the legacy shim's {"status": "processing", ...}.
    """
    from unittest.mock import AsyncMock, patch

    from app.workflows.engine import WorkflowEngine

    bundle = linear_template
    execution_id = _seed_execution(
        supabase_client,
        template_id=bundle["template_id"],
        version_id=bundle["version_id"],
    )
    bundle["created_executions"].append(execution_id)

    # No completed-step seeding — linear templates run through the EF.
    pre_rows = _fetch_steps(supabase_client, execution_id=execution_id)
    assert pre_rows == [], "Linear template should start with zero steps"

    engine = WorkflowEngine()
    execution_row = _fetch_execution(supabase_client, execution_id=execution_id)

    with patch("app.workflows.engine.edge_function_client") as mock_ef:
        mock_ef.execute_workflow = AsyncMock(return_value={"ok": True})
        result = await engine._advance_workflow(execution_row, [])
        mock_ef.execute_workflow.assert_called_once_with(
            execution_id, action="advance"
        )

    # Python engine inserted ZERO new rows — EF owns the linear orchestration.
    post_rows = _fetch_steps(supabase_client, execution_id=execution_id)
    assert post_rows == [], (
        f"Linear template should have ZERO Python-inserted rows; "
        f"got {len(post_rows)}: {post_rows}"
    )
    assert isinstance(result, dict)
    assert result.get("status") == "processing"
