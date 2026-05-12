# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Test: refactored create_hr_agent returns a PikarBaseAgent (W4 migration)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from app.agents.base_agent import PikarBaseAgent
from app.agents.hr.agent import create_hr_agent
from app.skills.registry import AgentID


def test_create_hr_agent_returns_pikar_base_agent():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_hr_agent(user_id=uuid4(), persona_id="startup")
    assert isinstance(agent, PikarBaseAgent)
    assert agent.agent_id == AgentID.HR


def test_agent_module_size_under_120_lines():
    """The refactored module should be small — the spec calls for ~30 lines
    of factory body; allow headroom for docstring + imports."""
    body = (
        Path(__file__).resolve().parents[4]
        / "app"
        / "agents"
        / "hr"
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
        agent = create_hr_agent(user_id=uuid4(), persona_id="startup")
    assert agent.ops.agent_id == "hr"
    assert agent.ops.approval.required_for_external_send is True


def test_legacy_positional_call_still_works():
    """Workflow callers in app/workflows/*.py still call positionally."""
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_hr_agent("_fb", persona="startup")
    assert isinstance(agent, PikarBaseAgent)
    assert agent.persona_id == "startup"


def test_legacy_no_arg_call_still_works():
    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = create_hr_agent()
    assert isinstance(agent, PikarBaseAgent)
    assert agent.persona_id == "default"
