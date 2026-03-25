# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Admin approval queue, override, and role management API — Phase 15.

Provides:
- GET  /admin/approvals/all               — cross-user approval queue with filters
- POST /admin/approvals/{id}/override     — admin override (approve/reject) with audit
- GET  /admin/roles                       — list all admin role assignments
- POST /admin/roles                       — create/update admin role (super_admin only)
- DELETE /admin/roles/{user_id}           — remove admin role (super_admin only)
- GET  /admin/roles/permissions           — list per-role section permissions
- PUT  /admin/roles/permissions           — update per-role section permissions (super_admin)

All endpoints are gated by ``require_admin`` or ``require_admin_role(min_role)``.
Override and role-mutation endpoints emit audit log entries with
``source='admin_override'`` or ``source='manual'`` respectively.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from app.middleware.admin_auth import require_admin, require_admin_role
from app.services.admin_audit import log_admin_action
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin-approvals"])

_security = HTTPBearer()

# Valid role values — must match user_roles.role CHECK constraint
_VALID_ROLES = frozenset({"junior_admin", "senior_admin", "admin", "super_admin"})

# Valid section values — must match admin_role_permissions.section CHECK constraint
_VALID_SECTIONS = frozenset(
    {
        "users",
        "monitoring",
        "analytics",
        "approvals",
        "config",
        "knowledge",
        "billing",
        "integrations",
        "settings",
        "audit_log",
    }
)

# Valid allowed_actions values
_VALID_ACTIONS = frozenset({"read", "write", "manage"})


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class OverrideDecision(BaseModel):
    """Request body for the approval override endpoint."""

    decision: str
    reason: str | None = None


class CreateAdminRole(BaseModel):
    """Request body for creating/updating an admin role assignment."""

    user_id: str
    role: str


class UpdateRolePermission(BaseModel):
    """Request body for updating per-role section permissions."""

    role: str
    section: str
    allowed_actions: list[str]


# ---------------------------------------------------------------------------
# GET /approvals/all
# ---------------------------------------------------------------------------


@router.get("/approvals/all")
async def list_all_approvals(
    admin_user: dict = Depends(require_admin),  # noqa: B008
    status: str | None = Query(default="PENDING"),
    action_type: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Return all approval requests across all users with optional filters.

    Requires admin access (any role). Results are ordered newest-first and
    paginated via ``limit``/``offset``.

    Args:
        admin_user: Injected by require_admin; confirms caller is an admin.
        status: Filter by status (default 'PENDING'). Pass None for all statuses.
        action_type: Optional filter by action_type value.
        user_id: Optional filter by requester user_id.
        limit: Page size (default 50, max 200).
        offset: Row offset for pagination.

    Returns:
        JSON with ``approvals`` list, ``total``, ``limit``, and ``offset``.
    """
    client = get_service_client()

    query = (
        client.table("approval_requests")
        .select(
            "id, action_type, status, payload, created_at, expires_at, "
            "responded_at, responder_ip, user_id"
        )
        .order("created_at", desc=True)
    )

    if status is not None:
        query = query.eq("status", status)
    if action_type is not None:
        query = query.eq("action_type", action_type)
    if user_id is not None:
        query = query.eq("user_id", user_id)

    query = query.range(offset, offset + limit - 1)

    result = await execute_async(query, op_name="approvals.admin.list_all")
    rows: list[dict] = result.data or []

    return {
        "approvals": rows,
        "total": len(rows),
        "limit": limit,
        "offset": offset,
    }


# ---------------------------------------------------------------------------
# POST /approvals/{approval_id}/override
# ---------------------------------------------------------------------------


@router.post("/approvals/{approval_id}/override")
async def override_approval(
    approval_id: str,
    body: OverrideDecision,
    request: Request,
    admin_user: dict = Depends(require_admin_role("senior_admin")),  # noqa: B008
    client_ip: str = "unknown",
) -> dict[str, Any]:
    """Admin override: approve or reject any pending approval request.

    Requires senior_admin or higher. Validates that the approval is still
    PENDING before updating. Logs the override with ``source='admin_override'``.

    Args:
        approval_id: UUID of the approval request to override.
        body: Override decision (APPROVED or REJECTED) and optional reason.
        request: FastAPI Request (used to extract client IP for audit log).
        admin_user: Injected by require_admin_role('senior_admin').
        client_ip: Fallback IP address when X-Forwarded-For is absent.

    Returns:
        JSON with ``approval_id`` and new ``status``.

    Raises:
        HTTPException 400: Invalid decision value.
        HTTPException 404: Approval not found.
        HTTPException 409: Approval is not in PENDING status.
    """
    decision = body.decision.upper()
    if decision not in ("APPROVED", "REJECTED"):
        raise HTTPException(
            status_code=400, detail="decision must be APPROVED or REJECTED"
        )

    # Resolve client IP from request
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = (forwarded.split(",")[0].strip() if forwarded else None) or str(
        request.client.host if request.client else "unknown"
    )

    client = get_service_client()

    # Fetch the current approval
    fetch_query = (
        client.table("approval_requests")
        .select("id, status, action_type, payload, expires_at")
        .eq("id", approval_id)
    )
    fetch_result = await execute_async(fetch_query, op_name="approvals.admin.fetch")
    rows: list[dict] = fetch_result.data or []

    if not rows:
        raise HTTPException(status_code=404, detail="Approval request not found")

    approval = rows[0]
    if approval["status"] != "PENDING":
        raise HTTPException(
            status_code=409,
            detail=f"Approval is already in status '{approval['status']}'",
        )

    # Atomic update
    update_query = (
        client.table("approval_requests")
        .update(
            {
                "status": decision,
                "responded_at": "now()",
                "responder_ip": client_ip,
            }
        )
        .eq("id", approval_id)
        .eq("status", "PENDING")
    )
    await execute_async(update_query, op_name="approvals.admin.override")

    # Audit log — source MUST be 'admin_override' (non-standard, accepted by validator fallback)
    await log_admin_action(
        admin_user_id=admin_user.get("id"),
        action="override_approval",
        target_type="approval",
        target_id=approval_id,
        details={
            "decision": decision,
            "reason": body.reason,
            "original_action_type": approval.get("action_type"),
        },
        source="admin_override",
    )

    return {"approval_id": approval_id, "status": decision}


# ---------------------------------------------------------------------------
# GET /roles
# ---------------------------------------------------------------------------


@router.get("/roles")
async def list_admin_roles(
    admin_user: dict = Depends(require_admin_role("admin")),  # noqa: B008
) -> dict[str, Any]:
    """Return all admin role assignments (admin+ only).

    Args:
        admin_user: Injected by require_admin_role('admin').

    Returns:
        JSON with ``admins`` list of role assignment dicts.
    """
    client = get_service_client()

    query = (
        client.table("user_roles")
        .select("user_id, role, created_at, updated_at")
        .neq("role", "user")
    )
    result = await execute_async(query, op_name="approvals.admin.list_roles")
    rows: list[dict] = result.data or []

    return {"admins": rows}


# ---------------------------------------------------------------------------
# POST /roles
# ---------------------------------------------------------------------------


@router.post("/roles")
async def create_admin_role(
    body: CreateAdminRole,
    admin_user: dict = Depends(require_admin_role("super_admin")),  # noqa: B008
) -> dict[str, Any]:
    """Create or update an admin role assignment (super_admin only).

    Upserts into ``user_roles``. If a row already exists for ``user_id``,
    the role is updated.

    Args:
        body: Target user_id and new role.
        admin_user: Injected by require_admin_role('super_admin').

    Returns:
        JSON with ``user_id`` and ``role``.

    Raises:
        HTTPException 400: Invalid role value.
    """
    if body.role not in _VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"role must be one of {sorted(_VALID_ROLES)}",
        )

    client = get_service_client()

    upsert_query = client.table("user_roles").upsert(
        {
            "user_id": body.user_id,
            "role": body.role,
            "updated_at": "now()",
        },
        on_conflict="user_id",
    )
    await execute_async(upsert_query, op_name="approvals.admin.create_role")

    await log_admin_action(
        admin_user_id=admin_user.get("id"),
        action="create_admin_role",
        target_type="user",
        target_id=body.user_id,
        details={"role": body.role},
        source="manual",
    )

    return {"user_id": body.user_id, "role": body.role}


# ---------------------------------------------------------------------------
# DELETE /roles/{target_user_id}
# ---------------------------------------------------------------------------


@router.delete("/roles/{target_user_id}")
async def delete_admin_role(
    target_user_id: str,
    admin_user: dict = Depends(require_admin_role("super_admin")),  # noqa: B008
) -> dict[str, Any]:
    """Remove an admin role assignment (super_admin only).

    Deletes the ``user_roles`` row for ``target_user_id`` only when the
    role is an admin-level role (not 'user').

    Args:
        target_user_id: UUID of the user whose admin role is removed.
        admin_user: Injected by require_admin_role('super_admin').

    Returns:
        JSON with ``deleted_user_id``.
    """
    client = get_service_client()

    delete_query = (
        client.table("user_roles")
        .delete()
        .eq("user_id", target_user_id)
        .neq("role", "user")
    )
    await execute_async(delete_query, op_name="approvals.admin.delete_role")

    await log_admin_action(
        admin_user_id=admin_user.get("id"),
        action="delete_admin_role",
        target_type="user",
        target_id=target_user_id,
        details=None,
        source="manual",
    )

    return {"deleted_user_id": target_user_id}


# ---------------------------------------------------------------------------
# GET /roles/permissions
# ---------------------------------------------------------------------------


@router.get("/roles/permissions")
async def list_role_permissions(
    admin_user: dict = Depends(require_admin_role("admin")),  # noqa: B008
) -> dict[str, Any]:
    """Return all per-role section permissions (admin+ only).

    Args:
        admin_user: Injected by require_admin_role('admin').

    Returns:
        JSON with ``permissions`` list of dicts grouped by role.
    """
    client = get_service_client()

    query = client.table("admin_role_permissions").select(
        "role, section, allowed_actions"
    )
    result = await execute_async(query, op_name="approvals.admin.list_permissions")
    rows: list[dict] = result.data or []

    # Group by role for convenient frontend consumption
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        role = row["role"]
        if role not in grouped:
            grouped[role] = []
        grouped[role].append(
            {"section": row["section"], "allowed_actions": row["allowed_actions"]}
        )

    return {"permissions": grouped}


# ---------------------------------------------------------------------------
# PUT /roles/permissions
# ---------------------------------------------------------------------------


@router.put("/roles/permissions")
async def update_role_permissions(
    body: UpdateRolePermission,
    admin_user: dict = Depends(require_admin_role("super_admin")),  # noqa: B008
) -> dict[str, Any]:
    """Update per-role section permissions (super_admin only).

    Upserts a single row into ``admin_role_permissions``.

    Args:
        body: Role, section, and new allowed_actions list.
        admin_user: Injected by require_admin_role('super_admin').

    Returns:
        JSON with ``role``, ``section``, and ``allowed_actions``.

    Raises:
        HTTPException 400: Invalid role, section, or action values.
    """
    if body.role not in _VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"role must be one of {sorted(_VALID_ROLES)}",
        )
    if body.section not in _VALID_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"section must be one of {sorted(_VALID_SECTIONS)}",
        )
    invalid_actions = set(body.allowed_actions) - _VALID_ACTIONS
    if invalid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid actions: {sorted(invalid_actions)}. Must be read, write, or manage.",
        )

    client = get_service_client()

    upsert_query = client.table("admin_role_permissions").upsert(
        {
            "role": body.role,
            "section": body.section,
            "allowed_actions": body.allowed_actions,
        },
        on_conflict="role,section",
    )
    await execute_async(upsert_query, op_name="approvals.admin.update_permissions")

    await log_admin_action(
        admin_user_id=admin_user.get("id"),
        action="update_role_permissions",
        target_type="role_permissions",
        target_id=f"{body.role}:{body.section}",
        details={
            "role": body.role,
            "section": body.section,
            "allowed_actions": body.allowed_actions,
        },
        source="manual",
    )

    return {
        "role": body.role,
        "section": body.section,
        "allowed_actions": body.allowed_actions,
    }
