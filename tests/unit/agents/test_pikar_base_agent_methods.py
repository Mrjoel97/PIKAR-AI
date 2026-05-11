# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""PikarBaseAgent — research / audit / run_step method wiring.

These are the three method bodies that
``app.agents.runtime.step_runtime.execute_task`` invokes on a real agent.
Tests mock every external module (research_gate, audit module, ADK
invocation) so the assertions focus on structural wiring, not LLM output.

Imports of the production runtime modules happen INSIDE test functions
(or fixtures) so they pick up the conftest-level ADK / google.genai
mock surface — matching the pattern in
``tests/unit/agents/test_base_agent_skeleton.py``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

# The conftest at ``tests/unit/conftest.py`` wires up MagicMock stand-ins
# for ``google.adk`` and ``google.genai`` before any test imports run.
# Per-test ``sys.modules.setdefault`` of stub MagicMocks (as
# test_base_agent_skeleton.py does) collides with the conftest replacement
# on partial test runs — so we lean on the conftest mocks exclusively
# and import production modules directly inside test bodies for parity
# with ``tests/unit/agents/runtime/test_research_gate.py``.


# ---------------------------------------------------------------------------
# Helpers (kept module-level — no runtime imports here).
# ---------------------------------------------------------------------------


def _ops_yaml(tmp_path: Path) -> Path:
    path = tmp_path / "operations.yaml"
    path.write_text(
        "agent_id: financial\nresearch:\n  max_iterations: 2\n",
        encoding="utf-8",
    )
    return path


def _instructions_md(tmp_path: Path) -> Path:
    path = tmp_path / "instructions.md"
    path.write_text("You are the Financial Analysis Agent.", encoding="utf-8")
    return path


class _FakeToolsManifest:
    """Standin for ``app.agents.runtime.tools_manifest.ToolsManifest``."""

    def __init__(self, tool_ids: list[str] | None = None) -> None:
        self.tool_ids = list(tool_ids or [])

    def resolve(self) -> list:
        return []


def _make_contract(*, todo_items=None):
    from app.agents.runtime.types import TaskContract

    return TaskContract(
        id=uuid4(),
        source="initiative_step",
        goal="Forecast Q3 revenue",
        todo_items=todo_items or [],
        success_criteria=["criterion-a"],
        owners=[],
        evidence_required=[],
        initiative_id=uuid4(),
        initiative_phase="validation",
        sibling_steps=[],
    )


def _make_todo():
    from app.agents.runtime.types import TodoItem

    return TodoItem(
        id=uuid4(),
        title="Draft the forecast",
        description="Pull last 12 months of revenue and project Q3.",
        status="pending",
        evidence=[],
        sort_order=0,
    )


def _make_complete_result():
    from app.agents.runtime.types import ResearchResult

    return ResearchResult(
        summary="all good",
        sources=[],
        contradictions=[],
        coverage_assessment="complete",
        missing_information=[],
    )


def _make_pass_audit():
    from app.agents.runtime.types import AuditReport

    return AuditReport(
        overall_status="pass",
        per_item=[],
        per_criterion=[],
        gaps=[],
        policy_violations=[],
        recoverable=True,
        next_action="submit",
    )


def _build_agent(tmp_path: Path, *, tool_ids=None):
    from app.agents.base_agent import PikarBaseAgent
    from app.skills.registry import AgentID

    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        return PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_instructions_md(tmp_path),
            tools_manifest=_FakeToolsManifest(tool_ids=tool_ids),
            ops_config_path=_ops_yaml(tmp_path),
            user_id=uuid4(),
            persona_id="founder",
        )


# ---------------------------------------------------------------------------
# research()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_research_opens_and_closes_gate_on_complete_coverage(tmp_path):
    """check_coverage returns a complete ResearchResult on first poll."""
    from app.agents.runtime import research_gate

    agent = _build_agent(tmp_path, tool_ids=["quick_research"])
    contract = _make_contract()
    complete_result = _make_complete_result()

    open_gate = AsyncMock(return_value=uuid4())
    record_tool_result = AsyncMock()
    check_coverage = AsyncMock(return_value=complete_result)
    close_gate = AsyncMock()

    with (
        patch.object(research_gate, "open_gate", open_gate),
        patch.object(research_gate, "record_tool_result", record_tool_result),
        patch.object(research_gate, "check_coverage", check_coverage),
        patch.object(research_gate, "close_gate", close_gate),
    ):
        result = await agent.research(contract=contract)

    assert result is complete_result
    open_gate.assert_awaited_once()
    record_tool_result.assert_awaited()  # at least one tool call recorded
    check_coverage.assert_awaited()
    close_gate.assert_awaited_once()
    close_kwargs = close_gate.await_args.kwargs
    assert close_kwargs["result"] is complete_result

    # And the result is cached on the agent for the audit phase to reuse.
    assert agent._last_research is complete_result


@pytest.mark.asyncio
async def test_research_returns_partial_fallback_on_gate_error(tmp_path):
    """check_coverage raises ResearchGateError when budget exhausted; the
    method must surface a partial-coverage fallback rather than bubble.
    """
    from app.agents.runtime import research_gate
    from app.agents.runtime.types import ResearchGateError, ResearchResult

    agent = _build_agent(tmp_path, tool_ids=["quick_research"])
    contract = _make_contract()

    open_gate = AsyncMock(return_value=uuid4())
    record_tool_result = AsyncMock()
    check_coverage = AsyncMock(side_effect=ResearchGateError("budget exhausted"))
    close_gate = AsyncMock()

    with (
        patch.object(research_gate, "open_gate", open_gate),
        patch.object(research_gate, "record_tool_result", record_tool_result),
        patch.object(research_gate, "check_coverage", check_coverage),
        patch.object(research_gate, "close_gate", close_gate),
    ):
        result = await agent.research(contract=contract)

    assert isinstance(result, ResearchResult)
    assert result.coverage_assessment == "partial"
    assert result.missing_information == list(contract.success_criteria)
    # The gate is still closed with the fallback result.
    close_gate.assert_awaited_once()


@pytest.mark.asyncio
async def test_research_loop_exhausted_returns_partial_when_check_keeps_returning_none(
    tmp_path,
):
    """If check_coverage keeps returning None for every iteration, the
    method exits the loop and falls back to partial coverage.
    """
    from app.agents.runtime import research_gate

    agent = _build_agent(tmp_path, tool_ids=["quick_research"])
    contract = _make_contract()
    # ops.research.max_iterations = 2 in _ops_yaml; check returns None twice.
    check_coverage = AsyncMock(return_value=None)

    with (
        patch.object(research_gate, "open_gate", AsyncMock(return_value=uuid4())),
        patch.object(research_gate, "record_tool_result", AsyncMock()),
        patch.object(research_gate, "check_coverage", check_coverage),
        patch.object(research_gate, "close_gate", AsyncMock()),
    ):
        result = await agent.research(contract=contract)

    assert result.coverage_assessment == "partial"
    # check_coverage was polled max_iterations times (2).
    assert check_coverage.await_count == 2


@pytest.mark.asyncio
async def test_research_falls_back_to_quick_research_when_no_research_tools_in_manifest(
    tmp_path,
):
    """An agent whose manifest has no RESEARCH_TOOL_IDS still gets one shot
    at coverage via the synthetic ``quick_research`` placeholder.
    """
    from app.agents.runtime import research_gate

    agent = _build_agent(tmp_path, tool_ids=["not_a_research_tool"])
    contract = _make_contract()

    record_tool_result = AsyncMock()
    with (
        patch.object(research_gate, "open_gate", AsyncMock(return_value=uuid4())),
        patch.object(research_gate, "record_tool_result", record_tool_result),
        patch.object(
            research_gate,
            "check_coverage",
            AsyncMock(return_value=_make_complete_result()),
        ),
        patch.object(research_gate, "close_gate", AsyncMock()),
    ):
        await agent.research(contract=contract)

    # At least one record_tool_result call, and that tool_id is in the
    # allow-set.
    assert record_tool_result.await_count >= 1
    used_tool_ids = {c.kwargs["tool_id"] for c in record_tool_result.await_args_list}
    assert "quick_research" in used_tool_ids


# ---------------------------------------------------------------------------
# audit()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_delegates_to_audit_against_contract_with_cached_research(
    tmp_path,
):
    """If ``self._last_research`` is set, the audit reuses it. Audit module
    is mocked — we assert the arguments only.
    """
    import app.agents.runtime.audit as audit_module
    from app.agents.runtime.types import Artifact

    agent = _build_agent(tmp_path)
    contract = _make_contract()
    cached = _make_complete_result()
    object.__setattr__(agent, "_last_research", cached)
    artifacts = [
        Artifact(kind="doc", ref="r1", summary="s", payload=None),
    ]
    expected_report = _make_pass_audit()

    audit_mock = AsyncMock(return_value=expected_report)
    with patch.object(audit_module, "audit_against_contract", audit_mock):
        report = await agent.audit(contract=contract, artifacts=artifacts)

    assert report is expected_report
    audit_mock.assert_awaited_once()
    kwargs = audit_mock.await_args.kwargs
    assert kwargs["contract"] is contract
    assert kwargs["artifacts"] is artifacts
    assert kwargs["research"] is cached
    assert kwargs["ops"] is agent.ops


@pytest.mark.asyncio
async def test_audit_supplies_empty_research_when_not_cached(tmp_path):
    """When no research has been run, audit supplies a minimal empty
    ResearchResult so :func:`audit_against_contract` still has a valid arg.
    """
    import app.agents.runtime.audit as audit_module
    from app.agents.runtime.types import ResearchResult

    agent = _build_agent(tmp_path)
    contract = _make_contract()
    artifacts: list = []

    audit_mock = AsyncMock(return_value=_make_pass_audit())
    with patch.object(audit_module, "audit_against_contract", audit_mock):
        await agent.audit(contract=contract, artifacts=artifacts)

    kwargs = audit_mock.await_args.kwargs
    supplied = kwargs["research"]
    assert isinstance(supplied, ResearchResult)
    assert supplied.summary == ""
    assert supplied.coverage_assessment == "complete"


@pytest.mark.asyncio
async def test_audit_handles_non_research_result_in_cache(tmp_path):
    """If _last_research somehow holds a non-ResearchResult value, the
    method must coerce to the empty fallback rather than passing junk
    into the audit module.
    """
    import app.agents.runtime.audit as audit_module
    from app.agents.runtime.types import ResearchResult

    agent = _build_agent(tmp_path)
    object.__setattr__(agent, "_last_research", "not a research result")
    contract = _make_contract()

    audit_mock = AsyncMock(return_value=_make_pass_audit())
    with patch.object(audit_module, "audit_against_contract", audit_mock):
        await agent.audit(contract=contract, artifacts=[])

    supplied = audit_mock.await_args.kwargs["research"]
    assert isinstance(supplied, ResearchResult)
    assert supplied.summary == ""


# ---------------------------------------------------------------------------
# run_step()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_step_returns_artifact_with_research_context(tmp_path):
    from app.agents.runtime.types import Artifact

    agent = _build_agent(tmp_path)
    item = _make_todo()
    research = _make_complete_result()

    artifact = await agent.run_step(item=item, research=research)

    assert isinstance(artifact, Artifact)
    assert artifact.kind == "doc"
    assert str(item.id) in artifact.ref
    # The summary echoes the todo title.
    assert item.title in artifact.summary
    # Payload should be non-None (placeholder carries prompt preview etc.).
    assert artifact.payload is not None


@pytest.mark.asyncio
async def test_run_step_handles_none_research(tmp_path):
    """The retry path in step_runtime passes ``research=None``; the method
    must tolerate that and still return an Artifact.
    """
    from app.agents.runtime.types import Artifact

    agent = _build_agent(tmp_path)
    item = _make_todo()

    artifact = await agent.run_step(item=item, research=None)

    assert isinstance(artifact, Artifact)
    assert "N/A" in (artifact.payload or {}).get("prompt_preview", "")


# ---------------------------------------------------------------------------
# Surface checks.
# ---------------------------------------------------------------------------


def test_methods_exist_on_class():
    from app.agents.base_agent import PikarBaseAgent

    for name in ("research", "audit", "run_step"):
        method = getattr(PikarBaseAgent, name, None)
        assert callable(method), f"missing method: {name}"


def test_step_summary_is_importable_from_types():
    # Defensive: step_runtime imports StepSummary, ensure it stays exported.
    from app.agents.runtime.types import StepSummary

    assert StepSummary is not None
