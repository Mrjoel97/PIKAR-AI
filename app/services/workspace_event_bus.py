# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Per-user workspace SSE channel manager backed by Redis pub/sub.

Reuses the singleton :class:`~app.services.cache.CacheService` Redis client so
we share its circuit breaker and connection pool. Channel naming follows the
``REDIS_KEY_PREFIXES`` convention: ``pikar:workspace:{user_id}``.

The bus is *presentation-only*. Durable state lives in ``agent_task_executions``
and the publication sinks. ``publish`` therefore degrades silently when Redis
is unavailable (it never raises), and ``subscribe`` yields nothing instead of
exploding when the client is down -- the SSE endpoint keeps the connection
warm via heartbeats.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Union
from uuid import UUID

from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.agents.runtime.types import (
    WorkspaceArtifactEvent,
    WorkspaceProgressEvent,
)
from app.services.cache import get_cache_service

logger = logging.getLogger(__name__)

WorkspaceEvent = Union[WorkspaceProgressEvent, WorkspaceArtifactEvent]

# Matches REDIS_KEY_PREFIXES convention in app/services/cache.py.
_CHANNEL_PREFIX = "pikar:workspace:"


def _channel_for(user_id: UUID) -> str:
    """Return the Redis pub/sub channel for a given user."""
    return f"{_CHANNEL_PREFIX}{user_id}"


async def publish(user_id: UUID, event: WorkspaceEvent) -> None:
    """Best-effort publish onto the user's workspace channel.

    Silently degrades when Redis is unavailable -- workspace events are
    presentation-only; durable state lives elsewhere.
    """
    cache = get_cache_service()
    try:
        client = await cache._ensure_connection()
    except (RedisConnectionError, RedisTimeoutError) as exc:
        logger.warning("workspace_event_bus.publish: Redis connect failed: %s", exc)
        return

    if client is None:
        return

    payload = event.model_dump_json()
    try:
        await client.publish(_channel_for(user_id), payload)
    except (RedisConnectionError, RedisTimeoutError) as exc:
        logger.warning("workspace_event_bus.publish: publish failed: %s", exc)
    except Exception as exc:  # noqa: BLE001 -- never crash callers
        logger.exception("workspace_event_bus.publish: unexpected error: %s", exc)


async def subscribe(user_id: UUID) -> AsyncIterator[WorkspaceEvent]:
    """Subscribe to the user's workspace channel.

    Yields parsed :class:`WorkspaceProgressEvent` and
    :class:`WorkspaceArtifactEvent` instances. Malformed JSON payloads and
    unknown event kinds are logged and skipped -- never raised.

    When Redis is unavailable, the iterator terminates immediately; the SSE
    endpoint keeps the HTTP connection alive via heartbeats.
    """
    cache = get_cache_service()
    try:
        client = await cache._ensure_connection()
    except (RedisConnectionError, RedisTimeoutError) as exc:
        logger.warning("workspace_event_bus.subscribe: Redis connect failed: %s", exc)
        return

    if client is None:
        logger.info("workspace_event_bus.subscribe: Redis unavailable, no events")
        return

    pubsub = client.pubsub()
    await pubsub.subscribe(_channel_for(user_id))
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            raw = message.get("data")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            try:
                data = json.loads(raw)
            except (TypeError, ValueError):
                logger.warning(
                    "workspace_event_bus: discarding bad payload: %r", raw
                )
                continue
            kind = data.get("kind") if isinstance(data, dict) else None
            if kind == "progress":
                try:
                    yield WorkspaceProgressEvent.model_validate(data)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "workspace_event_bus: invalid progress payload: %s", exc
                    )
                    continue
            elif kind == "artifact":
                try:
                    yield WorkspaceArtifactEvent.model_validate(data)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "workspace_event_bus: invalid artifact payload: %s", exc
                    )
                    continue
            else:
                logger.warning("workspace_event_bus: unknown kind=%r", kind)
                continue
    finally:
        try:
            await pubsub.unsubscribe(_channel_for(user_id))
            await pubsub.close()
        except Exception:  # noqa: BLE001
            pass


__all__ = ["WorkspaceEvent", "publish", "subscribe"]
