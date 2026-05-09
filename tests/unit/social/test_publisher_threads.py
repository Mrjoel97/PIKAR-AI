# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Failing tests for HYGIENE-01 -- Threads publisher branch.

Asserts the two-step container/publish flow against
``https://graph.threads.net/v1.0/{threads-user-id}/threads`` then
``.../threads_publish`` for text, image and video media types, plus error
shortcuts for missing ``platform_user_id``, container-creation failure,
and missing access token.

Pattern: ``respx`` for the upstream Meta endpoints (mirrors the existing
Facebook three-phase upload tests in ``test_publisher_facebook.py``);
direct attribute injection into a ``SocialPublisher`` instance
side-steps the ``get_social_connector`` singleton boot path.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

from app.social.publisher import SocialPublisher

THREADS_USER_ID = "1122334455"
ACCESS_TOKEN = "AT-THREADS"
BASE = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}"


def _make_publisher(
    *,
    token: str | None = ACCESS_TOKEN,
    platform_user_id: str | None = THREADS_USER_ID,
) -> SocialPublisher:
    """Build a SocialPublisher with a mocked connector.

    Bypasses ``__init__`` so the global supabase singleton is not invoked.
    """
    publisher = SocialPublisher.__new__(SocialPublisher)
    connector = MagicMock()
    connector.get_access_token = AsyncMock(return_value=token)
    connector.get_platform_user_id = MagicMock(return_value=platform_user_id)
    publisher.connector = connector
    return publisher


# ---------------------------------------------------------------------------
# Two-step container/publish flow
# ---------------------------------------------------------------------------


class TestThreadsPublisher:
    @pytest.mark.asyncio
    @respx.mock
    async def test_post_text_two_step(self):
        publisher = _make_publisher()

        container_route = respx.post(f"{BASE}/threads").mock(
            return_value=httpx.Response(200, json={"id": "container-A"})
        )
        publish_route = respx.post(f"{BASE}/threads_publish").mock(
            return_value=httpx.Response(200, json={"id": "thread-XYZ"})
        )

        result = await publisher.post_with_media(
            user_id="u1",
            platform="threads",
            content="hello world",
            media_urls=None,
            media_type="text",
        )

        assert container_route.call_count == 1
        assert publish_route.call_count == 1

        # First call: container creation form data.
        first_body = container_route.calls[0].request.content.decode()
        assert "media_type=TEXT" in first_body
        assert "text=hello+world" in first_body or "text=hello%20world" in first_body
        assert f"access_token={ACCESS_TOKEN}" in first_body

        # Second call: publish carries the creation_id.
        second_body = publish_route.calls[0].request.content.decode()
        assert "creation_id=container-A" in second_body
        assert f"access_token={ACCESS_TOKEN}" in second_body

        assert result["success"] is True
        assert result["platform"] == "threads"
        assert result["post_id"] == "thread-XYZ"
        assert result["media_type"] == "text"
        assert "successfully" in result["message"].lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_image_uses_image_url(self):
        publisher = _make_publisher()

        container_route = respx.post(f"{BASE}/threads").mock(
            return_value=httpx.Response(200, json={"id": "container-IMG"})
        )
        respx.post(f"{BASE}/threads_publish").mock(
            return_value=httpx.Response(200, json={"id": "thread-IMG-PUB"})
        )

        image_url = "https://cdn.example.com/pic.jpg"
        result = await publisher.post_with_media(
            user_id="u1",
            platform="threads",
            content="caption",
            media_urls=[image_url],
            media_type="image",
        )

        body = container_route.calls[0].request.content.decode()
        assert "media_type=IMAGE" in body
        # urlencoded image_url -- look for the host segment.
        assert "image_url=" in body
        assert "cdn.example.com" in body
        assert "text=caption" in body

        assert result["success"] is True
        assert result["media_type"] == "image"
        assert result["post_id"] == "thread-IMG-PUB"

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_video_uses_video_url(self):
        publisher = _make_publisher()

        container_route = respx.post(f"{BASE}/threads").mock(
            return_value=httpx.Response(200, json={"id": "container-VID"})
        )
        respx.post(f"{BASE}/threads_publish").mock(
            return_value=httpx.Response(200, json={"id": "thread-VID-PUB"})
        )

        video_url = "https://cdn.example.com/clip.mp4"
        result = await publisher.post_with_media(
            user_id="u1",
            platform="threads",
            content="caption",
            media_urls=[video_url],
            media_type="video",
        )

        body = container_route.calls[0].request.content.decode()
        assert "media_type=VIDEO" in body
        assert "video_url=" in body
        assert "cdn.example.com" in body

        assert result["success"] is True
        assert result["media_type"] == "video"
        assert result["post_id"] == "thread-VID-PUB"

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_no_user_id_returns_error_without_http_call(self):
        publisher = _make_publisher(platform_user_id=None)

        container_route = respx.post(f"{BASE}/threads").mock(
            return_value=httpx.Response(200, json={"id": "should-not-be-called"})
        )

        result = await publisher.post_with_media(
            user_id="u1",
            platform="threads",
            content="hi",
            media_urls=None,
            media_type="text",
        )

        assert "error" in result
        assert "Threads user ID missing" in result["error"]
        assert container_route.call_count == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_container_creation_failure_short_circuits(self):
        publisher = _make_publisher()

        container_route = respx.post(f"{BASE}/threads").mock(
            return_value=httpx.Response(400, text="invalid image url")
        )
        publish_route = respx.post(f"{BASE}/threads_publish").mock(
            return_value=httpx.Response(200, json={"id": "should-not-publish"})
        )

        result = await publisher.post_with_media(
            user_id="u1",
            platform="threads",
            content="hi",
            media_urls=["https://broken.example.com/x.jpg"],
            media_type="image",
        )

        assert "error" in result
        assert "Threads container creation failed" in result["error"]
        assert container_route.call_count == 1
        # Critically: publish was never attempted.
        assert publish_route.call_count == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_no_token_returns_error(self):
        publisher = _make_publisher(token=None)

        container_route = respx.post(f"{BASE}/threads").mock(
            return_value=httpx.Response(200, json={"id": "should-not-call"})
        )

        result = await publisher.post_with_media(
            user_id="u1",
            platform="threads",
            content="hi",
            media_urls=None,
            media_type="text",
        )

        assert "error" in result
        assert "No active connection for threads" in result["error"]
        # Token check happens before any platform-specific code.
        assert container_route.call_count == 0
        publisher.connector.get_platform_user_id.assert_not_called()
