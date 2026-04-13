"""Unit tests for AdminAgent get_feature_adoption tool and FeatureAdoptionService (Phase 69, Plan 01).

Tests verify:
- Test 7: Returns agent_adoption list with agent_name, unique_tools_used, total_calls, top_tools
- Test 8: When user_id is provided, filters to that user's activity only
- Test 9: When user_id is None, returns platform-wide adoption metrics
- Autonomy gate: blocked tier returns error dict
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_CHECK_AUTONOMY_PATCH = "app.agents.admin.tools.adoption._check_autonomy"
_FEATURE_ADOPTION_SERVICE_PATCH = "app.agents.admin.tools.adoption.FeatureAdoptionService"
_SERVICE_CLIENT_PATCH = "app.services.feature_adoption_service.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.services.feature_adoption_service.execute_async"

_TEST_USER_ID = "user-aaaabbbb-cccc-dddd-eeee-ffffaaaabbbb"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_telemetry_rows(*, with_user_filter: bool = False) -> list[dict]:
    """Build sample tool_telemetry rows for testing grouping logic."""
    user_id = _TEST_USER_ID if with_user_filter else "user-other-111"
    rows = [
        {
            "tool_name": "get_usage_stats",
            "agent_name": "AdminAgent",
            "user_id": _TEST_USER_ID,
            "status": "success",
            "created_at": "2026-04-10T10:00:00Z",
        },
        {
            "tool_name": "get_usage_stats",
            "agent_name": "AdminAgent",
            "user_id": _TEST_USER_ID,
            "status": "success",
            "created_at": "2026-04-11T10:00:00Z",
        },
        {
            "tool_name": "check_system_health",
            "agent_name": "AdminAgent",
            "user_id": _TEST_USER_ID,
            "status": "success",
            "created_at": "2026-04-11T11:00:00Z",
        },
        {
            "tool_name": "generate_followup_email",
            "agent_name": "SalesAgent",
            "user_id": user_id,
            "status": "success",
            "created_at": "2026-04-11T12:00:00Z",
        },
        {
            "tool_name": "score_hubspot_lead",
            "agent_name": "SalesAgent",
            "user_id": _TEST_USER_ID,
            "status": "success",
            "created_at": "2026-04-12T09:00:00Z",
        },
    ]
    return rows


# ---------------------------------------------------------------------------
# Test 7: Returns agent_adoption with expected fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_feature_adoption_structure():
    """get_feature_adoption returns agent_adoption list with correct fields."""
    mock_service = MagicMock()
    mock_service.compute_adoption = AsyncMock(
        return_value={
            "agent_adoption": [
                {
                    "agent_name": "AdminAgent",
                    "unique_tools_used": 2,
                    "total_calls": 3,
                    "top_tools": [
                        {"tool_name": "get_usage_stats", "call_count": 2},
                        {"tool_name": "check_system_health", "call_count": 1},
                    ],
                    "unique_users": 1,
                }
            ],
            "total_agents_active": 1,
            "total_unique_tools": 2,
            "period_days": 30,
        }
    )

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_FEATURE_ADOPTION_SERVICE_PATCH, return_value=mock_service):
            from app.agents.admin.tools.adoption import get_feature_adoption

            result = await get_feature_adoption(days=30, user_id=None)

    assert "agent_adoption" in result
    assert isinstance(result["agent_adoption"], list)
    assert len(result["agent_adoption"]) >= 1

    entry = result["agent_adoption"][0]
    assert "agent_name" in entry
    assert "unique_tools_used" in entry
    assert "total_calls" in entry
    assert "top_tools" in entry

    assert "total_agents_active" in result
    assert "total_unique_tools" in result
    assert "period_days" in result


# ---------------------------------------------------------------------------
# Test 8: When user_id is provided, filters to that user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_feature_adoption_user_filter():
    """get_feature_adoption passes user_id to service for per-user filtering."""
    mock_service = MagicMock()
    mock_service.compute_adoption = AsyncMock(
        return_value={
            "agent_adoption": [],
            "total_agents_active": 0,
            "total_unique_tools": 0,
            "period_days": 30,
        }
    )

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_FEATURE_ADOPTION_SERVICE_PATCH, return_value=mock_service):
            from app.agents.admin.tools.adoption import get_feature_adoption

            await get_feature_adoption(days=30, user_id=_TEST_USER_ID)

    # Verify service was called with the user_id filter
    mock_service.compute_adoption.assert_awaited_once_with(days=30, user_id=_TEST_USER_ID)


# ---------------------------------------------------------------------------
# Test 9: When user_id is None, returns platform-wide metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_feature_adoption_platform_wide():
    """When user_id is None, get_feature_adoption returns platform-wide metrics."""
    mock_service = MagicMock()
    mock_service.compute_adoption = AsyncMock(
        return_value={
            "agent_adoption": [
                {
                    "agent_name": "AdminAgent",
                    "unique_tools_used": 2,
                    "total_calls": 3,
                    "top_tools": [],
                    "unique_users": 3,
                }
            ],
            "total_agents_active": 1,
            "total_unique_tools": 2,
            "period_days": 30,
        }
    )

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_FEATURE_ADOPTION_SERVICE_PATCH, return_value=mock_service):
            from app.agents.admin.tools.adoption import get_feature_adoption

            result = await get_feature_adoption(days=30, user_id=None)

    # Verify service was called without a user_id
    mock_service.compute_adoption.assert_awaited_once_with(days=30, user_id=None)

    # When platform-wide, unique_users should be present in entries
    entry = result["agent_adoption"][0]
    assert "unique_users" in entry


# ---------------------------------------------------------------------------
# Test 10: Autonomy gate — blocked tier
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_feature_adoption_autonomy_blocked():
    """get_feature_adoption returns error dict when autonomy tier is blocked."""
    gate = {"error": "get_feature_adoption is blocked by admin configuration."}

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=gate)):
        from app.agents.admin.tools.adoption import get_feature_adoption

        result = await get_feature_adoption()

    assert "error" in result
    assert "agent_adoption" not in result


# ---------------------------------------------------------------------------
# FeatureAdoptionService unit tests (grouping logic)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_feature_adoption_service_grouping():
    """FeatureAdoptionService.compute_adoption groups tool_telemetry by agent correctly."""
    import os

    telemetry_rows = _make_telemetry_rows()
    mock_execute = AsyncMock(return_value=MagicMock(data=telemetry_rows))
    mock_client = MagicMock()

    with patch.dict(os.environ, {"SUPABASE_URL": "http://localhost", "SUPABASE_SERVICE_ROLE_KEY": "test-key"}):
        with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
            with patch(_EXECUTE_ASYNC_PATCH, new=mock_execute):
                from app.services.feature_adoption_service import FeatureAdoptionService

                svc = FeatureAdoptionService()
                result = await svc.compute_adoption(days=30, user_id=None)

    assert "agent_adoption" in result
    agents = {a["agent_name"]: a for a in result["agent_adoption"]}
    assert "AdminAgent" in agents
    admin_entry = agents["AdminAgent"]
    assert admin_entry["total_calls"] == 3
    assert admin_entry["unique_tools_used"] == 2
    assert len(admin_entry["top_tools"]) <= 5


@pytest.mark.asyncio
async def test_feature_adoption_service_user_filter():
    """FeatureAdoptionService.compute_adoption filters rows by user_id when provided."""
    import os

    telemetry_rows = _make_telemetry_rows()

    # Only rows for _TEST_USER_ID should be included
    # _make_telemetry_rows with_user_filter=False has SalesAgent row for "user-other-111"
    expected_user_rows = [r for r in telemetry_rows if r["user_id"] == _TEST_USER_ID]

    mock_execute = AsyncMock(return_value=MagicMock(data=expected_user_rows))
    mock_client = MagicMock()

    with patch.dict(os.environ, {"SUPABASE_URL": "http://localhost", "SUPABASE_SERVICE_ROLE_KEY": "test-key"}):
        with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
            with patch(_EXECUTE_ASYNC_PATCH, new=mock_execute):
                from app.services.feature_adoption_service import FeatureAdoptionService

                svc = FeatureAdoptionService()
                result = await svc.compute_adoption(days=30, user_id=_TEST_USER_ID)

    assert "agent_adoption" in result
    # unique_users should NOT appear in per-user result (or be absent)
    for entry in result["agent_adoption"]:
        assert "unique_users" not in entry
