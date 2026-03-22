"""Tests for the research event bus (Redis Streams)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock


def _run(coro):
    return asyncio.run(coro)


def test_emit_event_calls_xadd():
    """Emitting an event calls Redis XADD on the stream."""
    from app.services.research_event_bus import ResearchEventBus

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)  # no dedup key
    mock_redis.xadd = AsyncMock(return_value="1234-0")

    bus = ResearchEventBus(redis_client=mock_redis)
    result = _run(
        bus.emit(
            topic="SARB interest rate",
            domain="financial",
            trigger_type="stale_access",
            suggested_depth="quick",
            priority="medium",
        )
    )

    assert result["success"] is True
    mock_redis.xadd.assert_awaited_once()
    call_args = mock_redis.xadd.call_args
    assert call_args[0][0] == "research:events"  # stream name


def test_emit_deduplicates_within_window():
    """Same topic+domain within dedup window is skipped."""
    from app.services.research_event_bus import ResearchEventBus

    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="1234-0")
    mock_redis.get = AsyncMock(return_value="1")  # dedup key exists

    bus = ResearchEventBus(redis_client=mock_redis)
    result = _run(
        bus.emit(
            topic="SARB interest rate",
            domain="financial",
            trigger_type="stale_access",
            suggested_depth="quick",
        )
    )

    assert result["success"] is True
    assert result.get("deduplicated") is True
    mock_redis.xadd.assert_not_awaited()


def test_emit_handles_redis_failure():
    """Event emission fails gracefully on Redis error."""
    from app.services.research_event_bus import ResearchEventBus

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.xadd = AsyncMock(side_effect=Exception("Redis down"))

    bus = ResearchEventBus(redis_client=mock_redis)
    result = _run(
        bus.emit(
            topic="test",
            domain="financial",
            trigger_type="stale_access",
            suggested_depth="quick",
        )
    )

    assert result["success"] is False


def test_consume_reads_from_stream():
    """Consumer reads events from Redis Stream."""
    from app.services.research_event_bus import ResearchEventBus

    mock_redis = AsyncMock()
    # Simulate one event in stream, then empty
    mock_redis.xreadgroup = AsyncMock(
        side_effect=[
            [
                [
                    "research:events",
                    [
                        (
                            "1234-0",
                            {
                                "data": json.dumps(
                                    {
                                        "topic": "test",
                                        "domain": "financial",
                                        "trigger_type": "stale_access",
                                        "suggested_depth": "quick",
                                        "priority": "medium",
                                    }
                                )
                            },
                        )
                    ],
                ]
            ],
            [],  # empty on second call
        ]
    )
    mock_redis.xack = AsyncMock()

    bus = ResearchEventBus(redis_client=mock_redis)
    events = _run(bus.consume_batch(max_events=10))

    assert len(events) == 1
    assert events[0]["topic"] == "test"
    assert events[0]["domain"] == "financial"


def test_dedup_window_per_trigger_type():
    """Different trigger types have different dedup windows."""
    from app.services.research_event_bus import DEDUP_WINDOWS

    assert DEDUP_WINDOWS["coverage_gap"] > DEDUP_WINDOWS["stale_access"]
    assert DEDUP_WINDOWS["user_feedback"] <= 3600  # max 1 hour
