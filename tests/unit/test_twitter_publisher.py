"""Tests for Twitter publisher v2 media upload (Phase 104, POST-04).

Wave-0 RED tests asserting the desired behavior of ``_upload_image_twitter``
and the dispatching Twitter branch in ``post_with_media``. These fail until
Wave-1 lands the implementation in :mod:`app.social.publisher`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_publisher_with_token(token: str = "FAKE_TOKEN"):
    """Build a SocialPublisher with a stub connector that yields ``token``.

    Uses ``__new__`` to bypass ``__init__`` so we never touch the real
    Supabase singleton (which is what production ``get_social_connector``
    instantiates).
    """
    from app.social.publisher import SocialPublisher

    publisher = SocialPublisher.__new__(SocialPublisher)
    publisher.connector = MagicMock()
    publisher.connector.get_access_token = AsyncMock(return_value=token)
    return publisher


def _patch_async_client(get_responses, post_responses):
    """Return a patch context for ``httpx.AsyncClient`` with the given responses.

    ``get_responses`` and ``post_responses`` are lists used as ``side_effect``
    for the inner client's ``get`` / ``post`` AsyncMocks (in call order).
    """
    fake_client = MagicMock()
    fake_client.get = AsyncMock(side_effect=get_responses)
    fake_client.post = AsyncMock(side_effect=post_responses)

    fake_async_client = MagicMock()
    fake_async_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_async_client.__aexit__ = AsyncMock(return_value=None)

    return patch("httpx.AsyncClient", return_value=fake_async_client), fake_client


def _ok_image_get(size_bytes: int = 4_000_000):
    """Return a MagicMock simulating a successful image bytes fetch."""
    resp = MagicMock()
    resp.status_code = 200
    resp.content = b"x" * size_bytes
    resp.headers = {"content-type": "image/jpeg"}
    resp.raise_for_status = MagicMock(return_value=None)
    return resp


def _upload_response(status_code: int, payload: dict | None = None, text: str = "ok"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.json = MagicMock(return_value=payload or {})
    return resp


class TestImageUpload:
    """POST-04: simple v2 image upload path."""

    @pytest.mark.asyncio
    async def test_image_simple_upload(self):
        publisher = _make_publisher_with_token()

        get_responses = [_ok_image_get(4_000_000)]
        post_responses = [
            _upload_response(200, {"data": {"id": "MEDIA_ID_123"}}),
            _upload_response(201, {"data": {"id": "TWEET_ID"}}),
        ]
        ctx, fake_client = _patch_async_client(get_responses, post_responses)

        with ctx:
            result = await publisher.post_with_media(
                user_id="u1",
                platform="twitter",
                content="hello world",
                media_urls=["https://example.test/photo.jpg"],
                media_type="image",
            )

        assert "error" not in result, f"unexpected error: {result}"
        assert fake_client.post.call_count == 2

        first_call = fake_client.post.call_args_list[0]
        assert first_call.args[0] == "https://api.x.com/2/media/upload"
        assert "files" in first_call.kwargs
        assert "media" in first_call.kwargs["files"]
        assert first_call.kwargs.get("data") == {"media_category": "tweet_image"}
        assert first_call.kwargs["headers"]["Authorization"] == "Bearer FAKE_TOKEN"

        second_call = fake_client.post.call_args_list[1]
        assert second_call.args[0] == "https://api.twitter.com/2/tweets"
        assert second_call.kwargs.get("json") == {
            "text": "hello world",
            "media": {"media_ids": ["MEDIA_ID_123"]},
        }
        assert second_call.kwargs["headers"]["Authorization"] == "Bearer FAKE_TOKEN"

    @pytest.mark.asyncio
    async def test_image_simple_upload_too_large_returns_error(self, caplog):
        publisher = _make_publisher_with_token()

        # 5MB + 1 byte - guard must reject before issuing the upload POST.
        get_responses = [_ok_image_get(5 * 1024 * 1024 + 1)]
        post_responses: list = []  # no posts should fire
        ctx, fake_client = _patch_async_client(get_responses, post_responses)

        with ctx, caplog.at_level(logging.WARNING, logger="app.social.publisher"):
            result = await publisher.post_with_media(
                user_id="u1",
                platform="twitter",
                content="too big",
                media_urls=["https://example.test/huge.jpg"],
                media_type="image",
            )

        assert "error" in result
        assert "Twitter media upload failed" in result["error"]

        # Neither media upload nor tweet POST should have been called.
        for call in fake_client.post.call_args_list:
            assert call.args[0] != "https://api.x.com/2/media/upload"
            assert call.args[0] != "https://api.twitter.com/2/tweets"

        assert any(">5MB" in record.getMessage() for record in caplog.records)


class TestAuthErrorMessage:
    """POST-06: 403 from media upload surfaces a reconnect prompt."""

    @pytest.mark.asyncio
    async def test_403_returns_reconnect_message(self, caplog):
        publisher = _make_publisher_with_token()

        get_responses = [_ok_image_get(4_000_000)]
        post_responses = [
            _upload_response(403, text="missing scope: media.write"),
        ]
        ctx, fake_client = _patch_async_client(get_responses, post_responses)

        with ctx, caplog.at_level(logging.WARNING, logger="app.social.publisher"):
            result = await publisher.post_with_media(
                user_id="u1",
                platform="twitter",
                content="will fail",
                media_urls=["https://example.test/photo.jpg"],
                media_type="image",
            )

        assert "error" in result
        assert "reconnect" in result["error"].lower()

        # Tweet POST must NOT be attempted after upload failure.
        for call in fake_client.post.call_args_list:
            assert call.args[0] != "https://api.twitter.com/2/tweets"

        log_messages = [r.getMessage() for r in caplog.records]
        assert any("403" in m and "media.write" in m for m in log_messages)


class TestNoFictionalSourceUrl:
    """POST-04: dead v1.1 endpoint and fictional source_url must be gone."""

    def test_no_fictional_source_url_in_twitter_branch(self):
        src = Path("app/social/publisher.py").read_text(encoding="utf-8")

        twitter_section = src.split("# ----- TWITTER / X -----", 1)[1].split(
            "# ----- LINKEDIN -----", 1
        )[0]

        assert "source_url" not in twitter_section, (
            "Phase 104: source_url is fictional and must not appear in the "
            "Twitter branch"
        )
        assert "_upload_image_twitter" in twitter_section
        assert "upload.twitter.com" not in twitter_section
        assert "api.x.com/2/media/upload" in src


class TestVideoStubRaises:
    """POST-05 stub: video path returns 'not yet available' until 104-02.

    NOTE: This stub-guard test was REMOVED in Plan 104-02 once the chunked
    upload landed. See ``TestVideoChunkedUpload`` below.
    """


def _ok_video_get(size_bytes: int = 10 * 1024 * 1024, mime: str = "video/mp4"):
    """Return a MagicMock simulating a successful video bytes fetch."""
    resp = MagicMock()
    resp.status_code = 200
    resp.content = b"v" * size_bytes
    resp.headers = {"content-type": mime}
    resp.raise_for_status = MagicMock(return_value=None)
    return resp


def _status_response(
    state: str,
    *,
    check_after_secs: int | None = None,
    error: dict | None = None,
    progress_percent: int | None = None,
):
    """Build a STATUS poll response payload mock."""
    proc: dict[str, Any] = {"state": state}
    if check_after_secs is not None:
        proc["check_after_secs"] = check_after_secs
    if error is not None:
        proc["error"] = error
    if progress_percent is not None:
        proc["progress_percent"] = progress_percent
    return _upload_response(200, {"data": {"processing_info": proc}})


class TestVideoChunkedUpload:
    """POST-05: full INIT -> APPEND -> FINALIZE -> STATUS chunked flow.

    All tests patch ``app.social.publisher.asyncio.sleep`` to avoid real
    delays. Implementation note for Wave-1 (Task 2): the executor MUST add
    ``import asyncio`` at module scope of ``app/social/publisher.py`` so
    these patch targets resolve.

    Sleep ordering chosen here: sleep BEFORE each STATUS GET (the API tells
    us when to come back via ``check_after_secs``), so for a state machine
    of [pending, in_progress, succeeded] there are exactly 3 sleeps and 3
    STATUS GETs.
    """

    @pytest.mark.asyncio
    async def test_video_chunked_upload_succeeds(self):
        publisher = _make_publisher_with_token()

        # ~10MB video -> 3 APPEND chunks (4MB + 4MB + 2MB).
        size_10mb = 10 * 1024 * 1024
        get_responses = [
            _ok_video_get(size_10mb),
            # FINALIZE returned processing_info pending so we poll STATUS:
            _status_response("pending", check_after_secs=1),
            _status_response("in_progress", check_after_secs=1, progress_percent=50),
            _status_response("succeeded"),
        ]
        post_responses = [
            # INIT
            _upload_response(202, {"data": {"id": "VID_42"}}),
            # APPEND x 3 (return 204 to exercise the 204 acceptance path)
            _upload_response(204, {}),
            _upload_response(204, {}),
            _upload_response(204, {}),
            # FINALIZE -> processing pending
            _upload_response(
                201,
                {
                    "data": {
                        "id": "VID_42",
                        "processing_info": {"state": "pending", "check_after_secs": 1},
                    }
                },
            ),
            # Tweet create
            _upload_response(201, {"data": {"id": "TWEET_ID"}}),
        ]
        ctx, fake_client = _patch_async_client(get_responses, post_responses)

        with (
            ctx,
            patch(
                "app.social.publisher.asyncio.sleep", new_callable=AsyncMock
            ) as mock_sleep,
        ):
            result = await publisher.post_with_media(
                user_id="u1",
                platform="twitter",
                content="video test",
                media_urls=["https://example.test/clip.mp4"],
                media_type="video",
            )

        assert "error" not in result, f"unexpected error: {result}"

        # Verify POST sequence
        post_calls = fake_client.post.call_args_list
        assert len(post_calls) == 6

        # 0: INIT
        init_call = post_calls[0]
        assert init_call.args[0] == "https://api.x.com/2/media/upload/initialize"
        assert init_call.kwargs["json"] == {
            "media_type": "video/mp4",
            "total_bytes": size_10mb,
            "media_category": "tweet_video",
        }
        assert init_call.kwargs["headers"]["Content-Type"] == "application/json"
        assert init_call.kwargs["headers"]["Authorization"] == "Bearer FAKE_TOKEN"

        # 1-3: APPEND chunks with monotonic segment_index 0,1,2
        for idx in range(3):
            append_call = post_calls[idx + 1]
            assert append_call.args[0] == "https://api.x.com/2/media/upload"
            assert append_call.kwargs["data"]["command"] == "APPEND"
            assert append_call.kwargs["data"]["media_id"] == "VID_42"
            assert append_call.kwargs["data"]["segment_index"] == idx
            assert "media" in append_call.kwargs["files"]

        # 4: FINALIZE
        finalize_call = post_calls[4]
        assert (
            finalize_call.args[0] == "https://api.x.com/2/media/upload/VID_42/finalize"
        )

        # 5: tweet create with media_id attached
        tweet_call = post_calls[5]
        assert tweet_call.args[0] == "https://api.twitter.com/2/tweets"
        assert tweet_call.kwargs["json"] == {
            "text": "video test",
            "media": {"media_ids": ["VID_42"]},
        }

        # GETs: 1 video fetch + 3 STATUS polls
        get_calls = fake_client.get.call_args_list
        assert len(get_calls) == 4
        for status_call in get_calls[1:]:
            assert status_call.args[0] == "https://api.x.com/2/media/upload"
            assert status_call.kwargs["params"] == {
                "command": "STATUS",
                "media_id": "VID_42",
            }

        # Sleep ordering: sleep before each STATUS GET => 3 sleeps total.
        assert mock_sleep.await_count == 3

    @pytest.mark.asyncio
    async def test_video_chunked_upload_segment_index_sequence(self):
        """4MB chunk_size + 1 byte tail => exactly 5 chunks, indices [0..4]."""
        publisher = _make_publisher_with_token()

        chunk_size = 4 * 1024 * 1024
        size = 4 * chunk_size + 1  # 16,777,217 bytes
        get_responses = [
            _ok_video_get(size),
            # FINALIZE returns succeeded immediately => no status polls
        ]
        post_responses = [
            _upload_response(200, {"data": {"id": "VID_SEG"}}),
            *[_upload_response(204, {}) for _ in range(5)],
            # FINALIZE - no processing_info -> fast path returns media_id
            _upload_response(200, {"data": {"id": "VID_SEG"}}),
            _upload_response(201, {"data": {"id": "TWEET_SEG"}}),
        ]
        ctx, fake_client = _patch_async_client(get_responses, post_responses)

        with ctx, patch("app.social.publisher.asyncio.sleep", new_callable=AsyncMock):
            result = await publisher.post_with_media(
                user_id="u1",
                platform="twitter",
                content="seg test",
                media_urls=["https://example.test/clip.mp4"],
                media_type="video",
            )

        assert "error" not in result, f"unexpected error: {result}"

        # Indices 0,1,2,3,4 in order, no duplicates, no skips.
        post_calls = fake_client.post.call_args_list
        append_calls = [
            c for c in post_calls if c.args[0] == "https://api.x.com/2/media/upload"
        ]
        observed = [c.kwargs["data"]["segment_index"] for c in append_calls]
        assert observed == [0, 1, 2, 3, 4], f"segment_index sequence: {observed}"

    @pytest.mark.asyncio
    async def test_video_chunked_upload_failed_state(self, caplog):
        publisher = _make_publisher_with_token()

        size_10mb = 10 * 1024 * 1024
        get_responses = [
            _ok_video_get(size_10mb),
            _status_response(
                "failed",
                error={"code": "FailedToParseVideo", "message": "ProcessFailed"},
            ),
        ]
        post_responses = [
            _upload_response(202, {"data": {"id": "VID_BAD"}}),
            _upload_response(204, {}),
            _upload_response(204, {}),
            _upload_response(204, {}),
            _upload_response(
                201,
                {
                    "data": {
                        "id": "VID_BAD",
                        "processing_info": {
                            "state": "in_progress",
                            "check_after_secs": 1,
                        },
                    }
                },
            ),
        ]
        ctx, fake_client = _patch_async_client(get_responses, post_responses)

        with (
            ctx,
            patch("app.social.publisher.asyncio.sleep", new_callable=AsyncMock),
            caplog.at_level(logging.WARNING, logger="app.social.publisher"),
        ):
            result = await publisher.post_with_media(
                user_id="u1",
                platform="twitter",
                content="failed test",
                media_urls=["https://example.test/clip.mp4"],
                media_type="video",
            )

        assert "error" in result
        assert "Twitter media upload failed" in result["error"]

        # Tweet POST must NOT be issued.
        for call in fake_client.post.call_args_list:
            assert call.args[0] != "https://api.twitter.com/2/tweets"

        log_messages = [r.getMessage() for r in caplog.records]
        joined = " | ".join(log_messages)
        assert "FailedToParseVideo" in joined
        assert "ProcessFailed" in joined

    @pytest.mark.asyncio
    async def test_video_chunked_upload_timeout(self, caplog):
        publisher = _make_publisher_with_token()

        size_10mb = 10 * 1024 * 1024
        # STATUS keeps returning in_progress; time source jumps past deadline.
        get_responses = [
            _ok_video_get(size_10mb),
            # Provide several in-progress responses; only the first will be
            # consumed because the deadline check fires before the second poll.
            *[_status_response("in_progress", check_after_secs=100) for _ in range(10)],
        ]
        post_responses = [
            _upload_response(202, {"data": {"id": "VID_SLOW"}}),
            _upload_response(204, {}),
            _upload_response(204, {}),
            _upload_response(204, {}),
            _upload_response(
                201,
                {
                    "data": {
                        "id": "VID_SLOW",
                        "processing_info": {
                            "state": "in_progress",
                            "check_after_secs": 100,
                        },
                    }
                },
            ),
        ]
        ctx, fake_client = _patch_async_client(get_responses, post_responses)

        # Fake event loop time: first call = 0 (deadline = 600), then jump
        # to 601 to trip the timeout guard on the next iteration.
        time_values = iter([0.0, 601.0, 602.0, 603.0])
        fake_loop = MagicMock()
        fake_loop.time = MagicMock(side_effect=lambda: next(time_values))

        with (
            ctx,
            patch("app.social.publisher.asyncio.sleep", new_callable=AsyncMock),
            patch(
                "app.social.publisher.asyncio.get_event_loop", return_value=fake_loop
            ),
            caplog.at_level(logging.WARNING, logger="app.social.publisher"),
        ):
            result = await publisher.post_with_media(
                user_id="u1",
                platform="twitter",
                content="slow test",
                media_urls=["https://example.test/clip.mp4"],
                media_type="video",
            )

        assert "error" in result
        assert "Twitter media upload failed" in result["error"]

        # Tweet POST must NOT be issued.
        for call in fake_client.post.call_args_list:
            assert call.args[0] != "https://api.twitter.com/2/tweets"

        log_messages = [r.getMessage() for r in caplog.records]
        assert any("timed out" in m for m in log_messages), (
            f"expected 'timed out' in logs; got: {log_messages}"
        )

    @pytest.mark.asyncio
    async def test_video_large_logs_memory_warning_but_proceeds(self, caplog):
        publisher = _make_publisher_with_token()

        # 101MB triggers the >100MB warning. 101MB / 4MB = 25.25 -> 26 chunks.
        size_101mb = 101 * 1024 * 1024
        get_responses = [_ok_video_get(size_101mb)]
        post_responses = [
            # INIT
            _upload_response(202, {"data": {"id": "VID_BIG"}}),
            # APPEND x 26
            *[_upload_response(204, {}) for _ in range(26)],
            # FINALIZE - already succeeded (no processing_info) -> skip STATUS
            _upload_response(200, {"data": {"id": "VID_BIG"}}),
            # Tweet
            _upload_response(201, {"data": {"id": "TWEET_BIG"}}),
        ]
        ctx, fake_client = _patch_async_client(get_responses, post_responses)

        with (
            ctx,
            patch("app.social.publisher.asyncio.sleep", new_callable=AsyncMock),
            caplog.at_level(logging.WARNING, logger="app.social.publisher"),
        ):
            result = await publisher.post_with_media(
                user_id="u1",
                platform="twitter",
                content="big video",
                media_urls=["https://example.test/big.mp4"],
                media_type="video",
            )

        assert "error" not in result, f"unexpected error: {result}"

        log_messages = [r.getMessage() for r in caplog.records]
        assert any(">100MB" in m for m in log_messages), (
            f"expected '>100MB' substring in warnings; got: {log_messages}"
        )

        # APPEND should be called exactly 26 times with indices 0..25.
        post_calls = fake_client.post.call_args_list
        append_calls = [
            c for c in post_calls if c.args[0] == "https://api.x.com/2/media/upload"
        ]
        assert len(append_calls) == 26
        observed = [c.kwargs["data"]["segment_index"] for c in append_calls]
        assert observed == list(range(26))
