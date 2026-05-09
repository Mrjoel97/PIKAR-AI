# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the HandoffPacket envelope and session-state helpers."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.agents.handoff_packet import (
    HANDOFF_PACKET_STATE_KEY,
    HandoffPacket,
    apply_handoff_to_prompt,
    read_handoff,
    write_handoff,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _FakeCallbackContext:
    """Minimal CallbackContext stand-in: just exposes ``state`` as a dict."""

    def __init__(self, state: dict | None = None):
        self.state: dict = state if state is not None else {}


class _RaisingState:
    """Mapping-like that raises on every access. Used to verify defensiveness."""

    def get(self, *_args, **_kwargs):
        raise RuntimeError("state access blew up")

    def __getitem__(self, _key):
        raise RuntimeError("state access blew up")

    def __setitem__(self, _key, _value):
        raise RuntimeError("state write blew up")


class _RaisingContext:
    state = _RaisingState()


# ---------------------------------------------------------------------------
# Construction / validation
# ---------------------------------------------------------------------------


def test_handoff_packet_constructs_with_required_fields():
    packet = HandoffPacket(
        intent="Draft a Q3 marketing plan",
        target_agent="MarketingAgent",
    )
    assert packet.intent == "Draft a Q3 marketing plan"
    assert packet.target_agent == "MarketingAgent"
    # Defaults
    assert packet.evidence == []
    assert packet.constraints == []
    assert packet.expected_output_shape == "text"
    assert packet.source_agent == "executive"
    assert packet.correlation_id is None


def test_handoff_packet_missing_intent_raises():
    with pytest.raises(ValidationError):
        HandoffPacket(target_agent="MarketingAgent")  # type: ignore[call-arg]


def test_handoff_packet_missing_target_agent_raises():
    with pytest.raises(ValidationError):
        HandoffPacket(intent="something")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# to_prompt_block rendering
# ---------------------------------------------------------------------------


def test_to_prompt_block_includes_labeled_sections():
    packet = HandoffPacket(
        intent="Draft a Q3 marketing plan focused on SMBs",
        evidence=[
            "User said: 'we need a plan by next week'",
            "User mentioned target = SMBs",
        ],
        constraints=["Deadline: next Friday", "Format: PDF"],
        expected_output_shape="document",
        source_agent="executive",
        target_agent="MarketingAgent",
        correlation_id="trace-abc-123",
    )
    block = packet.to_prompt_block()

    # All labeled sections present
    assert "Intent:" in block
    assert "Evidence:" in block
    assert "Constraints:" in block
    assert "Expected Output Shape:" in block
    assert "Source:" in block
    assert "Target:" in block
    assert "Correlation ID:" in block

    # Values rendered
    assert "Draft a Q3 marketing plan focused on SMBs" in block
    assert "we need a plan by next week" in block
    assert "Deadline: next Friday" in block
    assert "document" in block
    assert "MarketingAgent" in block
    assert "trace-abc-123" in block

    # Stable wrapper
    assert "[HANDOFF PACKET]" in block
    assert "[/HANDOFF PACKET]" in block


def test_to_prompt_block_renders_none_markers_for_empty_lists():
    packet = HandoffPacket(intent="do a thing", target_agent="ContentAgent")
    block = packet.to_prompt_block()
    assert "Evidence:" in block
    assert "Constraints:" in block
    assert "(none)" in block
    # Correlation ID also defaults to (none) when unset
    assert "Correlation ID: (none)" in block


def test_to_prompt_block_is_stable_across_calls():
    packet = HandoffPacket(
        intent="i",
        evidence=["e1", "e2"],
        constraints=["c1"],
        target_agent="T",
    )
    assert packet.to_prompt_block() == packet.to_prompt_block()


# ---------------------------------------------------------------------------
# write_handoff / read_handoff round-trip
# ---------------------------------------------------------------------------


def test_write_and_read_handoff_round_trip_preserves_all_fields():
    ctx = _FakeCallbackContext()
    original = HandoffPacket(
        intent="Run a competitive analysis on Acme Corp",
        evidence=["User said: 'compare us to Acme'", "Past chat mentioned Acme"],
        constraints=["Scope: top 3 competitors", "Format: structured_json"],
        expected_output_shape="structured_json",
        source_agent="executive",
        target_agent="ResearchAgent",
        correlation_id="corr-xyz",
    )
    write_handoff(ctx, original)

    # Persisted as a dict (JSON-serializable shape)
    assert HANDOFF_PACKET_STATE_KEY in ctx.state
    assert isinstance(ctx.state[HANDOFF_PACKET_STATE_KEY], dict)

    restored = read_handoff(ctx)
    assert restored is not None
    assert restored.intent == original.intent
    assert restored.evidence == original.evidence
    assert restored.constraints == original.constraints
    assert restored.expected_output_shape == original.expected_output_shape
    assert restored.source_agent == original.source_agent
    assert restored.target_agent == original.target_agent
    assert restored.correlation_id == original.correlation_id


def test_read_handoff_returns_none_when_state_empty():
    ctx = _FakeCallbackContext()
    assert read_handoff(ctx) is None


def test_read_handoff_returns_none_for_malformed_payload():
    ctx = _FakeCallbackContext({HANDOFF_PACKET_STATE_KEY: {"intent": "only intent"}})
    # Missing target_agent -> validation fails -> None
    assert read_handoff(ctx) is None


def test_read_handoff_returns_none_when_value_not_a_dict():
    ctx = _FakeCallbackContext({HANDOFF_PACKET_STATE_KEY: "not a dict"})
    assert read_handoff(ctx) is None


def test_write_handoff_never_raises_on_broken_state():
    # Should swallow the error from _RaisingState.__setitem__
    write_handoff(
        _RaisingContext(),
        HandoffPacket(intent="i", target_agent="T"),
    )


def test_read_handoff_never_raises_on_broken_state():
    assert read_handoff(_RaisingContext()) is None


# ---------------------------------------------------------------------------
# apply_handoff_to_prompt
# ---------------------------------------------------------------------------


def test_apply_handoff_to_prompt_injects_block_when_packet_present():
    ctx = _FakeCallbackContext()
    write_handoff(
        ctx,
        HandoffPacket(
            intent="Summarize the Q4 board deck",
            evidence=["User: 'TL;DR the board deck'"],
            constraints=["Length: 3 bullets"],
            target_agent="ContentAgent",
        ),
    )
    block = apply_handoff_to_prompt(ctx)
    assert block != ""
    assert "Intent:" in block
    assert "Summarize the Q4 board deck" in block
    assert "ContentAgent" in block


def test_apply_handoff_to_prompt_is_noop_when_no_packet():
    ctx = _FakeCallbackContext()
    assert apply_handoff_to_prompt(ctx) == ""


def test_apply_handoff_to_prompt_swallows_state_access_errors():
    # Should not raise, returns empty string when state access blows up.
    assert apply_handoff_to_prompt(_RaisingContext()) == ""


def test_apply_handoff_to_prompt_swallows_validation_errors_via_read():
    ctx = _FakeCallbackContext({HANDOFF_PACKET_STATE_KEY: {"intent": "no target"}})
    assert apply_handoff_to_prompt(ctx) == ""
