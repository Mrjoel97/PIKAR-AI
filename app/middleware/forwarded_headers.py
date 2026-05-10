# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""ASGI middleware that honors X-Forwarded-* headers from trusted upstream proxies.

Why this exists:
    pikar-ai runs on Cloud Run behind a Cloudflare Worker that forwards
    upstream with the bare ``*.run.app`` URL as the Host header (so Cloud
    Run accepts the request). Without correcting the scope, Starlette's
    ``request.base_url`` produces ``http://pikar-ai-NNN.us-central1.run.app/``
    instead of the externally-visible ``https://api.pikar-ai.com/`` — which
    breaks OAuth redirect URIs (Google rejects with redirect_uri_mismatch),
    signed-URL generation, webhook callback construction, and anything
    else that builds a public URL from ``request.url``.

What this does:
    Rewrites the ASGI scope BEFORE Starlette materializes the Request:
      - ``X-Forwarded-Proto`` → ``scope["scheme"]``
      - ``X-Forwarded-Host``  → replace the ``host`` header in scope
      - ``X-Forwarded-Port``  → not honored separately; trust the host
        header's :port if present
      - ``X-Forwarded-For``   → not handled here (uvicorn's built-in
        ProxyHeadersMiddleware already handles client IP for loopback;
        rate limiters in this codebase parse this header directly)

Why pure ASGI and not BaseHTTPMiddleware:
    BaseHTTPMiddleware runs after Starlette wraps the scope into a
    Request, which is already too late — downstream code that reads
    ``request.base_url`` sees the un-rewritten host. A raw ASGI app
    mutates ``scope`` before any Request is built.

Security:
    When enabled, any client able to reach the container directly (e.g.,
    the public ``*.run.app`` URL with ``--allow-unauthenticated`` set) can
    spoof these headers. Mitigations:
      - Block direct ingress at the Cloud Run service (``--ingress=
        internal-and-cloud-load-balancing``).
      - Require a shared-secret header from the trusted upstream and
        validate it here before honoring X-Forwarded-*.
      - Disable entirely with ``TRUST_FORWARDED_HEADERS=0``.

    For the current pikar-ai threat model, OAuth redirect URIs are
    constrained by Google's authorized-list match (a spoofed redirect_uri
    that isn't in the OAuth client's allow-list is rejected), so the
    exposure is bounded.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable

from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)


def _is_enabled() -> bool:
    """Default-on; set TRUST_FORWARDED_HEADERS=0 to disable."""
    return os.environ.get("TRUST_FORWARDED_HEADERS", "1").strip() not in {"0", "false", "False", ""}


def _get_header(headers: Iterable[tuple[bytes, bytes]], name: bytes) -> bytes | None:
    """Return the first matching header value (case-insensitive)."""
    name_lower = name.lower()
    for key, value in headers:
        if key.lower() == name_lower:
            return value
    return None


def _replace_host_header(
    headers: list[tuple[bytes, bytes]], new_host: bytes
) -> list[tuple[bytes, bytes]]:
    """Return a new headers list with the host header replaced."""
    replaced = False
    out: list[tuple[bytes, bytes]] = []
    for key, value in headers:
        if key.lower() == b"host":
            if not replaced:
                out.append((b"host", new_host))
                replaced = True
        else:
            out.append((key, value))
    if not replaced:
        out.append((b"host", new_host))
    return out


class ForwardedHeadersMiddleware:
    """ASGI middleware that rewrites scope based on X-Forwarded-* headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.enabled = _is_enabled()
        if not self.enabled:
            logger.info(
                "ForwardedHeadersMiddleware DISABLED via TRUST_FORWARDED_HEADERS env var"
            )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.enabled or scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers: list[tuple[bytes, bytes]] = list(scope.get("headers", []))

        # X-Forwarded-Proto → scope["scheme"]
        proto = _get_header(headers, b"x-forwarded-proto")
        if proto:
            # Multiple proxies may comma-join; take the first (originating client).
            scheme = proto.decode("latin-1").split(",")[0].strip().lower()
            if scheme in {"http", "https", "ws", "wss"}:
                scope["scheme"] = scheme

        # X-Forwarded-Host → replace Host header so request.base_url sees it
        forwarded_host = _get_header(headers, b"x-forwarded-host")
        if forwarded_host:
            new_host = forwarded_host.split(b",")[0].strip()
            if new_host:
                scope["headers"] = _replace_host_header(headers, new_host)

        await self.app(scope, receive, send)
