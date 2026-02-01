# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Google Calendar service for event management.

Enables agents to:
- Create calendar events
- Check availability
- Schedule meetings
"""

from datetime import datetime, timedelta
from typing import Any
from dataclasses import dataclass

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource


@dataclass
class CalendarEvent:
    """Represents a calendar event."""
    id: str
    title: str
    start: datetime
    end: datetime
    description: str | None
    location: str | None
    attendees: list[str]
    link: str


class GoogleCalendarService:
    """Service for Google Calendar operations.
    
    Provides methods for:
    - Creating events
    - Checking availability
    - Listing upcoming events
    """
    
    def __init__(self, credentials: Credentials):
        """Initialize with Google OAuth credentials."""
        self.credentials = credentials
        self._service: Resource | None = None
    
    @property
    def service(self) -> Resource:
        """Lazy-load Calendar API service."""
        if self._service is None:
            self._service = build("calendar", "v3", credentials=self.credentials)
        return self._service
    
    def list_upcoming_events(
        self,
        max_results: int = 10,
        calendar_id: str = "primary",
    ) -> list[CalendarEvent]:
        """List upcoming events.
        
        Args:
            max_results: Maximum number of events.
            calendar_id: Calendar to query (default: primary).
            
        Returns:
            List of upcoming events.
        """
        now = datetime.utcnow().isoformat() + "Z"
        
        result = self.service.events().list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        
        events = []
        for item in result.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})
            
            events.append(CalendarEvent(
                id=item.get("id", ""),
                title=item.get("summary", ""),
                start=datetime.fromisoformat(
                    start.get("dateTime", start.get("date", "")).replace("Z", "+00:00")
                ),
                end=datetime.fromisoformat(
                    end.get("dateTime", end.get("date", "")).replace("Z", "+00:00")
                ),
                description=item.get("description"),
                location=item.get("location"),
                attendees=[
                    a.get("email", "") for a in item.get("attendees", [])
                ],
                link=item.get("htmlLink", ""),
            ))
        
        return events
    
    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
        send_notifications: bool = True,
        calendar_id: str = "primary",
    ) -> CalendarEvent:
        """Create a calendar event.
        
        Args:
            title: Event title.
            start: Start datetime.
            end: End datetime.
            description: Optional description.
            location: Optional location.
            attendees: Optional list of attendee emails.
            send_notifications: Whether to notify attendees.
            calendar_id: Calendar to create in.
            
        Returns:
            Created event details.
        """
        event_body: dict[str, Any] = {
            "summary": title,
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": "UTC",
            },
        }
        
        if description:
            event_body["description"] = description
        if location:
            event_body["location"] = location
        if attendees:
            event_body["attendees"] = [{"email": email} for email in attendees]
        
        result = self.service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            sendUpdates="all" if send_notifications else "none",
        ).execute()
        
        return CalendarEvent(
            id=result.get("id", ""),
            title=result.get("summary", ""),
            start=start,
            end=end,
            description=description,
            location=location,
            attendees=attendees or [],
            link=result.get("htmlLink", ""),
        )
    
    def check_availability(
        self,
        start: datetime,
        end: datetime,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Check if a time slot is available.
        
        Args:
            start: Start of time range.
            end: End of time range.
            calendar_id: Calendar to check.
            
        Returns:
            Dict with availability status and conflicts.
        """
        result = self.service.freebusy().query(
            body={
                "timeMin": start.isoformat() + "Z",
                "timeMax": end.isoformat() + "Z",
                "items": [{"id": calendar_id}],
            }
        ).execute()
        
        busy_times = result.get("calendars", {}).get(calendar_id, {}).get("busy", [])
        
        return {
            "available": len(busy_times) == 0,
            "conflicts": [
                {
                    "start": b.get("start"),
                    "end": b.get("end"),
                }
                for b in busy_times
            ],
        }
    
    def schedule_meeting(
        self,
        title: str,
        duration_minutes: int,
        attendees: list[str],
        preferred_start: datetime | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Schedule a meeting, finding available time if needed.
        
        Args:
            title: Meeting title.
            duration_minutes: Duration in minutes.
            attendees: List of attendee emails.
            preferred_start: Preferred start time (defaults to next hour).
            description: Optional description.
            
        Returns:
            Created event or availability info.
        """
        if preferred_start is None:
            # Default to next hour
            now = datetime.utcnow()
            preferred_start = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        end = preferred_start + timedelta(minutes=duration_minutes)
        
        # Check availability
        availability = self.check_availability(preferred_start, end)
        
        if availability["available"]:
            event = self.create_event(
                title=title,
                start=preferred_start,
                end=end,
                description=description,
                attendees=attendees,
            )
            return {
                "status": "success",
                "message": f"Meeting scheduled for {preferred_start.strftime('%B %d at %H:%M UTC')}",
                "event": {
                    "id": event.id,
                    "title": event.title,
                    "start": event.start.isoformat(),
                    "end": event.end.isoformat(),
                    "link": event.link,
                },
            }
        else:
            return {
                "status": "conflict",
                "message": "Time slot is busy",
                "conflicts": availability["conflicts"],
                "suggestion": "Try a different time or check calendar for available slots",
            }


def get_calendar_service(credentials: Credentials) -> GoogleCalendarService:
    """Get Calendar service instance."""
    return GoogleCalendarService(credentials)
