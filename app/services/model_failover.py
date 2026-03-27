# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Model failover service with circuit breaker pattern.

Automatically switches from primary model to fallback when the primary
experiences consecutive failures (5xx, quota exhausted, unavailable).
Auto-recovers back to primary after a cooldown period.

States:
- CLOSED: Using primary model (normal operation)
- OPEN: Using fallback model (primary failed too many times)
- HALF_OPEN: Testing primary model (cooldown expired, try one request)
"""

import logging
import os
import threading
import time

from google.adk.models import Gemini
from google.genai import types

logger = logging.getLogger(__name__)

# Configuration via env vars with sensible defaults
FAILOVER_FAILURE_THRESHOLD = int(os.getenv("MODEL_CB_FAILURE_THRESHOLD", "3"))
FAILOVER_RECOVERY_TIMEOUT = int(os.getenv("MODEL_CB_RECOVERY_TIMEOUT", "120"))  # seconds


class ModelFailover:
    """Circuit breaker for LLM model selection.

    Tracks consecutive model failures and automatically switches from the
    primary model to the fallback model once the failure threshold is reached.
    Recovers back to the primary model after a configurable cooldown period
    using the standard closed/open/half-open circuit breaker state machine.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern — one circuit breaker per process."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialise internal state (runs only once due to singleton)."""
        if self._initialized:
            return
        self._consecutive_failures = 0
        self._state = "closed"  # closed | open | half_open
        self._last_failure_time = 0.0
        self._primary_model = os.getenv("GEMINI_AGENT_MODEL_PRIMARY", "gemini-2.5-pro")
        self._fallback_model = os.getenv("GEMINI_AGENT_MODEL_FALLBACK", "gemini-2.5-flash")
        self._state_lock = threading.Lock()
        self._initialized = True

    @property
    def state(self) -> str:
        """Return the current circuit breaker state."""
        return self._state

    @property
    def active_model_name(self) -> str:
        """Return which model name is currently active."""
        if self._state == "closed":
            return self._primary_model
        if self._state == "open":
            if time.time() - self._last_failure_time > FAILOVER_RECOVERY_TIMEOUT:
                return self._primary_model  # will transition to half_open on next get_active_model
            return self._fallback_model
        # half_open — try primary
        return self._primary_model

    def get_active_model(self, retry_options: types.HttpRetryOptions | None = None) -> Gemini:
        """Get the currently active Gemini model based on circuit state.

        Args:
            retry_options: Optional HTTP retry configuration to attach to the model.

        Returns:
            A configured Gemini instance pointing to either the primary or fallback model.
        """
        with self._state_lock:
            if self._state == "open":
                elapsed = time.time() - self._last_failure_time
                if elapsed > FAILOVER_RECOVERY_TIMEOUT:
                    self._state = "half_open"
                    logger.info(
                        "Model failover: open -> half_open (testing primary after %.0fs)",
                        elapsed,
                    )

            model_name = self.active_model_name
            kwargs: dict = {"model": model_name}
            if retry_options:
                kwargs["retry_options"] = retry_options
            return Gemini(**kwargs)

    def record_success(self) -> None:
        """Record a successful model call, resetting the failure counter.

        Transitions half_open -> closed when the primary recovers successfully.
        """
        with self._state_lock:
            if self._state == "half_open":
                logger.info("Model failover: half_open -> closed (primary recovered)")
                self._state = "closed"
            self._consecutive_failures = 0

    def record_failure(self) -> None:
        """Record a model failure, potentially triggering failover.

        Transitions closed -> open after N consecutive failures, or
        half_open -> open when the primary is still failing.
        """
        with self._state_lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.time()

            if self._state == "half_open":
                self._state = "open"
                logger.warning("Model failover: half_open -> open (primary still failing)")
            elif self._state == "closed" and self._consecutive_failures >= FAILOVER_FAILURE_THRESHOLD:
                self._state = "open"
                logger.warning(
                    "Model failover: closed -> open (primary failed %d consecutive times,"
                    " switching to %s)",
                    self._consecutive_failures,
                    self._fallback_model,
                )

    def reset(self) -> None:
        """Reset to initial closed state (intended for testing only)."""
        with self._state_lock:
            self._consecutive_failures = 0
            self._state = "closed"
            self._last_failure_time = 0.0

    def get_status(self) -> dict:
        """Return current failover status suitable for health endpoints.

        Returns:
            A dict with state, active_model, failure counts, and configuration.
        """
        return {
            "state": self._state,
            "active_model": self.active_model_name,
            "consecutive_failures": self._consecutive_failures,
            "primary_model": self._primary_model,
            "fallback_model": self._fallback_model,
            "failure_threshold": FAILOVER_FAILURE_THRESHOLD,
            "recovery_timeout_seconds": FAILOVER_RECOVERY_TIMEOUT,
        }


# Module-level singleton
model_failover = ModelFailover()
