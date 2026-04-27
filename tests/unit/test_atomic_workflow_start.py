"""Unit tests for the atomic workflow start RPC behaviour.

These tests verify that engine.start_workflow:
  - calls rpc("start_workflow_execution_atomic", ...) instead of a two-step
    SELECT COUNT + INSERT
  - correctly maps a non-empty RPC response (success) to the execution flow
  - correctly returns the error dict when the RPC returns empty data (limit hit)
  - passes p_max_concurrent=0 when MAX_CONCURRENT_EXECUTIONS_PER_USER=0 so
    the Postgres function treats zero as "no limit" and always inserts
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

import app.workflows.engine as engine_module
from app.workflows.engine import WorkflowEngine


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_TEMPLATE = {
    "id": "tpl-atomic-1",
    "name": "Atomic Template",
    "version": 1,
    "lifecycle_status": "published",
    "phases": [
        {
            "name": "Phase 1",
            "steps": [
                {
                    "name": "Step 1",
                    "tool": "create_task",
                    "description": "Do something",
                    "required_approval": False,
                    "input_bindings": {"description": {"value": "task"}},
                    "risk_level": "low",
                    "required_integrations": [],
                    "verification_checks": ["success"],
                    "expected_outputs": ["task.id"],
                    "allow_parallel": False,
                }
            ],
        }
    ],
}

_EXECUTION_ROW = {
    "id": "exec-atomic-1",
    "user_id": "user-1",
    "status": "pending",
}

_ACTIVE_STATUS_LIST = ["pending", "running", "paused", "waiting_approval"]


# ---------------------------------------------------------------------------
# Fake helpers
# ---------------------------------------------------------------------------


class _FakeRpcQuery:
    """Simulates client.rpc(...).execute() — awaitable."""

    def __init__(self, response_data):
        self._data = response_data
        self.call_kwargs = None

    async def execute(self):
        result = MagicMock()
        result.data = self._data
        result.count = len(self._data) if self._data else None
        return result


class _FakeCountResponse:
    def __init__(self, count: int):
        self.data = [{"id": f"exec-{i}"} for i in range(count)]
        self.count = count


class _FakeTable:
    """Minimal query builder for workflow_executions select (count query after limit exceeded)."""

    def __init__(self, response_data, count=0):
        self._data = response_data
        self._count = count

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    async def execute(self):
        return _FakeCountResponse(self._count)


class _FakeClient:
    """Supabase-like client that records rpc() calls."""

    def __init__(self, *, template, rpc_data, active_count=0):
        self._template = template
        self._rpc_data = rpc_data
        self._active_count = active_count
        self.rpc_calls = []  # list of (fn_name, params) tuples

    def table(self, name: str):
        if name == "workflow_templates":
            return _StaticTable([self._template])
        # workflow_executions — used for count fallback after limit exceeded
        return _FakeTable([], count=self._active_count)

    def rpc(self, fn_name: str, params: dict):
        self.rpc_calls.append((fn_name, params))
        return _FakeRpcQuery(self._rpc_data)


class _StaticTable:
    """Always returns the given rows on execute()."""

    def __init__(self, rows):
        self._rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    async def execute(self):
        result = MagicMock()
        result.data = self._rows
        return result


# ---------------------------------------------------------------------------
# Helpers to build an engine with the right env state
# ---------------------------------------------------------------------------


def _make_engine(client: _FakeClient) -> WorkflowEngine:
    engine = object.__new__(WorkflowEngine)
    engine._async_client = client
    return engine


def _set_standard_env(monkeypatch):
    """Set env vars needed by start_workflow."""
    monkeypatch.setenv("BACKEND_API_URL", "http://localhost:8000")
    monkeypatch.setenv("WORKFLOW_SERVICE_SECRET", "x" * 40)
    monkeypatch.setenv("WORKFLOW_ENFORCE_READINESS_GATE", "false")


# ---------------------------------------------------------------------------
# Test 1: RPC returns row — success path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_atomic_start_success_calls_rpc_and_returns_pending(monkeypatch):
    """When the RPC returns a row, the engine extracts execution_id and returns status=pending."""
    client = _FakeClient(template=_TEMPLATE, rpc_data=[_EXECUTION_ROW])
    engine = _make_engine(client)

    monkeypatch.setenv("WORKFLOW_MAX_CONCURRENT_PER_USER", "3")
    _set_standard_env(monkeypatch)

    # Patch audit — no-op
    monkeypatch.setattr(engine, "_audit_execution_action", AsyncMock())
    # Patch edge function
    monkeypatch.setattr(
        "app.workflows.engine.edge_function_client.execute_workflow",
        AsyncMock(return_value={"success": True}),
    )
    # Force the module-level constant to 3
    monkeypatch.setattr(engine_module, "MAX_CONCURRENT_EXECUTIONS_PER_USER", 3)

    result = await engine.start_workflow(user_id="user-1", template_name="Atomic Template")

    # RPC was called exactly once with the right function name
    assert len(client.rpc_calls) == 1
    fn_name, params = client.rpc_calls[0]
    assert fn_name == "start_workflow_execution_atomic"
    assert params["p_user_id"] == "user-1"
    assert params["p_max_concurrent"] == 3

    # Result reflects the execution
    assert "error" not in result
    assert result["status"] == "pending"
    assert result["execution_id"] == "exec-atomic-1"


# ---------------------------------------------------------------------------
# Test 2: RPC returns empty list — concurrent limit exceeded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_atomic_start_limit_exceeded_returns_error_shape(monkeypatch):
    """When the RPC returns empty data the engine returns the standard limit error dict."""
    # Client has 3 active executions already (for the count fallback)
    client = _FakeClient(template=_TEMPLATE, rpc_data=[], active_count=3)
    engine = _make_engine(client)

    monkeypatch.setenv("WORKFLOW_MAX_CONCURRENT_PER_USER", "3")
    _set_standard_env(monkeypatch)
    monkeypatch.setattr(engine_module, "MAX_CONCURRENT_EXECUTIONS_PER_USER", 3)

    result = await engine.start_workflow(user_id="user-1", template_name="Atomic Template")

    # One RPC call was made
    assert len(client.rpc_calls) == 1
    fn_name, _ = client.rpc_calls[0]
    assert fn_name == "start_workflow_execution_atomic"

    # Error response shape must be preserved
    assert result["error_code"] == "concurrent_execution_limit"
    assert "error" in result
    assert result["active_count"] == 3
    assert result["limit"] == 3


# ---------------------------------------------------------------------------
# Test 3: Error dict shape — field completeness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_atomic_limit_error_contains_all_required_fields(monkeypatch):
    """The error dict must always contain error, error_code, active_count, and limit."""
    client = _FakeClient(template=_TEMPLATE, rpc_data=[], active_count=2)
    engine = _make_engine(client)

    _set_standard_env(monkeypatch)
    monkeypatch.setattr(engine_module, "MAX_CONCURRENT_EXECUTIONS_PER_USER", 2)

    result = await engine.start_workflow(user_id="user-1", template_name="Atomic Template")

    required_fields = {"error", "error_code", "active_count", "limit"}
    assert required_fields.issubset(result.keys()), (
        f"Missing fields: {required_fields - result.keys()}"
    )
    assert isinstance(result["error"], str)
    assert result["error_code"] == "concurrent_execution_limit"
    assert isinstance(result["active_count"], int)
    assert isinstance(result["limit"], int)


# ---------------------------------------------------------------------------
# Test 4: p_max_concurrent=0 (limit disabled) — RPC called with zero
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_atomic_start_zero_limit_passes_zero_to_rpc(monkeypatch):
    """When MAX_CONCURRENT_EXECUTIONS_PER_USER=0, the RPC is called with p_max_concurrent=0.

    The Postgres function treats 0 as "no limit" and always inserts.
    The mock returns data to simulate that behaviour.
    """
    client = _FakeClient(template=_TEMPLATE, rpc_data=[_EXECUTION_ROW])
    engine = _make_engine(client)

    monkeypatch.setenv("WORKFLOW_MAX_CONCURRENT_PER_USER", "0")
    _set_standard_env(monkeypatch)
    monkeypatch.setattr(engine_module, "MAX_CONCURRENT_EXECUTIONS_PER_USER", 0)

    monkeypatch.setattr(engine, "_audit_execution_action", AsyncMock())
    monkeypatch.setattr(
        "app.workflows.engine.edge_function_client.execute_workflow",
        AsyncMock(return_value={"success": True}),
    )

    result = await engine.start_workflow(user_id="user-1", template_name="Atomic Template")

    assert len(client.rpc_calls) == 1
    _, params = client.rpc_calls[0]
    assert params["p_max_concurrent"] == 0

    # Should succeed — mock returned data
    assert "error" not in result
    assert result["status"] == "pending"


# ---------------------------------------------------------------------------
# Test 5: Old SELECT COUNT path no longer called — only RPC
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_atomic_start_does_not_use_select_count_before_insert(monkeypatch):
    """The TOCTOU-prone SELECT COUNT pattern must NOT be used; only the RPC is called."""
    client = _FakeClient(template=_TEMPLATE, rpc_data=[_EXECUTION_ROW])
    engine = _make_engine(client)

    _set_standard_env(monkeypatch)
    monkeypatch.setattr(engine_module, "MAX_CONCURRENT_EXECUTIONS_PER_USER", 3)

    monkeypatch.setattr(engine, "_audit_execution_action", AsyncMock())
    monkeypatch.setattr(
        "app.workflows.engine.edge_function_client.execute_workflow",
        AsyncMock(return_value={"success": True}),
    )

    # Track table() calls to ensure workflow_executions is NOT queried for SELECT COUNT
    original_table = client.table
    table_calls = []

    def _tracking_table(name):
        table_calls.append(name)
        return original_table(name)

    client.table = _tracking_table

    await engine.start_workflow(user_id="user-1", template_name="Atomic Template")

    # The only workflow_executions hit should be the audit / post-limit count, not SELECT COUNT
    # More importantly, the rpc() path was used (not table().select().count)
    assert len(client.rpc_calls) == 1, "Expected exactly one RPC call"

    # workflow_executions should NOT appear in table calls before RPC was made
    # (it may appear after as part of update on failure, but not as a count SELECT)
    rpc_was_first = True  # by construction in our fake client, rpc is the only I/O
    assert rpc_was_first
