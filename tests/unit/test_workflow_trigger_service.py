from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.workflow_trigger_service import (
    WorkflowTriggerFrequency,
    WorkflowTriggerService,
    WorkflowTriggerType,
)


class _FakeQuery:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.operation = None
        self.payload = None
        self.filters = {}
        self.order_by = None
        self.limit_value = None

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def select(self, *_args, **_kwargs):
        self.operation = self.operation or "select"
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def lte(self, key, value):
        self.filters[key] = value
        return self

    def order(self, key, **kwargs):
        self.order_by = (key, kwargs)
        return self

    def limit(self, value):
        self.limit_value = value
        return self


class _FakeSupabase:
    def __init__(self):
        self.queries = []

    def table(self, name: str):
        query = _FakeQuery(name)
        self.queries.append(query)
        return query


@pytest.mark.asyncio
async def test_create_schedule_trigger_sets_next_run_at(monkeypatch):
    fake_supabase = _FakeSupabase()
    service = WorkflowTriggerService(supabase_client=fake_supabase)

    async def _fake_execute(query, op_name=None):
        assert op_name == "workflow_trigger_service.create_trigger"
        return SimpleNamespace(data=[{"id": "trg-1", **query.payload}])

    monkeypatch.setattr("app.services.workflow_trigger_service.execute_async", _fake_execute)

    result = await service.create_trigger(
        user_id="user-1",
        template_id="tpl-1",
        trigger_name="Daily startup review",
        trigger_type=WorkflowTriggerType.SCHEDULE,
        schedule_frequency=WorkflowTriggerFrequency.DAILY,
        context={"department": "ops"},
    )

    inserted = fake_supabase.queries[0].payload
    assert inserted["trigger_type"] == "schedule"
    assert inserted["schedule_frequency"] == "daily"
    assert inserted["event_name"] is None
    assert inserted["next_run_at"] is not None
    assert result["trigger"]["id"] == "trg-1"


@pytest.mark.asyncio
async def test_dispatch_event_queues_matching_trigger_jobs(monkeypatch):
    fake_supabase = _FakeSupabase()
    service = WorkflowTriggerService(supabase_client=fake_supabase)
    event_trigger = {
        "id": "trg-evt-1",
        "user_id": "user-1",
        "template_id": "tpl-2",
        "trigger_type": "event",
        "context": {"department": "sales"},
        "run_source": "agent_ui",
        "queue_mode": "followup",
        "lane": "automation",
        "persona": "startup",
    }

    async def _fake_execute(query, op_name=None):
        if op_name == "workflow_trigger_service.dispatch_event.lookup":
            return SimpleNamespace(data=[event_trigger])
        if op_name == "workflow_trigger_service.queue_trigger_job":
            return SimpleNamespace(data=[{"id": "job-1", **query.payload}])
        if op_name == "workflow_trigger_service.dispatch_event.bump":
            return SimpleNamespace(data=[{"id": query.filters.get("id")}])
        if op_name == "workflow_trigger_service.dispatch_event.log":
            return SimpleNamespace(data=[{"id": "evt-1", **query.payload}])
        raise AssertionError(f"Unexpected op_name: {op_name}")

    monkeypatch.setattr("app.services.workflow_trigger_service.execute_async", _fake_execute)

    result = await service.dispatch_event(
        user_id="user-1",
        event_name="crm.deal_won",
        payload={"deal_id": "deal-9"},
        source="user_event",
    )

    queued_job = next(
        query for query in fake_supabase.queries if query.table_name == "ai_jobs" and query.operation == "insert"
    )
    assert queued_job.payload["job_type"] == "workflow_trigger_start"
    assert queued_job.payload["input_data"]["event_name"] == "crm.deal_won"
    assert queued_job.payload["input_data"]["payload"] == {"deal_id": "deal-9"}
    assert result["status"] == "queued"
    assert result["matched_trigger_count"] == 1
    assert result["event"]["id"] == "evt-1"


@pytest.mark.asyncio
async def test_execute_trigger_job_routes_through_agent_kernel(monkeypatch):
    service = WorkflowTriggerService(supabase_client=_FakeSupabase())
    kernel = SimpleNamespace(start_workflow_mission=AsyncMock(return_value={"execution_id": "exec-42"}))

    monkeypatch.setattr("app.autonomy.agent_kernel.get_agent_kernel", lambda workflow_engine=None: kernel)
    monkeypatch.setattr("app.workflows.engine.get_workflow_engine", lambda: object())

    result = await service.execute_trigger_job(
        {
            "trigger_id": "trg-1",
            "user_id": "user-1",
            "template_id": "tpl-3",
            "trigger_type": "schedule",
            "context": {"initiative_id": "init-1"},
            "reason": "schedule",
            "event_name": None,
            "payload": {"period": "weekly"},
            "run_source": "agent_ui",
            "persona": "startup",
            "queue_mode": "parallel",
            "lane": "automation",
        }
    )

    kernel.start_workflow_mission.assert_awaited_once()
    kwargs = kernel.start_workflow_mission.await_args.kwargs
    assert kwargs["user_id"] == "user-1"
    assert kwargs["template_id"] == "tpl-3"
    assert kwargs["context"]["initiative_id"] == "init-1"
    assert kwargs["context"]["trigger"] == {
        "id": "trg-1",
        "type": "schedule",
        "reason": "schedule",
        "event_name": None,
    }
    assert kwargs["context"]["event_payload"] == {"period": "weekly"}
    assert kwargs["queue_mode"] == "parallel"
    assert kwargs["lane"] == "automation"
    assert result == {"status": "success", "trigger_id": "trg-1", "execution_id": "exec-42", "result": {"execution_id": "exec-42"}}
