"""Unit tests for admin audit logging service.

Tests verify:
- log_admin_action inserts row into admin_audit_log table
- monitoring_loop source with admin_user_id=None succeeds
- All 4 source tags are accepted ('manual', 'ai_agent', 'impersonation', 'monitoring_loop')
"""
import pytest
from unittest.mock import MagicMock, patch


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
