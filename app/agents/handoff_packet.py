# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Structured handoff envelope for Executive -> specialist routing.

Replaces re-deriving intent from session state with a typed packet
that carries explicit intent, evidence, constraints, and expected
output shape across the agent boundary.

The packet is written by the routing agent (Executive) into ADK
session.state under the key ``last_handoff_packet`` and is read by
the receiving specialist via its before_model_callback or prompt
construction step.

This is the initial implementation: the typed shape, session-state
read/write helpers, and a render function. Wiring the Executive's
routing logic to *emit* packets is intentionally deferred to a
follow-up PR (see TODO in ``app/agent.py``).
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

#: Session-state key under which the most recent handoff packet is stored.
HANDOFF_PACKET_STATE_KEY = "last_handoff_packet"


class HandoffPacket(BaseModel):
    """Typed envelope for Executive -> specialist agent handoffs.

    Carries the routing decision's explicit intent, supporting evidence,
    constraints, and the expected output shape so the receiving
    specialist does not have to re-derive intent from the raw user
    message or session state.
    """

    intent: str = Field(
        ..., description="One-sentence statement of what the user is asking for."
    )
    evidence: list[str] = Field(
        default_factory=list,
        description=(
            "Quotes or facts from the user's message that support the "
            "routing decision."
        ),
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Any explicit constraints (deadline, scope, format).",
    )
    expected_output_shape: str = Field(
        "text",
        description="text | widget | document | structured_json",
    )
    source_agent: str = Field(
        "executive", description="The agent emitting the handoff."
    )
    target_agent: str = Field(
        ..., description="The specialist agent receiving the handoff."
    )
    correlation_id: str | None = Field(
        None, description="Optional ID for telemetry/tracing."
    )

    def to_prompt_block(self) -> str:
        """Render as a system-prompt block the receiving specialist can read.

        The output is human-readable, label-prefixed, and stable across
        calls so specialists (and tests) can parse or assert on it.
        Empty evidence/constraint lists render as a single ``(none)``
        marker rather than being omitted, so the block always has the
        same labeled sections.
        """
        evidence_lines = (
            "\n".join(f"  - {item}" for item in self.evidence)
            if self.evidence
            else "  (none)"
        )
        constraints_lines = (
            "\n".join(f"  - {item}" for item in self.constraints)
            if self.constraints
            else "  (none)"
        )
        correlation = self.correlation_id or "(none)"
        return (
            "[HANDOFF PACKET]\n"
            f"Source: {self.source_agent}\n"
            f"Target: {self.target_agent}\n"
            f"Intent: {self.intent}\n"
            f"Expected Output Shape: {self.expected_output_shape}\n"
            "Evidence:\n"
            f"{evidence_lines}\n"
            "Constraints:\n"
            f"{constraints_lines}\n"
            f"Correlation ID: {correlation}\n"
            "[/HANDOFF PACKET]"
        )


# ---------------------------------------------------------------------------
# Session-state read/write helpers
# ---------------------------------------------------------------------------
#
# These helpers operate on an ADK ``CallbackContext`` (or any object exposing
# a dict-like ``state`` attribute). They are best-effort: failures during
# state access are logged at debug level and swallowed so a broken handoff
# never crashes the routing path.
#
# Packets are persisted as plain dicts (``model_dump()``) so they survive
# JSON serialization round-trips inside ADK session storage.


def write_handoff(callback_context: Any, packet: HandoffPacket) -> None:
    """Store ``packet`` in session state under ``last_handoff_packet``.

    Best-effort: never raises. If the underlying state mapping rejects
    the write (read-only, missing, or otherwise broken), the failure is
    logged and the call returns silently.
    """
    try:
        state = getattr(callback_context, "state", None)
        if state is None:
            return
        state[HANDOFF_PACKET_STATE_KEY] = packet.model_dump()
    except Exception:
        logger.debug("write_handoff: failed to persist packet", exc_info=True)


def read_handoff(callback_context: Any) -> HandoffPacket | None:
    """Read and validate the most recent handoff packet from session state.

    Returns ``None`` when no packet is present, when the stored value is
    not a dict, when validation fails, or when state access raises.
    Never raises.
    """
    try:
        state = getattr(callback_context, "state", None)
        if state is None:
            return None
        raw = state.get(HANDOFF_PACKET_STATE_KEY)
    except Exception:
        logger.debug("read_handoff: state access failed", exc_info=True)
        return None

    if raw is None:
        return None
    if isinstance(raw, HandoffPacket):
        return raw
    if not isinstance(raw, dict):
        logger.debug(
            "read_handoff: stored value is not a dict (got %s)", type(raw).__name__
        )
        return None
    try:
        return HandoffPacket.model_validate(raw)
    except ValidationError:
        logger.debug("read_handoff: stored packet failed validation", exc_info=True)
        return None


def apply_handoff_to_prompt(callback_context: Any) -> str:
    """Read-side helper: render the current handoff packet as a prompt block.

    Returns the rendered block (suitable for splicing into a system
    prompt) when a valid packet is in session state, or an empty string
    when no packet is present or any error occurs reading it.

    This helper is defensive on purpose: it is intended to be called
    from prompt construction paths that must not fail just because a
    handoff was missing or malformed.
    """
    try:
        packet = read_handoff(callback_context)
    except Exception:
        logger.debug(
            "apply_handoff_to_prompt: read_handoff raised unexpectedly",
            exc_info=True,
        )
        return ""
    if packet is None:
        return ""
    try:
        return packet.to_prompt_block()
    except Exception:
        logger.debug(
            "apply_handoff_to_prompt: to_prompt_block raised", exc_info=True
        )
        return ""
