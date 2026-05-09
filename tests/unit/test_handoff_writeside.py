# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for the HandoffPacket *write* side.

The write side is :func:`handoff_packet_before_agent_callback`, an ADK
``before_agent_callback`` that fires when a specialist agent's run begins.
It synthesises a minimal :class:`HandoffPacket` from the invocation's
``user_content`` (or session state fall-backs) and writes it to
``session.state[HANDOFF_STATE_KEY]`` so the specialist's
``before_model_callback`` can render it via :func:`apply_handoff_to_prompt`.

These tests cover:
  * Happy path: user_content is read and the packet round-trips through
    state into a rendered prompt block.
  * Self-handoff guard: when the callee is the Executive, no packet is
    written.
  * Missing user message: writes a minimal packet with ``intent="(unspecified)"``.
  * Defensive contract: any exception during synthesis is swallowed.
  * End-to-end: write -> apply_handoff_to_prompt produces the expected
    rendered block.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Stub the google.adk + google.genai surface the same way other unit tests do
# so importing app.agents.handoff_packet does not require the real ADK runtime.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_part(text: str) -> MagicMock:
    """Build a ``Part``-shaped mock that exposes a ``text`` attribute."""
    part = MagicMock()
    part.text = text
    return part


def _make_user_content(*texts: str) -> MagicMock:
    """Build a ``Content``-shaped mock with one ``Part`` per text."""
    content = MagicMock()
    content.parts = [_make_part(t) for t in texts]
    return content


def _make_callback_context(
    *,
    agent_name: str = "FinancialAnalysisAgent",
    user_content: object | None = None,
    session_id: str | None = "sess-abc",
    state: dict | None = None,
) -> MagicMock:
    """Build a CallbackContext-shaped mock matching ADK's surface.

    Sets ``agent_name``, ``user_content``, ``state`` (real dict), and
    ``session.id``. The MagicMock spec is intentionally loose so individual
    tests can override fields (e.g. delete ``user_content`` to force a
    state fall-back).
    """
    ctx = MagicMock()
    ctx.agent_name = agent_name
    ctx.user_content = user_content
    ctx.state = state if state is not None else {}
    if session_id is not None:
        ctx.session = MagicMock()
        ctx.session.id = session_id
    else:
        ctx.session = None
    return ctx


# ---------------------------------------------------------------------------
# Happy path: callback writes a packet sourced from user_content
# ---------------------------------------------------------------------------


def test_callback_writes_packet_from_user_content():
    from app.agents.handoff_packet import (
        HANDOFF_STATE_KEY,
        handoff_packet_before_agent_callback,
    )

    ctx = _make_callback_context(
        agent_name="FinancialAnalysisAgent",
        user_content=_make_user_content("Forecast Q4 revenue using last 6 months."),
        session_id="sess-1",
    )

    handoff_packet_before_agent_callback(ctx)

    stored = ctx.state[HANDOFF_STATE_KEY]
    assert isinstance(stored, dict)
    assert stored["intent"] == "Forecast Q4 revenue using last 6 months."
    assert stored["target_agent"] == "FinancialAnalysisAgent"
    assert stored["source_agent"] == "executive"
    assert stored["expected_output_shape"] == "text"
    assert stored["correlation_id"] == "sess-1"
    assert stored["evidence"] == []
    assert stored["constraints"] == []


def test_callback_concatenates_multipart_user_content():
    from app.agents.handoff_packet import (
        HANDOFF_STATE_KEY,
        handoff_packet_before_agent_callback,
    )

    ctx = _make_callback_context(
        agent_name="ContentCreationAgent",
        user_content=_make_user_content("Draft a blog post", "about Q4 launches."),
    )

    handoff_packet_before_agent_callback(ctx)

    stored = ctx.state[HANDOFF_STATE_KEY]
    assert stored["intent"] == "Draft a blog post about Q4 launches."
    assert stored["target_agent"] == "ContentCreationAgent"


# ---------------------------------------------------------------------------
# Self-handoff guard: Executive must not write a packet for itself
# ---------------------------------------------------------------------------


def test_callback_skips_when_callee_is_executive():
    from app.agents.handoff_packet import (
        HANDOFF_STATE_KEY,
        handoff_packet_before_agent_callback,
    )

    ctx = _make_callback_context(
        agent_name="ExecutiveAgent",
        user_content=_make_user_content("Hello there"),
    )

    handoff_packet_before_agent_callback(ctx)

    # No packet written.
    assert HANDOFF_STATE_KEY not in ctx.state


def test_callback_skips_when_agent_name_is_empty():
    from app.agents.handoff_packet import (
        HANDOFF_STATE_KEY,
        handoff_packet_before_agent_callback,
    )

    ctx = _make_callback_context(
        agent_name="",
        user_content=_make_user_content("Hello there"),
    )

    handoff_packet_before_agent_callback(ctx)

    assert HANDOFF_STATE_KEY not in ctx.state


# ---------------------------------------------------------------------------
# Missing user message: minimal packet with intent="(unspecified)"
# ---------------------------------------------------------------------------


def test_callback_writes_minimal_packet_when_user_content_missing():
    from app.agents.handoff_packet import (
        HANDOFF_STATE_KEY,
        handoff_packet_before_agent_callback,
    )

    ctx = _make_callback_context(
        agent_name="DataAnalysisAgent",
        user_content=None,
        session_id=None,
        state={},
    )
    # Make sure state.get("session_id") also returns None so correlation_id
    # is None (not the auto-set MagicMock value).
    ctx.session = None

    handoff_packet_before_agent_callback(ctx)

    stored = ctx.state[HANDOFF_STATE_KEY]
    assert stored["intent"] == "(unspecified)"
    assert stored["target_agent"] == "DataAnalysisAgent"


def test_callback_falls_back_to_state_user_message_key():
    from app.agents.handoff_packet import (
        HANDOFF_STATE_KEY,
        handoff_packet_before_agent_callback,
    )

    ctx = _make_callback_context(
        agent_name="MarketingAutomationAgent",
        user_content=None,
        state={"last_user_message": "Spin up a Q4 campaign."},
    )

    handoff_packet_before_agent_callback(ctx)

    stored = ctx.state[HANDOFF_STATE_KEY]
    assert stored["intent"] == "Spin up a Q4 campaign."
    assert stored["target_agent"] == "MarketingAutomationAgent"


# ---------------------------------------------------------------------------
# Defensive contract: never raise, even when synthesis blows up
# ---------------------------------------------------------------------------


class _ExplodingState:
    """A state-shaped object whose ``.get`` and ``__setitem__`` raise."""

    def get(self, _key, _default=None):
        raise RuntimeError("state get exploded")

    def __setitem__(self, _key, _value):
        raise RuntimeError("state set exploded")


def test_callback_swallows_exceptions_during_synthesis():
    from app.agents.handoff_packet import handoff_packet_before_agent_callback

    ctx = MagicMock()
    ctx.agent_name = "SalesIntelligenceAgent"
    ctx.user_content = None
    ctx.state = _ExplodingState()
    ctx.session = None

    # Must not raise.
    result = handoff_packet_before_agent_callback(ctx)
    assert result is None


def test_callback_swallows_exception_when_agent_name_access_fails():
    from app.agents.handoff_packet import handoff_packet_before_agent_callback

    class _Ctx:
        @property
        def agent_name(self):  # noqa: D401 — property under test
            raise RuntimeError("boom")

    # Must not raise.
    handoff_packet_before_agent_callback(_Ctx())


# ---------------------------------------------------------------------------
# End-to-end: write packet via callback, then render via apply_handoff_to_prompt
# ---------------------------------------------------------------------------


def test_callback_then_apply_handoff_to_prompt_round_trip():
    from app.agents.handoff_packet import (
        apply_handoff_to_prompt,
        handoff_packet_before_agent_callback,
    )

    ctx = _make_callback_context(
        agent_name="ComplianceRiskAgent",
        user_content=_make_user_content(
            "Run a SOX-style audit on Q3 vendor contracts."
        ),
        session_id="corr-sox-q3",
    )

    handoff_packet_before_agent_callback(ctx)

    block = apply_handoff_to_prompt(ctx)
    assert block, "expected non-empty rendered handoff block"
    assert "[HANDOFF FROM EXECUTIVE" in block
    assert "Run a SOX-style audit on Q3 vendor contracts." in block
    assert "Target agent: ComplianceRiskAgent" in block
    assert "Source agent: executive" in block
    assert "Correlation ID: corr-sox-q3" in block
