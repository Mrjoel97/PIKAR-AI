# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""workspace_event_bus.publish -- Redis pub/sub happy path and degraded mode."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agents.runtime.types import WorkspaceProgressEvent
from app.services import workspace_event_bus


@pytest.mark.asyncio
async def test_publish_emits_on_user_channel(monkeypatch):
    """publish() forwards the JSON-encoded event onto pikar:workspace:{uid}."""
    user_id = uuid4()
    fake_redis = AsyncMock()
    fake_redis.publish = AsyncMock(return_value=1)

    async def fake_ensure_connection(self):  # noqa: ARG001
        return fake_redis

    from app.services.cache import CacheService

    monkeypatch.setattr(CacheService, "_ensure_connection", fake_ensure_connection)

    event = WorkspaceProgressEvent(
        agent_id="financial",
        contract_id=uuid4(),
        item="Read income statement",
        status="started",
    )
    await workspace_event_bus.publish(user_id, event)

    assert fake_redis.publish.await_count == 1
    channel, payload = fake_redis.publish.await_args.args
    assert channel == f"pikar:workspace:{user_id}"
    assert '"kind":"progress"' in payload
    assert '"status":"started"' in payload


@pytest.mark.asyncio
async def test_publish_noop_when_redis_unavailable(monkeypatch):
    """publish() must not raise when Redis is disabled or down (degraded mode)."""
    user_id = uuid4()

    async def fake_ensure_connection(self):  # noqa: ARG001
        return None

    from app.services.cache import CacheService

    monkeypatch.setattr(CacheService, "_ensure_connection", fake_ensure_connection)

    event = WorkspaceProgressEvent(
        agent_id="financial",
        contract_id=None,
        item="x",
        status="started",
    )
    # Must not raise -- matches circuit-breaker contract.
    await workspace_event_bus.publish(user_id, event)


@pytest.mark.asyncio
async def test_publish_swallows_redis_connection_error(monkeypatch):
    """publish() must swallow Redis connection failures during publish()."""
    from redis.exceptions import ConnectionError as RedisConnectionError

    user_id = uuid4()
    fake_redis = AsyncMock()
    fake_redis.publish = AsyncMock(side_effect=RedisConnectionError("nope"))

    async def fake_ensure_connection(self):  # noqa: ARG001
        return fake_redis

    from app.services.cache import CacheService

    monkeypatch.setattr(CacheService, "_ensure_connection", fake_ensure_connection)

    event = WorkspaceProgressEvent(
        agent_id="financial",
        contract_id=None,
        item="x",
        status="started",
    )
    # Must not raise.
    await workspace_event_bus.publish(user_id, event)
    assert fake_redis.publish.await_count == 1
