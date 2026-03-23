"""Unit tests for AdminAgent user intelligence tools (Phase 13, Plan 02).

Tests verify:
- get_at_risk_users returns watch list with declining usage and inactive logins
- get_at_risk_users degrades gracefully when Stripe is not configured
- get_at_risk_users includes billing_status when Stripe is available
- get_at_risk_users returns empty list when no users match criteria
- get_at_risk_users returns error dict when autonomy level is "blocked"
- get_user_support_context returns usage_summary, error_patterns, suggested_steps
- get_user_support_context returns empty error_patterns when no recent errors
- get_user_support_context returns error dict when autonomy level is "blocked"
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch targets at the users_intelligence module level
_SERVICE_CLIENT_PATCH = "app.agents.admin.tools.users_intelligence.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.agents.admin.tools.users_intelligence.execute_async"
_CHECK_AUTONOMY_PATCH = "app.agents.admin.tools.users_intelligence.check_autonomy"
_INTEGRATION_PROXY_PATCH = "app.agents.admin.tools.users_intelligence.IntegrationProxyService"

_TEST_USER_ID = "user-11111111-1111-1111-1111-111111111111"
_TEST_USER_EMAIL = "at-risk@example.com"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_execute_async(rows: list[dict]) -> AsyncMock:
    """AsyncMock for execute_async returning given rows."""
    return AsyncMock(return_value=MagicMock(data=rows))


def _make_session_rows(user_id: str = _TEST_USER_ID) -> list[dict]:
    """Recent session rows indicating this user was active in the last 28 days."""
    return [{"user_id": user_id, "updated_at": datetime.now(UTC).isoformat()}]


def _make_events_current(user_id: str = _TEST_USER_ID, count: int = 2) -> list[dict]:
    """Recent session_event rows for the current 14-day window (low count = declining)."""
    now = datetime.now(UTC)
    return [
        {"user_id": user_id, "created_at": (now - timedelta(days=i)).isoformat()}
        for i in range(count)
    ]


def _make_events_prior(user_id: str = _TEST_USER_ID, count: int = 10) -> list[dict]:
    """Session_event rows for the prior 14-day window (high count = prior activity)."""
    now = datetime.now(UTC)
    return [
        {"user_id": user_id, "created_at": (now - timedelta(days=14 + i)).isoformat()}
        for i in range(count)
    ]


def _make_auth_user(
    email: str = _TEST_USER_EMAIL,
    days_since_login: int = 15,
) -> MagicMock:
    """Build a mock Supabase auth user with last_sign_in_at set to N days ago."""
    auth_user = MagicMock()
    auth_user.email = email
    auth_user.last_sign_in_at = (
        datetime.now(UTC) - timedelta(days=days_since_login)
    ).isoformat()
    return auth_user


def _make_auth_response(user: MagicMock) -> MagicMock:
    """Wrap a mock auth user in the auth.admin.get_user_by_id response shape."""
    resp = MagicMock()
    resp.user = user
    return resp


# ---------------------------------------------------------------------------
# Test 1: get_at_risk_users — basic case (returns watch list)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_at_risk_users_basic():
    """get_at_risk_users returns at_risk_users list for users with declining usage."""
    user_id = _TEST_USER_ID

    # execute_async call order:
    # 1. sessions table (distinct users active in last 28 days)
    # 2. session_events current window per user
    # 3. session_events prior window per user
    # 4. user_executive_agents (email lookup per user)
    execute_seq = [
        MagicMock(data=_make_session_rows(user_id)),      # sessions
        MagicMock(data=_make_events_current(user_id, 2)), # current 14d — 2 events
        MagicMock(data=_make_events_prior(user_id, 10)),  # prior 14d — 10 events
        MagicMock(data=[{"user_id": user_id, "email": _TEST_USER_EMAIL}]),  # email
    ]

    async def _mock_execute_async(query, op_name=""):
        return execute_seq.pop(0)

    auth_user = _make_auth_user(days_since_login=15)
    auth_resp = _make_auth_response(auth_user)

    mock_client = MagicMock()

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
            with patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(side_effect=_mock_execute_async)):
                with patch("asyncio.to_thread", new=AsyncMock(return_value=auth_resp)):
                    with patch(_INTEGRATION_PROXY_PATCH) as mock_proxy_cls:
                        mock_proxy = MagicMock()
                        mock_proxy.call = AsyncMock(side_effect=Exception("not configured"))
                        mock_proxy_cls.return_value = mock_proxy

                        from app.agents.admin.tools.users_intelligence import get_at_risk_users

                        result = await get_at_risk_users(threshold_days_inactive=7)

    assert "at_risk_users" in result
    assert "criteria" in result
    assert isinstance(result["at_risk_users"], list)
    assert len(result["at_risk_users"]) >= 1

    user_entry = result["at_risk_users"][0]
    assert user_entry["user_id"] == user_id
    assert "email" in user_entry
    assert "last_sign_in_at" in user_entry
    assert "activity_decline_pct" in user_entry
    assert "billing_status" in user_entry
    assert "risk_factors" in user_entry


# ---------------------------------------------------------------------------
# Test 2: get_at_risk_users — Stripe not configured (graceful degradation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_at_risk_users_no_stripe():
    """get_at_risk_users returns billing_status='unknown (Stripe not configured)' when Stripe fails."""
    user_id = _TEST_USER_ID

    execute_seq = [
        MagicMock(data=_make_session_rows(user_id)),
        MagicMock(data=_make_events_current(user_id, 1)),
        MagicMock(data=_make_events_prior(user_id, 10)),
        MagicMock(data=[{"user_id": user_id, "email": _TEST_USER_EMAIL}]),
    ]

    async def _mock_execute_async(query, op_name=""):
        return execute_seq.pop(0)

    auth_user = _make_auth_user(days_since_login=10)
    auth_resp = _make_auth_response(auth_user)
    mock_client = MagicMock()

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
            with patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(side_effect=_mock_execute_async)):
                with patch("asyncio.to_thread", new=AsyncMock(return_value=auth_resp)):
                    with patch(_INTEGRATION_PROXY_PATCH) as mock_proxy_cls:
                        mock_proxy = MagicMock()
                        mock_proxy.call = AsyncMock(side_effect=Exception("Stripe not configured"))
                        mock_proxy_cls.return_value = mock_proxy

                        from app.agents.admin.tools.users_intelligence import get_at_risk_users

                        result = await get_at_risk_users(threshold_days_inactive=7)

    assert "at_risk_users" in result
    users = result["at_risk_users"]
    assert len(users) >= 1
    assert "unknown" in users[0]["billing_status"].lower()
    # Must NOT error out — no "error" key
    assert "error" not in result


# ---------------------------------------------------------------------------
# Test 3: get_at_risk_users — Stripe available (billing_status from Stripe)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_at_risk_users_with_stripe():
    """get_at_risk_users includes billing_status from Stripe when configured."""
    user_id = _TEST_USER_ID

    execute_seq = [
        MagicMock(data=_make_session_rows(user_id)),
        MagicMock(data=_make_events_current(user_id, 1)),
        MagicMock(data=_make_events_prior(user_id, 10)),
        MagicMock(data=[{"user_id": user_id, "email": _TEST_USER_EMAIL}]),
    ]

    async def _mock_execute_async(query, op_name=""):
        return execute_seq.pop(0)

    auth_user = _make_auth_user(days_since_login=10)
    auth_resp = _make_auth_response(auth_user)
    mock_client = MagicMock()

    stripe_response = {
        "data": [{"subscriptions": {"data": [{"status": "past_due"}]}}]
    }

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
            with patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(side_effect=_mock_execute_async)):
                with patch("asyncio.to_thread", new=AsyncMock(return_value=auth_resp)):
                    with patch(_INTEGRATION_PROXY_PATCH) as mock_proxy_cls:
                        mock_proxy = MagicMock()
                        mock_proxy.call = AsyncMock(return_value=stripe_response)
                        mock_proxy_cls.return_value = mock_proxy

                        from app.agents.admin.tools.users_intelligence import get_at_risk_users

                        result = await get_at_risk_users(threshold_days_inactive=7)

    assert "at_risk_users" in result
    users = result["at_risk_users"]
    assert len(users) >= 1
    # billing_status should come from Stripe — not "unknown"
    assert "unknown" not in users[0]["billing_status"].lower()


# ---------------------------------------------------------------------------
# Test 4: get_at_risk_users — empty result (no at-risk users)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_at_risk_users_empty():
    """get_at_risk_users returns empty list when no users match at-risk criteria."""
    # sessions table returns no users in the last 28 days
    execute_seq = [
        MagicMock(data=[]),  # sessions — empty
    ]

    async def _mock_execute_async(query, op_name=""):
        return execute_seq.pop(0)

    mock_client = MagicMock()

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
            with patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(side_effect=_mock_execute_async)):
                from app.agents.admin.tools.users_intelligence import get_at_risk_users

                result = await get_at_risk_users(threshold_days_inactive=7)

    assert "at_risk_users" in result
    assert result["at_risk_users"] == []
    assert "criteria" in result
    assert "error" not in result


# ---------------------------------------------------------------------------
# Test 5: get_at_risk_users — autonomy blocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_at_risk_users_autonomy_blocked():
    """get_at_risk_users returns error dict when autonomy tier is blocked."""
    gate = {"error": "get_at_risk_users is blocked by admin configuration."}

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=gate)):
        from app.agents.admin.tools.users_intelligence import get_at_risk_users

        result = await get_at_risk_users()

    assert "error" in result
    assert "at_risk_users" not in result


# ---------------------------------------------------------------------------
# Test 6: get_user_support_context — basic case
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_support_context_basic():
    """get_user_support_context returns usage_summary, error_patterns, and suggested_steps."""
    user_id = _TEST_USER_ID

    # execute_async calls:
    # 1. session_events (last 10, usage_summary)
    # 2. session_events with tool_error filter (error_patterns)
    # 3. user_executive_agents (profile)
    event_rows = [
        {"user_id": user_id, "event_type": "message", "created_at": (datetime.now(UTC) - timedelta(hours=i)).isoformat()}
        for i in range(8)
    ]
    error_rows = [
        {
            "user_id": user_id,
            "event_type": "tool_error",
            "agent_name": "financial",
            "error_type": "timeout",
            "created_at": (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
        }
    ]
    profile_rows = [
        {"user_id": user_id, "persona": "startup", "onboarding_completed": True}
    ]

    execute_seq = [
        MagicMock(data=event_rows),
        MagicMock(data=error_rows),
        MagicMock(data=profile_rows),
    ]

    async def _mock_execute_async(query, op_name=""):
        return execute_seq.pop(0)

    mock_client = MagicMock()

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
            with patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(side_effect=_mock_execute_async)):
                from app.agents.admin.tools.users_intelligence import get_user_support_context

                result = await get_user_support_context(user_id)

    assert "user_id" in result
    assert result["user_id"] == user_id
    assert "usage_summary" in result
    assert "error_patterns" in result
    assert "suggested_steps" in result
    assert "allow_listed_actions" in result
    assert isinstance(result["allow_listed_actions"], list)
    assert isinstance(result["suggested_steps"], list)


# ---------------------------------------------------------------------------
# Test 7: get_user_support_context — no errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_support_context_no_errors():
    """When user has no recent errors, error_patterns is empty and steps focus on engagement."""
    user_id = _TEST_USER_ID

    event_rows = [
        {"user_id": user_id, "event_type": "message", "created_at": (datetime.now(UTC) - timedelta(days=2)).isoformat()}
    ]
    profile_rows = [
        {"user_id": user_id, "persona": "startup", "onboarding_completed": True}
    ]

    execute_seq = [
        MagicMock(data=event_rows),
        MagicMock(data=[]),       # no errors
        MagicMock(data=profile_rows),
    ]

    async def _mock_execute_async(query, op_name=""):
        return execute_seq.pop(0)

    mock_client = MagicMock()

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=None)):
        with patch(_SERVICE_CLIENT_PATCH, return_value=mock_client):
            with patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(side_effect=_mock_execute_async)):
                from app.agents.admin.tools.users_intelligence import get_user_support_context

                result = await get_user_support_context(user_id)

    assert result["error_patterns"] == []
    assert isinstance(result["suggested_steps"], list)


# ---------------------------------------------------------------------------
# Test 8: get_user_support_context — autonomy blocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_support_context_autonomy_blocked():
    """get_user_support_context returns error dict when autonomy tier is blocked."""
    gate = {"error": "get_user_support_context is blocked by admin configuration."}

    with patch(_CHECK_AUTONOMY_PATCH, new=AsyncMock(return_value=gate)):
        from app.agents.admin.tools.users_intelligence import get_user_support_context

        result = await get_user_support_context(_TEST_USER_ID)

    assert "error" in result
    assert "usage_summary" not in result
