# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for MonitoringJobService — CRUD, cadence filtering, and monitoring tick."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(rows=None):
    """Create a mock Supabase client that returns *rows* for all chained calls."""
    data = rows or []
    result = MagicMock()
    result.data = data

    chain = MagicMock()
    chain.insert.return_value = chain
    chain.select.return_value = chain
    chain.update.return_value = chain
    chain.delete.return_value = chain
    chain.eq.return_value = chain
    chain.in_.return_value = chain
    chain.order.return_value = chain
    chain.execute.return_value = result

    client = MagicMock()
    client.table.return_value = chain
    return client, chain, result


def _make_service(client):
    """Construct MonitoringJobService with an injected mock client."""
    with patch(
        "app.services.monitoring_job_service.get_service_client",
        return_value=client,
    ):
        from app.services.monitoring_job_service import MonitoringJobService

        return MonitoringJobService()


def _make_tick_job(job_id="j1", importance="normal", prev_hash=None, keywords=None):
    """Build a minimal job dict for run_monitoring_tick tests."""
    return {
        "id": job_id,
        "user_id": "u1",
        "topic": "Test Topic",
        "monitoring_type": "competitor",
        "importance": importance,
        "is_active": True,
        "keyword_triggers": keywords or [],
        "pinned_urls": [],
        "excluded_urls": [],
        "previous_state_hash": prev_hash,
    }


# ---------------------------------------------------------------------------
# create_job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_job_inserts_and_returns_row():
    """create_job inserts a row and returns the created dict."""
    job_row = {"id": "j1", "user_id": "u1", "topic": "Acme Corp", "is_active": True}
    client, chain, _ = _make_client(rows=[job_row])
    svc = _make_service(client)

    result = await svc.create_job(user_id="u1", topic="Acme Corp")

    assert result["id"] == "j1"
    client.table.assert_called_with("monitoring_jobs")
    chain.insert.assert_called_once()


@pytest.mark.asyncio
async def test_create_job_defaults_importance_normal():
    """create_job uses importance='normal' by default."""
    job_row = {"id": "j1", "user_id": "u1", "topic": "t", "importance": "normal"}
    client, chain, _ = _make_client(rows=[job_row])
    svc = _make_service(client)

    await svc.create_job(user_id="u1", topic="t")

    insert_args = chain.insert.call_args[0][0]
    assert insert_args["importance"] == "normal"


# ---------------------------------------------------------------------------
# list_jobs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_jobs_returns_user_rows():
    """list_jobs returns jobs for the given user_id."""
    rows = [
        {"id": "j1", "user_id": "u1", "topic": "Alpha"},
        {"id": "j2", "user_id": "u1", "topic": "Beta"},
    ]
    client, chain, _ = _make_client(rows=rows)
    svc = _make_service(client)

    jobs = await svc.list_jobs(user_id="u1")

    assert len(jobs) == 2
    chain.eq.assert_any_call("user_id", "u1")


@pytest.mark.asyncio
async def test_list_jobs_empty_returns_empty_list():
    """list_jobs returns empty list when no jobs exist."""
    client, _, _ = _make_client(rows=[])
    svc = _make_service(client)

    assert await svc.list_jobs(user_id="u1") == []


# ---------------------------------------------------------------------------
# update_job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_job_updates_is_active():
    """update_job updates is_active field."""
    updated = {"id": "j1", "user_id": "u1", "is_active": False}
    client, chain, _ = _make_client(rows=[updated])
    svc = _make_service(client)

    result = await svc.update_job(job_id="j1", user_id="u1", is_active=False)

    assert result["is_active"] is False
    update_kwargs = chain.update.call_args[0][0]
    assert update_kwargs["is_active"] is False


@pytest.mark.asyncio
async def test_update_job_updates_importance():
    """update_job updates importance field."""
    updated = {"id": "j1", "user_id": "u1", "importance": "critical"}
    client, chain, _ = _make_client(rows=[updated])
    svc = _make_service(client)

    result = await svc.update_job(job_id="j1", user_id="u1", importance="critical")

    assert result["importance"] == "critical"


# ---------------------------------------------------------------------------
# delete_job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_job_removes_row():
    """delete_job deletes the job and returns deleted=True."""
    client, chain, _ = _make_client(rows=[])
    svc = _make_service(client)

    result = await svc.delete_job(job_id="j1", user_id="u1")

    assert result["deleted"] is True
    chain.delete.assert_called_once()
    chain.eq.assert_any_call("id", "j1")


# ---------------------------------------------------------------------------
# get_due_jobs — cadence filtering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_due_jobs_daily_filters_critical():
    """get_due_jobs('daily') filters for importance=critical only."""
    client, chain, _ = _make_client(rows=[])
    svc = _make_service(client)

    await svc.get_due_jobs("daily")

    chain.eq.assert_any_call("importance", "critical")
    chain.in_.assert_not_called()


@pytest.mark.asyncio
async def test_get_due_jobs_weekly_filters_critical_and_normal():
    """get_due_jobs('weekly') filters for importance in (critical, normal)."""
    client, chain, _ = _make_client(rows=[])
    svc = _make_service(client)

    await svc.get_due_jobs("weekly")

    chain.in_.assert_called_once_with("importance", ["critical", "normal"])


@pytest.mark.asyncio
async def test_get_due_jobs_biweekly_returns_all_active():
    """get_due_jobs('biweekly') returns all active jobs without importance filter."""
    rows = [_make_tick_job("j1", "low"), _make_tick_job("j2", "normal")]
    client, chain, _ = _make_client(rows=rows)
    svc = _make_service(client)

    result = await svc.get_due_jobs("biweekly")

    chain.in_.assert_not_called()
    assert len(result) == 2


# ---------------------------------------------------------------------------
# run_monitoring_tick — execution flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_monitoring_tick_calls_research_for_each_job():
    """run_monitoring_tick calls _execute_research_job for each due job."""
    client, _, _ = _make_client(rows=[])
    svc = _make_service(client)
    job = _make_tick_job()

    mock_exec = AsyncMock(
        return_value={
            "success": True,
            "synthesis": {"findings": [{"text": "test findings"}], "success": True},
        }
    )

    with (
        patch.object(svc, "get_due_jobs", new=AsyncMock(return_value=[job])),
        patch("app.services.monitoring_job_service._check_budget", return_value=True),
        patch("app.services.monitoring_job_service._execute_research_job", mock_exec),
        patch("app.services.monitoring_job_service.write_to_graph", return_value={}),
        patch("app.services.monitoring_job_service.write_to_vault", new=AsyncMock(return_value={})),
        patch(
            "app.services.monitoring_job_service._is_significant_change",
            new=AsyncMock(return_value=False),
        ),
    ):
        results = await svc.run_monitoring_tick("daily")

    mock_exec.assert_called_once()
    assert results[0]["status"] == "success"


@pytest.mark.asyncio
async def test_run_monitoring_tick_skips_when_budget_exhausted():
    """run_monitoring_tick skips jobs when _check_budget returns False."""
    client, _, _ = _make_client(rows=[])
    svc = _make_service(client)
    job = _make_tick_job()

    mock_exec = AsyncMock()

    with (
        patch.object(svc, "get_due_jobs", new=AsyncMock(return_value=[job])),
        patch("app.services.monitoring_job_service._check_budget", return_value=False),
        patch("app.services.monitoring_job_service._execute_research_job", mock_exec),
    ):
        results = await svc.run_monitoring_tick("daily")

    mock_exec.assert_not_called()
    assert results[0]["status"] == "skipped"
    assert results[0]["alerted"] is False


@pytest.mark.asyncio
async def test_run_monitoring_tick_alerts_on_keyword_match():
    """run_monitoring_tick dispatches notification when keyword triggers match."""
    job = _make_tick_job(prev_hash="old", keywords=["layoffs"])
    client, _, _ = _make_client(rows=[])
    svc = _make_service(client)
    mock_dispatch = AsyncMock()

    with (
        patch.object(svc, "get_due_jobs", new=AsyncMock(return_value=[job])),
        patch("app.services.monitoring_job_service._check_budget", return_value=True),
        patch(
            "app.services.monitoring_job_service._execute_research_job",
            new=AsyncMock(
                return_value={
                    "success": True,
                    "synthesis": {
                        "findings": [
                            {"text": "Company announced layoffs of 200 staff this quarter"}
                        ],
                        "success": True,
                    },
                }
            ),
        ),
        patch("app.services.monitoring_job_service.write_to_graph", return_value={}),
        patch("app.services.monitoring_job_service.write_to_vault", new=AsyncMock(return_value={})),
        patch("app.services.monitoring_job_service.dispatch_notification", mock_dispatch),
    ):
        results = await svc.run_monitoring_tick("daily")

    mock_dispatch.assert_called_once()
    assert results[0]["alerted"] is True


@pytest.mark.asyncio
async def test_run_monitoring_tick_alerts_on_ai_significance():
    """run_monitoring_tick dispatches alert when AI significance check returns True."""
    job = _make_tick_job(prev_hash="old")
    client, _, _ = _make_client(rows=[])
    svc = _make_service(client)
    mock_dispatch = AsyncMock()

    with (
        patch.object(svc, "get_due_jobs", new=AsyncMock(return_value=[job])),
        patch("app.services.monitoring_job_service._check_budget", return_value=True),
        patch(
            "app.services.monitoring_job_service._execute_research_job",
            new=AsyncMock(
                return_value={
                    "success": True,
                    "synthesis": {"findings": [{"text": "Major product launch announced"}], "success": True},
                }
            ),
        ),
        patch("app.services.monitoring_job_service.write_to_graph", return_value={}),
        patch("app.services.monitoring_job_service.write_to_vault", new=AsyncMock(return_value={})),
        patch(
            "app.services.monitoring_job_service._is_significant_change",
            new=AsyncMock(return_value=True),
        ),
        patch("app.services.monitoring_job_service.dispatch_notification", mock_dispatch),
    ):
        results = await svc.run_monitoring_tick("daily")

    mock_dispatch.assert_called_once()
    assert results[0]["alerted"] is True


@pytest.mark.asyncio
async def test_run_monitoring_tick_updates_hash_after_execution():
    """run_monitoring_tick updates last_run_at and previous_state_hash after run."""
    job = _make_tick_job(prev_hash=None)
    client, chain, _ = _make_client(rows=[])
    svc = _make_service(client)

    with (
        patch.object(svc, "get_due_jobs", new=AsyncMock(return_value=[job])),
        patch("app.services.monitoring_job_service._check_budget", return_value=True),
        patch(
            "app.services.monitoring_job_service._execute_research_job",
            new=AsyncMock(
                return_value={
                    "success": True,
                    "synthesis": {"findings": [{"text": "some findings"}], "success": True},
                }
            ),
        ),
        patch("app.services.monitoring_job_service.write_to_graph", return_value={}),
        patch("app.services.monitoring_job_service.write_to_vault", new=AsyncMock(return_value={})),
        patch(
            "app.services.monitoring_job_service._is_significant_change",
            new=AsyncMock(return_value=False),
        ),
    ):
        results = await svc.run_monitoring_tick("daily")

    chain.update.assert_called()
    payload = chain.update.call_args[0][0]
    assert "last_run_at" in payload
    assert "previous_state_hash" in payload
    assert results[0]["status"] == "success"


@pytest.mark.asyncio
async def test_run_monitoring_tick_calls_write_to_graph_and_vault():
    """run_monitoring_tick writes results to knowledge graph and vault."""
    job = _make_tick_job()
    client, _, _ = _make_client(rows=[])
    svc = _make_service(client)

    mock_graph = MagicMock(return_value={})
    mock_vault = AsyncMock(return_value={})

    with (
        patch.object(svc, "get_due_jobs", new=AsyncMock(return_value=[job])),
        patch("app.services.monitoring_job_service._check_budget", return_value=True),
        patch(
            "app.services.monitoring_job_service._execute_research_job",
            new=AsyncMock(
                return_value={
                    "success": True,
                    "synthesis": {"findings": [{"text": "findings"}], "success": True},
                }
            ),
        ),
        patch("app.services.monitoring_job_service.write_to_graph", mock_graph),
        patch("app.services.monitoring_job_service.write_to_vault", mock_vault),
        patch(
            "app.services.monitoring_job_service._is_significant_change",
            new=AsyncMock(return_value=False),
        ),
    ):
        await svc.run_monitoring_tick("daily")

    mock_graph.assert_called_once()
    mock_vault.assert_called_once()


# ---------------------------------------------------------------------------
# /monitoring-tick endpoint — scheduler secret
# ---------------------------------------------------------------------------


def test_monitoring_tick_endpoint_rejects_missing_secret():
    """POST /scheduled/monitoring-tick returns 401 without X-Scheduler-Secret."""
    os.environ["SCHEDULER_SECRET"] = "test-secret"

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.services.scheduled_endpoints import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/scheduled/monitoring-tick")
    assert response.status_code == 401


def test_monitoring_tick_endpoint_rejects_wrong_secret():
    """POST /scheduled/monitoring-tick returns 401 with wrong secret."""
    os.environ["SCHEDULER_SECRET"] = "correct-secret"

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.services.scheduled_endpoints import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/scheduled/monitoring-tick",
        headers={"X-Scheduler-Secret": "wrong-secret"},
    )
    assert response.status_code == 401
