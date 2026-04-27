# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Governance API — enterprise audit trail, portfolio health, and approval chains.

Provides REST endpoints for querying the audit log, computing portfolio health
scores, and managing multi-level approval chains. All endpoints require the
"governance" feature gate (enterprise tier).

Approval chain creation and step decisions are additionally validated to ensure
correct state transitions before persisting.
"""


import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.middleware.feature_gate import require_feature
from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.middleware.workspace_role import require_role
from app.routers.onboarding import get_current_user_id
from app.services.governance_service import get_governance_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/governance",
    tags=["Governance"],
    dependencies=[Depends(require_feature("governance"))],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class AuditLogEntry(BaseModel):
    """A single governance audit log entry."""

    id: str
    user_id: str
    action_type: str
    resource_type: str
    resource_id: str | None
    details: dict
    created_at: str


class PortfolioHealthResponse(BaseModel):
    """Portfolio health score with component breakdown."""

    score: int
    components: dict


class ApprovalChainResponse(BaseModel):
    """An approval chain with its steps."""

    id: str
    user_id: str
    action_type: str
    resource_id: str | None
    resource_label: str | None
    status: str
    steps: list
    created_at: str
    resolved_at: str | None


class CreateChainRequest(BaseModel):
    """Body for creating a new approval chain."""

    action_type: str
    resource_id: str | None = None
    resource_label: str | None = None
    steps: list[dict] | None = None


class DecideStepRequest(BaseModel):
    """Body for deciding on an approval chain step."""

    decision: str = Field(pattern="^(approved|rejected)$")
    comment: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/audit-log", response_model=list[AuditLogEntry])
@limiter.limit(get_user_persona_limit)
async def get_audit_log(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action_type: str | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
) -> list[AuditLogEntry]:
    """Return a paginated audit log for the authenticated user.

    Entries are ordered by creation time descending (most recent first).
    Optionally filter by a specific action type (e.g. ``initiative.created``).

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        limit: Maximum number of entries to return (1-200, default 50).
        offset: Number of entries to skip for pagination.
        action_type: Optional filter for a specific action type string.
        user_id: Authenticated user ID (injected by FastAPI).

    Returns:
        List of AuditLogEntry objects ordered by created_at descending.
    """
    try:
        governance = get_governance_service()
        entries = await governance.get_audit_log(
            user_id=user_id,
            limit=limit,
            offset=offset,
            action_type=action_type,
        )
        return [AuditLogEntry(**entry) for entry in entries]
    except Exception as exc:
        logger.error("governance.get_audit_log error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve audit log") from exc


@router.get("/portfolio-health", response_model=PortfolioHealthResponse)
@limiter.limit(get_user_persona_limit)
async def get_portfolio_health(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> PortfolioHealthResponse:
    """Compute and return the portfolio health score for the authenticated user.

    The score (0-100) is a weighted composite of:
    - Initiative completion (40%)
    - Risk coverage (30%)
    - Resource allocation (30%)

    Each component degrades gracefully when its underlying table is unavailable.

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        user_id: Authenticated user ID (injected by FastAPI).

    Returns:
        PortfolioHealthResponse with the overall score and per-component breakdown.
    """
    try:
        governance = get_governance_service()
        result = await governance.compute_portfolio_health(user_id=user_id)
        return PortfolioHealthResponse(
            score=result["score"],
            components=result.get("components", {}),
        )
    except Exception as exc:
        logger.error("governance.portfolio_health error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to compute portfolio health") from exc


@router.post("/approval-chains", response_model=ApprovalChainResponse)
@limiter.limit(get_user_persona_limit)
async def create_approval_chain(
    request: Request,
    body: CreateChainRequest,
    user_id: str = Depends(get_current_user_id),
    _admin: None = Depends(require_role("admin")),
) -> ApprovalChainResponse:
    """Create a new multi-level approval chain.

    Requires admin role. When ``steps`` is omitted the default three-step chain
    (reviewer → approver → executive) is used. An audit event is logged for
    the creation.

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        body: Chain creation parameters.
        user_id: Authenticated user ID (injected by FastAPI).
        _admin: Admin role gate dependency (injected by FastAPI).

    Returns:
        ApprovalChainResponse for the newly created chain.
    """
    try:
        governance = get_governance_service()
        chain = await governance.create_approval_chain(
            user_id=user_id,
            action_type=body.action_type,
            resource_id=body.resource_id,
            resource_label=body.resource_label,
            steps=body.steps,
        )
        await governance.log_event(
            user_id=user_id,
            action_type="approval_chain.created",
            resource_type="approval_chain",
            resource_id=chain.get("id"),
            details={
                "action_type": body.action_type,
                "resource_label": body.resource_label,
            },
        )
        return ApprovalChainResponse(**chain)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("governance.create_approval_chain error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create approval chain") from exc


@router.get("/approval-chains", response_model=list[ApprovalChainResponse])
@limiter.limit(get_user_persona_limit)
async def list_approval_chains(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> list[ApprovalChainResponse]:
    """List all pending approval chains for the authenticated user.

    Returns chains in ``pending`` status where the authenticated user is the
    chain creator.

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        user_id: Authenticated user ID (injected by FastAPI).

    Returns:
        List of ApprovalChainResponse objects for pending chains.
    """
    try:
        governance = get_governance_service()
        chains = await governance.get_pending_chains(user_id=user_id)
        return [ApprovalChainResponse(**chain) for chain in chains]
    except Exception as exc:
        logger.error("governance.list_approval_chains error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list approval chains") from exc


@router.get("/approval-chains/{chain_id}", response_model=ApprovalChainResponse)
@limiter.limit(get_user_persona_limit)
async def get_approval_chain(
    request: Request,
    chain_id: str,
    user_id: str = Depends(get_current_user_id),
) -> ApprovalChainResponse:
    """Get the current status of an approval chain by ID.

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        chain_id: UUID of the approval chain to retrieve.
        user_id: Authenticated user ID (injected by FastAPI).

    Returns:
        ApprovalChainResponse for the requested chain.

    Raises:
        HTTPException: 404 when the chain does not exist.
    """
    try:
        governance = get_governance_service()
        chain = await governance.get_chain_status(chain_id=chain_id)
        if chain is None:
            raise HTTPException(status_code=404, detail="Approval chain not found")
        return ApprovalChainResponse(**chain)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("governance.get_approval_chain error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to get approval chain") from exc


@router.post(
    "/approval-chains/{chain_id}/steps/{step_order}/decide",
    response_model=ApprovalChainResponse,
)
@limiter.limit(get_user_persona_limit)
async def decide_chain_step(
    request: Request,
    chain_id: str,
    step_order: int,
    body: DecideStepRequest,
    user_id: str = Depends(get_current_user_id),
) -> ApprovalChainResponse:
    """Record an approve or reject decision for a specific approval chain step.

    The decision advances or terminates the chain accordingly. A ``step.decided``
    audit event is recorded by the GovernanceService internally.

    Args:
        request: Incoming HTTP request (injected by FastAPI).
        chain_id: UUID of the approval chain.
        step_order: 1-based position of the step to decide on.
        body: Decision payload (``approved`` or ``rejected``, optional comment).
        user_id: Authenticated user ID (injected by FastAPI).

    Returns:
        Updated ApprovalChainResponse reflecting the new step and chain status.

    Raises:
        HTTPException: 400 on invalid decision state, 404 when chain is not found.
    """
    try:
        governance = get_governance_service()
        chain = await governance.decide_step(
            chain_id=chain_id,
            step_order=step_order,
            approver_user_id=user_id,
            decision=body.decision,
            comment=body.comment,
        )
        return ApprovalChainResponse(**chain)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("governance.decide_chain_step error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to record step decision") from exc
