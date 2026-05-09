# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Pinterest publisher tests (Plan 108-02 / HYGIENE-02).

Pinterest pin creation hits ``POST https://api.pinterest.com/v5/pins``
with a JSON body containing ``board_id``, ``title`` (<=100 chars),
``description`` (<=500 chars), and a nested ``media_source`` with
``source_type='image_url'`` and the public image URL.

Pinterest is the first platform to require a per-platform parameter
(``board_id``) that cannot be inferred from the standard publisher
arguments. Plan 108-02 introduces a generic ``extra: dict | None`` kwarg
on ``post_with_media`` (and the ``publish_to_social`` agent tool) so
callers can pass platform-specific kwargs without polluting the base
signature. The publisher returns a structured error WITHOUT issuing any
HTTP call when ``extra['board_id']`` or ``media_url`` is missing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_response(
    *,
    status_code: int = 200,
    json_payload: dict[str, Any] | None = None,
    text: str = "",
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=json_payload or {})
    resp.text = text or ""
    return resp


def _make_async_client_cm(post_side_effect: Any | None = None) -> tuple[Any, Any]:
    """Return (async_client_cm_factory, mock_client) for httpx.AsyncClient patch.

    Use as: ``patch('httpx.AsyncClient', return_value=cm)`` -- where ``cm``
    is the ContextManager-shaped object whose ``__aenter__`` yields the
    inner ``mock_client`` (an AsyncMock with .post / .get).
    """
    mock_client = MagicMock()
    mock_client.post = AsyncMock(side_effect=post_side_effect)
    mock_client.get = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm, mock_client


def _build_publisher(token: str | None = "AT-PIN"):
    """Build a SocialPublisher whose connector returns ``token`` for any user."""
    from app.social.publisher import SocialPublisher

    publisher = SocialPublisher.__new__(SocialPublisher)
    connector = MagicMock()
    connector.get_access_token = AsyncMock(return_value=token)
    publisher.connector = connector
    return publisher


# ---------------------------------------------------------------------------
# 1. Successful pin creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pinterest_post_pin_success():
    publisher = _build_publisher()
    pin_response = _mock_response(
        status_code=201,
        json_payload={
            "id": "PIN-99",
            "board_id": "BOARD_X",
            "media_source": {"images": {"originals": {"url": "https://cdn/img.jpg"}}},
        },
    )
    cm, mock_client = _make_async_client_cm(post_side_effect=[pin_response])

    with patch("httpx.AsyncClient", return_value=cm):
        result = await publisher.post_with_media(
            user_id="u1",
            platform="pinterest",
            content="my pin caption",
            media_urls=["https://cdn/img.jpg"],
            media_type="image",
            extra={"board_id": "BOARD_X"},
        )

    assert result.get("success") is True, result
    assert result["platform"] == "pinterest"
    assert result["post_id"] == "PIN-99"
    assert result["media_type"] == "image"
    assert "successfully" in result["message"].lower()

    assert mock_client.post.await_count == 1
    call = mock_client.post.await_args_list[0]
    # URL is the first positional or url= kwarg.
    url = call.args[0] if call.args else call.kwargs.get("url")
    assert url == "https://api.pinterest.com/v5/pins"

    headers = call.kwargs.get("headers") or {}
    assert headers.get("Authorization") == "Bearer AT-PIN"
    assert headers.get("Content-Type") == "application/json"

    body = call.kwargs.get("json") or {}
    assert body.get("board_id") == "BOARD_X"
    assert body.get("title") == "my pin caption"
    assert body.get("description") == "my pin caption"
    media_source = body.get("media_source") or {}
    assert media_source.get("source_type") == "image_url"
    assert media_source.get("url") == "https://cdn/img.jpg"


# ---------------------------------------------------------------------------
# 2. Title truncated to 100 chars; description to 500
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pinterest_post_truncates_long_content():
    publisher = _build_publisher()
    pin_response = _mock_response(status_code=201, json_payload={"id": "PIN-100"})
    cm, mock_client = _make_async_client_cm(post_side_effect=[pin_response])

    long_content = "X" * 200
    with patch("httpx.AsyncClient", return_value=cm):
        result = await publisher.post_with_media(
            user_id="u1",
            platform="pinterest",
            content=long_content,
            media_urls=["https://cdn/img.jpg"],
            media_type="image",
            extra={"board_id": "BOARD_X"},
        )

    assert result.get("success") is True, result
    body = mock_client.post.await_args_list[0].kwargs.get("json") or {}
    # Title cuts at 100 chars; description tolerates up to 500 (200 fits).
    assert body.get("title") == "X" * 100
    assert body.get("description") == "X" * 200


# ---------------------------------------------------------------------------
# 3. Missing board_id -> structured error, NO http call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pinterest_post_missing_board_id_returns_error_without_http():
    publisher = _build_publisher()
    cm, mock_client = _make_async_client_cm()

    with patch("httpx.AsyncClient", return_value=cm):
        result = await publisher.post_with_media(
            user_id="u1",
            platform="pinterest",
            content="cap",
            media_urls=["https://cdn/img.jpg"],
            media_type="image",
            extra={},
        )

    assert "error" in result, result
    assert "board_id" in result["error"].lower(), result["error"]
    assert mock_client.post.await_count == 0


@pytest.mark.asyncio
async def test_pinterest_post_extra_none_returns_error_without_http():
    publisher = _build_publisher()
    cm, mock_client = _make_async_client_cm()

    with patch("httpx.AsyncClient", return_value=cm):
        result = await publisher.post_with_media(
            user_id="u1",
            platform="pinterest",
            content="cap",
            media_urls=["https://cdn/img.jpg"],
            media_type="image",
            extra=None,
        )

    assert "error" in result, result
    assert "board_id" in result["error"].lower(), result["error"]
    assert mock_client.post.await_count == 0


# ---------------------------------------------------------------------------
# 4. Missing media_url -> structured error, NO http call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pinterest_post_missing_media_url_returns_error_without_http():
    publisher = _build_publisher()
    cm, mock_client = _make_async_client_cm()

    with patch("httpx.AsyncClient", return_value=cm):
        result = await publisher.post_with_media(
            user_id="u1",
            platform="pinterest",
            content="cap",
            media_urls=None,
            media_type="image",
            extra={"board_id": "BOARD_X"},
        )

    assert "error" in result, result
    assert "image" in result["error"].lower() or "media" in result["error"].lower()
    assert mock_client.post.await_count == 0


# ---------------------------------------------------------------------------
# 5. API 4xx surfaces structured error with status text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pinterest_post_api_error_surfaces():
    publisher = _build_publisher()
    err_response = _mock_response(
        status_code=400,
        json_payload={"code": 2, "message": "Invalid board_id"},
        text='{"code":2,"message":"Invalid board_id"}',
    )
    cm, mock_client = _make_async_client_cm(post_side_effect=[err_response])

    with patch("httpx.AsyncClient", return_value=cm):
        result = await publisher.post_with_media(
            user_id="u1",
            platform="pinterest",
            content="cap",
            media_urls=["https://cdn/img.jpg"],
            media_type="image",
            extra={"board_id": "BAD-BOARD"},
        )

    assert "error" in result, result
    # The shared error handler returns "Post failed (<code>): <text>".
    assert "400" in result["error"] or "failed" in result["error"].lower()
    assert mock_client.post.await_count == 1
