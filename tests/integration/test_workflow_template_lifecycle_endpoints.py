"""Integration tests for workflow template create/edit/publish lifecycle endpoints."""

from fastapi.testclient import TestClient

from app import fast_api_app
import app.routers.onboarding as onboarding_router
import app.routers.workflows as workflows_router


def _override_user_id() -> str:
    return "00000000-0000-0000-0000-000000000001"


class _StubWorkflowEngine:
    async def create_template(self, **kwargs):
        return {
            "id": "tpl-1",
            "name": kwargs["name"],
            "description": kwargs.get("description", ""),
            "category": kwargs["category"],
            "phases": kwargs["phases"],
            "lifecycle_status": "draft",
            "version": 1,
        }

    async def update_template_draft(self, **kwargs):
        updates = kwargs["updates"]
        if not updates:
            return {"error": "No updates provided"}
        return {
            "id": kwargs["template_id"],
            "name": updates.get("name", "Draft Name"),
            "description": updates.get("description", ""),
            "category": updates.get("category", "custom"),
            "phases": updates.get("phases", []),
            "lifecycle_status": "draft",
            "version": 1,
        }

    async def publish_template(self, **kwargs):
        return {
            "template_id": kwargs["template_id"],
            "status": "published",
            "version": 2,
        }

    async def diff_template(self, **kwargs):
        return {
            "template_id": kwargs["template_id"],
            "against": kwargs.get("against", "published"),
            "has_changes": True,
            "changes": [{"path": "phases[0].steps[0].name", "type": "modified"}],
        }


def test_template_lifecycle_create_update_publish_diff(monkeypatch) -> None:
    monkeypatch.setattr(workflows_router, "get_workflow_engine", lambda: _StubWorkflowEngine())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            create_resp = client.post(
                "/workflows/templates",
                json={
                    "name": "Lifecycle Draft",
                    "description": "Draft from integration test",
                    "category": "custom",
                    "phases": [{"name": "Phase 1", "steps": [{"name": "Step 1", "tool": "create_task"}]}],
                    "is_generated": False,
                },
            )
            assert create_resp.status_code == 200
            assert create_resp.json()["lifecycle_status"] == "draft"
            assert create_resp.json()["id"] == "tpl-1"

            update_resp = client.patch(
                "/workflows/templates/tpl-1",
                json={
                    "name": "Lifecycle Draft Updated",
                    "description": "Updated",
                },
            )
            assert update_resp.status_code == 200
            assert update_resp.json()["name"] == "Lifecycle Draft Updated"
            assert update_resp.json()["lifecycle_status"] == "draft"

            publish_resp = client.post("/workflows/templates/tpl-1/publish", json={})
            assert publish_resp.status_code == 200
            assert publish_resp.json()["status"] == "published"
            assert publish_resp.json()["version"] == 2

            diff_resp = client.get("/workflows/templates/tpl-1/diff?against=published")
            assert diff_resp.status_code == 200
            assert diff_resp.json()["has_changes"] is True
            assert diff_resp.json()["against"] == "published"
    finally:
        fast_api_app.app.dependency_overrides.clear()
