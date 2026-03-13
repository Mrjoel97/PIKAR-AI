from fastapi import APIRouter, Depends, HTTPException, Request
from app.middleware.rate_limiter import limiter, get_user_persona_limit
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.personas.runtime import resolve_request_persona
from app.routers.approvals import get_pending_approvals
from app.routers.onboarding import get_current_user_id
from app.routers.org import get_org_chart
from app.services.dashboard_summary_service import get_dashboard_summary_service

router = APIRouter()


class AgentSummary(BaseModel):
    label: str
    role: Optional[str] = None
    status: str = 'active'


class BriefingData(BaseModel):
    greeting: str
    pending_approvals: List[Dict[str, Any]]
    online_agents: int
    agents: List[AgentSummary]
    system_status: str


@router.get('/briefing')
@limiter.limit(get_user_persona_limit)
async def get_briefing(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Aggregate data for the Morning Briefing widget."""
    try:
        from datetime import datetime

        hour = datetime.now().hour
        if hour < 12:
            greeting = 'Good Morning'
        elif hour < 18:
            greeting = 'Good Afternoon'
        else:
            greeting = 'Good Evening'

        approvals = await get_pending_approvals(request, user_id)
        org_data = await get_org_chart(request)
        agent_nodes = [n for n in org_data.nodes if n.type == 'agent']
        online_agents = len(agent_nodes)
        agents = [AgentSummary(label=n.label, role=n.role, status=n.status) for n in agent_nodes]

        return BriefingData(
            greeting=greeting,
            pending_approvals=approvals,
            online_agents=online_agents,
            agents=agents,
            system_status='All Systems Operational',
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/briefing/dashboard-summary')
@limiter.limit(get_user_persona_limit)
async def get_dashboard_summary(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Return persona-aware home data for the dashboard shell."""
    try:
        service = get_dashboard_summary_service()
        return await service.get_home_summary(
            user_id=user_id,
            persona=resolve_request_persona(request),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
