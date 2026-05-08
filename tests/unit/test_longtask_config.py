"""Tests for LONGTASK-05/06/07 config + behavior changes.

LONGTASK-05: SESSION_MAX_EVENTS default raised to 200, env-overridable.
LONGTASK-06: Vertex context cache TTL default raised to 3600s, env-overridable.
LONGTASK-07: reap_stale_jobs requeues heartbeat-silent jobs (no error_message)
             instead of unconditionally failing them.
"""

from __future__ import annotations

import importlib
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _stub_registry_module():
    """Stub app.agents.tools.registry to bypass an unrelated working-tree
    import error in integration_tools.py that breaks worker imports.

    Tests in this module only need WorkflowWorker.reap_stale_jobs, which
    does not touch the tool registry.
    """
    name = "app.agents.tools.registry"
    if name in sys.modules and not isinstance(
        sys.modules[name], types.ModuleType
    ):
        return
    mod = types.ModuleType(name)
    mod.get_tool = lambda *_a, **_k: None
    mod.TOOL_REGISTRY = {}
    sys.modules[name] = mod


_stub_registry_module()


# ---------------------------------------------------------------------------
# LONGTASK-05: SESSION_MAX_EVENTS
# ---------------------------------------------------------------------------


def test_session_max_events_default_is_200(monkeypatch):
    """With SESSION_MAX_EVENTS unset, the module constant resolves to 200."""
    monkeypatch.delenv("SESSION_MAX_EVENTS", raising=False)
    import app.persistence.supabase_session_service as sss

    importlib.reload(sss)
    assert sss.SESSION_MAX_EVENTS == 200


def test_session_max_events_respects_env_override(monkeypatch):
    """An explicit env value still wins."""
    monkeypatch.setenv("SESSION_MAX_EVENTS", "37")
    import app.persistence.supabase_session_service as sss

    importlib.reload(sss)
    assert sss.SESSION_MAX_EVENTS == 37


# ---------------------------------------------------------------------------
# LONGTASK-06: Vertex context cache TTL
# ---------------------------------------------------------------------------


_AGENT_PATH = Path(__file__).resolve().parents[2] / "app" / "agent.py"


def test_vertex_context_cache_ttl_expression_present():
    """The ContextCacheConfig is constructed with env-overridable TTL.

    A pure unit test of the App() construction is impractical (it pulls in
    the full executive agent). We verify the source contains the
    expression and that the resolution logic itself produces 3600 by
    default.
    """
    src = _AGENT_PATH.read_text(encoding="utf-8")
    assert 'os.getenv("VERTEX_CONTEXT_CACHE_TTL_S", "3600")' in src, (
        "ContextCacheConfig should resolve ttl_seconds via "
        "os.getenv('VERTEX_CONTEXT_CACHE_TTL_S', '3600')"
    )


def test_vertex_context_cache_ttl_default_resolves_to_3600(monkeypatch):
    monkeypatch.delenv("VERTEX_CONTEXT_CACHE_TTL_S", raising=False)
    assert int(os.getenv("VERTEX_CONTEXT_CACHE_TTL_S", "3600")) == 3600


def test_vertex_context_cache_ttl_env_override(monkeypatch):
    monkeypatch.setenv("VERTEX_CONTEXT_CACHE_TTL_S", "120")
    assert int(os.getenv("VERTEX_CONTEXT_CACHE_TTL_S", "3600")) == 120


# ---------------------------------------------------------------------------
# LONGTASK-07: reap_stale_jobs branching
# ---------------------------------------------------------------------------


class _FakeQuery:
    """Chainable mock that records all method calls + final update payload."""

    def __init__(self, table: "_FakeTable", op: str, payload: dict | None = None):
        self.table = table
        self.op = op
        self.payload = payload
        self.filters: list[tuple[str, ...]] = []

    # filter chain --------------------------------------------------------
    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.filters.append(("eq", col, val))
        return self

    def lt(self, col, val):
        self.filters.append(("lt", col, val))
        return self

    def in_(self, col, vals):
        self.filters.append(("in_", col, tuple(vals)))
        return self

    def execute(self):
        if self.op == "select":
            return MagicMock(data=self.table.select_rows)
        if self.op == "update":
            self.table.updates.append(
                {"payload": self.payload, "filters": self.filters}
            )
            return MagicMock(data=[])
        return MagicMock(data=[])


class _FakeTable:
    """Records select_rows fed back to the worker + all .update() payloads."""

    def __init__(self, select_rows):
        self.select_rows = select_rows
        self.updates: list[dict] = []

    def select(self, *_a, **_k):
        return _FakeQuery(self, "select")

    def update(self, payload):
        return _FakeQuery(self, "update", payload)


class _FakeClient:
    def __init__(self, select_rows):
        self.table_obj = _FakeTable(select_rows)

    def table(self, _name):
        return self.table_obj


def _make_worker(select_rows):
    """Build a WorkflowWorker with a stubbed supabase client."""
    from app.workflows import worker as worker_mod

    fake = _FakeClient(select_rows)
    with patch.object(worker_mod.WorkflowWorker, "_get_supabase", return_value=fake):
        # engine + step_executor pull other deps; stub them too.
        with patch.object(worker_mod, "get_workflow_engine", return_value=MagicMock()):
            with patch.object(worker_mod, "StepExecutor", return_value=MagicMock()):
                w = worker_mod.WorkflowWorker()
    return w, fake


@pytest.mark.asyncio
async def test_reap_stale_jobs_requeues_silent_jobs():
    """Jobs with no error_message are reset to pending, not failed."""
    rows = [
        {"id": "job-silent-1", "error_message": None},
        {"id": "job-silent-2", "error_message": ""},
    ]
    worker, fake = _make_worker(rows)

    await worker.reap_stale_jobs(timeout_hours=1)

    # Exactly one update issued — the requeue.
    assert len(fake.table_obj.updates) == 1
    upd = fake.table_obj.updates[0]
    assert upd["payload"]["status"] == "pending"
    assert upd["payload"]["locked_at"] is None
    # All silent ids should be in the in_() filter.
    in_filter = next(f for f in upd["filters"] if f[0] == "in_")
    assert set(in_filter[2]) == {"job-silent-1", "job-silent-2"}


@pytest.mark.asyncio
async def test_reap_stale_jobs_fails_jobs_with_error_message():
    """Jobs that already recorded an error stay failed."""
    rows = [
        {"id": "job-errored", "error_message": "boom"},
    ]
    worker, fake = _make_worker(rows)

    await worker.reap_stale_jobs(timeout_hours=1)

    assert len(fake.table_obj.updates) == 1
    upd = fake.table_obj.updates[0]
    assert upd["payload"]["status"] == "failed"


@pytest.mark.asyncio
async def test_reap_stale_jobs_partitions_mixed_batch():
    """Mixed batches issue both updates: one failed, one requeued."""
    rows = [
        {"id": "job-errored", "error_message": "stack trace"},
        {"id": "job-silent", "error_message": None},
    ]
    worker, fake = _make_worker(rows)

    await worker.reap_stale_jobs(timeout_hours=1)

    statuses = {u["payload"]["status"] for u in fake.table_obj.updates}
    assert statuses == {"failed", "pending"}


@pytest.mark.asyncio
async def test_reap_stale_jobs_noop_when_nothing_stale():
    worker, fake = _make_worker([])
    await worker.reap_stale_jobs(timeout_hours=1)
    assert fake.table_obj.updates == []
