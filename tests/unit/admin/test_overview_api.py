# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for admin overview API endpoint.

Tests verify:
- GET /admin/overview returns six cards in stable order
- One failing card source degrades only that card to neutral '—'
- Card status mapping (ok / warn / error / neutral) follows the documented thresholds
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request as StarletteRequest


def _make_mock_request():
    """Create a minimal Starlette Request for the slowapi rate limiter dependency."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/admin/overview",
        "query_string": b"",
        "headers": [(b"x-forwarded-for", b"127.0.0.1")],
        "client": ("127.0.0.1", 12345),
    }
    return StarletteRequest(scope=scope)


def _count_result(n: int) -> MagicMock:
    """Mimic Supabase count='exact' result shape."""
    r = MagicMock()
    r.count = n
    r.data = []
    return r


def _row_result(rows: list[dict]) -> MagicMock:
    r = MagicMock()
    r.count = None
    r.data = rows
    return r


def _mock_obs_service(
    *, error_rate: float = 0.0, total_count: int = 0, error_count: int = 0
):
    """Build a mock ObservabilityMetricsService instance.

    Patching the class itself (rather than its method) bypasses the real
    constructor, which requires SUPABASE_URL at import time and would
    otherwise blow up the test under bare environments.
    """
    instance = MagicMock()
    instance.compute_error_rate = AsyncMock(
        return_value={
            "error_rate": error_rate,
            "error_count": error_count,
            "total_count": total_count,
        }
    )
    return instance


@pytest.fixture
def admin_user_dict():
    """Minimal admin payload matching require_admin's contract."""
    return {
        "id": "admin-user-id",
        "email": "admin@pikar-ai.com",
        "role": "authenticated",
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# Happy path: every source returns clean data, all six cards render.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_overview_returns_six_cards_in_stable_order(admin_user_dict):
    """All sources succeed → six cards, in the documented order, with mapped statuses."""
    from app.routers.admin.overview import get_admin_overview

    async def fake_execute_async(query, op_name=""):
        # System status — five 'healthy' rows
        if op_name.startswith("overview.system_status."):
            return _row_result([{"status": "healthy"}])
        if op_name == "overview.active_users":
            return _count_result(42)
        if op_name == "overview.pending_approvals":
            return _count_result(0)
        if op_name == "overview.workflow_queue":
            return _count_result(3)
        if op_name == "overview.recent_alerts":
            return _count_result(0)
        return _row_result([])

    with (
        patch(
            "app.routers.admin.overview.get_service_client", return_value=MagicMock()
        ),
        patch(
            "app.routers.admin.overview.execute_async",
            side_effect=fake_execute_async,
        ),
        patch(
            "app.services.observability_metrics_service.ObservabilityMetricsService",
            return_value=_mock_obs_service(error_rate=0.005, total_count=200),
        ),
    ):
        result = await get_admin_overview(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    cards = result["cards"]
    assert len(cards) == 6

    # Stable order matches _CARDS in the router
    titles = [c["title"] for c in cards]
    assert titles == [
        "System Status",
        "Active Users",
        "Pending Approvals",
        "Agent Health",
        "Workflow Queue",
        "Recent Alerts",
    ]

    # System Status: all healthy → Operational/ok
    assert cards[0] == {"title": "System Status", "value": "Operational", "status": "ok"}
    # Active Users: 42 → ok
    assert cards[1]["value"] == "42"
    assert cards[1]["status"] == "ok"
    # Pending Approvals: 0 → ok (no backlog)
    assert cards[2] == {"title": "Pending Approvals", "value": "0", "status": "ok"}
    # Agent Health: 0.5% error rate → Healthy/ok
    assert cards[3] == {"title": "Agent Health", "value": "Healthy", "status": "ok"}
    # Workflow Queue
    assert cards[4]["value"] == "3"
    # Recent Alerts: 0 → ok
    assert cards[5] == {"title": "Recent Alerts", "value": "0", "status": "ok"}


# ---------------------------------------------------------------------------
# Partial failure: one source raises, only that card degrades.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_overview_degrades_only_failing_card(admin_user_dict):
    """If pending_approvals query throws, that card becomes neutral '—' but others render."""
    from app.routers.admin.overview import get_admin_overview

    async def fake_execute_async(query, op_name=""):
        if op_name.startswith("overview.system_status."):
            return _row_result([{"status": "healthy"}])
        if op_name == "overview.active_users":
            return _count_result(10)
        if op_name == "overview.pending_approvals":
            raise RuntimeError("approval_requests table missing")
        if op_name == "overview.workflow_queue":
            return _count_result(5)
        if op_name == "overview.recent_alerts":
            return _count_result(0)
        return _row_result([])

    with (
        patch(
            "app.routers.admin.overview.get_service_client", return_value=MagicMock()
        ),
        patch(
            "app.routers.admin.overview.execute_async",
            side_effect=fake_execute_async,
        ),
        patch(
            "app.services.observability_metrics_service.ObservabilityMetricsService",
            return_value=_mock_obs_service(error_rate=0.0, total_count=0),
        ),
    ):
        result = await get_admin_overview(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    cards = {c["title"]: c for c in result["cards"]}

    # Failing card → neutral '—'
    assert cards["Pending Approvals"] == {
        "title": "Pending Approvals",
        "value": "—",
        "status": "neutral",
    }
    # Others still rendered with real values
    assert cards["System Status"]["status"] == "ok"
    assert cards["Active Users"]["value"] == "10"
    assert cards["Workflow Queue"]["value"] == "5"
    # Agent Health with zero samples → "No data"/neutral, not red
    assert cards["Agent Health"] == {
        "title": "Agent Health",
        "value": "No data",
        "status": "neutral",
    }


# ---------------------------------------------------------------------------
# Threshold mapping for Agent Health card.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error_rate", "expected_value", "expected_status"),
    [
        (0.005, "Healthy", "ok"),  # 0.5% — well under warn threshold
        (0.025, "Warning", "warn"),  # 2.5% — between warn and error
        (0.10, "Degraded", "error"),  # 10% — over error threshold
    ],
)
@pytest.mark.asyncio
async def test_agent_health_card_threshold_mapping(
    admin_user_dict, error_rate, expected_value, expected_status
):
    """Agent Health card maps error rate to ok/warn/error per documented thresholds."""
    from app.routers.admin.overview import get_admin_overview

    async def fake_execute_async(query, op_name=""):
        if op_name.startswith("overview.system_status."):
            return _row_result([{"status": "healthy"}])
        return _count_result(0)

    with (
        patch(
            "app.routers.admin.overview.get_service_client", return_value=MagicMock()
        ),
        patch(
            "app.routers.admin.overview.execute_async",
            side_effect=fake_execute_async,
        ),
        patch(
            "app.services.observability_metrics_service.ObservabilityMetricsService",
            return_value=_mock_obs_service(
                error_rate=error_rate, error_count=5, total_count=200
            ),
        ),
    ):
        result = await get_admin_overview(
            request=_make_mock_request(),
            admin_user=admin_user_dict,
        )

    agent_card = next(c for c in result["cards"] if c["title"] == "Agent Health")
    assert agent_card["value"] == expected_value
    assert agent_card["status"] == expected_status
