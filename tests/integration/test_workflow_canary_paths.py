"""Integration tests for canary-path execution actions."""

from fastapi.testclient import TestClient

from app import fast_api_app
import app.routers.initiatives as initiatives_router
import app.routers.onboarding as onboarding_router
import app.routers.workflows as workflows_router
import app.agents.strategic.tools as strategic_tools


def _override_user_id() -> str:
    return "00000000-0000-0000-0000-000000000001"


class _StubWorkflowEngine:
    async def start_workflow(self, **_kwargs):
        return {
            "execution_id": "exec-1",
            "status": "pending",
            "current_step": "Phase 1: Step 1",
            "message": "started",
        }

    async def advance_execution(self, **_kwargs):
        return {"status": "advance_triggered", "execution_id": "exec-1"}

    async def approve_step(self, *_args, **_kwargs):
        return {"status": "approved", "message": "continued"}

    async def cancel_execution(self, **_kwargs):
        return {"status": "cancelled", "execution": {"id": "exec-1"}}

    async def retry_step(self, **_kwargs):
        return {"status": "retry_started", "step": {"id": "step-1", "status": "running"}}


class _StubInitiativeServiceMissingInputs:
    async def get_initiative(self, _initiative_id, user_id=None):
        return {"id": "init-1", "metadata": {"journey_id": "journey-1"}}


def test_canary_paths_start_advance_approve_cancel_retry(monkeypatch) -> None:
    monkeypatch.setenv("WORKFLOW_KILL_SWITCH", "false")
    monkeypatch.setenv("WORKFLOW_CANARY_ENABLED", "true")
    monkeypatch.setenv("WORKFLOW_CANARY_USER_IDS", "00000000-0000-0000-0000-000000000001")
    monkeypatch.setattr(workflows_router, "get_workflow_engine", lambda: _StubWorkflowEngine())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            start_resp = client.post("/workflows/start", json={"template_name": "Any Template"})
            assert start_resp.status_code == 200
            assert start_resp.json()["execution_id"] == "exec-1"

            advance_resp = client.post("/workflows/executions/exec-1/advance")
            assert advance_resp.status_code == 200
            assert advance_resp.json()["status"] == "advance_triggered"

            approve_resp = client.post("/workflows/executions/exec-1/approve", json={"feedback": "ok"})
            assert approve_resp.status_code == 200
            assert approve_resp.json()["status"] == "success"

            cancel_resp = client.post("/workflows/executions/exec-1/cancel", json={"reason": "user requested"})
            assert cancel_resp.status_code == 200
            assert cancel_resp.json()["status"] == "cancelled"

            retry_resp = client.post("/workflows/executions/exec-1/retry-step", json={"step_id": "step-1"})
            assert retry_resp.status_code == 200
            assert retry_resp.json()["status"] == "retry_started"
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_canary_paths_journey_start_returns_422_for_missing_inputs(monkeypatch) -> None:
    async def _fake_start_journey_workflow(_initiative_id: str):
        return {
            "success": False,
            "requirements_satisfied": False,
            "missing_inputs": ["desired_outcomes", "timeline"],
            "error": "Journey workflow requirements are not satisfied.",
        }

    monkeypatch.setattr(initiatives_router, "InitiativeService", lambda: _StubInitiativeServiceMissingInputs())
    monkeypatch.setattr(strategic_tools, "start_journey_workflow", _fake_start_journey_workflow)
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post("/initiatives/init-1/start-journey-workflow")
        assert response.status_code == 422
        payload = response.json()
        assert payload["message"] == "Journey workflow requirements are not satisfied"
        assert payload["details"]["requirements_satisfied"] is False
        assert payload["details"]["missing_inputs"] == ["desired_outcomes", "timeline"]
    finally:
        fast_api_app.app.dependency_overrides.clear()
