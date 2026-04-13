"""Unit tests for BillingAlertService and billing alert admin tools.

Tests verify (9 test behaviors from plan):
- Test 1: compute_cost_projection returns all required fields
- Test 2: projected > prior * 1.2 sets alert_recommended=True, severity="warning"
- Test 3: projected > prior * 1.5 sets alert_recommended=True, severity="critical"
- Test 4: projected <= prior * 1.2 sets alert_recommended=False
- Test 5: plain_english_summary explains the projection in human terms
- Test 6: check_and_alert dispatches billing.cost_projection_alert when alert_recommended
- Test 7: check_and_alert does NOT dispatch when alert_recommended=False
- Test 8: get_billing_cost_projection tool calls compute_cost_projection and returns result
- Test 9: check_billing_alerts tool calls check_and_alert and returns result
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Patch targets
# ---------------------------------------------------------------------------
_OBS_PATCH = "app.services.billing_alert_service.ObservabilityMetricsService"
_DISPATCH_PATCH = "app.services.billing_alert_service.dispatch_notification"
_EXECUTE_ASYNC_PATCH = "app.services.billing_alert_service.execute_async"
_AUTONOMY_PATCH = "app.agents.admin.tools.billing_alerts._check_autonomy"
_SERVICE_PATCH = "app.agents.admin.tools.billing_alerts.BillingAlertService"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _stub_supabase_env(monkeypatch):
    """Provide fake SUPABASE_* env vars so AdminService.__init__ doesn't raise."""
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-test-key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-test-key")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_obs_mock(
    mtd_actual: float,
    projected_full_month: float,
    daily_costs_prior: list[float] | None = None,
    agent_costs: dict[str, float] | None = None,
) -> MagicMock:
    """Build a mock ObservabilityMetricsService with preset return values."""
    mock = MagicMock()
    mock.project_monthly_ai_spend = AsyncMock(
        return_value={
            "mtd_actual": mtd_actual,
            "projected_full_month": projected_full_month,
            "projection_method": "linear_7day",
        }
    )
    # Prior month daily costs (sum = prior_month_total)
    prior_daily = daily_costs_prior or [10.0, 10.0, 10.0]
    mock.compute_ai_cost_by_day = AsyncMock(
        return_value=[{"date": f"2026-03-{i+1:02d}", "cost_usd": c} for i, c in enumerate(prior_daily)]
    )
    mock.compute_ai_cost_by_agent = AsyncMock(
        return_value=agent_costs or {"ContentAgent": 5.0, "FinancialAgent": 3.0}
    )
    return mock


# ---------------------------------------------------------------------------
# Test 1: compute_cost_projection returns required fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_cost_projection_returns_required_fields():
    """compute_cost_projection returns all required fields."""
    from app.services.billing_alert_service import BillingAlertService

    obs_mock = _make_obs_mock(mtd_actual=20.0, projected_full_month=30.0, daily_costs_prior=[10.0, 10.0, 10.0])
    with patch(_OBS_PATCH, return_value=obs_mock):
        svc = BillingAlertService()
        result = await svc.compute_cost_projection()

    required_keys = {
        "mtd_actual",
        "projected_full_month",
        "prior_month_total",
        "month_over_month_change_pct",
        "top_cost_drivers",
        "alert_recommended",
        "severity",
        "plain_english_summary",
    }
    assert required_keys.issubset(result.keys()), f"Missing keys: {required_keys - result.keys()}"
    assert isinstance(result["top_cost_drivers"], list)
    assert isinstance(result["plain_english_summary"], str)
    assert len(result["plain_english_summary"]) > 10


# ---------------------------------------------------------------------------
# Test 2: warning threshold at >20% increase
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_cost_projection_warning_threshold():
    """projected > prior * 1.2 sets alert_recommended=True, severity='warning'."""
    from app.services.billing_alert_service import BillingAlertService

    # prior = 30.0, projected = 37.0 → ~23% increase (>20%, <50%)
    obs_mock = _make_obs_mock(
        mtd_actual=15.0,
        projected_full_month=37.0,
        daily_costs_prior=[10.0, 10.0, 10.0],  # prior_month_total = 30.0
    )
    with patch(_OBS_PATCH, return_value=obs_mock):
        svc = BillingAlertService()
        result = await svc.compute_cost_projection()

    assert result["alert_recommended"] is True
    assert result["severity"] == "warning"
    assert result["prior_month_total"] == pytest.approx(30.0)
    assert result["month_over_month_change_pct"] > 20.0


# ---------------------------------------------------------------------------
# Test 3: critical threshold at >50% increase
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_cost_projection_critical_threshold():
    """projected > prior * 1.5 sets alert_recommended=True, severity='critical'."""
    from app.services.billing_alert_service import BillingAlertService

    # prior = 30.0, projected = 50.0 → ~67% increase (>50%)
    obs_mock = _make_obs_mock(
        mtd_actual=20.0,
        projected_full_month=50.0,
        daily_costs_prior=[10.0, 10.0, 10.0],  # prior_month_total = 30.0
    )
    with patch(_OBS_PATCH, return_value=obs_mock):
        svc = BillingAlertService()
        result = await svc.compute_cost_projection()

    assert result["alert_recommended"] is True
    assert result["severity"] == "critical"
    assert result["month_over_month_change_pct"] > 50.0


# ---------------------------------------------------------------------------
# Test 4: no alert when projected <= prior * 1.2
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_cost_projection_no_alert_below_threshold():
    """projected <= prior * 1.2 sets alert_recommended=False."""
    from app.services.billing_alert_service import BillingAlertService

    # prior = 30.0, projected = 33.0 → 10% increase (<20%)
    obs_mock = _make_obs_mock(
        mtd_actual=15.0,
        projected_full_month=33.0,
        daily_costs_prior=[10.0, 10.0, 10.0],
    )
    with patch(_OBS_PATCH, return_value=obs_mock):
        svc = BillingAlertService()
        result = await svc.compute_cost_projection()

    assert result["alert_recommended"] is False
    assert result["severity"] is None


# ---------------------------------------------------------------------------
# Test 5: plain_english_summary explains projection in human terms
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_cost_projection_plain_english_summary():
    """plain_english_summary explains the projection in human terms."""
    from app.services.billing_alert_service import BillingAlertService

    obs_mock = _make_obs_mock(
        mtd_actual=15.0,
        projected_full_month=45.0,
        daily_costs_prior=[10.0, 10.0, 10.0],  # prior = 30.0, +50% = critical
        agent_costs={"ContentAgent": 8.0, "FinancialAgent": 2.0},
    )
    with patch(_OBS_PATCH, return_value=obs_mock):
        svc = BillingAlertService()
        result = await svc.compute_cost_projection()

    summary = result["plain_english_summary"]
    # Must contain numeric cost reference
    assert "$" in summary or "%" in summary
    # Must mention the top driver
    assert "ContentAgent" in summary


# ---------------------------------------------------------------------------
# Test 6: check_and_alert dispatches when alert_recommended
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_and_alert_dispatches_when_alert_recommended():
    """check_and_alert calls dispatch_notification when alert_recommended=True."""
    from app.services.billing_alert_service import BillingAlertService

    obs_mock = _make_obs_mock(
        mtd_actual=15.0,
        projected_full_month=50.0,
        daily_costs_prior=[10.0, 10.0, 10.0],  # prior=30, critical
    )
    dispatch_mock = AsyncMock(return_value={"slack": True})

    with patch(_OBS_PATCH, return_value=obs_mock), patch(_DISPATCH_PATCH, dispatch_mock):
        svc = BillingAlertService()
        result = await svc.check_and_alert(admin_user_ids=["user-1", "user-2"])

    assert result["alerted"] is True
    assert result["notifications_sent"] == 2
    assert dispatch_mock.call_count == 2
    # Check event_type on first call
    first_call_kwargs = dispatch_mock.call_args_list[0]
    # dispatch_notification(user_id, event_type, payload)
    assert first_call_kwargs.args[1] == "billing.cost_projection_alert"


# ---------------------------------------------------------------------------
# Test 7: check_and_alert does NOT dispatch when alert not recommended
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_and_alert_no_dispatch_when_not_recommended():
    """check_and_alert does NOT call dispatch_notification when alert_recommended=False."""
    from app.services.billing_alert_service import BillingAlertService

    obs_mock = _make_obs_mock(
        mtd_actual=15.0,
        projected_full_month=33.0,
        daily_costs_prior=[10.0, 10.0, 10.0],  # prior=30, +10% → no alert
    )
    dispatch_mock = AsyncMock(return_value={})

    with patch(_OBS_PATCH, return_value=obs_mock), patch(_DISPATCH_PATCH, dispatch_mock):
        svc = BillingAlertService()
        result = await svc.check_and_alert(admin_user_ids=["user-1"])

    assert result["alerted"] is False
    assert result["notifications_sent"] == 0
    dispatch_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Test 8: get_billing_cost_projection tool calls compute_cost_projection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_billing_cost_projection_tool():
    """get_billing_cost_projection calls compute_cost_projection and returns result."""
    from app.agents.admin.tools.billing_alerts import get_billing_cost_projection

    expected = {
        "mtd_actual": 20.0,
        "projected_full_month": 45.0,
        "prior_month_total": 30.0,
        "month_over_month_change_pct": 50.0,
        "top_cost_drivers": [{"agent_name": "ContentAgent", "cost_usd": 10.0, "pct_of_total": 100.0}],
        "alert_recommended": True,
        "severity": "critical",
        "plain_english_summary": "Costs are up 50%.",
    }
    mock_svc = MagicMock()
    mock_svc.compute_cost_projection = AsyncMock(return_value=expected)

    with patch(_AUTONOMY_PATCH, return_value=None), patch(_SERVICE_PATCH, return_value=mock_svc):
        result = await get_billing_cost_projection()

    mock_svc.compute_cost_projection.assert_awaited_once()
    assert result == expected


# ---------------------------------------------------------------------------
# Test 9: check_billing_alerts tool calls check_and_alert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_billing_alerts_tool():
    """check_billing_alerts calls check_and_alert and returns result."""
    from app.agents.admin.tools.billing_alerts import check_billing_alerts

    expected = {"alerted": True, "notifications_sent": 1, "projection": {}}
    mock_svc = MagicMock()
    mock_svc.check_and_alert = AsyncMock(return_value=expected)

    with patch(_AUTONOMY_PATCH, return_value=None), patch(_SERVICE_PATCH, return_value=mock_svc):
        result = await check_billing_alerts()

    mock_svc.check_and_alert.assert_awaited_once()
    assert result == expected
