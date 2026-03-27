# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""AdManagementService - CRUD for ad campaigns, creatives, and spend tracking.

Manages platform-specific ad campaigns (Google Ads, Meta Ads), creative assets,
daily spend tracking, and ROAS calculations.
Used by MarketingAutomationAgent for paid media management.
"""

from app.services.base_service import AdminService, BaseService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async


class AdCampaignService(BaseService):
    """Service for managing platform-specific ad campaigns.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: str | None = None):
        super().__init__(user_token)

    async def create_ad_campaign(
        self,
        campaign_id: str,
        platform: str,
        name: str,
        ad_type: str = "search",
        objective: str = "conversions",
        targeting: dict = None,
        bid_strategy: str = "manual_cpc",
        bid_amount: float = None,
        daily_budget: float = None,
        total_budget: float = None,
        currency: str = "USD",
        start_date: str = None,
        end_date: str = None,
        metadata: dict = None,
        user_id: str | None = None,
    ) -> dict:
        """Create a platform-specific ad campaign linked to a marketing campaign.

        Args:
            campaign_id: Parent marketing campaign ID.
            platform: Ad platform (google_ads, meta_ads).
            name: Ad campaign name.
            ad_type: Ad type (search, display, video, shopping, performance_max,
                     feed, stories, reels, carousel, collection).
            objective: Campaign objective (awareness, traffic, engagement, leads,
                       conversions, sales).
            targeting: Targeting config {locations[], age_min, age_max, genders[],
                       interests[], keywords[], audiences[], placements[]}.
            bid_strategy: Bidding strategy (manual_cpc, maximize_clicks,
                          target_cpa, target_roas, etc.).
            bid_amount: Bid amount (CPC/CPA/ROAS target).
            daily_budget: Daily spend cap.
            total_budget: Total lifetime budget.
            currency: Currency code (default USD).
            start_date: Campaign start date (YYYY-MM-DD).
            end_date: Campaign end date (YYYY-MM-DD).
            metadata: Additional metadata.
            user_id: Optional user ID override.

        Returns:
            The created ad campaign record.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for ad campaign creation")

        data = {
            "user_id": effective_user_id,
            "campaign_id": campaign_id,
            "platform": platform,
            "name": name,
            "ad_type": ad_type,
            "objective": objective,
            "targeting": targeting or {},
            "bid_strategy": bid_strategy,
            "bid_amount": bid_amount,
            "daily_budget": daily_budget,
            "total_budget": total_budget,
            "currency": currency,
            "start_date": start_date,
            "end_date": end_date,
            "metadata": metadata or {},
            "status": "draft",
        }
        data = {k: v for k, v in data.items() if v is not None}

        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table("ad_campaigns").insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert")

    async def get_ad_campaign(
        self, ad_campaign_id: str, user_id: str | None = None
    ) -> dict:
        """Retrieve an ad campaign by ID."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("ad_campaigns").select("*").eq("id", ad_campaign_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_ad_campaign(
        self,
        ad_campaign_id: str,
        name: str | None = None,
        status: str | None = None,
        targeting: dict | None = None,
        bid_strategy: str | None = None,
        bid_amount: float | None = None,
        daily_budget: float | None = None,
        total_budget: float | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        metadata: dict | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Update an ad campaign."""
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if status is not None:
            update_data["status"] = status
        if targeting is not None:
            update_data["targeting"] = targeting
        if bid_strategy is not None:
            update_data["bid_strategy"] = bid_strategy
        if bid_amount is not None:
            update_data["bid_amount"] = bid_amount
        if daily_budget is not None:
            update_data["daily_budget"] = daily_budget
        if total_budget is not None:
            update_data["total_budget"] = total_budget
        if start_date is not None:
            update_data["start_date"] = start_date
        if end_date is not None:
            update_data["end_date"] = end_date
        if metadata is not None:
            update_data["metadata"] = metadata

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table("ad_campaigns").update(update_data).eq("id", ad_campaign_id)
        )
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update")

    async def list_ad_campaigns(
        self,
        campaign_id: str | None = None,
        platform: str | None = None,
        status: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list:
        """List ad campaigns with optional filters."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("ad_campaigns").select("*")

        if campaign_id:
            query = query.eq("campaign_id", campaign_id)
        if platform:
            query = query.eq("platform", platform)
        if status:
            query = query.eq("status", status)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(
            query.order("created_at", desc=True).limit(limit)
        )
        return response.data

    async def delete_ad_campaign(
        self, ad_campaign_id: str, user_id: str | None = None
    ) -> bool:
        """Delete an ad campaign."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("ad_campaigns").delete().eq("id", ad_campaign_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        return len(response.data) > 0


class AdCreativeService(BaseService):
    """Service for managing ad creative assets.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: str | None = None):
        super().__init__(user_token)

    async def create_creative(
        self,
        ad_campaign_id: str,
        name: str,
        creative_type: str = "image",
        headline: str = None,
        description: str = None,
        call_to_action: str = None,
        primary_text: str = None,
        destination_url: str = None,
        display_url: str = None,
        media_urls: list[str] = None,
        thumbnail_url: str = None,
        specs: dict = None,
        ab_variant: str = None,
        user_id: str | None = None,
    ) -> dict:
        """Create an ad creative linked to an ad campaign.

        Args:
            ad_campaign_id: Parent ad campaign ID.
            name: Creative name.
            creative_type: Type (image, video, carousel, responsive, html5, text_only).
            headline: Ad headline.
            description: Ad description.
            call_to_action: CTA text (Learn More, Shop Now, Sign Up, etc.).
            primary_text: Main ad copy.
            destination_url: Landing page URL.
            display_url: Displayed URL in ad.
            media_urls: List of media asset URLs.
            thumbnail_url: Thumbnail image URL.
            specs: Creative specs {width, height, aspect_ratio, file_format, duration_seconds}.
            ab_variant: A/B variant label (A, B, C).
            user_id: Optional user ID override.

        Returns:
            The created creative record.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for creative creation")

        data = {
            "user_id": effective_user_id,
            "ad_campaign_id": ad_campaign_id,
            "name": name,
            "creative_type": creative_type,
            "headline": headline,
            "description": description,
            "call_to_action": call_to_action,
            "primary_text": primary_text,
            "destination_url": destination_url,
            "display_url": display_url,
            "media_urls": media_urls or [],
            "thumbnail_url": thumbnail_url,
            "specs": specs or {},
            "ab_variant": ab_variant,
            "status": "draft",
        }
        data = {k: v for k, v in data.items() if v is not None}

        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table("ad_creatives").insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert")

    async def get_creative(self, creative_id: str, user_id: str | None = None) -> dict:
        """Retrieve a creative by ID."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("ad_creatives").select("*").eq("id", creative_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_creative(
        self,
        creative_id: str,
        name: str | None = None,
        headline: str | None = None,
        description: str | None = None,
        call_to_action: str | None = None,
        primary_text: str | None = None,
        destination_url: str | None = None,
        media_urls: list[str] | None = None,
        status: str | None = None,
        performance: dict | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Update a creative."""
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if headline is not None:
            update_data["headline"] = headline
        if description is not None:
            update_data["description"] = description
        if call_to_action is not None:
            update_data["call_to_action"] = call_to_action
        if primary_text is not None:
            update_data["primary_text"] = primary_text
        if destination_url is not None:
            update_data["destination_url"] = destination_url
        if media_urls is not None:
            update_data["media_urls"] = media_urls
        if status is not None:
            update_data["status"] = status
        if performance is not None:
            update_data["performance"] = performance

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("ad_creatives").update(update_data).eq("id", creative_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update")

    async def list_creatives(
        self,
        ad_campaign_id: str | None = None,
        creative_type: str | None = None,
        status: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
    ) -> list:
        """List creatives with optional filters."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("ad_creatives").select("*")

        if ad_campaign_id:
            query = query.eq("ad_campaign_id", ad_campaign_id)
        if creative_type:
            query = query.eq("creative_type", creative_type)
        if status:
            query = query.eq("status", status)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(
            query.order("created_at", desc=True).limit(limit)
        )
        return response.data

    async def delete_creative(
        self, creative_id: str, user_id: str | None = None
    ) -> bool:
        """Delete a creative."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table("ad_creatives").delete().eq("id", creative_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        return len(response.data) > 0


class AdSpendTrackingService(BaseService):
    """Service for tracking ad spend and calculating ROAS.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: str | None = None):
        super().__init__(user_token)

    async def record_daily_spend(
        self,
        ad_campaign_id: str,
        tracking_date: str,
        spend: float,
        impressions: int = 0,
        clicks: int = 0,
        conversions: int = 0,
        conversion_value: float = 0,
        currency: str = "USD",
        platform_data: dict = None,
        user_id: str | None = None,
    ) -> dict:
        """Record or update daily spend and metrics for an ad campaign.

        Upserts on (ad_campaign_id, tracking_date) — updates if exists.

        Args:
            ad_campaign_id: The ad campaign ID.
            tracking_date: Date (YYYY-MM-DD).
            spend: Amount spent.
            impressions: Number of impressions.
            clicks: Number of clicks.
            conversions: Number of conversions.
            conversion_value: Revenue attributed to conversions.
            currency: Currency code.
            platform_data: Raw metrics from platform API.
            user_id: Optional user ID override.

        Returns:
            The spend tracking record.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for spend tracking")

        # Calculate derived metrics
        ctr = round(clicks / impressions, 4) if impressions > 0 else 0
        cpc = round(spend / clicks, 2) if clicks > 0 else 0
        cpa = round(spend / conversions, 2) if conversions > 0 else 0
        roas = round(conversion_value / spend, 2) if spend > 0 else 0

        data = {
            "user_id": effective_user_id,
            "ad_campaign_id": ad_campaign_id,
            "tracking_date": tracking_date,
            "spend": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "conversion_value": conversion_value,
            "ctr": ctr,
            "cpc": cpc,
            "cpa": cpa,
            "roas": roas,
            "currency": currency,
            "platform_data": platform_data or {},
        }

        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(
            client.table("ad_spend_tracking").upsert(
                data, on_conflict="ad_campaign_id,tracking_date"
            )
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from upsert")

    async def get_spend_summary(
        self,
        ad_campaign_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Get aggregated spend summary for an ad campaign.

        Args:
            ad_campaign_id: The ad campaign ID.
            start_date: Start date filter (YYYY-MM-DD).
            end_date: End date filter (YYYY-MM-DD).
            user_id: Optional user ID override.

        Returns:
            Dict with total_spend, total_impressions, total_clicks,
            total_conversions, total_conversion_value, avg_ctr, avg_cpc,
            avg_cpa, overall_roas, and daily_breakdown.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table("ad_spend_tracking")
            .select("*")
            .eq("ad_campaign_id", ad_campaign_id)
        )
        if start_date:
            query = query.gte("tracking_date", start_date)
        if end_date:
            query = query.lte("tracking_date", end_date)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(query.order("tracking_date", desc=False))
        rows = response.data

        if not rows:
            return {
                "total_spend": 0,
                "total_impressions": 0,
                "total_clicks": 0,
                "total_conversions": 0,
                "total_conversion_value": 0,
                "avg_ctr": 0,
                "avg_cpc": 0,
                "avg_cpa": 0,
                "overall_roas": 0,
                "days_tracked": 0,
                "daily_breakdown": [],
            }

        total_spend = sum(float(r.get("spend", 0)) for r in rows)
        total_impressions = sum(r.get("impressions", 0) for r in rows)
        total_clicks = sum(r.get("clicks", 0) for r in rows)
        total_conversions = sum(r.get("conversions", 0) for r in rows)
        total_cv = sum(float(r.get("conversion_value", 0)) for r in rows)

        return {
            "total_spend": round(total_spend, 2),
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "total_conversion_value": round(total_cv, 2),
            "avg_ctr": round(total_clicks / total_impressions, 4)
            if total_impressions > 0
            else 0,
            "avg_cpc": round(total_spend / total_clicks, 2) if total_clicks > 0 else 0,
            "avg_cpa": round(total_spend / total_conversions, 2)
            if total_conversions > 0
            else 0,
            "overall_roas": round(total_cv / total_spend, 2) if total_spend > 0 else 0,
            "days_tracked": len(rows),
            "daily_breakdown": rows,
        }

    async def get_budget_pacing(
        self,
        ad_campaign_id: str,
        user_id: str | None = None,
    ) -> dict:
        """Calculate budget pacing for an ad campaign.

        Compares total spend to date against the campaign's total budget
        and daily budget to determine if spending is on-track, underpacing,
        or overpacing.

        Args:
            ad_campaign_id: The ad campaign ID.
            user_id: Optional user ID override.

        Returns:
            Dict with pacing status, spend_to_date, budget_remaining,
            daily_average_spend, projected_total_spend, and recommendation.
        """
        from datetime import date

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client

        # Get the ad campaign details
        camp_query = (
            client.table("ad_campaigns")
            .select("daily_budget, total_budget, start_date, end_date, status")
            .eq("id", ad_campaign_id)
        )
        if not self.is_authenticated and effective_user_id:
            camp_query = camp_query.eq("user_id", effective_user_id)
        camp_resp = await execute_async(camp_query.single())
        campaign = camp_resp.data

        # Get spend summary
        summary = await self.get_spend_summary(
            ad_campaign_id, user_id=effective_user_id
        )

        total_budget = float(campaign.get("total_budget") or 0)
        daily_budget = float(campaign.get("daily_budget") or 0)
        spend_to_date = summary["total_spend"]
        days_tracked = summary["days_tracked"]

        # Calculate pacing
        daily_avg = round(spend_to_date / days_tracked, 2) if days_tracked > 0 else 0
        budget_remaining = (
            round(total_budget - spend_to_date, 2) if total_budget > 0 else 0
        )

        # Determine days remaining
        end_date_str = campaign.get("end_date")
        if end_date_str:
            end = date.fromisoformat(end_date_str)
            days_remaining = max(0, (end - date.today()).days)
        else:
            days_remaining = 30  # Default assumption

        projected_total = round(daily_avg * (days_tracked + days_remaining), 2)

        # Pacing status
        if total_budget <= 0:
            pacing_status = "no_budget_set"
            recommendation = "Set a total budget to enable pacing analysis."
        elif projected_total > total_budget * 1.1:
            pacing_status = "overpacing"
            ideal_daily = round(budget_remaining / max(days_remaining, 1), 2)
            recommendation = (
                f"Spending ${daily_avg}/day but should be ~${ideal_daily}/day "
                f"to stay within ${total_budget} total budget. "
                f"Consider reducing daily budget or pausing low-ROAS ad sets."
            )
        elif projected_total < total_budget * 0.85:
            pacing_status = "underpacing"
            ideal_daily = round(budget_remaining / max(days_remaining, 1), 2)
            recommendation = (
                f"Spending ${daily_avg}/day but could spend ~${ideal_daily}/day. "
                f"Consider increasing bids, expanding targeting, or adding new ad creatives."
            )
        else:
            pacing_status = "on_track"
            recommendation = (
                f"Budget pacing is healthy at ${daily_avg}/day. "
                f"Projected to spend ${projected_total} of ${total_budget} total budget."
            )

        return {
            "ad_campaign_id": ad_campaign_id,
            "pacing_status": pacing_status,
            "spend_to_date": spend_to_date,
            "total_budget": total_budget,
            "daily_budget": daily_budget,
            "budget_remaining": budget_remaining,
            "daily_average_spend": daily_avg,
            "days_tracked": days_tracked,
            "days_remaining": days_remaining,
            "projected_total_spend": projected_total,
            "overall_roas": summary["overall_roas"],
            "recommendation": recommendation,
        }
