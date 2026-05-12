"""Linear engine non-regression — ROADMAP criteria #2, #9, #10 for Phase 111.

After Phase 111 Plan 03 lands the graph-executor dispatcher
(``WorkflowEngine.requires_graph_executor`` + ``decide_next_graph_nodes`` +
``_enqueue_graph_node_step`` + the wired ``_advance_workflow``), linear
templates MUST continue to execute identically to the post-Phase-110
baseline. The dispatcher decides graph vs. linear at the top of
``_advance_workflow`` and falls through to the Edge Function delegation
for linear templates (unchanged path).

Tests in this file:

1. ``test_linear_template_decide_next_returns_empty_for_dispatch``
   (skip-on-no-creds): seed a linear template (trigger -> agent-action
   -> output, no non-linear kinds), insert an execution pinned to its
   version_id, call ``decide_next_graph_nodes`` and assert ``[]`` —
   the caller (``_advance_workflow``) then falls through to the EF
   delegation. ROADMAP criterion 2.

2. ``test_linear_template_with_null_template_version_id_returns_empty``
   (skip-on-no-creds): legacy execution with ``template_version_id =
   NULL`` (pre-Phase-110) -> ``decide_next_graph_nodes`` returns ``[]``
   without a DB hit on the version row. The linear path remains the
   default for legacy executions. ROADMAP criterion 9.

3. ``test_outcome_writer_signature_unchanged`` (no DB needed, always
   runs): pins the public method signatures of ``OutcomeWriter`` —
   ``__init__(self, client)`` and ``write_for_step(self, *, step_id,
   tool_output, status, tool_name, duration_ms, error_message)``.
   ROADMAP criterion 10 (Spec A invariant).

   *Iteration 1 plan-checker BLOCKER #1 fix:* the previous plan draft
   incorrectly asserted ``"text" in params and "source" in params`` —
   those are ``_derive()`` INTERNAL return values, NOT public
   parameters. The corrected expected set is sourced from
   ``app/workflows/outcome_writer.py:30-39``.

Run requirements
----------------
    supabase start
    supabase db reset --local   # apply Phase 109 + 110 + 111 migrations
    export SUPABASE_URL=...
    export SUPABASE_SERVICE_ROLE_KEY=...
    uv run pytest tests/integration/test_linear_workflow_execution_post_branching.py -v

Without creds the DB tests SKIP cleanly. Test 3 (signature guard)
always runs.
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

import inspect
import os
import uuid
from collections.abc import Iterator
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Shared fixtures (DB-bound) — skip if creds missing
# ---------------------------------------------------------------------------


_HAS_CREDS = all(
    os.environ.get(var) for var in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
)


@pytest.fixture(scope="module")
def supabase_client() -> Any:
    """Service-role client for setup, cleanup, and direct row inspection.

    Skipped when SUPABASE creds aren't present.
    """
    if not _HAS_CREDS:
        pytest.skip("Supabase credentials not provided in environment variables.")
    try:
        from app.services.supabase_client import get_client

        return get_client()
    except Exception:
        pytest.skip("Supabase not available")


def _seed_linear_template(client: Any) -> Iterator[tuple[str, str]]:
    """INSERT a workflow_templates row + workflow_template_versions v1
    row with a LINEAR graph (trigger -> agent-action -> output, no
    non-linear kinds).

    Yields (template_id, version_id). Cleanup on teardown.
    """
    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    t1 = str(uuid.uuid4())
    a1 = str(uuid.uuid4())
    o1 = str(uuid.uuid4())

    nodes = [
        {"id": t1, "kind": "trigger", "label": "Start"},
        {
            "id": a1,
            "kind": "agent-action",
            "label": "Do thing",
            "config": {"tool_name": "noop"},
        },
        {"id": o1, "kind": "output", "label": "Done"},
    ]
    edges = [
        {"id": str(uuid.uuid4()), "source": t1, "target": a1},
        {"id": str(uuid.uuid4()), "source": a1, "target": o1},
    ]

    client.table("workflow_templates").insert(
        {
            "id": template_id,
            "name": f"phase111-linear-{template_id[:8]}",
            "description": "Phase 111 Task 03-04 synthetic LINEAR template",
            "category": "test",
            "lifecycle_status": "published",
            "phases": [],
            "graph_nodes": nodes,
            "graph_edges": edges,
            "current_version_id": version_id,
        }
    ).execute()
    client.table("workflow_template_versions").insert(
        {
            "id": version_id,
            "template_id": template_id,
            "version_number": 1,
            "graph_nodes": nodes,
            "graph_edges": edges,
            "graph_layout": {},
            "saved_by_user_id": None,
            "comment": "Phase 111 Task 03-04 synthetic v1",
        }
    ).execute()

    yield template_id, version_id

    # Cleanup
    client.table("workflow_executions").delete().eq(
        "template_id", template_id
    ).execute()
    client.table("workflow_template_versions").delete().eq(
        "template_id", template_id
    ).execute()
    client.table("workflow_templates").delete().eq(
        "id", template_id
    ).execute()


@pytest.fixture()
def linear_template(supabase_client: Any) -> Iterator[tuple[str, str]]:
    """Per-test fixture wrapping _seed_linear_template."""
    yield from _seed_linear_template(supabase_client)


# ---------------------------------------------------------------------------
# Test 1: Linear template -> decide_next_graph_nodes returns []
#         (caller falls through to EF — ROADMAP criterion 2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _HAS_CREDS, reason="Supabase credentials not provided."
)
async def test_linear_template_decide_next_returns_empty_for_dispatch(
    supabase_client: Any, linear_template: tuple[str, str]
) -> None:
    """A pinned LINEAR template -> decide_next_graph_nodes returns []
    so the caller can fall back to the Edge Function delegation path.

    Also confirms requires_graph_executor(linear_graph) is False — both
    primitives must agree on the routing decision.

    ROADMAP criterion 2: dispatch on non-linear kinds. The negative case
    (linear template -> no dispatch) is just as important as the
    positive case (covered by Task 03-03).
    """
    from app.workflows.engine import WorkflowEngine

    template_id, version_id = linear_template
    execution_id = str(uuid.uuid4())
    supabase_client.table("workflow_executions").insert(
        {
            "id": execution_id,
            "template_id": template_id,
            "template_version_id": version_id,
            "user_id": "phase111-task-03-04-test-user",
            "status": "running",
            "context": {},
        }
    ).execute()

    engine = WorkflowEngine()
    # 1. dispatch predicate says "linear"
    nodes, _edges = await engine._load_template_graph(version_id)
    assert engine.requires_graph_executor(nodes) is False

    # 2. dispatcher returns [] so caller routes to EF
    result = await engine.decide_next_graph_nodes(execution_id)
    assert result == []


# ---------------------------------------------------------------------------
# Test 2: Legacy execution (template_version_id NULL) -> decide returns []
#         (ROADMAP criterion 9 — no regression on legacy linear runs)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _HAS_CREDS, reason="Supabase credentials not provided."
)
async def test_linear_template_with_null_template_version_id_returns_empty(
    supabase_client: Any, linear_template: tuple[str, str]
) -> None:
    """Legacy executions (pre-Phase-110) have ``template_version_id =
    NULL``. The dispatcher returns ``[]`` immediately without touching
    the workflow_template_versions table, and the caller falls through
    to the EF delegation (unchanged path).

    ROADMAP criterion 9: linear runs unchanged.
    """
    from app.workflows.engine import WorkflowEngine

    template_id, _version_id = linear_template
    execution_id = str(uuid.uuid4())
    supabase_client.table("workflow_executions").insert(
        {
            "id": execution_id,
            "template_id": template_id,
            "template_version_id": None,  # legacy
            "user_id": "phase111-task-03-04-test-user",
            "status": "running",
            "context": {},
        }
    ).execute()

    engine = WorkflowEngine()
    result = await engine.decide_next_graph_nodes(execution_id)
    assert result == []


# ---------------------------------------------------------------------------
# Test 3: OutcomeWriter signature guard (no DB — ALWAYS runs)
#         (ROADMAP criterion 10 — Spec A invariant)
# ---------------------------------------------------------------------------


def test_outcome_writer_signature_unchanged() -> None:
    """Pin OutcomeWriter contract — Spec A invariant per ROADMAP criterion 10.

    Verifies the public method signatures have not drifted. If this
    fails, Phase 111 (or a later phase) has modified Spec A's
    outcome-writing path and the live-workspace view may regress.

    Iteration 1 plan-checker BLOCKER #1 fix: the previous draft
    incorrectly asserted ``"text" in params and "source" in params`` —
    those are ``_derive()`` INTERNAL return values, not public
    parameters. The corrected expected set is sourced from
    ``app/workflows/outcome_writer.py:30-39``.
    """
    from app.workflows.outcome_writer import OutcomeWriter

    # __init__ contract: (self, client) — Spec A's signature
    sig = inspect.signature(OutcomeWriter.__init__)
    init_params = list(sig.parameters.keys())
    assert init_params == ["self", "client"], (
        f"OutcomeWriter.__init__ signature changed: got {init_params}, "
        f"expected ['self', 'client']"
    )

    # write_for_step contract (verified against
    # app/workflows/outcome_writer.py:30-39 on 2026-05-12):
    #   write_for_step(self, *, step_id, tool_output, status, tool_name,
    #                  duration_ms, error_message=None)
    sig2 = inspect.signature(OutcomeWriter.write_for_step)
    params2 = list(sig2.parameters.keys())
    expected = {
        "self",
        "step_id",
        "tool_output",
        "status",
        "tool_name",
        "duration_ms",
        "error_message",
    }
    assert set(params2) == expected, (
        f"OutcomeWriter.write_for_step signature changed: got {params2}, "
        f"expected exactly {sorted(expected)}"
    )
