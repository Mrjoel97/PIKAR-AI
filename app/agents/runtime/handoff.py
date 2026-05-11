# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Cross-agent handoff recorder.

Wraps the existing :class:`app.agents.handoff_packet.HandoffPacket` so that
every cross-agent transition during an initiative writes one row to
``initiative_phase_history`` with ``event='handoff'``. This closes the
cross-agent visibility gap captured in the 2026-04-28 initiative audit —
the initiative record alone now reveals every transition (see
``docs/superpowers/specs/2026-05-11-agent-operating-model-design.md`` § 14).

We do *not* duplicate the prompt-injection behavior already shipped on the
``HandoffPacket`` side; ``lifecycle.before_agent`` still relies on the
existing read-side helper. This module only adds the durable history row.

Public API
----------
``record_handoff`` — appends one ``handoff`` row to ``initiative_phase_history``
and returns the synthetic ``packet_id`` it minted, or ``None`` on a no-op
(direct-mode chat with no initiative, malformed packet, or transient DB
failure). The call never raises — handoff logging must never break a turn.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from app.services.supabase_client import get_async_client

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.handoff_packet import HandoffPacket


# Table that owns the per-initiative event log. Every initiative phase
# transition, audit note, and now cross-agent handoff lands here.
_TABLE = "initiative_phase_history"


def _to_dict(packet: Any) -> dict[str, Any]:
    """Coerce a handoff packet to a JSON-serialisable dict.

    Tries, in order:
      1. ``packet.model_dump()`` (the canonical Pydantic ``BaseModel``
         shape — what :class:`HandoffPacket` actually exposes),
      2. ``dict(packet)`` (covers dict-like mappings and packets that
         implement ``__iter__`` over ``(key, value)`` pairs),
      3. ``vars(packet)`` (last-resort fallback for plain ``object``-style
         carriers that lack both of the above).

    Returns an empty dict if every fallback raises, so the caller can still
    write the row with the structural ``from_agent``/``to_agent`` fields
    intact even when the body is opaque.
    """
    # 1. Pydantic-style model_dump.
    model_dump = getattr(packet, "model_dump", None)
    if callable(model_dump):
        try:
            result = model_dump()
            if isinstance(result, dict):
                return result
        except Exception as exc:
            logger.debug("[handoff] model_dump failed: %s", exc)

    # 2. dict-cast (Mapping-compatible packets).
    try:
        return dict(packet)
    except Exception as exc:
        logger.debug("[handoff] dict-cast failed: %s", exc)

    # 3. vars() over the instance __dict__.
    try:
        return dict(vars(packet))
    except Exception as exc:
        logger.debug("[handoff] vars() failed: %s", exc)
        return {}


def _get_field(packet: Any, name: str) -> Any:
    """Best-effort attribute/key lookup against a packet-shaped value."""
    value = getattr(packet, name, None)
    if value is not None:
        return value
    try:
        return packet[name]  # type: ignore[index]
    except Exception:
        return None


async def record_handoff(
    *,
    packet: HandoffPacket,
    initiative_id: str | None,
    phase: str | None,
) -> str | None:
    """Insert a ``handoff`` row into ``initiative_phase_history``.

    Returns the synthetic packet id on success, or ``None`` if the handoff
    isn't tied to an initiative (direct-mode chats), if the Supabase call
    fails, or if the packet is malformed. Never raises.
    """
    if not initiative_id:
        # Direct-mode handoffs aren't logged here — they're captured on the
        # executive's ``agent_task_executions`` row via Section D telemetry.
        return None

    packet_id = str(uuid.uuid4())
    try:
        client = await get_async_client()
        row = {
            "initiative_id": initiative_id,
            "phase": phase,
            "event": "handoff",
            "from_agent": _get_field(packet, "source_agent"),
            "to_agent": _get_field(packet, "target_agent"),
            "packet_id": packet_id,
            "packet": _to_dict(packet),
        }
        await client.table(_TABLE).insert(row).execute()
        return packet_id
    except Exception as exc:
        logger.warning(
            "[handoff] record_handoff failed for initiative=%s: %s",
            initiative_id,
            exc,
        )
        return None


__all__ = ["record_handoff"]
