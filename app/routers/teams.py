# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Teams API — workspace management endpoints.

Provides REST endpoints for creating and managing team workspaces,
inviting members, and controlling member roles. All endpoints require
the "teams" feature gate (startup tier or higher).

Write endpoints (invite creation, role changes, member removal) are
additionally gated by the ``require_role("admin")`` dependency. The
accept-invite endpoint is accessible to any authenticated user because
the accepting user may not yet be a workspace member.
"""


import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.middleware.feature_gate import require_feature
from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.middleware.workspace_role import require_role
from app.routers.onboarding import get_current_user_id
from app.services.governance_service import get_governance_service
from app.services.team_analytics_service import TeamAnalyticsService
from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/teams",
    tags=["Teams"],
    dependencies=[Depends(require_feature("teams"))],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class WorkspaceResponse(BaseModel):
    """Current user's workspace details with their membership role."""

    id: str
    name: str
    slug: str | None
    owner_id: str
    role: str
    member_count: int


class MemberResponse(BaseModel):
    """A single workspace member record."""

    id: str
    user_id: str
    email: str
    display_name: str | None
    role: str
    joined_at: str


class CreateInviteRequest(BaseModel):
    """Body for creating a workspace invite link."""

    role: str = Field(default="viewer", pattern="^(editor|viewer)$")
    expires_hours: int = Field(default=168, ge=1, le=720)


class InviteResponse(BaseModel):
    """Invite link details returned after creation."""

    id: str
    token: str
    role: str
    expires_at: str
    share_url: str


class AcceptInviteRequest(BaseModel):
    """Body for accepting a workspace invite by token."""

    token: str


class UpdateRoleRequest(BaseModel):
    """Body for updating a workspace member's role."""

    role: str = Field(pattern="^(admin|editor|viewer)$")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/workspace", response_model=WorkspaceResponse)
@limiter.limit(get_user_persona_limit)
async def get_workspace(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> WorkspaceResponse:
    """Get or create the current user's workspace.

    Creates a workspace automatically if the user has none. Returns the
    workspace details along with the requesting user's membership role.

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        user_id: Authenticated user ID (injected by FastAPI).

    Returns:
        WorkspaceResponse with workspace info and the user's role.
    """
    try:
        service = WorkspaceService()
        workspace = await service.get_or_create_workspace(user_id)
        members = await service.get_workspace_members(workspace["id"])
        role = await service.get_member_role(user_id, workspace["id"])
        return WorkspaceResponse(
            id=workspace["id"],
            name=workspace["name"],
            slug=workspace.get("slug"),
            owner_id=workspace["owner_id"],
            role=role or "admin",
            member_count=len(members),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("teams.get_workspace error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to get workspace") from exc


@router.get("/members", response_model=list[MemberResponse])
@limiter.limit(get_user_persona_limit)
async def list_members(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> list[MemberResponse]:
    """List all members of the current user's workspace.

    The requesting user must be a member of the workspace. Returns an empty
    list when the user has no workspace yet.

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        user_id: Authenticated user ID (injected by FastAPI).

    Returns:
        List of MemberResponse objects for each workspace member.
    """
    try:
        service = WorkspaceService()
        workspace = await service.get_workspace_for_user(user_id)
        if workspace is None:
            return []
        members = await service.get_workspace_members(workspace["id"])
        return [
            MemberResponse(
                id=m["id"],
                user_id=m["user_id"],
                email=m.get("email") or "",
                display_name=m.get("full_name"),
                role=m["role"],
                joined_at=m["joined_at"],
            )
            for m in members
        ]
    except Exception as exc:
        logger.error("teams.list_members error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list members") from exc


@router.post("/invites", response_model=InviteResponse)
@limiter.limit(get_user_persona_limit)
async def create_invite(
    request: Request,
    body: CreateInviteRequest,
    user_id: str = Depends(get_current_user_id),
    _admin: None = Depends(require_role("admin")),
) -> InviteResponse:
    """Create a shareable invite link for the current user's workspace.

    Only workspace admins can create invite links. The generated token is
    single-use and expires after the configured number of hours (default
    168 h / 7 days).

    Args:
        request: Incoming HTTP request (base_url used to build share_url).
        body: Invite creation parameters (role, expiry hours).
        user_id: Authenticated user ID (injected by FastAPI).
        _admin: Admin role gate dependency (injected by FastAPI).

    Returns:
        InviteResponse with the token and a fully-qualified share URL.
    """
    try:
        service = WorkspaceService()
        workspace = await service.get_workspace_for_user(user_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="No workspace found")

        invite = await service.create_invite_link(
            workspace_id=workspace["id"],
            created_by=user_id,
            role=body.role,
            expires_hours=body.expires_hours,
        )
        share_url = f"{str(request.base_url).rstrip('/')}dashboard/team/join?token={invite['token']}"
        return InviteResponse(
            id=invite["id"],
            token=invite["token"],
            role=invite["role"],
            expires_at=invite["expires_at"],
            share_url=share_url,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("teams.create_invite error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create invite") from exc


@router.post("/invites/accept")
@limiter.limit(get_user_persona_limit)
async def accept_invite(
    request: Request,
    body: AcceptInviteRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Accept a workspace invite token and join the workspace.

    No workspace membership is required to call this endpoint — the accepting
    user may not yet belong to any workspace. Returns the new membership record
    on success.

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        body: Invite acceptance payload with the token string.
        user_id: Authenticated user ID (injected by FastAPI).

    Returns:
        The newly created workspace membership record dict.

    Raises:
        HTTPException: 400 when the token is invalid, expired, or already used.
    """
    try:
        service = WorkspaceService()
        membership = await service.accept_invite(token=body.token, user_id=user_id)
        governance = get_governance_service()
        await governance.log_event(
            user_id=user_id,
            action_type="member.joined",
            resource_type="workspace_member",
            resource_id=membership.get("id") if isinstance(membership, dict) else None,
            details={
                "workspace_id": membership.get("workspace_id")
                if isinstance(membership, dict)
                else None
            },
        )
        return {"success": True, "membership": membership}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("teams.accept_invite error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to accept invite") from exc


# AUTH-03 (Phase 49 Plan 03): the PATCH /members/{member_user_id}/role handler
# has moved to app/routers/teams_rbac.py (a sibling sub-router with the SAME
# /teams prefix but WITHOUT the require_feature("teams") gate) so workspace
# admins on any tier can manage member roles. UpdateRoleRequest and
# MemberResponse remain here because the new router imports them from this
# module.


@router.delete("/members/{member_user_id}")
@limiter.limit(get_user_persona_limit)
async def remove_member(
    request: Request,
    member_user_id: str,
    user_id: str = Depends(get_current_user_id),
    _admin: None = Depends(require_role("admin")),
) -> dict:
    """Remove a member from the workspace.

    Only workspace admins can remove members. The workspace owner cannot
    be removed.

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        member_user_id: The user_id of the member to remove.
        user_id: Authenticated user (actor) ID (injected by FastAPI).
        _admin: Admin role gate dependency (injected by FastAPI).

    Returns:
        Success confirmation dict.

    Raises:
        HTTPException: 400 when removal is not permitted.
    """
    try:
        service = WorkspaceService()
        workspace = await service.get_workspace_for_user(user_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="No workspace found")

        await service.remove_member(
            workspace_id=workspace["id"],
            target_user_id=member_user_id,
            actor_user_id=user_id,
        )
        governance = get_governance_service()
        await governance.log_event(
            user_id=user_id,
            action_type="member.removed",
            resource_type="workspace_member",
            resource_id=member_user_id,
            details={"workspace_id": workspace["id"]},
        )
        return {"success": True}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("teams.remove_member error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to remove member") from exc


# ---------------------------------------------------------------------------
# Team analytics endpoints
# ---------------------------------------------------------------------------


@router.get("/analytics")
@limiter.limit(get_user_persona_limit)
async def get_team_analytics(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Return workspace-scoped KPIs with optional per-member breakdown.

    Any workspace member may retrieve the aggregate KPIs. The
    ``member_breakdown`` field is included only for admin and owner roles;
    all other roles receive ``null``.

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        user_id: Authenticated user ID (injected by FastAPI).

    Returns:
        Dict with ``kpis`` (aggregate) and ``member_breakdown`` (list or null).

    Raises:
        HTTPException: 404 when the user has no workspace.
    """
    try:
        ws_service = WorkspaceService()
        workspace = await ws_service.get_workspace_for_user(user_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="No workspace found")

        workspace_id = workspace["id"]
        role = await ws_service.get_member_role(user_id, workspace_id)

        analytics_service = TeamAnalyticsService()
        kpis = await analytics_service.get_team_kpis(workspace_id)

        member_breakdown = None
        if role in ("admin", "owner"):
            member_breakdown = await analytics_service.get_per_member_kpis(workspace_id)

        return {"kpis": kpis, "member_breakdown": member_breakdown}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("teams.get_team_analytics error: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to get team analytics"
        ) from exc


@router.get("/shared/initiatives")
@limiter.limit(get_user_persona_limit)
async def list_shared_initiatives(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
) -> list:
    """Return initiatives created by any member of the current workspace.

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        limit: Maximum rows to return (1-200, default 50).
        user_id: Authenticated user ID (injected by FastAPI).

    Returns:
        List of initiative row dicts ordered by updated_at descending.

    Raises:
        HTTPException: 404 when the user has no workspace.
    """
    try:
        ws_service = WorkspaceService()
        workspace = await ws_service.get_workspace_for_user(user_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="No workspace found")

        analytics_service = TeamAnalyticsService()
        return await analytics_service.get_shared_initiatives(
            workspace["id"], limit=limit
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("teams.list_shared_initiatives error: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to list shared initiatives"
        ) from exc


@router.get("/shared/workflows")
@limiter.limit(get_user_persona_limit)
async def list_shared_workflows(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
) -> list:
    """Return workflow executions created by any member of the current workspace.

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        limit: Maximum rows to return (1-200, default 50).
        user_id: Authenticated user ID (injected by FastAPI).

    Returns:
        List of workflow_executions row dicts ordered by created_at descending.

    Raises:
        HTTPException: 404 when the user has no workspace.
    """
    try:
        ws_service = WorkspaceService()
        workspace = await ws_service.get_workspace_for_user(user_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="No workspace found")

        analytics_service = TeamAnalyticsService()
        return await analytics_service.get_shared_workflows(
            workspace["id"], limit=limit
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("teams.list_shared_workflows error: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to list shared workflows"
        ) from exc


@router.get("/activity")
@limiter.limit(get_user_persona_limit)
async def get_team_activity(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
) -> list:
    """Return workspace activity grouped by resource.

    Uses a single query against governance_audit_log with Python-level
    grouping to produce resource clusters. No N+1 queries.

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        limit: Maximum audit rows to pull before grouping (1-500, default 100).
        user_id: Authenticated user ID (injected by FastAPI).

    Returns:
        List of resource cluster dicts: {resource_type, resource_id,
        resource_name, events: [...]}, most-recently-active first.

    Raises:
        HTTPException: 404 when the user has no workspace.
    """
    try:
        ws_service = WorkspaceService()
        workspace = await ws_service.get_workspace_for_user(user_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="No workspace found")

        analytics_service = TeamAnalyticsService()
        return await analytics_service.get_activity_feed(workspace["id"], limit=limit)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("teams.get_team_activity error: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to get team activity"
        ) from exc
