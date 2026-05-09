"""Tests verifying WorkflowWorker hot paths use the async Supabase client.

The audit (LONGTASK) flagged synchronous ``.execute()`` calls inside
``async def`` methods of ``WorkflowWorker`` as event-loop blockers.
These tests pin down two guarantees:

1. The worker's hot-path methods (claim_next_job, execute_ai_job's RPC
   calls, cleanup_old_sessions, prune_old_versions, reap_stale_jobs)
   route their I/O through ``_get_async_supabase`` — i.e. the async
   Supabase client — and ``await`` the resulting builder.
2. A static check on the source confirms no sync ``self.client.rpc(...)
   .execute()`` or ``self.client.table(...)...execute()`` patterns
   remain on those hot paths (the sync ``self.client`` is still used by
   ``StepExecutor`` and ``get_runnable_steps`` which is intentional).
"""

from __future__ import annotations

import inspect
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _stub_registry_module():
    """Mirror the stub used by test_longtask_config to keep import
    side-effects identical when this module is run in isolation."""
    name = "app.agents.tools.registry"
    if name in sys.modules and not isinstance(sys.modules[name], types.ModuleType):
        return
    mod = types.ModuleType(name)
    mod.get_tool = lambda *_a, **_k: None
    mod.TOOL_REGISTRY = {}
    sys.modules[name] = mod


_stub_registry_module()


# ---------------------------------------------------------------------------
# Async fake client
# ---------------------------------------------------------------------------


class _AsyncQuery:
    """Awaitable, chainable stand-in for the async postgrest builder."""

    def __init__(self, recorder, op, payload=None, data=None):
        self._recorder = recorder
        self._op = op
        self._payload = payload
        self._data = data if data is not None else []

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def lt(self, *_a, **_k):
        return self

    def in_(self, *_a, **_k):
        return self

    def delete(self):
        self._op = "delete"
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    async def execute(self):
        self._recorder.calls.append(
            {"op": "execute", "kind": self._op, "payload": self._payload}
        )
        return MagicMock(data=self._data)


class _AsyncRPC(_AsyncQuery):
    """RPC handle — separate so the recorder can distinguish it from .table()."""


class _AsyncFakeClient:
    """Minimal async Supabase double covering the hot paths under test."""

    def __init__(self, *, rpc_data=None, select_rows=None):
        self.calls: list[dict] = []
        self._rpc_data = rpc_data if rpc_data is not None else []
        self._select_rows = select_rows if select_rows is not None else []

    def rpc(self, name, params):
        self.calls.append({"op": "rpc", "name": name, "params": params})
        return _AsyncRPC(self, "rpc", data=self._rpc_data)

    def table(self, name):
        self.calls.append({"op": "table", "name": name})
        return _AsyncQuery(self, "table_root", data=self._select_rows)


# ---------------------------------------------------------------------------
# Worker fixture
# ---------------------------------------------------------------------------


def _make_worker(async_client):
    from app.workflows import worker as worker_mod

    sync_stub = MagicMock()
    with patch.object(
        worker_mod.WorkflowWorker, "_get_supabase", return_value=sync_stub
    ):
        with patch.object(worker_mod, "get_workflow_engine", return_value=MagicMock()):
            with patch.object(worker_mod, "StepExecutor", return_value=MagicMock()):
                w = worker_mod.WorkflowWorker()
    w._async_client = async_client
    return w


# ---------------------------------------------------------------------------
# Behavioural tests — each hot path awaits the async client.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_next_job_uses_async_rpc():
    fake = _AsyncFakeClient(rpc_data=[{"id": "job-1", "job_type": "x"}])
    worker = _make_worker(fake)

    result = await worker.claim_next_job()

    assert result == {"id": "job-1", "job_type": "x"}
    rpc_calls = [c for c in fake.calls if c["op"] == "rpc"]
    assert any(c["name"] == "claim_next_ai_job" for c in rpc_calls)


@pytest.mark.asyncio
async def test_execute_ai_job_completes_via_async_rpc():
    fake = _AsyncFakeClient()
    worker = _make_worker(fake)
    worker.handle_job_type = AsyncMock(return_value={"ok": True})

    await worker.execute_ai_job(
        {"id": "job-2", "job_type": "daily_report", "input_data": {}}
    )

    rpc_names = [c["name"] for c in fake.calls if c["op"] == "rpc"]
    assert "complete_ai_job" in rpc_names
    assert "fail_ai_job" not in rpc_names


@pytest.mark.asyncio
async def test_execute_ai_job_failure_uses_async_fail_rpc():
    fake = _AsyncFakeClient()
    worker = _make_worker(fake)
    worker.handle_job_type = AsyncMock(side_effect=RuntimeError("boom"))

    await worker.execute_ai_job(
        {"id": "job-3", "job_type": "daily_report", "input_data": {}}
    )

    rpc_names = [c["name"] for c in fake.calls if c["op"] == "rpc"]
    assert "fail_ai_job" in rpc_names


@pytest.mark.asyncio
async def test_prune_old_versions_uses_async_rpc():
    fake = _AsyncFakeClient(rpc_data=7)
    worker = _make_worker(fake)

    await worker.prune_old_versions(keep_versions=10)

    rpc_calls = [c for c in fake.calls if c["op"] == "rpc"]
    assert any(c["name"] == "prune_session_versions" for c in rpc_calls)


@pytest.mark.asyncio
async def test_cleanup_old_sessions_uses_async_table():
    fake = _AsyncFakeClient(select_rows=[{"id": "s-1"}])
    worker = _make_worker(fake)

    await worker.cleanup_old_sessions(days=7)

    table_calls = [c for c in fake.calls if c["op"] == "table"]
    assert any(c["name"] == "sessions" for c in table_calls)


@pytest.mark.asyncio
async def test_reap_stale_jobs_uses_async_table():
    fake = _AsyncFakeClient(select_rows=[{"id": "j-1", "error_message": None}])
    worker = _make_worker(fake)

    await worker.reap_stale_jobs(timeout_hours=1)

    table_calls = [c for c in fake.calls if c["op"] == "table"]
    # one for the select, one for the update
    assert sum(1 for c in table_calls if c["name"] == "ai_jobs") >= 2


# ---------------------------------------------------------------------------
# Static guarantee — the audit-cited hot paths no longer issue sync I/O.
# ---------------------------------------------------------------------------


def test_hot_paths_have_no_sync_execute_calls():
    """The audit cited four blocking sites; verify all four are gone.

    We do NOT enforce this on ``StepExecutor`` consumers (e.g.
    ``get_runnable_steps``) which intentionally retain the sync client
    so ``StepExecutor`` continues to work unchanged.
    """
    from app.workflows import worker as worker_mod

    hot_paths = [
        worker_mod.WorkflowWorker.claim_next_job,
        worker_mod.WorkflowWorker.execute_ai_job,
        worker_mod.WorkflowWorker.cleanup_old_sessions,
        worker_mod.WorkflowWorker.prune_old_versions,
        worker_mod.WorkflowWorker.reap_stale_jobs,
    ]

    for fn in hot_paths:
        src = inspect.getsource(fn)
        # Sync client usage would appear as "self.client.rpc(" or
        # "self.client.table(" — neither should remain on these paths.
        assert "self.client.rpc(" not in src, (
            f"{fn.__qualname__} still uses sync self.client.rpc"
        )
        assert "self.client.table(" not in src, (
            f"{fn.__qualname__} still uses sync self.client.table"
        )
        # The async client should be reached via the dedicated helper.
        assert "_get_async_supabase" in src, (
            f"{fn.__qualname__} should route I/O through _get_async_supabase"
        )
