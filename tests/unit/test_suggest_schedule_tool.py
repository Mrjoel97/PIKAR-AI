# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Unit tests for the suggest_and_schedule_content tool.

Tests cover suggestion mode, scheduling mode, platform-specific timing,
default timing for unknown platforms, and content type mapping.
"""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_suggest_mode_returns_suggestion_without_scheduling():
    """Test 1: schedule=False returns suggestion only, no calendar entry created."""
    from app.agents.content.tools import suggest_and_schedule_content

    with patch(
        "app.agents.content.tools._compute_optimal_timing"
    ) as mock_timing:
        mock_timing.return_value = ("2026-04-15", "09:00", "Instagram posts perform best Mon-Fri at 9am")

        result = await suggest_and_schedule_content(
            title="Spring Launch Post",
            content_type="social_post",
            platform="instagram",
            description="Spring collection announcement",
            schedule=False,
        )

    assert result["success"] is True
    assert result["mode"] == "suggestion"
    assert result["optimal_date"] == "2026-04-15"
    assert result["optimal_time"] == "09:00"
    assert "reasoning" in result
    assert "message" in result
    assert "schedule it" in result["message"].lower() or "confirm" in result["message"].lower()


@pytest.mark.asyncio
async def test_schedule_mode_calls_calendar_service():
    """Test 2: schedule=True calls ContentCalendarService.schedule_content."""
    from app.agents.content.tools import suggest_and_schedule_content

    mock_calendar_item = {"id": "cal-123", "title": "Spring Launch Post", "status": "planned"}

    with (
        patch(
            "app.agents.content.tools._compute_optimal_timing"
        ) as mock_timing,
        patch(
            "app.services.content_calendar_service.ContentCalendarService"
        ) as MockCalendarService,
        patch(
            "app.services.request_context.get_current_user_id",
            return_value="user-abc",
        ),
    ):
        mock_timing.return_value = ("2026-04-15", "09:00", "Optimal for Instagram")
        mock_instance = MockCalendarService.return_value
        mock_instance.schedule_content = AsyncMock(return_value=mock_calendar_item)

        result = await suggest_and_schedule_content(
            title="Spring Launch Post",
            content_type="social_post",
            platform="instagram",
            description="Spring collection announcement",
            schedule=True,
        )

    assert result["success"] is True
    assert result["mode"] == "scheduled"
    assert result["calendar_item"] == mock_calendar_item
    assert "Spring Launch Post" in result["message"]
    mock_instance.schedule_content.assert_called_once()
    call_kwargs = mock_instance.schedule_content.call_args
    assert call_kwargs[1]["content_type"] == "social"
    assert call_kwargs[1]["platform"] == "instagram"


@pytest.mark.asyncio
async def test_instagram_uses_platform_guidelines():
    """Test 3: Instagram returns times from PLATFORM_GUIDELINES."""
    from app.agents.content.tools import _compute_optimal_timing

    with patch("app.agents.content.tools._today") as mock_today:
        # Wednesday 2026-04-15
        mock_today.return_value = date(2026, 4, 15)
        opt_date, opt_time, reasoning = _compute_optimal_timing("instagram")

    # Instagram guidelines: Mon-Fri 9am, 12pm, 3pm
    assert opt_time == "09:00"
    assert "instagram" in reasoning.lower() or "mon-fri" in reasoning.lower()
    # Should be a weekday
    parsed = datetime.strptime(opt_date, "%Y-%m-%d")
    assert parsed.weekday() < 5  # Mon-Fri


@pytest.mark.asyncio
async def test_linkedin_returns_business_hour_times():
    """Test 4: LinkedIn returns business-hour times from PLATFORM_GUIDELINES."""
    from app.agents.content.tools import _compute_optimal_timing

    with patch("app.agents.content.tools._today") as mock_today:
        # Monday 2026-04-13
        mock_today.return_value = date(2026, 4, 13)
        opt_date, opt_time, reasoning = _compute_optimal_timing("linkedin")

    # LinkedIn guidelines: Tue-Thu 8am-10am, 12pm
    assert opt_time == "09:00"
    assert "linkedin" in reasoning.lower() or "tue" in reasoning.lower()
    parsed = datetime.strptime(opt_date, "%Y-%m-%d")
    # Should be Tue-Thu (weekday 1, 2, or 3)
    assert parsed.weekday() in (1, 2, 3)


@pytest.mark.asyncio
async def test_unknown_platform_defaults_to_weekday():
    """Test 5: Unknown platform or None returns next weekday at 10:00."""
    from app.agents.content.tools import _compute_optimal_timing

    with patch("app.agents.content.tools._today") as mock_today:
        # Saturday 2026-04-18
        mock_today.return_value = date(2026, 4, 18)
        opt_date, opt_time, reasoning = _compute_optimal_timing(None)

    assert opt_time == "10:00"
    parsed = datetime.strptime(opt_date, "%Y-%m-%d")
    assert parsed.weekday() < 5  # Must be a weekday
    assert "default" in reasoning.lower() or "general" in reasoning.lower()


def test_content_type_mapping():
    """Test 6: Content type mapping works correctly."""
    from app.agents.content.tools import _map_content_type

    assert _map_content_type("social_post") == "social"
    assert _map_content_type("blog_intro") == "blog"
    assert _map_content_type("email") == "email"
    assert _map_content_type("caption") == "social"
    assert _map_content_type("headline") == "ad"
    assert _map_content_type("tagline") == "ad"
    assert _map_content_type("video") == "video"
    assert _map_content_type("unknown_thing") == "other"
