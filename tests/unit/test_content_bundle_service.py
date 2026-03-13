from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.content_bundle_service import ContentBundleService


class _FakeTable:
    def __init__(self, name: str, calls: list[dict[str, object]]):
        self.name = name
        self.calls = calls
        self.payload = None
        self.on_conflict = None

    def upsert(self, payload, on_conflict=None):
        self.payload = payload
        self.on_conflict = on_conflict
        self.calls.append(
            {
                "table": self.name,
                "payload": payload,
                "on_conflict": on_conflict,
            }
        )
        return self

    def execute(self):
        return SimpleNamespace(data=[self.payload])


class _FakeClient:
    def __init__(self):
        self.calls: list[dict[str, object]] = []

    def table(self, name: str):
        return _FakeTable(name, self.calls)


@pytest.mark.asyncio
async def test_register_media_output_persists_bundle_contract():
    client = _FakeClient()
    service = ContentBundleService(client=client)

    with patch("app.services.content_bundle_service.get_current_session_id", return_value="sess-123"), patch(
        "app.services.content_bundle_service.get_current_workflow_execution_id", return_value="exec-456"
    ):
        contract = await service.register_media_output(
            user_id="user-1",
            asset_id="asset-1",
            asset_type="video",
            title="Campaign Teaser",
            prompt="Create a teaser",
            file_url="https://example.com/video.mp4",
            source="director_service",
            metadata={"scene_count": 4},
        )

    assert contract["bundle_id"]
    assert contract["deliverable_id"]
    assert contract["workspace_item_id"]
    assert contract["session_id"] == "sess-123"
    assert contract["workflow_execution_id"] == "exec-456"

    assert [call["table"] for call in client.calls] == [
        "content_bundles",
        "content_bundle_deliverables",
        "workspace_items",
    ]
    assert client.calls[1]["on_conflict"] == "source_key"
    assert client.calls[2]["payload"]["layout_mode"] == "focus"
    assert client.calls[0]["payload"]["created_by"] == "user-1"
    assert client.calls[1]["payload"]["created_by"] == "user-1"
    assert client.calls[2]["payload"]["created_by"] == "user-1"


def test_attach_widget_contract_preserves_workspace_and_refs():
    service = ContentBundleService(client=None)
    widget = {
        "type": "video",
        "data": {"videoUrl": "https://example.com/video.mp4", "asset_id": "asset-1"},
        "workspace": {"mode": "grid"},
    }

    enriched = service.attach_widget_contract(
        widget,
        contract={
            "bundle_id": "bundle-1",
            "deliverable_id": "deliverable-1",
            "workspace_item_id": "workspace-1",
            "session_id": "sess-123",
            "workflow_execution_id": "exec-456",
            "workspace_mode": "grid",
        },
        extra_data={"platform_profile": "instagram_post"},
    )

    assert enriched["data"]["bundle_id"] == "bundle-1"
    assert enriched["data"]["platform_profile"] == "instagram_post"
    assert enriched["workspace"]["mode"] == "grid"
    assert enriched["workspace"]["workspaceItemId"] == "workspace-1"
