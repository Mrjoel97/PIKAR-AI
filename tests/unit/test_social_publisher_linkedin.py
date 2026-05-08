"""Tests for LinkedIn /rest/posts migration (POST-02) + URN flow (POST-01).

Covers:
- Text post request shape (headers + body envelope)
- 3-step image upload (initializeUpload -> PUT bytes -> /rest/posts)
- 4-step video upload (initializeUpload -> chunked PUTs -> finalizeUpload -> /rest/posts)
- Lazy URN backfill when ``platform_user_id`` is null
- Error path when backfill fails (no /rest/posts call)
- Happy path skips backfill when ``platform_user_id`` is already persisted
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.social.connector import SocialConnector
from app.social.publisher import SocialPublisher

# ----------------------------------------------------------------------
# Supabase fake (connected_accounts only)
# ----------------------------------------------------------------------


class _Result:
    def __init__(self, data: list[dict[str, Any]] | None = None):
        self.data = data or []


class _FakeTable:
    def __init__(self, name: str, client: _FakeClient):
        self.name = name
        self.client = client
        self._operation: str | None = None
        self._payload: dict[str, Any] | None = None
        self._filters: list[tuple[str, Any]] = []

    def select(self, _columns: str = "*"):
        self._operation = "select"
        return self

    def update(self, payload: dict[str, Any]):
        self._operation = "update"
        self._payload = payload
        return self

    def eq(self, column: str, value: Any):
        self._filters.append((column, value))
        return self

    def execute(self):
        if self._operation == "select":
            # Return rows that match all eq() filters.
            matching = [
                row
                for row in self.client.connected_accounts
                if all(row.get(c) == v for c, v in self._filters)
            ]
            return _Result(matching)

        if self._operation == "update" and self._payload:
            # Apply the update in-memory so subsequent selects see it.
            self.client.connected_account_updates.append(
                {"payload": self._payload, "filters": list(self._filters)}
            )
            for row in self.client.connected_accounts:
                if all(row.get(c) == v for c, v in self._filters):
                    row.update(self._payload)
            return _Result()

        return _Result()


class _FakeClient:
    def __init__(self):
        self.connected_accounts: list[dict[str, Any]] = []
        self.connected_account_updates: list[dict[str, Any]] = []

    def table(self, name: str):
        return _FakeTable(name, self)


# ----------------------------------------------------------------------
# httpx.AsyncClient stand-in
# ----------------------------------------------------------------------


class _Headers(dict):
    """Case-insensitive header dict (close enough to httpx.Headers)."""

    def __init__(self, init: dict[str, str] | None = None):
        super().__init__()
        if init:
            for k, v in init.items():
                self[k.lower()] = v

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        return super().get(key.lower(), default)


class _Response:
    def __init__(
        self,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        content: bytes = b"",
        text: str = "",
    ):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = _Headers(headers)
        self.content = content
        self.text = text

    def json(self):
        return self._json


class _FakeHttpx:
    """In-memory httpx.AsyncClient stand-in.

    Tests configure ``responses`` (URL substring -> ``_Response``) per
    instance and inspect ``requests`` after the fact. ``responses`` may
    map a URL to a callable that takes the request kwargs and returns a
    ``_Response`` so multi-call URLs (e.g., per-chunk PUT) can return
    different responses.
    """

    def __init__(self, *args, **kwargs):
        self.requests: list[dict[str, Any]] = []
        self.responses: dict[str, Any] = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def _dispatch(self, url: str, request: dict[str, Any]) -> _Response:
        for key, resp in self.responses.items():
            if key in url:
                if callable(resp):
                    return resp(request)
                return resp
        return _Response(status_code=404, text=f"no mock for {url}")

    async def post(
        self,
        url: str,
        data: Any = None,
        json: Any = None,
        headers: dict | None = None,
        content: bytes | None = None,
        timeout: float | None = None,
    ):
        request = {
            "method": "POST",
            "url": url,
            "headers": dict(headers or {}),
            "data": data,
            "json": json,
            "content": content,
        }
        self.requests.append(request)
        return self._dispatch(url, request)

    async def put(
        self,
        url: str,
        content: bytes | None = None,
        data: Any = None,
        headers: dict | None = None,
        timeout: float | None = None,
    ):
        request = {
            "method": "PUT",
            "url": url,
            "headers": dict(headers or {}),
            "content": content,
            "data": data,
        }
        self.requests.append(request)
        return self._dispatch(url, request)

    async def get(
        self,
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
        timeout: float | None = None,
    ):
        request = {
            "method": "GET",
            "url": url,
            "headers": dict(headers or {}),
            "params": params or {},
        }
        self.requests.append(request)
        return self._dispatch(url, request)


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


def _make_publisher(client: _FakeClient) -> SocialPublisher:
    """Build a SocialPublisher whose connector is wired to a fake supabase."""
    connector = SocialConnector.__new__(SocialConnector)
    connector.client = client
    connector._pkce_verifiers = {}
    publisher = SocialPublisher.__new__(SocialPublisher)
    publisher.connector = connector
    return publisher


def _seed_active_account(
    client: _FakeClient,
    user_id: str = "user-1",
    platform_user_id: str | None = "782bbtaQ",
) -> None:
    client.connected_accounts.append(
        {
            "user_id": user_id,
            "platform": "linkedin",
            "status": "active",
            "platform_user_id": platform_user_id,
            "platform_username": "John Doe",
            "access_token": "enc:tok",
            "refresh_token": "enc:rtok",
        }
    )


@pytest.fixture
def fake_httpx_factory():
    """Returns a factory that constructs a single ``_FakeHttpx`` instance.

    Patching ``httpx.AsyncClient`` with this factory lets tests pre-seed
    responses on the SHARED instance returned by every constructor call.
    """

    instance = _FakeHttpx()

    def _factory(*args, **kwargs):
        return instance

    return instance, _factory


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_linkedin_text_post_request_shape(fake_httpx_factory):
    """Text-only post: /rest/posts with correct headers and body envelope."""
    client = _FakeClient()
    _seed_active_account(client, platform_user_id="782bbtaQ")
    publisher = _make_publisher(client)

    instance, factory = fake_httpx_factory
    instance.responses = {
        "rest/posts": _Response(
            status_code=201,
            headers={"x-restli-id": "urn:li:share:6844785523593134080"},
        )
    }

    publisher.connector.get_access_token = AsyncMock(return_value="ACCESS")

    with patch("httpx.AsyncClient", factory):
        result = await publisher.post_text("user-1", "linkedin", "hello world")

    assert result["success"] is True
    assert result["platform"] == "linkedin"
    assert result["post_id"] == "urn:li:share:6844785523593134080"

    # Find the /rest/posts request.
    post_calls = [r for r in instance.requests if "rest/posts" in r["url"]]
    assert len(post_calls) == 1
    call = post_calls[0]
    assert call["url"] == "https://api.linkedin.com/rest/posts"
    headers = call["headers"]
    assert headers.get("LinkedIn-Version") == "202401"
    assert headers.get("X-Restli-Protocol-Version") == "2.0.0"
    assert headers.get("Authorization") == "Bearer ACCESS"
    assert headers.get("Content-Type") == "application/json"

    body = call["json"]
    assert body == {
        "author": "urn:li:person:782bbtaQ",
        "commentary": "hello world",
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    # Text-only -> no content key.
    assert "content" not in body


@pytest.mark.asyncio
async def test_linkedin_image_post_three_step_flow(fake_httpx_factory):
    """Image post: initializeUpload -> PUT bytes -> /rest/posts."""
    client = _FakeClient()
    _seed_active_account(client, platform_user_id="782bbtaQ")
    publisher = _make_publisher(client)

    image_bytes = b"\x89PNG\r\n\x1a\nFAKEIMAGEBYTES"

    instance, factory = fake_httpx_factory
    instance.responses = {
        # Public media URL fetch.
        "https://media.example/img.png": _Response(
            status_code=200, content=image_bytes
        ),
        # initializeUpload returns uploadUrl + image URN.
        "rest/images?action=initializeUpload": _Response(
            status_code=200,
            json_data={
                "value": {
                    "uploadUrl": "https://www.linkedin.com/dms-uploads/X",
                    "image": "urn:li:image:IMG_URN",
                }
            },
        ),
        # PUT to pre-signed URL.
        "dms-uploads/X": _Response(status_code=200),
        # Final /rest/posts.
        "rest/posts": _Response(
            status_code=201,
            headers={"x-restli-id": "urn:li:share:POSTURN"},
        ),
    }

    publisher.connector.get_access_token = AsyncMock(return_value="ACCESS")

    with patch("httpx.AsyncClient", factory):
        result = await publisher.post_with_media(
            "user-1",
            "linkedin",
            "Look at this picture",
            media_urls=["https://media.example/img.png"],
            media_type="image",
        )

    assert result["success"] is True
    assert result["post_id"] == "urn:li:share:POSTURN"

    # Verify the four-step call sequence in order.
    methods_urls = [(r["method"], r["url"]) for r in instance.requests]

    # Find indexes (some calls may interleave depending on impl).
    init_idx = next(i for i, mu in enumerate(methods_urls) if "rest/images" in mu[1])
    put_idx = next(i for i, mu in enumerate(methods_urls) if "dms-uploads/X" in mu[1])
    posts_idx = next(i for i, mu in enumerate(methods_urls) if "rest/posts" in mu[1])
    get_idx = next(
        i
        for i, mu in enumerate(methods_urls)
        if mu[0] == "GET" and "media.example/img.png" in mu[1]
    )

    # The PUT must happen AFTER initializeUpload and AFTER GET media bytes,
    # and /rest/posts must happen LAST.
    assert get_idx < put_idx
    assert init_idx < put_idx
    assert put_idx < posts_idx

    # initializeUpload body must scope to the author's URN.
    init_call = instance.requests[init_idx]
    assert init_call["json"] == {
        "initializeUploadRequest": {"owner": "urn:li:person:782bbtaQ"}
    }

    # PUT to dms-uploads must NOT include Authorization.
    put_call = instance.requests[put_idx]
    assert "Authorization" not in put_call["headers"]
    assert put_call["headers"].get("Content-Type") == "application/octet-stream"
    # The PUT body == bytes returned by the GET media URL.
    assert put_call["content"] == image_bytes

    # /rest/posts body includes content.media.id == returned image URN.
    posts_call = instance.requests[posts_idx]
    body = posts_call["json"]
    assert body["content"]["media"]["id"] == "urn:li:image:IMG_URN"
    assert body["content"]["media"]["altText"]
    assert isinstance(body["content"]["media"]["altText"], str)
    assert len(body["content"]["media"]["altText"]) <= 120


@pytest.mark.asyncio
async def test_linkedin_video_post_four_step_flow(fake_httpx_factory):
    """Video post: GET -> initializeUpload -> chunked PUTs -> finalizeUpload -> /rest/posts."""
    client = _FakeClient()
    _seed_active_account(client, platform_user_id="782bbtaQ")
    publisher = _make_publisher(client)

    video_bytes = b"\x00" * 6_000_000

    # Per-instruction PUT: dispatch by URL captures correct etag.
    def _put_v0(_request):
        return _Response(status_code=200, headers={"etag": "etag0"})

    def _put_v1(_request):
        return _Response(status_code=200, headers={"etag": "etag1"})

    instance, factory = fake_httpx_factory
    instance.responses = {
        "https://media.example/vid.mp4": _Response(
            status_code=200, content=video_bytes
        ),
        "rest/videos?action=initializeUpload": _Response(
            status_code=200,
            json_data={
                "value": {
                    "video": "urn:li:video:VID_URN",
                    "uploadInstructions": [
                        {
                            "uploadUrl": "https://dms-uploads.example/v0",
                            "firstByte": 0,
                            "lastByte": 4194303,
                        },
                        {
                            "uploadUrl": "https://dms-uploads.example/v1",
                            "firstByte": 4194304,
                            "lastByte": 5999999,
                        },
                    ],
                    "uploadToken": "TOK",
                }
            },
        ),
        "dms-uploads.example/v0": _put_v0,
        "dms-uploads.example/v1": _put_v1,
        "rest/videos?action=finalizeUpload": _Response(status_code=200),
        "rest/posts": _Response(
            status_code=201,
            headers={"x-restli-id": "urn:li:share:VIDPOST"},
        ),
    }

    publisher.connector.get_access_token = AsyncMock(return_value="ACCESS")

    with patch("httpx.AsyncClient", factory):
        result = await publisher.post_with_media(
            "user-1",
            "linkedin",
            "video caption",
            media_urls=["https://media.example/vid.mp4"],
            media_type="video",
        )

    assert result["success"] is True
    assert result["post_id"] == "urn:li:share:VIDPOST"

    # initializeUpload body shape.
    init_calls = [
        r
        for r in instance.requests
        if "rest/videos?action=initializeUpload" in r["url"]
    ]
    assert len(init_calls) == 1
    assert init_calls[0]["json"] == {
        "initializeUploadRequest": {
            "owner": "urn:li:person:782bbtaQ",
            "fileSizeBytes": 6_000_000,
            "uploadCaptions": False,
            "uploadThumbnail": False,
        }
    }

    # PUT 0: bytes [0:4194304] (firstByte:lastByte+1, inclusive range).
    put0 = next(r for r in instance.requests if "v0" in r["url"])
    assert put0["content"] == video_bytes[0:4194304]
    assert "Authorization" not in put0["headers"]

    # PUT 1: bytes [4194304:6000000].
    put1 = next(r for r in instance.requests if "v1" in r["url"])
    assert put1["content"] == video_bytes[4194304:6000000]

    # finalizeUpload body has uploadedPartIds in order.
    finalize_call = next(
        r for r in instance.requests if "rest/videos?action=finalizeUpload" in r["url"]
    )
    assert finalize_call["json"] == {
        "finalizeUploadRequest": {
            "video": "urn:li:video:VID_URN",
            "uploadToken": "TOK",
            "uploadedPartIds": ["etag0", "etag1"],
        }
    }

    # /rest/posts body has content.media.id == video URN.
    posts_call = next(r for r in instance.requests if "rest/posts" in r["url"])
    body = posts_call["json"]
    assert body["content"]["media"]["id"] == "urn:li:video:VID_URN"


@pytest.mark.asyncio
async def test_linkedin_lazy_urn_backfill(fake_httpx_factory):
    """Pre-Phase-103 row (platform_user_id=None) gets backfilled on publish."""
    client = _FakeClient()
    _seed_active_account(client, platform_user_id=None)
    publisher = _make_publisher(client)

    instance, factory = fake_httpx_factory
    instance.responses = {
        "v2/userinfo": _Response(
            status_code=200,
            json_data={"sub": "BACKFILLED_SUB", "name": "Late Joiner"},
        ),
        "rest/posts": _Response(
            status_code=201,
            headers={"x-restli-id": "urn:li:share:LATE"},
        ),
    }

    publisher.connector.get_access_token = AsyncMock(return_value="ACCESS")

    with patch("httpx.AsyncClient", factory):
        result = await publisher.post_text("user-1", "linkedin", "hi")

    assert result["success"] is True

    # Userinfo GET happened.
    userinfo_calls = [r for r in instance.requests if "v2/userinfo" in r["url"]]
    assert len(userinfo_calls) == 1

    # connected_accounts row was updated with platform_user_id.
    update_payloads = [u["payload"] for u in client.connected_account_updates]
    assert any(p.get("platform_user_id") == "BACKFILLED_SUB" for p in update_payloads)

    # /rest/posts uses urn:li:person:BACKFILLED_SUB as author.
    posts_call = next(r for r in instance.requests if "rest/posts" in r["url"])
    assert posts_call["json"]["author"] == "urn:li:person:BACKFILLED_SUB"


@pytest.mark.asyncio
async def test_linkedin_post_without_urn_after_backfill_failure_returns_error(
    fake_httpx_factory,
):
    """If /v2/userinfo also fails, we surface a reconnect-required error."""
    client = _FakeClient()
    _seed_active_account(client, platform_user_id=None)
    publisher = _make_publisher(client)

    instance, factory = fake_httpx_factory
    instance.responses = {
        "v2/userinfo": _Response(status_code=500, text="boom"),
    }

    publisher.connector.get_access_token = AsyncMock(return_value="ACCESS")

    with patch("httpx.AsyncClient", factory):
        result = await publisher.post_text("user-1", "linkedin", "hi")

    assert "error" in result
    assert "reconnect" in result["error"].lower()
    # No /rest/posts call should have happened.
    assert not any("rest/posts" in r["url"] for r in instance.requests)


@pytest.mark.asyncio
async def test_linkedin_post_uses_persisted_urn_no_backfill_call(
    fake_httpx_factory,
):
    """When platform_user_id is set, /v2/userinfo MUST NOT be called."""
    client = _FakeClient()
    _seed_active_account(client, platform_user_id="EXISTING")
    publisher = _make_publisher(client)

    instance, factory = fake_httpx_factory
    instance.responses = {
        "rest/posts": _Response(
            status_code=201,
            headers={"x-restli-id": "urn:li:share:EXISTING_POST"},
        ),
    }

    publisher.connector.get_access_token = AsyncMock(return_value="ACCESS")

    with patch("httpx.AsyncClient", factory):
        result = await publisher.post_text("user-1", "linkedin", "hello again")

    assert result["success"] is True

    # No /v2/userinfo call.
    userinfo_calls = [r for r in instance.requests if "v2/userinfo" in r["url"]]
    assert userinfo_calls == []

    # Author URN uses EXISTING.
    posts_call = next(r for r in instance.requests if "rest/posts" in r["url"])
    assert posts_call["json"]["author"] == "urn:li:person:EXISTING"
