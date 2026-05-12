# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Test: refactored create_operations_agent returns a PikarBaseAgent."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from app.agents.base_agent import PikarBaseAgent
from app.agents.operations.agent import create_operations_agent
from app.skills.registry import AgentID


def test_create_operations_agent_returns_pikar_base_agent():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_operations_agent(user_id=uuid4(), persona_id="startup")
    assert isinstance(agent, PikarBaseAgent)
    assert agent.agent_id == AgentID.OPS


def test_agent_module_size_under_180_lines():
    body = (
        Path(__file__).resolve().parents[4]
        / "app"
        / "agents"
        / "operations"
        / "agent.py"
    ).read_text(encoding="utf-8")
    code_lines = [
        line
        for line in body.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert len(code_lines) < 180


def test_agent_carries_ops_config():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_operations_agent(user_id=uuid4(), persona_id="startup")
    assert agent.ops.agent_id == "operations"
    assert agent.ops.approval.required_for_external_send is True


def test_legacy_positional_call_still_works():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_operations_agent("_fb", persona="startup")
    assert isinstance(agent, PikarBaseAgent)


def test_legacy_no_arg_call_still_works():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_operations_agent()
    assert isinstance(agent, PikarBaseAgent)


def test_factory_wires_configuration_sub_agent():
    """The director must wire ConfigurationAgent as a sub_agent."""
    captured: dict[str, Any] = {}

    def _capture(self: Any, **kwargs: Any) -> None:
        if "sub_agents" in kwargs and kwargs["sub_agents"]:
            captured.setdefault("sub_agents", kwargs["sub_agents"])

    with patch("app.agents.base_agent.PikarAgent.__init__", _capture):
        create_operations_agent(user_id=uuid4(), persona_id="startup")

    subs = captured.get("sub_agents") or []
    assert len(subs) == 1, f"expected 1 sub-agent (ConfigurationAgent), got {len(subs)}"
