# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shared fixtures for ``tests/unit/social``.

Provides ``FakeClient`` / ``FakeTable`` Supabase doubles that record
``upsert`` / ``update`` / ``delete`` payloads for the
``connected_accounts`` and ``oauth_pkce_states`` tables, plus a helper
to build a ``SocialConnector`` without invoking the real Supabase
singleton.

Also exposes Plan 107-01 fixtures (``fake_page_id``, ``fake_page_token``,
``fake_user_id``, ``mp4_bytes``) and multipart-form-field extraction
helpers used by the Facebook three-phase video upload tests.

These fakes are deliberately minimal: they only model the column shapes
and method-chains the tests actually exercise. Add columns / methods as
new tests need them.
"""

from __future__ import annotations

import re
from typing import Any

import httpx
import pytest


class _Result:
    """Stand-in for the ``execute()`` result returned by supabase-py."""

    def __init__(self, data: list[dict[str, Any]] | None = None):
        self.data = data or []


class FakeTable:
    """Minimal in-memory ``connected_accounts`` / ``oauth_pkce_states`` table."""

    def __init__(self, name: str, client: FakeClient):
        self.name = name
        self.client = client
        self._operation: str | None = None
        self._payload: dict[str, Any] | None = None
        self._filters: list[tuple[str, Any]] = []

    def select(self, _columns: str):
        self._operation = "select"
        return self

    def update(self, payload: dict[str, Any]):
        self._operation = "update"
        self._payload = payload
        return self

    def upsert(self, payload: dict[str, Any], on_conflict: str | None = None):
        self._operation = "upsert"
        self._payload = payload
        return self

    def delete(self):
        self._operation = "delete"
        return self

    def eq(self, column: str, value: Any):
        self._filters.append((column, value))
        return self

    def limit(self, _n: int):
        return self

    def execute(self):
        if self.name == "connected_accounts":
            return self._execute_connected_accounts()
        if self.name == "oauth_pkce_states":
            return self._execute_pkce_states()
        return _Result()

    def _execute_connected_accounts(self) -> _Result:
        if self._operation == "select":
            return _Result(list(self.client.connected_accounts))
        if self._operation == "update" and self._payload:
            self.client.connected_account_updates.append(dict(self._payload))
            for row in self.client.connected_accounts:
                row.update(self._payload)
            return _Result(list(self.client.connected_accounts))
        if self._operation == "upsert" and self._payload:
            self.client.connected_account_upserts.append(dict(self._payload))
            return _Result([dict(self._payload)])
        return _Result()

    def _execute_pkce_states(self) -> _Result:
        if self._operation == "select":
            state = next((v for c, v in self._filters if c == "state"), None)
            row = self.client.pkce_states.get(state) if state is not None else None
            return _Result([dict(row)] if row else [])
        if self._operation == "upsert" and self._payload:
            state = self._payload.get("state")
            if state is not None:
                self.client.pkce_states[state] = dict(self._payload)
            return _Result([dict(self._payload)])
        if self._operation == "delete":
            state = next((v for c, v in self._filters if c == "state"), None)
            if state is not None:
                self.client.pkce_states.pop(state, None)
            return _Result()
        return _Result()


class FakeClient:
    """Minimal Supabase client double for social-connector tests."""

    def __init__(self):
        self.connected_accounts: list[dict[str, Any]] = []
        self.connected_account_updates: list[dict[str, Any]] = []
        self.connected_account_upserts: list[dict[str, Any]] = []
        self.pkce_states: dict[str, dict[str, Any]] = {}

    def table(self, name: str):
        return FakeTable(name, self)


def make_connector(client: FakeClient):
    """Build a ``SocialConnector`` bound to ``client`` without Supabase IO."""
    from app.social.connector import SocialConnector

    connector = SocialConnector.__new__(SocialConnector)
    connector.client = client
    connector._pkce_verifiers = {}
    return connector


# ---------------------------------------------------------------------------
# Plan 107-01: Facebook three-phase video upload fixtures + helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_page_id() -> str:
    """Stand-in Facebook Page ID used by Plan 107-01 unit tests."""
    return "PAGE_1234567890"


@pytest.fixture
def fake_page_token() -> str:
    """Stand-in Page access token used by Plan 107-01 unit tests."""
    return "EAAG_FAKE_PAGE_ACCESS_TOKEN"


@pytest.fixture
def fake_user_id() -> str:
    """Stand-in Pikar user UUID for connected_accounts row lookups."""
    return "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def mp4_bytes() -> bytes:
    """10 MB of zero bytes -- stand-in for a 30s 1080p MP4 (typically 5-15 MB)."""
    return b"\x00" * (10 * 1024 * 1024)


def extract_upload_phase(request: httpx.Request) -> str:
    """Return the ``upload_phase`` form field value from a request body.

    Handles both multipart (``files=`` on the httpx call) and
    ``application/x-www-form-urlencoded`` (``data=`` only) bodies. Returns an
    empty string when the field is absent so test assertions fail loudly
    rather than silently passing.
    """
    return extract_form_field(request, "upload_phase")


def extract_form_field(request: httpx.Request, field_name: str) -> str:
    """Return the value of a named text form field from a request body.

    Handles both multipart and URL-encoded encodings.
    """
    body = request.content if request.content else b""
    if not body:
        return ""

    # Multipart shape: ``name="<field>"\r\n\r\n<value>\r\n``
    multipart_re = (
        rb'name="' + re.escape(field_name.encode()) + rb'"\r?\n\r?\n([^\r\n]+)'
    )
    match = re.search(multipart_re, body)
    if match:
        return match.group(1).decode()

    # URL-encoded shape: ``<field>=<value>&...`` (urlencoded values).
    from urllib.parse import parse_qs

    try:
        decoded = body.decode("utf-8", errors="replace")
    except Exception:
        return ""
    parsed = parse_qs(decoded, keep_blank_values=True)
    values = parsed.get(field_name)
    return values[0] if values else ""
