"""Unit tests for admin billing API endpoint.

Tests verify:
- test_billing_summary_returns_200: mock Stripe + subscriptions returns 200 with
  mrr, arr, churn_rate, plan_distribution fields
- test_billing_summary_no_stripe: Stripe not configured returns 200 with mrr=0,
  arr=0, data_source="db_only", plan_distribution still present from subscriptions
- test_billing_summary_requires_admin: request without admin auth returns 403
- test_billing_summary_empty_subscriptions: empty subscriptions table returns 200
  with data_source="no_data"
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request as StarletteRequest

# Patch targets scoped to billing router module
_EXECUTE_ASYNC_PATCH = "app.routers.admin.billing.execute_async"
_CONFIG_PATCH = "app.routers.admin.billing._get_integration_config"
_PROXY_CALL_PATCH = "app.routers.admin.billing.IntegrationProxyService.call"
_SERVICE_CLIENT_PATCH = "app.routers.admin.billing.get_service_client"


def _make_mock_request(path: str = "/admin/billing/summary", method: str = "GET"):
    """Create a minimal Starlette Request for rate limiter dependency."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [(b"x-forwarded-for", b"127.0.0.1")],
        "client": ("127.0.0.1", 12345),
    }
    return StarletteRequest(scope=scope)


def _make_subscription_rows() -> list[dict]:
    """Build fake subscriptions table rows."""
    return [
        {"tier": "solopreneur", "is_active": True, "will_renew": True, "billing_issue_at": None},
        {"tier": "solopreneur", "is_active": True, "will_renew": False, "billing_issue_at": None},
        {"tier": "startup", "is_active": True, "will_renew": True, "billing_issue_at": None},
        {"tier": "sme", "is_active": False, "will_renew": True, "billing_issue_at": None},
    ]


# =========================================================================
# Test 1: GET /admin/billing/summary returns 200 with all expected fields
# =========================================================================


@pytest.mark.asyncio
async def test_billing_summary_returns_200(admin_user_dict):
    """GET /admin/billing/summary returns 200 with mrr, arr, churn_rate, plan_distribution."""
    from app.routers.admin.billing import get_billing_summary

    sub_rows = _make_subscription_rows()
    sub_result = MagicMock()
    sub_result.data = sub_rows

    stripe_data = {"mrr": 9500.0, "arr": 114000.0, "active_subscriptions": 95}

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=sub_result)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value=("sk_test_key", {}, None))),
        patch(_PROXY_CALL_PATCH, new=AsyncMock(return_value=stripe_data)),
    ):
        result = await get_billing_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    assert "mrr" in result
    assert "arr" in result
    assert "churn_rate" in result
    assert "plan_distribution" in result
    assert result["mrr"] == 9500.0
    assert result["arr"] == 114000.0
    assert isinstance(result["plan_distribution"], list)
    # churn_pending = 1 (solopreneur with will_renew=False), total_active = 3
    assert result["churn_rate"] == pytest.approx(1 / 3, rel=0.01)
    assert result["data_source"] == "live"


# =========================================================================
# Test 2: Stripe not configured returns 200 with db_only data_source
# =========================================================================


@pytest.mark.asyncio
async def test_billing_summary_no_stripe(admin_user_dict):
    """GET /admin/billing/summary returns mrr=0, arr=0, data_source=db_only when Stripe not configured."""
    from app.routers.admin.billing import get_billing_summary

    sub_rows = _make_subscription_rows()
    sub_result = MagicMock()
    sub_result.data = sub_rows

    stripe_error = {"error": "Integration 'stripe' is not configured."}

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=sub_result)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value=stripe_error)),
    ):
        result = await get_billing_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    assert result["mrr"] == 0
    assert result["arr"] == 0
    assert result["data_source"] == "db_only"
    # plan_distribution should still be present from the subscriptions query
    assert "plan_distribution" in result
    assert isinstance(result["plan_distribution"], list)


# =========================================================================
# Test 3: Request without admin auth returns 403
# =========================================================================


@pytest.mark.asyncio
async def test_billing_summary_requires_admin():
    """GET /admin/billing/summary returns 403 when caller is not an admin."""
    from unittest.mock import MagicMock

    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    from app.middleware.admin_auth import require_admin

    # Build fake credentials
    creds = MagicMock(spec=HTTPAuthorizationCredentials)
    creds.credentials = "non-admin-token"

    non_admin_user = {
        "id": "user-regular",
        "email": "regular@test.com",
        "role": "authenticated",
        "metadata": {},
    }

    # Patch verify_token to return a non-admin user; DB role check returns False
    with (
        patch(
            "app.middleware.admin_auth.verify_token",
            new=AsyncMock(return_value=non_admin_user),
        ),
        patch.dict("os.environ", {"ADMIN_EMAILS": "admin@pikar.ai"}, clear=False),
        patch(
            "app.middleware.admin_auth.get_service_client",
            return_value=MagicMock(
                **{
                    "rpc.return_value.execute.return_value": MagicMock(data=False),
                }
            ),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(credentials=creds)

    assert exc_info.value.status_code == 403


# =========================================================================
# Test 4: Empty subscriptions table returns data_source="no_data"
# =========================================================================


@pytest.mark.asyncio
async def test_billing_summary_empty_subscriptions(admin_user_dict):
    """GET /admin/billing/summary returns data_source=no_data when subscriptions table empty."""
    from app.routers.admin.billing import get_billing_summary

    empty_result = MagicMock()
    empty_result.data = []

    stripe_error = {"error": "Integration 'stripe' is not configured."}

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=empty_result)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value=stripe_error)),
    ):
        result = await get_billing_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    assert result["data_source"] == "no_data"
    assert result["active_subscriptions"] == 0
    assert result["plan_distribution"] == []
