from unittest.mock import AsyncMock

import pytest

from app.autonomy.agent_kernel import AgentKernel, WorkflowMissionHookAdapter


class _StubEngine:
    def __init__(self):
        self.calls = []

    async def start_workflow(self, **kwargs):
        self.calls.append(kwargs)
        return {"execution_id": "exec-1", "status": "pending"}


class _FlagHook(WorkflowMissionHookAdapter):
    async def after_start(self, request, result):
        updated = dict(result)
        updated["hooked_template"] = request.template_name
        return updated


class _StubTriggerService:
    def __init__(self):
        self.dispatch_event = AsyncMock(return_value={"status": "queued"})


@pytest.mark.asyncio
async def test_agent_kernel_injects_metadata_and_mission(monkeypatch):
    engine = _StubEngine()
    trigger_service = _StubTriggerService()
    monkeypatch.setattr(
        "app.services.workflow_trigger_service.get_workflow_trigger_service",
        lambda: trigger_service,
    )
    kernel = AgentKernel(workflow_engine=engine)

    result = await kernel.start_workflow_mission(
        user_id="user-1",
        template_name="Idea-to-Venture",
        context={"initiative_id": "init-1"},
        run_source="agent_ui",
        persona="startup",
        session_id="session-1",
        parent_run_id="parent-1",
        queue_mode="parallel",
        lane="department",
    )

    assert len(engine.calls) == 1
    call = engine.calls[0]
    assert call["user_id"] == "user-1"
    assert call["template_name"] == "Idea-to-Venture"
    assert call["run_source"] == "agent_ui"
    assert call["persona"] == "startup"
    assert call["context"]["initiative_id"] == "init-1"
    assert call["context"]["_agent_kernel"] == {
        "lane": "department",
        "queue_mode": "parallel",
        "session_id": "session-1",
        "parent_run_id": "parent-1",
        "persona": "startup",
        "template_name": "Idea-to-Venture",
    }

    assert result["mission"]["kind"] == "workflow"
    assert result["mission"]["mission_id"] == "exec-1"
    assert result["mission"]["session_id"] == "session-1"
    assert result["mission"]["parent_run_id"] == "parent-1"
    assert result["mission"]["queue_mode"] == "parallel"
    assert result["mission"]["lane"] == "department"
    assert result["mission"]["template_name"] == "Idea-to-Venture"

    trigger_service.dispatch_event.assert_awaited_once()
    dispatch_kwargs = trigger_service.dispatch_event.await_args.kwargs
    assert dispatch_kwargs["user_id"] == "user-1"
    assert dispatch_kwargs["event_name"] == "workflow.started"
    assert dispatch_kwargs["payload"]["execution_id"] == "exec-1"
    assert dispatch_kwargs["payload"]["template_name"] == "Idea-to-Venture"


@pytest.mark.asyncio
async def test_agent_kernel_supports_custom_hooks():
    engine = _StubEngine()
    kernel = AgentKernel(workflow_engine=engine, workflow_hooks=[_FlagHook()])

    result = await kernel.start_workflow_mission(
        user_id="user-2",
        template_name="Launch Plan",
        context={"initiative_id": "init-2"},
    )

    assert result["hooked_template"] == "Launch Plan"
    assert engine.calls[0]["context"] == {"initiative_id": "init-2"}


@pytest.mark.asyncio
async def test_agent_kernel_skips_lifecycle_dispatch_for_trigger_context(monkeypatch):
    engine = _StubEngine()
    trigger_service = _StubTriggerService()
    monkeypatch.setattr(
        "app.services.workflow_trigger_service.get_workflow_trigger_service",
        lambda: trigger_service,
    )
    kernel = AgentKernel(workflow_engine=engine)

    await kernel.start_workflow_mission(
        user_id="user-3",
        template_id="tpl-1",
        context={"trigger": {"id": "trg-1", "type": "event"}},
        run_source="agent_ui",
    )

    trigger_service.dispatch_event.assert_not_awaited()
