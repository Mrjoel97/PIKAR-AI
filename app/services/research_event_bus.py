# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Research event bus using Redis Streams.

Provides persistent, at-least-once event delivery for research triggers.
Uses Redis Streams (XADD/XREADGROUP) instead of pub/sub because:
- Messages persist if the consumer is temporarily down
- Consumer groups enable distributed processing
- Acknowledgement (XACK) prevents message loss

Events trigger background research when:
- Coverage gaps are detected by self-improvement
- graph_read encounters stale data
- User gives negative feedback
- External webhooks signal changes
- Cross-domain entity updates propagate
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

STREAM_NAME = "research:events"
CONSUMER_GROUP = "intelligence-workers"
CONSUMER_NAME = "worker-1"

# Dedup windows in seconds per trigger type
DEDUP_WINDOWS: dict[str, int] = {
    "coverage_gap": 86400,  # 24 hours
    "low_confidence": 14400,  # 4 hours
    "stale_access": 3600,  # 1 hour
    "user_feedback": 3600,  # 1 hour
    "external_webhook": 7200,  # 2 hours
    "cross_domain": 28800,  # 8 hours
}

MAX_CONCURRENT_RESEARCH = 3
EVENT_QUEUE_MAX = 50


class ResearchEventBus:
    """Redis Streams-based event bus for research triggers."""

    def __init__(self, redis_client: Any = None) -> None:
        """Initialize with a Redis client.

        Args:
            redis_client: An async Redis client. If None, uses the
                CacheService's internal Redis connection.
        """
        self._redis = redis_client

    async def _get_redis(self):
        """Get or create Redis client."""
        if self._redis is not None:
            return self._redis
        from app.services.cache import get_cache_service

        cache = get_cache_service()
        if not cache._connected:
            await cache.connect()
        self._redis = cache._redis
        return self._redis

    async def emit(
        self,
        topic: str,
        domain: str,
        trigger_type: str,
        suggested_depth: str = "standard",
        priority: str = "medium",
        source_agent: str | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Publish a research event to the stream.

        Deduplicates within the trigger type's time window to prevent
        redundant research on the same topic.

        Args:
            topic: Research topic or query.
            domain: Agent domain.
            trigger_type: What triggered this event.
            suggested_depth: Recommended research depth.
            priority: Event priority (critical, high, medium, low).
            source_agent: Which agent triggered this.
            metadata: Additional context.

        Returns:
            Dict with success flag and optional dedup/event_id info.
        """
        try:
            redis = await self._get_redis()

            # Check dedup
            dedup_key = self._make_dedup_key(topic, domain, trigger_type)
            existing = await redis.get(dedup_key)
            if existing:
                logger.debug("Dedup hit for %s/%s/%s", topic, domain, trigger_type)
                return {"success": True, "deduplicated": True, "dedup_key": dedup_key}

            # Build event payload
            event = {
                "topic": topic,
                "domain": domain,
                "trigger_type": trigger_type,
                "suggested_depth": suggested_depth,
                "priority": priority,
                "source_agent": source_agent or "",
                "metadata": json.dumps(metadata or {}),
            }

            # Publish to stream
            event_id = await redis.xadd(
                STREAM_NAME,
                {"data": json.dumps(event)},
                maxlen=EVENT_QUEUE_MAX * 10,  # keep last 500 events
            )

            # Set dedup key with TTL
            dedup_ttl = DEDUP_WINDOWS.get(trigger_type, 3600)
            await redis.set(dedup_key, "1", ex=dedup_ttl)

            logger.info(
                "Research event emitted: %s/%s/%s (id=%s)",
                trigger_type,
                domain,
                topic[:50],
                event_id,
            )
            return {"success": True, "event_id": event_id, "deduplicated": False}

        except Exception as e:
            logger.warning("Failed to emit research event: %s", e)
            return {"success": False, "error": str(e)}

    async def consume_batch(
        self,
        max_events: int = 10,
        block_ms: int = 0,
    ) -> list[dict[str, Any]]:
        """Read a batch of events from the stream.

        Uses consumer groups for at-least-once delivery.

        Args:
            max_events: Max events to read in one batch.
            block_ms: How long to block waiting for events (0 = no block).

        Returns:
            List of event dicts.
        """
        try:
            redis = await self._get_redis()

            # Ensure consumer group exists
            try:
                await redis.xgroup_create(
                    STREAM_NAME,
                    CONSUMER_GROUP,
                    id="0",
                    mkstream=True,
                )
            except Exception:
                pass  # Group already exists

            # Read events
            results = await redis.xreadgroup(
                CONSUMER_GROUP,
                CONSUMER_NAME,
                {STREAM_NAME: ">"},
                count=max_events,
                block=block_ms,
            )

            if not results:
                return []

            events = []
            for _stream, messages in results:
                for msg_id, msg_data in messages:
                    try:
                        event = json.loads(msg_data.get("data", "{}"))
                        event["_msg_id"] = msg_id
                        events.append(event)
                    except (json.JSONDecodeError, AttributeError):
                        logger.warning("Invalid event data: %s", msg_data)
                        # Acknowledge bad messages to prevent reprocessing
                        await redis.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)

            return events

        except Exception as e:
            logger.error("Failed to consume events: %s", e)
            return []

    async def acknowledge(self, msg_id: str) -> bool:
        """Acknowledge a processed event.

        Args:
            msg_id: The Redis Stream message ID.

        Returns:
            True if acknowledged successfully.
        """
        try:
            redis = await self._get_redis()
            await redis.xack(STREAM_NAME, CONSUMER_GROUP, msg_id)
            return True
        except Exception as e:
            logger.warning("Failed to acknowledge %s: %s", msg_id, e)
            return False

    @staticmethod
    def _make_dedup_key(topic: str, domain: str, trigger_type: str) -> str:
        """Generate a dedup key for event deduplication."""
        content = f"{topic.lower().strip()}:{domain}:{trigger_type}"
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"research:dedup:{hash_val}"


# Module-level singleton
_event_bus: ResearchEventBus | None = None


def get_event_bus() -> ResearchEventBus:
    """Get the singleton event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = ResearchEventBus()
    return _event_bus
