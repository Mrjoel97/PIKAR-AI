# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Targeted helper-method tests on SocialConnector (Plan 108-04 backfill).

Covers branches not exercised by the platform-level callback / publisher
tests:

- ``_decrypt_token``: empty input, gAAAAA-prefixed Fernet token (logs +
  None), legacy plaintext (warns + returns), RuntimeError (no encryption
  configured), generic Exception fallthrough.
- ``_fetch_linkedin_identity``: HTTP error, non-200, malformed JSON,
  successful sub+name path.
- ``_fetch_platform_profile``: per-platform success (linkedin via
  delegation, twitter, facebook, instagram, tiktok, youtube),
  unsupported platform short-circuit, profile-call exception path,
  empty-data branch.
- ``revoke_connection`` sync wrapper invoked from inside a running
  event loop (thread-pool fallback).
- ``_revoke_at_provider`` for an unknown platform.
- ``_get_supabase`` test (calls singleton).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from cryptography.fernet import InvalidToken

from app.social.connector import SocialConnector
from tests.unit.social.conftest import FakeClient, make_connector


# ---------------------------------------------------------------------------
# _decrypt_token
# ---------------------------------------------------------------------------


def test_decrypt_token_none_returns_none():
    connector = make_connector(FakeClient())
    assert connector._decrypt_token(None) is None
    assert connector._decrypt_token("") is None


def test_decrypt_token_invalid_fernet_returns_none_for_encrypted_prefix():
    connector = make_connector(FakeClient())
    with patch(
        "app.social.connector.decrypt_secret",
        side_effect=InvalidToken("bad"),
    ):
        result = connector._decrypt_token("gAAAAA-something-encrypted")
    assert result is None


def test_decrypt_token_invalid_fernet_legacy_returns_plaintext():
    connector = make_connector(FakeClient())
    with patch(
        "app.social.connector.decrypt_secret",
        side_effect=InvalidToken("bad"),
    ):
        # Legacy plaintext token (no gAAAAA prefix) -- returns as-is
        result = connector._decrypt_token("legacy-plain-token")
    assert result == "legacy-plain-token"


def test_decrypt_token_runtime_error_returns_none():
    connector = make_connector(FakeClient())
    with patch(
        "app.social.connector.decrypt_secret",
        side_effect=RuntimeError("encryption not configured"),
    ):
        result = connector._decrypt_token("gAAAAA-x")
    assert result is None


def test_decrypt_token_generic_exception_returns_none():
    connector = make_connector(FakeClient())
    with patch(
        "app.social.connector.decrypt_secret",
        side_effect=ValueError("unexpected"),
    ):
        result = connector._decrypt_token("gAAAAA-x")
    assert result is None


# ---------------------------------------------------------------------------
# _fetch_linkedin_identity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_linkedin_identity_success():
    connector = make_connector(FakeClient())

    fake_resp = MagicMock(status_code=200)
    fake_resp.json = MagicMock(return_value={"sub": "abc", "name": "Alice"})
    http = MagicMock()
    http.get = AsyncMock(return_value=fake_resp)

    sub, name = await connector._fetch_linkedin_identity(http, "AT")
    assert sub == "abc"
    assert name == "Alice"


@pytest.mark.asyncio
async def test_fetch_linkedin_identity_uses_given_name_fallback():
    connector = make_connector(FakeClient())

    fake_resp = MagicMock(status_code=200)
    fake_resp.json = MagicMock(return_value={"sub": "abc", "given_name": "Bob"})
    http = MagicMock()
    http.get = AsyncMock(return_value=fake_resp)

    sub, name = await connector._fetch_linkedin_identity(http, "AT")
    assert sub == "abc"
    assert name == "Bob"


@pytest.mark.asyncio
async def test_fetch_linkedin_identity_http_error_returns_none_none():
    connector = make_connector(FakeClient())

    http = MagicMock()
    http.get = AsyncMock(side_effect=httpx.RequestError("dns"))

    sub, name = await connector._fetch_linkedin_identity(http, "AT")
    assert (sub, name) == (None, None)


@pytest.mark.asyncio
async def test_fetch_linkedin_identity_non_200_returns_none_none():
    connector = make_connector(FakeClient())

    fake_resp = MagicMock(status_code=500, text="error")
    http = MagicMock()
    http.get = AsyncMock(return_value=fake_resp)

    sub, name = await connector._fetch_linkedin_identity(http, "AT")
    assert (sub, name) == (None, None)


@pytest.mark.asyncio
async def test_fetch_linkedin_identity_malformed_json_returns_none_none():
    connector = make_connector(FakeClient())

    fake_resp = MagicMock(status_code=200)
    fake_resp.json = MagicMock(side_effect=ValueError("not json"))
    http = MagicMock()
    http.get = AsyncMock(return_value=fake_resp)

    sub, name = await connector._fetch_linkedin_identity(http, "AT")
    assert (sub, name) == (None, None)


# ---------------------------------------------------------------------------
# _fetch_platform_profile
# ---------------------------------------------------------------------------


def _make_resp(status: int, payload: Any = None) -> MagicMock:
    resp = MagicMock(status_code=status)
    resp.text = ""
    resp.json = MagicMock(return_value=payload or {})
    return resp


@pytest.mark.asyncio
async def test_fetch_platform_profile_linkedin_delegates():
    connector = make_connector(FakeClient())
    connector._fetch_linkedin_identity = AsyncMock(return_value=("X-1", "X Name"))
    http = MagicMock()
    sub, name = await connector._fetch_platform_profile("linkedin", "AT", http)
    assert (sub, name) == ("X-1", "X Name")


@pytest.mark.asyncio
async def test_fetch_platform_profile_twitter_success():
    connector = make_connector(FakeClient())
    http = MagicMock()
    http.get = AsyncMock(
        return_value=_make_resp(
            200, {"data": {"id": "T-1", "username": "alice"}}
        )
    )
    sub, name = await connector._fetch_platform_profile("twitter", "AT", http)
    assert (sub, name) == ("T-1", "alice")


@pytest.mark.asyncio
async def test_fetch_platform_profile_facebook_success():
    connector = make_connector(FakeClient())
    http = MagicMock()
    http.get = AsyncMock(
        return_value=_make_resp(200, {"id": "FB-1", "name": "Page"})
    )
    sub, name = await connector._fetch_platform_profile("facebook", "AT", http)
    assert (sub, name) == ("FB-1", "Page")


@pytest.mark.asyncio
async def test_fetch_platform_profile_instagram_walks_pages():
    connector = make_connector(FakeClient())
    http = MagicMock()
    http.get = AsyncMock(
        return_value=_make_resp(
            200,
            {
                "data": [
                    {},  # first page lacks instagram_business_account
                    {
                        "instagram_business_account": {
                            "id": "IG-99",
                            "username": "ig_handle",
                        }
                    },
                ]
            },
        )
    )
    sub, name = await connector._fetch_platform_profile("instagram", "AT", http)
    assert (sub, name) == ("IG-99", "ig_handle")


@pytest.mark.asyncio
async def test_fetch_platform_profile_tiktok_returns_open_id_no_username():
    connector = make_connector(FakeClient())
    http = MagicMock()
    http.get = AsyncMock(
        return_value=_make_resp(200, {"data": {"user": {"open_id": "TT-1"}}})
    )
    sub, name = await connector._fetch_platform_profile("tiktok", "AT", http)
    assert (sub, name) == ("TT-1", None)


@pytest.mark.asyncio
async def test_fetch_platform_profile_youtube_success():
    connector = make_connector(FakeClient())
    http = MagicMock()
    http.get = AsyncMock(
        return_value=_make_resp(
            200,
            {"items": [{"id": "CH-1", "snippet": {"title": "MyChannel"}}]},
        )
    )
    sub, name = await connector._fetch_platform_profile("youtube", "AT", http)
    assert (sub, name) == ("CH-1", "MyChannel")


@pytest.mark.asyncio
async def test_fetch_platform_profile_unsupported_platform_returns_none():
    connector = make_connector(FakeClient())
    http = MagicMock()
    sub, name = await connector._fetch_platform_profile("threads", "AT", http)
    assert (sub, name) == (None, None)


@pytest.mark.asyncio
async def test_fetch_platform_profile_non_200_logs_and_returns_none():
    connector = make_connector(FakeClient())
    http = MagicMock()
    http.get = AsyncMock(return_value=_make_resp(500))
    sub, name = await connector._fetch_platform_profile("twitter", "AT", http)
    assert (sub, name) == (None, None)


@pytest.mark.asyncio
async def test_fetch_platform_profile_http_exception_returns_none_none():
    connector = make_connector(FakeClient())
    http = MagicMock()
    http.get = AsyncMock(side_effect=httpx.RequestError("dns"))
    sub, name = await connector._fetch_platform_profile("twitter", "AT", http)
    assert (sub, name) == (None, None)


# ---------------------------------------------------------------------------
# _revoke_at_provider unknown platform
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revoke_at_provider_unknown_platform_returns_error():
    connector = make_connector(FakeClient())
    ok, err = await connector._revoke_at_provider("not-a-platform", "TOK")
    assert ok is False
    assert err is not None
    assert "unknown_platform" in err


# ---------------------------------------------------------------------------
# revoke_connection sync wrapper from inside a running loop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revoke_connection_inside_running_loop_uses_thread_pool(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "li-id")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "li-sec")
    client = FakeClient()
    connector = make_connector(client)
    client.connected_accounts.append(
        {
            "user_id": "u1",
            "platform": "linkedin",
            "status": "active",
            "access_token": None,
            "refresh_token": None,
            "token_expires_at": None,
        }
    )

    # Called from inside an async test (running loop) -- must use the
    # thread-pool bridge in revoke_connection.
    result = connector.revoke_connection("u1", "linkedin")
    assert result["success"] is True
    assert result["platform"] == "linkedin"


# ---------------------------------------------------------------------------
# _get_supabase falls through to the singleton in production but here
# we just exercise the branch via __init__ being skipped in our fakes.
# ---------------------------------------------------------------------------


def test_get_supabase_calls_get_service_client():
    with patch(
        "app.social.connector.get_service_client",
        return_value=MagicMock(name="supabase"),
    ) as mock_factory:
        connector = SocialConnector()
        assert mock_factory.called
        assert connector.client is mock_factory.return_value
