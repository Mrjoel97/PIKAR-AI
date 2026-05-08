# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Structured handoff envelope for Executive -> specialist routing.

Replaces re-deriving intent from session state with a typed packet
that carries explicit intent, evidence, constraints, and expected
output shape across the agent boundary.

This module ships the typed shape, session-state helpers, and a
read-side prompt-injection helper. Wiring on the Executive (write)
side is intentionally deferred to a future PR; see TODO in
``app/agent.py``. The read side is wired into
``app.agents.context_extractor.context_memory_before_model_callback``
so any specialist invoked after a packet is written will see the
rendered block prepended to its system instruction.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# Session-state key under which the most recent handoff packet is stored.
# Intentionally singular ("last_handoff_packet"): the executive routes one
# specialist at a time per turn, and the specialist consumes the packet on
# its next model call. A future revision may extend this to a per-agent map.
HANDOFF_STATE_KEY = "last_handoff_packet"


class HandoffPacket(BaseModel):
    """Typed envelope for Executive -> specialist agent handoffs.

    The packet is written by the Executive Agent (write side, deferred) and
    read by the receiving specialist via
    :func:`apply_handoff_to_prompt`, which renders it as a system-prompt
    block. All fields are explicit so specialists do not need to re-derive
    intent from raw session state.
    """

    intent: str = Field(
        ..., description="One-sentence statement of what the user is asking for."
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Quotes or facts from the user's message that support the routing decision.",
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
        "executive",
        description="The agent emitting the handoff.",
    )
    target_agent: str = Field(
        ...,
        description="The specialist agent receiving the handoff.",
    )
    correlation_id: str | None = Field(
        None,
        description="Optional ID for telemetry/tracing.",
    )

    def to_prompt_block(self) -> str:
        """Render as a system-prompt block the receiving specialist can read.

        The output is a stable, human-readable block delimited by
        ``[HANDOFF FROM EXECUTIVE]`` / ``[END HANDOFF]`` markers, with
        each labeled section on its own line. Evidence and constraints
        are rendered as bulleted lists; empty lists are omitted (rather
        than rendering a confusing "(none)" placeholder).
        """
        lines: list[str] = [
            "\n[HANDOFF FROM EXECUTIVE — use this to scope your response]",
            f"Intent: {self.intent}",
        ]
        if self.evidence:
            lines.append("Evidence:")
            for item in self.evidence:
                lines.append(f"  - {item}")
        if self.constraints:
            lines.append("Constraints:")
            for item in self.constraints:
                lines.append(f"  - {item}")
        lines.append(f"Expected output shape: {self.expected_output_shape}")
        lines.append(f"Source agent: {self.source_agent}")
        lines.append(f"Target agent: {self.target_agent}")
        if self.correlation_id:
            lines.append(f"Correlation ID: {self.correlation_id}")
        lines.append("[END HANDOFF]\n")
        return "\n".join(lines)


def write_handoff(callback_context: Any, packet: HandoffPacket) -> None:
    """Store a handoff packet in session state.

    Best-effort: never raises. If the callback context's state is
    inaccessible or the packet cannot be serialised, the call is a
    silent no-op (the receiving specialist will simply fall back to its
    default behavior).

    Stored as a plain dict (``packet.model_dump()``) so the value is
    JSON-serialisable for any downstream session-state persistence.
    """
    if packet is None:
        return
    try:
        callback_context.state[HANDOFF_STATE_KEY] = packet.model_dump()
    except Exception as exc:  # noqa: BLE001 — best-effort by contract
        logger.debug("[HandoffPacket] write skipped: %s", exc)


def read_handoff(callback_context: Any) -> HandoffPacket | None:
    """Read and validate a handoff packet from session state.

    Returns ``None`` when:
      * no packet has been written,
      * the stored value is not a dict,
      * pydantic validation fails (malformed packet),
      * state access raises.

    Never raises.
    """
    try:
        raw = callback_context.state.get(HANDOFF_STATE_KEY)
    except Exception as exc:  # noqa: BLE001 — best-effort by contract
        logger.debug("[HandoffPacket] read skipped (state error): %s", exc)
        return None

    if not isinstance(raw, dict):
        return None

    try:
        return HandoffPacket(**raw)
    except ValidationError as exc:
        logger.debug("[HandoffPacket] read skipped (validation error): %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 — defensive
        logger.debug("[HandoffPacket] read skipped (unexpected error): %s", exc)
        return None


def apply_handoff_to_prompt(callback_context: Any) -> str:
    """Read-side helper: return the rendered handoff prompt block.

    Returns an empty string when no packet exists or any step fails.
    Callers may unconditionally prepend the result to an instruction
    block list — an empty string contributes nothing.
    """
    try:
        packet = read_handoff(callback_context)
        if packet is None:
            return ""
        return packet.to_prompt_block()
    except Exception as exc:  # noqa: BLE001 — best-effort by contract
        logger.debug("[HandoffPacket] apply_handoff_to_prompt skipped: %s", exc)
        return ""


__all__ = [
    "HANDOFF_STATE_KEY",
    "HandoffPacket",
    "apply_handoff_to_prompt",
    "read_handoff",
    "write_handoff",
]
