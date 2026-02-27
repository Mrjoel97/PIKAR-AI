from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.director_service import DirectorService


class _StorageBucketStub:
    def upload(self, *args, **kwargs):
        return {"ok": True}

    def get_public_url(self, path: str):
        return f"https://example.com/{path}"


class _StorageStub:
    def from_(self, _bucket: str):
        return _StorageBucketStub()


class _SupabaseStub:
    storage = _StorageStub()


@pytest.mark.asyncio
async def test_pro_video_pipeline_happy_path():
    with patch("app.services.director_service.get_service_client", return_value=_SupabaseStub()), patch(
        "app.services.director_service.genai.Client", return_value=MagicMock(), create=True
    ):
        director = DirectorService()

    with patch.object(
        director,
        "_generate_storyboard",
        AsyncMock(return_value={"mood": "upbeat", "scenes": [{"description": "scene", "text": "hello", "duration": 4}]}),
    ), patch.object(
        director,
        "_process_scene",
        AsyncMock(return_value={"index": 0, "duration": 4, "text": "hello", "video_url": "https://example.com/s.mp4"}),
    ), patch(
        "app.services.director_service.remotion_render_service.render_programmatic_video",
        return_value=(b"bytes", "asset-id"),
    ):
        url = await director.create_pro_video("prompt", "user-1")

    assert url == "https://example.com/user-1/asset-id.mp4"


@pytest.mark.asyncio
async def test_pro_video_pipeline_partial_scene_failure_still_renders():
    with patch("app.services.director_service.get_service_client", return_value=_SupabaseStub()), patch(
        "app.services.director_service.genai.Client", return_value=MagicMock(), create=True
    ):
        director = DirectorService()

    with patch.object(
        director,
        "_generate_storyboard",
        AsyncMock(
            return_value={
                "mood": "upbeat",
                "scenes": [
                    {"description": "scene-a", "text": "a", "duration": 4},
                    {"description": "scene-b", "text": "b", "duration": 4},
                ],
            }
        ),
    ), patch.object(
        director,
        "_process_scene",
        AsyncMock(
            side_effect=[
                {"index": 0, "duration": 4, "text": "a", "video_url": "https://example.com/a.mp4"},
                None,
            ]
        ),
    ), patch(
        "app.services.director_service.remotion_render_service.render_programmatic_video",
        return_value=(b"bytes", "asset-id"),
    ):
        url = await director.create_pro_video("prompt", "user-1")

    assert url == "https://example.com/user-1/asset-id.mp4"

