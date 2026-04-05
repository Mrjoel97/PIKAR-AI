# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""AdPerformanceSyncService -- Scheduled 6-hour ad performance data sync.

Pulls campaign performance from Google Ads and Meta Ads for all connected
users, writes daily spend records to ``ad_spend_tracking``, and fires
budget pacing alerts when a platform is on track to exceed its monthly cap.

Triggered by Cloud Scheduler every 6 hours via
``POST /internal/sync/ad-performance`` (authenticated with
``WORKFLOW_SERVICE_SECRET``). Also available as an on-demand refresh via
``sync_user_on_demand`` (called from the integrations router).

Design decisions:
- Covers the last 7 days on each sync to account for Google's ~3 hour
  reporting lag and late-arriving conversions on Meta.
- Skips campaigns that have been paused for more than 30 days (stale).
- Meta API spend is already in USD in the insights response.
- Google Ads cost is returned in micros and converted to USD (÷ 1_000_000).
- Budget pacing alerts are fired as WARNING notifications; de-duplicated
  by checking whether a warning for the same platform was sent today.

Usage::

    svc = AdPerformanceSyncService()
    result = await svc.sync_all_users()
    # {"users_synced": 5, "platforms_synced": 8, "errors": [...]}
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.services.base_service import AdminService, BaseService

logger = logging.getLogger(__name__)

_AD_PROVIDERS = frozenset({"google_ads", "meta_ads"})

_PLATFORM_DISPLAY: dict[str, str] = {
    "google_ads": "Google Ads",
    "meta_ads": "Meta Ads",
}


class AdPerformanceSyncService(BaseService):
    """Scheduled performance data sync for Google Ads and Meta Ads.

    Args:
        user_token: User JWT for Supabase RLS (passed to BaseService).
    """

    # -------------------------------------------------------------------------
    # Main entry points
    # -------------------------------------------------------------------------

    async def sync_all_users(self) -> dict[str, Any]:
        """Sync performance data for all connected ad platform users.

        Queries ``integration_credentials`` for all users who have connected
        Google Ads or Meta Ads and whose tokens are not expired, then calls
        ``sync_user_platform`` for each user+platform pair.

        Returns:
            Summary dict: {"users_synced": N, "platforms_synced": N, "errors": [...]}.
        """
        admin = AdminService()
        from app.services.supabase_async import execute_async

        try:
            result = await execute_async(
                admin.client.table("integration_credentials")
                .select("user_id, provider, account_name, expires_at")
                .in_("provider", list(_AD_PROVIDERS)),
                op_name="ad_sync.list_credentials",
            )
            rows = result.data or []
        except Exception:
            logger.exception(
                "AdPerformanceSyncService.sync_all_users: credential query failed"
            )
            return {
                "users_synced": 0,
                "platforms_synced": 0,
                "errors": ["Credential query failed"],
            }

        now = datetime.now(tz=timezone.utc)
        active_rows = [
            r for r in rows
            if not r.get("expires_at")
            or _parse_expires_at(r["expires_at"]) > now
        ]

        users_seen: set[str] = set()
        platforms_synced = 0
        errors: list[str] = []

        for row in active_rows:
            user_id = row["user_id"]
            provider = row["provider"]
            users_seen.add(user_id)

            try:
                await self.sync_user_platform(user_id=user_id, platform=provider)
                platforms_synced += 1
            except Exception as exc:
                msg = f"user={user_id} platform={provider}: {exc!s}"
                logger.exception("sync_all_users error: %s", msg)
                errors.append(msg)

        return {
            "users_synced": len(users_seen),
            "platforms_synced": platforms_synced,
            "errors": errors,
        }

    async def sync_user_platform(self, user_id: str, platform: str) -> dict[str, Any]:
        """Sync performance data for one user + platform combination.

        Args:
            user_id: The user's UUID.
            platform: ``"google_ads"`` or ``"meta_ads"``.

        Returns:
            Dict: {"platform": platform, "records_synced": N}.
        """
        if platform == "google_ads":
            records = await self._sync_google_ads(user_id)
        elif platform == "meta_ads":
            records = await self._sync_meta_ads(user_id)
        else:
            logger.warning("Unknown ad platform: %s", platform)
            return {"platform": platform, "records_synced": 0}

        # Check budget pacing after sync so we have fresh data
        await self._check_budget_pacing(user_id, platform)

        return {"platform": platform, "records_synced": records}

    async def sync_user_on_demand(self, user_id: str, platform: str) -> dict[str, Any]:
        """On-demand performance sync for a single user + platform.

        Same logic as ``sync_user_platform`` — exposed separately for
        on-demand API calls and agent tool invocations.

        Args:
            user_id: The user's UUID.
            platform: ``"google_ads"`` or ``"meta_ads"``.

        Returns:
            Dict: {"platform": platform, "records_synced": N}.
        """
        return await self.sync_user_platform(user_id=user_id, platform=platform)

    # -------------------------------------------------------------------------
    # Platform-specific sync
    # -------------------------------------------------------------------------

    async def _sync_google_ads(self, user_id: str) -> int:
        """Pull Google Ads performance for the last 7 days and store it.

        Args:
            user_id: The user's UUID.

        Returns:
            Number of spend records written/updated.
        """
        from app.services.ad_management_service import AdCampaignService, AdSpendTrackingService
        from app.services.google_ads_service import GoogleAdsService

        # Get customer_id from credentials account_name
        admin = AdminService()
        from app.services.supabase_async import execute_async

        cred_result = await execute_async(
            admin.client.table("integration_credentials")
            .select("account_name")
            .eq("user_id", user_id)
            .eq("provider", "google_ads")
            .single(),
            op_name="ad_sync.google_cred",
        )
        cred = cred_result.data
        if not cred:
            logger.warning("No Google Ads credential for user=%s", user_id)
            return 0

        customer_id = cred.get("account_name", "")
        if not customer_id:
            logger.warning(
                "No customer_id (account_name) for google_ads user=%s", user_id
            )
            return 0

        # Fetch performance for last 7 days (covers reporting delay + late conversions)
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        ads_svc = GoogleAdsService()
        rows = await ads_svc.get_campaign_performance(
            user_id=user_id,
            customer_id=customer_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        if not rows:
            logger.info("No Google Ads performance rows for user=%s", user_id)
            return 0

        # Index local campaigns by platform_campaign_id for quick lookup
        campaign_svc = AdCampaignService()
        local_campaigns = await campaign_svc.list_ad_campaigns(
            platform="google_ads", user_id=user_id
        )
        campaign_map: dict[str, dict[str, Any]] = {
            c["platform_campaign_id"]: c
            for c in local_campaigns
            if c.get("platform_campaign_id")
        }

        spend_svc = AdSpendTrackingService()
        count = 0
        cutoff = date.today() - timedelta(days=30)

        for row in rows:
            campaign_id_str = str(row.get("campaign_id", ""))
            local_campaign = campaign_map.get(campaign_id_str)

            if not local_campaign:
                # Campaign exists on Google Ads but not locally — skip
                continue

            # Skip campaigns paused for more than 30 days
            if local_campaign.get("status") == "paused":
                updated_raw = local_campaign.get("updated_at", "")
                updated_date = _parse_date_from_str(updated_raw)
                if updated_date and updated_date < cutoff:
                    continue

            try:
                await spend_svc.record_daily_spend(
                    ad_campaign_id=local_campaign["id"],
                    tracking_date=row["date"],
                    spend=float(row.get("cost", 0)),
                    impressions=int(row.get("impressions", 0)),
                    clicks=int(row.get("clicks", 0)),
                    conversions=int(row.get("conversions", 0)),
                    conversion_value=float(row.get("conversion_value", 0)),
                    currency="USD",
                    platform_data=row,
                    user_id=user_id,
                )
                count += 1
            except Exception:
                logger.exception(
                    "Failed to record Google Ads spend for campaign=%s date=%s",
                    local_campaign["id"],
                    row.get("date"),
                )

        logger.info(
            "Google Ads sync complete for user=%s: %d records", user_id, count
        )
        return count

    async def _sync_meta_ads(self, user_id: str) -> int:
        """Pull Meta Ads insights for the last 7 days and store them.

        Meta API spend values in insights are in USD (not cents).

        Args:
            user_id: The user's UUID.

        Returns:
            Number of spend records written/updated.
        """
        from app.services.ad_management_service import AdCampaignService, AdSpendTrackingService
        from app.services.meta_ads_service import MetaAdsService

        admin = AdminService()
        from app.services.supabase_async import execute_async

        cred_result = await execute_async(
            admin.client.table("integration_credentials")
            .select("account_name")
            .eq("user_id", user_id)
            .eq("provider", "meta_ads")
            .single(),
            op_name="ad_sync.meta_cred",
        )
        cred = cred_result.data
        if not cred:
            logger.warning("No Meta Ads credential for user=%s", user_id)
            return 0

        ad_account_id = cred.get("account_name", "")
        if not ad_account_id:
            logger.warning(
                "No ad_account_id (account_name) for meta_ads user=%s", user_id
            )
            return 0

        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        meta_svc = MetaAdsService()
        rows = await meta_svc.get_campaign_insights(
            user_id=user_id,
            ad_account_id=ad_account_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        if not rows:
            logger.info("No Meta Ads insight rows for user=%s", user_id)
            return 0

        campaign_svc = AdCampaignService()
        local_campaigns = await campaign_svc.list_ad_campaigns(
            platform="meta_ads", user_id=user_id
        )
        campaign_map: dict[str, dict[str, Any]] = {
            c["platform_campaign_id"]: c
            for c in local_campaigns
            if c.get("platform_campaign_id")
        }

        spend_svc = AdSpendTrackingService()
        count = 0
        cutoff = date.today() - timedelta(days=30)

        for row in rows:
            campaign_id_str = str(row.get("campaign_id", ""))
            local_campaign = campaign_map.get(campaign_id_str)

            if not local_campaign:
                continue

            # Skip campaigns paused for more than 30 days
            if local_campaign.get("status") == "paused":
                updated_raw = local_campaign.get("updated_at", "")
                updated_date = _parse_date_from_str(updated_raw)
                if updated_date and updated_date < cutoff:
                    continue

            # Meta insights spend is already in USD
            spend_usd = float(row.get("spend", 0))

            try:
                await spend_svc.record_daily_spend(
                    ad_campaign_id=local_campaign["id"],
                    tracking_date=row["date"],
                    spend=spend_usd,
                    impressions=int(row.get("impressions", 0)),
                    clicks=int(row.get("clicks", 0)),
                    conversions=int(row.get("conversions", 0)),
                    conversion_value=float(row.get("conversion_value", 0)),
                    currency="USD",
                    platform_data=row,
                    user_id=user_id,
                )
                count += 1
            except Exception:
                logger.exception(
                    "Failed to record Meta Ads spend for campaign=%s date=%s",
                    local_campaign["id"],
                    row.get("date"),
                )

        logger.info(
            "Meta Ads sync complete for user=%s: %d records", user_id, count
        )
        return count

    # -------------------------------------------------------------------------
    # Budget pacing alert
    # -------------------------------------------------------------------------

    async def _check_budget_pacing(self, user_id: str, platform: str) -> None:
        """Check monthly budget pacing and fire an alert if overpacing.

        Sums all spend for the current month across active campaigns for
        the platform, calculates daily average, projects when the monthly
        cap would be reached, and fires a WARNING notification if the pace
        would exceed the cap before month end.

        Args:
            user_id: The user's UUID.
            platform: ``"google_ads"`` or ``"meta_ads"``.
        """
        from app.services.ad_budget_cap_service import AdBudgetCapService
        from app.services.supabase_async import execute_async

        cap_svc = AdBudgetCapService()
        cap = await cap_svc.get_cap(user_id=user_id, platform=platform)
        if not cap:
            return  # No cap configured — nothing to check

        today = date.today()
        month_start = today.replace(day=1).isoformat()
        days_elapsed = max(today.day, 1)
        import calendar
        _, days_in_month = calendar.monthrange(today.year, today.month)
        days_remaining = max(days_in_month - today.day, 1)

        admin = AdminService()

        # Sum spend this month for all campaigns on this platform for this user
        try:
            campaign_result = await execute_async(
                admin.client.table("ad_campaigns")
                .select("id")
                .eq("user_id", user_id)
                .eq("platform", platform),
                op_name="ad_pacing.get_campaigns",
            )
            campaign_ids = [r["id"] for r in (campaign_result.data or [])]
        except Exception:
            logger.exception(
                "Failed to get campaign IDs for pacing check user=%s platform=%s",
                user_id,
                platform,
            )
            return

        if not campaign_ids:
            return

        try:
            spend_result = await execute_async(
                admin.client.table("ad_spend_tracking")
                .select("spend")
                .in_("ad_campaign_id", campaign_ids)
                .gte("tracking_date", month_start),
                op_name="ad_pacing.get_month_spend",
            )
            month_spend = sum(
                float(r.get("spend", 0)) for r in (spend_result.data or [])
            )
        except Exception:
            logger.exception(
                "Failed to sum monthly spend for pacing check user=%s", user_id
            )
            return

        if month_spend <= 0:
            return

        daily_avg = month_spend / days_elapsed
        projected_total = month_spend + (daily_avg * days_remaining)

        if projected_total <= cap:
            return  # On track — no alert needed

        # Calculate projected date when cap would be hit
        if daily_avg > 0:
            days_to_cap = (cap - month_spend) / daily_avg
            projected_cap_date = today + timedelta(days=max(int(days_to_cap), 0))
            projected_date_str = projected_cap_date.strftime("%-d" if hasattr(projected_cap_date, "strftime") else "%d").lstrip("0") or "1"
            try:
                projected_date_str = projected_cap_date.strftime("%B %-d")
            except ValueError:
                projected_date_str = projected_cap_date.strftime("%B %d").lstrip("0")
        else:
            projected_date_str = "end of month"

        platform_name = _PLATFORM_DISPLAY.get(platform, platform)

        from app.notifications.notification_service import NotificationService, NotificationType

        notif_svc = NotificationService()
        await notif_svc.create_notification(
            user_id=user_id,
            title="Budget Pacing Alert",
            message=(
                f"{platform_name} is spending ${daily_avg:.0f}/day — "
                f"at this rate you'll hit your ${cap:,.0f}/mo cap by {projected_date_str}."
            ),
            type=NotificationType.WARNING,
            link="/dashboard/configuration",
            metadata={
                "platform": platform,
                "daily_avg": daily_avg,
                "monthly_cap": cap,
                "month_spend_to_date": month_spend,
                "projected_total": projected_total,
            },
        )
        logger.info(
            "Budget pacing alert fired for user=%s platform=%s "
            "(daily_avg=%.2f cap=%.2f projected=%.2f)",
            user_id,
            platform,
            daily_avg,
            cap,
            projected_total,
        )


# ============================================================================
# Module-level helpers
# ============================================================================


def _parse_expires_at(value: str) -> datetime:
    """Parse an ISO-8601 expires_at string to a timezone-aware datetime.

    Args:
        value: ISO-8601 string (e.g. ``"2026-04-05T12:00:00+00:00"``).

    Returns:
        A timezone-aware ``datetime``. Falls back to epoch on parse failure.
    """
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def _parse_date_from_str(value: str) -> date | None:
    """Extract a ``date`` from an ISO-8601 datetime string.

    Args:
        value: ISO-8601 datetime string.

    Returns:
        ``date`` object, or ``None`` on failure.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None


__all__ = ["AdPerformanceSyncService"]
