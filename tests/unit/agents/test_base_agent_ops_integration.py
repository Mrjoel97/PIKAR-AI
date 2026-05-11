# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""End-to-end smoke for Section A.

A constructed PikarBaseAgent exposes a fully-validated OperationsConfig,
the lifecycle callbacks are wired (stubs are safely callable), and the
NotImplementedError stubs reference the correct downstream section.
This is the final gate before Section B starts adding logic.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())

FIN_YAML = """\
agent_id: financial
model:
  primary: gemini-2.5-pro
  fallback: gemini-2.5-flash
research:
  max_iterations: 3
  required_source_min: 3
skills:
  allowed_ids: ["finance:*"]
  injection:
    top_k: 5
    similarity_floor: 0.65
initiative:
  phases_owned: ["validation", "build"]
  can_advance_phase: true
  can_close: false
"""


class _Manifest:
    def resolve(self):
        return []


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_pikar_base_agent_exposes_validated_ops(tmp_path):
    from app.agents.base_agent import PikarBaseAgent
    from app.agents.runtime.operations_config import OperationsConfig
    from app.skills.registry import AgentID

    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_write(tmp_path, "instructions.md", "Hi."),
            tools_manifest=_Manifest(),
            ops_config_path=_write(tmp_path, "operations.yaml", FIN_YAML),
            user_id=uuid4(),
            persona_id="founder",
        )

    assert isinstance(agent.ops, OperationsConfig)
    assert agent.ops.agent_id == "financial"
    assert agent.ops.initiative.phases_owned == ["validation", "build"]
    assert agent.ops.skills.injection.top_k == 5


def test_pikar_base_agent_lifecycle_callbacks_wired(tmp_path):
    """Section B replaced the stubs with real async callback bodies — verify
    each lifecycle factory wired its async callable into the ADK kwargs."""
    import inspect

    from app.agents.base_agent import PikarBaseAgent
    from app.skills.registry import AgentID

    captured: dict[str, object] = {}

    def fake_parent_init(self, **kwargs):
        captured.update(kwargs)

    with patch(
        "app.agents.base_agent.PikarAgent.__init__",
        fake_parent_init,
    ):
        PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_write(tmp_path, "instructions.md", "Hi."),
            tools_manifest=_Manifest(),
            ops_config_path=_write(tmp_path, "operations.yaml", FIN_YAML),
            user_id=uuid4(),
            persona_id="founder",
        )

    # ADK callback signatures (per google.adk.agents.base_agent):
    #   before_agent_callback(callback_context) -> Content | None
    #   before_tool_callback(tool, args, tool_context) -> dict | None
    #   after_tool_callback(tool, args, tool_context, tool_response) -> dict | None
    #   after_agent_callback(callback_context) -> Content | None
    invocations = {
        "before_agent_callback": (MagicMock(),),
        "before_tool_callback": (MagicMock(), {}, MagicMock()),
        "after_tool_callback": (MagicMock(), {}, MagicMock(), {}),
        "after_agent_callback": (MagicMock(),),
    }
    for key, args in invocations.items():
        cb = captured[key]
        assert callable(cb), f"{key} must be callable"
        # Bodies are async; invoking returns a coroutine. Close it without
        # awaiting so the RuntimeWarning doesn't fire — the per-callback
        # tests in test_lifecycle_bodies.py exercise the real behavior.
        coro = cb(*args)
        assert inspect.iscoroutine(coro), f"{key} must return a coroutine"
        coro.close()
