# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""workspace_event_bus.subscribe -- yields typed events parsed from Redis."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime.types import (
    WorkspaceArtifactEvent,
    WorkspaceProgressEvent,
)
from app.services import workspace_event_bus


class _FakePubSub:
    """Async-iterable stand-in for redis.asyncio.client.PubSub."""

    def __init__(self, messages):
        self._messages = messages
        self.subscribe = AsyncMock()
        self.unsubscribe = AsyncMock()
        self.close = AsyncMock()

    async def listen(self):
        for m in self._messages:
            yield m


@pytest.mark.asyncio
async def test_subscribe_yields_progress_then_artifact(monkeypatch):
    """subscribe() parses bytes payloads into typed events on the channel."""
    user_id = uuid4()
    progress = WorkspaceProgressEvent(
        agent_id="data", contract_id=None, item="step-1", status="in_progress"
    )
    artifact = WorkspaceArtifactEvent(
        agent_id="data",
        contract_id=None,
        artifact_kind="report",
        ref="vault://abc",
        summary="Q3 numbers",
        preview_url=None,
    )

    messages = [
        {"type": "subscribe", "data": 1},  # control msg -- skipped
        {"type": "message", "data": progress.model_dump_json().encode()},
        {"type": "message", "data": artifact.model_dump_json().encode()},
    ]

    fake_pubsub = _FakePubSub(messages)
    fake_redis = MagicMock()
    fake_redis.pubsub = MagicMock(return_value=fake_pubsub)

    async def fake_ensure_connection(self):  # noqa: ARG001
        return fake_redis

    from app.services.cache import CacheService

    monkeypatch.setattr(CacheService, "_ensure_connection", fake_ensure_connection)

    received: list = []
    async for evt in workspace_event_bus.subscribe(user_id):
        received.append(evt)
        if len(received) == 2:
            break

    assert received[0] == progress
    assert received[1] == artifact
    fake_pubsub.subscribe.assert_awaited_once_with(f"pikar:workspace:{user_id}")


@pytest.mark.asyncio
async def test_subscribe_returns_immediately_when_redis_unavailable(monkeypatch):
    """When Redis is disabled, subscribe() yields nothing and exits cleanly."""
    user_id = uuid4()

    async def fake_ensure_connection(self):  # noqa: ARG001
        return None

    from app.services.cache import CacheService

    monkeypatch.setattr(CacheService, "_ensure_connection", fake_ensure_connection)

    received: list = []
    async for evt in workspace_event_bus.subscribe(user_id):
        received.append(evt)
    assert received == []


@pytest.mark.asyncio
async def test_subscribe_handles_redis_connect_error(monkeypatch):
    """If _ensure_connection raises a connection error, iterator exits cleanly."""
    from redis.exceptions import ConnectionError as RedisConnectionError

    user_id = uuid4()

    async def fake_ensure_connection(self):  # noqa: ARG001
        raise RedisConnectionError("disconnected")

    from app.services.cache import CacheService

    monkeypatch.setattr(CacheService, "_ensure_connection", fake_ensure_connection)

    received: list = []
    async for evt in workspace_event_bus.subscribe(user_id):
        received.append(evt)
    assert received == []
