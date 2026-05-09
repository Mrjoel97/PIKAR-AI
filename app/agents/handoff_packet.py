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


# =============================================================================
# Write side: before_agent_callback
# =============================================================================
#
# When the Executive delegates to a specialist via ADK's transfer-to-agent
# flow, the specialist's ``before_agent_callback`` fires at the start of its
# run. That is the cleanest hook for synthesising a HandoffPacket *without*
# needing the Executive to call a write tool, and it sidesteps the
# manifest-prompt migration that would otherwise be required to teach the
# Executive to emit a structured packet.
#
# Strategy:
#   * Skip when the callee is the Executive itself (no self-handoff).
#   * Otherwise, build a minimal packet from whatever signal we can find:
#       1. The user's most recent message (the invocation's ``user_content``,
#          falling back to a few common session-state keys), and
#       2. The callee's agent name (``callback_context.agent_name``).
#   * The packet is written to session state so the receiving specialist's
#     ``before_model_callback`` can render it via ``apply_handoff_to_prompt``.
#
# This is intentionally defensive: any failure logs at debug and returns
# silently. The read side already tolerates a missing or malformed packet,
# so the worst case is that a specialist runs without a handoff prompt
# block — which is the pre-Wave-3 behavior.

# Agent name that identifies the Executive. Used to short-circuit
# self-handoffs so the Executive never writes a packet for itself.
_EXECUTIVE_AGENT_NAME = "ExecutiveAgent"

# Session-state keys we'll probe for a user message, in priority order.
# These mirror ad-hoc conventions seen in other parts of the codebase; we
# never *require* any of them, and missing values fall back cleanly.
_USER_MESSAGE_STATE_KEYS = (
    "last_user_message",
    "current_user_message",
    "user_text",
    "last_user_text",
)


def _extract_user_message(callback_context: Any) -> str:
    """Best-effort extraction of the user's most recent message.

    Tries, in order:
      1. ``callback_context.user_content`` (ADK ``ReadonlyContext`` property
         that exposes the ``Content`` object that started the invocation),
      2. A handful of conventional session-state keys.

    Returns the empty string when nothing is found. Never raises.
    """
    # 1. ADK invocation's user_content.
    try:
        user_content = getattr(callback_context, "user_content", None)
        if user_content is not None:
            parts = getattr(user_content, "parts", None) or []
            texts = [
                getattr(part, "text", "") or "" for part in parts if hasattr(part, "text")
            ]
            joined = " ".join(text for text in texts if text).strip()
            if joined:
                return joined
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.debug("[HandoffPacket] user_content read skipped: %s", exc)

    # 2. Conventional session-state keys.
    try:
        for key in _USER_MESSAGE_STATE_KEYS:
            value = callback_context.state.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.debug("[HandoffPacket] state user-message read skipped: %s", exc)

    return ""


def _extract_session_id(callback_context: Any) -> str | None:
    """Best-effort extraction of a session/correlation id for telemetry."""
    try:
        session = getattr(callback_context, "session", None)
        sid = getattr(session, "id", None) if session is not None else None
        if isinstance(sid, str) and sid:
            return sid
    except Exception:  # noqa: BLE001 — best-effort
        pass
    try:
        sid = callback_context.state.get("session_id")
        if isinstance(sid, str) and sid:
            return sid
    except Exception:  # noqa: BLE001 — best-effort
        pass
    return None


def handoff_packet_before_agent_callback(callback_context: Any) -> None:
    """Synthesize and write a HandoffPacket when delegating to a specialist.

    Fires at the start of an agent's run (ADK ``before_agent_callback``).
    When the callee is a specialist (i.e. *not* the Executive), this
    constructs a minimal :class:`HandoffPacket` from whatever routing
    signal we can find in the invocation context and writes it to
    ``session.state[HANDOFF_STATE_KEY]``. The specialist's
    ``before_model_callback`` will then inject the rendered block into its
    system prompt via :func:`apply_handoff_to_prompt`.

    Defensive contract:
      * Self-handoffs are skipped (the Executive must not write a packet
        for itself).
      * Missing user message → ``intent="(unspecified)"`` so the read side
        still has a renderable packet.
      * Any exception → logged at debug and swallowed. This callback must
        never break a real agent run.
    """
    try:
        agent_name = getattr(callback_context, "agent_name", "") or ""
        if not agent_name or agent_name == _EXECUTIVE_AGENT_NAME:
            # No callee name, or this *is* the Executive: never write a
            # self-handoff. The read-side handles a missing packet cleanly.
            return

        intent = _extract_user_message(callback_context) or "(unspecified)"
        correlation_id = _extract_session_id(callback_context)

        packet = HandoffPacket(
            intent=intent,
            evidence=[],
            constraints=[],
            expected_output_shape="text",
            source_agent="executive",
            target_agent=agent_name,
            correlation_id=correlation_id,
        )
        write_handoff(callback_context, packet)
    except Exception as exc:  # noqa: BLE001 — best-effort by contract
        logger.debug("[HandoffPacket] before_agent_callback skipped: %s", exc)
        return


__all__ = [
    "HANDOFF_STATE_KEY",
    "HandoffPacket",
    "apply_handoff_to_prompt",
    "handoff_packet_before_agent_callback",
    "read_handoff",
    "write_handoff",
]
