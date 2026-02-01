"""SupportTicketService - CRUD operations for customer support tickets.

This service provides Create, Read, Update, Delete operations for tickets
stored in Supabase with proper RLS authentication.
Used by CustomerSupportAgent.
"""

from typing import Optional, List
from app.services.base_service import BaseService


class SupportTicketService(BaseService):
    """Service for managing support tickets.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: Optional[str] = None):
        """Initialize the support ticket service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)
        self._table_name = "support_tickets"

    async def create_ticket(
        self,
        subject: str,
        description: str,
        customer_email: str,
        priority: str = "normal",
        status: str = "new",
        assigned_to: Optional[str] = None
    ) -> dict:
        """Create a new support ticket."""
        data = {
            "subject": subject,
            "description": description,
            "customer_email": customer_email,
            "priority": priority,
            "status": status,
            "assigned_to": assigned_to,
        }
        # Force return of inserted data
        response = self.client.table(self._table_name).insert(data).execute()
        # logger.info(f"Create Ticket Response: {response}")
        if response.data and len(response.data) > 0:
            return response.data[0]
        # Fallback if single object returned (unlikely with supabase-py but possible)
        if response.data and isinstance(response.data, dict):
            return response.data
        raise Exception(f"No data returned from insert ticket. Response: {response}")

    async def get_ticket(self, ticket_id: str) -> dict:
        """Retrieve a ticket by ID."""
        response = (
            self.client.table(self._table_name)
            .select("*")
            .eq("id", ticket_id)
            .single()
            .execute()
        )
        # .single() returns dict directly in .data usually
        if response.data:
            return response.data
        raise Exception(f"Ticket {ticket_id} not found")

    async def update_ticket(
        self,
        ticket_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[str] = None,
        resolution: Optional[str] = None
    ) -> dict:
        """Update a ticket record."""
        update_data = {}
        if status:
            update_data["status"] = status
        if priority:
            update_data["priority"] = priority
        if assigned_to:
            update_data["assigned_to"] = assigned_to
        if resolution:
            update_data["resolution"] = resolution
            
        response = (
            self.client.table(self._table_name)
            .update(update_data)
            .eq("id", ticket_id)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
        raise Exception(f"No data returned from update ticket {ticket_id}")

    async def list_tickets(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> List[dict]:
        """List tickets with optional filters."""
        query = self.client.table(self._table_name).select("*")
        if status:
            query = query.eq("status", status)
        if priority:
            query = query.eq("priority", priority)
        if assigned_to:
            query = query.eq("assigned_to", assigned_to)
            
        response = query.order("created_at", desc=True).execute()
        return response.data or []

    async def delete_ticket(self, ticket_id: str) -> bool:
        """Delete a ticket."""
        response = (
            self.client.table(self._table_name)
            .delete()
            .eq("id", ticket_id)
            .execute()
        )
        # Check if any rows were deleted
        if response.data and len(response.data) > 0:
            return True
        return False
