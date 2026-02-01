from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import secrets
import json
from supabase import create_client, Client
import os

# Config
# Note: In production, rely on env vars.
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

router = APIRouter()

def get_service_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Supabase URL and Service Role Key must be set")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Schemas
class ApprovalRequestCreate(BaseModel):
    action_type: str
    payload: Dict[str, Any]
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
async def create_approval_request(req: ApprovalRequestCreate):
    """
    Internal/Agent endpoint to generate magic links.
    """
    try:
        supabase = get_service_client()
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=req.expires_in_hours)

        data = {
            "token": token,
            "action_type": req.action_type,
            "payload": req.payload,
            "expires_at": expires_at.isoformat(),
            "status": "PENDING"
        }

        # Insert into DB
        res = supabase.table("approval_requests").insert(data).execute()
        
        # In a real deployed environment, this comes from an env var
        BASE_URL = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
        approval_link = f"{BASE_URL}/approval/{token}"

        return {
            "link": approval_link,
            "token": token,
            "expires_at": expires_at
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/approvals/{token}")
async def get_approval_request(token: str):
    """
    Public (token-gated) accessor for the Frontend.
    """
    try:
        supabase = get_service_client()
        res = supabase.table("approval_requests").select("*").eq("token", token).single().execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="Request not found or expired")
            
        return res.data
    except Exception as e:
         # Supabase single() raises error if not found
         raise HTTPException(status_code=404, detail="Request not found")

@router.post("/approvals/{token}/decision")
async def submit_approval_decision(token: str, decision: ApprovalDecision, request: Request):
    """
    Execute the decision (Approve/Reject).
    """
    if token != decision.token:
        raise HTTPException(status_code=400, detail="Token mismatch")
    
    if decision.decision not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Invalid decision")

    try:
        supabase = get_service_client()
        
        # 1. Fetch current status
        current = supabase.table("approval_requests").select("*").eq("token", token).single().execute()
        if not current.data:
             raise HTTPException(status_code=404, detail="Request not found")
        
        row = current.data
        if row['status'] != 'PENDING':
             return {"success": False, "status": row['status'], "message": "Request already processed"}
        
        if datetime.fromisoformat(row['expires_at'].replace('Z', '+00:00')) < datetime.utcnow().replace(tzinfo=datetime.utcnow().astimezone().tzinfo):
             # Mark expired if needed, or just block
             supabase.table("approval_requests").update({"status": "EXPIRED"}).eq("token", token).execute()
             return {"success": False, "status": "EXPIRED", "message": "Link expired"}

        # 2. Update status
        client_ip = request.client.host
        update_data = {
            "status": decision.decision,
            "responded_at": datetime.utcnow().isoformat(),
            "responder_ip": client_ip
        }
        
        res = supabase.table("approval_requests").update(update_data).eq("token", token).execute()

        # 3. Trigger downstream action (Post-Approvals)
        # For now, we just update state. 
        # In a real system, we'd fire a webhook or resume the agent workflow.
        
        return {
            "success": True, 
            "status": decision.decision, 
            "message": f"Successfully {decision.decision.lower()}."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/approvals/pending/list")
async def get_pending_approvals():
    """
    Get all pending approval requests.
    """
    try:
        supabase = get_service_client()
        res = supabase.table("approval_requests").select("id, action_type, created_at, token").eq("status", "PENDING").execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
