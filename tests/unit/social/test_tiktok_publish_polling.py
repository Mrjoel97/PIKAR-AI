# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for TikTok publish status polling (Phase 106-01, POST-08).

These tests pin the TikTok publish contract:

1. After ``/v2/post/publish/video/init/`` returns ``data.publish_id``, the
   publisher polls ``/v2/post/publish/status/fetch/`` every 5s (starting 5s
   after init) until a terminal status is reached or the 5-minute deadline
   trips.
2. On ``PUBLISH_COMPLETE`` the result carries the real ``video_id`` read
   from ``data.publicaly_available_post_id[0]`` (TikTok's typo, sic).
3. On ``FAILED`` the result is a structured error containing the verbatim
   ``fail_reason`` from TikTok.
4. On the 5-minute cap the result is a ``publish_pending`` error (never
   ``success: True``).
5. The polling loop is non-blocking -- it MUST use ``asyncio.sleep``,
   never ``time.sleep``.
6. The init URL is ``/v2/post/publish/video/init/`` (the video direct-post
   endpoint), never ``/v2/post/publish/content/init/`` (the photo /
   carousel endpoint).
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.social.publisher import SocialPublisher


def _resp(status_code: int, payload: dict[str, Any]) -> MagicMock:
    """Build a MagicMock httpx-like response."""
    m = MagicMock()
    m.status_code = status_code
    m.json = MagicMock(return_value=payload)
    m.text = str(payload)
    return m


def _wire_async_client(
    monkeypatch: pytest.MonkeyPatch, post_responses: list[MagicMock]
) -> AsyncMock:
    """Patch httpx.AsyncClient so its async-context-manager yields a mock client.

    Returns the inner mock client so tests can assert against
    ``.post.await_args_list``.
    """
    client = AsyncMock()
    client.post = AsyncMock(side_effect=post_responses)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr("httpx.AsyncClient", lambda *a, **kw: client)
    return client


def _wire_connector(monkeypatch: pytest.MonkeyPatch, token: str = "tok_xyz") -> None:
    """Patch ``app.social.publisher.get_social_connector`` to a mock returning ``token``."""
    connector = MagicMock()
    connector.get_access_token = AsyncMock(return_value=token)
    monkeypatch.setattr(
        "app.social.publisher.get_social_connector", lambda: connector
    )


@pytest.mark.asyncio
async def test_tiktok_publish_polls_until_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3-poll happy path: publisher polls until PUBLISH_COMPLETE and returns video_id."""
    init_resp = _resp(
        200, {"data": {"publish_id": "p_abc123"}, "error": {"code": "ok"}}
    )
    poll1 = _resp(
        200,
        {"data": {"status": "PROCESSING_UPLOAD"}, "error": {"code": "ok"}},
    )
    poll2 = _resp(
        200,
        {"data": {"status": "PROCESSING_DOWNLOAD"}, "error": {"code": "ok"}},
    )
    poll3 = _resp(
        200,
        {
            "data": {
                "status": "PUBLISH_COMPLETE",
                "publicaly_available_post_id": ["7012345678901234567"],
                "uploaded_bytes": 12345678,
            },
            "error": {"code": "ok"},
        },
    )
    client = _wire_async_client(monkeypatch, [init_resp, poll1, poll2, poll3])
    _wire_connector(monkeypatch)
    sleep_mock = AsyncMock()
    monkeypatch.setattr("asyncio.sleep", sleep_mock)

    result = await SocialPublisher().post_with_media(
        user_id="u1",
        platform="tiktok",
        content="hello world",
        media_urls=["https://example.com/v.mp4"],
        media_type="video",
    )

    assert result["success"] is True
    assert result["platform"] == "tiktok"
    assert result["video_id"] == "7012345678901234567"
    assert result["post_id"] == "7012345678901234567"
    assert result["publish_id"] == "p_abc123"
    assert result["media_type"] == "video"
    assert client.post.await_count == 4

    # Sleep cadence: at least 4 awaits, each with 5.0 (initial + between-poll).
    assert sleep_mock.await_count >= 4
    for call_args in sleep_mock.await_args_list:
        assert call_args.args[0] == 5.0

    # URL assertions.
    first_url = client.post.await_args_list[0].args[0]
    assert first_url == "https://open.tiktokapis.com/v2/post/publish/video/init/"
    for poll_call in client.post.await_args_list[1:]:
        assert (
            poll_call.args[0]
            == "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
        )
    # Status-fetch body contains publish_id.
    first_poll_kwargs = client.post.await_args_list[1].kwargs
    assert first_poll_kwargs["json"]["publish_id"] == "p_abc123"


@pytest.mark.asyncio
async def test_tiktok_publish_failed_returns_structured_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FAILED terminal status surfaces fail_reason verbatim and stops polling."""
    init_resp = _resp(
        200, {"data": {"publish_id": "p_abc123"}, "error": {"code": "ok"}}
    )
    fail_resp = _resp(
        200,
        {
            "data": {"status": "FAILED", "fail_reason": "video_pull_failed"},
            "error": {"code": "ok"},
        },
    )
    client = _wire_async_client(monkeypatch, [init_resp, fail_resp])
    _wire_connector(monkeypatch)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    result = await SocialPublisher().post_with_media(
        user_id="u1",
        platform="tiktok",
        content="hi",
        media_urls=["https://example.com/v.mp4"],
        media_type="video",
    )

    assert result.get("success") is not True
    assert "error" in result
    assert "video_pull_failed" in result["error"]
    assert result["fail_reason"] == "video_pull_failed"
    assert result["publish_id"] == "p_abc123"
    assert client.post.await_count == 2  # init + one poll, no further polls.


@pytest.mark.asyncio
async def test_tiktok_publish_cap_exceeded_returns_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5-minute cap trips with non-terminal status → publish_pending error."""
    init_resp = _resp(
        200, {"data": {"publish_id": "p_abc123"}, "error": {"code": "ok"}}
    )
    processing_resp = _resp(
        200,
        {"data": {"status": "PROCESSING_DOWNLOAD"}, "error": {"code": "ok"}},
    )
    # Provide a generous side_effect list so the helper never runs out.
    client = _wire_async_client(
        monkeypatch, [init_resp] + [processing_resp] * 200
    )
    _wire_connector(monkeypatch)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    # Patch the loop clock so deadline trips after the first poll.
    # Sequence: first call sets deadline (0.0 + 300.0 = 300.0); subsequent
    # checks return 999.0 → loop exits via the cap-exceeded path.
    clock_values = iter([0.0, 999.0, 999.0, 999.0, 999.0])
    mock_loop = MagicMock()
    mock_loop.time = MagicMock(side_effect=lambda: next(clock_values, 999.0))
    monkeypatch.setattr("asyncio.get_event_loop", lambda: mock_loop)

    result = await SocialPublisher().post_with_media(
        user_id="u1",
        platform="tiktok",
        content="hi",
        media_urls=["https://example.com/v.mp4"],
        media_type="video",
    )

    assert result.get("success") is not True
    assert "publish_pending" in result["error"]
    assert "check TikTok manually" in result["error"]
    assert result["publish_id"] == "p_abc123"


@pytest.mark.asyncio
async def test_tiktok_polling_uses_asyncio_sleep_not_time_sleep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Polling loop MUST use asyncio.sleep -- time.sleep blocks the event loop."""
    init_resp = _resp(
        200, {"data": {"publish_id": "p_abc123"}, "error": {"code": "ok"}}
    )
    poll1 = _resp(
        200,
        {"data": {"status": "PROCESSING_UPLOAD"}, "error": {"code": "ok"}},
    )
    poll2 = _resp(
        200,
        {"data": {"status": "PROCESSING_DOWNLOAD"}, "error": {"code": "ok"}},
    )
    poll3 = _resp(
        200,
        {
            "data": {
                "status": "PUBLISH_COMPLETE",
                "publicaly_available_post_id": ["7012345678901234567"],
            },
            "error": {"code": "ok"},
        },
    )
    _wire_async_client(monkeypatch, [init_resp, poll1, poll2, poll3])
    _wire_connector(monkeypatch)

    time_sleep_mock = MagicMock()
    monkeypatch.setattr(time, "sleep", time_sleep_mock)
    async_sleep_mock = AsyncMock()
    monkeypatch.setattr("asyncio.sleep", async_sleep_mock)

    result = await SocialPublisher().post_with_media(
        user_id="u1",
        platform="tiktok",
        content="hi",
        media_urls=["https://example.com/v.mp4"],
        media_type="video",
    )

    assert result["success"] is True
    assert time_sleep_mock.called is False, (
        "time.sleep blocks the event loop -- must use asyncio.sleep"
    )
    assert async_sleep_mock.await_count >= 4


@pytest.mark.asyncio
async def test_tiktok_init_uses_video_endpoint_not_content_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: init URL is /video/init/ (video endpoint), not /content/init/ (photo)."""
    init_resp = _resp(
        200, {"data": {"publish_id": "p_abc123"}, "error": {"code": "ok"}}
    )
    poll1 = _resp(
        200,
        {
            "data": {
                "status": "PUBLISH_COMPLETE",
                "publicaly_available_post_id": ["7012"],
            },
            "error": {"code": "ok"},
        },
    )
    client = _wire_async_client(monkeypatch, [init_resp, poll1])
    _wire_connector(monkeypatch)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    await SocialPublisher().post_with_media(
        user_id="u1",
        platform="tiktok",
        content="hi",
        media_urls=["https://example.com/v.mp4"],
        media_type="video",
    )

    first_url = client.post.await_args_list[0].args[0]
    assert first_url == "https://open.tiktokapis.com/v2/post/publish/video/init/"
    for call_args in client.post.await_args_list:
        assert "content/init" not in call_args.args[0]
