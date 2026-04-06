# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for outbound webhook CRUD, event catalog, delivery log, test send, and Zapier envelope."""

from __future__ import annotations

import sys
import types
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Module-level stubs installed BEFORE any app imports
# ---------------------------------------------------------------------------

_mock_rate_mod = types.ModuleType("app.middleware.rate_limiter")
_mock_rate_mod.limiter = MagicMock()
_mock_rate_mod.limiter.limit = lambda x: (lambda fn: fn)
_mock_rate_mod.get_user_persona_limit = MagicMock(return_value="100/minute")

_mock_onboarding = types.ModuleType("app.routers.onboarding")
_mock_onboarding.get_current_user_id = MagicMock(return_value="user-abc")

_mock_supa = types.ModuleType("app.services.supabase")
_mock_supa.get_service_client = MagicMock()

_mock_supa_async = types.ModuleType("app.services.supabase_async")
_mock_supa_async.execute_async = AsyncMock()

_mock_encryption = types.ModuleType("app.services.encryption")
_mock_encryption.encrypt_secret = MagicMock(return_value="encrypted-secret")
_mock_encryption.decrypt_secret = MagicMock(return_value="plaintext-secret-1234")

# Stub the specialized_agents module to prevent it from triggering the full
# agent import chain (google.adk, supabase.Client, etc.) when Python resolves
# the app.agents package __init__ on first import of app.agents.tools.*.
_mock_specialized = types.ModuleType("app.agents.specialized_agents")
_mock_specialized.SPECIALIZED_AGENTS = []
for _agent_name in (
    "compliance_agent", "content_agent", "customer_support_agent",
    "data_agent", "financial_agent", "hr_agent", "marketing_agent",
    "operations_agent", "sales_agent", "strategic_agent",
):
    setattr(_mock_specialized, _agent_name, MagicMock())

sys.modules.setdefault("app.middleware.rate_limiter", _mock_rate_mod)
sys.modules.setdefault("app.routers.onboarding", _mock_onboarding)
sys.modules.setdefault("app.services.supabase", _mock_supa)
sys.modules.setdefault("app.services.supabase_async", _mock_supa_async)
sys.modules.setdefault("app.services.encryption", _mock_encryption)
sys.modules.setdefault("app.agents.specialized_agents", _mock_specialized)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = "user-abc"
ENDPOINT_ID = str(uuid.uuid4())


def _make_endpoint_row(
    *,
    id=ENDPOINT_ID,
    user_id=USER_ID,
    url="https://example.com/hook",
    events=None,
    active=True,
    description="Test hook",
    consecutive_failures=0,
    created_at="2026-04-06T10:00:00+00:00",
    secret="encrypted-secret",
):
    """Build a realistic webhook_endpoints DB row."""
    return {
        "id": id,
        "user_id": user_id,
        "url": url,
        "secret": secret,
        "events": events or ["task.created"],
        "active": active,
        "description": description,
        "consecutive_failures": consecutive_failures,
        "created_at": created_at,
    }


def _make_delivery_row(
    *,
    endpoint_id=ENDPOINT_ID,
    event_type="task.created",
    status="delivered",
    attempts=1,
    response_code=200,
    created_at="2026-04-06T10:01:00+00:00",
):
    """Build a realistic webhook_deliveries DB row."""
    return {
        "id": str(uuid.uuid4()),
        "endpoint_id": endpoint_id,
        "event_type": event_type,
        "status": status,
        "attempts": attempts,
        "response_code": response_code,
        "created_at": created_at,
    }


# ---------------------------------------------------------------------------
# Task 1: Endpoint CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestEndpointCrud:
    """Tests for POST/GET/PATCH/DELETE /outbound-webhooks/endpoints."""

    async def test_create_endpoint_returns_plaintext_secret(self):
        """POST /endpoints creates endpoint and returns plaintext secret once."""
        from app.routers.outbound_webhooks import CreateEndpointRequest, create_endpoint

        mock_client = MagicMock()
        row = _make_endpoint_row()
        create_result = MagicMock()
        create_result.data = [row]

        with (
            patch("app.routers.outbound_webhooks.get_service_client", return_value=mock_client),
            patch("app.routers.outbound_webhooks.execute_async", new_callable=AsyncMock, return_value=create_result),
            patch("app.routers.outbound_webhooks.encrypt_secret", return_value="encrypted-secret"),
        ):
            req = CreateEndpointRequest(url="https://example.com/hook", events=["task.created"])
            result = await create_endpoint(req, user_id=USER_ID)

        assert "secret" in result
        assert result["secret"].startswith("whsec_")
        assert "endpoint" in result

    async def test_create_endpoint_rejects_unknown_events(self):
        """POST /endpoints returns 422 for unknown event types."""
        from fastapi import HTTPException

        from app.routers.outbound_webhooks import CreateEndpointRequest, create_endpoint

        mock_client = MagicMock()
        with patch("app.routers.outbound_webhooks.get_service_client", return_value=mock_client):
            req = CreateEndpointRequest(url="https://example.com/hook", events=["unknown.event"])
            with pytest.raises(HTTPException) as exc_info:
                await create_endpoint(req, user_id=USER_ID)

        assert exc_info.value.status_code == 422

    async def test_list_endpoints_returns_masked_secrets(self):
        """GET /endpoints lists endpoints with secret_preview (masked)."""
        from app.routers.outbound_webhooks import list_endpoints

        mock_client = MagicMock()
        row = _make_endpoint_row(secret="encrypted-secret")
        list_result = MagicMock()
        list_result.data = [row]

        with (
            patch("app.routers.outbound_webhooks.get_service_client", return_value=mock_client),
            patch("app.routers.outbound_webhooks.execute_async", new_callable=AsyncMock, return_value=list_result),
            patch("app.routers.outbound_webhooks.decrypt_secret", return_value="plaintext-secret-1234"),
        ):
            result = await list_endpoints(user_id=USER_ID)

        assert len(result) == 1
        ep = result[0]
        assert "secret_preview" in ep
        assert ep["secret_preview"].startswith("whsec_...")
        assert ep["secret_preview"].endswith("1234")

    async def test_delete_endpoint_owned_by_user(self):
        """DELETE /endpoints/{id} removes owned endpoint."""
        from app.routers.outbound_webhooks import delete_endpoint

        mock_client = MagicMock()
        row = _make_endpoint_row()
        fetch_result = MagicMock()
        fetch_result.data = [row]
        delete_result = MagicMock()
        delete_result.data = [row]

        call_idx = 0

        async def mock_exec(qb, *, op_name=None):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                return fetch_result
            return delete_result

        with (
            patch("app.routers.outbound_webhooks.get_service_client", return_value=mock_client),
            patch("app.routers.outbound_webhooks.execute_async", side_effect=mock_exec),
        ):
            result = await delete_endpoint(endpoint_id=ENDPOINT_ID, user_id=USER_ID)

        assert result["deleted"] is True

    async def test_delete_endpoint_returns_404_for_non_owned(self):
        """DELETE /endpoints/{id} returns 404 for non-owned endpoint."""
        from fastapi import HTTPException

        from app.routers.outbound_webhooks import delete_endpoint

        mock_client = MagicMock()
        fetch_result = MagicMock()
        fetch_result.data = []

        with (
            patch("app.routers.outbound_webhooks.get_service_client", return_value=mock_client),
            patch("app.routers.outbound_webhooks.execute_async", new_callable=AsyncMock, return_value=fetch_result),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_endpoint(endpoint_id=ENDPOINT_ID, user_id="other-user")

        assert exc_info.value.status_code == 404

    async def test_patch_endpoint_toggles_active(self):
        """PATCH /endpoints/{id} can toggle active status."""
        from app.routers.outbound_webhooks import UpdateEndpointRequest, update_endpoint

        mock_client = MagicMock()
        row = _make_endpoint_row(active=True)
        fetch_result = MagicMock()
        fetch_result.data = [row]
        updated_row = {**row, "active": False}
        update_result = MagicMock()
        update_result.data = [updated_row]

        call_idx = 0

        async def mock_exec(qb, *, op_name=None):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                return fetch_result
            return update_result

        with (
            patch("app.routers.outbound_webhooks.get_service_client", return_value=mock_client),
            patch("app.routers.outbound_webhooks.execute_async", side_effect=mock_exec),
        ):
            req = UpdateEndpointRequest(active=False)
            result = await update_endpoint(endpoint_id=ENDPOINT_ID, req=req, user_id=USER_ID)

        assert result["active"] is False


# ---------------------------------------------------------------------------
# Task 1: Event catalog
# ---------------------------------------------------------------------------


class TestEventCatalog:
    """Tests for GET /outbound-webhooks/events."""

    def test_get_events_returns_9_event_types(self):
        """get_events returns all 9 event types."""
        from app.routers.outbound_webhooks import get_events

        result = get_events()
        assert len(result) == 9

    def test_each_event_has_required_keys(self):
        """Each event entry has event_type, description, and schema."""
        from app.routers.outbound_webhooks import get_events

        result = get_events()
        for entry in result:
            assert "event_type" in entry
            assert "description" in entry
            assert "schema" in entry

    def test_known_event_types_present(self):
        """All 9 known event type strings are in the catalog."""
        from app.routers.outbound_webhooks import get_events

        event_types = {e["event_type"] for e in get_events()}
        expected = {
            "task.created", "task.updated", "workflow.started", "workflow.completed",
            "approval.pending", "approval.decided", "initiative.phase_changed",
            "contact.synced", "invoice.created",
        }
        assert event_types == expected


# ---------------------------------------------------------------------------
# Task 1: Delivery log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDeliveryLog:
    """Tests for GET /outbound-webhooks/endpoints/{id}/deliveries."""

    async def test_returns_delivery_rows_for_owned_endpoint(self):
        """GET /deliveries returns paginated delivery rows for owned endpoint."""
        from app.routers.outbound_webhooks import get_deliveries

        mock_client = MagicMock()
        row = _make_endpoint_row()
        fetch_ep_result = MagicMock()
        fetch_ep_result.data = [row]
        delivery_rows = [_make_delivery_row(), _make_delivery_row(status="failed")]
        fetch_del_result = MagicMock()
        fetch_del_result.data = delivery_rows

        call_idx = 0

        async def mock_exec(qb, *, op_name=None):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                return fetch_ep_result
            return fetch_del_result

        with (
            patch("app.routers.outbound_webhooks.get_service_client", return_value=mock_client),
            patch("app.routers.outbound_webhooks.execute_async", side_effect=mock_exec),
        ):
            result = await get_deliveries(endpoint_id=ENDPOINT_ID, user_id=USER_ID, limit=50, offset=0)

        assert len(result) == 2
        assert result[0]["status"] == "delivered"

    async def test_returns_404_for_non_owned_endpoint(self):
        """GET /deliveries returns 404 for non-owned endpoint."""
        from fastapi import HTTPException

        from app.routers.outbound_webhooks import get_deliveries

        mock_client = MagicMock()
        fetch_ep_result = MagicMock()
        fetch_ep_result.data = []

        with (
            patch("app.routers.outbound_webhooks.get_service_client", return_value=mock_client),
            patch("app.routers.outbound_webhooks.execute_async", new_callable=AsyncMock, return_value=fetch_ep_result),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_deliveries(endpoint_id=ENDPOINT_ID, user_id="other-user", limit=50, offset=0)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Task 1: Test send
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestTestSend:
    """Tests for POST /outbound-webhooks/endpoints/{id}/test."""

    async def test_test_send_enqueues_delivery(self):
        """POST /test enqueues a synthetic delivery for the endpoint."""
        from app.routers.outbound_webhooks import test_send

        mock_client = MagicMock()
        row = _make_endpoint_row(events=["task.created"])
        fetch_ep_result = MagicMock()
        fetch_ep_result.data = [row]

        call_idx = 0

        async def mock_exec(qb, *, op_name=None):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                return fetch_ep_result
            return MagicMock(data=[{"id": "del-test-1"}])

        with (
            patch("app.routers.outbound_webhooks.get_service_client", return_value=mock_client),
            patch("app.routers.outbound_webhooks.execute_async", side_effect=mock_exec),
        ):
            result = await test_send(endpoint_id=ENDPOINT_ID, user_id=USER_ID)

        assert result["queued"] is True

    async def test_test_send_returns_404_for_non_owned(self):
        """POST /test returns 404 for non-owned endpoint."""
        from fastapi import HTTPException

        from app.routers.outbound_webhooks import test_send

        mock_client = MagicMock()
        fetch_result = MagicMock()
        fetch_result.data = []

        with (
            patch("app.routers.outbound_webhooks.get_service_client", return_value=mock_client),
            patch("app.routers.outbound_webhooks.execute_async", new_callable=AsyncMock, return_value=fetch_result),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await test_send(endpoint_id=ENDPOINT_ID, user_id="other-user")

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Task 2: Zapier-compatible envelope
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestZapierEnvelope:
    """Tests for Zapier-compatible envelope in enqueue_webhook_event."""

    async def test_envelope_api_version_constant_exists(self):
        """_ENVELOPE_API_VERSION constant equals 2026-04."""
        from app.services.webhook_delivery_service import _ENVELOPE_API_VERSION

        assert _ENVELOPE_API_VERSION == "2026-04"

    async def test_enqueue_makes_find_and_insert_calls(self):
        """enqueue_webhook_event makes at least 2 DB calls (find endpoints + insert deliveries)."""
        from app.services.webhook_delivery_service import enqueue_webhook_event

        mock_client = MagicMock()
        endpoints_result = MagicMock()
        endpoints_result.data = [{"id": "ep-1"}]

        call_idx = 0

        async def mock_exec(qb, *, op_name=None):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                return endpoints_result
            return MagicMock(data=[{"id": "del-1"}])

        with (
            patch("app.services.webhook_delivery_service.get_service_client", return_value=mock_client),
            patch("app.services.webhook_delivery_service.execute_async", side_effect=mock_exec),
        ):
            count = await enqueue_webhook_event("task.created", {"task_id": "t1"})

        assert count == 1
        assert call_idx >= 2

    async def test_two_enqueue_calls_complete_independently(self):
        """Two separate enqueue calls complete independently without errors."""
        from app.services.webhook_delivery_service import enqueue_webhook_event

        mock_client = MagicMock()

        async def mock_exec(qb, *, op_name=None):
            if op_name and "find_endpoints" in op_name:
                return MagicMock(data=[{"id": "ep-1"}])
            return MagicMock(data=[{"id": "del-1"}])

        with (
            patch("app.services.webhook_delivery_service.get_service_client", return_value=mock_client),
            patch("app.services.webhook_delivery_service.execute_async", side_effect=mock_exec),
        ):
            c1 = await enqueue_webhook_event("task.created", {"x": 1})
            c2 = await enqueue_webhook_event("task.updated", {"x": 2})

        assert c1 == 1
        assert c2 == 1

    async def test_verification_snippets_available(self):
        """VERIFICATION_SNIPPETS has node_js, python, and curl keys with non-empty strings."""
        from app.models.webhook_events import VERIFICATION_SNIPPETS

        assert "node_js" in VERIFICATION_SNIPPETS
        assert "python" in VERIFICATION_SNIPPETS
        assert "curl" in VERIFICATION_SNIPPETS
        for key, snippet in VERIFICATION_SNIPPETS.items():
            assert isinstance(snippet, str), f"{key} must be a string"
            assert len(snippet) > 20, f"{key} snippet too short"


# ---------------------------------------------------------------------------
# Task 1 (Plan 03): Webhook agent tools
# ---------------------------------------------------------------------------


def _make_tool_context(user_id: str = USER_ID) -> MagicMock:
    """Build a mock ADK tool context with user_id in state."""
    ctx = MagicMock()
    ctx.state = {"user_id": user_id}
    return ctx


@pytest.mark.asyncio
class TestWebhookTools:
    """Tests for WEBHOOK_TOOLS functions (app.agents.tools.webhook_tools)."""

    # ------------------------------------------------------------------
    # list_webhook_endpoints
    # ------------------------------------------------------------------

    async def test_list_endpoints_returns_user_endpoints(self):
        """list_webhook_endpoints returns endpoints owned by the user without secrets."""
        from app.agents.tools.webhook_tools import list_webhook_endpoints

        ctx = _make_tool_context()
        row = _make_endpoint_row()
        mock_client = MagicMock()
        list_result = MagicMock()
        list_result.data = [row]

        with (
            patch("app.services.supabase.get_service_client", return_value=mock_client),
            patch("app.services.supabase_async.execute_async", new_callable=AsyncMock, return_value=list_result),
        ):
            result = await list_webhook_endpoints(ctx)

        assert result["endpoints"]
        ep = result["endpoints"][0]
        assert ep["id"] == ENDPOINT_ID
        assert ep["url"] == "https://example.com/hook"
        assert "secret" not in ep

    # ------------------------------------------------------------------
    # create_webhook_endpoint
    # ------------------------------------------------------------------

    async def test_create_endpoint_succeeds_with_valid_events(self):
        """create_webhook_endpoint returns endpoint_id and plaintext secret on success."""
        from app.agents.tools.webhook_tools import create_webhook_endpoint

        ctx = _make_tool_context()
        row = _make_endpoint_row()
        mock_client = MagicMock()
        insert_result = MagicMock()
        insert_result.data = [row]

        with (
            patch("app.services.supabase.get_service_client", return_value=mock_client),
            patch("app.services.supabase_async.execute_async", new_callable=AsyncMock, return_value=insert_result),
            patch("app.services.encryption.encrypt_secret", return_value="encrypted-secret"),
        ):
            result = await create_webhook_endpoint(ctx, url="https://example.com/hook", events=["task.created"])

        assert "endpoint_id" in result
        assert "secret" in result
        assert result["secret"].startswith("whsec_")
        assert "message" in result

    async def test_create_endpoint_rejects_unknown_events(self):
        """create_webhook_endpoint returns an error dict for unknown event types."""
        from app.agents.tools.webhook_tools import create_webhook_endpoint

        ctx = _make_tool_context()
        result = await create_webhook_endpoint(ctx, url="https://example.com/hook", events=["bad.event"])

        assert "error" in result

    # ------------------------------------------------------------------
    # delete_webhook_endpoint
    # ------------------------------------------------------------------

    async def test_delete_endpoint_owned_by_user(self):
        """delete_webhook_endpoint removes the endpoint and returns a confirmation dict."""
        from app.agents.tools.webhook_tools import delete_webhook_endpoint

        ctx = _make_tool_context()
        row = _make_endpoint_row()
        mock_client = MagicMock()
        fetch_result = MagicMock()
        fetch_result.data = [row]
        delete_result = MagicMock()
        delete_result.data = [row]

        call_idx = 0

        async def mock_exec(qb, *, op_name=None):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                return fetch_result
            return delete_result

        with (
            patch("app.services.supabase.get_service_client", return_value=mock_client),
            patch("app.services.supabase_async.execute_async", side_effect=mock_exec),
        ):
            result = await delete_webhook_endpoint(ctx, endpoint_id=ENDPOINT_ID)

        assert "deleted" in result or "message" in result

    async def test_delete_endpoint_not_owned_returns_error(self):
        """delete_webhook_endpoint returns error dict when endpoint not owned by user."""
        from app.agents.tools.webhook_tools import delete_webhook_endpoint

        ctx = _make_tool_context(user_id="other-user")
        mock_client = MagicMock()
        fetch_result = MagicMock()
        fetch_result.data = []

        with (
            patch("app.services.supabase.get_service_client", return_value=mock_client),
            patch("app.services.supabase_async.execute_async", new_callable=AsyncMock, return_value=fetch_result),
        ):
            result = await delete_webhook_endpoint(ctx, endpoint_id=ENDPOINT_ID)

        assert "error" in result

    # ------------------------------------------------------------------
    # list_webhook_events
    # ------------------------------------------------------------------

    async def test_list_events_returns_catalog_summary(self):
        """list_webhook_events returns all 9 event_type+description pairs."""
        from app.agents.tools.webhook_tools import list_webhook_events

        ctx = _make_tool_context()
        result = await list_webhook_events(ctx)

        assert "events" in result
        events = result["events"]
        assert len(events) == 9
        for ev in events:
            assert "event_type" in ev
            assert "description" in ev
            assert "schema" not in ev  # no schema in chat display

    # ------------------------------------------------------------------
    # get_webhook_delivery_log
    # ------------------------------------------------------------------

    async def test_delivery_log_returns_recent_deliveries(self):
        """get_webhook_delivery_log returns delivery rows for owned endpoint."""
        from app.agents.tools.webhook_tools import get_webhook_delivery_log

        ctx = _make_tool_context()
        row = _make_endpoint_row()
        delivery = _make_delivery_row()
        mock_client = MagicMock()
        fetch_ep_result = MagicMock()
        fetch_ep_result.data = [row]
        fetch_del_result = MagicMock()
        fetch_del_result.data = [delivery]

        call_idx = 0

        async def mock_exec(qb, *, op_name=None):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                return fetch_ep_result
            return fetch_del_result

        with (
            patch("app.services.supabase.get_service_client", return_value=mock_client),
            patch("app.services.supabase_async.execute_async", side_effect=mock_exec),
        ):
            result = await get_webhook_delivery_log(ctx, endpoint_id=ENDPOINT_ID)

        assert "deliveries" in result
        assert len(result["deliveries"]) == 1
        d = result["deliveries"][0]
        assert "event_type" in d
        assert "status" in d
        assert "created_at" in d

    async def test_delivery_log_not_owned_returns_error(self):
        """get_webhook_delivery_log returns error dict for non-owned endpoint."""
        from app.agents.tools.webhook_tools import get_webhook_delivery_log

        ctx = _make_tool_context(user_id="other-user")
        mock_client = MagicMock()
        fetch_result = MagicMock()
        fetch_result.data = []

        with (
            patch("app.services.supabase.get_service_client", return_value=mock_client),
            patch("app.services.supabase_async.execute_async", new_callable=AsyncMock, return_value=fetch_result),
        ):
            result = await get_webhook_delivery_log(ctx, endpoint_id=ENDPOINT_ID)

        assert "error" in result

    # ------------------------------------------------------------------
    # WEBHOOK_TOOLS export list
    # ------------------------------------------------------------------

    def test_webhook_tools_exports_five_functions(self):
        """WEBHOOK_TOOLS contains exactly 5 callable functions."""
        from app.agents.tools.webhook_tools import WEBHOOK_TOOLS

        assert len(WEBHOOK_TOOLS) == 5
        for fn in WEBHOOK_TOOLS:
            assert callable(fn)
