# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Tools for the Data Analysis Agent."""

import json


async def nl_data_query(question: str) -> dict:
    """Answer a natural language data question with plain-English response and chart data.

    Auto-routes to the correct data source (financial records, subscriptions,
    Shopify orders, analytics events, or external databases) based on the question.

    Args:
        question: Natural language question about business data.

    Returns:
        Dictionary with answer (plain-English), chart_data (for rendering),
        source (which data source was used), and raw_data (underlying numbers).
    """
    from app.services.data_query_service import DataQueryService
    from app.services.request_context import get_current_user_id

    try:
        service = DataQueryService()
        user_id = get_current_user_id() or "anonymous"

        classification = service.classify_query(question)
        source = classification["source"]

        raw_data = await service.query_internal_data(question, source, user_id)
        answer = service.format_nl_answer(raw_data, question)
        chart_data = service.format_chart_data(raw_data, source)

        return {
            "success": True,
            "answer": answer,
            "chart_data": chart_data,
            "source": source,
            "raw_data": raw_data,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


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


async def suggest_data_reports(provider: str | None = None) -> dict:
    """Suggest useful data reports based on connected integrations.

    When a new integration is connected, call this to discover what reports
    are available. If no provider specified, returns suggestions for all
    connected integrations.

    Args:
        provider: Integration provider name (stripe, shopify, google_ads, etc.).
            If None, checks all connected integrations.

    Returns:
        Dictionary with suggestions per integration and a summary message.
    """
    from app.services.weekly_report_service import WeeklyReportService

    try:
        from app.services.request_context import get_current_user_id

        service = WeeklyReportService()
        user_id = get_current_user_id()

        if provider:
            suggestions = service.get_data_catalog_suggestions(provider)
            integrations = [provider]
        else:
            integrations_data = await service.get_available_integrations(user_id)
            integrations = [i["provider"] for i in integrations_data]
            suggestions = []
            for integ in integrations:
                suggestions.extend(service.get_data_catalog_suggestions(integ))

        report_count = len(suggestions)
        if integrations:
            providers_str = ", ".join(integrations)
            message = (
                f"Found {report_count} report suggestions for your connected integrations: {providers_str}."
            )
        else:
            message = "No integrations connected yet. Connect Stripe, Shopify, or another integration to unlock reports."

        return {
            "success": True,
            "suggestions": suggestions,
            "integrations": integrations,
            "message": message,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "suggestions": [], "integrations": []}


async def generate_weekly_report() -> dict:
    """Generate the weekly business report on demand.

    Returns a structured report with revenue summary, top metrics,
    anomalies, and an executive summary in plain English.

    Returns:
        Dictionary containing the full weekly report and a success flag.
    """
    from app.services.weekly_report_service import WeeklyReportService

    try:
        from app.services.request_context import get_current_user_id

        service = WeeklyReportService()
        user_id = get_current_user_id()
        report = await service.generate_weekly_report(user_id)
        return {"success": True, "report": report}
    except Exception as e:
        return {"success": False, "error": str(e)}
