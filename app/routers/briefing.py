from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import os
from app.routers.approvals import get_pending_approvals
from app.routers.org import get_org_chart

router = APIRouter()

class BriefingData(BaseModel):
    greeting: str
    pending_approvals: List[Dict[str, Any]]
    online_agents: int
    system_status: str

@router.get("/briefing")
async def get_briefing():
    """
    Aggregates data for the Morning Briefing Widget.
    """
    try:
        # 1. Greeting (Time based)
        # Note: In a real app we'd use the user's timezone.
        from datetime import datetime
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good Morning"
        elif hour < 18:
            greeting = "Good Afternoon"
        else:
            greeting = "Good Evening"

        # 2. Pending Approvals
        # We reuse the logic from approvals router (calling the function directly if possible, or re-implementing query)
        # Since get_pending_approvals is async and locally available, we can call it.
        # However, it depends on request context/auth sometimes. Here it's simple.
        approvals = await get_pending_approvals()

        # 3. Agent Status
        # Reuse org chart logic
        org_data = await get_org_chart()
        # Count agents (nodes that are type 'agent')
        online_agents = len([n for n in org_data.nodes if n.type == 'agent'])

        return BriefingData(
            greeting=greeting,
            pending_approvals=approvals,
            online_agents=online_agents,
            system_status="All Systems Operational"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
