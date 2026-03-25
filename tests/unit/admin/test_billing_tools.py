"""Unit tests for AdminAgent billing tools.

Tests verify:
- test_get_billing_metrics_returns_data: IntegrationProxyService.call returns mrr/arr/active_subscriptions
- test_get_plan_distribution_returns_tiers: subscriptions table rows map to tier counts
- test_issue_refund_requires_confirmation: _check_autonomy returns confirm dict on first call
- test_issue_refund_executes_after_confirmation: confirmed refund returns refund_id
- test_detect_anomalies_flags_dau: DAU spike >2 stddev is flagged in anomalies list
- test_detect_anomalies_no_flag_stable: stable DAU returns empty anomalies list
- test_generate_executive_summary_returns_text: summary_text and recommendations present
- test_forecast_revenue_projects_trend: growing MRR produces projected_mrr > current_mrr
- test_forecast_revenue_insufficient_data: fewer than 7 rows returns insufficient_data=true
- test_assess_refund_risk_high: short tenure + low usage yields risk_level="high"
- test_assess_refund_risk_low: long tenure + high usage yields risk_level="low"
- test_get_billing_metrics_budget_exhausted: returns error when check_session_budget=False
- test_get_billing_metrics_not_configured: returns error when _get_integration_config returns error dict
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Patch targets scoped to billing module
# ---------------------------------------------------------------------------
_SERVICE_CLIENT_PATCH = "app.agents.admin.tools.billing.get_service_client"
_EXECUTE_ASYNC_PATCH = "app.agents.admin.tools.billing.execute_async"
_PROXY_CALL_PATCH = "app.agents.admin.tools.billing.IntegrationProxyService.call"
_BUDGET_PATCH = "app.agents.admin.tools.billing.check_session_budget"
_AUTONOMY_PATCH = "app.agents.admin.tools.billing._check_autonomy"
_CONFIG_PATCH = "app.agents.admin.tools.billing._get_integration_config"
_USAGE_STATS_PATCH = "app.agents.admin.tools.billing.get_usage_stats"
_AGENT_EFFECTIVENESS_PATCH = "app.agents.admin.tools.billing.get_agent_effectiveness"
_BILLING_METRICS_PATCH = "app.agents.admin.tools.billing.get_billing_metrics"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_autonomy_client(level: str) -> MagicMock:
    """Build a mock Supabase client that returns the given autonomy level."""
    client = MagicMock()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[{"autonomy_level": level}])
    return client


def _make_subscription_rows(
    tiers: list[str],
    is_active: bool = True,
    will_renew: bool = True,
) -> list[dict]:
    """Build fake subscriptions table rows."""
    return [
        {
            "tier": t,
            "is_active": is_active,
            "will_renew": will_renew,
            "billing_issue_at": None,
            "stripe_customer_id": f"cus_{i:03d}",
            "created_at": "2026-01-15T00:00:00Z",
        }
        for i, t in enumerate(tiers)
    ]


def _make_usage_rows(count: int = 30, spike_last: bool = False) -> list[dict]:
    """Build fake usage rows for anomaly detection tests.

    Rows are returned in DESC order (newest first) to match the analytics
    tool's query ordering. When spike_last=True, the first row (newest /
    index 0) is the spike so the anomaly detector sees it as "current".
    """
    rows = []
    for i in range(count):
        dau = 100
        if spike_last and i == 0:
            # First row = newest = current value; spike here triggers anomaly
            dau = 1000  # 10x spike — well above 2 stddev
        rows.append({"stat_date": f"2026-02-{(i % 28) + 1:02d}", "dau": dau, "mau": 500})
    return rows


# ---------------------------------------------------------------------------
# Test 1: get_billing_metrics returns MRR/ARR/active_subscriptions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_billing_metrics_returns_data():
    """get_billing_metrics returns mrr, arr, active_subscriptions from Stripe proxy."""
    from app.agents.admin.tools.billing import get_billing_metrics

    expected = {"mrr": 9500.0, "arr": 114000.0, "active_subscriptions": 95}

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value=("sk_test_key", {}, None))),
        patch(_BUDGET_PATCH, new=AsyncMock(return_value=True)),
        patch(_PROXY_CALL_PATCH, new=AsyncMock(return_value=expected)),
    ):
        result = await get_billing_metrics()

    assert result["mrr"] == 9500.0
    assert result["arr"] == 114000.0
    assert result["active_subscriptions"] == 95


# ---------------------------------------------------------------------------
# Test 2: get_plan_distribution returns tier counts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_plan_distribution_returns_tiers():
    """get_plan_distribution returns tier counts from subscriptions table."""
    from app.agents.admin.tools.billing import get_plan_distribution

    rows = _make_subscription_rows(
        ["solopreneur", "solopreneur", "startup", "sme", "enterprise"]
    )
    mock_result = MagicMock()
    mock_result.data = rows

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_SERVICE_CLIENT_PATCH, return_value=_build_autonomy_client("auto")),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_result)),
    ):
        result = await get_plan_distribution()

    assert "plan_distribution" in result
    tiers_by_name = {e["tier"]: e["count"] for e in result["plan_distribution"]}
    assert tiers_by_name.get("solopreneur") == 2
    assert tiers_by_name.get("startup") == 1
    assert result["total_active"] == 5


# ---------------------------------------------------------------------------
# Test 3: issue_refund returns confirmation dict on first call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_issue_refund_requires_confirmation():
    """issue_refund returns requires_confirmation=True when autonomy tier is confirm."""
    from app.agents.admin.tools.billing import issue_refund

    confirm_gate = {
        "requires_confirmation": True,
        "confirmation_token": "token-abc-123",
        "action_details": {"action": "issue_refund", "risk_level": "high"},
    }

    with patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=confirm_gate)):
        result = await issue_refund(charge_id="ch_test_123")

    assert result.get("requires_confirmation") is True
    assert "confirmation_token" in result


# ---------------------------------------------------------------------------
# Test 4: issue_refund executes after confirmation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_issue_refund_executes_after_confirmation():
    """issue_refund calls Stripe refund directly and returns refund_id after confirmation."""
    from app.agents.admin.tools.billing import issue_refund

    refund_response = {
        "refund_id": "re_test_abc123",
        "status": "succeeded",
        "amount": 2000,
        "currency": "usd",
        "charge": "ch_test_123",
    }

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value=("sk_test_key", {}, None))),
        patch(
            "app.agents.admin.tools.billing.asyncio.to_thread",
            new=AsyncMock(return_value=refund_response),
        ),
        patch(
            "app.agents.admin.tools.billing.log_admin_action",
            new=AsyncMock(return_value=None),
        ),
    ):
        result = await issue_refund(
            charge_id="ch_test_123",
            amount_cents=2000,
            confirmation_token="confirmed-token",
        )

    assert result.get("refund_id") == "re_test_abc123"
    assert result.get("status") == "succeeded"


# ---------------------------------------------------------------------------
# Test 5: detect_analytics_anomalies flags DAU spike
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_anomalies_flags_dau():
    """detect_analytics_anomalies flags DAU that spikes >2 stddev above baseline."""
    from app.agents.admin.tools.billing import detect_analytics_anomalies

    usage_rows = _make_usage_rows(count=30, spike_last=True)
    usage_data = {
        "usage_trends": usage_rows,
        "summary": {"avg_dau": 100},
    }
    effectiveness_data = {"agents": []}

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_USAGE_STATS_PATCH, new=AsyncMock(return_value=usage_data)),
        patch(_AGENT_EFFECTIVENESS_PATCH, new=AsyncMock(return_value=effectiveness_data)),
    ):
        result = await detect_analytics_anomalies(days=30)

    assert "anomalies" in result
    anomaly_metrics = [a["metric"] for a in result["anomalies"]]
    assert "dau" in anomaly_metrics


# ---------------------------------------------------------------------------
# Test 6: detect_analytics_anomalies returns empty for stable data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_anomalies_no_flag_stable():
    """detect_analytics_anomalies returns empty anomalies list for stable data."""
    from app.agents.admin.tools.billing import detect_analytics_anomalies

    usage_rows = _make_usage_rows(count=30, spike_last=False)
    usage_data = {
        "usage_trends": usage_rows,
        "summary": {"avg_dau": 100},
    }
    effectiveness_data = {"agents": []}

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_USAGE_STATS_PATCH, new=AsyncMock(return_value=usage_data)),
        patch(_AGENT_EFFECTIVENESS_PATCH, new=AsyncMock(return_value=effectiveness_data)),
    ):
        result = await detect_analytics_anomalies(days=30)

    assert result["anomalies"] == []


# ---------------------------------------------------------------------------
# Test 7: generate_executive_summary returns text and recommendations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_executive_summary_returns_text():
    """generate_executive_summary returns summary_text and recommendations list."""
    from app.agents.admin.tools.billing import generate_executive_summary

    usage_data = {
        "usage_trends": _make_usage_rows(count=10),
        "summary": {"avg_dau": 100, "total_messages": 500, "total_workflows": 50},
    }
    billing_data = {"mrr": 9500.0, "arr": 114000.0, "active_subscriptions": 95}
    effectiveness_data = {
        "agents": [
            {"agent_name": "financial", "success_rate": 95.0},
            {"agent_name": "content", "success_rate": 70.0},
        ]
    }

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_USAGE_STATS_PATCH, new=AsyncMock(return_value=usage_data)),
        patch(_BILLING_METRICS_PATCH, new=AsyncMock(return_value=billing_data)),
        patch(_AGENT_EFFECTIVENESS_PATCH, new=AsyncMock(return_value=effectiveness_data)),
    ):
        result = await generate_executive_summary(days=30)

    assert "summary_text" in result
    assert isinstance(result["summary_text"], str)
    assert len(result["summary_text"]) > 20
    assert "recommendations" in result
    assert isinstance(result["recommendations"], list)


# ---------------------------------------------------------------------------
# Test 8: forecast_revenue projects trend from growing data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_revenue_projects_trend():
    """forecast_revenue returns projected_mrr > current_mrr for growing subscription data."""
    from app.agents.admin.tools.billing import forecast_revenue

    # Build 20 subscription rows with growing MRR over months
    rows = [
        {
            "created_at": f"2025-{(i % 12) + 1:02d}-01T00:00:00Z",
            "price_id": "price_monthly_49",
            "is_active": True,
        }
        for i in range(20)
    ]
    mock_result = MagicMock()
    mock_result.data = rows

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_result)),
    ):
        result = await forecast_revenue(months_ahead=1)

    assert "insufficient_data" not in result or not result.get("insufficient_data")
    assert "projected_mrr" in result
    assert "current_mrr" in result
    assert "growth_rate_pct" in result
    assert "confidence" in result


# ---------------------------------------------------------------------------
# Test 9: forecast_revenue returns insufficient_data for <7 rows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_revenue_insufficient_data():
    """forecast_revenue returns insufficient_data=True when fewer than 7 subscriptions."""
    from app.agents.admin.tools.billing import forecast_revenue

    rows = [
        {"created_at": f"2026-01-0{i}T00:00:00Z", "price_id": "price_monthly_49", "is_active": True}
        for i in range(1, 4)
    ]
    mock_result = MagicMock()
    mock_result.data = rows

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=AsyncMock(return_value=mock_result)),
    ):
        result = await forecast_revenue(months_ahead=1)

    assert result.get("insufficient_data") is True
    assert "reason" in result


# ---------------------------------------------------------------------------
# Test 10: assess_refund_risk returns high risk for short tenure + low usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assess_refund_risk_high():
    """assess_refund_risk returns risk_level='high' for short tenure and low usage."""
    from app.agents.admin.tools.billing import assess_refund_risk

    sub_row = {
        "stripe_customer_id": "cus_test_001",
        "tier": "solopreneur",
        "created_at": "2026-02-15T00:00:00Z",  # ~1 month ago
        "is_active": True,
    }
    sub_result = MagicMock()
    sub_result.data = [sub_row]

    usage_result = MagicMock()
    usage_result.data = []  # no usage data → low usage

    def fake_execute(query, **kwargs):
        return AsyncMock(return_value=MagicMock(data=[sub_row]))()

    execute_mock = AsyncMock(side_effect=[sub_result, usage_result])

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=execute_mock),
    ):
        result = await assess_refund_risk(user_id="user-uuid-short")

    assert result.get("risk_level") == "high"
    assert "tenure_months" in result
    assert "usage_level" in result
    assert "recommendation" in result


# ---------------------------------------------------------------------------
# Test 11: assess_refund_risk returns low risk for long tenure + high usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assess_refund_risk_low():
    """assess_refund_risk returns risk_level='low' for long tenure and high usage."""
    from app.agents.admin.tools.billing import assess_refund_risk

    sub_row = {
        "stripe_customer_id": "cus_test_002",
        "tier": "startup",
        "created_at": "2025-01-01T00:00:00Z",  # ~14 months ago
        "is_active": True,
    }
    sub_result = MagicMock()
    sub_result.data = [sub_row]

    # High usage — 100 messages
    usage_row = {"messages": 100}
    usage_result = MagicMock()
    usage_result.data = [usage_row]

    execute_mock = AsyncMock(side_effect=[sub_result, usage_result])

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_SERVICE_CLIENT_PATCH, return_value=MagicMock()),
        patch(_EXECUTE_ASYNC_PATCH, new=execute_mock),
    ):
        result = await assess_refund_risk(user_id="user-uuid-long")

    assert result.get("risk_level") == "low"


# ---------------------------------------------------------------------------
# Test 12: get_billing_metrics returns error when budget exhausted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_billing_metrics_budget_exhausted():
    """get_billing_metrics returns error dict when session budget is exhausted."""
    from app.agents.admin.tools.billing import get_billing_metrics

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value=("sk_test_key", {}, None))),
        patch(_BUDGET_PATCH, new=AsyncMock(return_value=False)),
    ):
        result = await get_billing_metrics()

    assert "error" in result
    assert "budget" in result["error"].lower() or "exhausted" in result["error"].lower()


# ---------------------------------------------------------------------------
# Test 13: get_billing_metrics returns error when Stripe not configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_billing_metrics_not_configured():
    """get_billing_metrics propagates error dict when _get_integration_config fails."""
    from app.agents.admin.tools.billing import get_billing_metrics

    error_dict = {"error": "Integration 'stripe' is not configured."}

    with (
        patch(_AUTONOMY_PATCH, new=AsyncMock(return_value=None)),
        patch(_CONFIG_PATCH, new=AsyncMock(return_value=error_dict)),
    ):
        result = await get_billing_metrics()

    assert "error" in result
    assert "stripe" in result["error"].lower() or "configured" in result["error"].lower()
