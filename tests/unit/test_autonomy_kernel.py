import pytest

from app.autonomy.kernel import AutonomyKernel, ExecutorCapability


class _StubEngine:
    def __init__(self):
        self.calls = []

    async def start_workflow(self, **kwargs):
        self.calls.append(kwargs)
        return {"execution_id": "exec-1"}


class _StubInitiativeService:
    async def create_initiative(self, **kwargs):
        return {"id": "init-1", **kwargs}

    async def get_initiative(self, initiative_id, user_id=None):
        return {"id": initiative_id, "user_id": user_id}

    async def update_operational_state(self, initiative_id, **kwargs):
        return {"id": initiative_id, **kwargs}


def test_autonomy_kernel_init_is_lazy(monkeypatch):
    monkeypatch.setattr(
        "app.autonomy.kernel.InitiativeService",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("initiative service should be lazy")),
    )
    monkeypatch.setattr(
        "app.autonomy.kernel.get_workflow_engine",
        lambda: (_ for _ in ()).throw(AssertionError("workflow engine should be lazy")),
    )

    kernel = AutonomyKernel()

    assert kernel.planner is not None
    assert kernel.verifier is not None
    assert kernel.recovery is not None


@pytest.mark.asyncio
async def test_executor_capability_resolves_engine_lazily(monkeypatch):
    engine = _StubEngine()
    monkeypatch.setattr("app.autonomy.kernel.get_workflow_engine", lambda: engine)

    executor = ExecutorCapability()
    result = await executor.launch(
        user_id="user-1",
        template_names=["Idea-to-Venture"],
        context={"initiative_id": "init-1"},
    )

    assert result["success"] is True
    assert engine.calls[0]["user_id"] == "user-1"
    assert engine.calls[0]["template_name"] == "Idea-to-Venture"


@pytest.mark.asyncio
async def test_autonomy_kernel_uses_injected_initiative_service(monkeypatch):
    engine = _StubEngine()
    service = _StubInitiativeService()
    monkeypatch.setattr("app.autonomy.kernel.get_workflow_engine", lambda: engine)

    kernel = AutonomyKernel(initiative_service=service)
    result = await kernel.orchestrate_idea_to_venture(
        user_id="user-1",
        idea="Test idea",
        context="Test context",
    )

    assert result["initiative_id"] == "init-1"
    assert result["workflow_execution_id"] == "exec-1"
    assert result["template_name"] == "Idea-to-Venture"
