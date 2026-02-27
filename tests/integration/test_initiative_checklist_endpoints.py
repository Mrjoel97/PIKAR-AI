"""Integration tests for initiative checklist endpoints."""

from fastapi.testclient import TestClient

from app import fast_api_app
import app.routers.onboarding as onboarding_router
import app.routers.initiatives as initiatives_router


def _override_user_id() -> str:
    return "00000000-0000-0000-0000-000000000001"


class _StubInitiativeService:
    def __init__(self):
        self.last_items_kwargs = {}
        self.last_events_kwargs = {}

    async def list_checklist_items(self, **_kwargs):
        self.last_items_kwargs = _kwargs
        return [
            {
                "id": "item-1",
                "initiative_id": "init-1",
                "phase": "ideation",
                "title": "Define problem statement",
                "status": "pending",
            }
        ]

    async def create_checklist_item(self, **kwargs):
        return {
            "id": "item-created",
            "initiative_id": kwargs["initiative_id"],
            "phase": kwargs["phase"],
            "title": kwargs["title"],
            "status": kwargs.get("status", "pending"),
        }

    async def update_checklist_item(self, **kwargs):
        return {
            "id": kwargs["item_id"],
            "initiative_id": kwargs["initiative_id"],
            "phase": "ideation",
            "title": kwargs.get("title") or "Updated title",
            "status": kwargs.get("status") or "pending",
        }

    async def delete_checklist_item(self, **_kwargs):
        return True

    async def list_checklist_events(self, **_kwargs):
        self.last_events_kwargs = _kwargs
        return [{"id": "evt-1", "event_type": "created"}]


def test_list_checklist_items(monkeypatch) -> None:
    monkeypatch.setattr(initiatives_router, "InitiativeService", lambda: _StubInitiativeService())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.get("/initiatives/init-1/checklist")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["items"][0]["id"] == "item-1"
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_create_and_update_checklist_item(monkeypatch) -> None:
    monkeypatch.setattr(initiatives_router, "InitiativeService", lambda: _StubInitiativeService())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            create_resp = client.post(
                "/initiatives/init-1/checklist",
                json={"title": "Collect interviews", "phase": "ideation"},
            )
            update_resp = client.patch(
                "/initiatives/init-1/checklist/item-1",
                json={"status": "completed", "title": "Collect 10 interviews"},
            )
        assert create_resp.status_code == 200
        assert create_resp.json()["item"]["id"] == "item-created"
        assert update_resp.status_code == 200
        assert update_resp.json()["item"]["id"] == "item-1"
        assert update_resp.json()["item"]["status"] == "completed"
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_delete_and_list_events(monkeypatch) -> None:
    monkeypatch.setattr(initiatives_router, "InitiativeService", lambda: _StubInitiativeService())
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            delete_resp = client.delete("/initiatives/init-1/checklist/item-1")
            events_resp = client.get("/initiatives/init-1/checklist/events")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["success"] is True
        assert events_resp.status_code == 200
        assert events_resp.json()["count"] == 1
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_list_checklist_items_with_filters_and_pagination(monkeypatch) -> None:
    stub = _StubInitiativeService()
    monkeypatch.setattr(initiatives_router, "InitiativeService", lambda: stub)
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.get(
                "/initiatives/init-1/checklist?phase=ideation&status=pending&owner_label=alex"
                "&limit=20&offset=10&sort_by=updated_at&sort_order=desc"
            )
        assert response.status_code == 200
        assert stub.last_items_kwargs["phase"] == "ideation"
        assert stub.last_items_kwargs["status"] == "pending"
        assert stub.last_items_kwargs["owner_label"] == "alex"
        assert stub.last_items_kwargs["limit"] == 20
        assert stub.last_items_kwargs["offset"] == 10
        assert stub.last_items_kwargs["sort_by"] == "updated_at"
        assert stub.last_items_kwargs["sort_order"] == "desc"
    finally:
        fast_api_app.app.dependency_overrides.clear()


def test_list_checklist_events_with_filters_and_pagination(monkeypatch) -> None:
    stub = _StubInitiativeService()
    monkeypatch.setattr(initiatives_router, "InitiativeService", lambda: stub)
    fast_api_app.app.dependency_overrides[onboarding_router.get_current_user_id] = _override_user_id
    try:
        with TestClient(fast_api_app.app) as client:
            response = client.get(
                "/initiatives/init-1/checklist/events?limit=10&offset=5&event_type=updated&item_id=item-1"
                "&actor_user_id=00000000-0000-0000-0000-000000000099"
            )
        assert response.status_code == 200
        assert stub.last_events_kwargs["limit"] == 10
        assert stub.last_events_kwargs["offset"] == 5
        assert stub.last_events_kwargs["event_type"] == "updated"
        assert stub.last_events_kwargs["item_id"] == "item-1"
        assert stub.last_events_kwargs["actor_user_id"] == "00000000-0000-0000-0000-000000000099"
    finally:
        fast_api_app.app.dependency_overrides.clear()
