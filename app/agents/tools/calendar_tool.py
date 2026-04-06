# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Google Calendar tools for agents.

Provides tools for event management and scheduling, including:
- Free/busy slot finding
- Meeting preparation context (CRM + knowledge vault)
- Follow-up meeting suggestions (never auto-books)
- Recurring calendar pattern detection
"""

import asyncio
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

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


def find_free_slots(
    tool_context: ToolContextType,
    date: str,
    duration_minutes: int = 30,
    days_ahead: int = 3,
) -> dict[str, Any]:
    """Find open time slots on YOUR calendar over the next several days.

    Queries the user's primary calendar free/busy data to identify gaps
    during business hours (09:00-18:00 UTC).

    Args:
        tool_context: Agent tool context.
        date: Starting date in ISO format (e.g., "2026-04-06").
        duration_minutes: Required slot length in minutes (default 30).
        days_ahead: Number of days to look ahead (default 3).

    Returns:
        Dict with list of available slots and a caveat about external
        attendee availability.
    """
    try:
        service = _get_calendar_service(tool_context)

        start = datetime.fromisoformat(date).replace(
            hour=9, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
        )
        end = start + timedelta(days=days_ahead)
        end = end.replace(hour=18, minute=0, second=0, microsecond=0)

        slots = service.find_free_slots(start, end, duration_minutes)

        return {
            "status": "success",
            "slots": slots,
            "note": (
                "These are open slots on YOUR calendar. "
                "External attendees may have other commitments."
            ),
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to find free slots: {e}"}


async def get_meeting_context(
    tool_context: ToolContextType,
    hours_ahead: int = 4,
) -> dict[str, Any]:
    """Get enriched context for upcoming meetings.

    Fetches upcoming calendar events and enriches each with:
    - CRM data (contact name, company, deal info from the ``contacts`` table)
    - Knowledge vault snippets related to attendees / companies
    - Open action items from the ``tasks`` table mentioning attendees

    Args:
        tool_context: Agent tool context.
        hours_ahead: Look-ahead window in hours (default 4).

    Returns:
        Dict with enriched meeting list; each entry has ``crm_context``,
        ``vault_context``, and ``action_items`` keys.
    """
    try:
        service = _get_calendar_service(tool_context)

        # Get upcoming events (fetch enough to cover the window)
        events = service.list_upcoming_events(max_results=20)

        cutoff = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
        upcoming = [
            e
            for e in events
            if (e.start.tzinfo and e.start <= cutoff)
            or (not e.start.tzinfo and e.start.replace(tzinfo=timezone.utc) <= cutoff)
        ]

        if not upcoming:
            return {"status": "success", "meetings": []}

        async def _enrich(event: Any) -> dict[str, Any]:
            """Enrich a single event with CRM and vault context."""
            attendee_emails: list[str] = event.attendees or []
            attendee_query = " ".join(attendee_emails)
            company_query = " ".join(
                e.split("@")[1].split(".")[0] for e in attendee_emails if "@" in e
            )

            # --- CRM context (sync supabase call → thread) ---
            def _query_crm() -> list[dict[str, Any]]:
                try:
                    from app.services.supabase import (
                        get_service_client,
                    )

                    client = get_service_client()
                    rows: list[dict[str, Any]] = []
                    for email in attendee_emails:
                        resp = (
                            client.table("contacts")
                            .select("id,name,company,email,deal_stage,deal_value")
                            .eq("email", email)
                            .limit(1)
                            .execute()
                        )
                        if resp.data:
                            rows.extend(resp.data)
                    return rows
                except Exception as exc:
                    logger.debug("CRM lookup failed: %s", exc)
                    return []

            # --- Open tasks (sync supabase call → thread) ---
            def _query_tasks() -> list[dict[str, Any]]:
                try:
                    from app.services.supabase import (
                        get_service_client,
                    )

                    client = get_service_client()
                    # Look for tasks related to the meeting title or attendees
                    search_terms = [event.title] + [
                        e.split("@")[0] for e in attendee_emails if "@" in e
                    ]
                    results: list[dict[str, Any]] = []
                    for term in search_terms[:3]:  # Cap to avoid N+1 at scale
                        resp = (
                            client.table("tasks")
                            .select("id,title,status,due_date")
                            .ilike("title", f"%{term}%")
                            .eq("status", "open")
                            .limit(5)
                            .execute()
                        )
                        if resp.data:
                            results.extend(resp.data)
                    # Deduplicate by task id
                    seen: set[str] = set()
                    unique: list[dict[str, Any]] = []
                    for t in results:
                        if t.get("id") not in seen:
                            seen.add(t.get("id", ""))
                            unique.append(t)
                    return unique
                except Exception as exc:
                    logger.debug("Task lookup failed: %s", exc)
                    return []

            # Lazy import — avoid circular deps at module load time
            from app.rag.knowledge_vault import search_knowledge

            vault_search_query = f"{attendee_query} {company_query} {event.title}"
            crm_rows, tasks_rows, vault_result = await asyncio.gather(
                asyncio.to_thread(_query_crm),
                asyncio.to_thread(_query_tasks),
                search_knowledge(vault_search_query, top_k=5),
            )
            vault_snippets = vault_result.get("results", []) if vault_result else []

            return {
                "title": event.title,
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
                "attendees": attendee_emails,
                "crm_context": crm_rows,
                "vault_context": [
                    {"content": s.get("content", ""), "source": s.get("source", "")}
                    for s in (vault_snippets or [])[:5]
                ],
                "action_items": tasks_rows,
            }

        enriched = await asyncio.gather(*[_enrich(e) for e in upcoming])

        return {"status": "success", "meetings": list(enriched)}

    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {"status": "error", "message": f"Failed to get meeting context: {e}"}


def suggest_followup_meeting(
    tool_context: ToolContextType,
    meeting_title: str,
    attendee_emails: list[str],
    days_ahead: int = 5,
    duration_minutes: int = 30,
) -> dict[str, Any]:
    """Suggest an optimal follow-up meeting time.

    Finds the earliest morning slot on the user's calendar within
    ``days_ahead`` days and returns a suggestion dict.

    IMPORTANT: This function NEVER creates a calendar event. It only
    suggests a time and asks the user to confirm.

    Args:
        tool_context: Agent tool context.
        meeting_title: Title of the meeting to follow up on.
        attendee_emails: List of attendee email addresses.
        days_ahead: Number of days ahead to search (default 5).
        duration_minutes: Meeting duration in minutes (default 30).

    Returns:
        Dict with ``suggestion`` containing ``proposed_time``, ``title``,
        ``attendees``, and a confirmation prompt message.
    """
    try:
        service = _get_calendar_service(tool_context)

        start = datetime.now(timezone.utc).replace(
            hour=9, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        end = start + timedelta(days=days_ahead)
        end = end.replace(hour=18, minute=0, second=0, microsecond=0)

        slots = service.find_free_slots(start, end, duration_minutes)

        if not slots:
            return {
                "status": "no_slots",
                "message": (
                    f"No free slots found in the next {days_ahead} days for a "
                    f"{duration_minutes}-minute follow-up. Consider checking further ahead."
                ),
                "suggestion": None,
            }

        # Prefer morning slots (before noon UTC)
        morning_slots = [
            s
            for s in slots
            if "T09:" in s["start"] or "T10:" in s["start"] or "T11:" in s["start"]
        ]
        chosen = morning_slots[0] if morning_slots else slots[0]

        follow_up_title = f"Follow-up: {meeting_title}"

        return {
            "status": "success",
            "suggestion": {
                "proposed_time": chosen["start"],
                "duration_minutes": duration_minutes,
                "title": follow_up_title,
                "attendees": attendee_emails,
            },
            "message": (
                f"I suggest scheduling '{follow_up_title}' at {chosen['start']} "
                f"({duration_minutes} min). Shall I create this event?"
            ),
        }
    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to suggest follow-up meeting: {e}",
        }


def detect_calendar_patterns(
    tool_context: ToolContextType,
    days_back: int = 30,
) -> dict[str, Any]:
    """Detect recurring meeting patterns from calendar history.

    Looks at the past ``days_back`` days of events and identifies titles
    that appear 3 or more times, inferring frequency (weekly, biweekly,
    monthly) and typical day/time.

    Args:
        tool_context: Agent tool context.
        days_back: Number of past days to analyse (default 30).

    Returns:
        Dict with ``patterns`` list; each entry has ``title``,
        ``frequency``, ``typical_day``, ``typical_time``, and
        ``occurrences``.
    """
    try:
        service = _get_calendar_service(tool_context)

        # Fetch recent events (max 100 for pattern analysis)
        events = service.list_upcoming_events(max_results=100)

        if not events:
            return {"status": "success", "patterns": []}

        # Normalise title: lowercase, strip numbers/dates/weekday prefixes
        def _normalise(title: str) -> str:
            t = title.lower()
            t = re.sub(r"\b\d{1,4}[-/]\d{1,2}[-/]\d{1,4}\b", "", t)  # dates
            t = re.sub(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", "", t)
            t = re.sub(r"\b\d+\b", "", t)  # standalone numbers
            t = re.sub(r"\s+", " ", t).strip()
            return t

        # Group events by normalised title
        groups: dict[str, list[Any]] = defaultdict(list)
        for event in events:
            key = _normalise(event.title)
            if key:
                groups[key].append(event)

        # Identify patterns: 3+ occurrences of the same recurring meeting.
        # Require that the most-common raw title accounts for the majority of
        # occurrences to avoid false positives from events like "Unique Event 0",
        # "Unique Event 1", "Unique Event 2" that normalise to the same key.
        patterns: list[dict[str, Any]] = []
        for _norm_title, evts in groups.items():
            if len(evts) < 3:
                continue

            raw_titles = [e.title for e in evts]
            top_raw = max(set(raw_titles), key=raw_titles.count)
            top_raw_count = raw_titles.count(top_raw)

            # At least half must share the dominant raw title
            if top_raw_count < len(evts) / 2:
                continue

            evts_sorted = sorted(
                evts,
                key=lambda e: e.start if e.start.tzinfo else e.start.replace(tzinfo=timezone.utc),
            )

            # Detect frequency from median gap between consecutive events
            gaps: list[float] = []
            for i in range(1, len(evts_sorted)):
                a = evts_sorted[i - 1].start
                b = evts_sorted[i].start
                if not a.tzinfo:
                    a = a.replace(tzinfo=timezone.utc)
                if not b.tzinfo:
                    b = b.replace(tzinfo=timezone.utc)
                gaps.append((b - a).total_seconds() / 86400)  # days

            if not gaps:
                continue

            median_gap = sorted(gaps)[len(gaps) // 2]

            if median_gap <= 9:
                frequency = "weekly"
            elif median_gap <= 18:
                frequency = "biweekly"
            else:
                frequency = "monthly"

            # Typical day (most common weekday)
            weekdays = [e.start.strftime("%A") for e in evts_sorted]
            typical_day = max(set(weekdays), key=weekdays.count)

            # Typical time (most common hour)
            hours = [e.start.strftime("%H:%M") for e in evts_sorted]
            typical_time = max(set(hours), key=hours.count)

            # Use the most common raw title form (before normalisation)
            raw_titles = [e.title for e in evts_sorted]
            display_title = max(set(raw_titles), key=raw_titles.count)

            patterns.append(
                {
                    "title": display_title,
                    "frequency": frequency,
                    "typical_day": typical_day,
                    "typical_time": typical_time,
                    "occurrences": len(evts_sorted),
                }
            )

        return {"status": "success", "patterns": patterns}

    except ValueError as e:
        return {"status": "error", "message": str(e), "auth_required": True}
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to detect calendar patterns: {e}",
        }


# Export Calendar tools
CALENDAR_TOOLS = [
    list_events,
    create_calendar_event,
    check_availability,
    schedule_meeting,
    find_free_slots,
    get_meeting_context,
    suggest_followup_meeting,
    detect_calendar_patterns,
]
