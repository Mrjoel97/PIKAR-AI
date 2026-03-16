from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.services import scheduled_endpoints
from app.workflows.worker import WorkflowWorker


def test_verify_scheduler_requires_config(monkeypatch):
    monkeypatch.delenv("SCHEDULER_SECRET", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        scheduled_endpoints._verify_scheduler("secret")

    assert exc_info.value.status_code == 503


def test_verify_scheduler_rejects_wrong_secret(monkeypatch):
    monkeypatch.setenv("SCHEDULER_SECRET", "expected-secret")

    with pytest.raises(HTTPException) as exc_info:
        scheduled_endpoints._verify_scheduler("wrong-secret")

    assert exc_info.value.status_code == 401


def test_verify_scheduler_accepts_correct_secret(monkeypatch):
    monkeypatch.setenv("SCHEDULER_SECRET", "expected-secret")

    assert scheduled_endpoints._verify_scheduler("expected-secret") is True


@pytest.mark.asyncio
async def test_worker_invokes_generic_sync_tool(monkeypatch):
    worker = object.__new__(WorkflowWorker)

    monkeypatch.setattr(
        "app.agents.tools.registry.get_tool",
        lambda _tool_name: lambda **kwargs: {"status": "ok", "payload": kwargs},
    )

    result = await WorkflowWorker.handle_job_type(worker, "custom_tool", {"value": 42})

    assert result == {"status": "ok", "payload": {"value": 42}}


@pytest.mark.asyncio
async def test_worker_handles_workflow_trigger_jobs(monkeypatch):
    worker = object.__new__(WorkflowWorker)
    trigger_service = SimpleNamespace(execute_trigger_job=AsyncMock(return_value={"status": "success"}))
    monkeypatch.setattr(
        "app.services.workflow_trigger_service.get_workflow_trigger_service",
        lambda: trigger_service,
    )

    result = await WorkflowWorker.handle_job_type(worker, "workflow_trigger_start", {"trigger_id": "trg-1"})

    trigger_service.execute_trigger_job.assert_awaited_once_with({"trigger_id": "trg-1"})
    assert result == {"status": "success"}


@pytest.mark.asyncio
async def test_worker_runs_report_scheduler_when_due(monkeypatch):
    worker = object.__new__(WorkflowWorker)
    worker.last_report_schedule_tick = datetime.min
    worker.report_schedule_interval_seconds = 60

    tick_mock = AsyncMock(return_value=[{"status": "success"}])
    monkeypatch.setattr("app.services.report_scheduler.run_scheduler_tick", tick_mock)

    await WorkflowWorker.run_report_scheduler_if_due(worker)
    await WorkflowWorker.run_report_scheduler_if_due(worker)

    assert tick_mock.await_count == 1


@pytest.mark.asyncio
async def test_worker_runs_workflow_trigger_scheduler_when_due(monkeypatch):
    worker = object.__new__(WorkflowWorker)
    worker.last_workflow_trigger_tick = datetime.min
    worker.workflow_trigger_interval_seconds = 60

    tick_mock = AsyncMock(return_value=[{"status": "queued"}])
    monkeypatch.setattr("app.services.workflow_trigger_service.run_workflow_trigger_scheduler_tick", tick_mock)

    await WorkflowWorker.run_workflow_trigger_scheduler_if_due(worker)
    await WorkflowWorker.run_workflow_trigger_scheduler_if_due(worker)

    assert tick_mock.await_count == 1


@pytest.mark.asyncio
async def test_scheduled_endpoint_runs_workflow_trigger_tick(monkeypatch):
    monkeypatch.setenv("SCHEDULER_SECRET", "expected-secret")
    tick_mock = AsyncMock(return_value=[{"status": "queued", "trigger_id": "trg-1"}])
    monkeypatch.setattr("app.services.workflow_trigger_service.run_workflow_trigger_scheduler_tick", tick_mock)

    result = await scheduled_endpoints.trigger_workflow_trigger_tick("expected-secret")

    tick_mock.assert_awaited_once()
    assert result["status"] == "queued"
    assert result["count"] == 1
