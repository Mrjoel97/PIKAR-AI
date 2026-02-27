from unittest.mock import AsyncMock, patch

import pytest

from app.agents.tools import media


def test_should_use_director_pipeline_by_duration():
    pytest.skip("Director pipeline auto-routing is temporarily disabled for performance")
    assert media._should_use_director_pipeline("simple prompt", media.DIRECTOR_MIN_DURATION_SECONDS)


def test_should_use_director_pipeline_by_narrative_prompt():
    pytest.skip("Director pipeline auto-routing is temporarily disabled for performance")
    assert media._should_use_director_pipeline("make a cinematic story with transitions", 30)


@pytest.mark.asyncio
async def test_generate_video_routes_to_director_for_long_requests():
    pytest.skip("Director pipeline auto-routing is temporarily disabled for performance")
    with patch("app.agents.tools.media.create_pro_video", AsyncMock(return_value={"type": "video"})) as pro_mock:
        result = await media.generate_video(prompt="long-form brand story", duration_seconds=60, user_id="u1")

    assert result["type"] == "video"
    pro_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_pro_video_returns_progress_in_widget():
    director_mock = AsyncMock(return_value="https://example.com/final.mp4")
    director_instance = type("Director", (), {"create_pro_video": director_mock})()

    with patch("app.services.director_service.DirectorService", return_value=director_instance), patch(
        "app.services.request_context.get_current_user_id", return_value="u1"
    ):
        result = await media.create_pro_video(prompt="ad prompt", user_id="u1")

    assert result["type"] == "video"
    assert result["data"]["videoUrl"] == "https://example.com/final.mp4"
    assert "progress" in result["data"]
