"""Unit tests for AdminAgent governance tools — Phase 15.

Tests verify:
- test_recommend_autonomy_tier_read_only: read-only action recommends "auto"
- test_recommend_autonomy_tier_financial: financial mutation recommends "confirm"
- test_recommend_autonomy_tier_blocked: destructive action (delete_all_users) recommends "blocked"
- test_generate_compliance_report: returns narrative summary with action_count, grouped_by_source, key_actions
- test_generate_compliance_report_empty: no audit entries returns empty report with zero counts
- test_suggest_role_permissions_read_only: "read-only analyst" returns read-only section-action matrix
- test_suggest_role_permissions_full_access: "full operations lead" returns read+write on most sections
- test_generate_daily_digest: returns structured digest with all four sections
- test_generate_daily_digest_empty: zero items in all sections when no data
- test_classify_and_escalate_high: high-severity returns severity="high", escalated=True, routed_to="super_admin"
- test_classify_and_escalate_low: low-severity returns severity="low", escalated=False
- test_classify_and_escalate_autonomy_confirm: confirm-tier returns requires_confirmation on autonomy gate
- test_list_all_approvals_tool: returns pending approvals list from DB
- test_override_approval_tool: confirm-tier, updates approval status and logs audit
- test_manage_admin_role_tool: confirm-tier, creates/updates admin role via user_roles table
- test_admin_agent_tool_count: total tools in AdminAgent __all__ >= 58
"""

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Patch targets scoped to governance module
# ---------------------------------------------------------------------------
_SERVICE_CLIENT_PATCH = "app.agents.admin.tools.governance.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.agents.admin.tools.governance.execute_async"
_AUTONOMY_PATCH = "app.agents.admin.tools.governance._check_autonomy"
_AUDIT_PATCH = "app.agents.admin.tools.governance.log_admin_action"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_result(data: list) -> MagicMock:
    """Build a mock Supabase query result."""
    result = MagicMock()
    result.data = data
    return result


def _make_supabase_client_chain(data: list) -> MagicMock:
    """Build a mock Supabase client that returns the given data for .execute()."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.neq.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.filter.return_value = table_mock
    table_mock.gte.return_value = table_mock
    table_mock.lte.return_value = table_mock
    table_mock.lt.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.upsert.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=data)
    return client


# ---------------------------------------------------------------------------
# Test 1: recommend_autonomy_tier - read-only action → "auto"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recommend_autonomy_tier_read_only():
    """recommend_autonomy_tier recommends 'auto' for a read-only action."""
    from app.agents.admin.tools.governance import recommend_autonomy_tier

    with patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        result = await recommend_autonomy_tier(
            action_name="list_users",
            action_description="List all users in the system",
        )

    assert result["recommended_tier"] == "auto"
    assert "reasoning" in result
    assert "risk_factors" in result
    assert result["action_name"] == "list_users"


# ---------------------------------------------------------------------------
# Test 2: recommend_autonomy_tier - financial action → "confirm"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recommend_autonomy_tier_financial():
    """recommend_autonomy_tier recommends 'confirm' for a financial mutation."""
    from app.agents.admin.tools.governance import recommend_autonomy_tier

    with patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        result = await recommend_autonomy_tier(
            action_name="process_refund",
            action_description="Issue a refund for a payment charge",
        )

    assert result["recommended_tier"] == "confirm"
    assert "reasoning" in result


# ---------------------------------------------------------------------------
# Test 3: recommend_autonomy_tier - destructive action → "blocked"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recommend_autonomy_tier_blocked():
    """recommend_autonomy_tier recommends 'blocked' for delete_all_users."""
    from app.agents.admin.tools.governance import recommend_autonomy_tier

    with patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        result = await recommend_autonomy_tier(
            action_name="delete_all_users",
            action_description="Permanently delete all user accounts from the database",
        )

    assert result["recommended_tier"] == "blocked"
    assert "reasoning" in result


# ---------------------------------------------------------------------------
# Test 4: generate_compliance_report returns narrative summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_compliance_report():
    """generate_compliance_report returns action_count, grouped_by_source, key_actions, narrative."""
    from app.agents.admin.tools.governance import generate_compliance_report

    audit_rows = [
        {
            "action": "list_users",
            "source": "ai_agent",
            "admin_user_id": "admin-001",
            "created_at": "2026-03-01T10:00:00Z",
        },
        {
            "action": "list_users",
            "source": "ai_agent",
            "admin_user_id": "admin-001",
            "created_at": "2026-03-02T10:00:00Z",
        },
        {
            "action": "update_agent_config",
            "source": "manual",
            "admin_user_id": "admin-002",
            "created_at": "2026-03-03T10:00:00Z",
        },
    ]
    mock_result = _make_mock_result(audit_rows)

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_SERVICE_CLIENT_PATCH, return_value=_make_supabase_client_chain(audit_rows)),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_result)),
    ):
        result = await generate_compliance_report(
            start_date="2026-03-01",
            end_date="2026-03-31",
        )

    assert result["total_actions"] == 3
    assert "by_source" in result
    assert result["by_source"].get("ai_agent") == 2
    assert result["by_source"].get("manual") == 1
    assert "narrative" in result
    assert isinstance(result["narrative"], str)
    assert len(result["narrative"]) > 10
    assert "key_actions" in result


# ---------------------------------------------------------------------------
# Test 5: generate_compliance_report empty range
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_compliance_report_empty():
    """generate_compliance_report returns zero counts for empty date range."""
    from app.agents.admin.tools.governance import generate_compliance_report

    mock_result = _make_mock_result([])

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_SERVICE_CLIENT_PATCH, return_value=_make_supabase_client_chain([])),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_result)),
    ):
        result = await generate_compliance_report(
            start_date="2026-01-01",
            end_date="2026-01-02",
        )

    assert result["total_actions"] == 0
    assert "narrative" in result


# ---------------------------------------------------------------------------
# Test 6: suggest_role_permissions - read-only analyst
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suggest_role_permissions_read_only():
    """suggest_role_permissions returns read-only permissions for an analyst role."""
    from app.agents.admin.tools.governance import suggest_role_permissions

    with patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        result = await suggest_role_permissions(
            role_description="read-only analyst who can view dashboards",
        )

    assert "suggested_permissions" in result
    assert isinstance(result["suggested_permissions"], list)
    # All permissions should be read-only — no "write" or "manage" in allowed_actions
    for perm in result["suggested_permissions"]:
        actions = perm.get("allowed_actions", [])
        assert "write" not in actions, f"Expected no write, got {actions}"
        assert "manage" not in actions, f"Expected no manage, got {actions}"
    assert "reasoning" in result


# ---------------------------------------------------------------------------
# Test 7: suggest_role_permissions - full access operations lead
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suggest_role_permissions_full_access():
    """suggest_role_permissions returns read+write for full operations lead."""
    from app.agents.admin.tools.governance import suggest_role_permissions

    with patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        result = await suggest_role_permissions(
            role_description="full operations lead with access to everything",
        )

    assert "suggested_permissions" in result
    # At least some permissions should include write
    all_actions = []
    for perm in result["suggested_permissions"]:
        all_actions.extend(perm.get("allowed_actions", []))
    assert "write" in all_actions or "manage" in all_actions, (
        f"Expected write/manage in some permission, got: {all_actions}"
    )


# ---------------------------------------------------------------------------
# Test 8: generate_daily_digest returns structured digest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_daily_digest():
    """generate_daily_digest returns all four sections with data."""
    from app.agents.admin.tools.governance import generate_daily_digest

    approval_rows = [
        {"id": "appr-001", "status": "PENDING", "created_at": "2026-03-25T10:00:00Z"},
        {"id": "appr-002", "status": "PENDING", "created_at": "2026-03-25T11:00:00Z"},
    ]
    subscription_rows = [
        {"id": "sub-001", "user_id": "user-001", "current_period_end": "2026-03-26T00:00:00Z"},
    ]
    # pending_approvals + at_risk_users + anomalies + upcoming_expirations
    execute_mock = AsyncMock(
        side_effect=[
            _make_mock_result(approval_rows),   # pending_approvals
            _make_mock_result([]),               # at_risk_users
            _make_mock_result([]),               # anomalies
            _make_mock_result(subscription_rows),  # upcoming_expirations
        ]
    )

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_SERVICE_CLIENT_PATCH, return_value=_make_supabase_client_chain([])),
        patch(_EXECUTE_ASYNC_PATCH, new=execute_mock),
    ):
        result = await generate_daily_digest()

    assert "generated_at" in result
    assert "pending_approvals" in result
    assert result["pending_approvals"]["count"] == 2
    assert "at_risk_users" in result
    assert "anomalies" in result
    assert "upcoming_expirations" in result
    assert "narrative" in result


# ---------------------------------------------------------------------------
# Test 9: generate_daily_digest empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_daily_digest_empty():
    """generate_daily_digest returns zero counts for all sections when no data."""
    from app.agents.admin.tools.governance import generate_daily_digest

    execute_mock = AsyncMock(
        side_effect=[
            _make_mock_result([]),  # pending_approvals
            _make_mock_result([]),  # at_risk_users
            _make_mock_result([]),  # anomalies
            _make_mock_result([]),  # upcoming_expirations
        ]
    )

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_SERVICE_CLIENT_PATCH, return_value=_make_supabase_client_chain([])),
        patch(_EXECUTE_ASYNC_PATCH, new=execute_mock),
    ):
        result = await generate_daily_digest()

    assert result["pending_approvals"]["count"] == 0
    assert result["at_risk_users"]["count"] == 0
    assert result["anomalies"]["count"] == 0
    assert result["upcoming_expirations"]["count"] == 0


# ---------------------------------------------------------------------------
# Test 10: classify_and_escalate - high severity escalates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_and_escalate_high():
    """classify_and_escalate returns severity='high', escalated=True for high-severity issue."""
    from app.agents.admin.tools.governance import classify_and_escalate

    confirm_gate = {
        "requires_confirmation": False,  # auto proceed for this test
    }

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_AUDIT_PATCH, new=AsyncMock(return_value=None)),
    ):
        result = await classify_and_escalate(
            issue_description="Multiple users experiencing auth failure and degraded performance",
            issue_context={"affected_users": 50},
        )

    assert result["severity"] in ("high", "critical")
    assert result["escalated"] is True
    assert result["routed_to"] == "super_admin"
    assert "recommended_action" in result


# ---------------------------------------------------------------------------
# Test 11: classify_and_escalate - low severity does NOT escalate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_and_escalate_low():
    """classify_and_escalate returns severity='low', escalated=False for a minor suggestion."""
    from app.agents.admin.tools.governance import classify_and_escalate

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_AUDIT_PATCH, new=AsyncMock(return_value=None)),
    ):
        result = await classify_and_escalate(
            issue_description="Minor cosmetic suggestion about button color",
            issue_context=None,
        )

    assert result["severity"] in ("low", "medium")
    assert result["escalated"] is False
    assert result["routed_to"] is None


# ---------------------------------------------------------------------------
# Test 12: classify_and_escalate - autonomy confirm gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_and_escalate_autonomy_confirm():
    """classify_and_escalate returns requires_confirmation when autonomy gate fires."""
    from app.agents.admin.tools.governance import classify_and_escalate

    confirm_gate = {
        "requires_confirmation": True,
        "confirmation_token": "token-xyz-456",
        "action_details": {"action": "classify_and_escalate", "risk_level": "low"},
    }

    with patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=confirm_gate)):
        result = await classify_and_escalate(
            issue_description="Some issue",
            issue_context=None,
        )

    assert result.get("requires_confirmation") is True
    assert "confirmation_token" in result


# ---------------------------------------------------------------------------
# Test 13: list_all_approvals_tool returns pending list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_all_approvals_tool():
    """list_all_approvals returns pending approvals list from DB."""
    from app.agents.admin.tools.governance import list_all_approvals

    approval_rows = [
        {"id": "appr-001", "status": "PENDING", "user_id": "user-001"},
        {"id": "appr-002", "status": "PENDING", "user_id": "user-002"},
    ]
    mock_result = _make_mock_result(approval_rows)

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_SERVICE_CLIENT_PATCH, return_value=_make_supabase_client_chain(approval_rows)),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_result)),
    ):
        result = await list_all_approvals(status="PENDING", limit=20)

    assert "approvals" in result
    assert len(result["approvals"]) == 2
    assert result["total"] == 2


# ---------------------------------------------------------------------------
# Test 14: override_approval_tool - confirm-tier, logs audit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_override_approval_tool():
    """override_approval is confirm-tier; updates approval status and logs audit."""
    from app.agents.admin.tools.governance import override_approval

    # Existing approval row
    existing_row = {"id": "appr-001", "status": "PENDING", "user_id": "user-001"}
    fetch_result = _make_mock_result([existing_row])
    update_result = _make_mock_result([{**existing_row, "status": "APPROVED"}])

    execute_mock = AsyncMock(side_effect=[fetch_result, update_result])

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_SERVICE_CLIENT_PATCH, return_value=_make_supabase_client_chain([])),
        patch(_EXECUTE_ASYNC_PATCH, new=execute_mock),
        patch(_AUDIT_PATCH, new=AsyncMock(return_value=None)) as mock_audit,
    ):
        result = await override_approval(
            approval_id="appr-001",
            decision="APPROVED",
            reason="Manually approved by super admin",
            confirmation_token="confirmed-token",
        )

    assert result.get("success") is True
    assert result.get("approval_id") == "appr-001"
    mock_audit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 15: manage_admin_role_tool - confirm-tier, assigns role
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manage_admin_role_tool():
    """manage_admin_role is confirm-tier; creates/updates admin role via user_roles table."""
    from app.agents.admin.tools.governance import manage_admin_role

    upsert_result = _make_mock_result([{"user_id": "user-001", "role": "admin"}])
    execute_mock = AsyncMock(return_value=upsert_result)

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_SERVICE_CLIENT_PATCH, return_value=_make_supabase_client_chain([])),
        patch(_EXECUTE_ASYNC_PATCH, new=execute_mock),
        patch(_AUDIT_PATCH, new=AsyncMock(return_value=None)) as mock_audit,
    ):
        result = await manage_admin_role(
            target_user_id="user-001",
            role="admin",
            action="assign",
            confirmation_token="confirmed-token",
        )

    assert result.get("success") is True
    assert result.get("user_id") == "user-001"
    mock_audit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 16: AdminAgent __all__ has 58+ tools
# ---------------------------------------------------------------------------


def test_admin_agent_tool_count():
    """Total tools in AdminAgent __all__ >= 58 (50 existing + 8 new governance tools)."""
    from app.agents.admin.tools import __all__ as all_tools

    tool_count = len(all_tools)
    assert tool_count >= 58, (
        f"Expected at least 58 tools in AdminAgent __all__, got {tool_count}. "
        f"Tools: {sorted(all_tools)}"
    )
