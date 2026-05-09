# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for app.social.linkedin_webhook (Plan 108-04 / HYGIENE-04 backfill).

Covers:

- ``verify_signature``: missing secret, missing/malformed header,
  valid HMAC match, mismatch.
- ``store_webhook_event``: row shape upserted into
  ``social_webhook_events``.
- ``resolve_user_from_event``: payload shapes (top-level vs nested),
  hit / miss in connected_accounts.
- ``extract_event_type`` / ``extract_organization_id``: payload shape
  precedence (``eventType`` over ``type``; ``data.organization`` over
  ``organizationId``).
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# verify_signature
# ---------------------------------------------------------------------------


def test_verify_signature_missing_secret_returns_false(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("LINKEDIN_CLIENT_SECRET", raising=False)
    from app.social import linkedin_webhook

    assert linkedin_webhook.verify_signature(b"x", "hmacsha256=abc") is False


def test_verify_signature_missing_header_returns_false(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "secret")
    from app.social import linkedin_webhook

    assert linkedin_webhook.verify_signature(b"x", "") is False
    assert linkedin_webhook.verify_signature(b"x", "wrong=abc") is False


def test_verify_signature_valid_match_returns_true(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "secret")
    from app.social import linkedin_webhook

    payload = b"hello world"
    expected = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()
    assert linkedin_webhook.verify_signature(payload, f"hmacsha256={expected}") is True


def test_verify_signature_mismatch_returns_false(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "secret")
    from app.social import linkedin_webhook

    assert linkedin_webhook.verify_signature(b"x", "hmacsha256=deadbeef") is False


# ---------------------------------------------------------------------------
# store_webhook_event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_webhook_event_inserts_row():
    from app.social import linkedin_webhook

    fake_client = MagicMock()
    fake_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "evt-1", "platform": "linkedin"}]
    )
    with patch.object(linkedin_webhook, "get_service_client", return_value=fake_client):
        result = await linkedin_webhook.store_webhook_event(
            "MEMBER_SOCIAL_ACTION",
            {"foo": "bar"},
            user_id="u1",
            organization_id="urn:li:organization:99",
        )
    assert result["id"] == "evt-1"
    insert_call = fake_client.table.return_value.insert.call_args.args[0]
    assert insert_call["platform"] == "linkedin"
    assert insert_call["event_type"] == "MEMBER_SOCIAL_ACTION"
    assert insert_call["user_id"] == "u1"
    assert insert_call["linkedin_org_id"] == "urn:li:organization:99"
    assert insert_call["status"] == "pending"


@pytest.mark.asyncio
async def test_store_webhook_event_no_data_returns_empty_dict():
    from app.social import linkedin_webhook

    fake_client = MagicMock()
    fake_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[]
    )
    with patch.object(linkedin_webhook, "get_service_client", return_value=fake_client):
        result = await linkedin_webhook.store_webhook_event(
            "SHARE", {"foo": "bar"}
        )
    assert result == {}


# ---------------------------------------------------------------------------
# resolve_user_from_event
# ---------------------------------------------------------------------------


def test_resolve_user_from_event_nested_actor_finds_user():
    from app.social import linkedin_webhook

    fake_client = MagicMock()
    fake_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"user_id": "u-99"}]
    )
    with patch.object(linkedin_webhook, "get_service_client", return_value=fake_client):
        uid = linkedin_webhook.resolve_user_from_event(
            {"data": {"actor": "urn:li:person:ABC"}}
        )
    assert uid == "u-99"


def test_resolve_user_from_event_top_level_actor_finds_user():
    from app.social import linkedin_webhook

    fake_client = MagicMock()
    fake_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"user_id": "u-77"}]
    )
    with patch.object(linkedin_webhook, "get_service_client", return_value=fake_client):
        uid = linkedin_webhook.resolve_user_from_event({"actor": "urn:li:person:DEF"})
    assert uid == "u-77"


def test_resolve_user_from_event_no_actor_returns_none():
    from app.social import linkedin_webhook

    assert linkedin_webhook.resolve_user_from_event({}) is None


def test_resolve_user_from_event_no_match_returns_none():
    from app.social import linkedin_webhook

    fake_client = MagicMock()
    fake_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    with patch.object(linkedin_webhook, "get_service_client", return_value=fake_client):
        uid = linkedin_webhook.resolve_user_from_event(
            {"actor": "urn:li:person:NONEXIST"}
        )
    assert uid is None


# ---------------------------------------------------------------------------
# extract_event_type / extract_organization_id
# ---------------------------------------------------------------------------


def test_extract_event_type_prefers_eventType_field():
    from app.social import linkedin_webhook

    assert linkedin_webhook.extract_event_type({"eventType": "SHARE"}) == "SHARE"
    assert linkedin_webhook.extract_event_type({"type": "COMMENT"}) == "COMMENT"
    assert linkedin_webhook.extract_event_type({}) == "unknown"


def test_extract_organization_id_prefers_data_organization():
    from app.social import linkedin_webhook

    payload: dict[str, Any] = {
        "data": {"organization": "urn:li:organization:42"},
        "organizationId": "should-not-win",
    }
    assert (
        linkedin_webhook.extract_organization_id(payload)
        == "urn:li:organization:42"
    )

    assert (
        linkedin_webhook.extract_organization_id({"organizationId": "fallback"})
        == "fallback"
    )

    assert linkedin_webhook.extract_organization_id({}) is None
