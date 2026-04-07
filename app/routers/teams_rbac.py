# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Teams RBAC API — workspace role-management endpoints (un-gated).

AUTH-03 (Phase 49 Plan 03): extracted from ``app/routers/teams.py`` so the
workspace role assignment endpoint is callable by any workspace admin
regardless of subscription tier. The original ``app/routers/teams.py`` keeps
the ``require_feature("teams")`` router-level gate for analytics and invite
endpoints; this sibling router shares the ``/teams`` prefix but deliberately
omits the feature gate so the role-management UI works for solopreneur and
other non-teams-feature tiers.

Authentication is still enforced via ``require_role("admin")`` per endpoint,
so only workspace admins can mutate member roles. Solo users without a
workspace short-circuit through the ``require_role`` middleware (no workspace
implies the gate is a pass-through — see ``app/middleware/workspace_role.py``).

The new router is registered BEFORE the feature-gated ``teams_router`` in
``app/fast_api_app.py`` so its un-gated handler wins FastAPI's first-match
route resolution for the overlapping ``/teams/members/{uid}/role`` path.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.middleware.workspace_role import require_role
from app.routers.onboarding import get_current_user_id
from app.routers.teams import MemberResponse, UpdateRoleRequest
from app.services.governance_service import get_governance_service
from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)

# NOTE: deliberately NO `dependencies=[Depends(require_feature("teams"))]` here.
# AUTH-03 requires the role-management endpoints to be callable by any workspace
# admin regardless of subscription tier. See teams.py for the gated analytics
# and invite endpoints.
router = APIRouter(prefix="/teams", tags=["Teams RBAC"])


@router.patch("/members/{member_user_id}/role", response_model=MemberResponse)
@limiter.limit(get_user_persona_limit)
async def update_member_role(
    request: Request,
    member_user_id: str,
    body: UpdateRoleRequest,
    user_id: str = Depends(get_current_user_id),
    _admin: None = Depends(require_role("admin")),
) -> MemberResponse:
    """Update a workspace member's role. Admin only.

    Tier-agnostic: this handler is NOT behind the ``teams`` feature gate so a
    workspace admin on solopreneur (or any other tier) can call it. The
    ``require_role("admin")`` dependency still enforces actor authorisation,
    and ``WorkspaceService.update_member_role`` enforces owner immutability
    plus role-string validation at the service layer.

    Args:
        request: Incoming HTTP request (injected by FastAPI; required by the
            slowapi rate-limit decorator).
        member_user_id: The ``user_id`` of the member whose role to update.
        body: Role update payload with the new role string
            (one of ``admin``, ``editor``, ``viewer``).
        user_id: Authenticated actor user ID (injected by FastAPI).
        _admin: Admin role gate dependency (injected by FastAPI).

    Returns:
        ``MemberResponse`` reflecting the updated row.

    Raises:
        HTTPException: 400 when the role change is rejected by the service
            layer (e.g. owner immutability), 403 when the actor is not an
            admin, 404 when the actor has no workspace, 500 on unexpected
            errors.
    """
    try:
        service = WorkspaceService()
        workspace = await service.get_workspace_for_user(user_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="No workspace found")

        updated = await service.update_member_role(
            workspace_id=workspace["id"],
            target_user_id=member_user_id,
            new_role=body.role,
            actor_user_id=user_id,
        )
        # Best-effort governance audit log; never block the response on logging.
        try:
            governance = get_governance_service()
            await governance.log_event(
                user_id=user_id,
                action_type="role.changed",
                resource_type="workspace_member",
                resource_id=member_user_id,
                details={"new_role": body.role},
            )
        except Exception as log_exc:
            logger.warning(
                "teams_rbac.update_member_role audit log failed: %s", log_exc
            )

        return MemberResponse(
            id=updated["id"],
            user_id=updated["user_id"],
            email=updated.get("email") or "",
            display_name=updated.get("full_name"),
            role=updated["role"],
            joined_at=updated["joined_at"],
        )
    except HTTPException:
        raise
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("teams_rbac.update_member_role error: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to update member role"
        ) from exc
