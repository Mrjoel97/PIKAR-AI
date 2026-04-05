# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""AdApprovalService -- Approval gate for ad budget and spend operations.

All budget-increasing or campaign-activating operations on Google Ads and
Meta Ads are gated behind human approval. This service:

1. Determines whether an operation requires approval (``is_operation_gated``).
2. Builds a rich approval card with campaign details, projected monthly
   impact, and budget cap headroom, then calls ``request_human_approval``.
3. On approval, executes the actual platform API call via GoogleAdsService
   or MetaAdsService and updates the local ``ad_campaigns`` record.

Non-gated operations (pausing a campaign, reducing budget) execute
immediately without requiring approval.

Usage::

    svc = AdApprovalService()
    result = await svc.check_and_gate(
        user_id=user_id,
        operation="activate_campaign",
        platform="google_ads",
        campaign_name="Summer Sale",
        details={"campaign_id": "...", "customer_id": "...", "daily_budget": 50.0},
    )
    if result["approval_required"]:
        return {"message": result["message"]}
    # else: execute immediately or blocked
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.base_service import AdminService, BaseService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Operations that require human approval before execution.
# These all have the potential to start or increase real ad spend.
GATED_OPERATIONS: frozenset[str] = frozenset({
    "activate_campaign",     # draft / paused -> active (starts spending)
    "resume_campaign",       # paused -> active (re-starts spending)
    "increase_daily_budget", # daily budget goes up
    "increase_total_budget", # total budget goes up
    "increase_bid_amount",   # bid amount increases
    "change_bid_strategy",   # may increase spend indirectly
})

# Operations that execute immediately — no approval needed.
NON_GATED_OPERATIONS: frozenset[str] = frozenset({
    "create_draft_campaign", # no money moves; campaign stays paused
    "pause_campaign",        # stops spending
    "decrease_budget",       # reduces spending
    "update_targeting",      # on paused campaigns — no immediate spend
    "update_creative",       # on paused campaigns — no immediate spend
})

_PLATFORM_NAMES: dict[str, str] = {
    "google_ads": "Google Ads",
    "meta_ads": "Meta Ads",
}


class AdApprovalService(BaseService):
    """Gate budget/spend operations behind human approval cards.

    Args:
        user_token: User JWT for Supabase RLS (passed to BaseService).
    """

    # -------------------------------------------------------------------------
    # Gate classification
    # -------------------------------------------------------------------------

    async def is_operation_gated(self, operation: str) -> bool:
        """Return whether an operation requires human approval.

        Args:
            operation: Operation key (e.g. ``"activate_campaign"``).

        Returns:
            ``True`` if the operation is in ``GATED_OPERATIONS``.
        """
        return operation in GATED_OPERATIONS

    # -------------------------------------------------------------------------
    # Approval request
    # -------------------------------------------------------------------------

    async def request_budget_approval(
        self,
        user_id: str,
        operation: str,
        platform: str,
        campaign_name: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        """Create an approval request for a budget / spend operation.

        Builds an enriched payload including campaign details, projected
        monthly impact, and budget cap headroom, then calls
        ``request_human_approval`` from the approvals tool.

        Args:
            user_id: The user's UUID (used for budget cap check).
            operation: Operation key (must be in ``GATED_OPERATIONS``).
            platform: ``"google_ads"`` or ``"meta_ads"``.
            campaign_name: Human-readable campaign name.
            details: Operation-specific data (budget amounts, campaign IDs,
                     customer ID, etc.).

        Returns:
            Dict with keys: approval_required (True), approval_id,
            message (with approval link), card_data.
        """
        from app.agents.tools.approval_tool import request_human_approval
        from app.services.ad_budget_cap_service import AdBudgetCapService

        # Calculate projected monthly impact
        daily_budget = float(
            details.get("daily_budget") or details.get("new_daily_budget") or 0
        )
        projected_monthly = round(daily_budget * 30, 2)

        # Check budget cap headroom
        cap_svc = AdBudgetCapService(self._user_token)
        headroom_data: dict[str, Any] = {}
        if daily_budget > 0:
            headroom_data = await cap_svc.check_budget_headroom(
                user_id=user_id,
                platform=platform,
                proposed_daily_budget=daily_budget,
            )

        platform_name = _PLATFORM_NAMES.get(platform, platform)

        # Build card data for frontend rendering
        card_data: dict[str, Any] = {
            "operation": operation,
            "platform": platform,
            "platform_name": platform_name,
            "campaign_name": campaign_name,
            "current_budget": details.get("current_budget"),
            "new_budget": details.get("new_budget") or details.get("daily_budget"),
            "daily_budget": daily_budget,
            "projected_monthly_impact": projected_monthly,
            "cap_headroom": headroom_data.get("headroom"),
            "monthly_cap": headroom_data.get("monthly_cap"),
            "cap_allowed": headroom_data.get("allowed", True),
            "cap_message": headroom_data.get("message"),
            **{k: v for k, v in details.items()},
        }

        # Build approval payload including user context
        approval_payload: dict[str, Any] = {
            "user_id": user_id,
            "requester_user_id": user_id,
            "operation": operation,
            "platform": platform,
            "campaign_name": campaign_name,
            "card_data": card_data,
            **details,
        }

        action_description = (
            f"{operation.replace('_', ' ').title()} — "
            f"{campaign_name} ({platform_name})"
        )

        message = await request_human_approval(
            action_type="AD_BUDGET_CHANGE",
            action_description=action_description,
            payload=approval_payload,
        )

        # Extract approval_id from the generated approval_requests row
        approval_id = await self._get_latest_approval_id(user_id)

        return {
            "approval_required": True,
            "approval_id": approval_id,
            "message": message,
            "card_data": card_data,
        }

    async def _get_latest_approval_id(self, user_id: str) -> str | None:
        """Retrieve the most recently created AD_BUDGET_CHANGE approval ID.

        Args:
            user_id: The user's UUID.

        Returns:
            The UUID of the most recent pending approval, or ``None``.
        """
        admin = AdminService()
        try:
            result = await execute_async(
                admin.client.table("approval_requests")
                .select("id")
                .eq("user_id", user_id)
                .eq("action_type", "AD_BUDGET_CHANGE")
                .eq("status", "PENDING")
                .order("created_at", desc=True)
                .limit(1),
                op_name="ad_approval.get_latest_id",
            )
            if result.data:
                return result.data[0]["id"]
        except Exception:
            logger.exception(
                "Failed to retrieve latest approval ID for user=%s", user_id
            )
        return None

    # -------------------------------------------------------------------------
    # Approval execution
    # -------------------------------------------------------------------------

    async def execute_approved_operation(self, approval_id: str) -> dict[str, Any]:
        """Execute the ad platform operation after it has been approved.

        Fetches the approval_requests row, validates status is APPROVED,
        parses the payload, calls the appropriate service method, and
        updates the local ad_campaigns record.

        Args:
            approval_id: UUID of the approval_requests row.

        Returns:
            Dict with execution result or error detail.

        Raises:
            ValueError: If approval not found, not APPROVED, or unknown
                platform / operation.
        """
        admin = AdminService()

        # Fetch the approval row
        result = await execute_async(
            admin.client.table("approval_requests")
            .select("*")
            .eq("id", approval_id)
            .single(),
            op_name="ad_approval.fetch_approval",
        )
        if not result.data:
            raise ValueError(f"Approval not found: {approval_id}")

        row = result.data
        status = row.get("status", "")
        if status != "APPROVED":
            raise ValueError(
                f"Cannot execute approval {approval_id} — status is {status!r}, "
                "expected APPROVED."
            )

        payload = row.get("payload") or {}
        operation = payload.get("operation", "")
        platform = payload.get("platform", "")
        user_id = payload.get("user_id") or payload.get("requester_user_id", "")

        if not user_id:
            raise ValueError(f"No user_id in approval payload: {approval_id}")

        logger.info(
            "Executing approved ad operation: %s on %s for user=%s",
            operation,
            platform,
            user_id,
        )

        execution_result = await self._dispatch_operation(
            operation=operation,
            platform=platform,
            user_id=user_id,
            payload=payload,
        )

        # Update the local ad_campaigns record if we have an ad_campaign_id
        ad_campaign_id = payload.get("ad_campaign_id")
        if ad_campaign_id:
            await self._update_local_campaign(
                ad_campaign_id=ad_campaign_id,
                operation=operation,
                payload=payload,
            )

        return {
            "approval_id": approval_id,
            "operation": operation,
            "platform": platform,
            "result": execution_result,
        }

    async def _dispatch_operation(
        self,
        operation: str,
        platform: str,
        user_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Dispatch the approved operation to the correct platform service.

        Args:
            operation: Operation key.
            platform: ``"google_ads"`` or ``"meta_ads"``.
            user_id: The user's UUID.
            payload: Full approval payload.

        Returns:
            Result dict from the platform service call.
        """
        if platform == "google_ads":
            from app.services.google_ads_service import GoogleAdsService

            svc = GoogleAdsService(self._user_token)
            customer_id = payload.get("customer_id", "")

            if operation in ("activate_campaign", "resume_campaign"):
                return await svc.update_campaign_status(
                    user_id=user_id,
                    customer_id=customer_id,
                    campaign_id=payload.get("platform_campaign_id", ""),
                    status="active",
                )
            if operation in ("increase_daily_budget", "decrease_budget"):
                return await svc.update_campaign_budget(
                    user_id=user_id,
                    customer_id=customer_id,
                    campaign_budget_id=payload.get("campaign_budget_id", ""),
                    new_amount=float(
                        payload.get("new_budget") or payload.get("daily_budget") or 0
                    ),
                )

        elif platform == "meta_ads":
            from app.services.meta_ads_service import MetaAdsService

            svc = MetaAdsService(self._user_token)
            campaign_id = payload.get("platform_campaign_id", "")

            if operation in ("activate_campaign", "resume_campaign"):
                return await svc.update_campaign_status(
                    user_id=user_id,
                    campaign_id=campaign_id,
                    status="active",
                )
            if operation in ("increase_daily_budget", "decrease_budget"):
                new_budget_usd = float(
                    payload.get("new_budget") or payload.get("daily_budget") or 0
                )
                return await svc.update_campaign_budget(
                    user_id=user_id,
                    campaign_id=campaign_id,
                    daily_budget=new_budget_usd,
                )

        logger.warning(
            "Unknown operation=%s or platform=%s in _dispatch_operation",
            operation,
            platform,
        )
        return {
            "warning": (
                f"No handler for operation={operation!r} platform={platform!r}"
            )
        }

    async def _update_local_campaign(
        self,
        ad_campaign_id: str,
        operation: str,
        payload: dict[str, Any],
    ) -> None:
        """Update the local ad_campaigns record to reflect the executed change.

        Args:
            ad_campaign_id: UUID of the ad_campaigns row.
            operation: Operation that was executed.
            payload: Full approval payload.
        """
        from app.services.ad_management_service import AdCampaignService

        update_kwargs: dict[str, Any] = {}

        if operation in ("activate_campaign", "resume_campaign"):
            update_kwargs["status"] = "active"
        elif operation == "pause_campaign":
            update_kwargs["status"] = "paused"
        elif operation in ("increase_daily_budget", "decrease_budget"):
            new_budget = payload.get("new_budget") or payload.get("daily_budget")
            if new_budget is not None:
                update_kwargs["daily_budget"] = float(new_budget)

        if not update_kwargs:
            return

        try:
            campaign_svc = AdCampaignService()
            await campaign_svc.update_ad_campaign(
                ad_campaign_id=ad_campaign_id,
                **update_kwargs,
            )
        except Exception:
            logger.exception(
                "Failed to update local campaign %s after approval execution",
                ad_campaign_id,
            )

    # -------------------------------------------------------------------------
    # Combined gate + approval request
    # -------------------------------------------------------------------------

    async def check_and_gate(
        self,
        user_id: str,
        operation: str,
        platform: str,
        campaign_name: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        """Check if an operation needs approval and gate it if so.

        This is the main entry point for ad operation approval flows. It
        handles three outcomes:

        1. **Not gated** — returns ``{"approval_required": False, "execute": True}``
        2. **Budget cap exceeded** — returns blocked response without creating
           an approval request.
        3. **Approval required** — creates an approval card and returns the
           approval link message.

        Args:
            user_id: The user's UUID.
            operation: Operation key.
            platform: ``"google_ads"`` or ``"meta_ads"``.
            campaign_name: Human-readable campaign name.
            details: Operation-specific data (budget amounts, campaign IDs,
                     customer ID, etc.).

        Returns:
            Dict with ``approval_required`` and additional context keys.
        """
        if operation not in GATED_OPERATIONS:
            return {
                "approval_required": False,
                "execute": True,
                "operation": operation,
            }

        # Check budget cap before creating approval request
        daily_budget = float(
            details.get("daily_budget") or details.get("new_budget") or 0
        )
        if daily_budget > 0:
            from app.services.ad_budget_cap_service import AdBudgetCapService

            cap_svc = AdBudgetCapService(self._user_token)
            headroom = await cap_svc.check_budget_headroom(
                user_id=user_id,
                platform=platform,
                proposed_daily_budget=daily_budget,
            )
            if not headroom["allowed"]:
                return {
                    "approval_required": False,
                    "execute": False,
                    "blocked": True,
                    "message": headroom["message"],
                    "monthly_cap": headroom["monthly_cap"],
                    "headroom": headroom["headroom"],
                }

        return await self.request_budget_approval(
            user_id=user_id,
            operation=operation,
            platform=platform,
            campaign_name=campaign_name,
            details=details,
        )


__all__ = ["AdApprovalService", "GATED_OPERATIONS", "NON_GATED_OPERATIONS"]
