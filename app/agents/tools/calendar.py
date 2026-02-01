# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Google Calendar tools for agents.

Provides tools for event management and scheduling.
"""

from datetime import datetime, timedelta
from typing import Any

# Tool context type
ToolContextType = Any


def _get_calendar_service(tool_context: ToolContextType):
    """Get Calendar service from tool context credentials."""
    from app.integrations.google.calendar import GoogleCalendarService
    from app.integrations.google.client import get_google_credentials
    
    provider_token = tool_context.state.get("google_provider_token")
    refresh_token = tool_context.state.get("google_refresh_token")
    
    if not provider_token:
        raise ValueError("Google authentication required for calendar features.")
    
    credentials = get_google_credentials(provider_token, refresh_token)
    return GoogleCalendarService(credentials)


def list_events(
    tool_context: ToolContextType,
    max_results: int = 10,
) -> dict[str, Any]:
    """List upcoming calendar events.
    
    Args:
        tool_context: Agent tool context.
        max_results: Maximum number of events to return.
        
    Returns:
        Dict with list of upcoming events.
    """
    try:
        service = _get_calendar_service(tool_context)
        events = service.list_upcoming_events(max_results)
        
        return {
            "status": "success",
            "count": len(events),
            "events": [
                {
                    "id": e.id,
                    "title": e.title,
                    "start": e.start.isoformat(),
                    "end": e.end.isoformat(),
                    "location": e.location,
                    "attendees": e.attendees,
                    "link": e.link,
                }
                for e in events
            ],
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to list events: {e}"}


def create_calendar_event(
    tool_context: ToolContextType,
    title: str,
    start_time: str,
    duration_minutes: int = 60,
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
) -> dict[str, Any]:
    """Create a calendar event.
    
    Args:
        tool_context: Agent tool context.
        title: Event title.
        start_time: Start time in ISO format (e.g., "2026-02-01T10:00:00").
        duration_minutes: Duration in minutes (default 60).
        description: Optional description.
        location: Optional location.
        attendees: Optional list of attendee emails.
        
    Returns:
        Dict with created event details.
    """
    try:
        service = _get_calendar_service(tool_context)
        
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = start + timedelta(minutes=duration_minutes)
        
        event = service.create_event(
            title=title,
            start=start,
            end=end,
            description=description,
            location=location,
            attendees=attendees,
        )
        
        return {
            "status": "success",
            "message": f"Event '{title}' created",
            "event": {
                "id": event.id,
                "title": event.title,
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "link": event.link,
            },
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to create event: {e}"}


def check_availability(
    tool_context: ToolContextType,
    start_time: str,
    end_time: str,
) -> dict[str, Any]:
    """Check if a time slot is free on the calendar.
    
    Args:
        tool_context: Agent tool context.
        start_time: Start of time range in ISO format.
        end_time: End of time range in ISO format.
        
    Returns:
        Dict with availability status.
    """
    try:
        service = _get_calendar_service(tool_context)
        
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        
        result = service.check_availability(start, end)
        
        return {
            "status": "success",
            "available": result["available"],
            "conflicts": result["conflicts"],
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to check availability: {e}"}


def schedule_meeting(
    tool_context: ToolContextType,
    title: str,
    attendees: list[str],
    duration_minutes: int = 60,
    preferred_time: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Schedule a meeting, checking availability first.
    
    Args:
        tool_context: Agent tool context.
        title: Meeting title.
        attendees: List of attendee email addresses.
        duration_minutes: Duration in minutes.
        preferred_time: Preferred start time in ISO format (optional).
        description: Optional meeting description.
        
    Returns:
        Dict with scheduled meeting details or conflict info.
    """
    try:
        service = _get_calendar_service(tool_context)
        
        preferred = None
        if preferred_time:
            preferred = datetime.fromisoformat(preferred_time.replace("Z", "+00:00"))
        
        result = service.schedule_meeting(
            title=title,
            duration_minutes=duration_minutes,
            attendees=attendees,
            preferred_start=preferred,
            description=description,
        )
        
        return result
        
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to schedule meeting: {e}"}


# Export Calendar tools
CALENDAR_TOOLS = [
    list_events,
    create_calendar_event,
    check_availability,
    schedule_meeting,
]
