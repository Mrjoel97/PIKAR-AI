# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""subscribe must skip junk payloads -- workspace UX should never crash."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.runtime.types import WorkspaceProgressEvent
from app.services import workspace_event_bus


class _FakePubSub:
    def __init__(self, messages):
        self._messages = messages
        self.subscribe = AsyncMock()
        self.unsubscribe = AsyncMock()
        self.close = AsyncMock()

    async def listen(self):
        for m in self._messages:
            yield m


@pytest.mark.asyncio
async def test_subscribe_skips_bad_json_and_unknown_kinds(monkeypatch):
    """Malformed JSON and unknown ``kind`` values must be skipped silently."""
    user_id = uuid4()
    good = WorkspaceProgressEvent(
        agent_id="data", contract_id=None, item="step", status="started"
    )
    messages = [
        {"type": "message", "data": b"not-json"},
        {"type": "message", "data": b'{"kind":"telepathy"}'},
        {"type": "message", "data": good.model_dump_json().encode()},
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
        break

    assert received == [good]


@pytest.mark.asyncio
async def test_subscribe_skips_invalid_progress_payload(monkeypatch):
    """A payload whose kind=progress but missing required fields is dropped."""
    user_id = uuid4()
    good = WorkspaceProgressEvent(
        agent_id="data", contract_id=None, item="step", status="started"
    )
    messages = [
        # missing item/status -> ValidationError
        {"type": "message", "data": b'{"kind":"progress","agent_id":"x"}'},
        {"type": "message", "data": good.model_dump_json().encode()},
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
        break

    assert received == [good]
