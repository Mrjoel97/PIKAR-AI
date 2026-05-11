# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Lifecycle callback factories — Section A stubs only.

These functions must exist and return callables so PikarBaseAgent can wire
them. Their bodies are owned by Section B; here we only check the shape.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Stub the google.adk + google.genai surface the same way other unit tests do
# so importing the lifecycle module does not require the real ADK.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.adk.tools", MagicMock())
sys.modules.setdefault("google.adk.tools.tool_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())


def test_before_agent_returns_callable():
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent")
    cb = lifecycle.before_agent(agent)
    assert callable(cb)


def test_before_tool_returns_callable():
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent")
    cb = lifecycle.before_tool(agent)
    assert callable(cb)


def test_after_tool_returns_callable():
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent")
    cb = lifecycle.after_tool(agent)
    assert callable(cb)


def test_after_agent_returns_callable():
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent")
    cb = lifecycle.after_agent(agent)
    assert callable(cb)


def test_before_agent_stub_accepts_adk_signature():
    """before_agent_callback(callback_context) -> Content | None."""
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent")
    cb = lifecycle.before_agent(agent)
    assert cb(callback_context=MagicMock()) is None
    # Positional invocation also accepted (ADK uses positional in some paths).
    assert cb(MagicMock()) is None


def test_before_tool_stub_accepts_adk_signature():
    """before_tool_callback(tool, args, tool_context) -> dict | None."""
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent")
    cb = lifecycle.before_tool(agent)
    assert (
        cb(tool=MagicMock(), args={"foo": "bar"}, tool_context=MagicMock())
        is None
    )
    assert cb(MagicMock(), {"foo": "bar"}, MagicMock()) is None


def test_after_tool_stub_accepts_adk_signature():
    """after_tool_callback(tool, args, tool_context, tool_response) -> dict | None."""
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent")
    cb = lifecycle.after_tool(agent)
    assert (
        cb(
            tool=MagicMock(),
            args={"foo": "bar"},
            tool_context=MagicMock(),
            tool_response={"ok": True},
        )
        is None
    )
    assert cb(MagicMock(), {"foo": "bar"}, MagicMock(), {"ok": True}) is None


def test_after_agent_stub_accepts_adk_signature():
    """after_agent_callback(callback_context) -> Content | None."""
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent")
    cb = lifecycle.after_agent(agent)
    assert cb(callback_context=MagicMock()) is None
    assert cb(MagicMock()) is None


def test_factories_do_not_require_real_agent_methods():
    """Section A: factory must not touch agent attributes — stubs only.

    The MagicMock has no methods configured; if a factory tried to call
    e.g. ``agent.persona_policy`` and depended on a real return value, the
    stub contract would be violated.
    """
    from app.agents.runtime import lifecycle

    agent = MagicMock(name="PikarBaseAgent", spec=[])
    for factory in (
        lifecycle.before_agent,
        lifecycle.before_tool,
        lifecycle.after_tool,
        lifecycle.after_agent,
    ):
        cb = factory(agent)
        assert callable(cb)
