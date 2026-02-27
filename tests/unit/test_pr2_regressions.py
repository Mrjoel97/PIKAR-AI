"""Regression tests for PR-2 fixes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents.tools import deep_research as deep_research_module
from app.workflows.engine import WorkflowEngine


@pytest.mark.asyncio
async def test_deep_research_awaits_vault_ingest(monkeypatch):
    """Ensure vault ingestion is awaited (not fire-and-forget)."""
    tool = object.__new__(deep_research_module.DeepResearchTool)
    tool.search_tool = SimpleNamespace(
        search=AsyncMock(
            return_value={
                "answer": "summary",
                "results": [
                    {
                        "title": "Source",
                        "url": "https://example.com/a",
                        "content": "Useful market data. More details follow.",
                    }
                ],
            }
        )
    )
    tool.scrape_tool = SimpleNamespace(
        scrape=AsyncMock(
            return_value={
                "success": True,
                "markdown": "Detailed markdown content " * 30,
                "metadata": {"title": "Example"},
            }
        )
    )

    ingest_mock = AsyncMock(return_value={"success": True})
    monkeypatch.setattr(deep_research_module, "ingest_document_content", ingest_mock)

    result = await tool.research(
        topic="AI copilots for SMBs",
        research_type="market",
        num_sources=1,
        scrape_top_n=1,
        user_id="user-123",
        save_to_vault=True,
    )

    assert result["success"] is True
    assert result["saved_to_vault"] is True
    assert ingest_mock.await_count == 1


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, name: str, db: "_FakeDb"):
        self._name = name
        self._db = db
        self._insert_payload = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
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
            return _FakeResponse(
                [
                    {
                        "id": "tpl-1",
                        "name": "Template A",
                        "version": 1,
                        "lifecycle_status": "published",
                        "phases": [{"name": "Phase 1", "steps": [{"name": "Step 1"}]}],
                    }
                ]
            )
        if self._name == "workflow_readiness":
            return _FakeResponse(
                [
                    {
                        "template_id": "tpl-1",
                        "status": "ready",
                        "reason_codes": [],
                    }
                ]
            )
        if self._name == "workflow_executions":
            self._db.execution_inserts.append(self._insert_payload)
            execution_id = f"exec-{len(self._db.execution_inserts)}"
            return _FakeResponse([{"id": execution_id}])
        if self._name == "workflow_steps":
            self._db.step_inserts.append(self._insert_payload)
            return _FakeResponse([{"id": "step-1"}])
        return _FakeResponse([])


class _FakeDb:
    def __init__(self):
        self.execution_inserts = []
        self.step_inserts = []

    def table(self, name: str):
        return _FakeTable(name, self)


@pytest.mark.asyncio
async def test_workflow_start_default_context_is_fresh_per_call(monkeypatch):
    """Calling start_workflow without context should not leak state across calls."""
    fake_db = _FakeDb()
    engine = object.__new__(WorkflowEngine)
    engine.client = fake_db

    # Avoid scheduling real edge function calls during test.
    execute_workflow_mock = AsyncMock(return_value={"success": True})
    monkeypatch.setattr(
        "app.workflows.engine.edge_function_client.execute_workflow",
        execute_workflow_mock,
    )
    monkeypatch.setenv("BACKEND_API_URL", "http://localhost:8000")
    monkeypatch.setenv("WORKFLOW_SERVICE_SECRET", "x" * 40)

    await engine.start_workflow(user_id="u1", template_name="Template A")
    # Mutate first call context to simulate accidental shared-state leakage.
    fake_db.execution_inserts[0]["context"]["leak"] = True

    await engine.start_workflow(user_id="u1", template_name="Template A")

    second_execution_context = fake_db.execution_inserts[1]["context"]
    assert "leak" not in second_execution_context
    assert len(fake_db.step_inserts) == 0
    assert fake_db.execution_inserts[0]["status"] == "pending"
    assert fake_db.execution_inserts[1]["status"] == "pending"
    assert execute_workflow_mock.call_count == 2
