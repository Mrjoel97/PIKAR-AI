# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""SupportTicketService - CRUD operations for customer support tickets.

This service provides Create, Read, Update, Delete operations for tickets
stored in Supabase with proper RLS authentication.
Used by CustomerSupportAgent.
"""

from app.services.base_service import AdminService, BaseService
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async


class SupportTicketService(BaseService):
    """Service for managing support tickets.

    All queries are automatically scoped to the authenticated user via RLS.
    """

    def __init__(self, user_token: str | None = None):
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
        assigned_to: str | None = None,
        user_id: str | None = None,
        source: str = "manual",
        sentiment: str = "neutral",
    ) -> dict:
        """Create a new support ticket."""
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for ticket creation")
        data = {
            "subject": subject,
            "description": description,
            "customer_email": customer_email,
            "priority": priority,
            "status": status,
            "assigned_to": assigned_to,
            "user_id": effective_user_id,
            "source": source,
            "sentiment": sentiment,
        }
        # Force return of inserted data
        client = self.client if self.is_authenticated else AdminService().client
        response = await execute_async(client.table(self._table_name).insert(data))
        # logger.info(f"Create Ticket Response: {response}")
        if response.data and len(response.data) > 0:
            return response.data[0]
        # Fallback if single object returned (unlikely with supabase-py but possible)
        if response.data and isinstance(response.data, dict):
            return response.data
        raise Exception(f"No data returned from insert ticket. Response: {response}")

    async def get_ticket(self, ticket_id: str, user_id: str | None = None) -> dict:
        """Retrieve a ticket by ID."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).select("*").eq("id", ticket_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        # .single() returns dict directly in .data usually
        if response.data:
            return response.data
        raise Exception(f"Ticket {ticket_id} not found")

    async def update_ticket(
        self,
        ticket_id: str,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        resolution: str | None = None,
        user_id: str | None = None,
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

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).update(update_data).eq("id", ticket_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        if response.data and len(response.data) > 0:
            return response.data[0]
        raise Exception(f"No data returned from update ticket {ticket_id}")

    async def list_tickets(
        self,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        user_id: str | None = None,
    ) -> list[dict]:
        """List tickets with optional filters."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).select("*")
        if status:
            query = query.eq("status", status)
        if priority:
            query = query.eq("priority", priority)
        if assigned_to:
            query = query.eq("assigned_to", assigned_to)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)

        response = await execute_async(query.order("created_at", desc=True))
        return response.data or []

    async def find_similar_resolved_tickets(
        self,
        min_count: int = 3,
        user_id: str | None = None,
    ) -> list[dict]:
        """Find groups of resolved tickets with similar subjects.

        Queries resolved/closed tickets, groups by normalized subject prefix (first 50 chars
        lowercase), and returns groups with >= min_count tickets. Each group is a dict with:
        - subject_pattern: the common subject prefix
        - count: number of similar tickets
        - tickets: list of ticket dicts (id, subject, resolution, resolved_at)

        Args:
            min_count: Minimum number of tickets required to form a group (default 3).
            user_id: Optional user ID to scope the query.

        Returns:
            List of ticket groups meeting the min_count threshold.
        """
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._table_name)
            .select("id, subject, resolution, resolved_at, user_id")
            .in_("status", ["resolved", "closed"])
            .order("created_at", desc=True)
            .limit(100)
        )
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        tickets = response.data or []

        # Group by normalized subject prefix (first 50 chars, lowercase, stripped)
        groups: dict[str, list[dict]] = {}
        for ticket in tickets:
            raw_subject = ticket.get("subject", "") or ""
            prefix = raw_subject.strip().lower()[:50]
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(ticket)

        return [
            {
                "subject_pattern": prefix,
                "count": len(ticket_list),
                "tickets": ticket_list,
            }
            for prefix, ticket_list in groups.items()
            if len(ticket_list) >= min_count
        ]

    async def get_ticket_stats(self, user_id: str | None = None) -> dict:
        """Get aggregate ticket statistics for health dashboard.

        Fetches up to 500 tickets for the user and computes stats in Python
        to avoid needing raw SQL aggregation through the Supabase client.

        Returns:
            Dict with open_count, resolved_count, total_count,
            avg_resolution_hours, sentiment_breakdown, priority_breakdown.
        """
        from datetime import datetime

        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = (
            client.table(self._table_name)
            .select("id, status, priority, sentiment, created_at, resolved_at")
            .limit(500)
        )
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        tickets = response.data or []

        open_count = 0
        resolved_count = 0
        resolution_hours: list[float] = []
        sentiment_breakdown: dict[str, int] = {
            "positive": 0,
            "neutral": 0,
            "negative": 0,
        }
        priority_breakdown: dict[str, int] = {
            "low": 0,
            "normal": 0,
            "high": 0,
            "urgent": 0,
        }

        for ticket in tickets:
            status = ticket.get("status", "new")
            if status in ("resolved", "closed"):
                resolved_count += 1
                # Compute resolution hours from timestamps
                created_raw = ticket.get("created_at")
                resolved_raw = ticket.get("resolved_at")
                if created_raw and resolved_raw:
                    try:
                        created_dt = datetime.fromisoformat(
                            created_raw.replace("Z", "+00:00")
                        )
                        resolved_dt = datetime.fromisoformat(
                            resolved_raw.replace("Z", "+00:00")
                        )
                        delta_hours = (
                            resolved_dt - created_dt
                        ).total_seconds() / 3600.0
                        if delta_hours >= 0:
                            resolution_hours.append(delta_hours)
                    except (ValueError, TypeError):
                        pass
            else:
                open_count += 1

            sentiment = ticket.get("sentiment") or "neutral"
            if sentiment in sentiment_breakdown:
                sentiment_breakdown[sentiment] += 1
            else:
                sentiment_breakdown["neutral"] += 1

            priority = ticket.get("priority") or "normal"
            if priority in priority_breakdown:
                priority_breakdown[priority] += 1
            else:
                priority_breakdown["normal"] += 1

        avg_resolution_hours: float | None = None
        if resolution_hours:
            avg_resolution_hours = sum(resolution_hours) / len(resolution_hours)

        return {
            "open_count": open_count,
            "resolved_count": resolved_count,
            "total_count": len(tickets),
            "avg_resolution_hours": avg_resolution_hours,
            "sentiment_breakdown": sentiment_breakdown,
            "priority_breakdown": priority_breakdown,
        }

    async def delete_ticket(self, ticket_id: str, user_id: str | None = None) -> bool:
        """Delete a ticket."""
        effective_user_id = user_id or get_current_user_id()
        client = self.client if self.is_authenticated else AdminService().client
        query = client.table(self._table_name).delete().eq("id", ticket_id)
        if not self.is_authenticated and effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query)
        # Check if any rows were deleted
        if response.data and len(response.data) > 0:
            return True
        return False
