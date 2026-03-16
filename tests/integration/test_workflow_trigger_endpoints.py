from fastapi.testclient import TestClient

from app import fast_api_app
import app.routers.onboarding as onboarding_router
import app.routers.workflow_triggers as workflow_triggers_router


def _override_user_id() -> str:
    return "00000000-0000-0000-0000-000000000001"


class _StubWorkflowTriggerService:
    async def list_triggers(self, user_id: str, template_id=None, enabled=None):
        assert user_id == _override_user_id()
        return [
            {
                "id": "trg-1",
                "template_id": template_id or "tpl-1",
                "trigger_type": "schedule",
                "enabled": True if enabled is None else enabled,
            }
        ]

    async def create_trigger(self, **kwargs):
        return {"status": "success", "trigger": {"id": "trg-created", **kwargs, "trigger_type": kwargs["trigger_type"].value}}

    async def update_trigger(self, trigger_id: str, user_id: str, updates: dict):
        return {"status": "success", "trigger": {"id": trigger_id, "user_id": user_id, **updates}}

    async def delete_trigger(self, trigger_id: str, user_id: str):
        return {"status": "success", "trigger": {"id": trigger_id, "user_id": user_id}}

    async def dispatch_event(self, user_id: str, event_name: str, payload: dict, source: str):
        return {
            "status": "queued",
            "matched_trigger_count": 1,
            "event": {"id": "evt-1", "user_id": user_id, "event_name": event_name, "payload": payload, "source": source},
            "job_results": [{"status": "queued", "trigger_id": "trg-1"}],
        }


def test_workflow_trigger_list_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(workflow_triggers_router, "get_workflow_trigger_service", lambda: _StubWorkflowTriggerService())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.get("/workflow-triggers")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "success"
        assert payload["count"] == 1
        assert payload["triggers"][0]["id"] == "trg-1"
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_workflow_trigger_create_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(workflow_triggers_router, "get_workflow_trigger_service", lambda: _StubWorkflowTriggerService())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post(
                "/workflow-triggers",
                json={
                    "template_id": "tpl-1",
                    "trigger_name": "Daily founder standup",
                    "trigger_type": "schedule",
                    "schedule_frequency": "daily",
                    "context": {"department": "ops"},
                },
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "success"
        assert payload["trigger"]["id"] == "trg-created"
        assert payload["trigger"]["trigger_type"] == "schedule"
        assert payload["trigger"]["user_id"] == _override_user_id()
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_workflow_trigger_dispatch_event_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(workflow_triggers_router, "get_workflow_trigger_service", lambda: _StubWorkflowTriggerService())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.post(
                "/workflow-triggers/events/dispatch",
                json={"event_name": "workflow.started", "payload": {"execution_id": "exec-1"}, "source": "workflow_hook"},
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "queued"
        assert payload["matched_trigger_count"] == 1
        assert payload["event"]["event_name"] == "workflow.started"
    finally:
        fast_api_app.app.dependency_overrides.clear()


