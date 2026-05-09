# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""PKCE state utility tests for SocialConnector (Plan 108-04 / HYGIENE-04).

Covers:

- ``_generate_pkce`` produces a token_urlsafe verifier and an unpadded
  base64url(sha256) S256 challenge.
- ``_store_pkce_verifier`` + ``_pop_pkce_verifier`` round-trip via the
  supabase mock; pop deletes the row.
- Expired verifier returns ``None`` (and the row is deleted by pop).
- Wrong platform on pop returns ``None``.
- supabase write failure falls back to the in-memory ``_pkce_verifiers``
  dict.
- supabase read failure falls back to the in-memory dict.
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from tests.unit.social.conftest import FakeClient, make_connector


def test_generate_pkce_produces_s256_challenge():
    client = FakeClient()
    connector = make_connector(client)

    verifier, challenge = connector._generate_pkce()

    # Verifier should be a urlsafe string, long enough for high entropy.
    assert len(verifier) >= 64

    # Challenge must equal base64url(sha256(verifier)) without padding.
    digest = hashlib.sha256(verifier.encode()).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    assert challenge == expected
    # No padding ('=') in the challenge.
    assert "=" not in challenge


def test_store_and_pop_pkce_verifier_round_trip_via_supabase():
    client = FakeClient()
    connector = make_connector(client)

    with (
        patch(
            "app.social.connector.encrypt_secret",
            side_effect=lambda v: f"enc:{v}",
        ),
        patch(
            "app.social.connector.decrypt_secret",
            side_effect=lambda v: (
                v.removeprefix("enc:") if isinstance(v, str) else v
            ),
        ),
    ):
        connector._store_pkce_verifier("state-1", "user-1", "twitter", "ver-A")

        # Row landed in supabase fake
        assert "state-1" in client.pkce_states
        assert client.pkce_states["state-1"]["code_verifier"] == "enc:ver-A"

        # Pop returns the decrypted verifier and removes the row
        result = connector._pop_pkce_verifier("state-1", "twitter")

    assert result == "ver-A"
    assert "state-1" not in client.pkce_states


def test_pop_pkce_verifier_expired_returns_none():
    client = FakeClient()
    connector = make_connector(client)

    # Pre-load an expired row directly
    client.pkce_states["state-2"] = {
        "state": "state-2",
        "user_id": "user-1",
        "platform": "twitter",
        "code_verifier": "enc:ver-B",
        "expires_at": (
            datetime.now(timezone.utc) - timedelta(minutes=5)
        ).isoformat(),
    }

    with patch(
        "app.social.connector.decrypt_secret",
        side_effect=lambda v: v.removeprefix("enc:") if isinstance(v, str) else v,
    ):
        result = connector._pop_pkce_verifier("state-2", "twitter")

    assert result is None


def test_pop_pkce_verifier_wrong_platform_returns_none():
    client = FakeClient()
    connector = make_connector(client)

    client.pkce_states["state-3"] = {
        "state": "state-3",
        "user_id": "user-1",
        "platform": "twitter",
        "code_verifier": "enc:ver-C",
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(minutes=10)
        ).isoformat(),
    }

    with patch(
        "app.social.connector.decrypt_secret",
        side_effect=lambda v: v.removeprefix("enc:") if isinstance(v, str) else v,
    ):
        result = connector._pop_pkce_verifier("state-3", "linkedin")

    assert result is None


def test_store_pkce_verifier_falls_back_to_in_memory_on_db_error():
    client = FakeClient()
    connector = make_connector(client)

    # Force the supabase upsert path to raise
    def _broken_table(_name):
        raise RuntimeError("supabase down")

    with patch.object(client, "table", side_effect=_broken_table):
        connector._store_pkce_verifier("state-4", "user-1", "twitter", "ver-D")

    # Verifier landed in the local in-memory dict instead
    assert connector._pkce_verifiers.get("state-4") == "ver-D"


def test_pop_pkce_verifier_in_memory_fallback():
    client = FakeClient()
    connector = make_connector(client)

    # Pre-seed the in-memory dict (simulating a previous fallback write)
    connector._pkce_verifiers["state-5"] = "ver-E"

    # Force the supabase read path to raise so we hit the fallback branch
    def _broken_table(_name):
        raise RuntimeError("supabase down")

    with patch.object(client, "table", side_effect=_broken_table):
        result = connector._pop_pkce_verifier("state-5", "twitter")

    assert result == "ver-E"
    # Pop also removes the in-memory entry
    assert "state-5" not in connector._pkce_verifiers
