# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""VendorCostService — SaaS subscription and vendor cost tracking.

Provides CRUD operations for the vendor_subscriptions table, trial expiry
detection, and consolidation suggestion generation for the Operations Agent.

Usage::

    service = VendorCostService()
    summary = await service.get_cost_summary(user_id="user-123")
    # or use module-level convenience functions:
    from app.services.vendor_cost_service import get_vendor_costs
    summary = await get_vendor_costs(user_id="user-123")
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.base_service import BaseService

logger = logging.getLogger(__name__)

# Valid subscription categories
SUBSCRIPTION_CATEGORIES = frozenset(
    [
        "project_management",
        "communication",
        "analytics",
        "marketing",
        "design",
        "development",
        "crm",
        "accounting",
        "storage",
        "security",
        "other",
    ]
)

# Trial expiry default look-ahead window in days
_DEFAULT_TRIAL_DAYS_AHEAD = 7


class VendorCostService(BaseService):
    """Service for tracking SaaS subscriptions and vendor costs.

    Provides full CRUD for the vendor_subscriptions table plus higher-level
    analysis methods: trial expiry detection and cost consolidation suggestions.
    """

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def add_subscription(
        self,
        user_id: str,
        name: str,
        category: str,
        monthly_cost: float,
        billing_cycle: str = "monthly",
        annual_cost: float | None = None,
        renewal_date: str | None = None,
        trial_end_date: str | None = None,
        notes: str | None = None,
        integration_provider: str | None = None,
    ) -> dict[str, Any]:
        """Add a new SaaS subscription or vendor cost record.

        When ``billing_cycle`` is ``"annual"`` and ``annual_cost`` is provided
        but ``monthly_cost`` is 0, automatically computes
        ``monthly_cost = annual_cost / 12``.

        Args:
            user_id: Authenticated user identifier.
            name: Display name for the subscription (e.g. "Slack", "GitHub").
            category: Subscription category (e.g. "communication", "development").
            monthly_cost: Equivalent monthly cost in user's currency.
            billing_cycle: One of "monthly", "quarterly", "annual". Defaults to "monthly".
            annual_cost: Total annual cost if billing annually. Optional.
            renewal_date: Next renewal or billing date (ISO date string). Optional.
            trial_end_date: Trial expiry date (ISO date string). Optional.
            notes: Free-text notes about the subscription. Optional.
            integration_provider: Linked integration_credentials.provider slug. Optional.

        Returns:
            Inserted vendor_subscriptions row as a dict.
        """
        # Auto-compute monthly cost from annual if not provided
        if billing_cycle == "annual" and annual_cost and monthly_cost == 0:
            monthly_cost = annual_cost / 12

        row: dict[str, Any] = {
            "user_id": user_id,
            "name": name,
            "category": category,
            "monthly_cost": monthly_cost,
            "billing_cycle": billing_cycle,
        }
        if annual_cost is not None:
            row["annual_cost"] = annual_cost
        if renewal_date is not None:
            row["renewal_date"] = renewal_date
        if trial_end_date is not None:
            row["trial_end_date"] = trial_end_date
        if notes is not None:
            row["notes"] = notes
        if integration_provider is not None:
            row["integration_provider"] = integration_provider

        result = await self.execute(
            self.client.table("vendor_subscriptions").insert(row),
            op_name="vendor_costs.add_subscription",
        )
        data = result.data or []
        return data[0] if data else row

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list_subscriptions(
        self,
        user_id: str,
        active_only: bool = True,
    ) -> dict[str, Any]:
        """List all vendor subscriptions for a user with cost totals.

        Args:
            user_id: Authenticated user identifier.
            active_only: When True (default), only returns is_active=True rows.

        Returns:
            Dict with keys:
            - subscriptions: list of subscription rows
            - total_monthly_cost: sum of monthly_cost for returned rows
            - total_annual_cost: total_monthly_cost * 12
            - count: number of subscriptions
        """
        query = (
            self.client.table("vendor_subscriptions")
            .select("*")
            .eq("user_id", user_id)
            .order("name")
        )
        if active_only:
            query = query.eq("is_active", True)

        result = await self.execute(query, op_name="vendor_costs.list_subscriptions")
        subscriptions: list[dict] = result.data or []

        total_monthly = sum(float(s.get("monthly_cost", 0)) for s in subscriptions)
        return {
            "subscriptions": subscriptions,
            "total_monthly_cost": total_monthly,
            "total_annual_cost": total_monthly * 12,
            "count": len(subscriptions),
        }

    async def check_trial_expiries(
        self,
        user_id: str,
        days_ahead: int = _DEFAULT_TRIAL_DAYS_AHEAD,
    ) -> list[dict[str, Any]]:
        """Return subscriptions with a trial ending within ``days_ahead`` days.

        Queries active subscriptions with a non-null trial_end_date falling
        between today and today + days_ahead (inclusive). Enriches each result
        with a computed ``days_remaining`` field.

        Args:
            user_id: Authenticated user identifier.
            days_ahead: Look-ahead window in days (default 7).

        Returns:
            List of subscription dicts enriched with ``days_remaining``.
        """
        today = datetime.now(tz=timezone.utc).date()
        cutoff = today + timedelta(days=days_ahead)

        # Fetch active subscriptions with a trial_end_date set
        result = await self.execute(
            self.client.table("vendor_subscriptions")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .not_.is_("trial_end_date", "null"),
            op_name="vendor_costs.check_trial_expiries",
        )

        subscriptions: list[dict] = result.data or []
        enriched: list[dict] = []
        for sub in subscriptions:
            trial_date_str = sub.get("trial_end_date")
            if not trial_date_str:
                continue
            try:
                # Handle both date-only ("2026-05-01") and datetime strings
                trial_date_raw = trial_date_str.split("T")[0]
                trial_date = datetime.fromisoformat(trial_date_raw).date()
            except (ValueError, TypeError):
                continue
            # Python-side date filter: must be within [today, cutoff]
            if today <= trial_date <= cutoff:
                days_remaining = (trial_date - today).days
                enriched.append({**sub, "days_remaining": days_remaining})

        return enriched

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_subscription(
        self,
        user_id: str,
        subscription_id: str,
        **updates: Any,
    ) -> dict[str, Any]:
        """Update an existing subscription record.

        Args:
            user_id: Authenticated user identifier.
            subscription_id: UUID of the subscription to update.
            **updates: Fields to update (name, category, monthly_cost, etc.).

        Returns:
            Updated subscription row as a dict.
        """
        result = await self.execute(
            self.client.table("vendor_subscriptions")
            .update(updates)
            .eq("id", subscription_id)
            .eq("user_id", user_id),
            op_name="vendor_costs.update_subscription",
        )
        data = result.data or []
        return data[0] if data else {}

    # ------------------------------------------------------------------
    # Delete (soft-delete)
    # ------------------------------------------------------------------

    async def delete_subscription(
        self,
        user_id: str,
        subscription_id: str,
    ) -> dict[str, Any]:
        """Soft-delete a subscription by setting is_active=False.

        Preserves the historical record for cost reporting while removing
        the subscription from active tracking.

        Args:
            user_id: Authenticated user identifier.
            subscription_id: UUID of the subscription to delete.

        Returns:
            Dict with ``success=True`` and ``status="deleted"``.
        """
        await self.execute(
            self.client.table("vendor_subscriptions")
            .update({"is_active": False})
            .eq("id", subscription_id)
            .eq("user_id", user_id),
            op_name="vendor_costs.delete_subscription",
        )
        return {"success": True, "status": "deleted", "id": subscription_id}

    # ------------------------------------------------------------------
    # Summary / Analysis
    # ------------------------------------------------------------------

    async def get_cost_summary(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Build a consolidated cost summary with category breakdown and suggestions.

        Calls ``list_subscriptions`` and ``check_trial_expiries`` internally.
        Groups active subscriptions by category, detects consolidation
        opportunities (categories with 2+ tools), and surfaces trial expiry
        warnings.

        Args:
            user_id: Authenticated user identifier.

        Returns:
            Dict with keys:
            - total_monthly: total monthly spend across all active subscriptions
            - total_annual_estimate: total_monthly * 12
            - by_category: dict keyed by category with {tools, total_monthly, names}
            - trial_expiring: list of subscriptions with trials expiring within 7 days
            - consolidation_suggestions: list of plain-English suggestion strings
        """
        listing = await self.list_subscriptions(user_id, active_only=True)
        subscriptions = listing["subscriptions"]
        total_monthly = listing["total_monthly_cost"]

        # Group by category
        by_category: dict[str, dict[str, Any]] = {}
        for sub in subscriptions:
            cat = sub.get("category") or "other"
            if cat not in by_category:
                by_category[cat] = {
                    "tools": 0,
                    "total_monthly": 0.0,
                    "names": [],
                }
            by_category[cat]["tools"] += 1
            by_category[cat]["total_monthly"] += float(sub.get("monthly_cost", 0))
            by_category[cat]["names"].append(sub.get("name", "Unknown"))

        # Generate consolidation suggestions for categories with 2+ tools
        consolidation_suggestions: list[str] = []
        for cat, info in by_category.items():
            if info["tools"] >= 2:
                names_str = ", ".join(info["names"])
                potential_savings = round(info["total_monthly"] * 0.4, 2)
                consolidation_suggestions.append(
                    f"You have {info['tools']} {cat.replace('_', ' ')} tools "
                    f"({names_str}). Consider consolidating to reduce costs by "
                    f"~${potential_savings:.2f}/month."
                )

        # Trial expiry warnings (next 7 days)
        trial_expiring = await self.check_trial_expiries(
            user_id, days_ahead=_DEFAULT_TRIAL_DAYS_AHEAD
        )

        return {
            "total_monthly": total_monthly,
            "total_annual_estimate": total_monthly * 12,
            "by_category": by_category,
            "trial_expiring": trial_expiring,
            "consolidation_suggestions": consolidation_suggestions,
        }


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


async def get_vendor_costs(user_id: str) -> dict[str, Any]:
    """Return a full vendor cost summary for a user.

    Module-level convenience wrapper around
    ``VendorCostService.get_cost_summary``.

    Args:
        user_id: Authenticated user identifier.

    Returns:
        Dict with total_monthly, total_annual_estimate, by_category,
        trial_expiring, and consolidation_suggestions.
    """
    service = VendorCostService()
    return await service.get_cost_summary(user_id)


async def check_trial_expiries(
    user_id: str,
    days_ahead: int = _DEFAULT_TRIAL_DAYS_AHEAD,
) -> list[dict[str, Any]]:
    """Return subscriptions with trials expiring within ``days_ahead`` days.

    Module-level convenience wrapper around
    ``VendorCostService.check_trial_expiries``.

    Args:
        user_id: Authenticated user identifier.
        days_ahead: Look-ahead window in days (default 7).

    Returns:
        List of subscription dicts enriched with ``days_remaining``.
    """
    service = VendorCostService()
    return await service.check_trial_expiries(user_id, days_ahead)


__all__ = [
    "VendorCostService",
    "check_trial_expiries",
    "get_vendor_costs",
]
