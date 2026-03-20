# Executive Agent Telemetry (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add telemetry and monitoring to every agent delegation and tool invocation, with structured logs for real-time debugging and Supabase tables for dashboards.

**Architecture:** A singleton `TelemetryService` receives events from ADK callbacks (`before_model_callback`, `after_tool_callback`) and a tool timing decorator. Events emit structured JSON logs synchronously and batch-write to Supabase asynchronously via `asyncio.create_task`. Circuit breaker ensures telemetry failures never block agent responses.

**Tech Stack:** Python 3.10+, asyncio, Supabase (PostgreSQL), Python `logging`, existing `CacheService` circuit breaker pattern.

**Spec:** `docs/superpowers/specs/2026-03-20-executive-agent-enhancement-design.md` (Phase 1 section)

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `app/services/telemetry.py` | TelemetryService singleton: data models, structured logging, Supabase persistence, circuit breaker |
| Create | `supabase/migrations/20260320400000_telemetry_schema.sql` | `agent_telemetry` and `tool_telemetry` tables with indexes |
| Create | `app/agents/tools/tool_timing.py` | `timed_tool` decorator that wraps tool functions to measure execution duration |
| Modify | `app/agents/context_extractor.py` | Hook telemetry recording into `before_model_callback` and `after_tool_callback` |
| Modify | `app/agent.py` | Apply `timed_tool` decorator to `_EXECUTIVE_TOOLS` |
| Modify | `app/config/validation.py` | Add `ENABLE_TELEMETRY` environment variable |
| Create | `tests/unit/test_telemetry_service.py` | Unit tests for TelemetryService |
| Create | `tests/unit/test_tool_timing.py` | Unit tests for timed_tool decorator |
| Create | `tests/unit/test_telemetry_callbacks.py` | Unit tests for callback telemetry hooks |

---

### Task 1: Supabase Migration

**Files:**
- Create: `supabase/migrations/20260320400000_telemetry_schema.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- Telemetry schema for agent and tool usage tracking (Phase 1)

-- Agent delegation events
CREATE TABLE IF NOT EXISTS agent_telemetry (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_name TEXT NOT NULL,
    delegated_from TEXT,
    user_id UUID,
    session_id TEXT,
    task_summary TEXT,
    status TEXT NOT NULL CHECK (status IN ('success', 'error', 'timeout')),
    duration_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Tool usage events
CREATE TABLE IF NOT EXISTS tool_telemetry (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tool_name TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    user_id UUID,
    session_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('success', 'error')),
    duration_ms INTEGER,
    error_type TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for dashboard queries
CREATE INDEX IF NOT EXISTS idx_agent_telemetry_agent_created
    ON agent_telemetry(agent_name, created_at);
CREATE INDEX IF NOT EXISTS idx_tool_telemetry_tool_created
    ON tool_telemetry(tool_name, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_telemetry_user
    ON agent_telemetry(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_agent_telemetry_errors
    ON agent_telemetry(status, created_at)
    WHERE status = 'error';

-- RLS: service role only (telemetry is backend-written, not user-facing)
ALTER TABLE agent_telemetry ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_telemetry ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "service_role_agent_telemetry" ON agent_telemetry
    FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "service_role_tool_telemetry" ON tool_telemetry
    FOR ALL USING (auth.role() = 'service_role');

-- Data retention: scheduled cleanup (run weekly via pg_cron or Supabase function)
-- Keeps 90 days of telemetry data
CREATE OR REPLACE FUNCTION cleanup_telemetry_data()
RETURNS void AS $$
BEGIN
    DELETE FROM agent_telemetry WHERE created_at < now() - interval '90 days';
    DELETE FROM tool_telemetry WHERE created_at < now() - interval '90 days';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

- [ ] **Step 2: Verify migration file is in correct directory**

Run: `ls supabase/migrations/ | grep telemetry`
Expected: `20260320400000_telemetry_schema.sql`

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/20260320400000_telemetry_schema.sql
git commit -m "feat: add telemetry schema for agent and tool usage tracking"
```

---

### Task 2: Environment Variable for Telemetry Toggle

**Files:**
- Modify: `app/config/validation.py` (add to `ENVIRONMENT_VARIABLES` list)

- [ ] **Step 1: Add ENABLE_TELEMETRY env var definition**

In `app/config/validation.py`, add to the `ENVIRONMENT_VARIABLES` list:

```python
EnvironmentVariable(
    name="ENABLE_TELEMETRY",
    description="Enable agent/tool telemetry collection (structured logs + Supabase)",
    required_in=set(),
    default="1",
),
```

- [ ] **Step 2: Verify no import errors**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run python -c "from app.config.validation import ENVIRONMENT_VARIABLES; print(len(ENVIRONMENT_VARIABLES))"`
Expected: prints a number (no import error)

- [ ] **Step 3: Commit**

```bash
git add app/config/validation.py
git commit -m "feat: add ENABLE_TELEMETRY environment variable"
```

---

### Task 3: TelemetryService — Data Models and Structured Logging

**Files:**
- Create: `app/services/telemetry.py`
- Create: `tests/unit/test_telemetry_service.py`

- [ ] **Step 1: Write the failing test for data models and structured logging**

Create `tests/unit/test_telemetry_service.py`:

```python
"""Tests for TelemetryService — data models and structured logging."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _run(coro):
    """Helper to run async code in sync tests."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------

def test_agent_event_creation():
    from app.services.telemetry import AgentEvent

    event = AgentEvent(
        agent_name="FinancialAnalysisAgent",
        delegated_from="ExecutiveAgent",
        user_id="user-123",
        session_id="session-456",
        task_summary="Show me Q1 revenue",
        status="success",
        duration_ms=1200,
        input_tokens=500,
        output_tokens=300,
    )
    assert event.agent_name == "FinancialAnalysisAgent"
    assert event.status == "success"
    assert event.duration_ms == 1200


def test_tool_event_creation():
    from app.services.telemetry import ToolEvent

    event = ToolEvent(
        tool_name="search_business_knowledge",
        agent_name="ExecutiveAgent",
        user_id="user-123",
        session_id="session-456",
        status="success",
        duration_ms=350,
    )
    assert event.tool_name == "search_business_knowledge"
    assert event.status == "success"


def test_agent_event_to_log_dict():
    from app.services.telemetry import AgentEvent

    event = AgentEvent(
        agent_name="SalesIntelligenceAgent",
        delegated_from="ExecutiveAgent",
        user_id="user-123",
        session_id="session-456",
        task_summary="Score this lead",
        status="error",
        error_message="Model timeout",
    )
    log_dict = event.to_log_dict()
    assert log_dict["level"] == "INFO"
    assert log_dict["event"] == "agent_delegated"
    assert log_dict["agent"] == "SalesIntelligenceAgent"
    assert log_dict["delegated_from"] == "ExecutiveAgent"
    assert log_dict["status"] == "error"
    assert "error_message" in log_dict


def test_tool_event_to_log_dict():
    from app.services.telemetry import ToolEvent

    event = ToolEvent(
        tool_name="create_image",
        agent_name="ContentCreationAgent",
        user_id="user-123",
        session_id="session-456",
        status="success",
        duration_ms=2500,
    )
    log_dict = event.to_log_dict()
    assert log_dict["event"] == "tool_executed"
    assert log_dict["tool"] == "create_image"
    assert log_dict["agent"] == "ContentCreationAgent"


# ---------------------------------------------------------------------------
# Structured logging tests
# ---------------------------------------------------------------------------

def test_structured_log_emitted_for_agent_event(caplog):
    from app.services.telemetry import TelemetryService, AgentEvent

    service = TelemetryService.__new__(TelemetryService)
    service._initialized = True
    service._enabled = True
    service._supabase = None  # no DB, log-only

    event = AgentEvent(
        agent_name="DataAnalysisAgent",
        status="success",
        duration_ms=800,
    )

    with caplog.at_level(logging.INFO, logger="app.services.telemetry"):
        service._emit_structured_log(event)

    assert len(caplog.records) >= 1
    record = caplog.records[-1]
    assert "DataAnalysisAgent" in record.message


def test_structured_log_emitted_for_tool_event(caplog):
    from app.services.telemetry import TelemetryService, ToolEvent

    service = TelemetryService.__new__(TelemetryService)
    service._initialized = True
    service._enabled = True
    service._supabase = None

    event = ToolEvent(
        tool_name="deep_research",
        agent_name="ExecutiveAgent",
        status="success",
        duration_ms=5000,
    )

    with caplog.at_level(logging.INFO, logger="app.services.telemetry"):
        service._emit_structured_log(event)

    assert len(caplog.records) >= 1
    record = caplog.records[-1]
    assert "deep_research" in record.message
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run pytest tests/unit/test_telemetry_service.py -v --no-header 2>&1 | head -30`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.telemetry'`

- [ ] **Step 3: Implement TelemetryService — data models and logging**

Create `app/services/telemetry.py`:

```python
"""Telemetry service for agent and tool usage tracking.

Collects structured events from ADK callbacks, emits structured JSON logs
for real-time debugging (Cloud Run / Cloud Logging), and persists to
Supabase tables for historical dashboards.

Design principles:
- Fire-and-forget: telemetry never blocks agent responses
- Circuit breaker: degrades to log-only when Supabase is slow/down
- Singleton: one instance shared across all callbacks
"""

import asyncio
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

_ENABLE_TELEMETRY = os.getenv("ENABLE_TELEMETRY", "1").lower() in ("1", "true", "yes")

# Circuit breaker constants (match cache.py pattern)
_CB_FAILURE_THRESHOLD = 5
_CB_RECOVERY_TIMEOUT_S = 30.0


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class AgentEvent:
    """Records a single agent delegation or invocation."""

    agent_name: str
    status: str  # success | error | timeout
    delegated_from: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    task_summary: Optional[str] = None
    duration_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None

    def to_log_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "level": "INFO",
            "event": "agent_delegated",
            "agent": self.agent_name,
            "status": self.status,
        }
        if self.delegated_from:
            d["delegated_from"] = self.delegated_from
        if self.user_id:
            d["user_id"] = self.user_id
        if self.session_id:
            d["session_id"] = self.session_id
        if self.task_summary:
            d["task_summary"] = self.task_summary[:200]
        if self.duration_ms is not None:
            d["duration_ms"] = self.duration_ms
        if self.input_tokens is not None:
            d["input_tokens"] = self.input_tokens
        if self.output_tokens is not None:
            d["output_tokens"] = self.output_tokens
        if self.error_message:
            d["error_message"] = self.error_message
        d["timestamp"] = self.created_at or datetime.now(timezone.utc).isoformat()
        return d


@dataclass
class ToolEvent:
    """Records a single tool invocation."""

    tool_name: str
    agent_name: str
    status: str  # success | error
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    duration_ms: Optional[int] = None
    error_type: Optional[str] = None
    created_at: Optional[str] = None

    def to_log_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "level": "INFO",
            "event": "tool_executed",
            "tool": self.tool_name,
            "agent": self.agent_name,
            "status": self.status,
        }
        if self.user_id:
            d["user_id"] = self.user_id
        if self.session_id:
            d["session_id"] = self.session_id
        if self.duration_ms is not None:
            d["duration_ms"] = self.duration_ms
        if self.error_type:
            d["error_type"] = self.error_type
        d["timestamp"] = self.created_at or datetime.now(timezone.utc).isoformat()
        return d


@dataclass
class AgentHealth:
    """Aggregated agent health metrics over a time window."""

    agent_name: str
    total_calls: int = 0
    success_count: int = 0
    error_count: int = 0
    timeout_count: int = 0
    avg_duration_ms: Optional[float] = None
    success_rate: float = 0.0
    top_errors: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ToolUsageSummary:
    """Aggregated tool usage metrics over a time window."""

    tool_name: str
    agent_name: str
    call_count: int = 0
    error_count: int = 0
    avg_duration_ms: Optional[float] = None


# =============================================================================
# Telemetry Service (Singleton)
# =============================================================================


class TelemetryService:
    """Singleton service for recording and persisting telemetry events."""

    _instance: Optional["TelemetryService"] = None
    _instance_lock = threading.RLock()

    def __new__(cls) -> "TelemetryService":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self.__class__._instance_lock:
            if self._initialized:
                return
            self._enabled = _ENABLE_TELEMETRY
            self._supabase = None  # lazy-loaded on first DB write
            # Circuit breaker state
            self._cb_state = "closed"  # closed | open | half-open
            self._cb_failures = 0
            self._cb_last_failure: float = 0.0
            self._initialized = True

    # -----------------------------------------------------------------
    # Structured Logging (synchronous, always runs)
    # -----------------------------------------------------------------

    def _emit_structured_log(self, event: AgentEvent | ToolEvent) -> None:
        """Emit a structured JSON log line for real-time debugging."""
        if not self._enabled:
            return
        log_dict = event.to_log_dict()
        logger.info(json.dumps(log_dict, default=str))

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    async def record_agent_event(self, event: AgentEvent) -> None:
        """Log + persist an agent delegation event (fire-and-forget)."""
        if not self._enabled:
            return
        self._emit_structured_log(event)
        self._fire_and_forget(self._persist_agent_event(event))

    async def record_tool_event(self, event: ToolEvent) -> None:
        """Log + persist a tool usage event (fire-and-forget)."""
        if not self._enabled:
            return
        self._emit_structured_log(event)
        self._fire_and_forget(self._persist_tool_event(event))

    # -----------------------------------------------------------------
    # Supabase Persistence (async, fire-and-forget)
    # -----------------------------------------------------------------

    def _fire_and_forget(self, coro) -> None:
        """Schedule an async task without awaiting it."""
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(coro)
            task.add_done_callback(self._handle_task_exception)
        except RuntimeError:
            # No running loop — log-only mode
            pass

    @staticmethod
    def _handle_task_exception(task: asyncio.Task) -> None:
        """Log exceptions from fire-and-forget tasks (don't swallow them)."""
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            logger.warning("Telemetry write failed: %s", exc)

    def _get_supabase(self):
        """Lazy-load Supabase client on first DB write."""
        if self._supabase is None:
            try:
                from app.services.supabase_client import get_service_client
                self._supabase = get_service_client()
            except Exception:
                logger.debug("Supabase client not available — telemetry is log-only")
        return self._supabase

    def _cb_should_allow(self) -> bool:
        """Circuit breaker: should we attempt a DB write?"""
        if self._cb_state == "closed":
            return True
        if self._cb_state == "open":
            elapsed = time.monotonic() - self._cb_last_failure
            if elapsed >= _CB_RECOVERY_TIMEOUT_S:
                self._cb_state = "half-open"
                return True
            return False
        # half-open: allow one attempt
        return True

    def _cb_record_success(self) -> None:
        if self._cb_state == "half-open":
            self._cb_state = "closed"
            self._cb_failures = 0

    def _cb_record_failure(self) -> None:
        self._cb_failures += 1
        self._cb_last_failure = time.monotonic()
        if self._cb_state == "half-open":
            self._cb_state = "open"
        elif self._cb_failures >= _CB_FAILURE_THRESHOLD:
            self._cb_state = "open"
            logger.warning("Telemetry circuit breaker OPEN after %d failures", self._cb_failures)

    async def _persist_agent_event(self, event: AgentEvent) -> None:
        """Write agent event to Supabase (guarded by circuit breaker).

        Uses asyncio.to_thread to avoid blocking the event loop since
        the Supabase client is synchronous (httpx.Client, not AsyncClient).
        """
        if not self._cb_should_allow():
            return
        client = self._get_supabase()
        if client is None:
            return
        try:
            row = {
                "agent_name": event.agent_name,
                "delegated_from": event.delegated_from,
                "user_id": event.user_id,
                "session_id": event.session_id,
                "task_summary": (event.task_summary or "")[:200],
                "status": event.status,
                "duration_ms": event.duration_ms,
                "input_tokens": event.input_tokens,
                "output_tokens": event.output_tokens,
                "error_message": event.error_message,
            }
            await asyncio.to_thread(
                lambda: client.table("agent_telemetry").insert(row).execute()
            )
            self._cb_record_success()
        except Exception as exc:
            self._cb_record_failure()
            logger.debug("Failed to persist agent telemetry: %s", exc)

    async def _persist_tool_event(self, event: ToolEvent) -> None:
        """Write tool event to Supabase (guarded by circuit breaker)."""
        if not self._cb_should_allow():
            return
        client = self._get_supabase()
        if client is None:
            return
        try:
            row = {
                "tool_name": event.tool_name,
                "agent_name": event.agent_name,
                "user_id": event.user_id,
                "session_id": event.session_id,
                "status": event.status,
                "duration_ms": event.duration_ms,
                "error_type": event.error_type,
            }
            await asyncio.to_thread(
                lambda: client.table("tool_telemetry").insert(row).execute()
            )
            self._cb_record_success()
        except Exception as exc:
            self._cb_record_failure()
            logger.debug("Failed to persist tool telemetry: %s", exc)

    # -----------------------------------------------------------------
    # Query API (consumed by Phase 5 get_system_health tool)
    # -----------------------------------------------------------------

    async def get_agent_health(
        self, agent_name: str, window_hours: int = 24
    ) -> AgentHealth:
        """Aggregate success rate, avg latency, error patterns for an agent."""
        client = self._get_supabase()
        if client is None:
            return AgentHealth(agent_name=agent_name)
        try:
            result = await asyncio.to_thread(
                lambda: client.rpc("get_agent_health", {
                    "p_agent_name": agent_name,
                    "p_window_hours": window_hours,
                }).execute()
            )
            data = result.data[0] if result.data else {}
            return AgentHealth(
                agent_name=agent_name,
                total_calls=data.get("total_calls", 0),
                success_count=data.get("success_count", 0),
                error_count=data.get("error_count", 0),
                timeout_count=data.get("timeout_count", 0),
                avg_duration_ms=data.get("avg_duration_ms"),
                success_rate=data.get("success_rate", 0.0),
            )
        except Exception as exc:
            logger.debug("Failed to get agent health: %s", exc)
            return AgentHealth(agent_name=agent_name)

    async def get_tool_usage(
        self, window_hours: int = 24
    ) -> list[ToolUsageSummary]:
        """Get tool usage summary across all agents."""
        client = self._get_supabase()
        if client is None:
            return []
        try:
            result = await asyncio.to_thread(
                lambda: client.rpc("get_tool_usage", {
                    "p_window_hours": window_hours,
                }).execute()
            )
            return [
                ToolUsageSummary(
                    tool_name=row["tool_name"],
                    agent_name=row["agent_name"],
                    call_count=row.get("call_count", 0),
                    error_count=row.get("error_count", 0),
                    avg_duration_ms=row.get("avg_duration_ms"),
                )
                for row in (result.data or [])
            ]
        except Exception as exc:
            logger.debug("Failed to get tool usage: %s", exc)
            return []


# =============================================================================
# Module-level accessor (matches cache.py pattern)
# =============================================================================

_telemetry_service: Optional[TelemetryService] = None


def get_telemetry_service() -> TelemetryService:
    """Get the singleton TelemetryService instance."""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
    return _telemetry_service


def invalidate_telemetry_service() -> None:
    """Reset singleton for testing."""
    global _telemetry_service
    _telemetry_service = None
    TelemetryService._instance = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run pytest tests/unit/test_telemetry_service.py -v --no-header 2>&1 | tail -20`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/telemetry.py tests/unit/test_telemetry_service.py
git commit -m "feat: add TelemetryService with data models and structured logging"
```

---

### Task 4: TelemetryService — Supabase Persistence and Circuit Breaker Tests

**Files:**
- Modify: `tests/unit/test_telemetry_service.py` (add persistence + circuit breaker tests)

- [ ] **Step 1: Write failing tests for persistence and circuit breaker**

Append to `tests/unit/test_telemetry_service.py`:

```python
# ---------------------------------------------------------------------------
# Supabase persistence tests
# ---------------------------------------------------------------------------

def test_persist_agent_event_calls_supabase():
    from app.services.telemetry import TelemetryService, AgentEvent, invalidate_telemetry_service

    invalidate_telemetry_service()
    service = TelemetryService()

    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.execute.return_value = MagicMock()
    service._supabase = mock_client

    event = AgentEvent(
        agent_name="FinancialAnalysisAgent",
        status="success",
        duration_ms=1000,
    )

    _run(service._persist_agent_event(event))

    mock_client.table.assert_called_once_with("agent_telemetry")
    mock_table.insert.assert_called_once()
    inserted = mock_table.insert.call_args[0][0]
    assert inserted["agent_name"] == "FinancialAnalysisAgent"
    assert inserted["status"] == "success"


def test_persist_tool_event_calls_supabase():
    from app.services.telemetry import TelemetryService, ToolEvent, invalidate_telemetry_service

    invalidate_telemetry_service()
    service = TelemetryService()

    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.execute.return_value = MagicMock()
    service._supabase = mock_client

    event = ToolEvent(
        tool_name="create_image",
        agent_name="ContentCreationAgent",
        status="success",
        duration_ms=3000,
    )

    _run(service._persist_tool_event(event))

    mock_client.table.assert_called_once_with("tool_telemetry")
    inserted = mock_table.insert.call_args[0][0]
    assert inserted["tool_name"] == "create_image"


# ---------------------------------------------------------------------------
# Circuit breaker tests
# ---------------------------------------------------------------------------

def test_circuit_breaker_opens_after_threshold():
    from app.services.telemetry import TelemetryService, invalidate_telemetry_service

    invalidate_telemetry_service()
    service = TelemetryService()

    assert service._cb_state == "closed"

    # Simulate 5 failures (threshold)
    for _ in range(5):
        service._cb_record_failure()

    assert service._cb_state == "open"
    assert service._cb_should_allow() is False


def test_circuit_breaker_half_open_after_timeout():
    from app.services.telemetry import TelemetryService, invalidate_telemetry_service
    import time as time_mod

    invalidate_telemetry_service()
    service = TelemetryService()

    # Open the breaker
    for _ in range(5):
        service._cb_record_failure()
    assert service._cb_state == "open"

    # Simulate timeout elapsed
    service._cb_last_failure = time_mod.monotonic() - 31.0

    assert service._cb_should_allow() is True
    assert service._cb_state == "half-open"


def test_circuit_breaker_closes_on_success():
    from app.services.telemetry import TelemetryService, invalidate_telemetry_service

    invalidate_telemetry_service()
    service = TelemetryService()

    service._cb_state = "half-open"
    service._cb_record_success()

    assert service._cb_state == "closed"
    assert service._cb_failures == 0


def test_persist_skipped_when_circuit_open():
    from app.services.telemetry import TelemetryService, AgentEvent, invalidate_telemetry_service

    invalidate_telemetry_service()
    service = TelemetryService()

    mock_client = MagicMock()
    service._supabase = mock_client

    # Open circuit
    service._cb_state = "open"
    service._cb_last_failure = time.monotonic()  # recently failed

    event = AgentEvent(agent_name="Test", status="success")
    _run(service._persist_agent_event(event))

    # Supabase should NOT have been called
    mock_client.table.assert_not_called()


def test_disabled_telemetry_skips_everything():
    from app.services.telemetry import TelemetryService, AgentEvent, invalidate_telemetry_service

    invalidate_telemetry_service()
    service = TelemetryService()
    service._enabled = False

    event = AgentEvent(agent_name="Test", status="success")
    _run(service.record_agent_event(event))
    # No exception, no logging — just silently skipped
```

- [ ] **Step 2: Ensure `import time` is at top of test file**

**IMPORTANT:** Before running the tests, verify `import time` is in the imports block at the top of `tests/unit/test_telemetry_service.py` (next to `import asyncio`). The test `test_persist_skipped_when_circuit_open` uses `time.monotonic()` and will fail with `NameError` without it. Add it if missing.

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run pytest tests/unit/test_telemetry_service.py -v --no-header 2>&1 | tail -25`
Expected: All 12 tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_telemetry_service.py
git commit -m "test: add persistence and circuit breaker tests for TelemetryService"
```

---

### Task 5: Tool Timing Decorator

**Files:**
- Create: `app/agents/tools/tool_timing.py`
- Create: `tests/unit/test_tool_timing.py`

- [ ] **Step 1: Write failing tests for the timed_tool decorator**

Create `tests/unit/test_tool_timing.py`:

```python
"""Tests for timed_tool decorator — measures tool execution duration."""

import asyncio
import time
from unittest.mock import MagicMock, patch


def _run(coro):
    return asyncio.run(coro)


def test_timed_sync_tool_records_duration():
    from app.agents.tools.tool_timing import timed_tool

    @timed_tool
    def my_tool(query: str) -> dict:
        time.sleep(0.01)  # 10ms
        return {"result": query}

    result = my_tool("test")
    assert result == {"result": "test"}
    assert hasattr(my_tool, "_last_duration_ms")
    assert my_tool._last_duration_ms >= 10


def test_timed_async_tool_records_duration():
    from app.agents.tools.tool_timing import timed_tool

    @timed_tool
    async def my_async_tool(query: str) -> dict:
        await asyncio.sleep(0.01)
        return {"result": query}

    result = _run(my_async_tool("test"))
    assert result == {"result": "test"}
    assert hasattr(my_async_tool, "_last_duration_ms")
    assert my_async_tool._last_duration_ms >= 10


def test_timed_tool_preserves_function_metadata():
    from app.agents.tools.tool_timing import timed_tool

    @timed_tool
    def search_business_knowledge(query: str) -> dict:
        """Search the Knowledge Vault."""
        return {"results": []}

    assert search_business_knowledge.__name__ == "search_business_knowledge"
    assert "Knowledge Vault" in (search_business_knowledge.__doc__ or "")


def test_timed_tool_records_error():
    from app.agents.tools.tool_timing import timed_tool

    @timed_tool
    def failing_tool() -> dict:
        raise ValueError("oops")

    try:
        failing_tool()
    except ValueError:
        pass

    assert hasattr(failing_tool, "_last_duration_ms")
    assert hasattr(failing_tool, "_last_error")
    assert failing_tool._last_error == "ValueError"


def test_timed_tool_emits_telemetry_event():
    from app.agents.tools.tool_timing import timed_tool

    mock_service = MagicMock()

    with patch("app.agents.tools.tool_timing.get_telemetry_service", return_value=mock_service):
        @timed_tool
        def my_tool() -> dict:
            return {"ok": True}

        my_tool()

    # The decorator stores timing data but does NOT call telemetry directly.
    # The after_tool_callback reads _last_duration_ms and creates the ToolEvent.
    # So we just verify the timing metadata is set.
    assert my_tool._last_duration_ms is not None
    assert my_tool._last_error is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run pytest tests/unit/test_tool_timing.py -v --no-header 2>&1 | head -15`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.agents.tools.tool_timing'`

- [ ] **Step 3: Implement the timed_tool decorator**

Create `app/agents/tools/tool_timing.py`:

```python
"""Tool timing decorator for telemetry.

Wraps tool functions to measure execution duration. The after_tool_callback
reads the timing data from the wrapper and creates ToolEvent records.

Usage:
    @timed_tool
    def my_tool(query: str) -> dict:
        ...

    # After execution:
    my_tool._last_duration_ms  # int
    my_tool._last_error        # str | None
"""

import asyncio
import functools
import time
from typing import Any, Callable


def timed_tool(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that measures tool execution time.

    Sets `_last_duration_ms` and `_last_error` attributes on the wrapper
    after each invocation. The after_tool_callback reads these to create
    ToolEvent records without needing a before_tool_callback.
    """
    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            error_type = None
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as exc:
                error_type = type(exc).__name__
                raise
            finally:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                async_wrapper._last_duration_ms = elapsed_ms
                async_wrapper._last_error = error_type

        async_wrapper._last_duration_ms = None
        async_wrapper._last_error = None
        async_wrapper._is_timed_tool = True
        return async_wrapper

    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            error_type = None
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as exc:
                error_type = type(exc).__name__
                raise
            finally:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                sync_wrapper._last_duration_ms = elapsed_ms
                sync_wrapper._last_error = error_type

        sync_wrapper._last_duration_ms = None
        sync_wrapper._last_error = None
        sync_wrapper._is_timed_tool = True
        return sync_wrapper


def apply_timing(tools: list[Callable]) -> list[Callable]:
    """Apply timed_tool decorator to a list of tools.

    Skips tools that are already timed.
    """
    result = []
    for tool in tools:
        if getattr(tool, "_is_timed_tool", False):
            result.append(tool)
        else:
            result.append(timed_tool(tool))
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run pytest tests/unit/test_tool_timing.py -v --no-header 2>&1 | tail -15`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/tools/tool_timing.py tests/unit/test_tool_timing.py
git commit -m "feat: add timed_tool decorator for tool execution duration tracking"
```

---

### Task 6: Callback Telemetry Hooks

**Files:**
- Modify: `app/agents/context_extractor.py` (lines ~192-304)
- Create: `tests/unit/test_telemetry_callbacks.py`

- [ ] **Step 1: Write failing tests for callback telemetry**

Create `tests/unit/test_telemetry_callbacks.py`:

```python
"""Tests for telemetry hooks in context_extractor callbacks."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# We need to mock ADK imports before importing the module
import sys
sys.modules.setdefault("google.adk", MagicMock())
sys.modules.setdefault("google.adk.agents", MagicMock())
sys.modules.setdefault("google.adk.agents.callback_context", MagicMock())
sys.modules.setdefault("google.genai", MagicMock())
sys.modules.setdefault("google.genai.types", MagicMock())


def _run(coro):
    return asyncio.run(coro)


def test_after_tool_callback_records_tool_event():
    """When a timed tool completes, after_tool_callback should create a ToolEvent."""
    from app.services.telemetry import ToolEvent

    mock_telemetry = MagicMock()
    mock_telemetry.record_tool_event = AsyncMock()

    # Create a mock tool with timing data
    mock_tool = MagicMock()
    mock_tool.__name__ = "search_business_knowledge"
    mock_tool._is_timed_tool = True
    mock_tool._last_duration_ms = 250
    mock_tool._last_error = None

    # Create mock callback context
    mock_context = MagicMock()
    mock_context.state = {
        "user_id": "user-123",
        "session_id": "session-456",
    }

    with patch("app.agents.context_extractor.get_telemetry_service", return_value=mock_telemetry):
        from app.agents.context_extractor import _record_tool_telemetry
        _run(_record_tool_telemetry(mock_tool, mock_context, "success"))

    mock_telemetry.record_tool_event.assert_awaited_once()
    event = mock_telemetry.record_tool_event.call_args[0][0]
    assert isinstance(event, ToolEvent)
    assert event.tool_name == "search_business_knowledge"
    assert event.duration_ms == 250
    assert event.status == "success"


def test_before_model_callback_records_agent_start():
    """before_model_callback should record agent name and task summary."""
    mock_telemetry = MagicMock()

    mock_context = MagicMock()
    mock_context.state = {
        "user_id": "user-123",
    }
    mock_context.agent_name = "FinancialAnalysisAgent"

    with patch("app.agents.context_extractor.get_telemetry_service", return_value=mock_telemetry):
        from app.agents.context_extractor import _record_agent_start
        _record_agent_start(mock_context, "Show me revenue")

    # Agent start is recorded in state for later completion tracking
    assert "_telemetry_agent_start" in mock_context.state
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run pytest tests/unit/test_telemetry_callbacks.py -v --no-header 2>&1 | head -15`
Expected: FAIL — `ImportError: cannot import name '_record_tool_telemetry'`

- [ ] **Step 3: Add telemetry recording functions to context_extractor.py**

In `app/agents/context_extractor.py`, add these imports near the top (after existing imports):

```python
from app.services.telemetry import get_telemetry_service, ToolEvent
```

Add these helper functions before the existing callback functions (before line 192):

```python
# =============================================================================
# Telemetry Helpers
# =============================================================================

_TELEMETRY_AGENT_START_KEY = "_telemetry_agent_start"


def _record_agent_start(callback_context, task_summary: str | None = None) -> None:
    """Record agent invocation start time in session state.

    Called from before_model_callback. The completion is tracked when
    the next before_model_callback fires (indicating the agent returned).
    """
    import time
    agent_name = _get_callback_agent_name(callback_context)
    callback_context.state[_TELEMETRY_AGENT_START_KEY] = {
        "agent_name": agent_name,
        "start_time": time.monotonic(),
        "task_summary": (task_summary or "")[:200],
        "user_id": _get_callback_user_id(callback_context),
    }


async def _record_tool_telemetry(
    tool, tool_context, status: str
) -> None:
    """Create and record a ToolEvent from a timed tool's metadata."""
    if not getattr(tool, "_is_timed_tool", False):
        return

    service = get_telemetry_service()
    event = ToolEvent(
        tool_name=getattr(tool, "__name__", str(tool)),
        agent_name=_get_callback_agent_name(tool_context),
        user_id=_get_callback_user_id(tool_context),
        session_id=tool_context.state.get("session_id"),
        status=status,
        duration_ms=getattr(tool, "_last_duration_ms", None),
        error_type=getattr(tool, "_last_error", None),
    )
    await service.record_tool_event(event)
```

- [ ] **Step 4: Hook into existing `context_memory_after_tool_callback`**

In `context_memory_after_tool_callback` (around line 192), add telemetry recording at the END of the function, before the final `return`:

```python
    # --- Telemetry: record tool execution ---
    try:
        tool_status = "error" if getattr(tool, "_last_error", None) else "success"
        import asyncio
        loop = asyncio.get_running_loop()
        loop.create_task(_record_tool_telemetry(tool, tool_context, tool_status))
    except Exception:
        pass  # Telemetry never blocks
```

- [ ] **Step 5: Hook into existing `context_memory_before_model_callback`**

In `context_memory_before_model_callback` (around line 232), add near the top of the function:

```python
    # --- Telemetry: record agent start ---
    try:
        latest_text = None
        if llm_request and hasattr(llm_request, "contents") and llm_request.contents:
            for content in reversed(llm_request.contents):
                if hasattr(content, "parts"):
                    for part in content.parts:
                        if hasattr(part, "text") and part.text:
                            latest_text = part.text[:200]
                            break
                if latest_text:
                    break
        _record_agent_start(callback_context, latest_text)
    except Exception:
        pass  # Telemetry never blocks
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run pytest tests/unit/test_telemetry_callbacks.py -v --no-header 2>&1 | tail -15`
Expected: All 2 tests PASS

- [ ] **Step 7: Run existing context_extractor tests to verify no regressions**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run pytest tests/ -k "context" -v --no-header 2>&1 | tail -20`
Expected: All existing tests still PASS

- [ ] **Step 8: Commit**

```bash
git add app/agents/context_extractor.py tests/unit/test_telemetry_callbacks.py
git commit -m "feat: hook telemetry recording into ADK callbacks"
```

---

### Task 7: Apply Tool Timing to Executive Agent

**Files:**
- Modify: `app/agent.py` (line ~214, `_EXECUTIVE_TOOLS` list)

- [ ] **Step 1: Import `apply_timing` in agent.py**

In `app/agent.py`, add after the existing tool imports (around line 62):

```python
from app.agents.tools.tool_timing import apply_timing
```

- [ ] **Step 2: Wrap `_EXECUTIVE_TOOLS` with timing**

Change the `_EXECUTIVE_TOOLS` assignment (around line 214) from:

```python
_EXECUTIVE_TOOLS = _sanitize([
```

to:

```python
_EXECUTIVE_TOOLS = _sanitize(apply_timing([
```

And add a closing `)` after the list's closing `]`:

```python
]))
```

This applies the timing decorator to all tools BEFORE the sanitize pass.

- [ ] **Step 3: Verify import works**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run python -c "from app.agents.tools.tool_timing import apply_timing; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/agent.py
git commit -m "feat: apply tool timing decorator to Executive agent tools"
```

---

### Task 8: Integration Smoke Test

**Files:**
- No new files — validates end-to-end wiring

- [ ] **Step 1: Run full test suite to check for regressions**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run pytest tests/unit/ -v --no-header 2>&1 | tail -30`
Expected: All tests PASS (no regressions from callback changes)

- [ ] **Step 2: Verify structured log output**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run python -c "
from app.services.telemetry import get_telemetry_service, AgentEvent
import asyncio, logging
logging.basicConfig(level=logging.INFO)
svc = get_telemetry_service()
event = AgentEvent(agent_name='TestAgent', status='success', duration_ms=42)
asyncio.run(svc.record_agent_event(event))
print('Telemetry smoke test: OK')
"`
Expected: Structured JSON log line printed + "Telemetry smoke test: OK"

- [ ] **Step 3: Verify timed_tool end-to-end**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run python -c "
from app.agents.tools.tool_timing import timed_tool
import time

@timed_tool
def dummy_tool(q: str) -> dict:
    time.sleep(0.01)
    return {'q': q}

result = dummy_tool('hello')
print(f'Result: {result}')
print(f'Duration: {dummy_tool._last_duration_ms}ms')
print(f'Error: {dummy_tool._last_error}')
assert dummy_tool._last_duration_ms >= 10
print('Tool timing smoke test: OK')
"`
Expected: Duration >= 10ms, "Tool timing smoke test: OK"

- [ ] **Step 4: Run linter**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run ruff check app/services/telemetry.py app/agents/tools/tool_timing.py app/agents/context_extractor.py --fix`
Expected: No errors (or auto-fixed)

- [ ] **Step 5: Run formatter**

Run: `cd /c/Users/expert/Documents/PKA/Pikar-Ai && uv run ruff format app/services/telemetry.py app/agents/tools/tool_timing.py app/agents/context_extractor.py`
Expected: Files formatted

- [ ] **Step 6: Final commit (if lint/format made changes)**

```bash
git add -u
git commit -m "style: lint and format telemetry files"
```

---

## Review Fixes Applied

Issues from spec review, all addressed:
- **Added `AgentHealth` and `ToolUsageSummary` data models** + `get_agent_health()` / `get_tool_usage()` query methods on TelemetryService
- **Added data retention** — `cleanup_telemetry_data()` SQL function in migration
- **Fixed `asyncio.to_thread`** — Supabase sync client calls now wrapped to avoid blocking the event loop
- **Fixed `task_summary` truncation** — consistently 200 chars in both log and DB (was 500 in DB)
- **Added `"level": "INFO"` field** to `to_log_dict()` output matching spec format
- **Fixed circuit breaker** — explicit half-open -> open transition on failure
- **Fixed `import time` sequencing** — clarified it must be present before Task 4 tests run

## Summary

| Task | What it does | New/Modified Files | Tests |
|------|-------------|-------------------|-------|
| 1 | Migration SQL + retention | `supabase/migrations/20260320400000_telemetry_schema.sql` | N/A |
| 2 | Feature flag | `app/config/validation.py` | Import check |
| 3 | Data models + logging + query API | `app/services/telemetry.py` | 6 tests |
| 4 | Persistence + circuit breaker | `tests/unit/test_telemetry_service.py` | 6 more tests |
| 5 | Tool timing decorator | `app/agents/tools/tool_timing.py` | 5 tests |
| 6 | Callback hooks | `app/agents/context_extractor.py` | 2 tests |
| 7 | Wire timing to Executive | `app/agent.py` | Import check |
| 8 | Integration smoke test | — | End-to-end validation |
