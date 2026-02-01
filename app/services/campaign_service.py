"""CampaignService - CRUD operations for marketing campaigns.

This service provides Create, Read, Update, Delete operations for campaigns
stored in the campaigns table in Supabase with proper RLS authentication.
Used by MarketingAutomationAgent.
"""

from typing import Optional
from app.services.base_service import BaseService


class CampaignService(BaseService):
    """Service for managing marketing campaigns.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: Optional[str] = None):
        """Initialize the campaign service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._table_name = "campaigns"

    async def create_campaign(
        self,
        name: str,
        campaign_type: str,
        target_audience: str,
        schedule_start: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """Create a new marketing campaign.
        
        Args:
            name: Campaign name.
            campaign_type: Type (email, social, content, paid_ads).
            target_audience: Target audience description.
            schedule_start: Optional start date (ISO format).
            user_id: Optional user ID who owns the campaign.
            
        Returns:
            The created campaign record.
        """
        data = {
            "name": name,
            "campaign_type": campaign_type,
            "target_audience": target_audience,
            "schedule_start": schedule_start,
            "status": "draft",
            "user_id": user_id
        }
        
        response = self.client.table(self._table_name).insert(data).execute()
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert")

    async def get_campaign(self, campaign_id: str) -> dict:
        """Retrieve a single campaign by ID.
        
        Args:
            campaign_id: The unique campaign ID.
            
        Returns:
            The campaign record.
        """
        response = (
            self.client.table(self._table_name)
            .select("*")
            .eq("id", campaign_id)
            .single()
            .execute()
        )
        return response.data

    async def update_campaign(
        self,
        campaign_id: str,
        status: Optional[str] = None,
        name: Optional[str] = None,
        metrics: Optional[dict] = None
    ) -> dict:
        """Update a campaign's status or metrics.
        
        Args:
            campaign_id: The unique campaign ID.
            status: New status (draft, active, paused, completed).
            name: New campaign name.
            metrics: Performance metrics dict.
            
        Returns:
            The updated campaign record.
        """
        update_data = {}
        if status is not None:
            update_data["status"] = status
        if name is not None:
            update_data["name"] = name
        if metrics is not None:
            update_data["metrics"] = metrics
            
        response = (
            self.client.table(self._table_name)
            .update(update_data)
            .eq("id", campaign_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update")

    async def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign by ID.
        
        Args:
            campaign_id: The unique campaign ID.
            
        Returns:
            True if deletion was successful.
        """
        response = (
            self.client.table(self._table_name)
            .delete()
            .eq("id", campaign_id)
            .execute()
        )
        return len(response.data) > 0

    async def list_campaigns(
        self,
        status: Optional[str] = None,
        campaign_type: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> list:
        """List campaigns with optional filters.
        
        Args:
            status: Filter by campaign status.
            campaign_type: Filter by campaign type.
            user_id: Filter by user ID.
            limit: Maximum number of results (default 50).
            
        Returns:
            List of campaign records.
        """
        query = self.client.table(self._table_name).select("*")
        
        if status:
            query = query.eq("status", status)
        if campaign_type:
            query = query.eq("campaign_type", campaign_type)
        if user_id:
            query = query.eq("user_id", user_id)
            
        response = query.order("created_at", desc=True).limit(limit).execute()
        return response.data

    async def record_metrics(
        self,
        campaign_id: str,
        impressions: int = 0,
        clicks: int = 0,
        conversions: int = 0
    ) -> dict:
        """Record performance metrics for a campaign.
        
        Args:
            campaign_id: The unique campaign ID.
            impressions: Number of impressions.
            clicks: Number of clicks.
            conversions: Number of conversions.
            
        Returns:
            The updated campaign record with metrics.
        """
        metrics = {
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "ctr": round(clicks / impressions * 100, 2) if impressions > 0 else 0.0
        }
        return await self.update_campaign(campaign_id, metrics=metrics)
