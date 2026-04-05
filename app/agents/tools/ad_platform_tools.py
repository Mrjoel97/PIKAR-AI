# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Ad platform agent tools -- Google Ads and Meta Ads with approval gate.

Provides 13 agent-callable functions that bridge the agent to real ad
platform APIs (GoogleAdsService, MetaAdsService) and the approval gate
(AdApprovalService). Budget-altering and campaign-activating operations
are gated; read-only and pause operations execute immediately.

Approval gate logic:
- GATED:     activate_ad_campaign, change_ad_budget (increase only)
- NON-GATED: list campaigns, create campaign (paused), pause campaign,
             get performance, refresh performance, get/set budget cap

All tools use lazy imports and get_current_user_id() from request context.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


# ---------------------------------------------------------------------------
# Tool 1: connect_google_ads_status
# ---------------------------------------------------------------------------


async def connect_google_ads_status() -> dict[str, Any]:
    """Check if Google Ads is connected and return connection details.

    Returns:
        Dict with connected status, customer_id (account_name), and
        any connection error message.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.base_service import AdminService
        from app.services.supabase_async import execute_async

        admin = AdminService()
        result = await execute_async(
            admin.client.table("integration_credentials")
            .select("account_name, expires_at")
            .eq("user_id", user_id)
            .eq("provider", "google_ads")
            .limit(1),
            op_name="ad_tools.google_ads_status",
        )
        if result.data:
            row = result.data[0]
            return {
                "connected": True,
                "customer_id": row.get("account_name", ""),
                "expires_at": row.get("expires_at"),
            }
        return {
            "connected": False,
            "customer_id": None,
            "message": (
                "Google Ads not connected. "
                "Use the Configuration page to connect your account."
            ),
        }
    except Exception as exc:
        logger.exception("connect_google_ads_status failed for user=%s", user_id)
        return {"error": f"Failed to check Google Ads status: {exc}"}


# ---------------------------------------------------------------------------
# Tool 2: connect_meta_ads_status
# ---------------------------------------------------------------------------


async def connect_meta_ads_status() -> dict[str, Any]:
    """Check if Meta Ads is connected and return connection details.

    Returns:
        Dict with connected status, ad_account_id (account_name), and
        any connection error message.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.base_service import AdminService
        from app.services.supabase_async import execute_async

        admin = AdminService()
        result = await execute_async(
            admin.client.table("integration_credentials")
            .select("account_name, expires_at")
            .eq("user_id", user_id)
            .eq("provider", "meta_ads")
            .limit(1),
            op_name="ad_tools.meta_ads_status",
        )
        if result.data:
            row = result.data[0]
            return {
                "connected": True,
                "ad_account_id": row.get("account_name", ""),
                "expires_at": row.get("expires_at"),
            }
        return {
            "connected": False,
            "ad_account_id": None,
            "message": (
                "Meta Ads not connected. "
                "Use the Configuration page to connect your account."
            ),
        }
    except Exception as exc:
        logger.exception("connect_meta_ads_status failed for user=%s", user_id)
        return {"error": f"Failed to check Meta Ads status: {exc}"}


# ---------------------------------------------------------------------------
# Tool 3: list_google_ads_campaigns
# ---------------------------------------------------------------------------


async def list_google_ads_campaigns() -> dict[str, Any]:
    """List all campaigns from the connected Google Ads account.

    NON-GATED — read-only operation.

    Returns:
        Dict with campaigns list or error.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        status = await connect_google_ads_status()
        if not status.get("connected"):
            return {"error": "Google Ads not connected.", "campaigns": []}

        customer_id = status.get("customer_id", "")
        if not customer_id:
            return {
                "error": "No Google Ads customer ID found. "
                "Reconnect your account to set the customer ID.",
                "campaigns": [],
            }

        from app.services.google_ads_service import GoogleAdsService

        svc = GoogleAdsService()
        campaigns = await svc.list_campaigns(
            user_id=user_id, customer_id=customer_id
        )
        return {
            "success": True,
            "platform": "google_ads",
            "customer_id": customer_id,
            "count": len(campaigns),
            "campaigns": campaigns,
        }
    except Exception as exc:
        logger.exception("list_google_ads_campaigns failed for user=%s", user_id)
        return {"error": f"Failed to list Google Ads campaigns: {exc}"}


# ---------------------------------------------------------------------------
# Tool 4: list_meta_ads_campaigns
# ---------------------------------------------------------------------------


async def list_meta_ads_campaigns() -> dict[str, Any]:
    """List all campaigns from the connected Meta Ads account.

    NON-GATED — read-only operation.

    Returns:
        Dict with campaigns list or error.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        status = await connect_meta_ads_status()
        if not status.get("connected"):
            return {"error": "Meta Ads not connected.", "campaigns": []}

        ad_account_id = status.get("ad_account_id", "")
        if not ad_account_id:
            return {
                "error": "No Meta Ads account ID found. "
                "Reconnect your account to set the ad account ID.",
                "campaigns": [],
            }

        from app.services.meta_ads_service import MetaAdsService

        svc = MetaAdsService()
        campaigns = await svc.list_campaigns(
            user_id=user_id, ad_account_id=ad_account_id
        )
        return {
            "success": True,
            "platform": "meta_ads",
            "ad_account_id": ad_account_id,
            "count": len(campaigns),
            "campaigns": campaigns,
        }
    except Exception as exc:
        logger.exception("list_meta_ads_campaigns failed for user=%s", user_id)
        return {"error": f"Failed to list Meta Ads campaigns: {exc}"}


# ---------------------------------------------------------------------------
# Tool 5: create_google_ads_campaign
# ---------------------------------------------------------------------------


async def create_google_ads_campaign(
    name: str,
    daily_budget: float,
    campaign_type: str = "SEARCH",
) -> dict[str, Any]:
    """Create a new Google Ads campaign in PAUSED status.

    Checks budget cap headroom before creating. Campaign is always created
    as PAUSED — activation requires a separate approval gate.
    Also creates a local ad_campaigns record linked to the platform campaign.

    Args:
        name: Campaign name.
        daily_budget: Daily budget in USD.
        campaign_type: Google Ads channel type (default SEARCH).

    Returns:
        Dict with created campaign info, local ad_campaign_id, and note
        about activation requiring approval.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        # Check Google Ads connection
        status = await connect_google_ads_status()
        if not status.get("connected"):
            return {"error": "Google Ads not connected."}

        customer_id = status.get("customer_id", "")
        if not customer_id:
            return {"error": "No Google Ads customer ID found."}

        # Check budget cap headroom
        from app.services.ad_budget_cap_service import AdBudgetCapService

        cap_svc = AdBudgetCapService()
        headroom = await cap_svc.check_budget_headroom(
            user_id=user_id,
            platform="google_ads",
            proposed_daily_budget=daily_budget,
        )
        if not headroom["allowed"]:
            return {
                "success": False,
                "blocked": True,
                "message": headroom["message"],
                "monthly_cap": headroom.get("monthly_cap"),
            }

        # Create on Google Ads (always PAUSED)
        from app.services.google_ads_service import GoogleAdsService

        ads_svc = GoogleAdsService()
        result = await ads_svc.create_campaign(
            user_id=user_id,
            customer_id=customer_id,
            name=name,
            budget_amount=daily_budget,
            campaign_type=campaign_type,
        )
        if "error" in result:
            return result

        platform_campaign_id = result.get("campaign_id", "")

        # Create local record
        from app.services.ad_management_service import AdCampaignService

        campaign_svc = AdCampaignService()
        local_record = await campaign_svc.create_ad_campaign(
            campaign_id=None,
            platform="google_ads",
            name=name,
            ad_type="search",
            daily_budget=daily_budget,
            metadata={
                "platform_campaign_id": platform_campaign_id,
                "customer_id": customer_id,
                "budget_resource_name": result.get("budget_resource_name"),
                "campaign_resource_name": result.get("campaign_resource_name"),
            },
            user_id=user_id,
        )

        # Store platform_campaign_id directly on the local record
        if local_record.get("id"):
            await campaign_svc.update_ad_campaign(
                ad_campaign_id=local_record["id"],
                metadata={
                    "platform_campaign_id": platform_campaign_id,
                    "customer_id": customer_id,
                    "budget_resource_name": result.get("budget_resource_name"),
                    "campaign_resource_name": result.get("campaign_resource_name"),
                },
                user_id=user_id,
            )

        return {
            "success": True,
            "platform": "google_ads",
            "name": name,
            "daily_budget": daily_budget,
            "status": "paused",
            "platform_campaign_id": platform_campaign_id,
            "ad_campaign_id": local_record.get("id"),
            "customer_id": customer_id,
            "note": (
                "Campaign created in PAUSED status. "
                "Use activate_ad_campaign() to start serving ads — "
                "this requires approval since it will begin spending."
            ),
        }
    except Exception as exc:
        logger.exception("create_google_ads_campaign failed for user=%s", user_id)
        return {"error": f"Failed to create Google Ads campaign: {exc}"}


# ---------------------------------------------------------------------------
# Tool 6: create_meta_ads_campaign
# ---------------------------------------------------------------------------


async def create_meta_ads_campaign(
    name: str,
    daily_budget: float,
    objective: str = "OUTCOME_TRAFFIC",
) -> dict[str, Any]:
    """Create a new Meta Ads campaign in PAUSED status.

    Checks budget cap headroom before creating. Campaign is always created
    as PAUSED — activation requires a separate approval gate.
    Also creates a local ad_campaigns record linked to the platform campaign.

    Args:
        name: Campaign name.
        daily_budget: Daily budget in USD.
        objective: Meta campaign objective (default OUTCOME_TRAFFIC).

    Returns:
        Dict with created campaign info, local ad_campaign_id, and note
        about activation requiring approval.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        # Check Meta Ads connection
        status = await connect_meta_ads_status()
        if not status.get("connected"):
            return {"error": "Meta Ads not connected."}

        ad_account_id = status.get("ad_account_id", "")
        if not ad_account_id:
            return {"error": "No Meta Ads account ID found."}

        # Check budget cap headroom
        from app.services.ad_budget_cap_service import AdBudgetCapService

        cap_svc = AdBudgetCapService()
        headroom = await cap_svc.check_budget_headroom(
            user_id=user_id,
            platform="meta_ads",
            proposed_daily_budget=daily_budget,
        )
        if not headroom["allowed"]:
            return {
                "success": False,
                "blocked": True,
                "message": headroom["message"],
                "monthly_cap": headroom.get("monthly_cap"),
            }

        # Create on Meta Ads (always PAUSED); Meta budgets are in cents
        from app.services.meta_ads_service import MetaAdsService

        meta_svc = MetaAdsService()
        daily_budget_cents = int(daily_budget * 100)
        result = await meta_svc.create_campaign(
            user_id=user_id,
            ad_account_id=ad_account_id,
            name=name,
            objective=objective,
            daily_budget=daily_budget_cents,
        )
        if "error" in result:
            return result

        platform_campaign_id = result.get("id", "")

        # Create local record
        from app.services.ad_management_service import AdCampaignService

        campaign_svc = AdCampaignService()
        local_record = await campaign_svc.create_ad_campaign(
            campaign_id=None,
            platform="meta_ads",
            name=name,
            ad_type="feed",
            objective=objective.lower(),
            daily_budget=daily_budget,
            metadata={
                "platform_campaign_id": platform_campaign_id,
                "ad_account_id": ad_account_id,
            },
            user_id=user_id,
        )

        return {
            "success": True,
            "platform": "meta_ads",
            "name": name,
            "daily_budget": daily_budget,
            "objective": objective,
            "status": "paused",
            "platform_campaign_id": platform_campaign_id,
            "ad_campaign_id": local_record.get("id"),
            "ad_account_id": ad_account_id,
            "note": (
                "Campaign created in PAUSED status. "
                "Use activate_ad_campaign() to start serving ads — "
                "this requires approval since it will begin spending."
            ),
        }
    except Exception as exc:
        logger.exception("create_meta_ads_campaign failed for user=%s", user_id)
        return {"error": f"Failed to create Meta Ads campaign: {exc}"}


# ---------------------------------------------------------------------------
# Tool 7: activate_ad_campaign
# ---------------------------------------------------------------------------


async def activate_ad_campaign(
    platform: str,
    campaign_name: str,
    ad_campaign_id: str,
) -> dict[str, Any]:
    """Activate (unpause) an ad campaign — GATED operation.

    This operation starts real ad spending and therefore requires human
    approval. Calls AdApprovalService.check_and_gate() which will create
    an approval card if approval is needed.

    Args:
        platform: 'google_ads' or 'meta_ads'.
        campaign_name: Human-readable campaign name (for the approval card).
        ad_campaign_id: Local ad_campaigns UUID.

    Returns:
        If approval required: Dict with approval_required=True and message.
        If budget cap exceeded: Dict with blocked=True and message.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.ad_management_service import AdCampaignService

        # Fetch local campaign record to get platform IDs
        campaign_svc = AdCampaignService()
        local_campaign = await campaign_svc.get_ad_campaign(
            ad_campaign_id=ad_campaign_id, user_id=user_id
        )
        if not local_campaign:
            return {
                "error": f"Campaign {ad_campaign_id} not found.",
                "ad_campaign_id": ad_campaign_id,
            }

        metadata = local_campaign.get("metadata") or {}
        platform_campaign_id = metadata.get("platform_campaign_id", "")
        customer_id = metadata.get("customer_id", "")  # Google Ads only
        daily_budget = float(local_campaign.get("daily_budget") or 0)

        details: dict[str, Any] = {
            "ad_campaign_id": ad_campaign_id,
            "platform_campaign_id": platform_campaign_id,
            "daily_budget": daily_budget,
        }
        if platform == "google_ads" and customer_id:
            details["customer_id"] = customer_id

        from app.services.ad_approval_service import AdApprovalService

        approval_svc = AdApprovalService()
        result = await approval_svc.check_and_gate(
            user_id=user_id,
            operation="activate_campaign",
            platform=platform,
            campaign_name=campaign_name,
            details=details,
        )
        return result
    except Exception as exc:
        logger.exception("activate_ad_campaign failed for user=%s", user_id)
        return {"error": f"Failed to activate campaign: {exc}"}


# ---------------------------------------------------------------------------
# Tool 8: pause_ad_campaign
# ---------------------------------------------------------------------------


async def pause_ad_campaign(
    platform: str,
    ad_campaign_id: str,
) -> dict[str, Any]:
    """Pause an active ad campaign — NON-GATED immediate operation.

    Stops spending immediately. Updates both platform and local record.

    Args:
        platform: 'google_ads' or 'meta_ads'.
        ad_campaign_id: Local ad_campaigns UUID.

    Returns:
        Dict with success status and updated campaign info.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.ad_management_service import AdCampaignService

        # Get local campaign record
        campaign_svc = AdCampaignService()
        local_campaign = await campaign_svc.get_ad_campaign(
            ad_campaign_id=ad_campaign_id, user_id=user_id
        )
        if not local_campaign:
            return {"error": f"Campaign {ad_campaign_id} not found."}

        metadata = local_campaign.get("metadata") or {}
        platform_campaign_id = metadata.get("platform_campaign_id", "")

        # Execute on platform API
        if platform == "google_ads":
            customer_id = metadata.get("customer_id", "")
            if not customer_id:
                return {"error": "No customer_id found in campaign metadata."}

            from app.services.google_ads_service import GoogleAdsService

            ads_svc = GoogleAdsService()
            api_result = await ads_svc.update_campaign_status(
                user_id=user_id,
                customer_id=customer_id,
                campaign_id=platform_campaign_id,
                status="paused",
            )
        elif platform == "meta_ads":
            from app.services.meta_ads_service import MetaAdsService

            meta_svc = MetaAdsService()
            api_result = await meta_svc.update_campaign_status(
                user_id=user_id,
                campaign_id=platform_campaign_id,
                status="paused",
            )
        else:
            return {"error": f"Unknown platform: {platform!r}"}

        if "error" in api_result:
            return api_result

        # Update local record
        await campaign_svc.update_ad_campaign(
            ad_campaign_id=ad_campaign_id,
            status="paused",
            user_id=user_id,
        )

        return {
            "success": True,
            "platform": platform,
            "ad_campaign_id": ad_campaign_id,
            "status": "paused",
            "message": "Campaign paused successfully. Ad serving has stopped.",
        }
    except Exception as exc:
        logger.exception("pause_ad_campaign failed for user=%s", user_id)
        return {"error": f"Failed to pause campaign: {exc}"}


# ---------------------------------------------------------------------------
# Tool 9: change_ad_budget
# ---------------------------------------------------------------------------


async def change_ad_budget(
    platform: str,
    campaign_name: str,
    ad_campaign_id: str,
    new_daily_budget: float,
) -> dict[str, Any]:
    """Change the daily budget of an ad campaign.

    Budget INCREASES are GATED (require approval).
    Budget DECREASES execute immediately.

    Args:
        platform: 'google_ads' or 'meta_ads'.
        campaign_name: Human-readable campaign name (for approval card).
        ad_campaign_id: Local ad_campaigns UUID.
        new_daily_budget: New daily budget in USD.

    Returns:
        If approval required (increase): approval card data.
        If immediate (decrease): updated budget confirmation.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.ad_management_service import AdCampaignService

        campaign_svc = AdCampaignService()
        local_campaign = await campaign_svc.get_ad_campaign(
            ad_campaign_id=ad_campaign_id, user_id=user_id
        )
        if not local_campaign:
            return {"error": f"Campaign {ad_campaign_id} not found."}

        current_budget = float(local_campaign.get("daily_budget") or 0)
        metadata = local_campaign.get("metadata") or {}
        platform_campaign_id = metadata.get("platform_campaign_id", "")
        is_increase = new_daily_budget > current_budget

        if is_increase:
            # Budget increases are GATED
            details: dict[str, Any] = {
                "ad_campaign_id": ad_campaign_id,
                "platform_campaign_id": platform_campaign_id,
                "current_budget": current_budget,
                "new_budget": new_daily_budget,
                "daily_budget": new_daily_budget,
            }
            if platform == "google_ads":
                details["customer_id"] = metadata.get("customer_id", "")
                details["campaign_budget_id"] = metadata.get("campaign_budget_id", "")

            from app.services.ad_approval_service import AdApprovalService

            approval_svc = AdApprovalService()
            return await approval_svc.check_and_gate(
                user_id=user_id,
                operation="increase_daily_budget",
                platform=platform,
                campaign_name=campaign_name,
                details=details,
            )

        # Budget decrease — execute immediately
        if platform == "google_ads":
            customer_id = metadata.get("customer_id", "")
            campaign_budget_id = metadata.get("campaign_budget_id", "")
            if not customer_id:
                return {"error": "No customer_id found in campaign metadata."}

            from app.services.google_ads_service import GoogleAdsService

            ads_svc = GoogleAdsService()
            api_result = await ads_svc.update_campaign_budget(
                user_id=user_id,
                customer_id=customer_id,
                campaign_budget_id=campaign_budget_id,
                new_amount=new_daily_budget,
            )
        elif platform == "meta_ads":
            from app.services.meta_ads_service import MetaAdsService

            meta_svc = MetaAdsService()
            api_result = await meta_svc.update_campaign_budget(
                user_id=user_id,
                campaign_id=platform_campaign_id,
                daily_budget=int(new_daily_budget * 100),
            )
        else:
            return {"error": f"Unknown platform: {platform!r}"}

        if "error" in api_result:
            return api_result

        # Update local record
        await campaign_svc.update_ad_campaign(
            ad_campaign_id=ad_campaign_id,
            daily_budget=new_daily_budget,
            user_id=user_id,
        )

        return {
            "success": True,
            "platform": platform,
            "ad_campaign_id": ad_campaign_id,
            "previous_daily_budget": current_budget,
            "new_daily_budget": new_daily_budget,
            "message": (
                f"Daily budget reduced from ${current_budget:.2f} to "
                f"${new_daily_budget:.2f} immediately."
            ),
        }
    except Exception as exc:
        logger.exception("change_ad_budget failed for user=%s", user_id)
        return {"error": f"Failed to change campaign budget: {exc}"}


# ---------------------------------------------------------------------------
# Tool 10: get_ad_campaign_performance
# ---------------------------------------------------------------------------


async def get_ad_campaign_performance(
    platform: str,
    ad_campaign_id: str,
    days: int = 7,
) -> dict[str, Any]:
    """Get performance metrics for an ad campaign from local tracking data.

    NON-GATED — read-only. Queries ad_spend_tracking for the last N days.

    Args:
        platform: 'google_ads' or 'meta_ads'.
        ad_campaign_id: Local ad_campaigns UUID.
        days: Number of days to look back (default 7).

    Returns:
        Dict with spend summary including ROAS, CPC, CTR, and daily breakdown.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from datetime import date, timedelta

        from app.services.ad_management_service import AdSpendTrackingService

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        spend_svc = AdSpendTrackingService()
        summary = await spend_svc.get_spend_summary(
            ad_campaign_id=ad_campaign_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            user_id=user_id,
        )
        return {
            "success": True,
            "platform": platform,
            "ad_campaign_id": ad_campaign_id,
            "days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            **summary,
        }
    except Exception as exc:
        logger.exception("get_ad_campaign_performance failed for user=%s", user_id)
        return {"error": f"Failed to get campaign performance: {exc}"}


# ---------------------------------------------------------------------------
# Tool 11: refresh_ad_performance
# ---------------------------------------------------------------------------


async def refresh_ad_performance(platform: str) -> dict[str, Any]:
    """Trigger an on-demand performance sync for the specified platform.

    Pulls the latest spend data from the platform API and updates
    ad_spend_tracking. Use before checking performance to get fresh data.

    NON-GATED — does not change spend, only reads and stores data.

    Args:
        platform: 'google_ads' or 'meta_ads'.

    Returns:
        Dict with sync result (records_synced count).
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.ad_performance_sync_service import AdPerformanceSyncService

        sync_svc = AdPerformanceSyncService()
        result = await sync_svc.sync_user_on_demand(
            user_id=user_id, platform=platform
        )
        return {
            "success": True,
            "platform": platform,
            **result,
            "message": (
                f"Synced {result.get('records_synced', 0)} performance records "
                f"from {platform.replace('_', ' ').title()}."
            ),
        }
    except Exception as exc:
        logger.exception("refresh_ad_performance failed for user=%s", user_id)
        return {"error": f"Failed to refresh ad performance: {exc}"}


# ---------------------------------------------------------------------------
# Tool 12: get_ad_budget_cap
# ---------------------------------------------------------------------------


async def get_ad_budget_cap(platform: str) -> dict[str, Any]:
    """Get the current monthly budget cap for a platform.

    NON-GATED — read-only.

    Args:
        platform: 'google_ads' or 'meta_ads'.

    Returns:
        Dict with monthly_cap (USD) or None if not set.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.ad_budget_cap_service import AdBudgetCapService

        cap_svc = AdBudgetCapService()
        cap = await cap_svc.get_cap(user_id=user_id, platform=platform)
        if cap is None:
            return {
                "platform": platform,
                "monthly_cap": None,
                "message": (
                    f"No monthly budget cap set for {platform}. "
                    "Use set_ad_budget_cap() to configure one."
                ),
            }
        return {
            "success": True,
            "platform": platform,
            "monthly_cap": cap,
            "message": f"Monthly cap for {platform}: ${cap:.2f}",
        }
    except Exception as exc:
        logger.exception("get_ad_budget_cap failed for user=%s", user_id)
        return {"error": f"Failed to get budget cap: {exc}"}


# ---------------------------------------------------------------------------
# Tool 13: set_ad_budget_cap
# ---------------------------------------------------------------------------


async def set_ad_budget_cap(platform: str, monthly_cap: float) -> dict[str, Any]:
    """Set or update the monthly budget cap for a platform.

    This cap acts as a safety ceiling. No ad spend operations can exceed
    this amount per calendar month. Setting a cap is required before
    connecting an ad platform.

    NON-GATED — configuring the cap itself is a safety action.

    Args:
        platform: 'google_ads' or 'meta_ads'.
        monthly_cap: Monthly spending ceiling in USD.

    Returns:
        Dict with updated cap record.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    if monthly_cap <= 0:
        return {"error": "Monthly cap must be a positive number."}

    try:
        from app.services.ad_budget_cap_service import AdBudgetCapService

        cap_svc = AdBudgetCapService()
        result = await cap_svc.set_cap(
            user_id=user_id, platform=platform, monthly_cap=monthly_cap
        )
        return {
            "success": True,
            "platform": platform,
            "monthly_cap": monthly_cap,
            "message": (
                f"Monthly budget cap for {platform} set to ${monthly_cap:.2f}. "
                "This cap will be enforced for all future ad spend operations."
            ),
            **result,
        }
    except Exception as exc:
        logger.exception("set_ad_budget_cap failed for user=%s", user_id)
        return {"error": f"Failed to set budget cap: {exc}"}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

AD_PLATFORM_TOOLS = [
    connect_google_ads_status,
    connect_meta_ads_status,
    list_google_ads_campaigns,
    list_meta_ads_campaigns,
    create_google_ads_campaign,
    create_meta_ads_campaign,
    activate_ad_campaign,
    pause_ad_campaign,
    change_ad_budget,
    get_ad_campaign_performance,
    refresh_ad_performance,
    get_ad_budget_cap,
    set_ad_budget_cap,
]
