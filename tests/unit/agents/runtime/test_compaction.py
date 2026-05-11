# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""``maybe_compact`` — threshold trigger + session.state summary caching.

Covers Task 27 (basic trigger + keep_last_n behavior + failure tolerance)
and Task 41 (cache summary on ``session.state`` for the next turn).
"""

from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Stub the google.adk surface so importing app.agents.runtime.compaction
# (which indirectly pulls runtime types via type-checking imports) is
# safe in an offline unit-test environment.
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())


def _session_with_events(
    events: list[dict],
    approx_tokens: int,
    *,
    with_state: bool = True,
) -> MagicMock:
    s = MagicMock()
    s.id = "sess-1"
    s.events = events
    # Stand-in for the metric maybe_compact reads to decide whether to fire.
    s.approx_token_count = approx_tokens
    if with_state:
        s.state = {}
    return s


def _compaction_cfg(trigger: int = 80_000, keep: int = 12) -> MagicMock:
    c = MagicMock()
    c.trigger_token_count = trigger
    c.keep_last_n_turns = keep
    return c


# ---------------------------------------------------------------------------
# Task 27 — threshold + keep_last_n + failure handling
# ---------------------------------------------------------------------------


def test_maybe_compact_noop_under_threshold():
    from app.agents.runtime import compaction

    summarize = AsyncMock()
    session = _session_with_events(
        [{"i": i} for i in range(50)], approx_tokens=10_000
    )
    with patch.object(compaction, "summarize_dropped_events", summarize):
        result = asyncio.run(compaction.maybe_compact(session, _compaction_cfg()))

    assert result is None
    summarize.assert_not_awaited()


def test_maybe_compact_fires_above_threshold_and_keeps_last_n():
    from app.agents.runtime import compaction

    events = [{"i": i} for i in range(40)]
    summarize = AsyncMock(return_value="SUMMARY TEXT")
    session = _session_with_events(events, approx_tokens=90_000)
    with patch.object(compaction, "summarize_dropped_events", summarize):
        result = asyncio.run(
            compaction.maybe_compact(
                session, _compaction_cfg(trigger=80_000, keep=12)
            )
        )

    summarize.assert_awaited_once()
    call_args = summarize.await_args
    # The "dropped" set is everything except the last keep_last_n_turns events.
    assert call_args.kwargs["events"] == events[:-12]
    assert call_args.kwargs["session_id"] == "sess-1"
    assert result is not None
    assert result.summary == "SUMMARY TEXT"
    assert result.dropped_event_count == 40 - 12
    assert result.kept_event_count == 12


def test_maybe_compact_swallows_summarizer_failure():
    from app.agents.runtime import compaction

    summarize = AsyncMock(side_effect=RuntimeError("model down"))
    session = _session_with_events(
        [{"i": i} for i in range(40)], approx_tokens=90_000
    )
    with patch.object(compaction, "summarize_dropped_events", summarize):
        result = asyncio.run(compaction.maybe_compact(session, _compaction_cfg()))

    assert result is None


def test_maybe_compact_skips_when_fewer_events_than_keep():
    from app.agents.runtime import compaction

    summarize = AsyncMock()
    session = _session_with_events(
        [{"i": i} for i in range(5)], approx_tokens=90_000
    )
    with patch.object(compaction, "summarize_dropped_events", summarize):
        result = asyncio.run(
            compaction.maybe_compact(session, _compaction_cfg(keep=12))
        )

    assert result is None
    summarize.assert_not_awaited()


def test_maybe_compact_treats_empty_summary_as_noop():
    """If the summarizer returns None or '', we get no CompactionResult."""
    from app.agents.runtime import compaction

    session = _session_with_events(
        [{"i": i} for i in range(40)], approx_tokens=90_000
    )
    with patch.object(
        compaction,
        "summarize_dropped_events",
        AsyncMock(return_value=None),
    ):
        result = asyncio.run(compaction.maybe_compact(session, _compaction_cfg()))

    assert result is None


# ---------------------------------------------------------------------------
# Task 41 — cache compaction summary on session.state for next turn
# ---------------------------------------------------------------------------


def test_compaction_writes_summary_to_session_state():
    from app.agents.runtime import compaction

    with patch.object(
        compaction,
        "summarize_dropped_events",
        AsyncMock(return_value="SUM"),
    ):
        sess = _session_with_events(
            [{"i": i} for i in range(40)], approx_tokens=90_000
        )
        result = asyncio.run(compaction.maybe_compact(sess, _compaction_cfg()))

    assert result is not None
    assert sess.state.get(compaction.SESSION_STATE_SUMMARY_KEY) == "SUM"
    assert sess.state.get(compaction.SESSION_STATE_DROPPED_COUNT_KEY) == 28


def test_compaction_no_state_attribute_is_silent():
    """Sessions that don't expose a dict ``state`` must not crash compaction."""
    from app.agents.runtime import compaction

    with patch.object(
        compaction,
        "summarize_dropped_events",
        AsyncMock(return_value="SUM"),
    ):
        sess = MagicMock()
        sess.id = "sess-2"
        sess.events = [{"i": i} for i in range(40)]
        sess.approx_token_count = 90_000
        # No dict state — getattr(sess, "state", None) returns a MagicMock,
        # which is NOT a dict, so the cache path is skipped silently.
        sess.state = MagicMock(spec=[])  # not a dict
        result = asyncio.run(compaction.maybe_compact(sess, _compaction_cfg()))

    assert result is not None
    assert result.summary == "SUM"
