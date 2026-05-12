"""Unit tests for StepExecutor graph_node_id propagation (Phase 111 Plan 03).

Covers Task 03-02 of `111-03-engine-dispatch-PLAN.md`:
the surgical extension to ``StepExecutor._normalize_output`` that
propagates ``step.step_definition.graph_node_id`` into
``output_data._execution_meta.graph_node_id`` so the engine's
:meth:`WorkflowEngine.decide_next_graph_nodes` can rebuild the
``previous_outcomes`` dict keyed by graph node id (CONTEXT.md
decision 8 revision 2026-05-12 — JSONB workaround, no migration).

Linear runs never carry ``graph_node_id`` on their step_definition,
so the new key is absent and existing assertions don't change.

These tests exercise ``_normalize_output`` directly (pure-functional
staticmethod; the surgical edit lives there) rather than the whole
``execute_step`` path — that avoids needing a supabase client. The
full integration of the graph_node_id flow is covered by Tasks
03-05 + 03-06.
"""

# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

from typing import Any

from app.workflows.step_executor import StepExecutor


class TestStepExecutorGraphNodeIdFlow:
    """Pin the JSONB shape produced by _normalize_output for graph-routed runs."""

    def test_step_executor_writes_graph_node_id_to_execution_meta(self) -> None:
        """When step_definition carries a graph_node_id, the normalized
        output_data._execution_meta dict MUST include the same UUID — this is
        what WorkflowEngine.decide_next_graph_nodes reads to rebuild
        previous_outcomes keyed by graph node id.
        """
        step_definition: dict[str, Any] = {
            "name": "Lead scoring step",
            "graph_node_id": "node-uuid-123",
            "tool": "score_lead",
        }
        tool_output = {"lead_score": 75}

        normalized = StepExecutor._normalize_output(
            tool_output,
            tool_name="score_lead",
            trust_class="trusted",
            verification_status="passed",
            evidence_refs=[],
            duration_ms=42,
            attempt=1,
            step_definition=step_definition,
        )

        assert "_execution_meta" in normalized
        meta = normalized["_execution_meta"]
        assert meta.get("graph_node_id") == "node-uuid-123"

    def test_step_executor_omits_graph_node_id_when_not_set(self) -> None:
        """Linear runs (no graph_node_id on step_definition) MUST NOT carry
        a graph_node_id key in _execution_meta — the assertions on the existing
        shape (Phase 109/110 tests) must remain valid.
        """
        step_definition: dict[str, Any] = {
            "name": "Plain linear step",
            "tool": "do_thing",
        }

        normalized = StepExecutor._normalize_output(
            {"result": "ok"},
            tool_name="do_thing",
            trust_class="trusted",
            verification_status="passed",
            evidence_refs=[],
            duration_ms=10,
            attempt=1,
            step_definition=step_definition,
        )

        meta = normalized["_execution_meta"]
        # graph_node_id MUST be absent (or None) for linear runs
        assert meta.get("graph_node_id") is None

    def test_step_executor_preserves_other_execution_meta(self) -> None:
        """The existing _execution_meta fields (tool_name, trust_class,
        verification_status, evidence_refs, duration_ms, attempt,
        last_failure_reason, reason_code) must remain present alongside the
        new graph_node_id key — no regression in the meta dict shape.
        """
        step_definition: dict[str, Any] = {
            "graph_node_id": "node-9",
        }

        normalized = StepExecutor._normalize_output(
            {"x": 1},
            tool_name="some_tool",
            trust_class="trusted",
            verification_status="passed",
            evidence_refs=[{"id": "ev-1"}],
            duration_ms=99,
            attempt=2,
            last_failure_reason=None,
            reason_code=None,
            step_definition=step_definition,
        )

        meta = normalized["_execution_meta"]
        # New key
        assert meta.get("graph_node_id") == "node-9"
        # Existing keys still present
        assert meta.get("tool_name") == "some_tool"
        assert meta.get("trust_class") == "trusted"
        assert meta.get("verification_status") == "passed"
        assert meta.get("evidence_refs") == [{"id": "ev-1"}]
        assert meta.get("duration_ms") == 99
        assert meta.get("attempt") == 2
        assert "last_failure_reason" in meta
        assert "reason_code" in meta
