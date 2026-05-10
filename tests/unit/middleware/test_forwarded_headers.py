# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tests for ForwardedHeadersMiddleware (X-Forwarded-Proto/Host rewriting)."""

from __future__ import annotations

from typing import Any

import pytest

from app.middleware.forwarded_headers import ForwardedHeadersMiddleware


class _ScopeCapture:
    """Tiny ASGI app that captures the scope it received."""

    def __init__(self) -> None:
        self.scope: dict[str, Any] | None = None

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        self.scope = dict(scope)


def _http_scope(
    *, host: bytes = b"pikar-ai-917671810739.us-central1.run.app",
    scheme: str = "http",
    extra_headers: list[tuple[bytes, bytes]] | None = None,
) -> dict[str, Any]:
    return {
        "type": "http",
        "scheme": scheme,
        "headers": [(b"host", host), *(extra_headers or [])],
    }


@pytest.mark.asyncio
async def test_rewrites_scheme_from_x_forwarded_proto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRUST_FORWARDED_HEADERS", "1")
    capture = _ScopeCapture()
    mw = ForwardedHeadersMiddleware(capture)

    scope = _http_scope(extra_headers=[(b"x-forwarded-proto", b"https")])
    await mw(scope, lambda: None, lambda *_: None)

    assert capture.scope is not None
    assert capture.scope["scheme"] == "https"


@pytest.mark.asyncio
async def test_rewrites_host_from_x_forwarded_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRUST_FORWARDED_HEADERS", "1")
    capture = _ScopeCapture()
    mw = ForwardedHeadersMiddleware(capture)

    scope = _http_scope(
        extra_headers=[(b"x-forwarded-host", b"api.pikar-ai.com")]
    )
    await mw(scope, lambda: None, lambda *_: None)

    assert capture.scope is not None
    host_values = [v for k, v in capture.scope["headers"] if k == b"host"]
    assert host_values == [b"api.pikar-ai.com"]


@pytest.mark.asyncio
async def test_rewrites_both_together(monkeypatch: pytest.MonkeyPatch) -> None:
    """The compound Cloud Run + Cloudflare case that the middleware was written for."""
    monkeypatch.setenv("TRUST_FORWARDED_HEADERS", "1")
    capture = _ScopeCapture()
    mw = ForwardedHeadersMiddleware(capture)

    scope = _http_scope(
        scheme="http",
        host=b"pikar-ai-917671810739.us-central1.run.app",
        extra_headers=[
            (b"x-forwarded-proto", b"https"),
            (b"x-forwarded-host", b"api.pikar-ai.com"),
        ],
    )
    await mw(scope, lambda: None, lambda *_: None)

    assert capture.scope is not None
    assert capture.scope["scheme"] == "https"
    host_values = [v for k, v in capture.scope["headers"] if k == b"host"]
    assert host_values == [b"api.pikar-ai.com"]


@pytest.mark.asyncio
async def test_passthrough_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRUST_FORWARDED_HEADERS", "0")
    capture = _ScopeCapture()
    mw = ForwardedHeadersMiddleware(capture)

    scope = _http_scope(
        extra_headers=[
            (b"x-forwarded-proto", b"https"),
            (b"x-forwarded-host", b"api.pikar-ai.com"),
        ]
    )
    await mw(scope, lambda: None, lambda *_: None)

    assert capture.scope is not None
    # Disabled → scheme stays as set in scope, host stays as set in headers
    assert capture.scope["scheme"] == "http"
    host_values = [v for k, v in capture.scope["headers"] if k == b"host"]
    assert host_values == [b"pikar-ai-917671810739.us-central1.run.app"]


@pytest.mark.asyncio
async def test_passthrough_when_no_forwarded_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRUST_FORWARDED_HEADERS", "1")
    capture = _ScopeCapture()
    mw = ForwardedHeadersMiddleware(capture)

    scope = _http_scope()  # no X-Forwarded-* at all
    await mw(scope, lambda: None, lambda *_: None)

    assert capture.scope is not None
    assert capture.scope["scheme"] == "http"
    host_values = [v for k, v in capture.scope["headers"] if k == b"host"]
    assert host_values == [b"pikar-ai-917671810739.us-central1.run.app"]


@pytest.mark.asyncio
async def test_passthrough_for_non_http_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRUST_FORWARDED_HEADERS", "1")
    capture = _ScopeCapture()
    mw = ForwardedHeadersMiddleware(capture)

    scope: dict[str, Any] = {"type": "lifespan"}
    await mw(scope, lambda: None, lambda *_: None)

    assert capture.scope is not None
    assert capture.scope["type"] == "lifespan"


@pytest.mark.asyncio
async def test_takes_first_value_when_comma_chained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Some proxies chain: 'https, http' — take the first as originating scheme."""
    monkeypatch.setenv("TRUST_FORWARDED_HEADERS", "1")
    capture = _ScopeCapture()
    mw = ForwardedHeadersMiddleware(capture)

    scope = _http_scope(
        extra_headers=[
            (b"x-forwarded-proto", b"https, http"),
            (b"x-forwarded-host", b"api.pikar-ai.com, internal.example"),
        ]
    )
    await mw(scope, lambda: None, lambda *_: None)

    assert capture.scope is not None
    assert capture.scope["scheme"] == "https"
    host_values = [v for k, v in capture.scope["headers"] if k == b"host"]
    assert host_values == [b"api.pikar-ai.com"]
