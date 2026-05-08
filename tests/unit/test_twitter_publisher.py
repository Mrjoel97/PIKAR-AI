"""Tests for Twitter publisher v2 media upload (Phase 104, POST-04).

Wave-0 RED tests asserting the desired behavior of ``_upload_image_twitter``
and the dispatching Twitter branch in ``post_with_media``. These fail until
Wave-1 lands the implementation in :mod:`app.social.publisher`.
"""

from __future__ import annotations

import logging
from pathlib import Path
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
    """POST-05 stub: video path returns 'not yet available' until 104-02."""

    @pytest.mark.asyncio
    async def test_video_path_returns_not_yet_available_error(self):
        publisher = _make_publisher_with_token()

        # No HTTP calls expected - the dispatch should raise NotImplementedError
        # from the stub and the branch should catch it. We still need an
        # AsyncClient context though.
        get_responses: list = []
        post_responses: list = []
        ctx, fake_client = _patch_async_client(get_responses, post_responses)

        with ctx:
            result = await publisher.post_with_media(
                user_id="u1",
                platform="twitter",
                content="video please",
                media_urls=["https://example.test/clip.mp4"],
                media_type="video",
            )

        assert "error" in result
        assert "not yet available" in result["error"].lower()

        # Tweet POST must NOT be attempted.
        for call in fake_client.post.call_args_list:
            assert call.args[0] != "https://api.twitter.com/2/tweets"
