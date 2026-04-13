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
            message = f"Found {report_count} report suggestions for your connected integrations: {providers_str}."
        else:
            message = "No integrations connected yet. Connect Stripe, Shopify, or another integration to unlock reports."

        return {
            "success": True,
            "suggestions": suggestions,
            "integrations": integrations,
            "message": message,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "suggestions": [],
            "integrations": [],
        }


async def cohort_analysis(months: int = 6) -> dict:
    """Run full SaaS cohort analysis: retention, LTV, and churn by signup month.

    Analyzes Stripe transaction data to identify customer cohorts and compute
    retention rates, lifetime value, and churn rates per signup month.

    Args:
        months: Number of months of history to analyze (default 6).

    Returns:
        Dictionary with retention matrix, LTV by cohort, churn rates,
        executive summary, and chart data for rendering.
    """
    from app.services.cohort_analysis_service import CohortAnalysisService
    from app.services.request_context import get_current_user_id

    try:
        service = CohortAnalysisService()
        user_id = get_current_user_id() or "anonymous"
        result = await service.full_cohort_analysis(user_id, months)
        if result.get("retention", {}).get("total_customers", 0) == 0:
            return {
                "success": True,
                "message": (
                    "No Stripe revenue data found. Connect your Stripe account and "
                    "ensure financial_records are synced to run cohort analysis."
                ),
                "data": result,
            }
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def query_analytics(
    event_name: str | None = None,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    group_by: str | None = None,
) -> dict:
    """Query analytics events with filtering, date ranges, and optional grouping.

    Real implementation replacing the degraded placeholder. Queries the
    analytics_events table with full filter support.

    Args:
        event_name: Filter by specific event name.
        category: Filter by event category.
        start_date: ISO date string for range start (inclusive).
        end_date: ISO date string for range end (inclusive).
        limit: Maximum events to return.
        group_by: Optional grouping: "day", "week", "month", "category", "event_name".

    Returns:
        Dictionary with events list, count, and optional aggregations.
    """
    from app.services.analytics_service import AnalyticsService
    from app.services.request_context import get_current_user_id

    try:
        service = AnalyticsService()
        user_id = get_current_user_id()
        events = await service.query_events(
            event_name=event_name,
            category=category,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            user_id=user_id,
        )

        aggregations = None
        chart_data = None
        if group_by and events:
            aggregations, chart_data = _aggregate_events(events, group_by)

        return {
            "success": True,
            "events": events,
            "count": len(events),
            "aggregations": aggregations,
            "chart_data": chart_data,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "events": [], "count": 0}


async def query_usage(
    event_name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    group_by: str | None = None,
) -> dict:
    """Query usage analytics with filtering and aggregation.

    Real implementation replacing the degraded placeholder. Queries usage-category
    analytics events with full filter and grouping support.

    Args:
        event_name: Filter by specific usage event.
        start_date: ISO date string for range start.
        end_date: ISO date string for range end.
        limit: Maximum events to return.
        group_by: Optional grouping: "day", "week", "month", "event_name".

    Returns:
        Dictionary with usage events, counts, and trend data.
    """
    from app.services.analytics_service import AnalyticsService
    from app.services.request_context import get_current_user_id

    try:
        service = AnalyticsService()
        user_id = get_current_user_id()
        events = await service.query_events(
            event_name=event_name,
            category="usage",
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            user_id=user_id,
        )

        aggregations = None
        chart_data = None
        if events:
            # Always compute per-event frequency counts for usage metrics
            freq: dict[str, int] = {}
            for evt in events:
                name = evt.get("event_name", "unknown")
                freq[name] = freq.get(name, 0) + 1
            aggregations = freq

            if group_by:
                _, chart_data = _aggregate_events(events, group_by)
            else:
                chart_data = {
                    "labels": list(freq.keys()),
                    "values": list(freq.values()),
                    "type": "bar",
                    "title": "Usage Events by Type",
                }

        return {
            "success": True,
            "events": events,
            "count": len(events),
            "aggregations": aggregations,
            "chart_data": chart_data,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "events": [], "count": 0}


def _aggregate_events(
    events: list[dict], group_by: str
) -> tuple[dict, dict]:
    """Post-process events list into aggregated counts and chart data.

    Args:
        events: List of event dicts with event_name, category, created_at keys.
        group_by: One of "day", "week", "month", "category", "event_name".

    Returns:
        Tuple of (aggregations dict, chart_data dict).
    """
    from datetime import datetime

    buckets: dict[str, int] = {}

    for evt in events:
        if group_by in ("day", "week", "month"):
            raw = evt.get("created_at", "")
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if group_by == "day":
                    key = dt.strftime("%Y-%m-%d")
                elif group_by == "week":
                    key = dt.strftime("%Y-W%W")
                else:
                    key = dt.strftime("%Y-%m")
            except (ValueError, AttributeError):
                key = "unknown"
        elif group_by == "category":
            key = evt.get("category", "unknown")
        else:  # event_name
            key = evt.get("event_name", "unknown")

        buckets[key] = buckets.get(key, 0) + 1

    sorted_buckets = dict(sorted(buckets.items()))
    chart_data = {
        "labels": list(sorted_buckets.keys()),
        "values": list(sorted_buckets.values()),
        "type": "bar",
        "title": f"Events by {group_by}",
    }
    return sorted_buckets, chart_data


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
