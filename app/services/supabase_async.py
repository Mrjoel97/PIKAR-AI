"""Async helpers for executing blocking Supabase Python client calls safely."""

from __future__ import annotations

import asyncio
import logging
from typing import Any


logger = logging.getLogger(__name__)


async def execute_async(
    query_builder: Any,
    *,
    timeout: float | None = None,
    op_name: str | None = None,
) -> Any:
    """Run ``query_builder.execute()`` in a worker thread.

    The Supabase Python client ``execute()`` call is blocking. In FastAPI async
    routes/services, use this helper to avoid blocking the event loop.
    """

    label = op_name or "supabase.execute"
    try:
        task = asyncio.to_thread(query_builder.execute)
        if timeout is None:
            return await task
        return await asyncio.wait_for(task, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning("Timed out running %s after %.2fs", label, timeout or 0.0)
        raise
