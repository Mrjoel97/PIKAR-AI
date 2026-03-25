# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Redis-backed async SSE connection limits for authenticated users.

Enforces per-user slot limits and server-wide backpressure identically across
all Cloud Run replicas using Redis INCR/DECR with TTL-based stale cleanup.

Key design:
- Per-user connection slot:  pikar:sse:conn:{user_id}  (INCR/DECR, 5-min TTL)
- Per-user rate limit:       pikar:sse:rate:{user_id}  (INCR, 60-s sliding window)
- Total count via SCAN of    pikar:sse:conn:* keys
"""

from __future__ import annotations

import logging
import os

from app.services.cache import get_cache_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public constants / enums
# ---------------------------------------------------------------------------

DEFAULT_SSE_MAX_CONNECTIONS_PER_USER = 3
DEFAULT_SSE_MAX_NEW_CONN_PER_MINUTE = 10
DEFAULT_SSE_MAX_TOTAL_CONNECTIONS = 500
DEFAULT_SSE_CONN_TTL_SECONDS = 300  # 5 minutes — covers process-crash orphan cleanup


class SSERejectReason(str):
    """Sentinel strings for why an SSE acquire was rejected."""

    PER_USER_LIMIT = "per_user_limit"
    PER_USER_RATE = "per_user_rate"
    SERVER_BACKPRESSURE = "server_backpressure"


# Re-export as enum-style constants so callers can do:
#   from app.services.sse_connection_limits import SSERejectReason
#   result.reason == SSERejectReason.SERVER_BACKPRESSURE
SSERejectReason.PER_USER_LIMIT = SSERejectReason("per_user_limit")
SSERejectReason.PER_USER_RATE = SSERejectReason("per_user_rate")
SSERejectReason.SERVER_BACKPRESSURE = SSERejectReason("server_backpressure")


class SSEAcquireResult(tuple):
    """Named result that is also tuple-unpackable as (acquired, active, limit).

    Attributes
    ----------
    acquired : bool
    active   : int
    limit    : int
    reason   : SSERejectReason | None  — set when acquired is False
    """

    acquired: bool
    active: int
    limit: int
    reason: SSERejectReason | None

    def __new__(
        cls,
        acquired: bool,
        active: int,
        limit: int,
        reason: SSERejectReason | None = None,
    ) -> SSEAcquireResult:
        """Create a new SSEAcquireResult."""
        instance = super().__new__(cls, (acquired, active, limit))
        instance.acquired = acquired
        instance.active = active
        instance.limit = limit
        instance.reason = reason
        return instance


# ---------------------------------------------------------------------------
# Redis key helpers
# ---------------------------------------------------------------------------

_CONN_KEY_PREFIX = "pikar:sse:conn:"
_RATE_KEY_PREFIX = "pikar:sse:rate:"


def _conn_key(user_id: str) -> str:
    return f"{_CONN_KEY_PREFIX}{user_id}"


def _rate_key(user_id: str) -> str:
    return f"{_RATE_KEY_PREFIX}{user_id}"


# ---------------------------------------------------------------------------
# Sync helpers (env reads — no I/O)
# ---------------------------------------------------------------------------


def get_sse_connection_limit() -> int:
    """Return the configured per-user SSE connection limit (reads env at call time)."""
    raw_value = (os.getenv("SSE_MAX_CONNECTIONS_PER_USER") or "").strip()
    if not raw_value:
        return DEFAULT_SSE_MAX_CONNECTIONS_PER_USER
    try:
        parsed_value = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid SSE_MAX_CONNECTIONS_PER_USER=%r; using default %s",
            raw_value,
            DEFAULT_SSE_MAX_CONNECTIONS_PER_USER,
        )
        return DEFAULT_SSE_MAX_CONNECTIONS_PER_USER
    if parsed_value < 1:
        logger.warning(
            "SSE_MAX_CONNECTIONS_PER_USER must be >= 1; using default %s",
            DEFAULT_SSE_MAX_CONNECTIONS_PER_USER,
        )
        return DEFAULT_SSE_MAX_CONNECTIONS_PER_USER
    return parsed_value


def _get_max_new_conn_per_minute() -> int:
    raw = (os.getenv("SSE_MAX_NEW_CONN_PER_MINUTE") or "").strip()
    if not raw:
        return DEFAULT_SSE_MAX_NEW_CONN_PER_MINUTE
    try:
        v = int(raw)
        return v if v >= 1 else DEFAULT_SSE_MAX_NEW_CONN_PER_MINUTE
    except ValueError:
        return DEFAULT_SSE_MAX_NEW_CONN_PER_MINUTE


def _get_max_total_connections() -> int:
    raw = (os.getenv("SSE_MAX_TOTAL_CONNECTIONS") or "").strip()
    if not raw:
        return DEFAULT_SSE_MAX_TOTAL_CONNECTIONS
    try:
        v = int(raw)
        return v if v >= 1 else DEFAULT_SSE_MAX_TOTAL_CONNECTIONS
    except ValueError:
        return DEFAULT_SSE_MAX_TOTAL_CONNECTIONS


def _get_conn_ttl() -> int:
    raw = (os.getenv("SSE_CONN_TTL_SECONDS") or "").strip()
    if not raw:
        return DEFAULT_SSE_CONN_TTL_SECONDS
    try:
        v = int(raw)
        return v if v >= 1 else DEFAULT_SSE_CONN_TTL_SECONDS
    except ValueError:
        return DEFAULT_SSE_CONN_TTL_SECONDS


# ---------------------------------------------------------------------------
# Async public API
# ---------------------------------------------------------------------------


async def get_total_active_sse_count() -> int:
    """Return sum of all active SSE connection counts across all users.

    Uses SCAN to iterate pikar:sse:conn:* keys and sums their values.
    Returns 0 if Redis is unavailable.
    """
    try:
        redis = await get_cache_service()._ensure_connection()
        if redis is None:
            logger.warning("get_total_active_sse_count: Redis unavailable, returning 0")
            return 0

        total = 0
        cursor = 0
        while True:
            cursor, keys = await redis.scan(
                cursor, match=f"{_CONN_KEY_PREFIX}*", count=1000
            )
            for key in keys:
                raw = await redis.get(key)
                if raw is not None:
                    try:
                        total += int(raw)
                    except (ValueError, TypeError):
                        pass
            if cursor == 0:
                break
        return total
    except Exception:
        logger.warning("get_total_active_sse_count: Redis error, returning 0", exc_info=True)
        return 0


async def try_acquire_sse_connection(
    user_id: str, *, stream_name: str
) -> SSEAcquireResult:
    """Try to reserve an SSE connection slot for the user.

    Steps:
    1. Fail open if Redis is unavailable.
    2. Server-wide backpressure check — return SERVER_BACKPRESSURE if at cap.
    3. Per-user rate check — return PER_USER_RATE if too many new conns/min.
    4. Per-user slot check — return PER_USER_LIMIT if user at slot limit.
    5. INCR slot counter with TTL refresh.

    Returns
    -------
    SSEAcquireResult — tuple-unpackable as (acquired, active, limit).
    """
    limit = get_sse_connection_limit()

    try:
        redis = await get_cache_service()._ensure_connection()
    except Exception:
        logger.warning(
            "try_acquire_sse_connection: failed to get Redis client for user=%s on %s, failing open",
            user_id,
            stream_name,
        )
        return SSEAcquireResult(True, 0, limit)

    if redis is None:
        logger.warning(
            "try_acquire_sse_connection: Redis unavailable for user=%s on %s, failing open",
            user_id,
            stream_name,
        )
        return SSEAcquireResult(True, 0, limit)

    # --- Step 2: Server-wide backpressure ---
    max_total = _get_max_total_connections()
    try:
        current_total = await get_total_active_sse_count()
        if current_total >= max_total:
            logger.warning(
                "SSE server backpressure: total active=%s >= max=%s (user=%s stream=%s)",
                current_total,
                max_total,
                user_id,
                stream_name,
            )
            # Return current user count as active (best effort)
            raw_user = await redis.get(_conn_key(user_id))
            current_user = int(raw_user) if raw_user else 0
            return SSEAcquireResult(
                False, current_user, limit, reason=SSERejectReason.SERVER_BACKPRESSURE
            )
    except Exception:
        logger.warning(
            "try_acquire_sse_connection: backpressure check error for user=%s, continuing",
            user_id,
            exc_info=True,
        )

    # --- Step 3: Per-user rate limit ---
    max_rate = _get_max_new_conn_per_minute()
    try:
        rate_count = await redis.incr(_rate_key(user_id))
        if rate_count == 1:
            # First call in this window — set 60-second expiry
            await redis.expire(_rate_key(user_id), 60)
        if rate_count > max_rate:
            logger.warning(
                "SSE rate limit exceeded for user=%s on %s (%s/%s new conns/min)",
                user_id,
                stream_name,
                rate_count,
                max_rate,
            )
            raw_user = await redis.get(_conn_key(user_id))
            current_user = int(raw_user) if raw_user else 0
            return SSEAcquireResult(
                False, current_user, limit, reason=SSERejectReason.PER_USER_RATE
            )
    except Exception:
        logger.warning(
            "try_acquire_sse_connection: rate check error for user=%s, continuing",
            user_id,
            exc_info=True,
        )

    # --- Step 4: Per-user slot check ---
    try:
        raw_count = await redis.get(_conn_key(user_id))
        current_user_count = int(raw_count) if raw_count else 0
        if current_user_count >= limit:
            logger.warning(
                "SSE connection limit exceeded for user=%s on %s (%s/%s)",
                user_id,
                stream_name,
                current_user_count,
                limit,
            )
            return SSEAcquireResult(
                False, current_user_count, limit, reason=SSERejectReason.PER_USER_LIMIT
            )
    except Exception:
        logger.warning(
            "try_acquire_sse_connection: slot check error for user=%s, continuing",
            user_id,
            exc_info=True,
        )

    # --- Step 5: Acquire slot ---
    try:
        ttl = _get_conn_ttl()
        new_count = await redis.incr(_conn_key(user_id))
        await redis.expire(_conn_key(user_id), ttl)
        logger.debug(
            "SSE connection acquired for user=%s on %s (%s/%s)",
            user_id,
            stream_name,
            new_count,
            limit,
        )
        return SSEAcquireResult(True, new_count, limit)
    except Exception:
        logger.warning(
            "try_acquire_sse_connection: acquire error for user=%s, failing open",
            user_id,
            exc_info=True,
        )
        return SSEAcquireResult(True, 0, limit)


async def release_sse_connection(user_id: str, *, stream_name: str) -> int:
    """Release a previously acquired SSE connection slot.

    Decrements the Redis counter. Deletes the key when count reaches 0.
    Returns 0 and logs a warning if Redis is unavailable (fail open).
    """
    try:
        redis = await get_cache_service()._ensure_connection()
    except Exception:
        logger.warning(
            "release_sse_connection: failed to get Redis client for user=%s on %s",
            user_id,
            stream_name,
        )
        return 0

    if redis is None:
        logger.warning(
            "release_sse_connection: Redis unavailable for user=%s on %s",
            user_id,
            stream_name,
        )
        return 0

    try:
        result = await redis.decr(_conn_key(user_id))
        if result <= 0:
            await redis.delete(_conn_key(user_id))
            remaining = 0
        else:
            ttl = _get_conn_ttl()
            await redis.expire(_conn_key(user_id), ttl)
            remaining = result
        logger.debug(
            "SSE connection released for user=%s on %s (%s active remaining)",
            user_id,
            stream_name,
            remaining,
        )
        return remaining
    except Exception:
        logger.warning(
            "release_sse_connection: Redis error for user=%s on %s",
            user_id,
            stream_name,
            exc_info=True,
        )
        return 0


async def get_active_sse_connection_count(user_id: str) -> int:
    """Return the current number of open SSE connections for the user."""
    try:
        redis = await get_cache_service()._ensure_connection()
        if redis is None:
            return 0
        raw = await redis.get(_conn_key(user_id))
        return int(raw) if raw else 0
    except Exception:
        logger.warning(
            "get_active_sse_connection_count: Redis error for user=%s", user_id, exc_info=True
        )
        return 0


async def reset_sse_connection_limits() -> None:
    """Clear all pikar:sse:* keys in Redis. Used by tests for isolation."""
    try:
        redis = await get_cache_service()._ensure_connection()
        if redis is None:
            logger.warning("reset_sse_connection_limits: Redis unavailable, skipping")
            return

        cursor = 0
        keys_to_delete: list[bytes] = []
        while True:
            cursor, keys = await redis.scan(cursor, match="pikar:sse:*", count=1000)
            keys_to_delete.extend(keys)
            if cursor == 0:
                break

        if keys_to_delete:
            async with redis.pipeline() as pipe:
                for key in keys_to_delete:
                    pipe.delete(key)
                await pipe.execute()
        logger.debug("reset_sse_connection_limits: deleted %s keys", len(keys_to_delete))
    except Exception:
        logger.warning("reset_sse_connection_limits: Redis error", exc_info=True)
