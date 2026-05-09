# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for the publisher's per-platform media upload helpers (Plan 108-04).

Covers:

- ``_upload_image_twitter``: success + 403 (missing scope) + non-200 +
  >5MB short-circuit.
- ``_upload_video_twitter``: INIT failure + APPEND failure +
  FINALIZE failure (the success path is exercised end-to-end by
  ``test_publisher_existing_platforms.py``).
- ``_upload_linkedin_image``: init failure + missing uploadUrl +
  media fetch failure + PUT failure + success.
- ``_upload_linkedin_video``: init failure + media fetch failure +
  chunk PUT failure + missing etag + finalize failure + success.
- ``_upload_video_youtube``: media fetch failure + initiate failure +
  missing Location + small-file PUT success + chunked PUT.
- ``_post_chunk_with_retry``: 5xx retry, network exception retry, 4xx
  no-retry path.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_publisher() -> Any:
    from app.social.publisher import SocialPublisher

    publisher = SocialPublisher.__new__(SocialPublisher)
    connector = MagicMock()
    connector.get_access_token = AsyncMock(return_value="AT")
    connector.get_platform_user_id = MagicMock(return_value="li-99")
    connector.client = MagicMock()
    connector._fetch_linkedin_identity = AsyncMock(return_value=(None, None))
    connector._decrypt_token = MagicMock(side_effect=lambda v: v)
    publisher.connector = connector
    return publisher


# ---------------------------------------------------------------------------
# Twitter image upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_upload_image_twitter_success():
    publisher = _build_publisher()
    respx.get("https://cdn/img.jpg").mock(
        return_value=httpx.Response(
            200, content=b"fake image", headers={"content-type": "image/jpeg"}
        )
    )
    respx.post("https://api.x.com/2/media/upload").mock(
        return_value=httpx.Response(200, json={"data": {"id": "MID-1"}})
    )

    async with httpx.AsyncClient() as http:
        media_id = await publisher._upload_image_twitter(
            http, {"Authorization": "Bearer AT"}, "https://cdn/img.jpg"
        )
    assert media_id == "MID-1"


@pytest.mark.asyncio
@respx.mock
async def test_upload_image_twitter_403_returns_none():
    publisher = _build_publisher()
    respx.get("https://cdn/img.jpg").mock(
        return_value=httpx.Response(200, content=b"x", headers={"content-type": "image/jpeg"})
    )
    respx.post("https://api.x.com/2/media/upload").mock(
        return_value=httpx.Response(403, text="missing scope")
    )
    async with httpx.AsyncClient() as http:
        media_id = await publisher._upload_image_twitter(
            http, {"Authorization": "Bearer AT"}, "https://cdn/img.jpg"
        )
    assert media_id is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_image_twitter_non_200_returns_none():
    publisher = _build_publisher()
    respx.get("https://cdn/img.jpg").mock(
        return_value=httpx.Response(200, content=b"x")
    )
    respx.post("https://api.x.com/2/media/upload").mock(
        return_value=httpx.Response(500, text="server error")
    )
    async with httpx.AsyncClient() as http:
        media_id = await publisher._upload_image_twitter(
            http, {"Authorization": "Bearer AT"}, "https://cdn/img.jpg"
        )
    assert media_id is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_image_twitter_oversize_returns_none():
    publisher = _build_publisher()
    big = b"\x00" * (6 * 1024 * 1024)
    respx.get("https://cdn/big.jpg").mock(
        return_value=httpx.Response(200, content=big)
    )
    async with httpx.AsyncClient() as http:
        media_id = await publisher._upload_image_twitter(
            http, {"Authorization": "Bearer AT"}, "https://cdn/big.jpg"
        )
    assert media_id is None


# ---------------------------------------------------------------------------
# Twitter video upload (failure branches)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_upload_video_twitter_init_failure_returns_none():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(
        return_value=httpx.Response(200, content=b"\x00" * 100)
    )
    respx.post("https://api.x.com/2/media/upload/initialize").mock(
        return_value=httpx.Response(500, text="boom")
    )
    async with httpx.AsyncClient() as http:
        media_id = await publisher._upload_video_twitter(
            http, {"Authorization": "Bearer AT"}, "https://cdn/v.mp4"
        )
    assert media_id is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_video_twitter_append_failure_returns_none():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(
        return_value=httpx.Response(200, content=b"\x00" * 100)
    )
    respx.post("https://api.x.com/2/media/upload/initialize").mock(
        return_value=httpx.Response(200, json={"data": {"id": "MID"}})
    )
    respx.post("https://api.x.com/2/media/upload").mock(
        return_value=httpx.Response(500, text="append failed")
    )
    async with httpx.AsyncClient() as http:
        media_id = await publisher._upload_video_twitter(
            http, {"Authorization": "Bearer AT"}, "https://cdn/v.mp4"
        )
    assert media_id is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_video_twitter_finalize_failure_returns_none():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(
        return_value=httpx.Response(200, content=b"\x00" * 100)
    )
    respx.post("https://api.x.com/2/media/upload/initialize").mock(
        return_value=httpx.Response(200, json={"data": {"id": "MID"}})
    )
    respx.post("https://api.x.com/2/media/upload").mock(
        return_value=httpx.Response(204)
    )
    respx.post("https://api.x.com/2/media/upload/MID/finalize").mock(
        return_value=httpx.Response(500, text="finalize failed")
    )
    async with httpx.AsyncClient() as http:
        media_id = await publisher._upload_video_twitter(
            http, {"Authorization": "Bearer AT"}, "https://cdn/v.mp4"
        )
    assert media_id is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_video_twitter_finalize_success_no_processing_info():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(
        return_value=httpx.Response(200, content=b"\x00" * 100)
    )
    respx.post("https://api.x.com/2/media/upload/initialize").mock(
        return_value=httpx.Response(200, json={"data": {"id": "MID"}})
    )
    respx.post("https://api.x.com/2/media/upload").mock(
        return_value=httpx.Response(204)
    )
    respx.post("https://api.x.com/2/media/upload/MID/finalize").mock(
        return_value=httpx.Response(200, json={"data": {}})
    )
    async with httpx.AsyncClient() as http:
        media_id = await publisher._upload_video_twitter(
            http, {"Authorization": "Bearer AT"}, "https://cdn/v.mp4"
        )
    assert media_id == "MID"


# ---------------------------------------------------------------------------
# LinkedIn image upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_upload_linkedin_image_init_failure_returns_none():
    publisher = _build_publisher()
    respx.post(
        "https://api.linkedin.com/rest/images?action=initializeUpload"
    ).mock(return_value=httpx.Response(500, text="bad"))
    async with httpx.AsyncClient() as http:
        urn = await publisher._upload_linkedin_image(
            http, {"Authorization": "Bearer AT"}, "urn:li:person:X", "https://cdn/img.jpg"
        )
    assert urn is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_linkedin_image_incomplete_init_returns_none():
    publisher = _build_publisher()
    respx.post(
        "https://api.linkedin.com/rest/images?action=initializeUpload"
    ).mock(return_value=httpx.Response(200, json={"value": {}}))
    async with httpx.AsyncClient() as http:
        urn = await publisher._upload_linkedin_image(
            http, {"Authorization": "Bearer AT"}, "urn:li:person:X", "https://cdn/img.jpg"
        )
    assert urn is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_linkedin_image_media_fetch_failure_returns_none():
    publisher = _build_publisher()
    respx.post(
        "https://api.linkedin.com/rest/images?action=initializeUpload"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "value": {
                    "uploadUrl": "https://upload.linkedin.com/x",
                    "image": "urn:li:image:X",
                }
            },
        )
    )
    respx.get("https://cdn/img.jpg").mock(return_value=httpx.Response(404))
    async with httpx.AsyncClient() as http:
        urn = await publisher._upload_linkedin_image(
            http, {"Authorization": "Bearer AT"}, "urn:li:person:X", "https://cdn/img.jpg"
        )
    assert urn is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_linkedin_image_put_failure_returns_none():
    publisher = _build_publisher()
    respx.post(
        "https://api.linkedin.com/rest/images?action=initializeUpload"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "value": {
                    "uploadUrl": "https://upload.linkedin.com/x",
                    "image": "urn:li:image:X",
                }
            },
        )
    )
    respx.get("https://cdn/img.jpg").mock(
        return_value=httpx.Response(200, content=b"img")
    )
    respx.put("https://upload.linkedin.com/x").mock(
        return_value=httpx.Response(500)
    )
    async with httpx.AsyncClient() as http:
        urn = await publisher._upload_linkedin_image(
            http, {"Authorization": "Bearer AT"}, "urn:li:person:X", "https://cdn/img.jpg"
        )
    assert urn is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_linkedin_image_success():
    publisher = _build_publisher()
    respx.post(
        "https://api.linkedin.com/rest/images?action=initializeUpload"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "value": {
                    "uploadUrl": "https://upload.linkedin.com/x",
                    "image": "urn:li:image:OK",
                }
            },
        )
    )
    respx.get("https://cdn/img.jpg").mock(
        return_value=httpx.Response(200, content=b"img")
    )
    respx.put("https://upload.linkedin.com/x").mock(
        return_value=httpx.Response(201)
    )
    async with httpx.AsyncClient() as http:
        urn = await publisher._upload_linkedin_image(
            http, {"Authorization": "Bearer AT"}, "urn:li:person:X", "https://cdn/img.jpg"
        )
    assert urn == "urn:li:image:OK"


# ---------------------------------------------------------------------------
# LinkedIn video upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_upload_linkedin_video_media_fetch_failure_returns_none():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(return_value=httpx.Response(404))
    async with httpx.AsyncClient() as http:
        urn = await publisher._upload_linkedin_video(
            http, {"Authorization": "Bearer AT"}, "urn:li:person:X", "https://cdn/v.mp4"
        )
    assert urn is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_linkedin_video_init_failure_returns_none():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(
        return_value=httpx.Response(200, content=b"\x00" * 50)
    )
    respx.post(
        "https://api.linkedin.com/rest/videos?action=initializeUpload"
    ).mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as http:
        urn = await publisher._upload_linkedin_video(
            http, {"Authorization": "Bearer AT"}, "urn:li:person:X", "https://cdn/v.mp4"
        )
    assert urn is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_linkedin_video_chunk_put_failure_returns_none():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(
        return_value=httpx.Response(200, content=b"\x00" * 100)
    )
    respx.post(
        "https://api.linkedin.com/rest/videos?action=initializeUpload"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "value": {
                    "video": "urn:li:video:X",
                    "uploadToken": "TOKEN",
                    "uploadInstructions": [
                        {
                            "uploadUrl": "https://upload.linkedin.com/v/c0",
                            "firstByte": 0,
                            "lastByte": 99,
                        }
                    ],
                }
            },
        )
    )
    respx.put("https://upload.linkedin.com/v/c0").mock(
        return_value=httpx.Response(500)
    )
    async with httpx.AsyncClient() as http:
        urn = await publisher._upload_linkedin_video(
            http, {"Authorization": "Bearer AT"}, "urn:li:person:X", "https://cdn/v.mp4"
        )
    assert urn is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_linkedin_video_missing_etag_returns_none():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(
        return_value=httpx.Response(200, content=b"\x00" * 100)
    )
    respx.post(
        "https://api.linkedin.com/rest/videos?action=initializeUpload"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "value": {
                    "video": "urn:li:video:X",
                    "uploadToken": "TOKEN",
                    "uploadInstructions": [
                        {
                            "uploadUrl": "https://upload.linkedin.com/v/c0",
                            "firstByte": 0,
                            "lastByte": 99,
                        }
                    ],
                }
            },
        )
    )
    respx.put("https://upload.linkedin.com/v/c0").mock(
        return_value=httpx.Response(201)  # no etag header
    )
    async with httpx.AsyncClient() as http:
        urn = await publisher._upload_linkedin_video(
            http, {"Authorization": "Bearer AT"}, "urn:li:person:X", "https://cdn/v.mp4"
        )
    assert urn is None


@pytest.mark.asyncio
@respx.mock
async def test_upload_linkedin_video_success():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(
        return_value=httpx.Response(200, content=b"\x00" * 100)
    )
    respx.post(
        "https://api.linkedin.com/rest/videos?action=initializeUpload"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "value": {
                    "video": "urn:li:video:OK",
                    "uploadToken": "TOKEN",
                    "uploadInstructions": [
                        {
                            "uploadUrl": "https://upload.linkedin.com/v/c0",
                            "firstByte": 0,
                            "lastByte": 99,
                        }
                    ],
                }
            },
        )
    )
    respx.put("https://upload.linkedin.com/v/c0").mock(
        return_value=httpx.Response(201, headers={"etag": "etag-1"})
    )
    respx.post(
        "https://api.linkedin.com/rest/videos?action=finalizeUpload"
    ).mock(return_value=httpx.Response(200))
    async with httpx.AsyncClient() as http:
        urn = await publisher._upload_linkedin_video(
            http, {"Authorization": "Bearer AT"}, "urn:li:person:X", "https://cdn/v.mp4"
        )
    assert urn == "urn:li:video:OK"


# ---------------------------------------------------------------------------
# YouTube upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_upload_video_youtube_media_fetch_failure_returns_error():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(return_value=httpx.Response(404))
    async with httpx.AsyncClient() as http:
        result = await publisher._upload_video_youtube(
            http, "AT", "https://cdn/v.mp4", title="t", description="d"
        )
    assert result["success"] is False
    assert result["reason"] == "media_fetch_failed"


@pytest.mark.asyncio
@respx.mock
async def test_upload_video_youtube_init_failure_maps_error():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(
        return_value=httpx.Response(200, content=b"\x00" * 100)
    )
    from app.social.publisher import YOUTUBE_RESUMABLE_INIT_URL

    respx.post(YOUTUBE_RESUMABLE_INIT_URL).mock(
        return_value=httpx.Response(401, text="unauthorized")
    )
    async with httpx.AsyncClient() as http:
        result = await publisher._upload_video_youtube(
            http, "AT", "https://cdn/v.mp4", title="t", description="d"
        )
    assert result["success"] is False
    assert result["stage"] == "initiate"


@pytest.mark.asyncio
@respx.mock
async def test_upload_video_youtube_missing_location_returns_error():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(
        return_value=httpx.Response(200, content=b"\x00" * 100)
    )
    from app.social.publisher import YOUTUBE_RESUMABLE_INIT_URL

    respx.post(YOUTUBE_RESUMABLE_INIT_URL).mock(
        return_value=httpx.Response(200)
    )
    async with httpx.AsyncClient() as http:
        result = await publisher._upload_video_youtube(
            http, "AT", "https://cdn/v.mp4", title="t", description="d"
        )
    assert result["success"] is False
    assert result["reason"] == "missing_location_header"


@pytest.mark.asyncio
@respx.mock
async def test_upload_video_youtube_small_file_single_put_success():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(
        return_value=httpx.Response(200, content=b"\x00" * 100)
    )
    from app.social.publisher import YOUTUBE_RESUMABLE_INIT_URL

    session_url = "https://upload.youtube.com/session/abc"
    respx.post(YOUTUBE_RESUMABLE_INIT_URL).mock(
        return_value=httpx.Response(200, headers={"Location": session_url})
    )
    respx.put(session_url).mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "YT-1",
                "status": {"privacyStatus": "public"},
            },
        )
    )
    async with httpx.AsyncClient() as http:
        result = await publisher._upload_video_youtube(
            http, "AT", "https://cdn/v.mp4", title="t", description="d"
        )
    assert result["success"] is True
    assert result["post_id"] == "YT-1"
    assert result["privacy_status"] == "public"


@pytest.mark.asyncio
@respx.mock
async def test_upload_video_youtube_put_4xx_maps_error():
    publisher = _build_publisher()
    respx.get("https://cdn/v.mp4").mock(
        return_value=httpx.Response(200, content=b"\x00" * 100)
    )
    from app.social.publisher import YOUTUBE_RESUMABLE_INIT_URL

    session_url = "https://upload.youtube.com/session/abc"
    respx.post(YOUTUBE_RESUMABLE_INIT_URL).mock(
        return_value=httpx.Response(200, headers={"Location": session_url})
    )
    respx.put(session_url).mock(
        return_value=httpx.Response(403, text="forbidden")
    )
    async with httpx.AsyncClient() as http:
        result = await publisher._upload_video_youtube(
            http, "AT", "https://cdn/v.mp4", title="t", description="d"
        )
    assert result["success"] is False
    assert result["stage"] == "upload"


# ---------------------------------------------------------------------------
# _post_chunk_with_retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_chunk_with_retry_4xx_no_retry():
    from app.social.publisher import _post_chunk_with_retry

    http = MagicMock()
    resp = MagicMock(status_code=400)
    http.post = AsyncMock(return_value=resp)

    result = await _post_chunk_with_retry(http, "https://x", {})

    assert result is resp
    assert http.post.await_count == 1


@pytest.mark.asyncio
async def test_post_chunk_with_retry_5xx_retries_once():
    from app.social.publisher import _post_chunk_with_retry

    http = MagicMock()
    bad = MagicMock(status_code=503)
    good = MagicMock(status_code=200)
    http.post = AsyncMock(side_effect=[bad, good])

    result = await _post_chunk_with_retry(http, "https://x", {})

    assert result is good
    assert http.post.await_count == 2


@pytest.mark.asyncio
async def test_post_chunk_with_retry_network_exception_retries_then_succeeds():
    import httpx as _httpx

    from app.social.publisher import _post_chunk_with_retry

    http = MagicMock()
    good = MagicMock(status_code=200)
    http.post = AsyncMock(side_effect=[_httpx.RequestError("dns"), good])

    result = await _post_chunk_with_retry(http, "https://x", {})

    assert result is good
    assert http.post.await_count == 2


@pytest.mark.asyncio
async def test_post_chunk_with_retry_two_network_exceptions_raises():
    import httpx as _httpx

    from app.social.publisher import _post_chunk_with_retry

    http = MagicMock()
    http.post = AsyncMock(
        side_effect=[
            _httpx.RequestError("dns"),
            _httpx.RequestError("dns again"),
        ]
    )

    with pytest.raises(_httpx.RequestError):
        await _post_chunk_with_retry(http, "https://x", {})


# ---------------------------------------------------------------------------
# Publisher singleton
# ---------------------------------------------------------------------------


def test_get_social_publisher_returns_singleton():
    from app.social import publisher as pub_mod

    pub_mod._publisher = None
    with patch.object(pub_mod, "SocialPublisher", lambda: MagicMock()):
        a = pub_mod.get_social_publisher()
        b = pub_mod.get_social_publisher()
    assert a is b
    pub_mod._publisher = None


# ---------------------------------------------------------------------------
# get_post_analytics delegates to SocialAnalyticsService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_post_analytics_delegates_to_analytics_service():
    publisher = _build_publisher()
    fake_service = MagicMock()
    fake_service.get_platform_analytics = AsyncMock(
        return_value={"success": True, "platform": "twitter"}
    )
    with patch(
        "app.social.analytics.get_social_analytics_service",
        return_value=fake_service,
    ):
        result = await publisher.get_post_analytics("u1", "twitter", "POST-1")
    assert result["success"] is True
    fake_service.get_platform_analytics.assert_awaited_once_with(
        user_id="u1",
        platform="twitter",
        metric_type="post",
        resource_id="POST-1",
    )
