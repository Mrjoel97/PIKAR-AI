# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the webhook infrastructure (inbound + outbound)."""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import types
from datetime import datetime, timedelta, timezone
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


# ---------------------------------------------------------------------------
# Task 2 -- Outbound delivery worker tests
# ---------------------------------------------------------------------------

# Stub encryption module for delivery service import
_mock_encryption = types.ModuleType("app.services.encryption")
_mock_encryption.encrypt_secret = MagicMock(return_value="encrypted")  # type: ignore[attr-defined]
_mock_encryption.decrypt_secret = MagicMock(return_value="decrypted-secret")  # type: ignore[attr-defined]
sys.modules.setdefault("app.services.encryption", _mock_encryption)


@pytest.mark.asyncio
class TestEnqueueWebhookEvent:
    """Tests for enqueue_webhook_event."""

    async def test_creates_deliveries_for_subscribed_endpoints(self):
        """Creates deliveries for all active endpoints subscribed to the event type."""
        from app.services.webhook_delivery_service import enqueue_webhook_event

        mock_client = MagicMock()

        # Two active endpoints subscribed to "task.created"
        endpoints_result = MagicMock()
        endpoints_result.data = [
            {"id": "ep-1", "url": "https://a.com/hook", "events": ["task.created"]},
            {"id": "ep-2", "url": "https://b.com/hook", "events": ["task.created", "task.updated"]},
        ]

        insert_result = MagicMock()
        insert_result.data = [{"id": "del-1"}, {"id": "del-2"}]

        call_idx = 0

        async def mock_exec(qb, *, op_name=None):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                return endpoints_result
            return insert_result

        with (
            patch("app.services.webhook_delivery_service.get_service_client", return_value=mock_client),
            patch("app.services.webhook_delivery_service.execute_async", side_effect=mock_exec),
        ):
            count = await enqueue_webhook_event("task.created", {"task_id": "t1"})

        assert count == 2

    async def test_skips_disabled_endpoints(self):
        """Skips endpoints where active=false (query filters them)."""
        from app.services.webhook_delivery_service import enqueue_webhook_event

        mock_client = MagicMock()

        # Query returns only active endpoints (active=false are excluded by query)
        endpoints_result = MagicMock()
        endpoints_result.data = []  # No active endpoints matched

        async def mock_exec(qb, *, op_name=None):
            return endpoints_result

        with (
            patch("app.services.webhook_delivery_service.get_service_client", return_value=mock_client),
            patch("app.services.webhook_delivery_service.execute_async", side_effect=mock_exec),
        ):
            count = await enqueue_webhook_event("task.created", {"task_id": "t1"})

        assert count == 0


@pytest.mark.asyncio
class TestDeliverSingle:
    """Tests for _deliver_single."""

    async def test_sends_post_with_hmac_header(self):
        """Sends POST with X-Pikar-Signature HMAC header."""
        from app.services.webhook_delivery_service import _deliver_single

        mock_client = MagicMock()
        delivery = {
            "id": "del-1",
            "event_type": "task.created",
            "payload": {"task_id": "t1"},
            "attempts": 0,
            "webhook_endpoints": {
                "id": "ep-1",
                "url": "https://example.com/hook",
                "secret": "encrypted-secret",
                "consecutive_failures": 0,
            },
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        update_result = MagicMock()
        update_result.data = [{"id": "del-1"}]

        with (
            patch("app.services.webhook_delivery_service.decrypt_secret", return_value="my-secret"),
            patch("app.services.webhook_delivery_service.httpx.AsyncClient") as mock_httpx,
            patch("app.services.webhook_delivery_service.execute_async", new_callable=AsyncMock, return_value=update_result),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await _deliver_single(mock_client, delivery)

        assert result["status"] == "delivered"
        # Verify X-Pikar-Signature was set
        call_args = mock_ctx.post.call_args
        headers = call_args.kwargs.get("headers", {})
        assert "X-Pikar-Signature" in headers
        assert headers["X-Pikar-Signature"].startswith("sha256=")

    async def test_marks_delivered_on_2xx(self):
        """Marks delivery status 'delivered' on 2xx response."""
        from app.services.webhook_delivery_service import _deliver_single

        mock_client = MagicMock()
        delivery = {
            "id": "del-1",
            "event_type": "task.created",
            "payload": {"task_id": "t1"},
            "attempts": 0,
            "webhook_endpoints": {
                "id": "ep-1",
                "url": "https://example.com/hook",
                "secret": "enc",
                "consecutive_failures": 3,
            },
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        update_result = MagicMock()
        update_result.data = [{"id": "del-1"}]

        with (
            patch("app.services.webhook_delivery_service.decrypt_secret", return_value="s"),
            patch("app.services.webhook_delivery_service.httpx.AsyncClient") as mock_httpx,
            patch("app.services.webhook_delivery_service.execute_async", new_callable=AsyncMock, return_value=update_result),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await _deliver_single(mock_client, delivery)

        assert result["status"] == "delivered"
        assert result["attempts"] == 1

    async def test_increments_attempts_and_backoff_on_failure(self):
        """On non-2xx, increments attempts and sets next_retry_at with backoff."""
        from app.services.webhook_delivery_service import (
            RETRY_BACKOFF_SECONDS,
            _deliver_single,
        )

        mock_client = MagicMock()
        delivery = {
            "id": "del-2",
            "event_type": "task.updated",
            "payload": {"task_id": "t2"},
            "attempts": 1,  # second attempt
            "webhook_endpoints": {
                "id": "ep-2",
                "url": "https://fail.com/hook",
                "secret": "enc",
                "consecutive_failures": 0,
            },
        }

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        update_result = MagicMock()
        update_result.data = [{"id": "del-2"}]

        with (
            patch("app.services.webhook_delivery_service.decrypt_secret", return_value="s"),
            patch("app.services.webhook_delivery_service.httpx.AsyncClient") as mock_httpx,
            patch("app.services.webhook_delivery_service.execute_async", new_callable=AsyncMock, return_value=update_result),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await _deliver_single(mock_client, delivery)

        assert result["status"] == "failed"
        assert result["attempts"] == 2
        # Backoff schedule verification
        assert RETRY_BACKOFF_SECONDS == [1, 5, 30, 300, 1800]

    async def test_marks_dead_after_max_attempts(self):
        """Marks status 'dead' when attempts reaches MAX_ATTEMPTS (5)."""
        from app.services.webhook_delivery_service import _deliver_single

        mock_client = MagicMock()
        delivery = {
            "id": "del-3",
            "event_type": "workflow.started",
            "payload": {},
            "attempts": 4,  # Will become 5 = MAX_ATTEMPTS
            "webhook_endpoints": {
                "id": "ep-3",
                "url": "https://dead.com/hook",
                "secret": "enc",
                "consecutive_failures": 0,
            },
        }

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        update_result = MagicMock()
        update_result.data = [{"id": "del-3"}]

        with (
            patch("app.services.webhook_delivery_service.decrypt_secret", return_value="s"),
            patch("app.services.webhook_delivery_service.httpx.AsyncClient") as mock_httpx,
            patch("app.services.webhook_delivery_service.execute_async", new_callable=AsyncMock, return_value=update_result),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await _deliver_single(mock_client, delivery)

        assert result["status"] == "dead"
        assert result["attempts"] == 5

    async def test_circuit_breaker_disables_after_threshold(self):
        """Disables endpoint after CIRCUIT_BREAKER_THRESHOLD consecutive failures."""
        from app.services.webhook_delivery_service import (
            CIRCUIT_BREAKER_THRESHOLD,
            _deliver_single,
        )

        mock_client = MagicMock()
        delivery = {
            "id": "del-4",
            "event_type": "task.created",
            "payload": {},
            "attempts": 0,
            "webhook_endpoints": {
                "id": "ep-4",
                "url": "https://broken.com/hook",
                "secret": "enc",
                "consecutive_failures": CIRCUIT_BREAKER_THRESHOLD - 1,
            },
        }

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"

        update_result = MagicMock()
        update_result.data = [{"id": "del-4"}]

        exec_calls = []

        async def track_exec(qb, *, op_name=None):
            exec_calls.append(op_name)
            return update_result

        with (
            patch("app.services.webhook_delivery_service.decrypt_secret", return_value="s"),
            patch("app.services.webhook_delivery_service.httpx.AsyncClient") as mock_httpx,
            patch("app.services.webhook_delivery_service.execute_async", side_effect=track_exec),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await _deliver_single(mock_client, delivery)

        # Should have called endpoint disable
        assert "webhook.delivery.disable_endpoint" in exec_calls
        assert CIRCUIT_BREAKER_THRESHOLD == 10

    async def test_circuit_breaker_resets_on_success(self):
        """Resets consecutive_failures to 0 on successful delivery."""
        from app.services.webhook_delivery_service import _deliver_single

        mock_client = MagicMock()
        delivery = {
            "id": "del-5",
            "event_type": "task.created",
            "payload": {},
            "attempts": 0,
            "webhook_endpoints": {
                "id": "ep-5",
                "url": "https://ok.com/hook",
                "secret": "enc",
                "consecutive_failures": 5,
            },
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        update_result = MagicMock()
        update_result.data = [{"id": "del-5"}]

        exec_calls = []

        async def track_exec(qb, *, op_name=None):
            exec_calls.append(op_name)
            return update_result

        with (
            patch("app.services.webhook_delivery_service.decrypt_secret", return_value="s"),
            patch("app.services.webhook_delivery_service.httpx.AsyncClient") as mock_httpx,
            patch("app.services.webhook_delivery_service.execute_async", side_effect=track_exec),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await _deliver_single(mock_client, delivery)

        assert result["status"] == "delivered"
        # Should have reset endpoint failures
        assert "webhook.delivery.reset_failures" in exec_calls


@pytest.mark.asyncio
class TestRunWebhookDeliveryTick:
    """Tests for run_webhook_delivery_tick."""

    async def test_fetches_pending_deliveries_due_for_retry(self):
        """Only fetches deliveries where next_retry_at <= now and attempts < 5."""
        from app.services.webhook_delivery_service import run_webhook_delivery_tick

        mock_client = MagicMock()

        # No pending deliveries
        fetch_result = MagicMock()
        fetch_result.data = []

        with (
            patch("app.services.webhook_delivery_service.get_service_client", return_value=mock_client),
            patch("app.services.webhook_delivery_service.execute_async", new_callable=AsyncMock, return_value=fetch_result),
        ):
            results = await run_webhook_delivery_tick()

        assert results == []
