"""Unit tests for admin observability API endpoints.

Plan 51-03 / OBS-02, OBS-03, OBS-04. Verifies:

- GET /admin/observability/summary is gated by require_admin (403 without admin)
- POST /admin/observability/run-rollup is gated by verify_service_auth (401 without secret)
- Router is importable and has correct endpoint paths

Follows the Windows-safe sys.modules stub pattern established in Phase 49-05:
short-circuit ``app.middleware.rate_limiter`` before importing the router
to sidestep the slowapi.Limiter() -> starlette.Config() -> .env
UnicodeDecodeError on Windows cp1252.
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
# Stub SUPABASE env vars so AdminService.__init__ doesn't raise.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _stub_supabase_env(monkeypatch):
    """Provide fake SUPABASE_* env vars for AdminService.__init__ validation."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-test-key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-test-key")


def _make_mock_request(path: str = "/admin/observability/summary", method: str = "GET"):
    """Create a minimal Starlette Request for the rate limiter dependency."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [(b"x-forwarded-for", b"127.0.0.1")],
        "client": ("127.0.0.1", 12345),
    }
    return StarletteRequest(scope=scope)


# =========================================================================
# Test 1: Router is importable and exposes correct routes
# =========================================================================


class TestObservabilityRouterImport:
    """Verify the observability router module imports cleanly."""

    def test_router_importable(self):
        """app.routers.admin.observability must be importable without errors."""
        with (
            patch(
                "app.services.supabase.get_service_client",
                return_value=MagicMock(),
            ),
        ):
            from app.routers.admin import observability  # noqa: F401

        assert observability.router is not None

    def test_router_has_expected_routes(self):
        """Router must expose summary, latency, errors, cost, and run-rollup routes."""
        with patch(
            "app.services.supabase.get_service_client",
            return_value=MagicMock(),
        ):
            from app.routers.admin import observability

        route_paths = {route.path for route in observability.router.routes}
        assert "/admin/observability/summary" in route_paths
        assert "/admin/observability/latency" in route_paths
        assert "/admin/observability/errors" in route_paths
        assert "/admin/observability/cost" in route_paths
        assert "/admin/observability/run-rollup" in route_paths


# =========================================================================
# TestObservabilityApiAuth
# =========================================================================


class TestObservabilityApiAuth:
    """Verify require_admin gate on GET observability endpoints."""

    @pytest.mark.asyncio
    async def test_observability_summary_requires_admin(self):
        """GET /admin/observability/summary returns 403 when caller is not an admin."""
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials

        from app.middleware.admin_auth import require_admin

        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = "non-admin-token"

        non_admin_user = {
            "id": "user-regular",
            "email": "regular@test.com",
            "role": "authenticated",
            "metadata": {},
        }

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

    def test_observability_run_rollup_requires_service_auth(self):
        """POST /admin/observability/run-rollup returns 401 without service secret.

        verify_service_auth uses Header dependency (x_service_secret parameter),
        so we call it directly with None (no secret provided).
        """
        from fastapi import HTTPException

        from app.app_utils.auth import verify_service_auth

        with patch.dict(
            "os.environ",
            {"WORKFLOW_SERVICE_SECRET": "real-secret"},
            clear=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                # Pass None for x_service_secret to simulate missing header
                verify_service_auth(x_service_secret=None)

        assert exc_info.value.status_code == 401


# =========================================================================
# Test: summary endpoint returns expected fields for valid admin
# =========================================================================


@pytest.mark.asyncio
async def test_observability_summary_returns_fields(admin_user_dict):
    """GET /admin/observability/summary returns all hero metric fields for valid admin."""
    with patch(
        "app.services.supabase.get_service_client",
        return_value=MagicMock(),
    ):
        from app.routers.admin.observability import get_observability_summary

    summary_data = {
        "error_rate_24h": 0.02,
        "mtd_ai_spend": 12.50,
        "projected_monthly_spend": 42.00,
        "p95_latency_24h": 320.5,
        "threshold_breach": None,
    }

    # Patch all service methods
    with (
        patch(
            "app.routers.admin.observability.ObservabilityMetricsService.compute_error_rate",
            new=AsyncMock(
                return_value={"error_rate": 0.02, "error_count": 1, "total_count": 50}
            ),
        ),
        patch(
            "app.routers.admin.observability.ObservabilityMetricsService.project_monthly_ai_spend",
            new=AsyncMock(
                return_value={
                    "mtd_actual": 12.50,
                    "projected_full_month": 42.00,
                    "projection_method": "linear_7day",
                }
            ),
        ),
        patch(
            "app.routers.admin.observability.ObservabilityMetricsService.compute_latency_percentiles",
            new=AsyncMock(
                return_value={
                    "p50": 150.0,
                    "p95": 320.5,
                    "p99": 480.0,
                    "sample_count": 50,
                    "error_count": 1,
                }
            ),
        ),
        patch(
            "app.routers.admin.observability.ObservabilityMetricsService.check_error_threshold",
            new=AsyncMock(return_value=None),
        ),
    ):
        result = await get_observability_summary(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    assert "error_rate_24h" in result
    assert "mtd_ai_spend" in result
    assert "projected_monthly_spend" in result
    assert "p95_latency_24h" in result
    assert "threshold_breach" in result
    assert result["error_rate_24h"] == pytest.approx(0.02)
    assert result["p95_latency_24h"] == pytest.approx(320.5)
    assert result["threshold_breach"] is None
