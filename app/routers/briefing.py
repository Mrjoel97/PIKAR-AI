from fastapi import APIRouter, HTTPException, Request
from app.middleware.rate_limiter import limiter, get_user_persona_limit
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.routers.approvals import get_pending_approvals
from app.routers.org import get_org_chart

router = APIRouter()

class AgentSummary(BaseModel):
    label: str
    role: Optional[str] = None
    status: str = "active"


class BriefingData(BaseModel):
    greeting: str
    pending_approvals: List[Dict[str, Any]]
    online_agents: int
    agents: List[AgentSummary]  # For workspace "Agents online" card
    system_status: str

@router.get("/briefing")
@limiter.limit(get_user_persona_limit)
async def get_briefing(request: Request):
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
        approvals = await get_pending_approvals(request)

        # 3. Agent Status (for workspace "Agents online" card)
        org_data = await get_org_chart(request)
        agent_nodes = [n for n in org_data.nodes if n.type == "agent"]
        online_agents = len(agent_nodes)
        agents = [
            AgentSummary(label=n.label, role=n.role, status=n.status)
            for n in agent_nodes
        ]

        return BriefingData(
            greeting=greeting,
            pending_approvals=approvals,
            online_agents=online_agents,
            agents=agents,
            system_status="All Systems Operational"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
