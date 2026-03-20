"""Telemetry service for Pikar AI agent delegation and tool invocation tracking.

This module provides a singleton TelemetryService that:
- Defines structured data models for agent and tool events
- Emits structured JSON logs for every event
- Persists events to Supabase asynchronously via fire-and-forget
- Applies a circuit breaker to protect against Supabase unavailability
- Exposes query helpers for agent health and tool usage summaries
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class AgentEvent:
    """Record of a single agent delegation invocation."""

    agent_name: str
    status: str  # "success" | "error" | "timeout"
    delegated_from: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    task_summary: Optional[str] = None
    duration_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_log_dict(self) -> dict[str, Any]:
        """Return a structured dict suitable for JSON logging."""
        d: dict[str, Any] = {
            "level": "INFO",
            "event": "agent_delegated",
            "agent": self.agent_name,
            "status": self.status,
            "delegated_from": self.delegated_from,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "task_summary": self.task_summary,
            "duration_ms": self.duration_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "created_at": self.created_at.isoformat(),
        }
        if self.error_message is not None:
            d["error_message"] = self.error_message
        return d


@dataclass
class ToolEvent:
    """Record of a single tool invocation."""

    tool_name: str
    agent_name: str
    status: str  # "success" | "error" | "timeout"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    duration_ms: Optional[int] = None
    error_type: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_log_dict(self) -> dict[str, Any]:
        """Return a structured dict suitable for JSON logging."""
        d: dict[str, Any] = {
            "level": "INFO",
            "event": "tool_executed",
            "tool": self.tool_name,
            "agent": self.agent_name,
            "status": self.status,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat(),
        }
        if self.error_type is not None:
            d["error_type"] = self.error_type
        return d


@dataclass
class AgentHealth:
    """Aggregated health statistics for a single agent over a time window."""

    agent_name: str
    total_calls: int
    success_count: int
    error_count: int
    timeout_count: int
    avg_duration_ms: float
    success_rate: float
    top_errors: list[str] = field(default_factory=list)


@dataclass
class ToolUsageSummary:
    """Aggregated usage statistics for a single tool over a time window."""

    tool_name: str
    agent_name: str
    call_count: int
    error_count: int
    avg_duration_ms: float


# ---------------------------------------------------------------------------
# TelemetryService singleton
# ---------------------------------------------------------------------------


class TelemetryService:
    """Singleton service for recording and querying agent/tool telemetry.

    Follows the same singleton pattern as CacheService:
    - threading.RLock guards instance creation
    - Double-checked locking in __init__ prevents re-initialisation
    - Module-level get_telemetry_service() is the recommended accessor

    Circuit breaker protects Supabase persistence:
    - closed  -> open  after 5 consecutive failures
    - open    -> half-open after 30 s recovery timeout
    - half-open -> closed on success, back to open on failure
    """

    _instance: Optional["TelemetryService"] = None
    _instance_lock = threading.RLock()

    # Circuit-breaker defaults
    _CB_FAILURE_THRESHOLD: int = 5
    _CB_RECOVERY_TIMEOUT: float = 30.0

    def __new__(cls) -> "TelemetryService":
        """Return (or create) the singleton instance."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialise state (runs only once due to double-checked guard)."""
        if self._initialized:
            return

        with self.__class__._instance_lock:
            if self._initialized:
                return

            self._enabled: bool = os.getenv("ENABLE_TELEMETRY", "1") not in ("0", "false", "False")
            self._supabase: Any = None  # lazy-loaded

            # Circuit breaker state
            self._cb_state: str = "closed"  # "closed" | "open" | "half-open"
            self._cb_failures: int = 0
            self._cb_last_failure_time: Optional[float] = None

            self._initialized = True

    # ------------------------------------------------------------------
    # Structured logging
    # ------------------------------------------------------------------

    def _emit_structured_log(self, event: AgentEvent | ToolEvent) -> None:
        """Emit a single structured JSON log line for the event."""
        log_dict = event.to_log_dict()
        logger.info(json.dumps(log_dict, default=str))

    # ------------------------------------------------------------------
    # Public recording API
    # ------------------------------------------------------------------

    async def record_agent_event(self, event: AgentEvent) -> None:
        """Record an agent delegation event: log it and persist asynchronously."""
        if not self._enabled:
            return
        self._emit_structured_log(event)
        self._fire_and_forget(self._persist_agent_event(event))

    async def record_tool_event(self, event: ToolEvent) -> None:
        """Record a tool invocation event: log it and persist asynchronously."""
        if not self._enabled:
            return
        self._emit_structured_log(event)
        self._fire_and_forget(self._persist_tool_event(event))

    # ------------------------------------------------------------------
    # Fire-and-forget helper
    # ------------------------------------------------------------------

    def _fire_and_forget(self, coro: Any) -> None:
        """Schedule a coroutine as a background task without awaiting it."""
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(coro)

            def _on_done(t: asyncio.Task) -> None:
                exc = t.exception()
                if exc is not None:
                    logger.warning("Telemetry background task failed: %s", exc)

            task.add_done_callback(_on_done)
        except RuntimeError:
            # No running event loop — skip persistence silently
            logger.debug("No running event loop; skipping telemetry persistence")

    # ------------------------------------------------------------------
    # Supabase lazy loader
    # ------------------------------------------------------------------

    def _get_supabase(self) -> Any:
        """Lazily load and return the Supabase service client."""
        if self._supabase is None:
            from app.services.supabase_client import get_service_client  # noqa: PLC0415

            self._supabase = get_service_client()
        return self._supabase

    # ------------------------------------------------------------------
    # Circuit breaker
    # ------------------------------------------------------------------

    def _cb_should_allow(self) -> bool:
        """Return True if the circuit breaker permits a Supabase call."""
        if self._cb_state == "closed":
            return True

        if self._cb_state == "open":
            if self._cb_last_failure_time is not None:
                elapsed = time.time() - self._cb_last_failure_time
                if elapsed >= self._CB_RECOVERY_TIMEOUT:
                    logger.info("Telemetry circuit breaker: recovery timeout elapsed, moving to half-open")
                    self._cb_state = "half-open"
                    return True
            return False

        # half-open: allow a single probe
        return True

    def _cb_record_success(self) -> None:
        """Reset the circuit breaker on a successful Supabase call."""
        if self._cb_state == "half-open":
            logger.info("Telemetry circuit breaker: probe succeeded, closing circuit")
        self._cb_state = "closed"
        self._cb_failures = 0

    def _cb_record_failure(self) -> None:
        """Increment failure count and open the circuit when threshold is reached."""
        self._cb_failures += 1
        self._cb_last_failure_time = time.time()

        if self._cb_state == "closed":
            if self._cb_failures >= self._CB_FAILURE_THRESHOLD:
                logger.warning(
                    "Telemetry circuit breaker: failure threshold (%d) reached, opening circuit",
                    self._CB_FAILURE_THRESHOLD,
                )
                self._cb_state = "open"
        elif self._cb_state == "half-open":
            # Probe failed — immediately reopen
            logger.warning("Telemetry circuit breaker: half-open probe failed, reopening circuit")
            self._cb_state = "open"

    # ------------------------------------------------------------------
    # Supabase persistence helpers
    # ------------------------------------------------------------------

    async def _persist_agent_event(self, event: AgentEvent) -> None:
        """Persist an AgentEvent row to Supabase (async, circuit-breaker guarded)."""
        if not self._cb_should_allow():
            return

        task_summary = event.task_summary
        if task_summary and len(task_summary) > 200:
            task_summary = task_summary[:200]

        row = {
            "agent_name": event.agent_name,
            "delegated_from": event.delegated_from,
            "user_id": event.user_id,
            "session_id": event.session_id,
            "task_summary": task_summary,
            "status": event.status,
            "duration_ms": event.duration_ms,
            "input_tokens": event.input_tokens,
            "output_tokens": event.output_tokens,
            "error_message": event.error_message,
            "created_at": event.created_at.isoformat(),
        }

        try:
            client = self._get_supabase()
            await asyncio.to_thread(lambda: client.table("agent_events").insert(row).execute())
            self._cb_record_success()
        except Exception as exc:
            logger.warning("Failed to persist agent event to Supabase: %s", exc)
            self._cb_record_failure()

    async def _persist_tool_event(self, event: ToolEvent) -> None:
        """Persist a ToolEvent row to Supabase (async, circuit-breaker guarded)."""
        if not self._cb_should_allow():
            return

        row = {
            "tool_name": event.tool_name,
            "agent_name": event.agent_name,
            "user_id": event.user_id,
            "session_id": event.session_id,
            "status": event.status,
            "duration_ms": event.duration_ms,
            "error_type": event.error_type,
            "created_at": event.created_at.isoformat(),
        }

        try:
            client = self._get_supabase()
            await asyncio.to_thread(lambda: client.table("tool_events").insert(row).execute())
            self._cb_record_success()
        except Exception as exc:
            logger.warning("Failed to persist tool event to Supabase: %s", exc)
            self._cb_record_failure()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def get_agent_health(
        self,
        agent_name: str,
        window_hours: int = 24,
    ) -> AgentHealth:
        """Return aggregated health stats for agent_name over the past window_hours.

        Degrades gracefully: returns a zero-count AgentHealth on any error.
        """
        default = AgentHealth(
            agent_name=agent_name,
            total_calls=0,
            success_count=0,
            error_count=0,
            timeout_count=0,
            avg_duration_ms=0.0,
            success_rate=0.0,
        )

        if not self._cb_should_allow():
            return default

        try:
            client = self._get_supabase()
            result = await asyncio.to_thread(
                lambda: client.rpc(
                    "get_agent_health",
                    {"p_agent_name": agent_name, "p_window_hours": window_hours},
                ).execute()
            )
            self._cb_record_success()
            data = result.data
            if not data:
                return default
            row = data[0] if isinstance(data, list) else data
            return AgentHealth(
                agent_name=agent_name,
                total_calls=row.get("total_calls", 0),
                success_count=row.get("success_count", 0),
                error_count=row.get("error_count", 0),
                timeout_count=row.get("timeout_count", 0),
                avg_duration_ms=float(row.get("avg_duration_ms", 0.0)),
                success_rate=float(row.get("success_rate", 0.0)),
                top_errors=row.get("top_errors") or [],
            )
        except Exception as exc:
            logger.warning("Failed to fetch agent health from Supabase: %s", exc)
            self._cb_record_failure()
            return default

    async def get_tool_usage(self, window_hours: int = 24) -> list[ToolUsageSummary]:
        """Return per-tool usage summaries over the past window_hours.

        Degrades gracefully: returns an empty list on any error.
        """
        if not self._cb_should_allow():
            return []

        try:
            client = self._get_supabase()
            result = await asyncio.to_thread(
                lambda: client.rpc(
                    "get_tool_usage",
                    {"p_window_hours": window_hours},
                ).execute()
            )
            self._cb_record_success()
            rows = result.data or []
            return [
                ToolUsageSummary(
                    tool_name=r.get("tool_name", ""),
                    agent_name=r.get("agent_name", ""),
                    call_count=r.get("call_count", 0),
                    error_count=r.get("error_count", 0),
                    avg_duration_ms=float(r.get("avg_duration_ms", 0.0)),
                )
                for r in rows
            ]
        except Exception as exc:
            logger.warning("Failed to fetch tool usage from Supabase: %s", exc)
            self._cb_record_failure()
            return []


# ---------------------------------------------------------------------------
# Module-level accessors
# ---------------------------------------------------------------------------


def get_telemetry_service() -> TelemetryService:
    """Return the singleton TelemetryService instance.

    This is the recommended way to obtain the service throughout the application.
    """
    return TelemetryService()


def invalidate_telemetry_service() -> None:
    """Destroy the singleton instance — intended for use in tests only."""
    with TelemetryService._instance_lock:
        TelemetryService._instance = None
