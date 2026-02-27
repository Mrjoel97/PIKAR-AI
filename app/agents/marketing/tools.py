# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tools for the Marketing Automation Agent."""


async def create_campaign(name: str, campaign_type: str, target_audience: str) -> dict:
    """Create a new marketing campaign.
    
    Args:
        name: Campaign name.
        campaign_type: Type (email, social, content, paid_ads).
        target_audience: Target audience description.
        
    Returns:
        Dictionary containing the created campaign.
    """
    from app.services.campaign_service import CampaignService
    
    try:
        from app.services.request_context import get_current_user_id
        service = CampaignService()
        campaign = await service.create_campaign(
            name,
            campaign_type,
            target_audience,
            user_id=get_current_user_id()
        )
        return {"success": True, "campaign": campaign}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_campaign(campaign_id: str) -> dict:
    """Retrieve a campaign by ID.
    
    Args:
        campaign_id: The unique campaign ID.
        
    Returns:
        Dictionary containing the campaign details.
    """
    from app.services.campaign_service import CampaignService
    
    try:
        from app.services.request_context import get_current_user_id
        service = CampaignService()
        campaign = await service.get_campaign(campaign_id, user_id=get_current_user_id())
        return {"success": True, "campaign": campaign}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def update_campaign(campaign_id: str, status: str = None, name: str = None) -> dict:
    """Update a campaign's status or name.
    
    Args:
        campaign_id: The unique campaign ID.
        status: New status (draft, active, paused, completed).
        name: New campaign name.
        
    Returns:
        Dictionary confirming the update.
    """
    from app.services.campaign_service import CampaignService
    
    try:
        from app.services.request_context import get_current_user_id
        service = CampaignService()
        campaign = await service.update_campaign(
            campaign_id,
            status=status,
            name=name,
            user_id=get_current_user_id()
        )
        return {"success": True, "campaign": campaign}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_campaigns(status: str = None, campaign_type: str = None) -> dict:
    """List campaigns with optional filters.
    
    Args:
        status: Filter by campaign status.
        campaign_type: Filter by campaign type.
        
    Returns:
        Dictionary containing list of campaigns.
    """
    from app.services.campaign_service import CampaignService
    
    try:
        from app.services.request_context import get_current_user_id
        service = CampaignService()
        campaigns = await service.list_campaigns(
            status=status,
            campaign_type=campaign_type,
            user_id=get_current_user_id()
        )
        return {"success": True, "campaigns": campaigns, "count": len(campaigns)}
    except Exception as e:
        return {"success": False, "error": str(e), "campaigns": []}


async def record_campaign_metrics(campaign_id: str, impressions: int = 0, clicks: int = 0, conversions: int = 0) -> dict:
    """Record performance metrics for a campaign.
    
    Args:
        campaign_id: The unique campaign ID.
        impressions: Number of impressions.
        clicks: Number of clicks.
        conversions: Number of conversions.
        
    Returns:
        Dictionary with updated campaign metrics.
    """
    from app.services.campaign_service import CampaignService
    
    try:
        from app.services.request_context import get_current_user_id
        service = CampaignService()
        result = await service.record_metrics(
            campaign_id,
            impressions,
            clicks,
            conversions,
            user_id=get_current_user_id()
        )
        return {"success": True, "campaign": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
