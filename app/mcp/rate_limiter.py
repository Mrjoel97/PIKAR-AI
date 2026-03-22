"""Simple in-memory token-bucket rate limiter for MCP external API calls.

WARNING: This rate limiter is per-process only. Under multi-instance deployment
(e.g., Cloud Run with N replicas), the effective rate limit is N * rate_per_minute.
For production, back this with Redis for distributed rate limiting.
"""

import asyncio
import time


class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(self, rate_per_minute: int):
        self._rate = rate_per_minute
        self._tokens = float(rate_per_minute)
        self._max_tokens = float(rate_per_minute)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Try to acquire a token. Returns True if allowed, False if rate limited."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self._max_tokens,
                self._tokens + elapsed * (self._rate / 60.0),
            )
            self._last_refill = now

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False


_buckets: dict[str, TokenBucket] = {}
_buckets_lock = asyncio.Lock()


async def check_rate_limit(operation: str, rate_per_minute: int) -> bool:
    """Check if an operation is within its rate limit.

    Args:
        operation: Name of the operation (e.g., "search", "scrape", "crawl").
        rate_per_minute: Maximum operations per minute.

    Returns:
        True if allowed, False if rate limited.
    """
    async with _buckets_lock:
        if operation not in _buckets:
            _buckets[operation] = TokenBucket(rate_per_minute)

    return await _buckets[operation].acquire()
