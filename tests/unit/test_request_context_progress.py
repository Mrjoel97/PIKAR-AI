import asyncio

import pytest

from app.services.request_context import (
    emit_progress_update,
    get_current_progress_queue,
    set_current_progress_queue,
)


@pytest.mark.asyncio
async def test_emit_progress_update_writes_to_queue():
    queue: asyncio.Queue[dict] = asyncio.Queue()
    set_current_progress_queue(queue)
    try:
        await emit_progress_update("planning_started", {"scene_count": 4})
        event = await queue.get()
        assert event["type"] == "director_progress"
        assert event["stage"] == "planning_started"
        assert event["payload"]["scene_count"] == 4
        assert get_current_progress_queue() is queue
    finally:
        set_current_progress_queue(None)

