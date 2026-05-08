# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shared fixtures for ``tests/unit/social``.

Provides ``FakeClient`` / ``FakeTable`` Supabase doubles that record
``upsert`` / ``update`` / ``delete`` payloads for the
``connected_accounts`` and ``oauth_pkce_states`` tables, plus a helper
to build a ``SocialConnector`` without invoking the real Supabase
singleton.

These fakes are deliberately minimal: they only model the column shapes
and method-chains the tests actually exercise. Add columns / methods as
new tests need them.
"""

from __future__ import annotations

from typing import Any


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
