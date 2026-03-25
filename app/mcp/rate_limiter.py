# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Redis-backed sliding-window rate limiter for MCP external API calls.

Replaces per-process TokenBucket with distributed Redis counter shared
across all Cloud Run replicas. Fails open when Redis is unavailable so
MCP tool calls are never blocked by Redis downtime.
"""

from __future__ import annotations

import logging
import time as _time

logger = logging.getLogger(__name__)


async def check_rate_limit(operation: str, rate_per_minute: int) -> bool:
    """Check if an MCP operation is within its rate limit.

    Uses Redis sliding window keyed by operation name + minute bucket.
    Fails open (returns True) if Redis is unavailable.

    Args:
        operation: Name of the operation (e.g., 'search', 'scrape', 'crawl').
        rate_per_minute: Maximum operations per minute across all replicas.

    Returns:
        True if allowed, False if rate limited.
    """
    from app.services.cache import REDIS_KEY_PREFIXES, get_cache_service

    prefix = REDIS_KEY_PREFIXES["rate_limit"]
    now = int(_time.time())
    window_start = (now // 60) * 60
    key = f"{prefix}mcp:{operation}:{window_start}"

    try:
        cache = get_cache_service()
        client = await cache._ensure_connection()
        if client is None:
            logger.warning(
                "Redis unavailable for MCP rate limiter (%s), failing open", operation
            )
            return True

        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 65)  # 60s window + 5s buffer
        results = await pipe.execute()
        count = int(results[0])

        if count > rate_per_minute:
            logger.warning(
                "MCP rate limit exceeded for operation=%s count=%s limit=%s",
                operation,
                count,
                rate_per_minute,
            )
            return False
        return True
    except Exception as exc:
        logger.warning(
            "MCP rate limiter Redis error for operation=%s: %s — failing open",
            operation,
            exc,
        )
        return True
