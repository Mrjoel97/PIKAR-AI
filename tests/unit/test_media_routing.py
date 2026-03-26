from unittest.mock import AsyncMock, patch

import pytest

from app.agents.tools import media


def test_should_use_director_pipeline_by_duration():
    assert not media._should_use_director_pipeline("simple prompt", media.VEO_MAX_DURATION_SECONDS)
    assert media._should_use_director_pipeline("simple prompt", media.VEO_MAX_DURATION_SECONDS + 1)


def test_should_not_use_director_pipeline_for_short_clips_even_if_prompt_is_narrative():
    assert not media._should_use_director_pipeline("make a cinematic story with transitions", media.VEO_MAX_DURATION_SECONDS)


@pytest.mark.asyncio
async def test_generate_video_routes_to_director_for_long_requests():
    with patch("app.agents.tools.media.create_pro_video", AsyncMock(return_value={"type": "video"})) as pro_mock:
        result = await media.generate_video(prompt="long-form brand story", duration_seconds=60, user_id="u1")

    assert result["type"] == "video"
    pro_mock.assert_awaited_once_with(prompt="long-form brand story", user_id="u1", duration_seconds=60)


@pytest.mark.asyncio
async def test_create_pro_video_returns_progress_and_contract_in_widget():
    director_mock = AsyncMock(
        return_value={
            "asset_id": "asset-123",
            "video_url": "https://example.com/final.mp4",
            "storyboard_captions": ["Hook", "CTA"],
        }
    )
    director_instance = type("Director", (), {"create_pro_video": director_mock})()
    bundle_mock = AsyncMock(
        return_value={
            "bundle_id": "bundle-123",
            "deliverable_id": "deliverable-123",
            "workspace_item_id": "workspace-123",
            "session_id": "sess-123",
            "workflow_execution_id": "exec-123",
            "workspace_mode": "focus",
        }
    )
    bundle_service = type("BundleService", (), {"register_media_output": bundle_mock})()

    with patch("app.services.director_service.DirectorService", return_value=director_instance), patch(
        "app.services.content_bundle_service.ContentBundleService", return_value=bundle_service
    ), patch("app.services.request_context.get_current_user_id", return_value="u1"), patch(
        "app.services.request_context.get_current_session_id", return_value="sess-123"
    ), patch("app.services.request_context.get_current_workflow_execution_id", return_value="exec-123"):
        result = await media.create_pro_video(prompt="ad prompt", user_id="u1", duration_seconds=90)

    assert result["type"] == "video"
    assert result["data"]["videoUrl"] == "https://example.com/final.mp4"
    assert result["data"]["asset_id"] == "asset-123"
    assert result["data"]["durationSeconds"] == 90
    assert result["data"]["bundle_id"] == "bundle-123"
    assert result["workspace"]["mode"] == "focus"
    assert result["workspace"]["workflowExecutionId"] == "exec-123"
    assert "progress" in result["data"]
    director_mock.assert_awaited_once()
    assert director_mock.await_args.kwargs["return_metadata"] is True
    assert director_mock.await_args.kwargs["target_duration_seconds"] == 90


@pytest.mark.asyncio
async def test_save_and_return_video_widget_falls_back_to_vertex_url_when_storage_fails():
    upload_mock = __import__("unittest.mock").mock.Mock(side_effect=RuntimeError("upload failed"))
    storage_bucket = __import__("unittest.mock").mock.Mock(upload=upload_mock)
    supabase = __import__("unittest.mock").mock.Mock()
    supabase.storage.from_.return_value = storage_bucket

    contract_mock = AsyncMock(
        return_value={
            "workspace_mode": "focus",
            "session_id": "sess-123",
            "workflow_execution_id": "exec-123",
        }
    )

    with patch("app.agents.tools.media._register_media_contract", contract_mock), patch(
        "app.services.request_context.get_current_session_id", return_value="sess-123"
    ), patch("app.services.request_context.get_current_workflow_execution_id", return_value="exec-123"):
        result = await media._save_and_return_video_widget(
            supabase,
            "u1",
            "asset-123",
            b"video-bytes",
            "launch teaser",
            6,
            "vertex veo",
            fallback_video_url="https://example.com/video.mp4",
            model_used="veo-3.1-fast-generate-001",
        )

    assert result["type"] == "video"
    assert result["data"]["videoUrl"] == "https://example.com/video.mp4"
    assert result["workspace"]["mode"] == "focus"
    assert upload_mock.call_count == 3
