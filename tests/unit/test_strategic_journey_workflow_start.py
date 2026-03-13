"""Unit tests for strategic start_journey_workflow behavior."""

import pytest

import app.agents.strategic.tools as strategic_tools


class _StubInitiativeService:
    async def get_initiative(self, initiative_id, user_id=None):
        return {
            "id": initiative_id,
            "title": "Acquire first clients",
            "metadata": {
                "journey_id": "journey-1",
                "desired_outcomes": "Acquire first 3 clients",
                "timeline": "90 days",
            },
        }

    async def update_operational_state(self, initiative_id, **kwargs):
        return {
            "id": initiative_id,
            "metadata": {"operational_state": kwargs},
            "verification_status": kwargs.get("verification_status"),
            "trust_summary": kwargs.get("trust_summary") or {},
        }

    async def update_initiative(self, _initiative_id, workflow_execution_id=None, status=None, metadata=None, user_id=None):
        return {
            "workflow_execution_id": workflow_execution_id,
            "status": status,
            "metadata": metadata or {},
            "user_id": user_id,
        }


class _StubInitiativeServiceMissingInputs(_StubInitiativeService):
    async def get_initiative(self, initiative_id, user_id=None):
        return {
            "id": initiative_id,
            "title": "Acquire first clients",
            "metadata": {
                "journey_id": "journey-1",
            },
        }


class _StubJourneyQuery:
    def __init__(self, row):
        self._row = row

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def execute(self):
        class _Resp:
            pass

        resp = _Resp()
        resp.data = [self._row]
        return resp


class _StubSupabaseClient:
    def __init__(self, row):
        self._row = row

    def table(self, name):
        if name != "user_journeys":
            raise AssertionError(f"Unexpected table: {name}")
        return _StubJourneyQuery(self._row)


class _StubEngine:
    def __init__(self, response):
        self._response = response
        self.calls = []

    async def start_workflow(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        return self._response


@pytest.mark.asyncio
async def test_start_journey_workflow_passes_context_with_keyword_args(monkeypatch):
    stub_engine = _StubEngine(
        {
            "execution_id": "exec-1",
            "status": "pending",
            "message": "queued",
            "current_step": "Phase 1: Step 1",
        }
    )
    journey_row = {
        "primary_workflow_template_name": "Lead Generation Workflow",
        "title": "First Client Acquisition",
        "suggested_workflows": [],
    }

    monkeypatch.setattr("app.services.request_context.get_current_user_id", lambda: "user-1")
    monkeypatch.setattr("app.services.initiative_service.InitiativeService", lambda: _StubInitiativeService())
    monkeypatch.setattr("app.services.supabase.get_service_client", lambda: _StubSupabaseClient(journey_row))
    monkeypatch.setattr("app.workflows.engine.get_workflow_engine", lambda: stub_engine)

    result = await strategic_tools.start_journey_workflow("init-1")

    assert result["success"] is True
    assert result["workflow_execution_id"] == "exec-1"
    assert len(stub_engine.calls) == 1
    call = stub_engine.calls[0]
    assert call["args"] == ()
    assert call["kwargs"]["user_id"] == "user-1"
    assert call["kwargs"]["template_name"] == "Lead Generation Workflow"
    assert call["kwargs"]["run_source"] == "agent_ui"
    assert call["kwargs"]["context"]["initiative_id"] == "init-1"
    assert call["kwargs"]["context"]["desired_outcomes"] == "Acquire first 3 clients"
    assert call["kwargs"]["context"]["timeline"] == "90 days"
    assert call["kwargs"]["context"]["user_id"] == "user-1"
    assert isinstance(result["trust_summary"], dict)


@pytest.mark.asyncio
async def test_start_journey_workflow_returns_kernel_blockers(monkeypatch):
    stub_engine = _StubEngine(
        {
            "error": "Workflow 'Lead Generation Workflow' is not ready for execution",
            "error_code": "workflow_not_ready",
            "readiness": {"status": "blocked", "reason_codes": ["integration_missing"]},
        }
    )
    journey_row = {
        "primary_workflow_template_name": "Lead Generation Workflow",
        "title": "First Client Acquisition",
        "suggested_workflows": [],
    }

    monkeypatch.setattr("app.services.request_context.get_current_user_id", lambda: "user-1")
    monkeypatch.setattr("app.services.initiative_service.InitiativeService", lambda: _StubInitiativeService())
    monkeypatch.setattr("app.services.supabase.get_service_client", lambda: _StubSupabaseClient(journey_row))
    monkeypatch.setattr("app.workflows.engine.get_workflow_engine", lambda: stub_engine)

    result = await strategic_tools.start_journey_workflow("init-1")

    assert result["success"] is False
    assert result["error_code"] == "workflow_contract_invalid"
    assert len(result["blockers"]) >= 1


@pytest.mark.asyncio
async def test_start_journey_workflow_defaults_missing_inputs(monkeypatch):
    stub_engine = _StubEngine(
        {
            "execution_id": "exec-2",
            "status": "pending",
            "message": "queued",
            "current_step": "Phase 1: Step 1",
        }
    )
    journey_row = {
        "primary_workflow_template_name": "Lead Generation Workflow",
        "title": "First Client Acquisition",
        "suggested_workflows": [],
    }

    monkeypatch.setattr("app.services.request_context.get_current_user_id", lambda: "user-1")
    monkeypatch.setattr("app.services.initiative_service.InitiativeService", lambda: _StubInitiativeServiceMissingInputs())
    monkeypatch.setattr("app.services.supabase.get_service_client", lambda: _StubSupabaseClient(journey_row))
    monkeypatch.setattr("app.workflows.engine.get_workflow_engine", lambda: stub_engine)

    result = await strategic_tools.start_journey_workflow("init-2")

    assert result["success"] is True
    assert result["defaulted_inputs"] == ["desired_outcomes", "timeline"]
    call = stub_engine.calls[0]
    assert call["kwargs"]["context"]["desired_outcomes"] == "Not specified"
    assert call["kwargs"]["context"]["timeline"] == "Not specified"
