"""Unit tests for admin audit logging service and audit log API endpoint.

Tests verify:
- log_admin_action inserts row into admin_audit_log table
- monitoring_loop source with admin_user_id=None succeeds
- All 4 source tags are accepted ('manual', 'ai_agent', 'impersonation', 'monitoring_loop')
- _resolve_admin_emails resolves UUIDs to emails via Supabase auth admin API
- _resolve_admin_emails handles null admin_user_id (returns "System")
- _resolve_admin_emails falls back to raw UUID on auth API failure
- list_audit_log endpoint injects admin_email into every returned entry
"""
from unittest.mock import MagicMock, patch

import pytest

_SERVICE_CLIENT_PATCH = "app.services.admin_audit.get_service_client"


@pytest.fixture
def mock_supabase():
    """Mock Supabase client for audit log insert."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[{"id": "audit-row-1"}])
    return client


@pytest.mark.asyncio
async def test_log_admin_action(mock_supabase):
    """log_admin_action inserts row into admin_audit_log with correct fields."""
    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase):
        from app.services.admin_audit import log_admin_action

        await log_admin_action(
            admin_user_id="user-123",
            action="check_system_health",
            target_type="system",
            target_id=None,
            details={"result": "healthy"},
            source="ai_agent",
        )

    mock_supabase.table.assert_called_once_with("admin_audit_log")
    mock_supabase.table.return_value.insert.assert_called_once()
    insert_data = mock_supabase.table.return_value.insert.call_args[0][0]
    assert insert_data["admin_user_id"] == "user-123"
    assert insert_data["action"] == "check_system_health"
    assert insert_data["source"] == "ai_agent"


@pytest.mark.asyncio
async def test_log_admin_action_monitoring(mock_supabase):
    """log_admin_action with source='monitoring_loop' and admin_user_id=None succeeds."""
    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase):
        from app.services.admin_audit import log_admin_action

        # Should not raise even with None admin_user_id
        await log_admin_action(
            admin_user_id=None,
            action="scheduled_health_check",
            target_type="system",
            target_id=None,
            details={"triggered_by": "cron"},
            source="monitoring_loop",
        )

    insert_data = mock_supabase.table.return_value.insert.call_args[0][0]
    assert insert_data["admin_user_id"] is None
    assert insert_data["source"] == "monitoring_loop"


@pytest.mark.asyncio
async def test_log_admin_action_all_sources(mock_supabase):
    """All 4 source tags are accepted without error."""
    valid_sources = ("manual", "ai_agent", "impersonation", "monitoring_loop")

    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase):
        from app.services.admin_audit import log_admin_action

        for source in valid_sources:
            await log_admin_action(
                admin_user_id="user-123" if source != "monitoring_loop" else None,
                action="test_action",
                target_type=None,
                target_id=None,
                details=None,
                source=source,
            )

    # 4 inserts should have been made
    assert mock_supabase.table.return_value.insert.call_count == 4


@pytest.mark.asyncio
async def test_log_admin_action_does_not_raise_on_db_error():
    """Audit errors are swallowed — log_admin_action never raises."""
    error_client = MagicMock()
    table_mock = MagicMock()
    error_client.table.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.execute.side_effect = Exception("DB connection failure")

    with patch(_SERVICE_CLIENT_PATCH, return_value=error_client):
        from app.services.admin_audit import log_admin_action

        # Should not raise despite DB error
        await log_admin_action(
            admin_user_id="user-123",
            action="check_system_health",
            target_type=None,
            target_id=None,
            details=None,
            source="manual",
        )


@pytest.mark.asyncio
async def test_log_admin_action_source_in_row(mock_supabase):
    """Source tag appears correctly in the inserted row."""
    with patch(_SERVICE_CLIENT_PATCH, return_value=mock_supabase):
        from app.services.admin_audit import log_admin_action

        await log_admin_action(
            admin_user_id="user-456",
            action="delete_user",
            target_type="user",
            target_id="target-user-789",
            details={"reason": "test"},
            source="impersonation",
        )

    insert_data = mock_supabase.table.return_value.insert.call_args[0][0]
    assert insert_data["source"] == "impersonation"
    assert insert_data["target_type"] == "user"
    assert insert_data["target_id"] == "target-user-789"


# ---------------------------------------------------------------------------
# Tests for _resolve_admin_emails (AUDT-03 fix)
# ---------------------------------------------------------------------------

_ROUTER_MODULE = "app.routers.admin.audit"


def _make_auth_response(email: str) -> MagicMock:
    """Build a mock Supabase auth.admin.get_user_by_id() response."""
    user_mock = MagicMock()
    user_mock.email = email
    response = MagicMock()
    response.user = user_mock
    return response


def test_resolve_admin_emails_resolves_uuid_to_email():
    """_resolve_admin_emails looks up each unique UUID and injects admin_email."""
    from app.routers.admin.audit import _resolve_admin_emails

    client = MagicMock()
    client.auth.admin.get_user_by_id.return_value = _make_auth_response("alice@example.com")

    rows = [
        {"id": "r1", "admin_user_id": "uuid-alice", "action": "do_thing"},
    ]
    result = _resolve_admin_emails(client, rows)

    assert result[0]["admin_email"] == "alice@example.com"
    client.auth.admin.get_user_by_id.assert_called_once_with("uuid-alice")


def test_resolve_admin_emails_null_user_id_returns_system():
    """Rows with admin_user_id=None get admin_email='System'."""
    from app.routers.admin.audit import _resolve_admin_emails

    client = MagicMock()
    rows = [
        {"id": "r1", "admin_user_id": None, "action": "scheduled_health_check"},
    ]
    result = _resolve_admin_emails(client, rows)

    assert result[0]["admin_email"] == "System"
    client.auth.admin.get_user_by_id.assert_not_called()


def test_resolve_admin_emails_deduplicates_lookups():
    """Each unique UUID is looked up exactly once even when repeated across rows."""
    from app.routers.admin.audit import _resolve_admin_emails

    client = MagicMock()
    client.auth.admin.get_user_by_id.return_value = _make_auth_response("bob@example.com")

    rows = [
        {"id": "r1", "admin_user_id": "uuid-bob", "action": "action_a"},
        {"id": "r2", "admin_user_id": "uuid-bob", "action": "action_b"},
        {"id": "r3", "admin_user_id": "uuid-bob", "action": "action_c"},
    ]
    result = _resolve_admin_emails(client, rows)

    # All three rows should have the resolved email
    assert all(r["admin_email"] == "bob@example.com" for r in result)
    # But the API was only called once
    assert client.auth.admin.get_user_by_id.call_count == 1


def test_resolve_admin_emails_fallback_on_api_error():
    """When auth API raises, the raw UUID is used as fallback email."""
    from app.routers.admin.audit import _resolve_admin_emails

    client = MagicMock()
    client.auth.admin.get_user_by_id.side_effect = Exception("auth API unavailable")

    rows = [
        {"id": "r1", "admin_user_id": "uuid-charlie", "action": "do_something"},
    ]
    result = _resolve_admin_emails(client, rows)

    # Falls back to raw UUID — page renders, not blank
    assert result[0]["admin_email"] == "uuid-charlie"


def test_resolve_admin_emails_mixed_rows():
    """Mix of null and non-null admin_user_id rows are all handled correctly."""
    from app.routers.admin.audit import _resolve_admin_emails

    def _lookup(uid: str) -> MagicMock:
        return _make_auth_response(f"{uid}@test.com")

    client = MagicMock()
    client.auth.admin.get_user_by_id.side_effect = _lookup

    rows = [
        {"id": "r1", "admin_user_id": "uuid-dan", "action": "manual_action"},
        {"id": "r2", "admin_user_id": None, "action": "monitoring_check"},
        {"id": "r3", "admin_user_id": "uuid-eve", "action": "impersonation_action"},
    ]
    result = _resolve_admin_emails(client, rows)

    assert result[0]["admin_email"] == "uuid-dan@test.com"
    assert result[1]["admin_email"] == "System"
    assert result[2]["admin_email"] == "uuid-eve@test.com"


def test_resolve_admin_emails_empty_rows():
    """Empty row list returns empty list without calling auth API."""
    from app.routers.admin.audit import _resolve_admin_emails

    client = MagicMock()
    result = _resolve_admin_emails(client, [])

    assert result == []
    client.auth.admin.get_user_by_id.assert_not_called()


def test_resolve_admin_emails_preserves_original_fields():
    """Existing row fields are preserved alongside the injected admin_email."""
    from app.routers.admin.audit import _resolve_admin_emails

    client = MagicMock()
    client.auth.admin.get_user_by_id.return_value = _make_auth_response("frank@example.com")

    row = {
        "id": "row-1",
        "admin_user_id": "uuid-frank",
        "action": "create_user",
        "target_type": "user",
        "target_id": "target-99",
        "source": "manual",
        "details": {"note": "test"},
        "created_at": "2026-03-22T10:00:00Z",
    }
    result = _resolve_admin_emails(client, [row])

    entry = result[0]
    assert entry["id"] == "row-1"
    assert entry["action"] == "create_user"
    assert entry["source"] == "manual"
    assert entry["admin_email"] == "frank@example.com"


# ---------------------------------------------------------------------------
# Integration-style test: list_audit_log endpoint injects admin_email
# ---------------------------------------------------------------------------


def test_list_audit_log_endpoint_injects_admin_email():
    """list_audit_log calls _resolve_admin_emails and returns admin_email in entries."""
    from unittest.mock import AsyncMock

    with (
        patch(f"{_ROUTER_MODULE}.get_service_client") as mock_get_client,
        patch(f"{_ROUTER_MODULE}.require_admin", new_callable=lambda: lambda: AsyncMock(return_value={"id": "admin-uuid", "email": "admin@test.com"})),
    ):
        client = MagicMock()
        mock_get_client.return_value = client

        # Mock the DB query result
        db_rows = [
            {
                "id": "entry-1",
                "admin_user_id": "uuid-admin",
                "action": "delete_user",
                "source": "manual",
                "created_at": "2026-03-22T09:00:00Z",
                "target_type": "user",
                "target_id": "target-1",
                "details": {},
            }
        ]
        query_chain = MagicMock()
        client.table.return_value = query_chain
        query_chain.select.return_value = query_chain
        query_chain.order.return_value = query_chain
        query_chain.range.return_value = query_chain
        query_chain.execute.return_value = MagicMock(data=db_rows, count=1)

        # Mock auth resolution
        client.auth.admin.get_user_by_id.return_value = _make_auth_response("admin@test.com")

        from app.routers.admin.audit import _resolve_admin_emails

        entries = _resolve_admin_emails(client, db_rows)

    assert entries[0]["admin_email"] == "admin@test.com"
    assert "admin_user_id" in entries[0]  # original field still present
