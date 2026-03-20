# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tools for the Data Analysis Agent."""

import json


async def track_event(event_name: str, category: str, properties: str = None) -> dict:
    """Track a new analytics event.

    Args:
        event_name: Name of the event.
        category: Event category.
        properties: JSON string of event properties.

    Returns:
        Dictionary confirming the event was tracked.
    """
    from app.services.analytics_service import AnalyticsService

    try:
        from app.services.request_context import get_current_user_id

        service = AnalyticsService()
        props_dict = json.loads(properties) if properties else {}
        event = await service.track_event(
            event_name, category, properties=props_dict, user_id=get_current_user_id()
        )
        return {
            "success": True,
            "event": event,
            "event_id": event.get("id") if isinstance(event, dict) else None,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def query_events(
    event_name: str = None, category: str = None, limit: int = 100
) -> dict:
    """Query analytics events.

    Args:
        event_name: Filter by event name.
        category: Filter by category.
        limit: Max number of events to return.

    Returns:
        Dictionary containing list of events.
    """
    from app.services.analytics_service import AnalyticsService

    try:
        from app.services.request_context import get_current_user_id

        service = AnalyticsService()
        events = await service.query_events(
            event_name=event_name,
            category=category,
            limit=limit,
            user_id=get_current_user_id(),
        )
        return {"success": True, "events": events, "count": len(events)}
    except Exception as e:
        return {"success": False, "error": str(e), "events": []}


async def create_report(
    title: str, report_type: str, data: str, description: str = None
) -> dict:
    """Create a new analytics report.

    Args:
        title: Report title.
        report_type: Type of report (growth, usage, performance).
        data: JSON string of report data.
        description: Report description.

    Returns:
        Dictionary containing the created report.
    """
    from app.services.analytics_service import AnalyticsService

    try:
        from app.services.request_context import get_current_user_id

        service = AnalyticsService()
        data_dict = json.loads(data) if data else {}
        report = await service.create_report(
            title, report_type, data_dict, description, user_id=get_current_user_id()
        )
        return {
            "success": True,
            "report": report,
            "report_id": report.get("id") if isinstance(report, dict) else None,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_reports(report_type: str = None) -> dict:
    """List analytics reports.

    Args:
        report_type: Filter by report type.

    Returns:
        Dictionary containing list of reports.
    """
    from app.services.analytics_service import AnalyticsService

    try:
        from app.services.request_context import get_current_user_id

        service = AnalyticsService()
        reports = await service.list_reports(
            report_type=report_type, user_id=get_current_user_id()
        )
        return {"success": True, "reports": reports, "count": len(reports)}
    except Exception as e:
        return {"success": False, "error": str(e), "reports": []}
