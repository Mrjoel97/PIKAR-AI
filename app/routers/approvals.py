import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.app_utils.auth import get_user_id_from_bearer_token
from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

router = APIRouter()


# Strict rate limit for approval endpoints (5 per minute)
def get_approval_rate_limit() -> str:
    """Get rate limit for approval endpoints."""
    return "5/minute"


def _hash_token(token: str) -> str:
    """Hash token using SHA-256 for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def _extract_requester_user_id(request: Request) -> str | None:
    auth_header = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None
    return get_user_id_from_bearer_token(auth_header.split(" ", 1)[1])


def _row_matches_user(row: dict[str, Any], user_id: str) -> bool:
    payload = row.get("payload") or {}
    if not isinstance(payload, dict):
        return False
    return (
        payload.get("requester_user_id") == user_id or payload.get("user_id") == user_id
    )


def _serialize_pending_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") or {}
    public_token = payload.get("public_token") if isinstance(payload, dict) else None
    return {
        "id": row.get("id"),
        "action_type": row.get("action_type"),
        "created_at": row.get("created_at"),
        "token": public_token,
    }


# Schemas
class ApprovalRequestCreate(BaseModel):
    action_type: str
    payload: dict[str, Any]
    expires_in_hours: int = 24


class ApprovalDecision(BaseModel):
    token: str
    decision: str  # APPROVED / REJECTED


class ApprovalResponse(BaseModel):
    success: bool
    status: str
    message: str


# Endpoints
@router.post("/approvals/create")
@limiter.limit(get_approval_rate_limit)
async def create_approval_request(
    request: Request,
    req: ApprovalRequestCreate,
    requester_user_id: str = Depends(get_current_user_id),
):
    """Internal/Agent endpoint to generate magic links."""
    try:
        supabase = get_service_client()
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=req.expires_in_hours)

        payload = dict(req.payload or {})
        payload.setdefault("requester_user_id", requester_user_id)
        payload.setdefault("public_token", token)

        data = {
            "token": token_hash,
            "action_type": req.action_type,
            "payload": payload,
            "expires_at": expires_at.isoformat(),
            "status": "PENDING",
        }

        await execute_async(
            supabase.table("approval_requests").insert(data),
            op_name="approvals.create",
        )

        base_url = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
        approval_link = f"{base_url}/approval/{token}"

        return {
            "link": approval_link,
            "token": token,
            "expires_at": expires_at,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approvals/{token}")
@limiter.limit(get_approval_rate_limit)
async def get_approval_request(request: Request, token: str):
    """Public (token-gated) accessor for the Frontend."""
    try:
        supabase = get_service_client()
        token_hash = _hash_token(token)
        response = await execute_async(
            supabase.table("approval_requests")
            .select("id, action_type, status, created_at, expires_at")
            .eq("token", token_hash)
            .single(),
            op_name="approvals.get",
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Request not found or expired")

        return response.data
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Request not found")


@router.post("/approvals/{token}/decision")
@limiter.limit(get_approval_rate_limit)
async def submit_approval_decision(
    token: str, decision: ApprovalDecision, request: Request
):
    """Execute the decision (Approve/Reject)."""
    if token != decision.token:
        raise HTTPException(status_code=400, detail="Token mismatch")

    if decision.decision not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Invalid decision")

    try:
        supabase = get_service_client()
        token_hash = _hash_token(token)

        # First fetch to check existence and expiry without a PENDING guard
        current = await execute_async(
            supabase.table("approval_requests")
            .select("status, expires_at")
            .eq("token", token_hash)
            .single(),
            op_name="approvals.decision.get_current",
        )
        if not current.data:
            raise HTTPException(status_code=404, detail="Request not found")

        row = current.data
        expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
        if expires_at < datetime.now(timezone.utc):
            # Opportunistically mark as expired; ignore if already transitioned
            await execute_async(
                supabase.table("approval_requests")
                .update({"status": "EXPIRED"})
                .eq("token", token_hash)
                .eq("status", "PENDING"),
                op_name="approvals.decision.expire",
            )
            return {"success": False, "status": "EXPIRED", "message": "Link expired"}

        client_ip = request.client.host if request.client else None
        now = datetime.now(timezone.utc).isoformat()

        # Atomic: only update if still PENDING — prevents double-approval race
        result = await execute_async(
            supabase.table("approval_requests")
            .update(
                {
                    "status": decision.decision,
                    "responded_at": now,
                    "responder_ip": client_ip,
                }
            )
            .eq("token", token_hash)
            .eq("status", "PENDING"),
            op_name="approvals.decision.update",
        )

        if not result.data:
            return {
                "success": False,
                "status": row["status"],
                "message": "Already decided or not found",
            }

        return {
            "success": True,
            "status": decision.decision,
            "message": f"Successfully {decision.decision.lower()}.",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approvals/pending/list")
@limiter.limit(get_user_persona_limit)
async def get_pending_approvals(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Get pending approval requests scoped to the authenticated user."""
    try:
        supabase = get_service_client()
        response = await execute_async(
            supabase.table("approval_requests")
            .select("id, action_type, created_at, payload")
            .eq("status", "PENDING")
            .eq("requester_user_id", user_id),
            op_name="approvals.pending.list",
        )
        rows = [row for row in (response.data or []) if _row_matches_user(row, user_id)]
        return [_serialize_pending_row(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approvals/history")
@limiter.limit(get_user_persona_limit)
async def get_approval_history(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """Get approval history (non-PENDING) scoped to the authenticated user."""
    try:
        supabase = get_service_client()
        query = (
            supabase.table("approval_requests")
            .select("id, action_type, status, created_at, responded_at, payload")
            .neq("status", "PENDING")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if status and status in ("APPROVED", "REJECTED", "EXPIRED"):
            query = query.eq("status", status)

        response = await execute_async(query, op_name="approvals.history")
        rows = [row for row in (response.data or []) if _row_matches_user(row, user_id)]
        return [
            {
                "id": row.get("id"),
                "action_type": row.get("action_type"),
                "status": row.get("status"),
                "created_at": row.get("created_at"),
                "responded_at": row.get("responded_at"),
            }
            for row in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
