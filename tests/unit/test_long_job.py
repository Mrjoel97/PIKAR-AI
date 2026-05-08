# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for long-running job helpers (LONGTASK-01).

Covers:
- ``submit_long_job`` inserts a row with the right shape.
- ``poll_job_progress`` yields progress events as the row state advances
  and terminates on a completion status.
- ``run_as_long_job`` agent tool returns the handoff dict and pushes a
  ``long_task_started`` event onto the request progress queue.
- ``wrap_long_task_as_job_handoff`` produces the SSE event payload and
  the allowlist passes the new event types through.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import long_job as long_job_module
from app.sse_utils import (
    _PROGRESS_EVENT_ALLOWLIST,
    serialize_progress_event,
    wrap_long_task_as_job_handoff,
)


# ---------------------------------------------------------------------------
# Helpers — fake Supabase table chain
# ---------------------------------------------------------------------------


def _make_async_client_with_row(row: dict | None) -> MagicMock:
    """Build an AsyncClient mock whose .table().select()...execute() returns row."""
    client = MagicMock()

    async def _async_execute():
        resp = MagicMock()
        resp.data = [row] if row is not None else []
        return resp

    table = MagicMock()
    select = MagicMock()
    eq = MagicMock()
    limit = MagicMock()

    client.table.return_value = table
    table.select.return_value = select
    select.eq.return_value = eq
    eq.limit.return_value = limit
    limit.execute = _async_execute

    # Insert chain (used by submit_long_job)
    insert = MagicMock()
    table.insert.return_value = insert
    insert.execute = AsyncMock(return_value=MagicMock(data=[row] if row else []))

    return client


# ---------------------------------------------------------------------------
# submit_long_job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_long_job_inserts_pending_row():
    """submit_long_job inserts a row with status=pending and returns id."""
    captured: dict = {}

    async def _fake_get_async_client():
        client = MagicMock()
        table = MagicMock()
        client.table.return_value = table

        insert_mock = MagicMock()
        table.insert.return_value = insert_mock
        insert_mock.execute = AsyncMock(return_value=MagicMock(data=[{"id": "x"}]))

        def _capture_insert(row):
            captured["row"] = row
            return insert_mock

        table.insert.side_effect = _capture_insert
        return client

    with patch.object(long_job_module, "get_async_client", _fake_get_async_client):
        job_id = await long_job_module.submit_long_job(
            kind="daily_report",
            payload={"foo": "bar"},
            user_id="user-1",
            session_id="sess-99",
        )

    assert job_id  # uuid
    row = captured["row"]
    assert row["status"] == "pending"
    assert row["job_type"] == "daily_report"
    assert row["user_id"] == "user-1"
    assert row["input_data"]["foo"] == "bar"
    # session_id should be merged into the payload so handlers can read it
    assert row["input_data"]["session_id"] == "sess-99"
    # Auto-generated id is propagated into the row
    assert row["id"] == job_id


@pytest.mark.asyncio
async def test_submit_long_job_does_not_overwrite_existing_session_id():
    """When payload already carries session_id we keep it as-is."""

    captured: dict = {}

    async def _fake_get_async_client():
        client = MagicMock()
        table = MagicMock()
        client.table.return_value = table

        insert_mock = MagicMock()
        insert_mock.execute = AsyncMock(return_value=MagicMock(data=[{"id": "x"}]))

        def _capture_insert(row):
            captured["row"] = row
            return insert_mock

        table.insert.side_effect = _capture_insert
        return client

    with patch.object(long_job_module, "get_async_client", _fake_get_async_client):
        await long_job_module.submit_long_job(
            kind="weekly_digest",
            payload={"session_id": "explicit"},
            user_id="user-1",
            session_id="from-context",
        )

    assert captured["row"]["input_data"]["session_id"] == "explicit"


# ---------------------------------------------------------------------------
# poll_job_progress
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_poll_job_progress_yields_until_completed():
    """poll_job_progress yields progress events as status flips, ending on completed."""
    states = [
        {
            "id": "job-1",
            "user_id": "user-1",
            "job_type": "daily_report",
            "status": "pending",
            "input_data": {"estimated_duration_s": 600},
            "output_data": None,
        },
        {
            "id": "job-1",
            "user_id": "user-1",
            "job_type": "daily_report",
            "status": "processing",
            "input_data": {},
            "output_data": {"progress_pct": 40, "message": "halfway"},
        },
        {
            "id": "job-1",
            "user_id": "user-1",
            "job_type": "daily_report",
            "status": "completed",
            "input_data": {},
            "output_data": {"progress_pct": 100, "summary": "done"},
            "completed_at": "2026-05-09T00:00:00Z",
        },
    ]
    state_iter = iter(states)
    last_state: dict[str, dict | None] = {"row": None}

    async def _fake_get_job_row(job_id, *, user_id=None):
        try:
            last_state["row"] = next(state_iter)
        except StopIteration:
            pass
        return last_state["row"]

    # Patch sleep to avoid real waits
    async def _no_sleep(_s):
        return None

    with patch.object(long_job_module, "get_job_row", _fake_get_job_row), patch.object(
        long_job_module.asyncio, "sleep", _no_sleep
    ):
        events: list[dict] = []
        async for ev in long_job_module.poll_job_progress("job-1", user_id="user-1"):
            events.append(ev)

    statuses = [e["status"] for e in events]
    assert "pending" in statuses
    assert "processing" in statuses
    assert events[-1]["status"] == "completed"
    assert events[-1]["event_type"] == "long_task_completed"
    # Result is forwarded
    assert events[-1]["result"]["summary"] == "done"
    # Progress detail is preserved on the processing event
    proc = next(e for e in events if e["status"] == "processing")
    assert proc["progress_pct"] == 40
    assert proc["message"] == "halfway"


@pytest.mark.asyncio
async def test_poll_job_progress_yields_failure_for_missing_row():
    async def _fake_get_job_row(job_id, *, user_id=None):
        return None

    with patch.object(long_job_module, "get_job_row", _fake_get_job_row):
        events: list[dict] = []
        async for ev in long_job_module.poll_job_progress("missing", user_id="u"):
            events.append(ev)

    assert len(events) == 1
    assert events[0]["status"] == "failed"
    assert events[0]["error"] == "job_not_found"


# ---------------------------------------------------------------------------
# run_as_long_job tool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_as_long_job_returns_handoff_dict_and_enqueues_event():
    """run_as_long_job submits a job and pushes a long_task_started event."""
    from app.agents.tools import long_task as long_task_mod

    queue: asyncio.Queue = asyncio.Queue()

    with patch.object(
        long_task_mod, "submit_long_job", AsyncMock(return_value="job-xyz")
    ), patch.object(
        long_task_mod, "get_current_user_id", lambda: "user-1"
    ), patch.object(
        long_task_mod, "get_current_session_id", lambda: "sess-1"
    ), patch.object(
        long_task_mod, "get_current_progress_queue", lambda: queue
    ):
        result = await long_task_mod.run_as_long_job(
            kind="daily_report",
            payload={"foo": "bar"},
            estimated_duration_s=900,
        )

    assert result["success"] is True
    assert result["kind"] == "long_task_handoff"
    assert result["job_id"] == "job-xyz"
    assert result["status"] == "pending"
    assert result["estimated_duration_s"] == 900
    assert result["poll_url"] == "/jobs/job-xyz/progress"
    assert "user_message" in result

    # The progress queue should now hold a long_task_started event
    enqueued = queue.get_nowait()
    assert enqueued["event_type"] == "long_task_started"
    assert enqueued["job_id"] == "job-xyz"
    assert enqueued["estimated_duration_s"] == 900
    assert enqueued["poll_url"] == "/jobs/job-xyz/progress"


@pytest.mark.asyncio
async def test_run_as_long_job_handles_submit_failure():
    """If submission fails we return a failure handoff (no exception)."""
    from app.agents.tools import long_task as long_task_mod

    with patch.object(
        long_task_mod,
        "submit_long_job",
        AsyncMock(side_effect=RuntimeError("db down")),
    ), patch.object(long_task_mod, "get_current_user_id", lambda: "u"), patch.object(
        long_task_mod, "get_current_session_id", lambda: "s"
    ), patch.object(long_task_mod, "get_current_progress_queue", lambda: None):
        result = await long_task_mod.run_as_long_job(
            kind="weekly_digest", payload={}
        )

    assert result["success"] is False
    assert result["kind"] == "long_task_handoff"
    assert "db down" in result["error"]


# ---------------------------------------------------------------------------
# SSE wrapper + allowlist
# ---------------------------------------------------------------------------


def test_wrap_long_task_as_job_handoff_shape():
    payload = wrap_long_task_as_job_handoff(
        {
            "job_id": "abc",
            "kind": "daily_report",
            "estimated_duration_s": 600,
        }
    )
    assert payload["event_type"] == "long_task_started"
    assert payload["job_id"] == "abc"
    assert payload["kind"] == "daily_report"
    assert payload["estimated_duration_s"] == 600
    assert payload["poll_url"] == "/jobs/abc/progress"
    assert isinstance(payload["ts"], int)


def test_progress_allowlist_includes_long_task_events():
    for name in (
        "long_task_started",
        "long_task_progress",
        "long_task_completed",
    ):
        assert name in _PROGRESS_EVENT_ALLOWLIST


def test_serialize_progress_event_passes_long_task_started_through():
    serialized = serialize_progress_event(
        {
            "event_type": "long_task_started",
            "job_id": "abc",
            "kind": "daily_report",
            "estimated_duration_s": 600,
            "poll_url": "/jobs/abc/progress",
        }
    )
    decoded = json.loads(serialized)
    assert decoded["event_type"] == "long_task_started"
    assert decoded["job_id"] == "abc"
    assert decoded["kind"] == "daily_report"
    assert decoded["poll_url"] == "/jobs/abc/progress"


def test_serialize_progress_event_passes_long_task_completed_through():
    serialized = serialize_progress_event(
        {
            "event_type": "long_task_completed",
            "job_id": "abc",
            "status": "completed",
            "result": {"summary": "done"},
        }
    )
    decoded = json.loads(serialized)
    assert decoded["event_type"] == "long_task_completed"
    assert decoded["status"] == "completed"
    assert decoded["result"] == {"summary": "done"}
