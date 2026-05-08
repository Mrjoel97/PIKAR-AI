"""Tests for scripts/migrate_connected_accounts_encryption.py (AUTH-02 backfill).

The script is one-time backfill that converts plaintext access_token /
refresh_token rows in public.connected_accounts to Fernet ciphertext.
Idempotent: rows that already decrypt cleanly are a no-op on every pass.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from cryptography.fernet import InvalidToken

from scripts.migrate_connected_accounts_encryption import is_already_fernet, run


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

    def select(self, _columns: str):
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
        if self.name != "connected_accounts":
            return _Result()
        if self._operation == "select":
            return _Result(self.client.connected_accounts)
        if self._operation == "update" and self._payload is not None:
            self.client.update_calls.append(
                {
                    "filters": list(self._filters),
                    "payload": dict(self._payload),
                }
            )
            return _Result([self._payload])
        return _Result()


class _FakeClient:
    def __init__(self):
        self.connected_accounts: list[dict[str, Any]] = []
        self.update_calls: list[dict[str, Any]] = []

    def table(self, name: str):
        return _FakeTable(name, self)


def _enc(value: str) -> str:
    return f"enc:{value}"


def _dec(value: str) -> str:
    if value.startswith("gAAAAA-fernet-"):
        return value.replace("gAAAAA-fernet-", "recovered-")
    raise InvalidToken


def test_dry_run_does_not_write_anything():
    client = _FakeClient()
    client.connected_accounts = [
        {
            "id": "row-a",
            "access_token": "plaintext-A",
            "refresh_token": None,
        },
        {
            "id": "row-b",
            "access_token": "gAAAAA-fernet-B",
            "refresh_token": None,
        },
    ]

    with (
        patch(
            "scripts.migrate_connected_accounts_encryption.encrypt_secret",
            side_effect=_enc,
        ),
        patch(
            "scripts.migrate_connected_accounts_encryption.decrypt_secret",
            side_effect=_dec,
        ),
    ):
        result = run(client, dry_run=True)

    assert result == {
        "total": 2,
        "already_encrypted": 1,
        "migrated": 1,
        "failed": 0,
    }
    assert client.update_calls == []


def test_apply_migrates_only_plaintext_rows():
    client = _FakeClient()
    client.connected_accounts = [
        {
            "id": "row-a",
            "access_token": "plaintext-A",
            "refresh_token": None,
        },
        {
            "id": "row-b",
            "access_token": "gAAAAA-fernet-B",
            "refresh_token": None,
        },
    ]

    with (
        patch(
            "scripts.migrate_connected_accounts_encryption.encrypt_secret",
            side_effect=_enc,
        ),
        patch(
            "scripts.migrate_connected_accounts_encryption.decrypt_secret",
            side_effect=_dec,
        ),
    ):
        result = run(client, dry_run=False)

    assert result == {
        "total": 2,
        "already_encrypted": 1,
        "migrated": 1,
        "failed": 0,
    }
    assert len(client.update_calls) == 1
    call = client.update_calls[0]
    assert ("id", "row-a") in call["filters"]
    assert call["payload"] == {"access_token": "enc:plaintext-A"}


def test_apply_is_idempotent_on_already_encrypted_rows():
    client = _FakeClient()
    client.connected_accounts = [
        {
            "id": "row-b",
            "access_token": "gAAAAA-fernet-B",
            "refresh_token": None,
        },
    ]

    with (
        patch(
            "scripts.migrate_connected_accounts_encryption.encrypt_secret",
            side_effect=_enc,
        ),
        patch(
            "scripts.migrate_connected_accounts_encryption.decrypt_secret",
            side_effect=_dec,
        ),
    ):
        first = run(client, dry_run=False)
        second = run(client, dry_run=False)

    assert first == {
        "total": 1,
        "already_encrypted": 1,
        "migrated": 0,
        "failed": 0,
    }
    assert second == first
    assert client.update_calls == []


def test_is_already_fernet_treats_none_as_nothing_to_do():
    # Defensive smoke: None (no token stored) MUST NOT trigger an encrypt.
    with patch(
        "scripts.migrate_connected_accounts_encryption.decrypt_secret",
        side_effect=AssertionError("decrypt should not be called for None"),
    ):
        assert is_already_fernet(None) is True
        assert is_already_fernet("") is True


def test_is_already_fernet_returns_false_on_invalid_token():
    with patch(
        "scripts.migrate_connected_accounts_encryption.decrypt_secret",
        side_effect=InvalidToken,
    ):
        assert is_already_fernet("plaintext") is False


def test_is_already_fernet_propagates_runtime_error():
    with (
        patch(
            "scripts.migrate_connected_accounts_encryption.decrypt_secret",
            side_effect=RuntimeError("ADMIN_ENCRYPTION_KEY missing"),
        ),
        pytest.raises(RuntimeError),
    ):
        is_already_fernet("anything")
