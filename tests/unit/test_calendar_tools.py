# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for extended calendar tools.

Tests for:
- GoogleCalendarService.get_freebusy() and find_free_slots()
- find_free_slots tool
- get_meeting_context tool
- suggest_followup_meeting tool
- detect_calendar_patterns tool
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool_context(token: str = "fake-token") -> MagicMock:
    """Return a minimal mock tool_context with google token state."""
    ctx = MagicMock()
    ctx.state = {
        "google_provider_token": token,
        "google_refresh_token": "fake-refresh",
    }
    return ctx


def _dt(hour: int, minute: int = 0, day: int = 1) -> datetime:
    """Return a UTC datetime for 2026-04-{day} at HH:MM."""
    return datetime(2026, 4, day, hour, minute, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# GoogleCalendarService — get_freebusy / find_free_slots
# ---------------------------------------------------------------------------


class TestGoogleCalendarServiceFreebusy:
    """Tests for GoogleCalendarService.get_freebusy() and find_free_slots()."""

    def _make_service(self) -> "GoogleCalendarService":  # noqa: F821
        from app.integrations.google.calendar import GoogleCalendarService

        svc = GoogleCalendarService.__new__(GoogleCalendarService)
        svc._service = MagicMock()
        return svc

    def test_get_freebusy_returns_busy_intervals(self):
        """get_freebusy returns dict keyed by calendar_id with busy list."""
        from app.integrations.google.calendar import GoogleCalendarService

        svc = self._make_service()
        freebusy_response = {
            "calendars": {
                "primary": {
                    "busy": [
                        {"start": "2026-04-01T10:00:00Z", "end": "2026-04-01T11:00:00Z"},
                    ]
                }
            }
        }
        svc.service.freebusy().query().execute.return_value = freebusy_response

        result = svc.get_freebusy(
            start=_dt(9), end=_dt(17), calendar_ids=["primary"]
        )

        assert "primary" in result
        assert len(result["primary"]) == 1
        assert result["primary"][0]["start"] == "2026-04-01T10:00:00Z"

    def test_find_free_slots_returns_available_windows(self):
        """find_free_slots returns slots between busy intervals."""
        svc = self._make_service()
        # Busy 10-11
        freebusy_response = {
            "calendars": {
                "primary": {
                    "busy": [
                        {"start": "2026-04-01T10:00:00Z", "end": "2026-04-01T11:00:00Z"},
                    ]
                }
            }
        }
        svc.service.freebusy().query().execute.return_value = freebusy_response

        slots = svc.find_free_slots(
            start=_dt(9), end=_dt(17), duration_minutes=30
        )

        assert len(slots) > 0
        for slot in slots:
            assert "start" in slot
            assert "end" in slot
            assert "duration_minutes" in slot
            assert slot["duration_minutes"] == 30

    def test_find_free_slots_all_free_when_no_busy(self):
        """find_free_slots returns slots when no busy intervals exist."""
        svc = self._make_service()
        freebusy_response = {"calendars": {"primary": {"busy": []}}}
        svc.service.freebusy().query().execute.return_value = freebusy_response

        slots = svc.find_free_slots(start=_dt(9), end=_dt(17), duration_minutes=30)

        assert len(slots) > 0

    def test_find_free_slots_empty_when_fully_booked(self):
        """find_free_slots returns empty list when all business hours are busy."""
        svc = self._make_service()
        # Busy the entire day 9am-6pm
        freebusy_response = {
            "calendars": {
                "primary": {
                    "busy": [
                        {"start": "2026-04-01T09:00:00Z", "end": "2026-04-01T18:00:00Z"},
                    ]
                }
            }
        }
        svc.service.freebusy().query().execute.return_value = freebusy_response

        slots = svc.find_free_slots(start=_dt(9), end=_dt(18), duration_minutes=30)

        assert slots == []

    def test_find_free_slots_capped_at_ten(self):
        """find_free_slots returns at most 10 slots."""
        svc = self._make_service()
        freebusy_response = {"calendars": {"primary": {"busy": []}}}
        svc.service.freebusy().query().execute.return_value = freebusy_response

        # Large window: 9am-6pm = 9 hours = 18 x 30min slots, capped at 10
        slots = svc.find_free_slots(start=_dt(9), end=_dt(18), duration_minutes=30)

        assert len(slots) <= 10

    def test_get_freebusy_defaults_to_primary(self):
        """get_freebusy uses primary calendar when calendar_ids is None."""
        svc = self._make_service()
        freebusy_response = {"calendars": {"primary": {"busy": []}}}
        svc.service.freebusy().query().execute.return_value = freebusy_response

        result = svc.get_freebusy(start=_dt(9), end=_dt(17))

        assert "primary" in result


# ---------------------------------------------------------------------------
# find_free_slots tool
# ---------------------------------------------------------------------------


class TestFindFreeSlotsTool:
    """Tests for the find_free_slots agent tool function."""

    @patch("app.agents.tools.calendar_tool._get_calendar_service")
    def test_find_free_slots_returns_slots(self, mock_get_svc):
        """find_free_slots tool returns slots with note about external attendees."""
        from app.agents.tools.calendar_tool import find_free_slots

        mock_svc = MagicMock()
        mock_svc.find_free_slots.return_value = [
            {
                "start": "2026-04-06T09:00:00+00:00",
                "end": "2026-04-06T09:30:00+00:00",
                "duration_minutes": 30,
            }
        ]
        mock_get_svc.return_value = mock_svc

        ctx = _make_tool_context()
        result = find_free_slots(ctx, date="2026-04-06", duration_minutes=30)

        assert result["status"] == "success"
        assert "slots" in result
        assert len(result["slots"]) == 1
        assert "note" in result
        assert "YOUR calendar" in result["note"]

    @patch("app.agents.tools.calendar_tool._get_calendar_service")
    def test_find_free_slots_auth_error(self, mock_get_svc):
        """find_free_slots returns auth error when no token."""
        from app.agents.tools.calendar_tool import find_free_slots

        mock_get_svc.side_effect = ValueError("Google authentication required")

        ctx = _make_tool_context(token="")
        result = find_free_slots(ctx, date="2026-04-06")

        assert result["status"] == "error"
        assert result.get("auth_required") is True


# ---------------------------------------------------------------------------
# get_meeting_context tool
# ---------------------------------------------------------------------------


class TestGetMeetingContext:
    """Tests for the get_meeting_context agent tool function."""

    @pytest.mark.asyncio
    @patch("app.agents.tools.calendar_tool._get_calendar_service")
    async def test_get_meeting_context_enriches_meetings(self, mock_get_svc):
        """get_meeting_context returns meetings with crm_context and vault_context keys."""
        from app.agents.tools.calendar_tool import get_meeting_context
        from app.integrations.google.calendar import CalendarEvent

        # Upcoming meeting in 1 hour
        now = datetime.now(timezone.utc)
        event = CalendarEvent(
            id="evt-1",
            title="Sales call with Acme",
            start=now + timedelta(hours=1),
            end=now + timedelta(hours=2),
            description=None,
            location=None,
            attendees=["alice@acme.com"],
            link="https://calendar.google.com/event/1",
        )

        mock_svc = MagicMock()
        mock_svc.list_upcoming_events.return_value = [event]
        mock_get_svc.return_value = mock_svc

        # search_knowledge is lazily imported inside the function body.
        # Patch it at the source module level.
        mock_search_knowledge = AsyncMock(return_value={"results": []})

        with (
            patch(
                "app.agents.tools.calendar_tool.asyncio.to_thread",
                new_callable=AsyncMock,
            ) as mock_thread,
            patch(
                "app.rag.knowledge_vault.search_knowledge",
                mock_search_knowledge,
            ),
        ):
            mock_thread.return_value = []  # No CRM contacts or tasks found

            ctx = _make_tool_context()
            result = await get_meeting_context(ctx, hours_ahead=4)

        assert result["status"] == "success"
        assert "meetings" in result
        assert len(result["meetings"]) == 1
        meeting = result["meetings"][0]
        assert "crm_context" in meeting
        assert "vault_context" in meeting

    @pytest.mark.asyncio
    @patch("app.agents.tools.calendar_tool._get_calendar_service")
    async def test_get_meeting_context_empty_when_no_meetings(self, mock_get_svc):
        """get_meeting_context returns empty meetings list when no upcoming events."""
        from app.agents.tools.calendar_tool import get_meeting_context

        mock_svc = MagicMock()
        mock_svc.list_upcoming_events.return_value = []
        mock_get_svc.return_value = mock_svc

        ctx = _make_tool_context()
        result = await get_meeting_context(ctx, hours_ahead=4)

        assert result["status"] == "success"
        assert result["meetings"] == []

    @pytest.mark.asyncio
    @patch("app.agents.tools.calendar_tool._get_calendar_service")
    async def test_get_meeting_context_auth_error(self, mock_get_svc):
        """get_meeting_context returns auth error dict on ValueError."""
        from app.agents.tools.calendar_tool import get_meeting_context

        mock_get_svc.side_effect = ValueError("Google authentication required")

        ctx = _make_tool_context(token="")
        result = await get_meeting_context(ctx, hours_ahead=4)

        assert result["status"] == "error"
        assert result.get("auth_required") is True


# ---------------------------------------------------------------------------
# suggest_followup_meeting tool
# ---------------------------------------------------------------------------


class TestSuggestFollowupMeeting:
    """Tests for the suggest_followup_meeting agent tool function."""

    @patch("app.agents.tools.calendar_tool._get_calendar_service")
    def test_suggest_followup_returns_suggestion_dict(self, mock_get_svc):
        """suggest_followup_meeting returns suggestion without creating event."""
        from app.agents.tools.calendar_tool import suggest_followup_meeting

        mock_svc = MagicMock()
        mock_svc.find_free_slots.return_value = [
            {
                "start": "2026-04-08T09:00:00+00:00",
                "end": "2026-04-08T09:30:00+00:00",
                "duration_minutes": 30,
            }
        ]
        mock_get_svc.return_value = mock_svc

        ctx = _make_tool_context()
        result = suggest_followup_meeting(
            ctx,
            meeting_title="Q1 Review",
            attendee_emails=["bob@example.com"],
            days_ahead=5,
            duration_minutes=30,
        )

        assert result["status"] == "success"
        assert "suggestion" in result
        suggestion = result["suggestion"]
        assert "proposed_time" in suggestion
        assert "Follow-up: Q1 Review" in suggestion["title"]
        assert "bob@example.com" in suggestion["attendees"]
        # Most critical: create_event must NOT have been called
        mock_svc.create_event.assert_not_called()

    @patch("app.agents.tools.calendar_tool._get_calendar_service")
    def test_suggest_followup_respects_freebusy(self, mock_get_svc):
        """suggest_followup_meeting uses free/busy to pick optimal time."""
        from app.agents.tools.calendar_tool import suggest_followup_meeting

        # Service returns two slots; tool should pick earliest (morning pref)
        mock_svc = MagicMock()
        mock_svc.find_free_slots.return_value = [
            {
                "start": "2026-04-08T09:00:00+00:00",
                "end": "2026-04-08T09:30:00+00:00",
                "duration_minutes": 30,
            },
            {
                "start": "2026-04-08T14:00:00+00:00",
                "end": "2026-04-08T14:30:00+00:00",
                "duration_minutes": 30,
            },
        ]
        mock_get_svc.return_value = mock_svc

        ctx = _make_tool_context()
        result = suggest_followup_meeting(
            ctx,
            meeting_title="Demo",
            attendee_emails=["alice@example.com"],
        )

        assert result["status"] == "success"
        # Should pick morning slot (09:00) over afternoon
        assert "09:00" in result["suggestion"]["proposed_time"] or "T09:" in result["suggestion"]["proposed_time"]

    @patch("app.agents.tools.calendar_tool._get_calendar_service")
    def test_suggest_followup_no_slots_available(self, mock_get_svc):
        """suggest_followup_meeting returns message when no slots are free."""
        from app.agents.tools.calendar_tool import suggest_followup_meeting

        mock_svc = MagicMock()
        mock_svc.find_free_slots.return_value = []
        mock_get_svc.return_value = mock_svc

        ctx = _make_tool_context()
        result = suggest_followup_meeting(
            ctx,
            meeting_title="Strategy Review",
            attendee_emails=["ceo@corp.com"],
        )

        assert result["status"] in ("success", "no_slots")
        # Still must not call create_event
        mock_svc.create_event.assert_not_called()


# ---------------------------------------------------------------------------
# detect_calendar_patterns tool
# ---------------------------------------------------------------------------


class TestDetectCalendarPatterns:
    """Tests for the detect_calendar_patterns agent tool function."""

    @patch("app.agents.tools.calendar_tool._get_calendar_service")
    def test_detect_patterns_identifies_weekly_meetings(self, mock_get_svc):
        """detect_calendar_patterns identifies weekly recurring meetings."""
        from app.integrations.google.calendar import CalendarEvent
        from app.agents.tools.calendar_tool import detect_calendar_patterns

        # Build 5 occurrences of "Weekly Standup" at Mon 9am, one week apart
        events = []
        base = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)  # Monday
        for i in range(5):
            dt = base + timedelta(weeks=i)
            events.append(
                CalendarEvent(
                    id=f"evt-{i}",
                    title="Weekly Standup",
                    start=dt,
                    end=dt + timedelta(hours=1),
                    description=None,
                    location=None,
                    attendees=[],
                    link="",
                )
            )

        mock_svc = MagicMock()
        # list_upcoming_events used for recent past (days_back)
        mock_svc.list_upcoming_events.return_value = events
        mock_get_svc.return_value = mock_svc

        ctx = _make_tool_context()
        result = detect_calendar_patterns(ctx, days_back=30)

        assert result["status"] == "success"
        assert "patterns" in result
        # Should find at least one pattern
        assert len(result["patterns"]) >= 1
        titles = [p["title"] for p in result["patterns"]]
        assert any("standup" in t.lower() or "Standup" in t for t in titles)

    @patch("app.agents.tools.calendar_tool._get_calendar_service")
    def test_detect_patterns_handles_no_patterns(self, mock_get_svc):
        """detect_calendar_patterns returns empty patterns list gracefully."""
        from app.integrations.google.calendar import CalendarEvent
        from app.agents.tools.calendar_tool import detect_calendar_patterns

        # Unique one-off events — no recurring pattern
        events = [
            CalendarEvent(
                id=f"evt-{i}",
                title=f"Unique Event {i}",
                start=datetime(2026, 3, i + 1, 10, 0, tzinfo=timezone.utc),
                end=datetime(2026, 3, i + 1, 11, 0, tzinfo=timezone.utc),
                description=None,
                location=None,
                attendees=[],
                link="",
            )
            for i in range(3)
        ]

        mock_svc = MagicMock()
        mock_svc.list_upcoming_events.return_value = events
        mock_get_svc.return_value = mock_svc

        ctx = _make_tool_context()
        result = detect_calendar_patterns(ctx, days_back=30)

        assert result["status"] == "success"
        assert result["patterns"] == []

    @patch("app.agents.tools.calendar_tool._get_calendar_service")
    def test_detect_patterns_auth_error(self, mock_get_svc):
        """detect_calendar_patterns returns auth error when not authenticated."""
        from app.agents.tools.calendar_tool import detect_calendar_patterns

        mock_get_svc.side_effect = ValueError("Google authentication required")

        ctx = _make_tool_context(token="")
        result = detect_calendar_patterns(ctx, days_back=30)

        assert result["status"] == "error"
        assert result.get("auth_required") is True


# ---------------------------------------------------------------------------
# CALENDAR_TOOLS list
# ---------------------------------------------------------------------------


class TestCalendarToolsList:
    """Tests that CALENDAR_TOOLS exports all 8 tools."""

    def test_calendar_tools_has_nine_entries(self):
        """CALENDAR_TOOLS list must contain 9 tool functions (8 original + generate_recurring_tasks)."""
        from app.agents.tools.calendar_tool import CALENDAR_TOOLS

        assert len(CALENDAR_TOOLS) == 9

    def test_calendar_tools_includes_new_tools(self):
        """CALENDAR_TOOLS must include all 4 new tools by name."""
        from app.agents.tools.calendar_tool import (
            CALENDAR_TOOLS,
            detect_calendar_patterns,
            find_free_slots,
            get_meeting_context,
            suggest_followup_meeting,
        )

        tool_names = [t.__name__ for t in CALENDAR_TOOLS]
        assert "find_free_slots" in tool_names
        assert "get_meeting_context" in tool_names
        assert "suggest_followup_meeting" in tool_names
        assert "detect_calendar_patterns" in tool_names

    def test_calendar_tools_includes_existing_tools(self):
        """CALENDAR_TOOLS must still include the original 4 tools."""
        from app.agents.tools.calendar_tool import CALENDAR_TOOLS

        tool_names = [t.__name__ for t in CALENDAR_TOOLS]
        assert "list_events" in tool_names
        assert "create_calendar_event" in tool_names
        assert "check_availability" in tool_names
        assert "schedule_meeting" in tool_names


# ---------------------------------------------------------------------------
# generate_recurring_tasks
# ---------------------------------------------------------------------------


class TestGenerateRecurringTasks:
    """Tests for generate_recurring_tasks — task creation from calendar patterns."""

    def _make_ctx(self) -> MagicMock:
        """Return a minimal mock tool_context with google token state."""
        return _make_tool_context()

    def _two_patterns(self) -> list[dict]:
        """Return two sample detected patterns."""
        return [
            {
                "title": "Weekly Sales Sync",
                "frequency": "weekly",
                "typical_day": "Monday",
                "typical_time": "10:00",
                "occurrences": 4,
            },
            {
                "title": "Daily Standup",
                "frequency": "daily",
                "typical_day": "weekday",
                "typical_time": "09:00",
                "occurrences": 20,
            },
        ]

    @pytest.mark.asyncio
    async def test_generate_recurring_tasks_creates_tasks(self):
        """Two detected patterns should produce two synced_task inserts."""
        patterns_result = {"status": "success", "patterns": self._two_patterns()}

        mock_table = MagicMock()
        mock_insert = MagicMock()
        mock_insert.execute = MagicMock(return_value=MagicMock(data=[{"id": "task-1"}]))
        mock_table.insert = MagicMock(return_value=mock_insert)

        mock_client = MagicMock()
        mock_client.table = MagicMock(return_value=mock_table)

        mock_admin = MagicMock()
        mock_admin.client = mock_client

        ctx = self._make_ctx()

        with (
            patch(
                "app.agents.tools.calendar_tool.detect_calendar_patterns",
                return_value=patterns_result,
            ),
            patch(
                "app.agents.tools.calendar_tool._get_user_id",
                return_value="user-123",
            ),
        ):
            # Patch AdminService inside calendar_tool
            with patch.dict(
                "sys.modules",
                {"app.services.base_service": MagicMock(AdminService=MagicMock(return_value=mock_admin))},
            ):
                from app.agents.tools import calendar_tool as ct

                ct._admin_service_module = None  # force re-import
                # Patch lazily at the function level
                with patch("app.agents.tools.calendar_tool.AdminService", return_value=mock_admin, create=True):
                    from app.agents.tools.calendar_tool import generate_recurring_tasks

                    result = await generate_recurring_tasks(ctx)

        assert result["status"] == "success"
        assert result["patterns_found"] == 2
        assert len(result["tasks_created"]) == 2
        # Verify task titles contain "Recurring:"
        titles = [t["title"] for t in result["tasks_created"]]
        assert any("Recurring: Weekly Sales Sync" in t for t in titles)
        assert any("Recurring: Daily Standup" in t for t in titles)

    @pytest.mark.asyncio
    async def test_generate_recurring_tasks_no_patterns(self):
        """Empty pattern list produces no inserts and empty tasks_created."""
        ctx = self._make_ctx()

        with patch(
            "app.agents.tools.calendar_tool.detect_calendar_patterns",
            return_value={"status": "success", "patterns": []},
        ):
            from app.agents.tools.calendar_tool import generate_recurring_tasks

            result = await generate_recurring_tasks(ctx)

        assert result["status"] == "success"
        assert result["tasks_created"] == []
        assert result["patterns_found"] == 0

    def test_generate_recurring_tasks_in_calendar_tools(self):
        """generate_recurring_tasks must appear in the CALENDAR_TOOLS export."""
        from app.agents.tools.calendar_tool import CALENDAR_TOOLS, generate_recurring_tasks

        assert generate_recurring_tasks in CALENDAR_TOOLS
