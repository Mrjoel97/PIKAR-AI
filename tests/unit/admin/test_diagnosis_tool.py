"""Unit tests for AdminAgent diagnose_user_problem tool (Phase 69, Plan 01).

Tests verify:
- Test 1: When OAuth tokens are expired/missing, diagnosis includes "integration_issues"
- Test 2: When API health endpoints are degraded, diagnosis includes "platform_health_issues"
- Test 3: When ad budget cap is exceeded, diagnosis includes "budget_cap_exceeded"
- Test 4: When pending approvals exist, diagnosis includes "pending_approvals"
- Test 5: When all checks pass, diagnosis returns "no_issues_found" with all_clear=True
- Test 6: Returns a plain_english_summary string that a non-technical user can understand
- Autonomy gate: blocked tier returns error dict
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_CHECK_AUTONOMY_PATCH = "app.agents.admin.tools.diagnosis._check_autonomy"
_SERVICE_CLIENT_PATCH = "app.agents.admin.tools.diagnosis.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.agents.admin.tools.diagnosis.execute_async"

_TEST_USER_ID = "user-aaaabbbb-cccc-dddd-eeee-ffffaaaabbbb"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_execute_side_effect(*row_lists: list[dict]):
    """Return a side_effect that pops from the given sequence of row lists."""
    seq = [MagicMock(data=rows) for rows in row_lists]

    async def _side_effect(query, op_name=""):
        return seq.pop(0)

    return _side_effect


def _mock_client():
    """Return a MagicMock Supabase client."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Test 1: OAuth tokens expired/missing → integration_issues
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnose_integration_issues():
    """When MCP integrations exist but inactive, integration_issues is populated."""
    # user_mcp_integrations: has integrations, is_active=False → flagged
    oauth_rows = [
        {"user_id": _TEST_USER_ID, "provider": "google", "is_active": False},
        {"user_id": _TEST_USER_ID, "provider": "slack", "is_active": False},
    ]
    # api_health_checks: all healthy
    health_rows = [{"endpoint": "live", "status": "healthy", "response_time_ms": 80}]
    # ad_budget_caps: no exceeded caps
    budget_rows: list[dict] = []
    # governance_approvals: no pending
    approval_rows: list[dict] = []

    side_effect = _make_execute_side_effect(oauth_rows, health_rows, budget_rows, approval_rows)

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_SERVICE_CLIENT_PATCH, return_value=_mock_client()):
            with patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(side_effect=side_effect)):
                from app.agents.admin.tools.diagnosis import diagnose_user_problem

                result = await diagnose_user_problem(_TEST_USER_ID)

    assert "issues" in result
    assert "plain_english_summary" in result
    categories = [i["category"] for i in result["issues"]]
    assert "integration_issues" in categories

    # Should mention the providers
    integration_issue = next(i for i in result["issues"] if i["category"] == "integration_issues")
    assert "details" in integration_issue
    assert "recommended_action" in integration_issue
    assert "severity" in integration_issue


# ---------------------------------------------------------------------------
# Test 2: API health degraded → platform_health_issues
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnose_platform_health_issues():
    """When API health endpoints are degraded, platform_health_issues is populated."""
    oauth_rows: list[dict] = []
    health_rows = [
        {"endpoint": "live", "status": "healthy", "response_time_ms": 80},
        {"endpoint": "embeddings", "status": "unhealthy", "response_time_ms": None},
        {"endpoint": "cache", "status": "degraded", "response_time_ms": 3000},
    ]
    budget_rows: list[dict] = []
    approval_rows: list[dict] = []

    side_effect = _make_execute_side_effect(oauth_rows, health_rows, budget_rows, approval_rows)

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_SERVICE_CLIENT_PATCH, return_value=_mock_client()):
            with patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(side_effect=side_effect)):
                from app.agents.admin.tools.diagnosis import diagnose_user_problem

                result = await diagnose_user_problem(_TEST_USER_ID)

    assert "issues" in result
    categories = [i["category"] for i in result["issues"]]
    assert "platform_health_issues" in categories

    health_issue = next(i for i in result["issues"] if i["category"] == "platform_health_issues")
    assert "details" in health_issue
    # Should reference the degraded endpoints
    details_str = str(health_issue["details"])
    assert "embeddings" in details_str or "cache" in details_str


# ---------------------------------------------------------------------------
# Test 3: Ad budget cap exceeded → budget_cap_exceeded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnose_budget_cap_exceeded():
    """When ad budget is exceeded, budget_cap_exceeded issue is included."""
    oauth_rows: list[dict] = []
    health_rows: list[dict] = []
    budget_rows = [
        {
            "user_id": _TEST_USER_ID,
            "platform": "google_ads",
            "monthly_cap_usd": 500.0,
            "current_spend_usd": 520.0,
        }
    ]
    approval_rows: list[dict] = []

    side_effect = _make_execute_side_effect(oauth_rows, health_rows, budget_rows, approval_rows)

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_SERVICE_CLIENT_PATCH, return_value=_mock_client()):
            with patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(side_effect=side_effect)):
                from app.agents.admin.tools.diagnosis import diagnose_user_problem

                result = await diagnose_user_problem(_TEST_USER_ID)

    assert "issues" in result
    categories = [i["category"] for i in result["issues"]]
    assert "budget_cap_exceeded" in categories

    budget_issue = next(i for i in result["issues"] if i["category"] == "budget_cap_exceeded")
    assert "details" in budget_issue
    details_str = str(budget_issue["details"])
    assert "google_ads" in details_str


# ---------------------------------------------------------------------------
# Test 4: Pending approvals exist → pending_approvals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnose_pending_approvals():
    """When pending governance approvals exist, pending_approvals issue is included."""
    oauth_rows: list[dict] = []
    health_rows: list[dict] = []
    budget_rows: list[dict] = []
    approval_rows = [
        {"user_id": _TEST_USER_ID, "status": "pending", "action_type": "create_campaign"},
        {"user_id": _TEST_USER_ID, "status": "pending", "action_type": "issue_refund"},
    ]

    side_effect = _make_execute_side_effect(oauth_rows, health_rows, budget_rows, approval_rows)

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_SERVICE_CLIENT_PATCH, return_value=_mock_client()):
            with patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(side_effect=side_effect)):
                from app.agents.admin.tools.diagnosis import diagnose_user_problem

                result = await diagnose_user_problem(_TEST_USER_ID)

    assert "issues" in result
    categories = [i["category"] for i in result["issues"]]
    assert "pending_approvals" in categories

    approval_issue = next(i for i in result["issues"] if i["category"] == "pending_approvals")
    assert "details" in approval_issue
    # Should include count of pending approvals
    details = approval_issue["details"]
    assert details.get("count") == 2 or "2" in str(details)


# ---------------------------------------------------------------------------
# Test 5: All checks pass → no_issues_found with all_clear=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnose_all_clear():
    """When all diagnostic checks pass, result has all_clear=True and no issues.

    The health check queries `.neq("status", "healthy")` so a healthy endpoint
    returns no rows — the mock reflects this by returning an empty list.
    """
    oauth_rows: list[dict] = []
    health_rows: list[dict] = []  # neq("status", "healthy") returns no rows for healthy endpoints
    budget_rows: list[dict] = []
    approval_rows: list[dict] = []

    side_effect = _make_execute_side_effect(oauth_rows, health_rows, budget_rows, approval_rows)

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_SERVICE_CLIENT_PATCH, return_value=_mock_client()):
            with patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(side_effect=side_effect)):
                from app.agents.admin.tools.diagnosis import diagnose_user_problem

                result = await diagnose_user_problem(_TEST_USER_ID)

    assert "all_clear" in result
    assert result["all_clear"] is True
    assert result.get("issues", []) == []
    assert "plain_english_summary" in result


# ---------------------------------------------------------------------------
# Test 6: plain_english_summary is a non-technical human-readable string
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnose_plain_english_summary_with_issues():
    """plain_english_summary describes issues in plain English when problems are found."""
    oauth_rows = [{"user_id": _TEST_USER_ID, "provider": "google", "is_active": False}]
    health_rows: list[dict] = []
    budget_rows: list[dict] = []
    approval_rows: list[dict] = []

    side_effect = _make_execute_side_effect(oauth_rows, health_rows, budget_rows, approval_rows)

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_SERVICE_CLIENT_PATCH, return_value=_mock_client()):
            with patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(side_effect=side_effect)):
                from app.agents.admin.tools.diagnosis import diagnose_user_problem

                result = await diagnose_user_problem(_TEST_USER_ID)

    summary = result["plain_english_summary"]
    assert isinstance(summary, str)
    assert len(summary) > 10
    # Should mention issues, not return raw JSON
    assert "{" not in summary or "issue" in summary.lower()


@pytest.mark.asyncio
async def test_diagnose_plain_english_summary_all_clear():
    """plain_english_summary says 'All systems look good' when all clear.

    Health check returns empty (no degraded endpoints found by neq filter).
    """
    oauth_rows: list[dict] = []
    health_rows: list[dict] = []  # neq("status", "healthy") returns empty when all healthy
    budget_rows: list[dict] = []
    approval_rows: list[dict] = []

    side_effect = _make_execute_side_effect(oauth_rows, health_rows, budget_rows, approval_rows)

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_SERVICE_CLIENT_PATCH, return_value=_mock_client()):
            with patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(side_effect=side_effect)):
                from app.agents.admin.tools.diagnosis import diagnose_user_problem

                result = await diagnose_user_problem(_TEST_USER_ID)

    summary = result["plain_english_summary"]
    assert "All systems" in summary or "all systems" in summary or "all clear" in summary.lower()


# ---------------------------------------------------------------------------
# Test 7: Autonomy gate — blocked tier
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnose_autonomy_blocked():
    """diagnose_user_problem returns error dict when autonomy tier is blocked."""
    gate = {"error": "diagnose_user_problem is blocked by admin configuration."}

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=gate)):
        from app.agents.admin.tools.diagnosis import diagnose_user_problem

        result = await diagnose_user_problem(_TEST_USER_ID)

    assert "error" in result
    assert "issues" not in result
