# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Per-platform publisher tests for the 6 platforms shipped before 108-04.

Backfills ``publisher.post_with_media`` request-shape coverage for
``twitter``, ``linkedin``, ``facebook``, ``instagram``, ``tiktok``, and
``youtube``. Each platform asserts:

- URL / headers / body shape on the success path
- The structured no-token shortcut (no HTTP issued)
- A 4xx surface produces the standard error envelope
- Platform-specific shortcuts (e.g. instagram text-only -> error,
  tiktok non-video -> error, youtube non-video -> error)

This is a Plan 108-04 / HYGIENE-04 deliverable: tests document the
*current* publisher behavior even when the audit flags the underlying
flow as broken (e.g. LinkedIn URN placeholder, Facebook /me/feed for
non-Page accounts). Out-of-scope fixes are tracked in their respective
phase plans -- the tests here pin the present-day shape so a later
fix can replace them in lockstep.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx


def _build_publisher(
    *,
    token: str | None = "AT",
    platform_user_id: str | None = None,
) -> Any:
    """Construct a SocialPublisher with a mocked connector."""
    from app.social.publisher import SocialPublisher

    publisher = SocialPublisher.__new__(SocialPublisher)
    connector = MagicMock()
    connector.get_access_token = AsyncMock(return_value=token)
    connector.get_platform_user_id = MagicMock(return_value=platform_user_id)
    # Allow lazy-backfill / Facebook page_context calls to be configured
    # per-test by reaching into ``connector.client``.
    connector.client = MagicMock()
    connector._fetch_linkedin_identity = AsyncMock(return_value=(None, None))
    connector._decrypt_token = MagicMock(side_effect=lambda v: v)
    publisher.connector = connector
    return publisher


# ---------------------------------------------------------------------------
# TWITTER
# ---------------------------------------------------------------------------


class TestTwitterPublisher:
    @pytest.mark.asyncio
    @respx.mock
    async def test_post_text_no_media_uses_v2_tweets(self):
        publisher = _build_publisher()
        route = respx.post("https://api.twitter.com/2/tweets").mock(
            return_value=httpx.Response(201, json={"data": {"id": "TWEET-1"}})
        )
        result = await publisher.post_with_media(
            user_id="u1",
            platform="twitter",
            content="hello",
            media_urls=None,
            media_type="text",
        )
        assert route.call_count == 1
        body = route.calls[0].request.content.decode()
        assert '"text"' in body and "hello" in body
        # Bearer header
        auth = route.calls[0].request.headers.get("authorization")
        assert auth == "Bearer AT"
        assert result["success"] is True
        assert result["post_id"] == "TWEET-1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_no_token_returns_error_without_http(self):
        publisher = _build_publisher(token=None)
        route = respx.post("https://api.twitter.com/2/tweets").mock(
            return_value=httpx.Response(201, json={})
        )
        result = await publisher.post_with_media(
            user_id="u1",
            platform="twitter",
            content="hello",
            media_urls=None,
            media_type="text",
        )
        assert route.call_count == 0
        assert "error" in result and "no active connection" in result["error"].lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_4xx_surfaces_error(self):
        publisher = _build_publisher()
        respx.post("https://api.twitter.com/2/tweets").mock(
            return_value=httpx.Response(403, text="Forbidden")
        )
        result = await publisher.post_with_media(
            user_id="u1",
            platform="twitter",
            content="hello",
            media_urls=None,
            media_type="text",
        )
        assert "error" in result
        assert "403" in result["error"]


# ---------------------------------------------------------------------------
# LINKEDIN
# ---------------------------------------------------------------------------


class TestLinkedInPublisher:
    @pytest.mark.asyncio
    @respx.mock
    async def test_post_text_uses_rest_posts_with_urn_author(self):
        publisher = _build_publisher(platform_user_id=None)
        # platform_user_id read by _resolve_linkedin_author_urn
        publisher.connector.client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"platform_user_id": "li-user-99"}]
        )
        route = respx.post("https://api.linkedin.com/rest/posts").mock(
            return_value=httpx.Response(
                201,
                json={"id": "urn:li:share:abc"},
                headers={"x-restli-id": "urn:li:share:abc"},
            )
        )
        result = await publisher.post_with_media(
            user_id="u1",
            platform="linkedin",
            content="news",
            media_urls=None,
            media_type="text",
        )
        assert route.call_count == 1
        # Body shape
        import json as _json

        body = _json.loads(route.calls[0].request.content.decode())
        assert body["author"] == "urn:li:person:li-user-99"
        assert body["commentary"] == "news"
        assert body["lifecycleState"] == "PUBLISHED"
        assert body["visibility"] == "PUBLIC"
        # Headers
        h = route.calls[0].request.headers
        assert h.get("authorization") == "Bearer AT"
        assert h.get("linkedin-version") == "202401"
        assert h.get("x-restli-protocol-version") == "2.0.0"
        assert result["success"] is True
        assert result["post_id"] == "urn:li:share:abc"

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_no_token_returns_error_without_http(self):
        publisher = _build_publisher(token=None)
        route = respx.post("https://api.linkedin.com/rest/posts").mock(
            return_value=httpx.Response(200, json={})
        )
        result = await publisher.post_with_media(
            user_id="u1",
            platform="linkedin",
            content="hi",
            media_urls=None,
            media_type="text",
        )
        assert route.call_count == 0
        assert "error" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_missing_author_urn_returns_reconnect_error(self):
        publisher = _build_publisher()
        # No platform_user_id and lazy-backfill returns (None, None)
        publisher.connector.client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        publisher.connector._fetch_linkedin_identity = AsyncMock(
            return_value=(None, None)
        )
        result = await publisher.post_with_media(
            user_id="u1",
            platform="linkedin",
            content="hi",
            media_urls=None,
            media_type="text",
        )
        assert "error" in result
        assert "reconnect" in result["error"].lower()


# ---------------------------------------------------------------------------
# FACEBOOK
# ---------------------------------------------------------------------------


class TestFacebookPublisher:
    @pytest.mark.asyncio
    @respx.mock
    async def test_post_text_uses_me_feed(self):
        publisher = _build_publisher()
        route = respx.post(
            "https://graph.facebook.com/v23.0/me/feed"
        ).mock(return_value=httpx.Response(200, json={"id": "FB-POST-1"}))
        result = await publisher.post_with_media(
            user_id="u1",
            platform="facebook",
            content="news!",
            media_urls=None,
            media_type="text",
        )
        assert route.call_count == 1
        import json as _json

        body = _json.loads(route.calls[0].request.content.decode())
        assert body == {"message": "news!"}
        h = route.calls[0].request.headers
        assert h.get("authorization") == "Bearer AT"
        assert result["success"] is True
        assert result["post_id"] == "FB-POST-1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_image_uses_me_photos_with_url(self):
        publisher = _build_publisher()
        route = respx.post(
            "https://graph.facebook.com/v23.0/me/photos"
        ).mock(return_value=httpx.Response(200, json={"id": "FB-PHOTO-1"}))
        result = await publisher.post_with_media(
            user_id="u1",
            platform="facebook",
            content="caption",
            media_urls=["https://cdn/img.jpg"],
            media_type="image",
        )
        assert route.call_count == 1
        import json as _json

        body = _json.loads(route.calls[0].request.content.decode())
        assert body == {"message": "caption", "url": "https://cdn/img.jpg"}
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_4xx_surfaces_error(self):
        publisher = _build_publisher()
        respx.post("https://graph.facebook.com/v23.0/me/feed").mock(
            return_value=httpx.Response(400, text="Bad Request")
        )
        result = await publisher.post_with_media(
            user_id="u1",
            platform="facebook",
            content="hi",
            media_urls=None,
            media_type="text",
        )
        assert "error" in result
        assert "400" in result["error"]


# ---------------------------------------------------------------------------
# INSTAGRAM
# ---------------------------------------------------------------------------


class TestInstagramPublisher:
    @pytest.mark.asyncio
    @respx.mock
    async def test_post_text_only_returns_error_without_http(self):
        publisher = _build_publisher()
        result = await publisher.post_with_media(
            user_id="u1",
            platform="instagram",
            content="hi",
            media_urls=None,
            media_type="text",
        )
        assert "error" in result
        assert "media" in result["error"].lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_image_two_step_container_then_publish(self):
        publisher = _build_publisher()
        media_route = respx.post(
            "https://graph.facebook.com/v23.0/me/media"
        ).mock(return_value=httpx.Response(200, json={"id": "ig-container-1"}))
        publish_route = respx.post(
            "https://graph.facebook.com/v23.0/me/media_publish"
        ).mock(return_value=httpx.Response(200, json={"id": "IG-POST-1"}))

        result = await publisher.post_with_media(
            user_id="u1",
            platform="instagram",
            content="caption",
            media_urls=["https://cdn/img.jpg"],
            media_type="image",
        )
        assert media_route.call_count == 1
        assert publish_route.call_count == 1
        import json as _json

        body = _json.loads(media_route.calls[0].request.content.decode())
        assert body == {"caption": "caption", "image_url": "https://cdn/img.jpg"}
        publish_body = _json.loads(publish_route.calls[0].request.content.decode())
        assert publish_body == {"creation_id": "ig-container-1"}
        assert result["success"] is True
        assert result["post_id"] == "IG-POST-1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_video_uses_reels_media_type(self):
        publisher = _build_publisher()
        media_route = respx.post(
            "https://graph.facebook.com/v23.0/me/media"
        ).mock(return_value=httpx.Response(200, json={"id": "ig-reel-1"}))
        publish_route = respx.post(
            "https://graph.facebook.com/v23.0/me/media_publish"
        ).mock(return_value=httpx.Response(200, json={"id": "IG-REEL-PUB"}))

        result = await publisher.post_with_media(
            user_id="u1",
            platform="instagram",
            content="caption",
            media_urls=["https://cdn/vid.mp4"],
            media_type="video",
        )
        assert media_route.call_count == 1
        import json as _json

        body = _json.loads(media_route.calls[0].request.content.decode())
        assert body["media_type"] == "REELS"
        assert body["video_url"] == "https://cdn/vid.mp4"
        assert publish_route.call_count == 1
        assert result["success"] is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_carousel_creates_children_then_carousel_then_publish(self):
        publisher = _build_publisher()

        # All POSTs to /me/media will be intercepted; respx returns the
        # same mocked response. We track call count to assert the 3-step.
        # Use side-effect via incrementing counter.
        media_responses = [
            httpx.Response(200, json={"id": "child-1"}),
            httpx.Response(200, json={"id": "child-2"}),
            httpx.Response(200, json={"id": "carousel-c1"}),
        ]
        idx = {"i": 0}

        def _media_side_effect(request):
            i = idx["i"]
            idx["i"] = i + 1
            return media_responses[i]

        media_route = respx.post(
            "https://graph.facebook.com/v23.0/me/media"
        ).mock(side_effect=_media_side_effect)
        publish_route = respx.post(
            "https://graph.facebook.com/v23.0/me/media_publish"
        ).mock(return_value=httpx.Response(200, json={"id": "IG-CAR-1"}))

        result = await publisher.post_with_media(
            user_id="u1",
            platform="instagram",
            content="cap",
            media_urls=["https://cdn/a.jpg", "https://cdn/b.jpg"],
            media_type="carousel",
        )
        # 2 children + 1 carousel container = 3 POSTs to /me/media
        assert media_route.call_count == 3
        assert publish_route.call_count == 1
        import json as _json

        # Final container payload uses CAROUSEL with children list
        carousel_body = _json.loads(media_route.calls[2].request.content.decode())
        assert carousel_body["media_type"] == "CAROUSEL"
        assert carousel_body["children"] == ["child-1", "child-2"]
        assert carousel_body["caption"] == "cap"
        assert result["success"] is True


# ---------------------------------------------------------------------------
# YOUTUBE
# ---------------------------------------------------------------------------


class TestYouTubePublisher:
    @pytest.mark.asyncio
    async def test_post_text_only_returns_error_without_http(self):
        publisher = _build_publisher()
        result = await publisher.post_with_media(
            user_id="u1",
            platform="youtube",
            content="title",
            media_urls=None,
            media_type="text",
        )
        assert "error" in result
        assert "video" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_post_video_delegates_to_upload_video_youtube(self):
        publisher = _build_publisher()

        async def fake_upload(http, token, media_url, **_kw):
            assert token == "AT"
            assert media_url == "https://cdn/v.mp4"
            return {
                "success": True,
                "platform": "youtube",
                "post_id": "YT-1",
                "video_id": "YT-1",
            }

        with patch.object(
            publisher,
            "_upload_video_youtube",
            side_effect=fake_upload,
        ):
            result = await publisher.post_with_media(
                user_id="u1",
                platform="youtube",
                content="cap",
                media_urls=["https://cdn/v.mp4"],
                media_type="video",
            )
        assert result["success"] is True
        assert result["post_id"] == "YT-1"
        assert result["media_type"] == "video"

    @pytest.mark.asyncio
    async def test_post_video_upload_failure_passes_through_envelope(self):
        publisher = _build_publisher()

        async def fake_upload(http, token, media_url, **_kw):
            return {
                "success": False,
                "error": "youtube_quota_exceeded",
                "reason": "quota",
                "retriable": True,
                "remedy": "wait",
                "stage": "init",
            }

        with patch.object(
            publisher,
            "_upload_video_youtube",
            side_effect=fake_upload,
        ):
            result = await publisher.post_with_media(
                user_id="u1",
                platform="youtube",
                content="cap",
                media_urls=["https://cdn/v.mp4"],
                media_type="video",
            )
        assert result["success"] is False
        assert result["error"] == "youtube_quota_exceeded"
        assert result["reason"] == "quota"


# ---------------------------------------------------------------------------
# TIKTOK
# ---------------------------------------------------------------------------


class TestTikTokPublisher:
    @pytest.mark.asyncio
    async def test_post_text_only_returns_error_without_http(self):
        publisher = _build_publisher()
        result = await publisher.post_with_media(
            user_id="u1",
            platform="tiktok",
            content="x",
            media_urls=None,
            media_type="text",
        )
        assert "error" in result
        assert "video" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_post_image_only_returns_error_without_http(self):
        publisher = _build_publisher()
        result = await publisher.post_with_media(
            user_id="u1",
            platform="tiktok",
            content="x",
            media_urls=["https://cdn/img.jpg"],
            media_type="image",
        )
        assert "error" in result
        assert "video" in result["error"].lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_video_init_uses_pull_from_url_and_polls(self):
        publisher = _build_publisher()
        init_route = respx.post(
            "https://open.tiktokapis.com/v2/post/publish/video/init/"
        ).mock(
            return_value=httpx.Response(
                200, json={"data": {"publish_id": "PUB-1"}, "error": {"code": "ok"}}
            )
        )

        async def fake_poll(http, headers, publish_id):
            assert publish_id == "PUB-1"
            return {
                "success": True,
                "platform": "tiktok",
                "post_id": "PUB-1",
                "media_type": "video",
            }

        with patch.object(
            publisher,
            "_poll_tiktok_publish_status",
            side_effect=fake_poll,
        ):
            result = await publisher.post_with_media(
                user_id="u1",
                platform="tiktok",
                content="x" * 200,  # Title trims to 150
                media_urls=["https://cdn/v.mp4"],
                media_type="video",
            )
        assert init_route.call_count == 1
        import json as _json

        body = _json.loads(init_route.calls[0].request.content.decode())
        assert body["source_info"]["source"] == "PULL_FROM_URL"
        assert body["source_info"]["video_url"] == "https://cdn/v.mp4"
        assert body["post_info"]["title"] == "x" * 150
        assert body["post_info"]["privacy_level"] == "PUBLIC_TO_EVERYONE"
        assert result["success"] is True
        assert result["post_id"] == "PUB-1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_post_video_init_no_publish_id_surfaces_error(self):
        publisher = _build_publisher()
        respx.post(
            "https://open.tiktokapis.com/v2/post/publish/video/init/"
        ).mock(return_value=httpx.Response(200, json={"data": {}}))
        result = await publisher.post_with_media(
            user_id="u1",
            platform="tiktok",
            content="cap",
            media_urls=["https://cdn/v.mp4"],
            media_type="video",
        )
        assert "error" in result
        assert "publish_id" in result["error"].lower()


# ---------------------------------------------------------------------------
# Generic / unknown platform
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_unknown_platform_returns_error():
    publisher = _build_publisher()
    result = await publisher.post_with_media(
        user_id="u1",
        platform="not-a-platform",
        content="hi",
        media_urls=None,
        media_type="text",
    )
    assert "error" in result
    assert "not implemented" in result["error"].lower()
