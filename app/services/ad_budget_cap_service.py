# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""AdBudgetCapService — Per-platform monthly ad spend cap enforcement.

This service is the safety net for all ad budget operations.  Before any
budget-creating or budget-increasing action on Google Ads or Meta Ads,
callers should invoke ``check_budget_headroom`` to ensure the proposed spend
will not exceed the user's configured monthly cap.

The cap must be set (via ``set_cap``) before completing the OAuth flow for
any ad platform.  The router layer is responsible for enforcing this
pre-condition.

All writes use ``AdminService`` (service role) so the service can be called
from background workers or internal operations that carry no user JWT.

Usage::

    svc = AdBudgetCapService(user_token=jwt)
    result = await svc.check_budget_headroom(user_id, "google_ads", 50.0)
    if not result["allowed"]:
        raise ValueError(result["message"])
"""

from __future__ import annotations

import logging
from calendar import monthrange
from datetime import date
from typing import Any

from app.services.base_service import AdminService, BaseService

logger = logging.getLogger(__name__)


class AdBudgetCapService(BaseService):
    """Enforce per-user, per-platform monthly ad spend caps.

    Reads from ``ad_budget_caps`` (via RLS with the user token) for
    ``get_cap`` and ``is_cap_set``.  Writes always use ``AdminService``
    (service role) so caps can be set from admin workflows or background
    tasks without a user JWT.

    Args:
        user_token: User JWT for Supabase RLS (passed to BaseService).
    """

    # -------------------------------------------------------------------------
    # Cap read/write
    # -------------------------------------------------------------------------

    async def get_cap(self, user_id: str, platform: str) -> float | None:
        """Retrieve the monthly cap for a user + platform.

        Args:
            user_id: The user's UUID.
            platform: ``"google_ads"`` or ``"meta_ads"``.

        Returns:
            Monthly cap in USD, or ``None`` if no cap has been set.
        """
        result = await self.execute(
            self.client.table("ad_budget_caps")
            .select("monthly_cap")
            .eq("user_id", user_id)
            .eq("platform", platform),
            op_name="ad_budget_caps.get_cap",
        )
        if result.data:
            return float(result.data[0]["monthly_cap"])
        return None

    async def set_cap(
        self, user_id: str, platform: str, monthly_cap: float
    ) -> dict[str, Any]:
        """Set or update the monthly cap for a user + platform.

        Uses an upsert on the ``(user_id, platform)`` unique constraint so
        this method is idempotent — safe to call on both initial setup and
        subsequent updates.

        Writes with ``AdminService`` (service role) to support admin
        workflows and background tasks that carry no user JWT.

        Args:
            user_id: The user's UUID.
            platform: ``"google_ads"`` or ``"meta_ads"``.
            monthly_cap: Monthly budget ceiling in USD.

        Returns:
            The upserted row dict.
        """
        admin = AdminService()
        row = {
            "user_id": user_id,
            "platform": platform,
            "monthly_cap": monthly_cap,
        }
        result = await self.execute(
            admin.client.table("ad_budget_caps").upsert(
                row, on_conflict="user_id,platform"
            ),
            op_name="ad_budget_caps.set_cap",
        )
        return result.data[0] if result.data else row

    async def is_cap_set(self, user_id: str, platform: str) -> bool:
        """Check whether a monthly cap has been configured for user + platform.

        Args:
            user_id: The user's UUID.
            platform: ``"google_ads"`` or ``"meta_ads"``.

        Returns:
            ``True`` if a cap row exists, ``False`` otherwise.
        """
        cap = await self.get_cap(user_id, platform)
        return cap is not None

    # -------------------------------------------------------------------------
    # Headroom calculation
    # -------------------------------------------------------------------------

    async def check_budget_headroom(
        self,
        user_id: str,
        platform: str,
        proposed_daily_budget: float,
    ) -> dict[str, Any]:
        """Check whether a proposed daily budget fits within the monthly cap.

        The calculation:
        - ``committed`` = sum of all active campaign daily_budgets × remaining
          calendar days in the current month.
        - ``headroom`` = monthly_cap - committed.
        - ``proposed_monthly`` = proposed_daily_budget × remaining days.
        - ``allowed`` = proposed_monthly <= headroom.

        Args:
            user_id: The user's UUID.
            platform: ``"google_ads"`` or ``"meta_ads"``.
            proposed_daily_budget: Proposed new daily budget in USD.

        Returns:
            Dict with keys::

                {
                    "allowed": bool,
                    "monthly_cap": float | None,
                    "committed": float,
                    "headroom": float,
                    "proposed_monthly": float,
                    "remaining_days": int,
                    "message": str,
                }

            If no cap is set, ``allowed`` is ``True`` with a warning message.
        """
        cap = await self.get_cap(user_id, platform)

        if cap is None:
            return {
                "allowed": True,
                "monthly_cap": None,
                "committed": 0.0,
                "headroom": float("inf"),
                "proposed_monthly": 0.0,
                "remaining_days": 0,
                "message": (
                    f"No monthly cap set for {platform}. "
                    "Consider setting a cap in Settings to control ad spend."
                ),
            }

        today = date.today()
        _, days_in_month = monthrange(today.year, today.month)
        remaining_days = max(days_in_month - today.day + 1, 1)

        # Sum daily_budget of all active campaigns for this user + platform
        result = await self.execute(
            self.client.table("ad_campaigns")
            .select("daily_budget")
            .eq("user_id", user_id)
            .eq("platform", platform)
            .eq("status", "active"),
            op_name="ad_budget_caps.check_headroom",
        )
        active_campaigns = result.data or []
        active_daily_total = sum(
            float(row.get("daily_budget") or 0) for row in active_campaigns
        )

        committed = active_daily_total * remaining_days
        headroom = cap - committed
        proposed_monthly = proposed_daily_budget * remaining_days
        allowed = proposed_monthly <= headroom

        if allowed:
            message = (
                f"Budget approved. ${proposed_monthly:.2f} proposed "
                f"fits within ${headroom:.2f} remaining of your "
                f"${cap:.2f}/mo {platform} cap."
            )
        else:
            message = (
                f"This would exceed your ${cap:.2f}/mo {platform} cap "
                f"(${committed:.2f} already committed). "
                "Increase your cap in Settings or reduce other campaigns."
            )

        return {
            "allowed": allowed,
            "monthly_cap": cap,
            "committed": committed,
            "headroom": headroom,
            "proposed_monthly": proposed_monthly,
            "remaining_days": remaining_days,
            "message": message,
        }


__all__ = ["AdBudgetCapService"]
