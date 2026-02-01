from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import os
import inspect
import importlib
import pkgutil

# Import your agent base classes or structure if available
# from app.agents import ... 

router = APIRouter()

class OrgNode(BaseModel):
    id: str
    type: str # 'user', 'agent'
    label: str
    role: Optional[str] = None
    reports_to: Optional[str] = None # ID of manager
    status: str = 'active' # 'active', 'offline', 'busy'

class OrgChartResponse(BaseModel):
    nodes: List[OrgNode]

@router.get("/org-chart", response_model=OrgChartResponse)
async def get_org_chart():
    """
    Returns the dynamic organization chart of the hybrid workforce.
    Aggregates:
    1. The Human User (Director)
    2. Available AI Agents (scanned from filesystem)
    """
    nodes = []

    # 1. The Human Director (Mocked for now, or fetch from DB user session)
    # In a real app, we'd get the current user. Here we default to "Director".
    user_id = "user-001"
    nodes.append(OrgNode(
        id=user_id,
        type="user",
        label="You (Director)",
        role="Human Executive",
        status="active"
    ))

    # 2. Dynamic Agent Discovery
    # We scan the app/agents directory
    agents_root = os.path.join(os.getcwd(), "app", "agents")
    
    # Categories based on folder names
    if os.path.exists(agents_root):
        for item in os.listdir(agents_root):
            item_path = os.path.join(agents_root, item)
            if os.path.isdir(item_path) and not item.startswith("__") and item != "tools":
                agent_name = item.replace("_", " ").title()
                agent_id = f"agent-{item}"
                
                # Check for agent.py existence to confirm it's a real agent
                if os.path.exists(os.path.join(item_path, "agent.py")) or \
                   os.path.exists(os.path.join(item_path, "__init__.py")):
                    
                    nodes.append(OrgNode(
                        id=agent_id,
                        type="agent",
                        label=f"{agent_name} Agent",
                        role="AI Employee",
                        reports_to=user_id,
                        status="active"
                    ))

    return OrgChartResponse(nodes=nodes)
