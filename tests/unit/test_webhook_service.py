# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the webhook infrastructure (inbound + outbound)."""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Module-level mocking: stub out the heavy rate_limiter dependency so
# importing ``app.routers.webhooks`` does not trigger .env file reads.
# ---------------------------------------------------------------------------
_MOCK_LIMITER = MagicMock()
_MOCK_LIMITER.limit = lambda x: (lambda fn: fn)  # no-op decorator

_mock_rate_mod = types.ModuleType("app.middleware.rate_limiter")
_mock_rate_mod.limiter = _MOCK_LIMITER  # type: ignore[attr-defined]
_mock_rate_mod.get_user_persona_limit = "100/minute"  # type: ignore[attr-defined]

# Stub the social.linkedin_webhook module
_mock_linkedin = types.ModuleType("app.social.linkedin_webhook")
_mock_linkedin.extract_event_type = MagicMock(return_value="test")  # type: ignore[attr-defined]
_mock_linkedin.extract_organization_id = MagicMock(return_value="org1")  # type: ignore[attr-defined]
_mock_linkedin.resolve_user_from_event = MagicMock(return_value="user1")  # type: ignore[attr-defined]
_mock_linkedin.store_webhook_event = AsyncMock(return_value={"id": "x"})  # type: ignore[attr-defined]
_mock_linkedin.verify_signature = MagicMock(return_value=True)  # type: ignore[attr-defined]

# Stub MCP config
_mock_mcp_config_mod = types.ModuleType("app.mcp.config")
_mock_mcp_config_mod.get_mcp_config = MagicMock()  # type: ignore[attr-defined]

# Stub onboarding
_mock_onboarding = types.ModuleType("app.routers.onboarding")
_mock_onboarding.get_current_user_id = MagicMock(return_value="user-123")  # type: ignore[attr-defined]

# Stub supabase modules
_mock_supa = types.ModuleType("app.services.supabase")
_mock_supa.get_service_client = MagicMock()  # type: ignore[attr-defined]

_mock_supa_async = types.ModuleType("app.services.supabase_async")
_mock_supa_async.execute_async = AsyncMock()  # type: ignore[attr-defined]

# Install stubs BEFORE importing the router
sys.modules.setdefault("app.middleware.rate_limiter", _mock_rate_mod)
sys.modules.setdefault("app.social.linkedin_webhook", _mock_linkedin)
sys.modules.setdefault("app.mcp.config", _mock_mcp_config_mod)
sys.modules.setdefault("app.routers.onboarding", _mock_onboarding)
sys.modules.setdefault("app.services.supabase", _mock_supa)
sys.modules.setdefault("app.services.supabase_async", _mock_supa_async)


# ---------------------------------------------------------------------------
# Task 1 -- Inbound webhook + event catalog tests
# ---------------------------------------------------------------------------


class TestVerifyInboundSignature:
    """Tests for _verify_inbound_signature helper."""

    def test_valid_hmac_sha256_signature(self):
        """Valid HMAC-SHA256 signature returns True."""
        from app.routers.webhooks import _verify_inbound_signature

        secret = "test-webhook-secret"
        body = b'{"event": "task.created"}'
        expected_sig = hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()

        result = _verify_inbound_signature(
            body=body,
            secret=secret,
            signature_header=f"sha256={expected_sig}",
        )
        assert result is True

    def test_tampered_payload_returns_false(self):
        """Tampered payload returns False."""
        from app.routers.webhooks import _verify_inbound_signature

        secret = "test-webhook-secret"
        body = b'{"event": "task.created"}'
        tampered = b'{"event": "task.deleted"}'
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        result = _verify_inbound_signature(
            body=tampered,
            secret=secret,
            signature_header=f"sha256={sig}",
        )
        assert result is False

    def test_uses_compare_digest(self):
        """Must use hmac.compare_digest, not ==."""
        from app.routers import webhooks as mod

        secret = "test-secret"
        body = b'{"data":"x"}'
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        with patch.object(hmac, "compare_digest", wraps=hmac.compare_digest) as spy:
            mod._verify_inbound_signature(
                body=body,
                secret=secret,
                signature_header=f"sha256={sig}",
            )
            spy.assert_called_once()

    def test_empty_signature_returns_false(self):
        """Empty signature header returns False."""
        from app.routers.webhooks import _verify_inbound_signature

        result = _verify_inbound_signature(
            body=b"payload",
            secret="secret",
            signature_header="",
        )
        assert result is False


class TestExtractEventId:
    """Tests for _extract_event_id helper."""

    def test_extracts_generic_id(self):
        """Extracts event_id from payload id field."""
        from app.routers.webhooks import _extract_event_id

        payload = {"id": "evt_123", "type": "task.created"}
        assert _extract_event_id("generic", payload) == "evt_123"

    def test_extracts_stripe_id(self):
        """Stripe payloads have event id at top level."""
        from app.routers.webhooks import _extract_event_id

        payload = {"id": "evt_stripe_456", "type": "invoice.paid"}
        assert _extract_event_id("stripe", payload) == "evt_stripe_456"

    def test_fallback_to_hash_when_no_id(self):
        """When no id field, falls back to payload hash."""
        from app.routers.webhooks import _extract_event_id

        payload = {"data": "no-id-here"}
        result = _extract_event_id("unknown", payload)
        assert result is not None
        assert len(result) > 0


class TestExtractEventType:
    """Tests for _extract_event_type helper."""

    def test_extracts_type_field(self):
        """Extracts type from payload."""
        from app.routers.webhooks import _extract_event_type

        assert _extract_event_type("stripe", {"type": "invoice.paid"}) == "invoice.paid"

    def test_extracts_event_field_fallback(self):
        """Falls back to event field when type is absent."""
        from app.routers.webhooks import _extract_event_type

        assert _extract_event_type("custom", {"event": "contact.created"}) == "contact.created"

    def test_returns_unknown_when_missing(self):
        """Returns 'unknown' when neither type nor event is present."""
        from app.routers.webhooks import _extract_event_type

        assert _extract_event_type("x", {}) == "unknown"


class TestEventCatalog:
    """Tests for the webhook event catalog."""

    def test_catalog_has_all_9_event_types(self):
        """EVENT_CATALOG contains all 9 defined event types."""
        from app.models.webhook_events import EVENT_CATALOG

        expected = {
            "task.created",
            "task.updated",
            "workflow.started",
            "workflow.completed",
            "approval.pending",
            "approval.decided",
            "initiative.phase_changed",
            "contact.synced",
            "invoice.created",
        }
        assert set(EVENT_CATALOG.keys()) == expected

    def test_each_event_has_payload_schema(self):
        """Each event type has a description and payload_schema."""
        from app.models.webhook_events import EVENT_CATALOG

        for event_type, meta in EVENT_CATALOG.items():
            assert "description" in meta, f"{event_type} missing description"
            assert "payload_schema" in meta, f"{event_type} missing payload_schema"
            assert isinstance(meta["payload_schema"], dict)

    def test_webhook_event_type_enum_values(self):
        """WebhookEventType enum has all expected string values."""
        from app.models.webhook_events import WebhookEventType

        expected = {
            "task.created",
            "task.updated",
            "workflow.started",
            "workflow.completed",
            "approval.pending",
            "approval.decided",
            "initiative.phase_changed",
            "contact.synced",
            "invoice.created",
        }
        actual = {e.value for e in WebhookEventType}
        assert actual == expected

    def test_get_event_schema_returns_schema(self):
        """get_event_schema returns schema for known event type."""
        from app.models.webhook_events import get_event_schema

        schema = get_event_schema("task.created")
        assert schema is not None
        assert isinstance(schema, dict)
        assert schema["type"] == "object"

    def test_get_event_schema_returns_none_for_unknown(self):
        """get_event_schema returns None for unknown event type."""
        from app.models.webhook_events import get_event_schema

        assert get_event_schema("nonexistent.event") is None


@pytest.mark.asyncio
class TestInboundWebhookInsert:
    """Tests for _handle_inbound_insert function."""

    async def test_duplicate_returns_duplicate_status(self):
        """When upsert returns empty data, respond with duplicate status."""
        from app.routers.webhooks import _handle_inbound_insert

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []

        with patch(
            "app.routers.webhooks.execute_async",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await _handle_inbound_insert(
                client=mock_client,
                provider="stripe",
                event_id="evt_123",
                event_type="invoice.paid",
                payload={"id": "evt_123"},
            )

        assert result["status"] == "duplicate"
        assert result["event_id"] == "evt_123"

    async def test_successful_insert_queues_job(self):
        """Successful insert queues a webhook_inbound_process job in ai_jobs."""
        from app.routers.webhooks import _handle_inbound_insert

        mock_client = MagicMock()
        mock_insert_result = MagicMock()
        mock_insert_result.data = [{"id": "row-uuid-1"}]

        mock_job_result = MagicMock()
        mock_job_result.data = [{"id": "job-uuid-1"}]

        call_count = 0

        async def mock_execute(qb, *, op_name=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_insert_result
            return mock_job_result

        with patch("app.routers.webhooks.execute_async", side_effect=mock_execute):
            result = await _handle_inbound_insert(
                client=mock_client,
                provider="hubspot",
                event_id="hs_evt_789",
                event_type="contact.created",
                payload={"id": "hs_evt_789"},
            )

        assert result["status"] == "received"
        assert result["event_id"] == "hs_evt_789"
        assert call_count == 2  # insert + job queue
