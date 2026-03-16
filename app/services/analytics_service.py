"""AnalyticsService - Event tracking and reporting operations.

This service manages analytics events and reports stored in Supabase.
Used by DataAnalysisAgent.
"""

from typing import Optional, List, Dict, Any
from supabase import Client
from app.services.supabase import get_service_client
from app.services.request_context import get_current_user_id
from app.services.supabase_async import execute_async


class AnalyticsService:
    """Service for managing analytics events and reports."""
    
    def __init__(self):
        self.client: Client = get_service_client()
        self._events_table = "analytics_events"
        self._reports_table = "analytics_reports"

    # ==========================
    # Event Operations
    # ==========================

    async def track_event(
        self,
        event_name: str,
        category: str,
        properties: Dict[str, Any] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """Track a new analytics event."""
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for analytics event")
        data = {
            "event_name": event_name,
            "category": category,
            "properties": properties or {},
            "user_id": effective_user_id,
        }
        response = await execute_async(self.client.table(self._events_table).insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert event")

    async def query_events(
        self,
        event_name: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        user_id: Optional[str] = None
    ) -> List[dict]:
        """Query analytics events."""
        effective_user_id = user_id or get_current_user_id()
        query = self.client.table(self._events_table).select("*")
        
        if event_name:
            query = query.eq("event_name", event_name)
        if category:
            query = query.eq("category", category)
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)
            
        response = await execute_async(query.order("created_at", desc=True).limit(limit))
        return response.data

    # ==========================
    # Report Operations
    # ==========================

    async def create_report(
        self,
        title: str,
        report_type: str,
        data: Dict[str, Any],
        description: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """Create a new analytics report."""
        effective_user_id = user_id or get_current_user_id()
        if not effective_user_id:
            raise Exception("Missing user_id for analytics report")
        data = {
            "title": title,
            "report_type": report_type,
            "data": data,
            "description": description,
            "status": "final",
            "user_id": effective_user_id,
        }
        response = await execute_async(self.client.table(self._reports_table).insert(data))
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert report")

    async def get_report(self, report_id: str, user_id: Optional[str] = None) -> dict:
        """Retrieve a report by ID."""
        effective_user_id = user_id or get_current_user_id()
        query = (
            self.client.table(self._reports_table)
            .select("*")
            .eq("id", report_id)
        )
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)
        response = await execute_async(query.single())
        return response.data

    async def list_reports(
        self,
        report_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[dict]:
        """List reports with optional filters."""
        effective_user_id = user_id or get_current_user_id()
        query = self.client.table(self._reports_table).select("*")
        if report_type:
            query = query.eq("report_type", report_type)
        if effective_user_id:
            query = query.eq("user_id", effective_user_id)
            
        response = await execute_async(query.order("created_at", desc=True))
        return response.data
