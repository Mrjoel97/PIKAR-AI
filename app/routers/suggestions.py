# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Suggestion chip endpoint for persona-aware chat prompts.

Returns personalized, time-of-day-sensitive suggestion chips
for the chat interface.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.routers.onboarding import get_current_user_id
from app.services.suggestion_service import SuggestionItem, get_suggestions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/suggestions", tags=["Suggestions"])


@router.get("", response_model=list[SuggestionItem])
async def suggestions_endpoint(
    persona: str = Query(..., description="User persona key"),
    hour: int | None = Query(
        None,
        description="Hour of day (0-23), defaults to server UTC hour",
    ),
    recent_activity: str | None = Query(
        None,
        description="Comma-separated recent activity keys",
    ),
    _user_id: str = Depends(get_current_user_id),
) -> list[SuggestionItem]:
    """Return 4-6 personalized suggestion chips.

    Suggestions are tailored to the user's persona, time of day,
    and recent activity history.
    """
    effective_hour = hour if hour is not None else datetime.now(tz=timezone.utc).hour
    activity_list = (
        [a.strip() for a in recent_activity.split(",") if a.strip()]
        if recent_activity
        else None
    )

    return await get_suggestions(
        persona=persona,
        hour=effective_hour,
        recent_activity=activity_list,
    )
