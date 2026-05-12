# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Test: refactored create_strategic_agent returns a PikarBaseAgent."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from app.agents.base_agent import PikarBaseAgent
from app.agents.strategic.agent import create_strategic_agent
from app.skills.registry import AgentID


def test_create_strategic_agent_returns_pikar_base_agent():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_strategic_agent(user_id=uuid4(), persona_id="startup")
    assert isinstance(agent, PikarBaseAgent)
    assert agent.agent_id == AgentID.STRAT


def test_agent_module_size_under_200_lines():
    """Strategic owns 4 sub-agent factories so it gets a slightly larger
    budget than the single-sub-agent migrations (compliance/sales/etc.)."""
    body = (
        Path(__file__).resolve().parents[4]
        / "app"
        / "agents"
        / "strategic"
        / "agent.py"
    ).read_text(encoding="utf-8")
    code_lines = [
        line
        for line in body.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert len(code_lines) < 200, (
        f"agent.py grew to {len(code_lines)} non-comment lines; refactor it back"
    )


def test_agent_carries_ops_config():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_strategic_agent(user_id=uuid4(), persona_id="startup")
    assert agent.ops.agent_id == "strategic"
    assert agent.ops.approval.required_for_external_send is True
    assert agent.ops.audit.escalate_on_partial is True
    assert agent.ops.initiative.can_advance_phase is True
    assert agent.ops.initiative.can_close is False


def test_legacy_positional_call_still_works():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_strategic_agent("_fb", persona="startup")
    assert isinstance(agent, PikarBaseAgent)
    assert agent.persona_id == "startup"


def test_legacy_no_arg_call_still_works():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_strategic_agent()
    assert isinstance(agent, PikarBaseAgent)


def test_factory_wires_four_sub_agents():
    """The strategic director must wire all four sub-agents:
    BraindumpPipeline, ResearchSuite, KnowledgeVaultAgent, InitiativeOpsAgent."""
    captured: dict[str, Any] = {}

    def _capture(self: Any, **kwargs: Any) -> None:
        if "sub_agents" in kwargs and kwargs["sub_agents"]:
            captured.setdefault("sub_agents", kwargs["sub_agents"])

    with patch("app.agents.base_agent.PikarAgent.__init__", _capture):
        create_strategic_agent(user_id=uuid4(), persona_id="startup")

    subs = captured.get("sub_agents") or []
    assert len(subs) == 4, f"expected 4 sub-agents, got {len(subs)}"

    sub_names = {getattr(s, "name", None) for s in subs}
    # BraindumpPipeline + ResearchSuite are ParallelAgent / SequentialAgent
    # so they expose .name from the ADK base class.
    assert "BraindumpPipeline" in sub_names
    assert "ResearchSuite" in sub_names
    assert any(n and n.startswith("KnowledgeVaultAgent") for n in sub_names)
    assert any(n and n.startswith("InitiativeOpsAgent") for n in sub_names)


def test_factory_creates_fresh_sub_agents_each_call():
    """ADK forbids parent re-assignment, so each factory call must
    instantiate fresh sub-agents."""
    captured: list[Any] = []

    def _capture(self: Any, **kwargs: Any) -> None:
        captured.append(kwargs.get("sub_agents") or [])

    with patch("app.agents.base_agent.PikarAgent.__init__", _capture):
        create_strategic_agent(user_id=uuid4(), persona_id="startup")
        create_strategic_agent(user_id=uuid4(), persona_id="startup")

    assert len(captured) == 2
    first_set, second_set = captured
    # No sub-agent instance is shared across factory calls.
    assert not (set(map(id, first_set)) & set(map(id, second_set)))
