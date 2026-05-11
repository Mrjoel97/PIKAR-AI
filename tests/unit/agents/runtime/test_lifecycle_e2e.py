# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""End-to-end smoke test for the four lifecycle callbacks together.

Task 45 — exercises one full turn through ``before_agent`` -> ``before_tool``
(research tool, allowed) -> ``after_tool`` (records research result, gate
not yet closed) -> ``before_tool`` (non-research tool, blocked) ->
``after_tool`` (next coverage check returns complete, gate closes) ->
``before_tool`` (non-research tool, now allowed) -> ``after_agent``
(audit + compaction).

Every runtime submodule is patched at
``app.agents.runtime.lifecycle.<submodule>``. The submodule call signatures
documented in :mod:`app.agents.runtime.lifecycle` are asserted in order.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Stub the ADK + genai surface just like the rest of the unit suite does.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.adk.tools", MagicMock())
sys.modules.setdefault("google.adk.tools.tool_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())

from app.agents.runtime import lifecycle  # noqa: E402
from app.agents.runtime.types import ResearchGateError  # noqa: E402


def _make_agent() -> MagicMock:
    agent = MagicMock(name="PikarBaseAgent")
    agent.agent_id = SimpleNamespace(value="financial")
    agent.user_id = uuid4()
    agent.persona_id = "founder"
    agent.ops = SimpleNamespace(compaction=SimpleNamespace())
    return agent


def _make_callback_context(state: dict) -> MagicMock:
    ctx = MagicMock(name="CallbackContext")
    ctx.state = state
    ctx.user_content = SimpleNamespace(
        parts=[SimpleNamespace(text="research and then send the report")]
    )
    ctx.session = SimpleNamespace(
        id=uuid4(), approx_token_count=0, events=[], state=state
    )
    return ctx


def _make_tool_context(state: dict) -> MagicMock:
    tool_ctx = MagicMock(name="ToolContext")
    tool_ctx.state = state
    return tool_ctx


def _make_tool(name: str) -> MagicMock:
    tool = MagicMock(name=f"tool::{name}")
    tool.name = name
    return tool


@pytest.mark.asyncio
async def test_full_turn_research_then_execute_then_audit():
    """One contiguous turn through all four callbacks.

    Shared state dict is threaded through every callback so the
    research-gate / persona-policy / compaction-summary handoffs work the
    way they would inside an ADK Runner.
    """

    agent = _make_agent()
    state: dict = {}
    contract_id = uuid4()
    state[lifecycle._RUNTIME_CONTRACT_ID_KEY] = contract_id
    state[lifecycle._RUNTIME_INITIATIVE_ID_KEY] = uuid4()

    classifier_result = SimpleNamespace(mode="initiative", signal="rule")
    persona_policy = MagicMock(name="PersonaPolicy")
    audit_report = MagicMock(name="AuditReport")
    compaction_result = SimpleNamespace(
        summary="this is the compacted summary",
        dropped_event_count=4,
        kept_event_count=8,
    )
    coverage_complete = MagicMock(name="ResearchResult")

    # ---- patch every submodule -----------------------------------------

    with (
        # task_router / persona_gate / skill_injection / memory_retrieval
        patch.object(
            lifecycle.persona_gate,
            "load_persona_policy",
            new=AsyncMock(return_value=persona_policy),
        ) as load_policy,
        patch.object(
            lifecycle.task_router,
            "classify",
            new=AsyncMock(return_value=classifier_result),
        ) as classify,
        patch.object(
            lifecycle.skill_injection,
            "match_and_inject",
            new=AsyncMock(return_value="## Relevant skills\n- s"),
        ) as match_inject,
        patch.object(
            lifecycle.memory_retrieval,
            "retrieve_relevant_history",
            new=AsyncMock(return_value="## Prior work\n- p"),
        ) as retrieve_history,
        patch.object(
            lifecycle.persona_gate,
            "apply_prompt_fragments",
            return_value="## Persona Policy\n- careful",
        ) as apply_fragments,
        # before_tool gates
        patch.object(lifecycle.persona_gate, "check_tool_allowed") as check_allowed,
        patch.object(
            lifecycle.persona_gate,
            "check_action_threshold",
            new=AsyncMock(return_value=None),
        ) as check_threshold,
        patch.object(lifecycle.persona_gate, "record_violation") as record_violation,
        # research_gate
        patch.object(
            lifecycle.research_gate,
            "is_open",
            new=AsyncMock(return_value=True),
        ) as is_open,
        patch.object(
            lifecycle.research_gate,
            "RESEARCH_TOOL_IDS",
            frozenset({"deep_research"}),
        ),
        patch.object(
            lifecycle.research_gate,
            "record_tool_result",
            new=AsyncMock(return_value=None),
        ) as record_research,
        patch.object(
            lifecycle.research_gate,
            "check_coverage",
            new=AsyncMock(side_effect=[None, coverage_complete]),
        ) as check_coverage,
        patch.object(
            lifecycle.research_gate,
            "close_gate",
            new=AsyncMock(return_value=None),
        ) as close_gate,
        # after_agent
        patch.object(
            lifecycle.audit,
            "audit_against_contract",
            new=AsyncMock(return_value=audit_report),
        ) as audit_call,
        patch.object(
            lifecycle.audit,
            "persist_audit_report",
            new=AsyncMock(return_value=uuid4()),
        ) as persist_audit,
        patch.object(
            lifecycle.audit,
            "attach_audit_summary_to_evidence",
            new=AsyncMock(return_value=None),
        ) as attach_audit,
        patch.object(
            lifecycle.compaction,
            "maybe_compact",
            new=AsyncMock(return_value=compaction_result),
        ) as compact,
        patch.object(lifecycle, "publication", None),
    ):
        # Build all four callbacks once (they share `agent`).
        ba_cb = lifecycle.before_agent(agent)
        bt_cb = lifecycle.before_tool(agent)
        at_cb = lifecycle.after_tool(agent)
        aa_cb = lifecycle.after_agent(agent)

        # 1. before_agent ---------------------------------------------------
        cb_ctx = _make_callback_context(state)
        await ba_cb(cb_ctx)

        load_policy.assert_called_once()
        classify.assert_called_once()
        match_inject.assert_called_once()
        retrieve_history.assert_called_once()
        apply_fragments.assert_called_once()
        assert state[lifecycle._RUNTIME_PERSONA_POLICY_KEY] is persona_policy
        assert state[lifecycle._RUNTIME_CLASSIFIER_MODE_KEY] == "initiative"
        blob = state[lifecycle._RUNTIME_BLOCKS_KEY]
        assert "## Relevant skills" in blob
        assert "## Prior work" in blob
        assert "## Persona Policy" in blob

        # 2. before_tool (research tool, gate open -> allowed) -------------
        tool_ctx = _make_tool_context(state)
        result = await bt_cb(_make_tool("deep_research"), {}, tool_ctx)
        assert result is None
        check_allowed.assert_called()
        check_threshold.assert_called()
        is_open.assert_called()  # gate consulted

        # 3. after_tool (research tool, coverage not yet complete) ---------
        await at_cb(
            _make_tool("deep_research"), {}, tool_ctx, {"summary": "partial"}
        )
        record_research.assert_called_once()
        assert record_research.call_args.kwargs["contract_id"] == contract_id
        # First check_coverage returned None -> close_gate NOT yet called.
        assert check_coverage.call_count == 1
        close_gate.assert_not_called()
        assert lifecycle._RUNTIME_RESEARCH_RESULT_KEY not in state

        # 4. before_tool (non-research tool, gate still open -> BLOCKED) ----
        with pytest.raises(ResearchGateError):
            await bt_cb(_make_tool("send_email"), {}, _make_tool_context(state))
        record_violation.assert_called()

        # 5. after_tool again (research tool, second call coverage complete)
        is_open_count_before = is_open.call_count
        await at_cb(
            _make_tool("deep_research"),
            {},
            tool_ctx,
            {"summary": "done", "sources": [1, 2, 3]},
        )
        # check_coverage called a second time, this time returning coverage.
        assert check_coverage.call_count == 2
        close_gate.assert_called_once()
        assert close_gate.call_args.kwargs["contract_id"] == contract_id
        assert close_gate.call_args.kwargs["result"] is coverage_complete
        assert state[lifecycle._RUNTIME_RESEARCH_RESULT_KEY] is coverage_complete

        # 6. before_tool (non-research tool, gate now closed -> allowed) ----
        # Simulate the gate now reporting closed by flipping is_open's return.
        is_open.return_value = False
        result = await bt_cb(_make_tool("send_email"), {}, _make_tool_context(state))
        assert result is None
        assert is_open.call_count > is_open_count_before

        # 7. after_agent (audit + compaction) -------------------------------
        # Stage an artifact so the audit chain fires.
        state[lifecycle._RUNTIME_ARTIFACTS_KEY] = [
            SimpleNamespace(kind="report", ref="s3://x", summary="r", payload=None)
        ]
        state[lifecycle._RUNTIME_CONTRACT_KEY] = SimpleNamespace(
            id=uuid4(),
            source="initiative_step",
            goal="g",
            todo_items=[],
            success_criteria=[],
            owners=[],
            evidence_required=[],
            initiative_id=state[lifecycle._RUNTIME_INITIATIVE_ID_KEY],
            initiative_phase="execution",
            sibling_steps=[],
        )

        aa_ctx = _make_callback_context(state)
        await aa_cb(aa_ctx)

        audit_call.assert_called_once()
        persist_audit.assert_called_once()
        attach_audit.assert_called_once()
        compact.assert_called_once()
        # Compaction summary cached for the next turn.
        assert (
            state[lifecycle._RUNTIME_COMPACTION_SUMMARY_KEY]
            == "this is the compacted summary"
        )

        # No callback errors should have been recorded in a clean happy path.
        assert state.get(lifecycle._RUNTIME_CALLBACK_ERRORS_KEY, []) == []
