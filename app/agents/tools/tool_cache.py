# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Lightweight bounded TTL cache for deterministic tool responses.

Caches read-heavy tool responses for a short TTL to avoid
redundant Supabase queries within the same conversation turn.

Cache design:
- Backed by cachetools.TTLCache — bounded by maxsize AND time.
- Entries auto-expire after DEFAULT_TTL seconds (cache-wide TTL).
- Once maxsize is reached, the least-recently-used entry is evicted.
- The ``ttl`` parameter on set_cached is retained for API compatibility;
  the cache-wide TTL of DEFAULT_TTL seconds governs actual expiry.
"""

import asyncio
import functools
import logging
from typing import Any

import cachetools

logger = logging.getLogger(__name__)

DEFAULT_TTL = 30  # seconds (cache-wide)
MAX_CACHE_SIZE = 10_000

# Bounded TTL cache — entries auto-expire and total size is capped.
# Uses cachetools.TTLCache which evicts LRU entries when maxsize is exceeded
# and automatically expires stale entries on access.
_cache: cachetools.TTLCache = cachetools.TTLCache(maxsize=MAX_CACHE_SIZE, ttl=DEFAULT_TTL)


def get_cached(key: str) -> Any | None:
    """Get a cached value if present and not expired.

    Args:
        key: Cache key (typically tool_name:user_id or tool_name:user_id:args_hash).

    Returns:
        Cached value or None if expired/missing.
    """
    val = _cache.get(key)
    if val is not None:
        logger.debug("[tool_cache] HIT: %s", key)
        return val
    return None


def set_cached(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    """Store a value in the cache.

    Args:
        key: Cache key.
        value: Value to cache.
        ttl: Time-to-live in seconds (accepted for API compatibility;
             the cache-wide TTL of DEFAULT_TTL seconds governs actual expiry).
    """
    _cache[key] = value
    logger.debug("[tool_cache] SET: %s (ttl=%ds)", key, ttl)


def cached_tool(key_fn, ttl: int = DEFAULT_TTL):
    """Decorator to auto-cache tool responses.

    Args:
        key_fn: Callable that takes the same args as the decorated function
                and returns a string cache key.
        ttl: TTL hint (passed through to set_cached for API compatibility).
    """

    def decorator(fn):
        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            key = key_fn(*args, **kwargs)
            cached = get_cached(key)
            if cached is not None:
                return cached
            result = await fn(*args, **kwargs)
            set_cached(key, result, ttl)
            return result

        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            key = key_fn(*args, **kwargs)
            cached = get_cached(key)
            if cached is not None:
                return cached
            result = fn(*args, **kwargs)
            set_cached(key, result, ttl)
            return result

        return async_wrapper if asyncio.iscoroutinefunction(fn) else sync_wrapper

    return decorator


def invalidate(key: str) -> None:
    """Remove a specific key from cache."""
    _cache.pop(key, None)


def invalidate_prefix(prefix: str) -> int:
    """Remove all cache entries whose key starts with prefix.

    Useful for invalidating all entries for a specific tool (e.g., after a write).
    TTLCache is a dict subclass so we can iterate its keys safely after snapshotting.

    Args:
        prefix: Key prefix to match.

    Returns:
        Number of entries removed.
    """
    keys_to_remove = [k for k in list(_cache.keys()) if k.startswith(prefix)]
    for k in keys_to_remove:
        _cache.pop(k, None)
    return len(keys_to_remove)


def clear() -> None:
    """Clear the entire cache."""
    _cache.clear()
