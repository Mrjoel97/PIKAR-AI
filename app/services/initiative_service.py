"""InitiativeService - CRUD operations for strategic initiatives and OKRs.

This service provides Create, Read, Update, Delete operations for initiatives
stored in the initiatives table in Supabase with proper RLS authentication.
Used by StrategicPlanningAgent.
"""

from typing import Optional
from app.services.base_service import BaseService


class InitiativeService(BaseService):
    """Service for managing initiatives and OKRs.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: Optional[str] = None):
        """Initialize the initiative service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._table_name = "initiatives"

    async def create_initiative(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        user_id: Optional[str] = None
    ) -> dict:
        """Create a new initiative.
        
        Args:
            title: Initiative title.
            description: Initiative description.
            priority: Priority level (low, medium, high, critical).
            user_id: Optional user ID who owns the initiative.
            
        Returns:
            The created initiative record.
        """
        data = {
            "title": title,
            "description": description,
            "priority": priority,
            "status": "draft",
            "progress": 0,
            "user_id": user_id
        }
        
        response = self.client.table(self._table_name).insert(data).execute()
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert")

    async def get_initiative(self, initiative_id: str) -> dict:
        """Retrieve a single initiative by ID.
        
        Args:
            initiative_id: The unique initiative ID.
            
        Returns:
            The initiative record.
        """
        response = (
            self.client.table(self._table_name)
            .select("*")
            .eq("id", initiative_id)
            .single()
            .execute()
        )
        return response.data

    async def update_initiative(
        self,
        initiative_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> dict:
        """Update an initiative's status or progress.
        
        Args:
            initiative_id: The unique initiative ID.
            status: New status (draft, active, completed, on_hold).
            progress: Progress percentage (0-100).
            title: New title.
            description: New description.
            
        Returns:
            The updated initiative record.
        """
        update_data = {}
        if status is not None:
            update_data["status"] = status
        if progress is not None:
            update_data["progress"] = progress
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
            
        response = (
            self.client.table(self._table_name)
            .update(update_data)
            .eq("id", initiative_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        raise Exception("No data returned from update")

    async def delete_initiative(self, initiative_id: str) -> bool:
        """Delete an initiative by ID.
        
        Args:
            initiative_id: The unique initiative ID.
            
        Returns:
            True if deletion was successful.
        """
        response = (
            self.client.table(self._table_name)
            .delete()
            .eq("id", initiative_id)
            .execute()
        )
        return len(response.data) > 0

    async def list_initiatives(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50
    ) -> list:
        """List initiatives with optional filters.
        
        Args:
            status: Filter by initiative status.
            user_id: Filter by user ID.
            priority: Filter by priority.
            limit: Maximum number of results (default 50).
            
        Returns:
            List of initiative records.
        """
        query = self.client.table(self._table_name).select("*")
        
        if status:
            query = query.eq("status", status)
        if user_id:
            query = query.eq("user_id", user_id)
        if priority:
            query = query.eq("priority", priority)
            
        response = query.order("created_at", desc=True).limit(limit).execute()
        return response.data
