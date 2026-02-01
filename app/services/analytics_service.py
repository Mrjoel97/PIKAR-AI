"""AnalyticsService - Event tracking and reporting operations.

This service manages analytics events and reports stored in Supabase.
Used by DataAnalysisAgent.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from supabase import create_client, Client


class AnalyticsService:
    """Service for managing analytics events and reports."""
    
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError("Supabase credentials missing")
        self.client: Client = create_client(url, key)
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
        data = {
            "event_name": event_name,
            "category": category,
            "properties": properties or {},
            "user_id": user_id,
        }
        response = self.client.table(self._events_table).insert(data).execute()
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert event")

    async def query_events(
        self,
        event_name: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """Query analytics events."""
        query = self.client.table(self._events_table).select("*")
        
        if event_name:
            query = query.eq("event_name", event_name)
        if category:
            query = query.eq("category", category)
        if start_date:
            query = query.gte("created_at", start_date)
        if end_date:
            query = query.lte("created_at", end_date)
            
        response = query.order("created_at", desc=True).limit(limit).execute()
        return response.data

    # ==========================
    # Report Operations
    # ==========================

    async def create_report(
        self,
        title: str,
        report_type: str,
        data: Dict[str, Any],
        description: Optional[str] = None
    ) -> dict:
        """Create a new analytics report."""
        data = {
            "title": title,
            "report_type": report_type,
            "data": data,
            "description": description,
            "status": "final"
        }
        response = self.client.table(self._reports_table).insert(data).execute()
        if response.data:
            return response.data[0]
        raise Exception("No data returned from insert report")

    async def get_report(self, report_id: str) -> dict:
        """Retrieve a report by ID."""
        response = (
            self.client.table(self._reports_table)
            .select("*")
            .eq("id", report_id)
            .single()
            .execute()
        )
        return response.data

    async def list_reports(self, report_type: Optional[str] = None) -> List[dict]:
        """List reports with optional filters."""
        query = self.client.table(self._reports_table).select("*")
        if report_type:
            query = query.eq("report_type", report_type)
            
        response = query.order("created_at", desc=True).execute()
        return response.data
