# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for the HandoffPacket envelope and its session-state helpers."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

# Stub the google.adk + google.genai surface the same way other unit tests do
# so importing app.agents.handoff_packet (and any indirect deps) does not
# require the real ADK runtime.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())


def _make_callback_context() -> MagicMock:
    """Build a CallbackContext-shaped mock with a real dict for state."""
    ctx = MagicMock()
    ctx.state = {}
    return ctx


# ---------------------------------------------------------------------------
# Construction & validation
# ---------------------------------------------------------------------------


def test_handoff_packet_constructs_with_required_fields():
    from app.agents.handoff_packet import HandoffPacket

    packet = HandoffPacket(
        intent="Draft a quarterly P&L summary",
        target_agent="FinancialAnalysisAgent",
    )

    assert packet.intent == "Draft a quarterly P&L summary"
    assert packet.target_agent == "FinancialAnalysisAgent"
    # Defaults
    assert packet.evidence == []
    assert packet.constraints == []
    assert packet.expected_output_shape == "text"
    assert packet.source_agent == "executive"
    assert packet.correlation_id is None


def test_handoff_packet_missing_required_fields_raises():
    from app.agents.handoff_packet import HandoffPacket

    with pytest.raises(ValidationError):
        HandoffPacket()  # type: ignore[call-arg]

    with pytest.raises(ValidationError):
        HandoffPacket(intent="something")  # type: ignore[call-arg]

    with pytest.raises(ValidationError):
        HandoffPacket(target_agent="X")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# to_prompt_block — stable, human-readable, all fields labelled
# ---------------------------------------------------------------------------


def test_to_prompt_block_contains_all_labelled_sections():
    from app.agents.handoff_packet import HandoffPacket

    packet = HandoffPacket(
        intent="Produce a Q3 financial report",
        evidence=['user said "I need numbers by Friday"', "Q3 closed last week"],
        constraints=["deadline: Friday EOD", "include MoM trend"],
        expected_output_shape="document",
        source_agent="executive",
        target_agent="FinancialAnalysisAgent",
        correlation_id="corr-123",
    )

    block = packet.to_prompt_block()

    # Stable delimiters
    assert "[HANDOFF FROM EXECUTIVE" in block
    assert "[END HANDOFF]" in block

    # Labelled fields
    assert "Intent: Produce a Q3 financial report" in block
    assert "Evidence:" in block
    assert 'user said "I need numbers by Friday"' in block
    assert "Q3 closed last week" in block
    assert "Constraints:" in block
    assert "deadline: Friday EOD" in block
    assert "include MoM trend" in block
    assert "Expected output shape: document" in block
    assert "Source agent: executive" in block
    assert "Target agent: FinancialAnalysisAgent" in block
    assert "Correlation ID: corr-123" in block


def test_to_prompt_block_omits_empty_evidence_and_constraints():
    from app.agents.handoff_packet import HandoffPacket

    packet = HandoffPacket(
        intent="Quick lookup",
        target_agent="DataAnalysisAgent",
    )
    block = packet.to_prompt_block()

    # Empty lists shouldn't render their headers (avoid confusing "(none)" lines).
    assert "Evidence:" not in block
    assert "Constraints:" not in block
    # But required labels still present
    assert "Intent: Quick lookup" in block
    assert "Expected output shape: text" in block
    assert "Target agent: DataAnalysisAgent" in block


# ---------------------------------------------------------------------------
# write_handoff + read_handoff round-trip
# ---------------------------------------------------------------------------


def test_write_and_read_handoff_round_trip_preserves_all_fields():
    from app.agents.handoff_packet import (
        HANDOFF_STATE_KEY,
        HandoffPacket,
        read_handoff,
        write_handoff,
    )

    ctx = _make_callback_context()
    original = HandoffPacket(
        intent="Draft a launch email",
        evidence=["mentioned 'launch on Tuesday'"],
        constraints=["tone: friendly", "max 200 words"],
        expected_output_shape="structured_json",
        source_agent="executive",
        target_agent="ContentCreationAgent",
        correlation_id="abc-xyz",
    )

    write_handoff(ctx, original)

    # Stored as a plain dict for serialisability
    stored = ctx.state[HANDOFF_STATE_KEY]
    assert isinstance(stored, dict)

    roundtripped = read_handoff(ctx)
    assert roundtripped is not None
    assert roundtripped.intent == original.intent
    assert roundtripped.evidence == original.evidence
    assert roundtripped.constraints == original.constraints
    assert roundtripped.expected_output_shape == original.expected_output_shape
    assert roundtripped.source_agent == original.source_agent
    assert roundtripped.target_agent == original.target_agent
    assert roundtripped.correlation_id == original.correlation_id


def test_read_handoff_returns_none_when_missing():
    from app.agents.handoff_packet import read_handoff

    ctx = _make_callback_context()
    assert read_handoff(ctx) is None


def test_read_handoff_returns_none_on_malformed_payload():
    from app.agents.handoff_packet import HANDOFF_STATE_KEY, read_handoff

    ctx = _make_callback_context()
    # Missing required `intent` and `target_agent` fields.
    ctx.state[HANDOFF_STATE_KEY] = {"evidence": ["nope"]}

    assert read_handoff(ctx) is None


def test_read_handoff_returns_none_on_non_dict_payload():
    from app.agents.handoff_packet import HANDOFF_STATE_KEY, read_handoff

    ctx = _make_callback_context()
    ctx.state[HANDOFF_STATE_KEY] = "not a dict"
    assert read_handoff(ctx) is None


# ---------------------------------------------------------------------------
# apply_handoff_to_prompt — the read-side glue used by context_extractor
# ---------------------------------------------------------------------------


def test_apply_handoff_to_prompt_injects_block_when_packet_present():
    from app.agents.handoff_packet import (
        HandoffPacket,
        apply_handoff_to_prompt,
        write_handoff,
    )

    ctx = _make_callback_context()
    write_handoff(
        ctx,
        HandoffPacket(
            intent="Summarise customer feedback",
            evidence=["3 tickets mention slow load times"],
            constraints=["one paragraph"],
            target_agent="CustomerSupportAgent",
        ),
    )

    block = apply_handoff_to_prompt(ctx)

    assert block  # non-empty
    assert "[HANDOFF FROM EXECUTIVE" in block
    assert "Summarise customer feedback" in block
    assert "3 tickets mention slow load times" in block
    assert "CustomerSupportAgent" in block


def test_apply_handoff_to_prompt_no_op_when_packet_absent():
    from app.agents.handoff_packet import apply_handoff_to_prompt

    ctx = _make_callback_context()
    assert apply_handoff_to_prompt(ctx) == ""


def test_apply_handoff_to_prompt_no_op_when_packet_malformed():
    from app.agents.handoff_packet import HANDOFF_STATE_KEY, apply_handoff_to_prompt

    ctx = _make_callback_context()
    ctx.state[HANDOFF_STATE_KEY] = {"evidence": ["incomplete"]}  # missing required
    assert apply_handoff_to_prompt(ctx) == ""


# ---------------------------------------------------------------------------
# Defensive contract: helpers must swallow exceptions raised by state access
# ---------------------------------------------------------------------------


class _ExplodingState:
    """A state-shaped object whose .get and __setitem__ raise."""

    def get(self, _key, _default=None):
        raise RuntimeError("state get exploded")

    def __setitem__(self, _key, _value):
        raise RuntimeError("state set exploded")


def _make_exploding_context() -> MagicMock:
    ctx = MagicMock()
    ctx.state = _ExplodingState()
    return ctx


def test_write_handoff_swallows_state_errors():
    from app.agents.handoff_packet import HandoffPacket, write_handoff

    ctx = _make_exploding_context()
    packet = HandoffPacket(intent="x", target_agent="y")

    # Must not raise.
    write_handoff(ctx, packet)


def test_read_handoff_swallows_state_errors():
    from app.agents.handoff_packet import read_handoff

    ctx = _make_exploding_context()
    assert read_handoff(ctx) is None


def test_apply_handoff_to_prompt_swallows_state_errors():
    from app.agents.handoff_packet import apply_handoff_to_prompt

    ctx = _make_exploding_context()
    assert apply_handoff_to_prompt(ctx) == ""


def test_write_handoff_with_none_packet_is_noop():
    from app.agents.handoff_packet import HANDOFF_STATE_KEY, write_handoff

    ctx = _make_callback_context()
    write_handoff(ctx, None)  # type: ignore[arg-type]
    assert HANDOFF_STATE_KEY not in ctx.state
