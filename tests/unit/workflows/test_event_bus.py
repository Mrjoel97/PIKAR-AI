"""Unit tests for the in-process workflow event bus."""

import asyncio

import pytest

from app.workflows.event_bus import publish_workflow_event, subscribe, unsubscribe


@pytest.mark.asyncio
async def test_subscribe_receives_published_event():
    q = await subscribe("test-channel")
    try:
        await publish_workflow_event("test-channel", {"hello": "world"})
        event = await asyncio.wait_for(q.get(), timeout=1.0)
        assert event == {"hello": "world"}
    finally:
        unsubscribe("test-channel", q)


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery():
    q = await subscribe("test-channel-2")
    unsubscribe("test-channel-2", q)
    await publish_workflow_event("test-channel-2", {"x": 1})
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(q.get(), timeout=0.1)


@pytest.mark.asyncio
async def test_publish_to_no_subscribers_is_noop():
    # Should not raise.
    await publish_workflow_event("nobody-listening", {"x": 1})
