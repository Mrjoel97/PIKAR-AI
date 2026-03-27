# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""ContentCalendarService - CRUD operations for editorial content calendar.

This service provides Create, Read, Update, Delete operations for content
calendar items stored in the content_calendar table in Supabase.
Used by MarketingAutomationAgent for editorial planning and scheduling.
"""

from app.services.base_service import AdminService, BaseService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async


class ContentCalendarService(BaseService):
    """Service for managing the content calendar.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: str | None = None):
        """Initialize the content calendar service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._table_name = "content_calendar"

    async def schedule_content(
        self,
        title: str,
        content_type: str,
        scheduled_date: str,
        platform: str = None,
        scheduled_time: str = None,
        description: str = None,
        campaign_id: str = None,
        blog_post_id: str = None,
        metadata: dict = None,
        user_id: str | None = None,
    ) -> dict:
        """Schedule a content item on the calendar.

        Args:
            title: Content title or name.
            content_type: Type (blog, social, email, video, newsletter, ad, other).
            scheduled_date: Date to publish (YYYY-MM-DD).
            platform: Target platform (twitter, linkedin, blog, email, etc.).
            scheduled_time: Time to publish (HH:MM).
            description: Content description or notes.
            campaign_id: Optional campaign this belongs to.
            blog_post_id: Optional linked blog post.
            metadata: Additional metadata (target_audience, cta, hashtags, utm_params).
            user_id: Optional user ID override.

        Returns:
            The created calendar item.
        """
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for calendar scheduling")

        data = {
            "user_id": effective_user_id,
            "title": title,
            "content_type": content_type,
            "scheduled_date": scheduled_date,
            "platform": platform,
            "scheduled_time": scheduled_time,
            "description": description,
            "campaign_id": campaign_id,
            "blog_post_id": blog_post_id,
            "metadata": metadata or {},
            "status": "planned",
        }
        data = {k: v for k, v in data.items() if v is not None}

        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table(self._table_name).insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert")

    async def get_calendar_item(self, item_id: str, user_id: str | None = None) -> dict:
        """Retrieve a calendar item by ID.

        Args:
            item_id: The unique calendar item ID.
            user_id: Optional user ID override.

        Returns:
            The calendar item record.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).select("*").eq("id", item_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def update_calendar_item(
        self,
        item_id: str,
        title: str | None = None,
        scheduled_date: str | None = None,
        scheduled_time: str | None = None,
        status: str | None = None,
        platform: str | None = None,
        description: str | None = None,
        metadata: dict | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Update a calendar item.

        Args:
            item_id: The unique calendar item ID.
            title: New title.
            scheduled_date: New date (YYYY-MM-DD).
            scheduled_time: New time (HH:MM).
            status: New status (planned, in_progress, ready, scheduled, published, cancelled).
            platform: New platform.
            description: New description.
            metadata: New metadata.
            user_id: Optional user ID override.

        Returns:
            The updated calendar item.
        """
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if scheduled_date is not None:
            update_data["scheduled_date"] = scheduled_date
        if scheduled_time is not None:
            update_data["scheduled_time"] = scheduled_time
        if status is not None:
            update_data["status"] = status
        if platform is not None:
            update_data["platform"] = platform
        if description is not None:
            update_data["description"] = description
        if metadata is not None:
            update_data["metadata"] = metadata

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).update(update_data).eq("id", item_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update")

    async def delete_calendar_item(
        self, item_id: str, user_id: str | None = None
    ) -> bool:
        """Delete a calendar item.

        Args:
            item_id: The unique calendar item ID.
            user_id: Optional user ID override.

        Returns:
            True if deletion was successful.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).delete().eq("id", item_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        return len(response.data) > 0

    async def list_calendar(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        content_type: str | None = None,
        status: str | None = None,
        platform: str | None = None,
        campaign_id: str | None = None,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list:
        """List calendar items with optional date range and filters.

        Args:
            start_date: Start of date range (YYYY-MM-DD).
            end_date: End of date range (YYYY-MM-DD).
            content_type: Filter by content type.
            status: Filter by status.
            platform: Filter by platform.
            campaign_id: Filter by campaign.
            user_id: Optional user ID override.
            limit: Maximum results (default 100).

        Returns:
            List of calendar items sorted by scheduled date.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).select("*")

        if start_date:
            query = query.gte("scheduled_date", start_date)
        if end_date:
            query = query.lte("scheduled_date", end_date)
        if content_type:
            query = query.eq("content_type", content_type)
        if status:
            query = query.eq("status", status)
        if platform:
            query = query.eq("platform", platform)
        if campaign_id:
            query = query.eq("campaign_id", campaign_id)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(
            query.order("scheduled_date", desc=False).limit(limit)
        )
        return response.data
