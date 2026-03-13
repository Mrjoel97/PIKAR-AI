import pytest

from app.agents.tools import workflows


class _StubEngine:
    def __init__(self):
        self.calls = []

    async def start_workflow(self, **kwargs):
        self.calls.append(kwargs)
        return {"execution_id": "exec-1", "status": "pending"}


@pytest.mark.asyncio
async def test_start_workflow_uses_authenticated_user_context(monkeypatch):
    engine = _StubEngine()
    monkeypatch.setattr("app.services.request_context.get_current_user_id", lambda: "user-123")
    monkeypatch.setattr("app.workflows.engine.get_workflow_engine", lambda: engine)

    result = await workflows.start_workflow(
        template_name="Landing Page to Launch",
        topic="New product launch",
        context={"initiative_id": "init-1"},
    )

    assert result["execution_id"] == "exec-1"
    assert len(engine.calls) == 1
    assert engine.calls[0]["user_id"] == "user-123"
    assert engine.calls[0]["template_name"] == "Landing Page to Launch"
    assert engine.calls[0]["run_source"] == "agent_ui"
    assert engine.calls[0]["context"] == {
        "initiative_id": "init-1",
        "topic": "New product launch",
    }


@pytest.mark.asyncio
async def test_start_workflow_requires_authenticated_user_context(monkeypatch):
    monkeypatch.setattr("app.services.request_context.get_current_user_id", lambda: None)

    result = await workflows.start_workflow(template_name="Idea-to-Venture")

    assert result == {"error": "Missing user context for workflow execution"}
