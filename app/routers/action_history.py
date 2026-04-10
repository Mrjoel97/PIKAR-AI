# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""REST API for querying the unified action history.

Provides a GET endpoint for the frontend to retrieve a chronological feed of
all AI-performed actions across every agent, with filtering and pagination.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.services.supabase import get_service_client
from app.services.unified_action_history_service import get_action_history_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/action-history", tags=["Action History"])
security = HTTPBearer()


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    """Verify the JWT token using Supabase and return the user_id.

    Returns:
        The user's UUID as a string (from Supabase Auth).
    """
    token = credentials.credentials
    supabase = get_service_client()
    try:
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(
                status_code=401, detail="Invalid authentication credentials"
            )
        return user.user.id
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Auth error: %s", e)
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials"
        ) from e


@router.get("/")
@limiter.limit(get_user_persona_limit)
async def get_action_history(
    request: Request,
    user_id: Annotated[str, Depends(get_current_user_id)],
    agent_name: Annotated[str | None, Query(description="Filter by agent name")] = None,
    action_type: Annotated[str | None, Query(description="Filter by action type")] = None,
    days: Annotated[int, Query(ge=1, le=365, description="Look-back period in days")] = 30,
    limit: Annotated[int, Query(ge=1, le=200, description="Max rows to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> dict[str, Any]:
    """Query the unified action history for the authenticated user.

    Returns a chronological feed of all AI-performed actions across every agent,
    with optional filtering by agent name, action type, and date range.
    """
    svc = get_action_history_service()
    actions = await svc.get_action_history(
        user_id=user_id,
        agent_name=agent_name,
        action_type=action_type,
        days=days,
        limit=limit,
        offset=offset,
    )
    return {
        "actions": actions,
        "total": len(actions),
        "filters": {
            "agent_name": agent_name,
            "action_type": action_type,
            "days": days,
        },
    }
