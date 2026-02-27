from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.mcp.tools.canva_media import execute_content_pipeline


@pytest.mark.asyncio
async def test_execute_content_pipeline_uses_director_metadata_and_drafts_caption():
    director_instance = SimpleNamespace(
        create_pro_video=AsyncMock(
            return_value={
                "video_url": "https://example.com/final.mp4",
                "storyboard_captions": ["Fuel the impossible", "Zero crash. Full focus."],
                "scenes": [{"index": 0}, {"index": 1}],
            }
        )
    )
    canva_tool = SimpleNamespace(
        generate_social_post=AsyncMock(return_value={"success": True, "platform": "instagram", "text": "draft"})
    )

    with patch("app.services.director_service.DirectorService", return_value=director_instance), patch(
        "app.mcp.tools.canva_media.get_canva_tool",
        return_value=canva_tool,
    ), patch("app.services.request_context.get_current_user_id", return_value="u1"):
        result = await execute_content_pipeline(
            prompt="Create a surreal ad for a new energy drink",
            platform="instagram",
            user_id="u1",
        )

    assert result["success"] is True
    assert result["video_url"] == "https://example.com/final.mp4"
    assert result["storyboard_captions"] == ["Fuel the impossible", "Zero crash. Full focus."]
    assert result["publish_result"]["attempted"] is False
    assert "drafted social caption" in result["user_message"].lower() or "caption" in result["user_message"].lower()

    director_instance.create_pro_video.assert_awaited_once()
    create_kwargs = director_instance.create_pro_video.await_args.kwargs
    assert create_kwargs["return_metadata"] is True
    assert create_kwargs["nano_banana_mode"] == "always"

    canva_tool.generate_social_post.assert_awaited_once()
    caption_text = canva_tool.generate_social_post.await_args.kwargs["text"]
    assert "Write a highly converting, engaging caption" not in caption_text
    assert "Fuel the impossible" in caption_text


@pytest.mark.asyncio
async def test_execute_content_pipeline_can_attempt_auto_publish_and_normalize_platform_alias():
    director_instance = SimpleNamespace(
        create_pro_video=AsyncMock(
            return_value={
                "video_url": "https://example.com/final.mp4",
                "storyboard_captions": ["New launch", "Try it today"],
                "scenes": [{"index": 0}],
            }
        )
    )
    canva_tool = SimpleNamespace(
        generate_social_post=AsyncMock(return_value={"success": True, "platform": "twitter", "text": "draft"})
    )
    publisher = SimpleNamespace(post_with_media=AsyncMock(return_value={"success": True, "post_id": "post-123"}))

    with patch("app.services.director_service.DirectorService", return_value=director_instance), patch(
        "app.mcp.tools.canva_media.get_canva_tool",
        return_value=canva_tool,
    ), patch("app.services.request_context.get_current_user_id", return_value="u1"), patch(
        "app.social.publisher.get_social_publisher",
        return_value=publisher,
    ):
        result = await execute_content_pipeline(
            prompt="Launch video",
            platform="x",
            user_id="u1",
            auto_publish=True,
        )

    assert result["success"] is True
    assert result["publish_result"]["attempted"] is True
    assert result["publish_result"]["success"] is True
    publisher.post_with_media.assert_awaited_once()
    publish_kwargs = publisher.post_with_media.await_args.kwargs
    assert publish_kwargs["platform"] == "twitter"
    assert publish_kwargs["media_urls"] == ["https://example.com/final.mp4"]
