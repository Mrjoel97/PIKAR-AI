from fastapi.testclient import TestClient

from app import fast_api_app
import app.routers.onboarding as onboarding_router
import app.routers.workflows as workflows_router


def _override_user_id() -> str:
    return "00000000-0000-0000-0000-000000000001"


class _StubWorkflowEngine:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def list_executions(self, *, user_id: str, status=None, status_filters=None, limit: int = 20, offset: int = 0):
        self.calls.append(
            {
                "user_id": user_id,
                "status": status,
                "status_filters": status_filters,
                "limit": limit,
                "offset": offset,
            }
        )
        return [{"id": "exec-1", "user_id": user_id, "status": "running"}]


def test_workflow_execution_list_endpoint_supports_multi_status_filters(monkeypatch) -> None:
    engine = _StubWorkflowEngine()
    monkeypatch.setattr(workflows_router, "get_workflow_engine", lambda: engine)
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.get("/workflows/executions?statuses=running,waiting_approval,pending&limit=60&offset=5")
        assert response.status_code == 200
        assert response.json()[0]["id"] == "exec-1"
        assert engine.calls == [
            {
                "user_id": _override_user_id(),
                "status": None,
                "status_filters": ["running", "waiting_approval", "pending"],
                "limit": 60,
                "offset": 5,
            }
        ]
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_workflow_execution_list_endpoint_preserves_single_status_behavior(monkeypatch) -> None:
    engine = _StubWorkflowEngine()
    monkeypatch.setattr(workflows_router, "get_workflow_engine", lambda: engine)
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.get("/workflows/executions?status=completed")
        assert response.status_code == 200
        assert engine.calls == [
            {
                "user_id": _override_user_id(),
                "status": "completed",
                "status_filters": ["completed"],
                "limit": 20,
                "offset": 0,
            }
        ]
    finally:
        fast_api_app.app.dependency_overrides.clear()
