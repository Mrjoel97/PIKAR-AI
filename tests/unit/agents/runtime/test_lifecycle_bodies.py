# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Section B per-callback unit tests for :mod:`app.agents.runtime.lifecycle`.

Each test mocks every runtime submodule at
``app.agents.runtime.lifecycle.<submodule>`` and exercises one branch of the
factory's returned async callable.

Coverage map (tasks reference the W1+W2 plan):

* ``before_agent`` — Tasks 29, 30, 43
* ``before_tool``  — Tasks 31, 32, 33, 34, 43
* ``after_tool``   — Tasks 35, 43
* ``after_agent``  — Tasks 36, 37, 38, 43
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

# Stub the google.adk + google.genai surface BEFORE importing the lifecycle
# module — matches the pattern used by the other unit tests in this folder.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.adk.tools", MagicMock())
sys.modules.setdefault("google.adk.tools.tool_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())

from app.agents.runtime import lifecycle  # noqa: E402
from app.agents.runtime.types import (  # noqa: E402
    InitiativeContractError,
    PersonaPolicyError,
    ResearchGateError,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_agent(*, persona_id: str = "founder") -> MagicMock:
    """Build a minimal stand-in for :class:`PikarBaseAgent`.

    The lifecycle factories only ever touch ``agent.user_id``,
    ``agent.agent_id``, ``agent.persona_id``, and ``agent.ops`` — a
    MagicMock with those attributes set is sufficient.
    """
    agent = MagicMock(name="PikarBaseAgent")
    agent.agent_id = SimpleNamespace(value="financial")
    agent.user_id = uuid4()
    agent.persona_id = persona_id
    agent.ops = SimpleNamespace(compaction=SimpleNamespace())
    return agent


def _make_callback_context(state: dict | None = None) -> MagicMock:
    """Return a MagicMock shaped like ADK's CallbackContext.

    ``state`` is mutable — the lifecycle bodies write into it.
    ``user_content`` carries a single text part so ``_extract_user_text``
    returns deterministic input.
    """
    ctx = MagicMock(name="CallbackContext")
    ctx.state = state if state is not None else {}
    part = SimpleNamespace(text="please draft a report")
    ctx.user_content = SimpleNamespace(parts=[part])
    ctx.session = SimpleNamespace(
        id=uuid4(), approx_token_count=0, events=[], state=ctx.state
    )
    return ctx


def _make_tool_context(state: dict | None = None) -> MagicMock:
    """Return a MagicMock shaped like ADK's ToolContext."""
    tool_ctx = MagicMock(name="ToolContext")
    tool_ctx.state = state if state is not None else {}
    return tool_ctx


def _make_tool(name: str) -> MagicMock:
    """Return a mock tool with a ``.name`` attribute."""
    tool = MagicMock(name=f"tool::{name}")
    tool.name = name
    return tool


@pytest.fixture
def agent():
    return _make_agent()


# ---------------------------------------------------------------------------
# before_agent — Tasks 29, 30, 43
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_before_agent_happy_path_composes_blocks_in_order(agent):
    """Classify -> persona policy -> skills -> memory -> persona fragments
    are all called, and the composed blocks land in session state in the
    documented order."""

    classifier_result = SimpleNamespace(mode="direct", signal="rule")
    persona_policy_obj = MagicMock(name="PersonaPolicy")

    with (
        patch.object(
            lifecycle.persona_gate, "load_persona_policy", new=AsyncMock(return_value=persona_policy_obj)
        ),
        patch.object(
            lifecycle.task_router, "classify", new=AsyncMock(return_value=classifier_result)
        ),
        patch.object(
            lifecycle.skill_injection,
            "match_and_inject",
            new=AsyncMock(return_value="## Skills\n- skill A"),
        ),
        patch.object(
            lifecycle.memory_retrieval,
            "retrieve_relevant_history",
            new=AsyncMock(return_value="## Prior work\n- memory A"),
        ),
        patch.object(
            lifecycle.persona_gate,
            "apply_prompt_fragments",
            return_value="## Persona Policy\n- be precise",
        ),
    ):
        callback = lifecycle.before_agent(agent)
        ctx = _make_callback_context()
        result = await callback(ctx)

    assert result is None
    blob = ctx.state[lifecycle._RUNTIME_BLOCKS_KEY]
    # Composition order: compaction (absent), skills, memory, persona.
    assert "## Skills" in blob
    assert "## Prior work" in blob
    assert "## Persona Policy" in blob
    assert blob.index("## Skills") < blob.index("## Prior work") < blob.index(
        "## Persona Policy"
    )
    # Classifier signal cached for downstream consumers.
    assert ctx.state[lifecycle._RUNTIME_CLASSIFIER_MODE_KEY] == "direct"
    assert ctx.state[lifecycle._RUNTIME_CLASSIFIER_SIGNAL_KEY] == "rule"
    # Persona policy cached so before_tool can reuse it without DB round trip.
    assert ctx.state[lifecycle._RUNTIME_PERSONA_POLICY_KEY] is persona_policy_obj


@pytest.mark.asyncio
async def test_before_agent_includes_cached_compaction_summary(agent):
    """A summary cached on state by a prior turn must be folded into the
    composed blocks blob ahead of skills / memory / persona fragments."""

    classifier_result = SimpleNamespace(mode="direct", signal="rule")

    with (
        patch.object(
            lifecycle.persona_gate, "load_persona_policy", new=AsyncMock(return_value=MagicMock())
        ),
        patch.object(
            lifecycle.task_router, "classify", new=AsyncMock(return_value=classifier_result)
        ),
        patch.object(
            lifecycle.skill_injection,
            "match_and_inject",
            new=AsyncMock(return_value="## Skills\nbody"),
        ),
        patch.object(
            lifecycle.memory_retrieval,
            "retrieve_relevant_history",
            new=AsyncMock(return_value=""),
        ),
        patch.object(
            lifecycle.persona_gate, "apply_prompt_fragments", return_value=""
        ),
    ):
        callback = lifecycle.before_agent(agent)
        seed_state = {
            lifecycle._RUNTIME_COMPACTION_SUMMARY_KEY: "earlier-turn summary",
        }
        ctx = _make_callback_context(state=seed_state)
        await callback(ctx)

    blob = ctx.state[lifecycle._RUNTIME_BLOCKS_KEY]
    assert "Prior conversation summary" in blob
    assert "earlier-turn summary" in blob
    assert blob.index("Prior conversation summary") < blob.index("## Skills")


@pytest.mark.asyncio
async def test_before_agent_records_initiative_contract_error_via_inner_handler(agent):
    """An ``InitiativeContractError`` raised from a wrapped submodule call is
    caught by the per-step ``except Exception`` and recorded on the
    callback-errors bucket. The outer ``except InitiativeContractError``
    handler is reserved for contract-validation errors raised OUTSIDE the
    inner try blocks (e.g. ``_wrap_user_request`` once Section D wires
    initiative contract validation in).

    Either way the contract is the same: the callback never crashes the
    turn — it returns ``None`` and the error is visible on session state.
    """

    with (
        patch.object(
            lifecycle.persona_gate,
            "load_persona_policy",
            new=AsyncMock(side_effect=InitiativeContractError("bad contract")),
        ),
        # Stub remaining submodules so the rest of the body runs cleanly.
        patch.object(
            lifecycle.task_router,
            "classify",
            new=AsyncMock(return_value=SimpleNamespace(mode="initiative", signal="rule")),
        ),
        patch.object(
            lifecycle.skill_injection,
            "match_and_inject",
            new=AsyncMock(return_value=""),
        ),
        patch.object(
            lifecycle.memory_retrieval,
            "retrieve_relevant_history",
            new=AsyncMock(return_value=""),
        ),
        patch.object(
            lifecycle.persona_gate, "apply_prompt_fragments", return_value=""
        ),
    ):
        callback = lifecycle.before_agent(agent)
        ctx = _make_callback_context()
        result = await callback(ctx)

    assert result is None
    errors = ctx.state.get(lifecycle._RUNTIME_CALLBACK_ERRORS_KEY) or []
    assert any("bad contract" in e for e in errors)
    assert any("InitiativeContractError" in e for e in errors)


@pytest.mark.asyncio
async def test_before_agent_generic_exception_is_isolated(agent, caplog):
    """Task 43: a generic exception in any submodule must be caught,
    logged, and recorded on session state — not raised."""

    with (
        patch.object(
            lifecycle.persona_gate,
            "load_persona_policy",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch.object(
            lifecycle.task_router,
            "classify",
            new=AsyncMock(side_effect=RuntimeError("classifier exploded")),
        ),
        patch.object(
            lifecycle.skill_injection,
            "match_and_inject",
            new=AsyncMock(return_value=""),
        ),
        patch.object(
            lifecycle.memory_retrieval,
            "retrieve_relevant_history",
            new=AsyncMock(return_value=""),
        ),
        patch.object(
            lifecycle.persona_gate, "apply_prompt_fragments", return_value=""
        ),
    ):
        callback = lifecycle.before_agent(agent)
        ctx = _make_callback_context()
        # Must not raise.
        result = await callback(ctx)

    assert result is None
    errors = ctx.state.get(lifecycle._RUNTIME_CALLBACK_ERRORS_KEY) or []
    assert any("classifier exploded" in e for e in errors)
    # When the classifier fails the lifecycle still defaults the mode.
    assert ctx.state[lifecycle._RUNTIME_CLASSIFIER_MODE_KEY] == "direct"


# ---------------------------------------------------------------------------
# before_tool — Tasks 31, 32, 33, 34, 43
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_before_tool_allows_call_when_persona_passes(agent):
    """Persona allows + threshold passes + no research gate -> returns None."""

    policy = MagicMock(name="PersonaPolicy")
    tool_ctx = _make_tool_context(state={lifecycle._RUNTIME_PERSONA_POLICY_KEY: policy})

    with (
        patch.object(lifecycle.persona_gate, "check_tool_allowed"),
        patch.object(
            lifecycle.persona_gate,
            "check_action_threshold",
            new=AsyncMock(return_value=None),
        ),
        patch.object(lifecycle.research_gate, "is_open", new=AsyncMock(return_value=False)),
    ):
        callback = lifecycle.before_tool(agent)
        result = await callback(_make_tool("safe_tool"), {}, tool_ctx)

    assert result is None


@pytest.mark.asyncio
async def test_before_tool_persona_deny_records_violation_and_raises(agent):
    """A PersonaPolicyError from check_tool_allowed records a violation and
    propagates so the agent surface can render a refusal."""

    tool_ctx = _make_tool_context()
    record_violation = MagicMock()

    with (
        patch.object(
            lifecycle.persona_gate,
            "check_tool_allowed",
            side_effect=PersonaPolicyError("denied"),
        ),
        patch.object(lifecycle.persona_gate, "record_violation", record_violation),
    ):
        callback = lifecycle.before_tool(agent)
        with pytest.raises(PersonaPolicyError):
            await callback(_make_tool("bad_tool"), {}, tool_ctx)

    # record_violation was called with kind="tool_denied" and the offending tool id.
    record_violation.assert_called_once()
    call_args = record_violation.call_args
    assert call_args.args[1] == "tool_denied"
    assert call_args.args[3] == "bad_tool"
    # Violations list seeded onto state.
    assert lifecycle._RUNTIME_VIOLATIONS_KEY in tool_ctx.state


@pytest.mark.asyncio
async def test_before_tool_threshold_exceeded_without_token_refuses(agent):
    """check_action_threshold returning a 'required' hint without a token on
    state OR args triggers PersonaPolicyError via _verify_approval_token."""

    tool_ctx = _make_tool_context()
    threshold_hint = {"required": True, "ticket": "TICKET-1"}

    with (
        patch.object(lifecycle.persona_gate, "check_tool_allowed"),
        patch.object(
            lifecycle.persona_gate,
            "check_action_threshold",
            new=AsyncMock(return_value=threshold_hint),
        ),
        patch.object(lifecycle.persona_gate, "record_violation", MagicMock()),
    ):
        callback = lifecycle.before_tool(agent)
        with pytest.raises(PersonaPolicyError):
            await callback(_make_tool("stripe_charge"), {"amount_usd": 9999}, tool_ctx)


@pytest.mark.asyncio
async def test_before_tool_research_gate_blocks_non_research_tool(agent):
    """Research gate is open + tool not in RESEARCH_TOOL_IDS -> ResearchGateError."""

    contract_id = uuid4()
    tool_ctx = _make_tool_context(state={lifecycle._RUNTIME_CONTRACT_ID_KEY: contract_id})

    with (
        patch.object(lifecycle.persona_gate, "check_tool_allowed"),
        patch.object(
            lifecycle.persona_gate,
            "check_action_threshold",
            new=AsyncMock(return_value=None),
        ),
        patch.object(lifecycle.research_gate, "is_open", new=AsyncMock(return_value=True)),
        # Force production-style fallback by replacing the attribute with the frozenset.
        patch.object(
            lifecycle.research_gate,
            "RESEARCH_TOOL_IDS",
            frozenset({"deep_research", "tavily_search"}),
        ),
        patch.object(lifecycle.persona_gate, "record_violation", MagicMock()),
    ):
        # Delete is_research_tool if present so the code falls back to the frozenset.
        if hasattr(lifecycle.research_gate, "is_research_tool"):
            with patch.object(lifecycle.research_gate, "is_research_tool", create=True, new=None):
                callback = lifecycle.before_tool(agent)
                with pytest.raises(ResearchGateError):
                    await callback(_make_tool("send_email"), {}, tool_ctx)
        else:
            callback = lifecycle.before_tool(agent)
            with pytest.raises(ResearchGateError):
                await callback(_make_tool("send_email"), {}, tool_ctx)


@pytest.mark.asyncio
async def test_before_tool_research_gate_allows_research_tool(agent):
    """Research gate is open + tool IS in RESEARCH_TOOL_IDS -> returns None."""

    contract_id = uuid4()
    tool_ctx = _make_tool_context(state={lifecycle._RUNTIME_CONTRACT_ID_KEY: contract_id})

    with (
        patch.object(lifecycle.persona_gate, "check_tool_allowed"),
        patch.object(
            lifecycle.persona_gate,
            "check_action_threshold",
            new=AsyncMock(return_value=None),
        ),
        patch.object(lifecycle.research_gate, "is_open", new=AsyncMock(return_value=True)),
        patch.object(
            lifecycle.research_gate,
            "RESEARCH_TOOL_IDS",
            frozenset({"deep_research", "tavily_search"}),
        ),
    ):
        callback = lifecycle.before_tool(agent)
        result = await callback(_make_tool("deep_research"), {}, tool_ctx)

    assert result is None


@pytest.mark.asyncio
async def test_before_tool_approval_token_honored(agent):
    """When threshold returns a 'required' ticket AND tool_context state
    carries a matching approval_token, _verify_approval_token is invoked."""

    tool_ctx = _make_tool_context(
        state={"approval_token::stripe_charge": "tok-abc"}
    )
    threshold_hint = {"required": True, "ticket": "TICKET-1"}

    with (
        patch.object(lifecycle.persona_gate, "check_tool_allowed"),
        patch.object(
            lifecycle.persona_gate,
            "check_action_threshold",
            new=AsyncMock(return_value=threshold_hint),
        ),
        patch.object(
            lifecycle,
            "_verify_approval_token",
            new=AsyncMock(return_value=None),
        ) as verify,
        patch.object(lifecycle.research_gate, "is_open", new=AsyncMock(return_value=False)),
    ):
        callback = lifecycle.before_tool(agent)
        result = await callback(_make_tool("stripe_charge"), {}, tool_ctx)

    assert result is None
    verify.assert_called_once()
    assert verify.call_args.kwargs["token"] == "tok-abc"
    assert verify.call_args.kwargs["tool_id"] == "stripe_charge"


@pytest.mark.asyncio
async def test_before_tool_generic_exception_isolated(agent):
    """Task 43: a non-policy exception from a gate must NOT bubble out;
    the tool proceeds and the failure is logged onto state."""

    tool_ctx = _make_tool_context()

    with (
        patch.object(
            lifecycle.persona_gate,
            "check_tool_allowed",
            side_effect=RuntimeError("supabase outage"),
        ),
        patch.object(
            lifecycle.persona_gate,
            "check_action_threshold",
            new=AsyncMock(return_value=None),
        ),
        patch.object(lifecycle.research_gate, "is_open", new=AsyncMock(return_value=False)),
    ):
        callback = lifecycle.before_tool(agent)
        result = await callback(_make_tool("safe_tool"), {}, tool_ctx)

    assert result is None
    errors = tool_ctx.state.get(lifecycle._RUNTIME_CALLBACK_ERRORS_KEY) or []
    assert any("supabase outage" in e for e in errors)


# ---------------------------------------------------------------------------
# after_tool — Task 35, 43
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_after_tool_records_research_result(agent):
    """A research tool + open contract -> record_tool_result called with
    contract_id, tool_id, and the raw response."""

    contract_id = uuid4()
    tool_ctx = _make_tool_context(state={lifecycle._RUNTIME_CONTRACT_ID_KEY: contract_id})
    response = {"summary": "x", "sources": []}

    with (
        patch.object(
            lifecycle.research_gate,
            "RESEARCH_TOOL_IDS",
            frozenset({"deep_research"}),
        ),
        patch.object(
            lifecycle.research_gate,
            "record_tool_result",
            new=AsyncMock(return_value=None),
        ) as record,
        patch.object(
            lifecycle.research_gate,
            "check_coverage",
            new=AsyncMock(return_value=None),
        ),
    ):
        callback = lifecycle.after_tool(agent)
        await callback(_make_tool("deep_research"), {}, tool_ctx, response)

    record.assert_called_once()
    kw = record.call_args.kwargs
    assert kw["contract_id"] == contract_id
    assert kw["tool_id"] == "deep_research"
    assert kw["result"] == response


@pytest.mark.asyncio
async def test_after_tool_closes_gate_when_coverage_complete(agent):
    """When check_coverage returns a ResearchResult, close_gate is called
    with the same contract_id and the coverage result."""

    contract_id = uuid4()
    tool_ctx = _make_tool_context(state={lifecycle._RUNTIME_CONTRACT_ID_KEY: contract_id})
    coverage = MagicMock(name="ResearchResult")

    with (
        patch.object(
            lifecycle.research_gate,
            "RESEARCH_TOOL_IDS",
            frozenset({"deep_research"}),
        ),
        patch.object(
            lifecycle.research_gate,
            "record_tool_result",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            lifecycle.research_gate,
            "check_coverage",
            new=AsyncMock(return_value=coverage),
        ),
        patch.object(
            lifecycle.research_gate,
            "close_gate",
            new=AsyncMock(return_value=None),
        ) as close,
    ):
        callback = lifecycle.after_tool(agent)
        await callback(_make_tool("deep_research"), {}, tool_ctx, {})

    close.assert_called_once()
    kw = close.call_args.kwargs
    assert kw["contract_id"] == contract_id
    assert kw["result"] is coverage
    assert tool_ctx.state[lifecycle._RUNTIME_RESEARCH_RESULT_KEY] is coverage


@pytest.mark.asyncio
async def test_after_tool_publication_module_none_is_noop(agent):
    """When ``publication is None`` (Section D not yet shipped) after_tool
    must still run cleanly without error."""

    tool_ctx = _make_tool_context()

    with patch.object(lifecycle, "publication", None):
        callback = lifecycle.after_tool(agent)
        await callback(_make_tool("anything"), {}, tool_ctx, {"ok": True})

    # State has no failures recorded.
    assert tool_ctx.state.get(lifecycle._RUNTIME_TOOL_FAILURES_KEY) is None
    assert tool_ctx.state.get(lifecycle._RUNTIME_CALLBACK_ERRORS_KEY) is None


@pytest.mark.asyncio
async def test_after_tool_logs_tool_failure_to_state(agent):
    """A tool_response with ``error`` is appended to the per-session
    failures buffer for retry book-keeping."""

    tool_ctx = _make_tool_context()
    bad_response = {"error": "rate-limited", "code": 429}

    with patch.object(lifecycle, "publication", None):
        callback = lifecycle.after_tool(agent)
        await callback(
            _make_tool("send_email"),
            {"to": "x@y.com"},
            tool_ctx,
            bad_response,
        )

    failures = tool_ctx.state.get(lifecycle._RUNTIME_TOOL_FAILURES_KEY) or []
    assert len(failures) == 1
    assert failures[0]["tool_id"] == "send_email"
    assert failures[0]["error"] == "rate-limited"
    assert failures[0]["args"] == {"to": "x@y.com"}


@pytest.mark.asyncio
async def test_after_tool_generic_exception_isolated(agent):
    """Task 43: an exception from record_tool_result must not propagate."""

    contract_id = uuid4()
    tool_ctx = _make_tool_context(state={lifecycle._RUNTIME_CONTRACT_ID_KEY: contract_id})

    with (
        patch.object(
            lifecycle.research_gate,
            "RESEARCH_TOOL_IDS",
            frozenset({"deep_research"}),
        ),
        patch.object(
            lifecycle.research_gate,
            "record_tool_result",
            new=AsyncMock(side_effect=RuntimeError("vault down")),
        ),
        patch.object(
            lifecycle.research_gate,
            "check_coverage",
            new=AsyncMock(return_value=None),
        ),
    ):
        callback = lifecycle.after_tool(agent)
        # Must not raise.
        result = await callback(_make_tool("deep_research"), {}, tool_ctx, {})

    assert result is None
    errors = tool_ctx.state.get(lifecycle._RUNTIME_CALLBACK_ERRORS_KEY) or []
    assert any("vault down" in e for e in errors)


# ---------------------------------------------------------------------------
# after_agent — Tasks 36, 37, 38, 43
# ---------------------------------------------------------------------------


def _fake_artifact() -> SimpleNamespace:
    return SimpleNamespace(
        kind="report",
        ref="s3://x",
        summary="report",
        payload=None,
    )


def _fake_contract() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        source="initiative_step",
        goal="g",
        todo_items=[],
        success_criteria=[],
        owners=[],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="execution",
        sibling_steps=[],
    )


@pytest.mark.asyncio
async def test_after_agent_audit_runs_when_artifacts_present(agent):
    """artifacts on state -> audit_against_contract + persist_audit_report +
    attach_audit_summary_to_evidence all called in order."""

    contract = _fake_contract()
    audit_report = MagicMock(name="AuditReport")
    state = {
        lifecycle._RUNTIME_CONTRACT_KEY: contract,
        lifecycle._RUNTIME_ARTIFACTS_KEY: [_fake_artifact()],
        lifecycle._RUNTIME_CLASSIFIER_MODE_KEY: "initiative",
    }

    with (
        patch.object(
            lifecycle.audit,
            "audit_against_contract",
            new=AsyncMock(return_value=audit_report),
        ) as audit_call,
        patch.object(
            lifecycle.audit,
            "persist_audit_report",
            new=AsyncMock(return_value=uuid4()),
        ) as persist_call,
        patch.object(
            lifecycle.audit,
            "attach_audit_summary_to_evidence",
            new=AsyncMock(return_value=None),
        ) as attach_call,
        patch.object(
            lifecycle.compaction, "maybe_compact", new=AsyncMock(return_value=None)
        ),
    ):
        callback = lifecycle.after_agent(agent)
        ctx = _make_callback_context(state=state)
        await callback(ctx)

    audit_call.assert_called_once()
    persist_call.assert_called_once()
    attach_call.assert_called_once()
    # persist was called with the contract id
    assert persist_call.call_args.kwargs["task_contract_id"] == contract.id


@pytest.mark.asyncio
async def test_after_agent_audit_skipped_without_artifacts(agent):
    """No artifacts on state -> audit chain MUST be skipped."""

    state = {lifecycle._RUNTIME_CLASSIFIER_MODE_KEY: "direct"}

    with (
        patch.object(
            lifecycle.audit, "audit_against_contract", new=AsyncMock()
        ) as audit_call,
        patch.object(
            lifecycle.compaction, "maybe_compact", new=AsyncMock(return_value=None)
        ),
    ):
        callback = lifecycle.after_agent(agent)
        ctx = _make_callback_context(state=state)
        await callback(ctx)

    audit_call.assert_not_called()


@pytest.mark.asyncio
async def test_after_agent_compaction_always_runs_and_caches_summary(agent):
    """compaction.maybe_compact is invoked unconditionally; when it returns
    a result the summary is cached on session state for the next turn."""

    compaction_result = SimpleNamespace(
        summary="compacted-summary",
        dropped_event_count=8,
        kept_event_count=12,
    )

    with patch.object(
        lifecycle.compaction,
        "maybe_compact",
        new=AsyncMock(return_value=compaction_result),
    ) as compact:
        callback = lifecycle.after_agent(agent)
        ctx = _make_callback_context()
        await callback(ctx)

    compact.assert_called_once()
    assert ctx.state[lifecycle._RUNTIME_COMPACTION_SUMMARY_KEY] == "compacted-summary"


@pytest.mark.asyncio
async def test_after_agent_records_pending_handoff(agent):
    """A staged handoff packet + initiative context -> record_handoff."""

    packet_dict = {
        "intent": "send to specialist",
        "evidence": [],
        "constraints": [],
        "expected_output_shape": "text",
        "source_agent": "executive",
        "target_agent": "financial",
        "correlation_id": None,
    }
    initiative_id = uuid4()
    state = {
        lifecycle._RUNTIME_PENDING_HANDOFF_KEY: packet_dict,
        lifecycle._RUNTIME_INITIATIVE_ID_KEY: initiative_id,
        lifecycle._RUNTIME_INITIATIVE_PHASE_KEY: "execution",
        lifecycle._RUNTIME_CLASSIFIER_MODE_KEY: "initiative",
    }

    with (
        patch.object(
            lifecycle.compaction, "maybe_compact", new=AsyncMock(return_value=None)
        ),
        patch.object(
            lifecycle.handoff,
            "record_handoff",
            new=AsyncMock(return_value="packet-1"),
        ) as record,
    ):
        callback = lifecycle.after_agent(agent)
        ctx = _make_callback_context(state=state)
        await callback(ctx)

    record.assert_called_once()
    kw = record.call_args.kwargs
    assert kw["initiative_id"] == initiative_id
    assert kw["phase"] == "execution"
    # The dict was coerced into a HandoffPacket model.
    from app.agents.handoff_packet import HandoffPacket

    assert isinstance(kw["packet"], HandoffPacket)


@pytest.mark.asyncio
async def test_after_agent_generic_exception_isolated(agent):
    """Task 43: a compaction exception must not bubble out — it lands in
    the per-session callback-errors bucket instead."""

    with patch.object(
        lifecycle.compaction,
        "maybe_compact",
        new=AsyncMock(side_effect=RuntimeError("compactor down")),
    ):
        callback = lifecycle.after_agent(agent)
        ctx = _make_callback_context()
        # Must not raise.
        result = await callback(ctx)

    assert result is None
    errors = ctx.state.get(lifecycle._RUNTIME_CALLBACK_ERRORS_KEY) or []
    assert any("compactor down" in e for e in errors)


# ---------------------------------------------------------------------------
# apply_injected_blocks helper
# ---------------------------------------------------------------------------


def test_apply_injected_blocks_prepends_when_present():
    state = {lifecycle._RUNTIME_BLOCKS_KEY: "## Skills\nbody"}
    out = lifecycle.apply_injected_blocks(state, "Base instruction")
    assert out.startswith("## Skills")
    assert out.endswith("Base instruction")


def test_apply_injected_blocks_passthrough_when_absent():
    assert lifecycle.apply_injected_blocks({}, "Base") == "Base"
    # Defensive: non-dict state returns instruction unchanged.
    assert lifecycle.apply_injected_blocks("not-a-dict", "Base") == "Base"  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Factory shape (smoke tests retained from the deleted stubs file)
# ---------------------------------------------------------------------------


def test_factories_return_callables(agent):
    assert callable(lifecycle.before_agent(agent))
    assert callable(lifecycle.before_tool(agent))
    assert callable(lifecycle.after_tool(agent))
    assert callable(lifecycle.after_agent(agent))


def test_factories_name_includes_agent_id(agent):
    assert lifecycle.before_agent(agent).__name__ == "before_agent::financial"
    assert lifecycle.before_tool(agent).__name__ == "before_tool::financial"
    assert lifecycle.after_tool(agent).__name__ == "after_tool::financial"
    assert lifecycle.after_agent(agent).__name__ == "after_agent::financial"
