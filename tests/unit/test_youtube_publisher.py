"""Tests for YouTube resumable upload (POST-07).

Covers the two-step ``videos.insert`` resumable protocol:

  1. POST ``.../upload/youtube/v3/videos?uploadType=resumable&part=snippet,status``
     with snippet+status JSON metadata + ``X-Upload-Content-*`` headers
     -> 200 OK with ``Location`` header containing the session URL.
  2. PUT raw video bytes to the session URL with ``Content-Type: video/*``
     -> 201 Created with the full video resource.

The test file is RED until ``YOUTUBE_RESUMABLE_INIT_URL`` and
``_upload_video_youtube`` exist in ``app/social/publisher.py``. Each error
test asserts the structured ``{success, error, reason, retriable, remedy,
stage}`` shape that POST-07 SC2 mandates.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from app.social.publisher import YOUTUBE_RESUMABLE_INIT_URL, SocialPublisher

# ----------------------------------------------------------------------
# Fixtures and helpers
# ----------------------------------------------------------------------

# ``YOUTUBE_RESUMABLE_INIT_URL`` is imported above as a load-bearing symbol --
# its absence is the RED-state signal until Task 2 of plan 105-01 lands.
YT_INIT_URL = YOUTUBE_RESUMABLE_INIT_URL
SESSION_URL = "https://www.googleapis.com/upload/youtube/v3/videos?upload_id=XYZ"
MEDIA_URL = "https://supabase.local/test.mp4"


def _make_publisher() -> SocialPublisher:
    """Build a SocialPublisher with the connector token-fetch stubbed.

    Bypasses ``__init__`` to avoid triggering ``get_social_connector()`` which
    instantiates the real Supabase client (requires SUPABASE_* env vars). We
    only need ``connector.get_access_token`` for these tests.
    """
    pub = SocialPublisher.__new__(SocialPublisher)
    pub.connector = SimpleNamespace(
        get_access_token=AsyncMock(return_value="fake_token")
    )
    return pub


async def _post(pub: SocialPublisher, *, content: str = "hello") -> dict:
    """Drive ``post_with_media`` for a YouTube video and return the result."""
    return await pub.post_with_media(
        user_id="u1",
        platform="youtube",
        content=content,
        media_urls=[MEDIA_URL],
        media_type="video",
    )


# ----------------------------------------------------------------------
# 1. Two-step request sequence
# ----------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_youtube_resumable_two_step_sequence(respx_mock):
    """POST init then PUT bytes -> success result with post_id from JSON body."""
    respx_mock.get(MEDIA_URL).mock(
        return_value=httpx.Response(200, content=b"\x00" * 1024)
    )
    init_route = respx_mock.post(YT_INIT_URL).mock(
        return_value=httpx.Response(200, headers={"Location": SESSION_URL}, content=b"")
    )
    put_route = respx_mock.put(re.compile(r"upload_id=XYZ")).mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "abc123",
                "status": {
                    "privacyStatus": "public",
                    "uploadStatus": "uploaded",
                },
            },
        )
    )

    pub = _make_publisher()
    result = await _post(pub)

    assert result["success"] is True, result
    assert result["post_id"] == "abc123"
    assert init_route.call_count == 1
    assert put_route.call_count == 1


# ----------------------------------------------------------------------
# 2. Init-request shape
# ----------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_youtube_init_request_shape(respx_mock):
    """Init headers + JSON body match the YouTube resumable spec."""
    import json as _json

    respx_mock.get(MEDIA_URL).mock(
        return_value=httpx.Response(200, content=b"\x00" * 1024)
    )
    init_route = respx_mock.post(YT_INIT_URL).mock(
        return_value=httpx.Response(200, headers={"Location": SESSION_URL}, content=b"")
    )
    respx_mock.put(re.compile(r"upload_id=XYZ")).mock(
        return_value=httpx.Response(
            201, json={"id": "abc123", "status": {"privacyStatus": "public"}}
        )
    )

    pub = _make_publisher()
    await _post(pub, content="x" * 250)

    sent = init_route.calls[0].request
    assert sent.url == YT_INIT_URL, sent.url
    # Headers
    assert sent.headers.get("Authorization") == "Bearer fake_token"
    assert sent.headers.get("Content-Type") == "application/json; charset=UTF-8"
    assert sent.headers.get("X-Upload-Content-Type") == "video/mp4"
    assert sent.headers.get("X-Upload-Content-Length") == "1024"
    # JSON body
    body = _json.loads(sent.content.decode("utf-8"))
    assert "snippet" in body and "status" in body
    assert len(body["snippet"]["title"]) <= 100
    assert body["snippet"]["title"]  # non-empty
    assert body["snippet"]["categoryId"] == "22"
    assert body["snippet"].get("description")
    assert body["status"]["privacyStatus"]
    assert body["status"]["selfDeclaredMadeForKids"] is False
    assert "source_url" not in body, "fictional source_url field must not be sent"


# ----------------------------------------------------------------------
# 3. PUT-request shape
# ----------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_youtube_put_request_shape(respx_mock):
    """PUT uses fresh headers (no leakage) and raw video bytes as body."""
    payload = b"\x42" * 1024
    respx_mock.get(MEDIA_URL).mock(return_value=httpx.Response(200, content=payload))
    respx_mock.post(YT_INIT_URL).mock(
        return_value=httpx.Response(200, headers={"Location": SESSION_URL}, content=b"")
    )
    put_route = respx_mock.put(re.compile(r"upload_id=XYZ")).mock(
        return_value=httpx.Response(
            201, json={"id": "abc123", "status": {"privacyStatus": "public"}}
        )
    )

    pub = _make_publisher()
    result = await _post(pub)
    assert result["success"] is True, result

    sent = put_route.calls[0].request
    assert sent.headers.get("Authorization") == "Bearer fake_token"
    assert sent.headers.get("Content-Type") == "video/mp4"
    assert sent.headers.get("Content-Length") == "1024"
    # Pitfall 2 — fresh headers dict, no JSON / no X-Upload-Content-* leakage
    assert sent.headers.get("X-Upload-Content-Type") is None
    assert sent.headers.get("X-Upload-Content-Length") is None
    ct = sent.headers.get("Content-Type") or ""
    assert "application/json" not in ct
    # Body bytes are exactly the downloaded media bytes
    assert sent.content == payload


# ----------------------------------------------------------------------
# 4. Scoped-grep: source_url absent from YouTube branch
# ----------------------------------------------------------------------


def test_youtube_no_source_url_in_codebase():
    """The fictional ``source_url`` field is gone from publisher.py YouTube branch.

    Phase 104 owns Twitter ``source_url`` (line ~57). This test reads only the
    YouTube branch to avoid coupling phases.
    """
    src = Path("app/social/publisher.py").read_text(encoding="utf-8")
    yt_start = src.index("# ----- YOUTUBE -----")
    # The YouTube branch ends just before the next ``else:`` at the same indent.
    yt_end = src.index("\n                else:", yt_start)
    yt_slice = src[yt_start:yt_end]
    assert "source_url" not in yt_slice, (
        "source_url must not appear in YouTube branch of publisher.py"
    )


# ----------------------------------------------------------------------
# 5. Error: 400 invalidTitle
# ----------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_youtube_error_400_invalid_metadata(respx_mock):
    """Init returns 400 invalidTitle -> non-retriable structured error."""
    respx_mock.get(MEDIA_URL).mock(
        return_value=httpx.Response(200, content=b"\x00" * 1024)
    )
    respx_mock.post(YT_INIT_URL).mock(
        return_value=httpx.Response(
            400,
            json={
                "error": {
                    "code": 400,
                    "errors": [{"reason": "invalidTitle"}],
                    "message": "Invalid title",
                }
            },
        )
    )

    pub = _make_publisher()
    result = await _post(pub)

    assert result["success"] is False
    assert result["reason"] == "invalidTitle"
    assert result["retriable"] is False
    assert "non-empty video title" in result["remedy"]
    assert result["stage"] == "initiate"


# ----------------------------------------------------------------------
# 6. Error: 401 token expired
# ----------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_youtube_error_401_token_expired(respx_mock):
    """Init 401 authorizationRequired -> non-retriable, re-authenticate."""
    respx_mock.get(MEDIA_URL).mock(
        return_value=httpx.Response(200, content=b"\x00" * 1024)
    )
    respx_mock.post(YT_INIT_URL).mock(
        return_value=httpx.Response(
            401,
            json={
                "error": {
                    "code": 401,
                    "errors": [{"reason": "authorizationRequired"}],
                    "message": "Login required",
                }
            },
        )
    )

    pub = _make_publisher()
    result = await _post(pub)

    assert result["success"] is False
    assert result["reason"] == "authorizationRequired"
    assert result["retriable"] is False
    assert "re-authenticate" in result["remedy"].lower()


# ----------------------------------------------------------------------
# 7. Error: 403 quota exceeded
# ----------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_youtube_error_403_quota_exceeded(respx_mock):
    """Init 403 quotaExceeded -> retriable with daily-quota remedy."""
    respx_mock.get(MEDIA_URL).mock(
        return_value=httpx.Response(200, content=b"\x00" * 1024)
    )
    respx_mock.post(YT_INIT_URL).mock(
        return_value=httpx.Response(
            403,
            json={
                "error": {
                    "code": 403,
                    "errors": [{"reason": "quotaExceeded"}],
                    "message": "Quota exceeded",
                }
            },
        )
    )

    pub = _make_publisher()
    result = await _post(pub)

    assert result["success"] is False
    assert result["reason"] == "quotaExceeded"
    assert result["retriable"] is True
    remedy = result["remedy"].lower()
    assert "24h" in remedy or "daily quota" in remedy


# ----------------------------------------------------------------------
# 8. Error: 404 expired session URL on PUT
# ----------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_youtube_error_404_expired_session(respx_mock):
    """PUT returns 404 notFound -> retriable, re-initiate session."""
    respx_mock.get(MEDIA_URL).mock(
        return_value=httpx.Response(200, content=b"\x00" * 1024)
    )
    respx_mock.post(YT_INIT_URL).mock(
        return_value=httpx.Response(200, headers={"Location": SESSION_URL}, content=b"")
    )
    respx_mock.put(re.compile(r"upload_id=XYZ")).mock(
        return_value=httpx.Response(
            404,
            json={
                "error": {
                    "code": 404,
                    "errors": [{"reason": "notFound"}],
                    "message": "Upload session not found",
                }
            },
        )
    )

    pub = _make_publisher()
    result = await _post(pub)

    assert result["success"] is False
    assert result["reason"] == "notFound"
    assert result["retriable"] is True
    remedy = result["remedy"].lower()
    assert "re-initiate" in remedy or "session expired" in remedy
    assert result["stage"] == "upload"


# ----------------------------------------------------------------------
# 9. Error: 5xx transient
# ----------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_youtube_error_5xx_transient(respx_mock):
    """Init 503 -> retriable with transient/backoff remedy."""
    respx_mock.get(MEDIA_URL).mock(
        return_value=httpx.Response(200, content=b"\x00" * 1024)
    )
    respx_mock.post(YT_INIT_URL).mock(
        return_value=httpx.Response(503, text="Service Unavailable")
    )

    pub = _make_publisher()
    result = await _post(pub)

    assert result["success"] is False
    assert result["retriable"] is True
    remedy = result["remedy"].lower()
    assert "transient" in remedy or "retry with backoff" in remedy


# ----------------------------------------------------------------------
# 10. Network interrupt on PUT
# ----------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_youtube_network_interrupt_during_put(respx_mock):
    """PUT raises httpx.RequestError -> structured retriable error."""
    respx_mock.get(MEDIA_URL).mock(
        return_value=httpx.Response(200, content=b"\x00" * 1024)
    )
    respx_mock.post(YT_INIT_URL).mock(
        return_value=httpx.Response(200, headers={"Location": SESSION_URL}, content=b"")
    )
    respx_mock.put(re.compile(r"upload_id=XYZ")).mock(
        side_effect=httpx.ReadError("connection reset")
    )

    pub = _make_publisher()
    result = await _post(pub)

    assert result["success"] is False
    assert result.get("reason")
    assert result["retriable"] is True
    assert "retry" in result["remedy"].lower()


# ----------------------------------------------------------------------
# 11. Missing Location header
# ----------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_youtube_missing_location_header(respx_mock):
    """Init 200 with no ``Location`` header -> structured error."""
    respx_mock.get(MEDIA_URL).mock(
        return_value=httpx.Response(200, content=b"\x00" * 1024)
    )
    respx_mock.post(YT_INIT_URL).mock(return_value=httpx.Response(200, content=b""))

    pub = _make_publisher()
    result = await _post(pub)

    assert result["success"] is False
    assert result["reason"] == "missing_location_header"
    assert result["retriable"] is True


# ----------------------------------------------------------------------
# 12. Chunked upload (>25MB) with 308 Resume Incomplete handling
# ----------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock(assert_all_called=False)
async def test_youtube_chunked_upload_resume_path(respx_mock):
    """30MB upload -> 4 PUTs (3x 8MB + 1x 6MB), 308 -> 308 -> 308 -> 201."""
    from app.social.publisher import YOUTUBE_CHUNK_SIZE  # 8MB

    total = 30 * 1024 * 1024
    payload = b"\x00" * total
    expected_chunks = -(-total // YOUTUBE_CHUNK_SIZE)  # ceil division -> 4
    assert expected_chunks == 4

    respx_mock.get(MEDIA_URL).mock(return_value=httpx.Response(200, content=payload))
    respx_mock.post(YT_INIT_URL).mock(
        return_value=httpx.Response(200, headers={"Location": SESSION_URL}, content=b"")
    )
    chunk_responses = [
        httpx.Response(308, headers={"Range": "bytes=0-8388607"}, content=b""),
        httpx.Response(308, headers={"Range": "bytes=0-16777215"}, content=b""),
        httpx.Response(308, headers={"Range": "bytes=0-25165823"}, content=b""),
        httpx.Response(
            201,
            json={
                "id": "chunked_video_id",
                "status": {"privacyStatus": "public"},
            },
        ),
    ]
    put_route = respx_mock.put(re.compile(r"upload_id=XYZ")).mock(
        side_effect=chunk_responses
    )

    pub = _make_publisher()
    result = await _post(pub)

    assert result["success"] is True, result
    assert result["post_id"] == "chunked_video_id"
    assert put_route.call_count == expected_chunks

    # Inspect each request's Content-Range
    expected_ranges = [
        f"bytes 0-8388607/{total}",
        f"bytes 8388608-16777215/{total}",
        f"bytes 16777216-25165823/{total}",
        f"bytes 25165824-{total - 1}/{total}",
    ]
    expected_lengths = [
        YOUTUBE_CHUNK_SIZE,
        YOUTUBE_CHUNK_SIZE,
        YOUTUBE_CHUNK_SIZE,
        total - 3 * YOUTUBE_CHUNK_SIZE,  # = 6291456
    ]
    for i, call in enumerate(put_route.calls):
        req = call.request
        assert req.headers.get("Content-Range") == expected_ranges[i], (
            f"chunk {i}: expected {expected_ranges[i]}, "
            f"got {req.headers.get('Content-Range')}"
        )
        assert req.headers.get("Content-Length") == str(expected_lengths[i])
