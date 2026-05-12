# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Test: refactored create_customer_support_agent returns a PikarBaseAgent."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app.agents.base_agent import PikarBaseAgent
from app.agents.customer_support.agent import create_customer_support_agent
from app.skills.registry import AgentID


def test_create_customer_support_agent_returns_pikar_base_agent():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_customer_support_agent(user_id=uuid4(), persona_id="startup")
    assert isinstance(agent, PikarBaseAgent)
    assert agent.agent_id == AgentID.SUPP


def test_agent_module_size_under_120_lines():
    body = (
        Path(__file__).resolve().parents[4]
        / "app"
        / "agents"
        / "customer_support"
        / "agent.py"
    ).read_text(encoding="utf-8")
    code_lines = [
        line
        for line in body.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert len(code_lines) < 120, (
        f"agent.py grew to {len(code_lines)} non-comment lines; refactor it back"
    )


def test_agent_carries_ops_config():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_customer_support_agent(user_id=uuid4(), persona_id="startup")
    assert agent.ops.agent_id == "customer_support"
    assert agent.ops.approval.required_for_external_send is True


def test_legacy_positional_call_still_works():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_customer_support_agent("_fb", persona="startup")
    assert isinstance(agent, PikarBaseAgent)
    assert agent.persona_id == "startup"


def test_legacy_no_arg_call_still_works():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_customer_support_agent()
    assert isinstance(agent, PikarBaseAgent)
    assert agent.persona_id == "default"
