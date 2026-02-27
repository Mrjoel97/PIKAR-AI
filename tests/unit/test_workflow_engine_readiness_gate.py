from unittest.mock import AsyncMock

import pytest

from app.workflows.engine import WorkflowEngine


def _set_callback_env(monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_API_URL", "http://localhost:8000")
    monkeypatch.setenv("WORKFLOW_SERVICE_SECRET", "x" * 40)


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, name: str, db: "_FakeDb"):
        self._name = name
        self._db = db
        self._filters = {}
        self._insert_payload = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self._filters[key] = value
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def insert(self, payload):
        self._insert_payload = payload
        return self

    def execute(self):
        if self._name == "workflow_templates":
            return _FakeResponse([self._db.template])
        if self._name == "workflow_readiness":
            if self._db.readiness_error:
                raise RuntimeError(self._db.readiness_error)
            row = self._db.readiness_row
            if not row:
                return _FakeResponse([])
            template_id = self._filters.get("template_id")
            if template_id and row.get("template_id") != template_id:
                return _FakeResponse([])
            return _FakeResponse([row])
        if self._name == "workflow_executions":
            self._db.execution_inserts.append(self._insert_payload)
            return _FakeResponse([{"id": f"exec-{len(self._db.execution_inserts)}"}])
        return _FakeResponse([])


class _FakeDb:
    def __init__(
        self,
        readiness_row=None,
        readiness_error: str | None = None,
        lifecycle_status: str = "published",
    ):
        self.template = {
            "id": "tpl-1",
            "name": "Template A",
            "version": 1,
            "lifecycle_status": lifecycle_status,
            "phases": [{"name": "Phase 1", "steps": [{"name": "Step 1"}]}],
        }
        self.readiness_row = readiness_row
        self.readiness_error = readiness_error
        self.execution_inserts = []

    def table(self, name: str):
        return _FakeTable(name, self)


@pytest.mark.asyncio
async def test_start_workflow_allows_when_readiness_gate_disabled(monkeypatch):
    fake_db = _FakeDb(
        readiness_row={
            "template_id": "tpl-1",
            "status": "blocked",
            "reason_codes": ["integration_missing"],
        }
    )
    engine = object.__new__(WorkflowEngine)
    engine.client = fake_db

    execute_workflow_mock = AsyncMock(return_value={"success": True})
    monkeypatch.setattr(
        "app.workflows.engine.edge_function_client.execute_workflow",
        execute_workflow_mock,
    )
    monkeypatch.setenv("WORKFLOW_ENFORCE_READINESS_GATE", "false")
    _set_callback_env(monkeypatch)

    result = await engine.start_workflow(user_id="u1", template_name="Template A")

    assert "error" not in result
    assert result["status"] == "pending"
    assert execute_workflow_mock.call_count == 1


@pytest.mark.asyncio
async def test_start_workflow_blocks_draft_for_user_visible_sources(monkeypatch):
    fake_db = _FakeDb(
        readiness_row={
            "template_id": "tpl-1",
            "status": "ready",
            "reason_codes": [],
        },
        lifecycle_status="draft",
    )
    engine = object.__new__(WorkflowEngine)
    engine.client = fake_db
    monkeypatch.setenv("WORKFLOW_ENFORCE_READINESS_GATE", "true")

    result = await engine.start_workflow(
        user_id="u1",
        template_name="Template A",
        run_source="user_ui",
    )

    assert result["error_code"] == "template_not_published"
    assert result["lifecycle_status"] == "draft"


@pytest.mark.asyncio
async def test_start_workflow_allows_draft_for_internal_run_sources(monkeypatch):
    fake_db = _FakeDb(
        readiness_row={
            "template_id": "tpl-1",
            "status": "ready",
            "reason_codes": [],
        },
        lifecycle_status="draft",
    )
    engine = object.__new__(WorkflowEngine)
    engine.client = fake_db
    monkeypatch.setenv("WORKFLOW_ENFORCE_READINESS_GATE", "true")

    execute_workflow_mock = AsyncMock(return_value={"success": True})
    monkeypatch.setattr(
        "app.workflows.engine.edge_function_client.execute_workflow",
        execute_workflow_mock,
    )

    result = await engine.start_workflow(
        user_id="u1",
        template_name="Template A",
        run_source="internal_service",
    )

    assert "error" not in result
    assert result["status"] == "pending"
    assert execute_workflow_mock.call_count == 1


@pytest.mark.asyncio
async def test_start_workflow_blocks_archived_templates(monkeypatch):
    fake_db = _FakeDb(
        readiness_row={
            "template_id": "tpl-1",
            "status": "ready",
            "reason_codes": [],
        },
        lifecycle_status="archived",
    )
    engine = object.__new__(WorkflowEngine)
    engine.client = fake_db
    monkeypatch.setenv("WORKFLOW_ENFORCE_READINESS_GATE", "true")

    result = await engine.start_workflow(user_id="u1", template_name="Template A")

    assert result["error_code"] == "template_archived"


@pytest.mark.asyncio
async def test_start_workflow_blocks_non_ready_when_gate_enabled(monkeypatch):
    fake_db = _FakeDb(
        readiness_row={
            "template_id": "tpl-1",
            "status": "blocked",
            "reason_codes": ["integration_missing", "owner_not_assigned"],
        }
    )
    engine = object.__new__(WorkflowEngine)
    engine.client = fake_db
    monkeypatch.setenv("WORKFLOW_ENFORCE_READINESS_GATE", "true")

    result = await engine.start_workflow(user_id="u1", template_name="Template A")

    assert result["error_code"] == "workflow_not_ready"
    assert "not ready for execution" in result["error"]


@pytest.mark.asyncio
async def test_start_workflow_blocks_when_readiness_missing_and_gate_enabled(monkeypatch):
    fake_db = _FakeDb(readiness_row=None)
    engine = object.__new__(WorkflowEngine)
    engine.client = fake_db
    monkeypatch.setenv("WORKFLOW_ENFORCE_READINESS_GATE", "true")

    result = await engine.start_workflow(user_id="u1", template_name="Template A")

    assert result["error_code"] == "workflow_readiness_unavailable"
    assert "readiness check failed" in result["error"].lower()


@pytest.mark.asyncio
async def test_start_workflow_allows_ready_when_gate_enabled(monkeypatch):
    fake_db = _FakeDb(
        readiness_row={
            "template_id": "tpl-1",
            "status": "ready",
            "reason_codes": [],
        }
    )
    engine = object.__new__(WorkflowEngine)
    engine.client = fake_db
    monkeypatch.setenv("WORKFLOW_ENFORCE_READINESS_GATE", "true")
    _set_callback_env(monkeypatch)

    execute_workflow_mock = AsyncMock(return_value={"success": True})
    monkeypatch.setattr(
        "app.workflows.engine.edge_function_client.execute_workflow",
        execute_workflow_mock,
    )

    result = await engine.start_workflow(user_id="u1", template_name="Template A")

    assert "error" not in result
    assert result["status"] == "pending"
    assert execute_workflow_mock.call_count == 1


@pytest.mark.asyncio
async def test_start_workflow_blocks_user_visible_start_when_callback_config_missing(monkeypatch):
    fake_db = _FakeDb(
        readiness_row={
            "template_id": "tpl-1",
            "status": "ready",
            "reason_codes": [],
        }
    )
    engine = object.__new__(WorkflowEngine)
    engine.client = fake_db
    monkeypatch.setenv("WORKFLOW_ENFORCE_READINESS_GATE", "true")
    monkeypatch.delenv("BACKEND_API_URL", raising=False)
    monkeypatch.delenv("WORKFLOW_SERVICE_SECRET", raising=False)
    # Default false => strict execution mode in the edge function path.
    monkeypatch.delenv("WORKFLOW_ALLOW_FALLBACK_SIMULATION", raising=False)

    result = await engine.start_workflow(user_id="u1", template_name="Template A", run_source="user_ui")

    assert result["error_code"] == "workflow_execution_infra_not_configured"
    assert "BACKEND_API_URL" in result["missing_config"]
    assert "WORKFLOW_SERVICE_SECRET" in result["missing_config"]
    assert fake_db.execution_inserts == []
