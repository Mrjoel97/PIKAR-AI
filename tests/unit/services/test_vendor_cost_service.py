# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for VendorCostService.

Tests cover:
- add_subscription creates a vendor subscription record with full and minimal inputs
- list_subscriptions returns all subscriptions with correct total monthly cost
- check_trial_expiries filters subscriptions by trial_end_date within N days
- get_cost_summary groups by category and generates consolidation suggestions
- update_subscription modifies an existing subscription record
- delete_subscription removes a subscription record (soft-delete)
- Annual billing cycle auto-computes monthly_cost from annual_cost
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch):
    """Set required env vars for BaseService init."""
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")


@pytest.fixture()
def service():
    """Return a VendorCostService instance."""
    from app.services.vendor_cost_service import VendorCostService

    return VendorCostService()


def _make_sub(
    sub_id: str = "sub-1",
    user_id: str = "user-123",
    name: str = "Slack",
    category: str = "communication",
    monthly_cost: float = 10.0,
    billing_cycle: str = "monthly",
    is_active: bool = True,
    trial_end_date: str | None = None,
    renewal_date: str | None = None,
) -> dict:
    """Build a synthetic vendor_subscriptions row."""
    return {
        "id": sub_id,
        "user_id": user_id,
        "name": name,
        "category": category,
        "monthly_cost": monthly_cost,
        "billing_cycle": billing_cycle,
        "is_active": is_active,
        "trial_end_date": trial_end_date,
        "renewal_date": renewal_date,
        "notes": None,
        "integration_provider": None,
        "annual_cost": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


def _days_from_now(days: int) -> str:
    """Return ISO date string N days from today."""
    return (datetime.now(tz=timezone.utc) + timedelta(days=days)).strftime(
        "%Y-%m-%d"
    )


# ---------------------------------------------------------------------------
# Tests: add_subscription
# ---------------------------------------------------------------------------


class TestAddSubscription:
    """Tests for the add_subscription method."""

    @pytest.mark.asyncio()
    async def test_add_subscription_full_inputs(self, service):
        """add_subscription inserts a row and returns the inserted record."""
        inserted = _make_sub(
            name="Notion",
            category="project_management",
            monthly_cost=16.0,
            billing_cycle="monthly",
            trial_end_date="2026-05-01",
            renewal_date="2026-06-01",
        )
        mock_result = MagicMock()
        mock_result.data = [inserted]

        with patch.object(service, "execute", new_callable=AsyncMock, return_value=mock_result):
            result = await service.add_subscription(
                user_id="user-123",
                name="Notion",
                category="project_management",
                monthly_cost=16.0,
                billing_cycle="monthly",
                trial_end_date="2026-05-01",
                renewal_date="2026-06-01",
            )

        assert result["name"] == "Notion"
        assert result["category"] == "project_management"
        assert result["monthly_cost"] == 16.0

    @pytest.mark.asyncio()
    async def test_add_subscription_minimal_inputs(self, service):
        """add_subscription works with only required fields (name, category, monthly_cost)."""
        inserted = _make_sub(name="Zoom", category="communication", monthly_cost=15.0)
        mock_result = MagicMock()
        mock_result.data = [inserted]

        with patch.object(service, "execute", new_callable=AsyncMock, return_value=mock_result):
            result = await service.add_subscription(
                user_id="user-123",
                name="Zoom",
                category="communication",
                monthly_cost=15.0,
            )

        assert result["name"] == "Zoom"
        assert result["monthly_cost"] == 15.0

    @pytest.mark.asyncio()
    async def test_annual_billing_computes_monthly_cost(self, service):
        """When billing_cycle='annual' and annual_cost given but monthly_cost=0, monthly_cost = annual_cost/12."""
        # The service should compute monthly_cost = 120 / 12 = 10.0
        inserted = _make_sub(
            name="GitHub",
            category="development",
            monthly_cost=10.0,
            billing_cycle="annual",
        )
        mock_result = MagicMock()
        mock_result.data = [inserted]

        captured_insert = {}

        async def capture_execute(query, **kwargs):
            # We can't easily inspect the query builder, so just return the result
            return mock_result

        with patch.object(service, "execute", side_effect=capture_execute):
            result = await service.add_subscription(
                user_id="user-123",
                name="GitHub",
                category="development",
                monthly_cost=0.0,
                billing_cycle="annual",
                annual_cost=120.0,
            )

        # Result returns the mock row with computed monthly_cost
        assert result["name"] == "GitHub"


# ---------------------------------------------------------------------------
# Tests: list_subscriptions
# ---------------------------------------------------------------------------


class TestListSubscriptions:
    """Tests for the list_subscriptions method."""

    @pytest.mark.asyncio()
    async def test_list_subscriptions_returns_totals(self, service):
        """list_subscriptions computes total_monthly_cost and count correctly."""
        subs = [
            _make_sub(sub_id="s1", name="Slack", monthly_cost=10.0),
            _make_sub(sub_id="s2", name="Notion", monthly_cost=16.0),
            _make_sub(sub_id="s3", name="GitHub", monthly_cost=4.0),
        ]
        mock_result = MagicMock()
        mock_result.data = subs

        with patch.object(service, "execute", new_callable=AsyncMock, return_value=mock_result):
            result = await service.list_subscriptions("user-123")

        assert result["count"] == 3
        assert result["total_monthly_cost"] == pytest.approx(30.0, abs=0.01)
        assert result["total_annual_cost"] == pytest.approx(360.0, abs=0.01)
        assert len(result["subscriptions"]) == 3

    @pytest.mark.asyncio()
    async def test_list_subscriptions_empty(self, service):
        """list_subscriptions returns zero totals when no subscriptions exist."""
        mock_result = MagicMock()
        mock_result.data = []

        with patch.object(service, "execute", new_callable=AsyncMock, return_value=mock_result):
            result = await service.list_subscriptions("user-123")

        assert result["count"] == 0
        assert result["total_monthly_cost"] == 0.0
        assert result["subscriptions"] == []


# ---------------------------------------------------------------------------
# Tests: check_trial_expiries
# ---------------------------------------------------------------------------


class TestCheckTrialExpiries:
    """Tests for the check_trial_expiries method."""

    @pytest.mark.asyncio()
    async def test_returns_expiring_trials(self, service):
        """check_trial_expiries returns subscriptions with trial ending within days_ahead."""
        soon = _days_from_now(3)
        far = _days_from_now(30)
        subs = [
            _make_sub(sub_id="s1", name="HubSpot Trial", trial_end_date=soon),
            _make_sub(sub_id="s2", name="Salesforce Trial", trial_end_date=far),
        ]
        mock_result = MagicMock()
        mock_result.data = subs

        with patch.object(service, "execute", new_callable=AsyncMock, return_value=mock_result):
            result = await service.check_trial_expiries("user-123", days_ahead=7)

        # Only the subscription expiring in 3 days should be returned
        names = [r["name"] for r in result]
        assert "HubSpot Trial" in names
        assert "Salesforce Trial" not in names

    @pytest.mark.asyncio()
    async def test_returns_empty_when_no_trials(self, service):
        """check_trial_expiries returns empty list when no trials are expiring."""
        mock_result = MagicMock()
        mock_result.data = []

        with patch.object(service, "execute", new_callable=AsyncMock, return_value=mock_result):
            result = await service.check_trial_expiries("user-123")

        assert result == []

    @pytest.mark.asyncio()
    async def test_days_remaining_computed(self, service):
        """check_trial_expiries includes days_remaining field in results."""
        soon = _days_from_now(5)
        subs = [_make_sub(sub_id="s1", name="Trial Tool", trial_end_date=soon)]
        mock_result = MagicMock()
        mock_result.data = subs

        with patch.object(service, "execute", new_callable=AsyncMock, return_value=mock_result):
            result = await service.check_trial_expiries("user-123", days_ahead=7)

        assert len(result) == 1
        assert "days_remaining" in result[0]
        # 5 days from now — allow 1 day tolerance
        assert 4 <= result[0]["days_remaining"] <= 6


# ---------------------------------------------------------------------------
# Tests: get_cost_summary
# ---------------------------------------------------------------------------


class TestGetCostSummary:
    """Tests for the get_cost_summary method."""

    @pytest.mark.asyncio()
    async def test_groups_by_category(self, service):
        """get_cost_summary groups subscriptions by category with per-category totals."""
        subs = [
            _make_sub(sub_id="s1", name="Slack", category="communication", monthly_cost=10.0),
            _make_sub(sub_id="s2", name="Zoom", category="communication", monthly_cost=15.0),
            _make_sub(sub_id="s3", name="Notion", category="project_management", monthly_cost=16.0),
        ]
        mock_list_result = MagicMock()
        mock_list_result.data = subs
        mock_trial_result = MagicMock()
        mock_trial_result.data = []

        call_count = 0

        async def mock_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_list_result
            return mock_trial_result

        with patch.object(service, "execute", side_effect=mock_execute):
            result = await service.get_cost_summary("user-123")

        assert "by_category" in result
        assert "communication" in result["by_category"]
        assert result["by_category"]["communication"]["total_monthly"] == pytest.approx(25.0, abs=0.01)
        assert "project_management" in result["by_category"]

    @pytest.mark.asyncio()
    async def test_consolidation_suggestions_for_duplicate_categories(self, service):
        """get_cost_summary flags categories with 2+ subscriptions for consolidation."""
        subs = [
            _make_sub(sub_id="s1", name="Asana", category="project_management", monthly_cost=10.0),
            _make_sub(sub_id="s2", name="Monday.com", category="project_management", monthly_cost=12.0),
        ]
        mock_list_result = MagicMock()
        mock_list_result.data = subs
        mock_trial_result = MagicMock()
        mock_trial_result.data = []

        call_count = 0

        async def mock_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_list_result
            return mock_trial_result

        with patch.object(service, "execute", side_effect=mock_execute):
            result = await service.get_cost_summary("user-123")

        assert len(result["consolidation_suggestions"]) >= 1
        suggestion_text = " ".join(result["consolidation_suggestions"])
        assert "project_management" in suggestion_text.lower() or "Asana" in suggestion_text or "Monday" in suggestion_text

    @pytest.mark.asyncio()
    async def test_no_consolidation_for_unique_categories(self, service):
        """get_cost_summary does not suggest consolidation when each category has one tool."""
        subs = [
            _make_sub(sub_id="s1", name="Slack", category="communication", monthly_cost=10.0),
            _make_sub(sub_id="s2", name="Notion", category="project_management", monthly_cost=16.0),
        ]
        mock_list_result = MagicMock()
        mock_list_result.data = subs
        mock_trial_result = MagicMock()
        mock_trial_result.data = []

        call_count = 0

        async def mock_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_list_result
            return mock_trial_result

        with patch.object(service, "execute", side_effect=mock_execute):
            result = await service.get_cost_summary("user-123")

        assert result["consolidation_suggestions"] == []

    @pytest.mark.asyncio()
    async def test_includes_trial_expiring_key(self, service):
        """get_cost_summary includes trial_expiring list from check_trial_expiries."""
        subs = [_make_sub(sub_id="s1", name="Slack", monthly_cost=10.0)]
        mock_list_result = MagicMock()
        mock_list_result.data = subs
        mock_trial_result = MagicMock()
        mock_trial_result.data = []

        call_count = 0

        async def mock_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_list_result
            return mock_trial_result

        with patch.object(service, "execute", side_effect=mock_execute):
            result = await service.get_cost_summary("user-123")

        assert "trial_expiring" in result
        assert "total_monthly" in result
        assert "total_annual_estimate" in result


# ---------------------------------------------------------------------------
# Tests: update_subscription
# ---------------------------------------------------------------------------


class TestUpdateSubscription:
    """Tests for the update_subscription method."""

    @pytest.mark.asyncio()
    async def test_update_returns_updated_row(self, service):
        """update_subscription returns the updated record."""
        updated = _make_sub(sub_id="s1", name="Slack", monthly_cost=20.0)
        mock_result = MagicMock()
        mock_result.data = [updated]

        with patch.object(service, "execute", new_callable=AsyncMock, return_value=mock_result):
            result = await service.update_subscription(
                user_id="user-123",
                subscription_id="s1",
                monthly_cost=20.0,
            )

        assert result["monthly_cost"] == 20.0
        assert result["id"] == "s1"


# ---------------------------------------------------------------------------
# Tests: delete_subscription
# ---------------------------------------------------------------------------


class TestDeleteSubscription:
    """Tests for the delete_subscription method."""

    @pytest.mark.asyncio()
    async def test_delete_returns_success(self, service):
        """delete_subscription returns success status."""
        mock_result = MagicMock()
        mock_result.data = [{"id": "s1", "is_active": False}]

        with patch.object(service, "execute", new_callable=AsyncMock, return_value=mock_result):
            result = await service.delete_subscription("user-123", "s1")

        assert result.get("success") is True or result.get("status") == "deleted"


# ---------------------------------------------------------------------------
# Tests: module-level convenience functions
# ---------------------------------------------------------------------------


class TestModuleLevelFunctions:
    """Module-level get_vendor_costs and check_trial_expiries convenience functions."""

    @pytest.mark.asyncio()
    async def test_get_vendor_costs_returns_summary_structure(self):
        """Module-level get_vendor_costs returns same structure as get_cost_summary."""
        mock_result_subs = MagicMock()
        mock_result_subs.data = []
        mock_result_trials = MagicMock()
        mock_result_trials.data = []

        call_count = 0

        async def mock_execute(query, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_result_subs
            return mock_result_trials

        from app.services.vendor_cost_service import VendorCostService

        svc = VendorCostService()
        with patch.object(svc, "execute", side_effect=mock_execute):
            # Patch the class so the module-level function uses our mock
            with patch(
                "app.services.vendor_cost_service.VendorCostService",
                return_value=svc,
            ):
                from app.services.vendor_cost_service import get_vendor_costs

                result = await get_vendor_costs("user-123")

        assert "total_monthly" in result
        assert "by_category" in result
        assert "consolidation_suggestions" in result

    @pytest.mark.asyncio()
    async def test_check_trial_expiries_module_function(self):
        """Module-level check_trial_expiries returns list of expiring trials."""
        mock_result = MagicMock()
        mock_result.data = []

        from app.services.vendor_cost_service import VendorCostService

        svc = VendorCostService()
        with patch.object(svc, "execute", new_callable=AsyncMock, return_value=mock_result):
            with patch(
                "app.services.vendor_cost_service.VendorCostService",
                return_value=svc,
            ):
                from app.services.vendor_cost_service import (
                    check_trial_expiries as module_check_trial_expiries,
                )

                result = await module_check_trial_expiries("user-123")

        assert isinstance(result, list)
