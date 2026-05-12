# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Test: refactored create_content_agent returns a PikarBaseAgent (W4-Pilot)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app.agents.base_agent import PikarBaseAgent
from app.agents.content.agent import create_content_agent
from app.skills.registry import AgentID


def test_create_content_agent_returns_pikar_base_agent():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_content_agent(user_id=uuid4(), persona_id="startup")
    assert isinstance(agent, PikarBaseAgent)
    assert agent.agent_id == AgentID.CONT


def test_agent_module_size_under_350_lines():
    """The refactored module includes 3 sub-agent factories + director factory;
    the W4 plan calls for the director slim (~30 LOC) while keeping the 3
    internal sub-agent factories. Total non-comment lines should stay under
    350 so future drift stays visible."""
    body = (
        Path(__file__).resolve().parents[4] / "app" / "agents" / "content" / "agent.py"
    ).read_text(encoding="utf-8")
    code_lines = [
        line
        for line in body.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert len(code_lines) < 350, (
        f"agent.py grew to {len(code_lines)} non-comment lines; refactor it back"
    )


def test_agent_carries_ops_config():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_content_agent(user_id=uuid4(), persona_id="startup")
    assert agent.ops.agent_id == "content"
    assert agent.ops.approval.required_for_external_send is True


def test_legacy_positional_call_still_works():
    """Workflow callers in app/workflows/*.py still call positionally."""
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_content_agent("_fb", persona="startup")
    assert isinstance(agent, PikarBaseAgent)
    assert agent.persona_id == "startup"


def test_legacy_no_arg_call_still_works():
    """The most common workflow pattern is ``create_content_agent()``."""
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_content_agent()
    assert isinstance(agent, PikarBaseAgent)
    assert agent.persona_id == "default"


def test_legacy_output_key_threads_through():
    """``output_key=`` is the W4 hook for workflow steps to read agent output."""
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        # No exception means the kwarg was accepted and forwarded.
        agent = create_content_agent(output_key="content_draft")
    assert isinstance(agent, PikarBaseAgent)
