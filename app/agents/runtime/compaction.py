# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Session compaction trigger.

Wraps the existing :mod:`app.services.conversation_summarizer` so the
runtime layer fires summarization when an agent's session crosses
``ops.compaction.trigger_token_count``. The session keeps the last
``keep_last_n_turns`` events; everything older is summarized and stored
on ``session.state`` for the next turn to read as background context.

Called from ``lifecycle.after_agent`` (spec § 5). Never raises — a
summarizer outage must not break the user's turn.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.services.conversation_summarizer import summarize_dropped_events

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from app.agents.runtime.operations_config import CompactionConfig


# Keys cached on ``session.state`` for the next turn to consume. Prefixed
# with ``_runtime_`` so they're obviously framework-owned rather than
# user/agent state.
SESSION_STATE_SUMMARY_KEY = "_runtime_compaction_summary"
SESSION_STATE_DROPPED_COUNT_KEY = "_runtime_compaction_dropped_count"


@dataclass
class CompactionResult:
    """Outcome of a compaction pass."""

    summary: str
    dropped_event_count: int
    kept_event_count: int


async def maybe_compact(
    session: Any,
    cfg: "CompactionConfig",
) -> CompactionResult | None:
    """Trigger compaction when the session crosses the configured threshold.

    Returns ``None`` when no compaction was needed (token count below
    ``trigger_token_count``), when the session has fewer events than
    ``keep_last_n_turns`` (nothing to drop), or when the summarizer
    fails. Never raises.

    On success, the summary is also cached on ``session.state`` under
    :data:`SESSION_STATE_SUMMARY_KEY` so the next turn can prepend it as
    background context.
    """
    trigger = int(getattr(cfg, "trigger_token_count", 80_000))
    keep = int(getattr(cfg, "keep_last_n_turns", 12))

    approx_tokens = int(getattr(session, "approx_token_count", 0) or 0)
    if approx_tokens < trigger:
        return None

    events = list(getattr(session, "events", []) or [])
    if len(events) <= keep:
        # Token count is up but we don't have enough turns to drop. Bail
        # rather than feeding the summarizer an empty list.
        return None

    dropped = events[:-keep]
    kept = events[-keep:]
    session_id = getattr(session, "id", "") or "unknown"

    try:
        summary = await summarize_dropped_events(
            events=dropped,
            session_id=session_id,
        )
    except Exception as exc:  # noqa: BLE001 — never break the turn
        logger.warning(
            "[compaction] summarizer failed for session %s: %s", session_id, exc
        )
        return None

    if not summary:
        return None

    result = CompactionResult(
        summary=summary,
        dropped_event_count=len(dropped),
        kept_event_count=len(kept),
    )

    # Cache on session.state so the next turn's before_agent callback
    # can prepend the summary to the model's context. Best-effort: if
    # the session implementation doesn't expose a mutable mapping, log
    # and move on rather than failing the compaction.
    try:
        state = getattr(session, "state", None)
        if isinstance(state, dict):
            state[SESSION_STATE_SUMMARY_KEY] = result.summary
            state[SESSION_STATE_DROPPED_COUNT_KEY] = result.dropped_event_count
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "[compaction] could not persist summary to session.state: %s", exc
        )

    return result


__all__ = [
    "SESSION_STATE_DROPPED_COUNT_KEY",
    "SESSION_STATE_SUMMARY_KEY",
    "CompactionResult",
    "maybe_compact",
]
