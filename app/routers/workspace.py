# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Workspace SSE endpoint.

Streams :mod:`app.services.workspace_event_bus` events to the authenticated
user's browser for live updates of the ActiveWorkspace canvas. Frames follow
the SSE spec (``data: <json>\\n\\n``). During idle periods, a heartbeat
comment (``: heartbeat\\n\\n``) is emitted every 15 seconds so proxies and
load balancers don't drop the connection.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.routers.onboarding import get_current_user_id
from app.services import workspace_event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace", tags=["Workspace"])

# Patchable from tests; production value matches the spec.
_HEARTBEAT_INTERVAL_S = 15.0


async def _event_stream(user_id: UUID, request: Request) -> AsyncIterator[bytes]:
    """Yield SSE-formatted bytes from the user's workspace channel.

    Interleaves a heartbeat comment every ``_HEARTBEAT_INTERVAL_S`` seconds so
    intermediaries don't close the connection during quiet periods.
    """
    queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def _pump() -> None:
        try:
            async for event in workspace_event_bus.subscribe(user_id):
                await queue.put(
                    f"data: {event.model_dump_json()}\n\n".encode()
                )
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("workspace SSE pump failed for user %s", user_id)
        finally:
            await queue.put(None)

    pump_task = asyncio.create_task(_pump())
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                item = await asyncio.wait_for(
                    queue.get(), timeout=_HEARTBEAT_INTERVAL_S
                )
            except asyncio.TimeoutError:
                yield b": heartbeat\n\n"
                continue
            if item is None:
                break
            yield item
    finally:
        pump_task.cancel()
        try:
            await pump_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass


@router.get("/events")
async def workspace_events(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    """SSE stream of workspace progress + artifact events for the current user."""
    return StreamingResponse(
        _event_stream(UUID(user_id), request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


__all__ = ["router"]
