"""Lightweight TTL cache for deterministic tool responses.

Caches read-heavy tool responses for a short TTL to avoid
redundant Supabase queries within the same conversation turn.
"""

import time
import logging
import functools
import asyncio
from typing import Any

logger = logging.getLogger(__name__)

# Cache: key -> (timestamp, value)
_cache: dict[str, tuple[float, Any]] = {}
DEFAULT_TTL = 30  # seconds


def get_cached(key: str) -> Any | None:
    """Get a cached value if still within TTL.

    Args:
        key: Cache key (typically tool_name:user_id or tool_name:user_id:args_hash).

    Returns:
        Cached value or None if expired/missing.
    """
    if key in _cache:
        ts, val = _cache[key]
        if time.monotonic() - ts < DEFAULT_TTL:
            logger.debug("[tool_cache] HIT: %s", key)
            return val
        # Expired — remove
        del _cache[key]
    return None


def set_cached(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    """Store a value in the cache.

    Args:
        key: Cache key.
        value: Value to cache.
        ttl: Time-to-live in seconds (default: 30).
    """
    _cache[key] = (time.monotonic(), value)
    logger.debug("[tool_cache] SET: %s (ttl=%ds)", key, ttl)


def cached_tool(key_fn, ttl: int = DEFAULT_TTL):
    """Decorator to auto-cache tool responses."""
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

    Args:
        prefix: Key prefix to match.

    Returns:
        Number of entries removed.
    """
    keys_to_remove = [k for k in _cache if k.startswith(prefix)]
    for k in keys_to_remove:
        del _cache[k]
    return len(keys_to_remove)


def clear() -> None:
    """Clear the entire cache."""
    _cache.clear()
