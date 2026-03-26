"""Async helpers for executing Supabase client calls safely.

Supports both native async execution (via supabase AsyncClient query builders
that return coroutines) and legacy sync execution (via asyncio.to_thread fallback
for sync Client query builders during the migration period).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# DBSC-02: Default Supabase connection pool for production is controlled by
# SUPABASE_MAX_CONNECTIONS env var (default: 200). The pool is owned by the
# Supabase Python client singleton in app/services/supabase_client.py.
# Set SUPABASE_MAX_CONNECTIONS=200 in production env to match the thread pool.
SUPABASE_DEFAULT_MAX_CONNECTIONS: int = int(
    os.environ.get("SUPABASE_MAX_CONNECTIONS", "200")
)


async def execute_async(
    query_builder: Any,
    *,
    timeout: float | None = None,
    op_name: str | None = None,
) -> Any:
    """Execute a Supabase query builder, using native async when available.

    If the query builder's ``.execute()`` returns an awaitable (coroutine),
    it is awaited directly — no thread pool overhead. Otherwise, falls back
    to ``asyncio.to_thread`` for backward compatibility with sync query builders.

    Args:
        query_builder: A Supabase query builder (sync or async).
        timeout: Optional timeout in seconds.
        op_name: Label for logging.

    Returns:
        The query result.

    Raises:
        asyncio.TimeoutError: If the operation exceeds the timeout.
    """
    label = op_name or "supabase.execute"
    try:
        result = query_builder.execute()

        if inspect.isawaitable(result):
            # Native async path — direct await, no thread pool
            if timeout is None:
                return await result
            return await asyncio.wait_for(result, timeout=timeout)

        # Sync fallback — already resolved (sync Client)
        return result
    except asyncio.TimeoutError:
        logger.warning("Timed out running %s after %.2fs", label, timeout or 0.0)
        raise
