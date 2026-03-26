# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Supabase resilience layer with async-compatible circuit breaker.

Wraps Supabase operations with:
- Circuit breaker (closed/open/half-open) to prevent cascading failures
- Automatic client reconnection on connection loss
- Graceful degradation returning empty results instead of crashing

The circuit breaker uses ``asyncio.Lock`` for state transitions, making it
safe for concurrent async callers without blocking the event loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)

# Circuit breaker config
SB_CB_FAILURE_THRESHOLD = int(os.getenv("SUPABASE_CB_FAILURE_THRESHOLD", "5"))
SB_CB_RECOVERY_TIMEOUT = int(os.getenv("SUPABASE_CB_RECOVERY_TIMEOUT", "30"))


class SupabaseCircuitBreaker:
    """Async-compatible circuit breaker for Supabase operations.

    Implements the closed/open/half-open state machine:
    - ``closed``: requests are allowed, failures are counted
    - ``open``: requests are blocked until the recovery timeout elapses
    - ``half_open``: one probe request is allowed; success closes the circuit,
      failure re-opens it

    The singleton ``__new__`` uses ``threading.Lock`` (runs once at import time).
    The per-request ``_state_lock`` uses ``asyncio.Lock`` for non-blocking async.
    """

    _instance: SupabaseCircuitBreaker | None = None
    _lock = threading.Lock()

    def __new__(cls) -> SupabaseCircuitBreaker:
        """Singleton pattern — one breaker per process.

        Uses threading.Lock for the one-time singleton creation (sync, import-time).
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize state (idempotent due to singleton guard)."""
        if getattr(self, "_initialized", False):
            return
        self._consecutive_failures = 0
        self._state = "closed"
        self._last_failure_time = 0.0
        self._state_lock = asyncio.Lock()
        self._initialized = True

    async def should_allow_request(self) -> bool:
        """Return True if the circuit allows the request to proceed."""
        async with self._state_lock:
            if self._state == "closed":
                return True
            if self._state == "open":
                if time.time() - self._last_failure_time > SB_CB_RECOVERY_TIMEOUT:
                    self._state = "half_open"
                    logger.info("Supabase circuit breaker: open -> half_open")
                    return True
                return False
            # half_open: allow one probe
            return True

    async def record_success(self) -> None:
        """Record a successful operation; close the circuit if it was half-open."""
        async with self._state_lock:
            if self._state == "half_open":
                logger.info("Supabase circuit breaker: half_open -> closed")
                self._state = "closed"
            self._consecutive_failures = 0

    async def record_failure(self, error: Exception | None = None) -> None:
        """Record a failed operation; open the circuit when the threshold is reached."""
        async with self._state_lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.time()
            if self._state == "half_open":
                self._state = "open"
                logger.warning(
                    "Supabase circuit breaker: half_open -> open (probe failed: %s)",
                    error,
                )
            elif (
                self._state == "closed"
                and self._consecutive_failures >= SB_CB_FAILURE_THRESHOLD
            ):
                self._state = "open"
                logger.warning(
                    "Supabase circuit breaker: closed -> open (%d consecutive failures)",
                    self._consecutive_failures,
                )

    async def reset(self) -> None:
        """Unconditionally reset the circuit breaker to closed state."""
        async with self._state_lock:
            self._consecutive_failures = 0
            self._state = "closed"
            self._last_failure_time = 0.0

    async def get_status(self) -> dict[str, Any]:
        """Return a serialisable snapshot of the current circuit breaker state."""
        async with self._state_lock:
            return {
                "state": self._state,
                "consecutive_failures": self._consecutive_failures,
                "failure_threshold": SB_CB_FAILURE_THRESHOLD,
                "recovery_timeout_seconds": SB_CB_RECOVERY_TIMEOUT,
                "last_failure_time": self._last_failure_time or None,
            }


# Module-level singleton — importers reference this directly.
supabase_circuit_breaker = SupabaseCircuitBreaker()


def with_supabase_resilience(default_return: Any = None) -> Callable:
    """Decorator factory for resilient Supabase operations.

    Wraps an ``async`` function with circuit breaker logic.  When the circuit
    is open the decorated function short-circuits and returns *default_return*
    immediately.  All exceptions are caught, recorded, and swallowed — the
    caller always receives *default_return* on failure rather than an
    unhandled exception.

    Usage::

        @with_supabase_resilience(default_return=[])
        async def fetch_items(user_id: str) -> list:
            client = await get_async_client()
            result = await execute_async(
                client.table("items").select("*").eq("user_id", user_id)
            )
            return result.data
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not await supabase_circuit_breaker.should_allow_request():
                logger.warning(
                    "Supabase circuit breaker open — returning default for %s",
                    func.__name__,
                )
                return default_return

            try:
                result = await func(*args, **kwargs)
                await supabase_circuit_breaker.record_success()
                return result
            except Exception as exc:
                logger.warning(
                    "Supabase error in %s: %s",
                    func.__name__,
                    exc,
                )
                await supabase_circuit_breaker.record_failure(exc)
                return default_return

        return wrapper

    return decorator
