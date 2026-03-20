"""Per-process SSE connection limits for authenticated users."""

from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)

DEFAULT_SSE_MAX_CONNECTIONS_PER_USER = 3

# In-memory connection counts are per-process only. This is sufficient for the
# current deployment guardrail and keeps the hot path dependency-free.
_active_connection_counts: dict[str, int] = {}
_connection_lock = threading.Lock()


def get_sse_connection_limit() -> int:
    """Return the configured per-user SSE connection limit."""
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


def try_acquire_sse_connection(
    user_id: str, *, stream_name: str
) -> tuple[bool, int, int]:
    """Try to reserve an SSE connection slot for the user."""
    limit = get_sse_connection_limit()
    with _connection_lock:
        active_connections = _active_connection_counts.get(user_id, 0)
        if active_connections >= limit:
            logger.warning(
                "SSE connection limit exceeded for user %s on %s (%s/%s)",
                user_id,
                stream_name,
                active_connections,
                limit,
            )
            return False, active_connections, limit
        active_connections += 1
        _active_connection_counts[user_id] = active_connections
    return True, active_connections, limit


def release_sse_connection(user_id: str, *, stream_name: str) -> int:
    """Release a previously acquired SSE connection slot."""
    with _connection_lock:
        active_connections = _active_connection_counts.get(user_id, 0)
        if active_connections <= 1:
            _active_connection_counts.pop(user_id, None)
            remaining_connections = 0
        else:
            remaining_connections = active_connections - 1
            _active_connection_counts[user_id] = remaining_connections
    logger.debug(
        "Released SSE connection for user %s on %s (%s active remaining)",
        user_id,
        stream_name,
        remaining_connections,
    )
    return remaining_connections


def get_active_sse_connection_count(user_id: str) -> int:
    """Return the current number of open SSE connections for the user."""
    with _connection_lock:
        return _active_connection_counts.get(user_id, 0)


def reset_sse_connection_limits() -> None:
    """Clear in-memory connection counts. Used by tests."""
    with _connection_lock:
        _active_connection_counts.clear()
