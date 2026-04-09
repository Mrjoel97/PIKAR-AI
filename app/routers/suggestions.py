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
from app.services.workflow_discovery_service import (
    ContentTemplate,
    WorkflowMatch,
    get_content_templates,
    search_workflows_by_intent,
)

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


@router.get("/workflows", response_model=list[WorkflowMatch])
async def workflow_search_endpoint(
    query: str = Query(..., description="Natural-language description of desired workflow"),
    _user_id: str = Depends(get_current_user_id),
) -> list[WorkflowMatch]:
    """Search workflows by natural-language intent.

    Returns up to 5 scored workflow matches based on keyword
    and substring overlap with available workflow templates.
    """
    return await search_workflows_by_intent(query)


@router.get("/templates", response_model=list[ContentTemplate])
async def content_templates_endpoint(
    category: str | None = Query(
        None,
        description="Filter templates by category",
    ),
    _user_id: str = Depends(get_current_user_id),
) -> list[ContentTemplate]:
    """Return browsable content templates, optionally filtered by category."""
    return await get_content_templates(category=category)
