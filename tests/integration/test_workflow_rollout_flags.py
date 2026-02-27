"""Integration tests for workflow rollout controls (canary + kill switch)."""

from fastapi.testclient import TestClient

from app import fast_api_app
import app.routers.onboarding as onboarding_router
import app.routers.workflows as workflows_router


class _StubEngine:
    async def start_workflow(self, **_kwargs):
        return {
            "execution_id": "exec-1",
            "status": "pending",
            "current_step": "Phase 1: Step 1",
            "message": "ok",
        }


def _override_user_id() -> str:
    return "00000000-0000-0000-0000-000000000001"


def test_start_workflow_blocked_by_kill_switch(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_KILL_SWITCH", "true")
    monkeypatch.delenv("WORKFLOW_CANARY_ENABLED", raising=False)
    monkeypatch.setattr(workflows_router, "get_workflow_engine", lambda: _StubEngine())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/workflows/start", json={"template_name": "Any Template", "topic": ""})
        assert response.status_code == 503
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_start_workflow_blocked_for_non_canary_user(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_KILL_SWITCH", "false")
    monkeypatch.setenv("WORKFLOW_CANARY_ENABLED", "true")
    monkeypatch.setenv("WORKFLOW_CANARY_USER_IDS", "00000000-0000-0000-0000-000000000002")
    monkeypatch.setattr(workflows_router, "get_workflow_engine", lambda: _StubEngine())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/workflows/start", json={"template_name": "Any Template", "topic": ""})
        assert response.status_code == 403
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_start_workflow_allowed_for_canary_user(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_KILL_SWITCH", "false")
    monkeypatch.setenv("WORKFLOW_CANARY_ENABLED", "true")
    monkeypatch.setenv("WORKFLOW_CANARY_USER_IDS", "00000000-0000-0000-0000-000000000001")
    monkeypatch.setattr(workflows_router, "get_workflow_engine", lambda: _StubEngine())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/workflows/start", json={"template_name": "Any Template", "topic": ""})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["execution_id"] == "exec-1"
    finally:
        fast_api_app.app.dependency_overrides.clear()
