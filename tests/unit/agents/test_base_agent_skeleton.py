# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""PikarBaseAgent — Section A skeleton only.

Verifies the constructor loads OperationsConfig, persists agent_id /
user_id / persona_id, hooks all four ADK callbacks (factories from
runtime.lifecycle), and exposes the five abstract methods (bodies in B/C/D).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Stub the ADK surface like other unit tests do — see test_agent_memory_callback.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())


def _ops_yaml(tmp_path: Path) -> Path:
    path = tmp_path / "operations.yaml"
    path.write_text("agent_id: financial\n", encoding="utf-8")
    return path


def _instructions_md(tmp_path: Path) -> Path:
    path = tmp_path / "instructions.md"
    path.write_text("You are the Financial Analysis Agent.", encoding="utf-8")
    return path


class _FakeToolsManifest:
    def resolve(self):
        return []


def test_constructor_loads_ops_config_and_persists_identity(tmp_path):
    from app.agents.base_agent import PikarBaseAgent
    from app.skills.registry import AgentID

    uid = uuid4()
    with patch(
        "app.agents.base_agent.PikarAgent.__init__", return_value=None
    ) as parent:
        agent = PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_instructions_md(tmp_path),
            tools_manifest=_FakeToolsManifest(),
            ops_config_path=_ops_yaml(tmp_path),
            user_id=uid,
            persona_id="founder",
        )

    assert agent.agent_id == AgentID.FIN
    assert agent.user_id == uid
    assert agent.persona_id == "founder"
    assert agent.ops.agent_id == "financial"
    assert parent.called


def test_constructor_wires_all_four_lifecycle_callbacks(tmp_path):
    from app.agents import base_agent
    from app.agents.base_agent import PikarBaseAgent
    from app.skills.registry import AgentID

    sentinels = {
        "before_agent": MagicMock(name="ba"),
        "before_tool": MagicMock(name="bt"),
        "after_tool": MagicMock(name="at"),
        "after_agent": MagicMock(name="aa"),
    }
    with (
        patch.object(
            base_agent.lifecycle,
            "before_agent",
            return_value=sentinels["before_agent"],
        ),
        patch.object(
            base_agent.lifecycle,
            "before_tool",
            return_value=sentinels["before_tool"],
        ),
        patch.object(
            base_agent.lifecycle,
            "after_tool",
            return_value=sentinels["after_tool"],
        ),
        patch.object(
            base_agent.lifecycle,
            "after_agent",
            return_value=sentinels["after_agent"],
        ),
        patch(
            "app.agents.base_agent.PikarAgent.__init__", return_value=None
        ) as parent,
    ):
        PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_instructions_md(tmp_path),
            tools_manifest=_FakeToolsManifest(),
            ops_config_path=_ops_yaml(tmp_path),
            user_id=uuid4(),
            persona_id="founder",
        )

    kwargs = parent.call_args.kwargs
    assert kwargs["before_agent_callback"] is sentinels["before_agent"]
    assert kwargs["before_tool_callback"] is sentinels["before_tool"]
    assert kwargs["after_tool_callback"] is sentinels["after_tool"]
    assert kwargs["after_agent_callback"] is sentinels["after_agent"]


def test_constructor_reads_instructions_markdown(tmp_path):
    from app.agents.base_agent import PikarBaseAgent
    from app.skills.registry import AgentID

    with patch(
        "app.agents.base_agent.PikarAgent.__init__", return_value=None
    ) as parent:
        PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_instructions_md(tmp_path),
            tools_manifest=_FakeToolsManifest(),
            ops_config_path=_ops_yaml(tmp_path),
            user_id=uuid4(),
            persona_id="founder",
        )

    instruction = parent.call_args.kwargs["instruction"]
    assert "Financial Analysis Agent" in instruction


def test_constructor_rejects_empty_instructions(tmp_path):
    """Empty/missing instructions_path -> ValueError."""
    import pytest

    from app.agents.base_agent import PikarBaseAgent
    from app.skills.registry import AgentID

    empty_md = tmp_path / "empty.md"
    empty_md.write_text("   \n\n", encoding="utf-8")

    with (
        patch("app.agents.base_agent.PikarAgent.__init__", return_value=None),
        pytest.raises(ValueError, match="empty"),
    ):
        PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=empty_md,
            tools_manifest=_FakeToolsManifest(),
            ops_config_path=_ops_yaml(tmp_path),
            user_id=uuid4(),
            persona_id="founder",
        )


def test_five_abstract_methods_raise_until_section_b_c_d(tmp_path):
    """The class skeleton declares the five methods but does not implement
    them — calls must raise NotImplementedError so a half-migrated agent
    fails loudly rather than silently no-op."""
    import asyncio

    from app.agents.base_agent import PikarBaseAgent
    from app.skills.registry import AgentID

    with patch("app.agents.base_agent.PikarAgent.__init__", return_value=None):
        agent = PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_instructions_md(tmp_path),
            tools_manifest=_FakeToolsManifest(),
            ops_config_path=_ops_yaml(tmp_path),
            user_id=uuid4(),
            persona_id="founder",
        )

    async def _run():
        import pytest

        with pytest.raises(NotImplementedError):
            await agent.respond_directly(request=MagicMock())
        with pytest.raises(NotImplementedError):
            await agent.execute_task(contract=MagicMock())
        with pytest.raises(NotImplementedError):
            await agent.start_initiative(
                goal="x", success_criteria=[], owners=[AgentID.FIN]
            )
        with pytest.raises(NotImplementedError):
            await agent.advance_phase(
                initiative_id=uuid4(), current_phase="ideation"
            )
        with pytest.raises(NotImplementedError):
            await agent.close_initiative(initiative_id=uuid4())

    asyncio.run(_run())


def test_legacy_pikar_agent_still_exported():
    """Backward-compat: existing factories import PikarAgent. Must keep working."""
    from app.agents.base_agent import PikarAgent

    assert PikarAgent is not None


def test_tools_manifest_protocol_accepts_concrete_dataclass(tmp_path):
    """Concrete ToolsManifest from runtime.tools_manifest must satisfy the
    Protocol the agent constructor expects."""
    from app.agents.base_agent import PikarBaseAgent
    from app.agents.runtime.tools_manifest import ToolsManifest
    from app.skills.registry import AgentID

    with patch(
        "app.agents.base_agent.PikarAgent.__init__", return_value=None
    ) as parent:
        PikarBaseAgent(
            agent_id=AgentID.FIN,
            instructions_path=_instructions_md(tmp_path),
            tools_manifest=ToolsManifest(tool_ids=[]),
            ops_config_path=_ops_yaml(tmp_path),
            user_id=uuid4(),
            persona_id="founder",
        )

    # Section A stub returns empty list — verify it propagated to ADK.
    assert parent.call_args.kwargs["tools"] == []
