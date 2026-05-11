"""Internal pub-sub for per-execution SSE delivery.

Backed by an in-process subscriber map. Redis pub/sub will be added later for
multi-replica setups; the in-memory path is enough for the current single-process
FastAPI deployment.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)

_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)


async def publish_workflow_event(channel: str, payload: dict[str, Any]) -> None:
    """Publish a workflow event to all in-process subscribers."""
    for q in list(_subscribers.get(channel, [])):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning("event_bus queue full on %s; dropping event", channel)


async def subscribe(channel: str) -> asyncio.Queue:
    """Subscribe to a channel and return the queue that receives events."""
    q: asyncio.Queue = asyncio.Queue(maxsize=128)
    _subscribers[channel].append(q)
    return q


def unsubscribe(channel: str, q: asyncio.Queue) -> None:
    """Remove a subscriber queue from a channel."""
    try:
        _subscribers[channel].remove(q)
    except ValueError:
        pass
