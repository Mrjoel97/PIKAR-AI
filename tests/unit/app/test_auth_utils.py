from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.app_utils import auth as auth_module


def _build_request(headers: dict[str, str] | None = None) -> Request:
    headers = headers or {}
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in headers.items()
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_get_current_user_id_uses_shared_verify_token(monkeypatch):
    credentials = MagicMock()
    verify_mock = AsyncMock(return_value={"id": "user-123", "email": "user@test.com"})
    monkeypatch.setattr(auth_module, "verify_token", verify_mock)

    user = await auth_module.get_current_user(credentials)
    user_id = await auth_module.get_current_user_id(user)

    assert user_id == "user-123"
    verify_mock.assert_awaited_once_with(credentials)


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_missing_id():
    with pytest.raises(HTTPException) as excinfo:
        await auth_module.get_current_user_id({})

    assert excinfo.value.status_code == 401


def test_resolve_request_user_id_prefers_bearer_token(monkeypatch):
    request = _build_request(
        {
            "Authorization": "Bearer real-token",
            "x-user-id": "spoofed-header-user",
        }
    )
    request.state.user_id = "spoofed-state-user"

    monkeypatch.setattr(
        auth_module, "get_user_id_from_token", lambda token: "jwt-user-123"
    )

    assert auth_module.resolve_request_user_id(request) == "jwt-user-123"


def test_resolve_request_user_id_disables_header_fallback_for_invalid_bearer(
    monkeypatch,
):
    request = _build_request(
        {
            "Authorization": "Bearer broken-token",
            "x-user-id": "spoofed-header-user",
        }
    )
    request.state.user_id = "spoofed-state-user"

    monkeypatch.setattr(auth_module, "get_user_id_from_token", lambda token: None)

    assert (
        auth_module.resolve_request_user_id(
            request, allow_header_fallback=False
        )
        is None
    )


def test_resolve_request_user_id_uses_header_fallback_without_bearer(monkeypatch):
    request = _build_request({"x-user-id": "header-user-123"})

    monkeypatch.setattr(
        auth_module,
        "get_user_id_from_token",
        lambda token: (_ for _ in ()).throw(AssertionError("should not decode token")),
    )

    assert auth_module.resolve_request_user_id(request) == "header-user-123"


@pytest.mark.asyncio
async def test_verify_token_skips_local_hs256_verification_for_es256_tokens(monkeypatch):
    credentials = MagicMock(credentials="es256-token")
    user = MagicMock(
        id="user-123",
        email="joel@pikar-ai.com",
        user_metadata={},
        app_metadata={"provider": "google"},
        role="authenticated",
    )
    user_response = MagicMock(user=user)
    supabase_client = MagicMock()
    supabase_client.auth.get_user.return_value = user_response

    def fail_decode(*args, **kwargs):
        raise AssertionError("jwt.decode should not run for ES256 tokens")

    monkeypatch.setenv("SUPABASE_JWT_SECRET", "legacy-hs256-secret")
    monkeypatch.setattr(auth_module.jwt, "get_unverified_header", lambda token: {"alg": "ES256"})
    monkeypatch.setattr(auth_module.jwt, "decode", fail_decode)
    monkeypatch.setattr(auth_module, "get_supabase_client", lambda: supabase_client)

    result = await auth_module.verify_token(credentials)

    assert result["id"] == "user-123"
    supabase_client.auth.get_user.assert_called_once_with("es256-token")
