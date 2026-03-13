import os
import sys
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("LOCAL_DEV_BYPASS", "1")
os.environ.setdefault("SKIP_ENV_VALIDATION", "1")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key")

stub_tool_registry = types.ModuleType("app.agents.tools.registry")


async def _stub_create_task(**_kwargs):
    return {"success": True}


class _StubSchema:
    model_fields = {"description": object()}


_stub_create_task.input_schema = _StubSchema
stub_tool_registry.TOOL_REGISTRY = {"create_task": _stub_create_task}
stub_tool_registry.placeholder_tool = _stub_create_task
sys.modules.setdefault("app.agents.tools.registry", stub_tool_registry)

import app.routers.briefing as briefing_router
import app.routers.initiatives as initiatives_router
import app.routers.onboarding as onboarding_router
import app.routers.workflows as workflows_router


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(workflows_router.router)
    app.include_router(initiatives_router.router)
    app.include_router(briefing_router.router)
    return app


class _StubWorkflowEngine:
    def __init__(self):
        self.calls = []

    async def list_templates(self, *, category=None, lifecycle_status=None, persona=None):
        self.calls.append(
            {
                "category": category,
                "lifecycle_status": lifecycle_status,
                "persona": persona,
            }
        )
        return []


class _StubInitiativeService:
    def __init__(self):
        self.calls = []

    async def list_templates(self, persona=None, category=None):
        self.calls.append({"persona": persona, "category": category})
        return []



def test_workflow_templates_route_uses_request_persona_header(monkeypatch) -> None:
    stub_engine = _StubWorkflowEngine()
    monkeypatch.setattr(workflows_router, "get_workflow_engine", lambda: stub_engine)

    with TestClient(_build_test_app()) as client:
        response = client.get("/workflows/templates", headers={"x-pikar-persona": "startup"})

    assert response.status_code == 200
    assert stub_engine.calls == [
        {
            "category": None,
            "lifecycle_status": None,
            "persona": "startup",
        }
    ]



def test_workflow_templates_route_allows_explicit_persona_override(monkeypatch) -> None:
    stub_engine = _StubWorkflowEngine()
    monkeypatch.setattr(workflows_router, "get_workflow_engine", lambda: stub_engine)

    with TestClient(_build_test_app()) as client:
        response = client.get(
            "/workflows/templates?persona=enterprise",
            headers={"x-pikar-persona": "startup"},
        )

    assert response.status_code == 200
    assert stub_engine.calls[-1]["persona"] == "enterprise"



def test_initiative_templates_route_uses_request_persona_header(monkeypatch) -> None:
    stub_service = _StubInitiativeService()
    monkeypatch.setattr(initiatives_router, "InitiativeService", lambda: stub_service)

    with TestClient(_build_test_app()) as client:
        response = client.get("/initiatives/templates", headers={"x-pikar-persona": "sme"})

    assert response.status_code == 200
    assert stub_service.calls == [{"persona": "sme", "category": None}]


class _StubDashboardSummaryService:
    def __init__(self):
        self.calls = []

    async def get_home_summary(self, *, user_id: str, persona: str | None):
        self.calls.append({"user_id": user_id, "persona": persona})
        return {
            "persona": persona,
            "headline": "stub",
            "kpis": [],
            "collections": {},
            "recommended_action": {"title": "stub", "description": "stub", "href": "/dashboard"},
        }


def test_dashboard_summary_route_uses_request_persona_header(monkeypatch) -> None:
    stub_service = _StubDashboardSummaryService()
    monkeypatch.setattr(briefing_router, "get_dashboard_summary_service", lambda: stub_service)

    app = _build_test_app()
    app.dependency_overrides[onboarding_router.get_current_user_id] = lambda: "user-123"
    try:
        with TestClient(app) as client:
            response = client.get("/briefing/dashboard-summary", headers={"x-pikar-persona": "enterprise"})

        assert response.status_code == 200
        assert response.json()["persona"] == "enterprise"
        assert stub_service.calls == [{"user_id": "user-123", "persona": "enterprise"}]
    finally:
        app.dependency_overrides.clear()