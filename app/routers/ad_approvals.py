# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Ad Approvals Router.

REST endpoints for the ad budget approval gate:

- ``POST /ad-approvals/{approval_id}/decide`` — Approve or reject an operation.
  On approval, executes the actual Google Ads / Meta Ads API call.
- ``GET  /ad-approvals/{approval_id}``         — Render the approval card.
- ``GET  /ad-approvals/pending``               — List pending approvals for user.
"""


import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.routers.onboarding import get_current_user_id
from app.services.base_service import AdminService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ad-approvals", tags=["Ad Approvals"])


# ============================================================================
# Request schemas
# ============================================================================


class ApprovalDecisionRequest(BaseModel):
    """Request body for an approval decision."""

    decision: str  # "approve" or "reject"


# ============================================================================
# Helpers
# ============================================================================


async def _get_approval_row(approval_id: str) -> dict[str, Any] | None:
    """Fetch an approval_requests row by ID.

    Args:
        approval_id: UUID of the approval request.

    Returns:
        Row dict or ``None`` if not found.
    """
    admin = AdminService()
    try:
        result = await execute_async(
            admin.client.table("approval_requests")
            .select("*")
            .eq("id", approval_id)
            .single(),
            op_name="ad_approvals.get_row",
        )
        return result.data
    except Exception:
        logger.exception(
            "Failed to fetch approval_requests row: %s", approval_id
        )
        return None


def _row_belongs_to_user(row: dict[str, Any], user_id: str) -> bool:
    """Check whether an approval row belongs to the requesting user.

    Falls back to the payload's user_id / requester_user_id fields when
    the top-level user_id column is absent (older rows).

    Args:
        row: approval_requests row dict.
        user_id: Authenticated user's UUID.

    Returns:
        ``True`` if the row belongs to the user.
    """
    if row.get("user_id") == user_id:
        return True
    payload = row.get("payload") or {}
    if isinstance(payload, dict):
        return (
            payload.get("user_id") == user_id
            or payload.get("requester_user_id") == user_id
        )
    return False


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/{approval_id}/decide")
async def decide_approval(
    approval_id: str,
    body: ApprovalDecisionRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Approve or reject an ad budget operation.

    On ``"approve"``: executes the actual Google Ads / Meta Ads API call
    via ``AdApprovalService.execute_approved_operation``, then marks the row
    APPROVED.

    On ``"reject"``: marks the row REJECTED without executing anything.

    Args:
        approval_id: UUID of the approval_requests row.
        body: Decision payload with ``decision`` field (``"approve"`` or
              ``"reject"``).
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with result of execution (approve) or confirmation (reject).

    Raises:
        HTTPException: 404 if not found, 403 if not owner, 400 if not pending,
                       422 if decision value is invalid.
    """
    decision = body.decision.lower()
    if decision not in ("approve", "reject"):
        raise HTTPException(
            status_code=422,
            detail="decision must be 'approve' or 'reject'",
        )

    row = await _get_approval_row(approval_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Approval request not found: {approval_id}",
        )

    if not _row_belongs_to_user(row, current_user_id):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to decide this approval",
        )

    if row.get("status") != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Approval is not pending (current status: {row.get('status')})",
        )

    admin = AdminService()

    if decision == "approve":
        # 1. Mark as APPROVED in DB
        await execute_async(
            admin.client.table("approval_requests")
            .update({"status": "APPROVED"})
            .eq("id", approval_id),
            op_name="ad_approvals.approve",
        )

        # 2. Execute the platform operation
        from app.services.ad_approval_service import AdApprovalService

        svc = AdApprovalService()
        try:
            result = await svc.execute_approved_operation(approval_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception(
                "Failed to execute approved ad operation: %s", approval_id
            )
            raise HTTPException(
                status_code=502,
                detail=f"Platform API call failed: {exc!s}",
            ) from exc

        return JSONResponse(
            content={"status": "APPROVED", "executed": True, "result": result}
        )

    # Reject
    await execute_async(
        admin.client.table("approval_requests")
        .update({"status": "REJECTED"})
        .eq("id", approval_id),
        op_name="ad_approvals.reject",
    )
    return JSONResponse(
        content={"status": "REJECTED", "executed": False, "approval_id": approval_id}
    )


@router.get("/pending")
async def list_pending_approvals(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """List pending ad approval requests for the current user.

    Args:
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON list of pending approval cards.
    """
    admin = AdminService()
    try:
        result = await execute_async(
            admin.client.table("approval_requests")
            .select("*")
            .eq("user_id", current_user_id)
            .eq("action_type", "AD_BUDGET_CHANGE")
            .eq("status", "PENDING")
            .order("created_at", desc=True)
            .limit(50),
            op_name="ad_approvals.list_pending",
        )
        rows = result.data or []
    except Exception:
        logger.exception(
            "Failed to list pending ad approvals for user=%s", current_user_id
        )
        rows = []

    # Return only card-safe fields (no raw tokens)
    cards = []
    for row in rows:
        payload = row.get("payload") or {}
        card_data = payload.get("card_data") if isinstance(payload, dict) else {}
        cards.append({
            "id": row.get("id"),
            "created_at": row.get("created_at"),
            "expires_at": row.get("expires_at"),
            "card_data": card_data or payload,
        })

    return JSONResponse(content=cards)


@router.get("/{approval_id}")
async def get_approval_card(
    approval_id: str,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
) -> JSONResponse:
    """Return the approval request card data for frontend rendering.

    Args:
        approval_id: UUID of the approval_requests row.
        current_user_id: Authenticated user's UUID.

    Returns:
        JSON with approval metadata and card_data for display.

    Raises:
        HTTPException: 404 if not found, 403 if not the owner.
    """
    row = await _get_approval_row(approval_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Approval request not found: {approval_id}",
        )

    if not _row_belongs_to_user(row, current_user_id):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this approval",
        )

    payload = row.get("payload") or {}
    card_data = payload.get("card_data") if isinstance(payload, dict) else {}

    return JSONResponse(content={
        "id": row.get("id"),
        "status": row.get("status"),
        "action_type": row.get("action_type"),
        "created_at": row.get("created_at"),
        "expires_at": row.get("expires_at"),
        "card_data": card_data or payload,
    })
