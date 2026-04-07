"""Unit tests for admin billing API endpoint.

Tests verify:
- test_billing_summary_returns_200: mock Stripe + subscriptions returns 200 with
  mrr, arr, churn_rate, plan_distribution fields
- test_billing_summary_no_stripe: Stripe not configured returns 200 with mrr
  computed from DB, data_source="db_only", plan_distribution still present
- test_billing_summary_requires_admin: request without admin auth returns 403
- test_billing_summary_empty_subscriptions: empty subscriptions table returns 200
  with data_source="no_data"

Plan 50-03 / BILL-04 additions:
- test_churn_rate_uses_metrics_service: churn_rate now reflects
  BillingMetricsService.compute_churn_rate output, NOT churn_pending/active
- test_mrr_from_db_when_stripe_unavailable: MRR is non-zero from DB even when
  Stripe is unreachable
- test_include_trend_query_param: ``?include_trend=true`` returns churn_trend
  field; omitted by default
- test_stripe_variance_warning: when Stripe live MRR drifts >10% from DB MRR,
  the endpoint logs a warning but does NOT raise (non-fatal cross-check)

Follows the Windows-safe import-stub pattern used by Plan 49-05 — short-circuit
``app.middleware.rate_limiter`` before importing the router under test, because
the real rate limiter pulls in slowapi which reads ``.env`` at import time and
crashes on Windows cp1252 with box-drawing characters in the file.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request as StarletteRequest

# ---------------------------------------------------------------------------
# Stub heavy / Windows-flaky modules BEFORE importing the router under test.
# ---------------------------------------------------------------------------
if "app.middleware.rate_limiter" not in sys.modules:
    _mock_rate_limiter = types.ModuleType("app.middleware.rate_limiter")
    _mock_limiter = MagicMock()
    _mock_limiter.limit = lambda *_args, **_kwargs: (lambda fn: fn)
    _mock_rate_limiter.limiter = _mock_limiter
    _mock_rate_limiter.get_user_persona_limit = "100/minute"
    _mock_rate_limiter.get_remote_address = lambda *_a, **_kw: "127.0.0.1"
    sys.modules["app.middleware.rate_limiter"] = _mock_rate_limiter


# ---------------------------------------------------------------------------
# Stub Supabase env vars so AdminService.__init__ doesn't raise. The actual
# client is patched per-test via _SERVICE_CLIENT_PATCH and the service
# methods are patched via _METRICS_*_PATCH so no real Supabase call is made.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _stub_supabase_env(monkeypatch):
    """Provide fake SUPABASE_* env vars for AdminService.__init__ validation."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-test-key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-test-key")

# Patch targets scoped to billing router module
_EXECUTE_ASYNC_PATCH = "app.routers.admin.billing.execute_async"
_CONFIG_PATCH = "app.routers.admin.billing._get_integration_config"
_PROXY_CALL_PATCH = "app.routers.admin.billing.IntegrationProxyService.call"
_SERVICE_CLIENT_PATCH = "app.routers.admin.billing.get_service_client"

# Plan 50-03: BillingMetricsService method-level patches
_METRICS_MRR_PATCH = (
    "app.routers.admin.billing.BillingMetricsService.compute_mrr"
)
_METRICS_CHURN_PATCH = (
    "app.routers.admin.billing.BillingMetricsService.compute_churn_rate"
)
_METRICS_TREND_PATCH = (
    "app.routers.admin.billing.BillingMetricsService.compute_churn_trend"
)


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
    """GET /admin/billing/summary returns 200 with mrr, arr, churn_rate, plan_distribution.

    Plan 50-03: mrr now comes from BillingMetricsService.compute_mrr (DB-native),
    NOT directly from the Stripe proxy. The Stripe call is now a non-fatal
    cross-check; it sets data_source='live' on success.
    """
    from app.routers.admin.billing import get_billing_summary

    sub_rows = _make_subscription_rows()
    sub_result = MagicMock()
    sub_result.data = sub_rows

    # DB-native MRR for the same subscription rows: 2*99 + 1*297 = 495
    mrr_data = {"mrr": 495.0, "arr": 5940.0}
    churn_data = {
        "churn_rate": 0.05,
        "canceled_in_period": 1,
        "active_at_start": 20,
        "window_days": 30,
    }
    # Stripe live data — within 10% so no variance warning
    stripe_data = {"mrr": 500.0, "arr": 6000.0, "active_subscriptions": 95}

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=sub_result)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value=("sk_test_key", {}, None))),
        patch(_PROXY_CALL_PATCH, new=AsyncMock(return_value=stripe_data)),
        patch(_METRICS_MRR_PATCH, new=AsyncMock(return_value=mrr_data)),
        patch(_METRICS_CHURN_PATCH, new=AsyncMock(return_value=churn_data)),
    ):
        result = await get_billing_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    assert "mrr" in result
    assert "arr" in result
    assert "churn_rate" in result
    assert "plan_distribution" in result
    # MRR comes from BillingMetricsService now, not Stripe pass-through
    assert result["mrr"] == 495.0
    assert result["arr"] == 5940.0
    assert isinstance(result["plan_distribution"], list)
    # Real churn comes from BillingMetricsService output
    assert result["churn_rate"] == pytest.approx(0.05)
    assert result["canceled_in_period"] == 1
    assert result["data_source"] == "live"


# =========================================================================
# Test 2: Stripe not configured returns 200 with db_only data_source
# =========================================================================


@pytest.mark.asyncio
async def test_billing_summary_no_stripe(admin_user_dict):
    """When Stripe is not configured, MRR still computed from DB, data_source=db_only."""
    from app.routers.admin.billing import get_billing_summary

    sub_rows = _make_subscription_rows()
    sub_result = MagicMock()
    sub_result.data = sub_rows

    mrr_data = {"mrr": 495.0, "arr": 5940.0}
    churn_data = {
        "churn_rate": 0.0,
        "canceled_in_period": 0,
        "active_at_start": 3,
        "window_days": 30,
    }

    stripe_error = {"error": "Integration 'stripe' is not configured."}

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=sub_result)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value=stripe_error)),
        patch(_METRICS_MRR_PATCH, new=AsyncMock(return_value=mrr_data)),
        patch(_METRICS_CHURN_PATCH, new=AsyncMock(return_value=churn_data)),
    ):
        result = await get_billing_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    # Plan 50-03: MRR from DB even without Stripe
    assert result["mrr"] == 495.0
    assert result["arr"] == 5940.0
    assert result["data_source"] == "db_only"
    # plan_distribution should still be present from the subscriptions query
    assert "plan_distribution" in result
    assert isinstance(result["plan_distribution"], list)


# =========================================================================
# Test 3: Request without admin auth returns 403 (require_admin regression)
# =========================================================================


@pytest.mark.asyncio
async def test_billing_summary_requires_admin():
    """GET /admin/billing/summary returns 403 when caller is not an admin.

    Regression guard for Plan 50-03 — verifies the endpoint remains gated by
    require_admin even after the BillingMetricsService rewire.
    """
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

    mrr_data = {"mrr": 0.0, "arr": 0.0}
    churn_data = {
        "churn_rate": 0.0,
        "canceled_in_period": 0,
        "active_at_start": 0,
        "window_days": 30,
    }

    stripe_error = {"error": "Integration 'stripe' is not configured."}

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=empty_result)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value=stripe_error)),
        patch(_METRICS_MRR_PATCH, new=AsyncMock(return_value=mrr_data)),
        patch(_METRICS_CHURN_PATCH, new=AsyncMock(return_value=churn_data)),
    ):
        result = await get_billing_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    assert result["data_source"] == "no_data"
    assert result["active_subscriptions"] == 0
    assert result["plan_distribution"] == []


# =========================================================================
# Plan 50-03 NEW: churn_rate reflects BillingMetricsService output
# =========================================================================


@pytest.mark.asyncio
async def test_churn_rate_uses_metrics_service(admin_user_dict):
    """churn_rate must come from BillingMetricsService, not churn_pending/active."""
    from app.routers.admin.billing import get_billing_summary

    sub_rows = _make_subscription_rows()
    sub_result = MagicMock()
    sub_result.data = sub_rows

    # Service returns 0.08 — endpoint must propagate this exact value
    churn_data = {
        "churn_rate": 0.08,
        "canceled_in_period": 4,
        "active_at_start": 50,
        "window_days": 30,
    }
    mrr_data = {"mrr": 495.0, "arr": 5940.0}

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=sub_result)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value={"error": "n/a"})),
        patch(_METRICS_MRR_PATCH, new=AsyncMock(return_value=mrr_data)),
        patch(_METRICS_CHURN_PATCH, new=AsyncMock(return_value=churn_data)),
    ):
        result = await get_billing_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    assert result["churn_rate"] == pytest.approx(0.08)
    assert result["canceled_in_period"] == 4
    # Old "will-not-renew" pending count is still present alongside the new field
    assert "churn_pending" in result
    # And it is NOT being used for churn_rate any more — sanity check
    # (sub_rows has 1 will_renew=False on 3 active; old logic = 1/3 ≠ 0.08)
    assert result["churn_rate"] != pytest.approx(1 / 3, rel=0.01)


# =========================================================================
# Plan 50-03 NEW: MRR from DB when Stripe unavailable
# =========================================================================


@pytest.mark.asyncio
async def test_mrr_from_db_when_stripe_unavailable(admin_user_dict):
    """MRR is non-zero from BillingMetricsService.compute_mrr even without Stripe."""
    from app.routers.admin.billing import get_billing_summary

    sub_rows = _make_subscription_rows()
    sub_result = MagicMock()
    sub_result.data = sub_rows

    # DB-native MRR — this is the assertion target
    mrr_data = {"mrr": 1188.0, "arr": 14256.0}
    churn_data = {
        "churn_rate": 0.0,
        "canceled_in_period": 0,
        "active_at_start": 12,
        "window_days": 30,
    }

    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=sub_result)),
        # Stripe absent
        patch(
            _CONFIG_PATCH,
            new=AsyncMock(return_value={"error": "stripe not configured"}),
        ),
        patch(_METRICS_MRR_PATCH, new=AsyncMock(return_value=mrr_data)),
        patch(_METRICS_CHURN_PATCH, new=AsyncMock(return_value=churn_data)),
    ):
        result = await get_billing_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    assert result["mrr"] == 1188.0
    assert result["arr"] == 14256.0
    assert result["data_source"] == "db_only"


# =========================================================================
# Plan 50-03 NEW: include_trend query parameter
# =========================================================================


@pytest.mark.asyncio
async def test_include_trend_query_param(admin_user_dict):
    """``?include_trend=true`` returns churn_trend; default response omits it."""
    from app.routers.admin.billing import get_billing_summary

    sub_rows = _make_subscription_rows()
    sub_result = MagicMock()
    sub_result.data = sub_rows

    mrr_data = {"mrr": 495.0, "arr": 5940.0}
    churn_data = {
        "churn_rate": 0.05,
        "canceled_in_period": 1,
        "active_at_start": 20,
        "window_days": 30,
    }
    trend_data = [
        {"date": f"2026-04-{day:02d}", "canceled": 0} for day in range(1, 31)
    ]

    common_patches = [
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=sub_result)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value={"error": "n/a"})),
        patch(_METRICS_MRR_PATCH, new=AsyncMock(return_value=mrr_data)),
        patch(_METRICS_CHURN_PATCH, new=AsyncMock(return_value=churn_data)),
        patch(_METRICS_TREND_PATCH, new=AsyncMock(return_value=trend_data)),
    ]

    # Default: no churn_trend in response
    with common_patches[0], common_patches[1], common_patches[2], common_patches[3], common_patches[4], common_patches[5]:
        default_result = await get_billing_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )
    assert "churn_trend" not in default_result

    # Opt-in: churn_trend included
    with (
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=sub_result)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value={"error": "n/a"})),
        patch(_METRICS_MRR_PATCH, new=AsyncMock(return_value=mrr_data)),
        patch(_METRICS_CHURN_PATCH, new=AsyncMock(return_value=churn_data)),
        patch(_METRICS_TREND_PATCH, new=AsyncMock(return_value=trend_data)),
    ):
        opted_result = await get_billing_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
            include_trend=True,
        )
    assert "churn_trend" in opted_result
    assert isinstance(opted_result["churn_trend"], list)
    assert len(opted_result["churn_trend"]) == 30


# =========================================================================
# Plan 50-03 NEW: Stripe variance warning is non-fatal
# =========================================================================


@pytest.mark.asyncio
async def test_stripe_variance_warning_non_fatal(admin_user_dict, caplog):
    """When Stripe live MRR differs by >10% from DB MRR, warn but do not raise."""
    import logging

    from app.routers.admin.billing import get_billing_summary

    sub_rows = _make_subscription_rows()
    sub_result = MagicMock()
    sub_result.data = sub_rows

    # DB says 1000, Stripe says 1500 — 50% variance => warning expected
    mrr_data = {"mrr": 1000.0, "arr": 12000.0}
    churn_data = {
        "churn_rate": 0.0,
        "canceled_in_period": 0,
        "active_at_start": 10,
        "window_days": 30,
    }
    stripe_data = {"mrr": 1500.0, "arr": 18000.0}

    with (
        caplog.at_level(logging.WARNING, logger="app.routers.admin.billing"),
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=sub_result)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value=("sk_test", {}, None))),
        patch(_PROXY_CALL_PATCH, new=AsyncMock(return_value=stripe_data)),
        patch(_METRICS_MRR_PATCH, new=AsyncMock(return_value=mrr_data)),
        patch(_METRICS_CHURN_PATCH, new=AsyncMock(return_value=churn_data)),
    ):
        result = await get_billing_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    # DB value still wins
    assert result["mrr"] == 1000.0
    assert result["data_source"] == "live"
    # Warning was emitted
    assert any(
        "variance" in rec.message.lower() or "MRR" in rec.message
        for rec in caplog.records
    )
