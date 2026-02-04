from fastapi import APIRouter, HTTPException, Request
from app.middleware.rate_limiter import limiter, get_user_persona_limit
from typing import Dict, Any
from app.services.supabase import get_service_client

router = APIRouter()

@router.get("/pages/{page_id}")
@limiter.limit(get_user_persona_limit)
async def get_page_content(request: Request, page_id: str):
    """
    Retrieve public landing page content.
    """
    try:
        supabase = get_service_client()
        res = supabase.table("landing_pages").select("*").eq("id", page_id).single().execute()
        
        if not res.data:
             raise HTTPException(status_code=404, detail="Page not found")
             
        return res.data
    except Exception as e:
        raise HTTPException(status_code=404, detail="Page not found")

@router.post("/pages/{page_id}/submit")
@limiter.limit(get_user_persona_limit)
async def submit_lead(request: Request, page_id: str, payload: Dict[str, Any]):
    """
    Capture a lead from a landing page form.
    """
    # In a real app we'd save this to a `leads` table or CRM.
    # For now we'll just log it.
    print(f"Lead captured for page {page_id}: {payload}")
    return {"success": True, "message": "Lead captured"}
