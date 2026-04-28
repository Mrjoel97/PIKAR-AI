# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Public team invite endpoints.

Provides display-safe invite metadata for the public `/invite/[token]` page
without requiring frontend runtime access to service-role secrets.
"""


import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teams", tags=["Teams Public"])


class PublicInviteDetailsResponse(BaseModel):
    """Display-safe public invite metadata."""

    id: str
    workspaceName: str
    role: str
    invitedEmail: str | None
    inviterName: str | None
    expiresAt: str
    isActive: bool


def _status_code_for_invite_error(message: str) -> int:
    normalized = message.lower()
    if "not found" in normalized:
        return 404
    if "revoked" in normalized or "accepted" in normalized or "expired" in normalized:
        return 410
    return 400


@router.get("/invites/details", response_model=PublicInviteDetailsResponse)
async def get_invite_details(
    token: str = Query(..., min_length=1, description="Invite token"),
) -> PublicInviteDetailsResponse:
    """Return public metadata for a workspace invite token."""
    try:
        service = WorkspaceService()
        details = await service.get_invite_details(token.strip())
        return PublicInviteDetailsResponse(**details)
    except ValueError as exc:
        raise HTTPException(
            status_code=_status_code_for_invite_error(str(exc)),
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("teams_public.get_invite_details error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to load invitation details.",
        ) from exc
