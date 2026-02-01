from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.services.supabase import get_service_client
from app.services.department_runner import runner

router = APIRouter()

@router.get("/departments")
async def get_departments():
    """List all departments and their real-time state."""
    supabase = get_service_client()
    res = supabase.table("departments").select("*").order("name").execute()
    return res.data

@router.post("/departments/{id}/toggle")
async def toggle_department(id: str):
    """Start or Pause a department."""
    supabase = get_service_client()
    
    # Get current status
    curr = supabase.table("departments").select("status").eq("id", id).single().execute()
    if not curr.data:
        raise HTTPException(status_code=404, detail="Department not found")
        
    new_status = 'PAUSED' if curr.data['status'] == 'RUNNING' else 'RUNNING'
    
    supabase.table("departments").update({"status": new_status}).eq("id", id).execute()
    return {"status": new_status}

@router.post("/departments/tick")
async def manual_tick():
    """Manually trigger a heartbeat cycle (for testing/demo)."""
    results = await runner.tick()
    return {"results": results}
