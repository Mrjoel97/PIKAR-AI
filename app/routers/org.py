"""Organization Chart Router - Dynamic agent introspection endpoint."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import limiter, get_user_persona_limit

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class OrgNode(BaseModel):
    """A single node in the organization chart."""

    id: str
    type: str  # 'user', 'agent'
    label: str
    role: Optional[str] = None
    reports_to: Optional[str] = None  # ID of manager
    status: str = "active"  # 'active', 'offline', 'busy'
    # Introspection fields (populated for agent nodes)
    tools: List[str] = []
    tool_count: int = 0
    capabilities: str = ""
    model: str = ""


class OrgChartResponse(BaseModel):
    """Full org chart payload."""

    nodes: List[OrgNode]


# ---------------------------------------------------------------------------
# Agent metadata helpers
# ---------------------------------------------------------------------------

def _tool_name(tool) -> str:
    """Extract a human-readable name from any ADK tool object."""
    # Function tools have __name__; wrapped tools may expose .name
    for attr in ("name", "__name__"):
        val = getattr(tool, attr, None)
        if val and isinstance(val, str):
            return val
    return str(tool)


def _model_label(agent) -> str:
    """Extract the model identifier string from an ADK agent."""
    model_obj = getattr(agent, "model", None)
    if model_obj is None:
        return ""
    # Gemini wrapper stores the model name in .model attribute
    model_name = getattr(model_obj, "model", None)
    if model_name and isinstance(model_name, str):
        return model_name
    return str(model_obj)


def _capabilities_from_description(agent) -> str:
    """Build a capabilities summary from the agent's description field."""
    desc = getattr(agent, "description", "") or ""
    # The description often has the format "Role - detailed capabilities"
    if " - " in desc:
        return desc.split(" - ", 1)[1]
    return desc


def _get_tool_list(agent) -> List[str]:
    """Return a sorted list of unique tool names for the agent."""
    tools = getattr(agent, "tools", None) or []
    names: list[str] = []
    for t in tools:
        name = _tool_name(t)
        if name not in names:
            names.append(name)
    names.sort()
    return names


# ---------------------------------------------------------------------------
# Agent introspection registry
# ---------------------------------------------------------------------------

def _build_agent_registry() -> dict:
    """Build a mapping of folder_name -> agent metadata from live ADK agents.

    This imports the SPECIALIZED_AGENTS list (and executive_agent) once and
    caches metadata so the endpoint is fast.
    """
    registry: dict[str, dict] = {}

    try:
        from app.agents.specialized_agents import SPECIALIZED_AGENTS
        from app.agent import executive_agent

        # Executive agent metadata (used for the director node)
        exec_tools = _get_tool_list(executive_agent)
        registry["__executive__"] = {
            "tools": exec_tools,
            "tool_count": len(exec_tools),
            "capabilities": "Central orchestrator, task delegation, cross-domain coordination, workflow management",
            "model": _model_label(executive_agent),
        }

        # Map ADK agent name -> folder key used by filesystem scan
        # ADK agent names: FinancialAnalysisAgent, ContentCreationAgent, etc.
        name_to_folder: dict[str, str] = {
            "FinancialAnalysisAgent": "financial",
            "ContentCreationAgent": "content",
            "StrategicPlanningAgent": "strategic",
            "SalesIntelligenceAgent": "sales",
            "MarketingCampaignAgent": "marketing",
            "OperationsAgent": "operations",
            "HRRecruitmentAgent": "hr",
            "ComplianceRiskAgent": "compliance",
            "CustomerSupportAgent": "customer_support",
            "DataAnalyticsAgent": "data",
        }

        for agent in SPECIALIZED_AGENTS:
            agent_name = getattr(agent, "name", "")
            folder = name_to_folder.get(agent_name)
            if not folder:
                # Fallback: derive folder from agent name
                folder = (
                    agent_name.replace("Agent", "")
                    .replace("Analysis", "")
                    .replace("Intelligence", "")
                    .replace("Campaign", "")
                    .replace("Recruitment", "")
                    .replace("Risk", "")
                    .replace("Analytics", "")
                    .replace("Planning", "")
                    .replace("Creation", "")
                    .replace("Support", "")
                    .strip()
                    .lower()
                )

            tools = _get_tool_list(agent)
            registry[folder] = {
                "tools": tools,
                "tool_count": len(tools),
                "capabilities": _capabilities_from_description(agent),
                "model": _model_label(agent),
                "role": getattr(agent, "description", "AI Employee") or "AI Employee",
            }

    except Exception:
        logger.warning("Could not introspect live agents for org-chart; falling back to basic info", exc_info=True)

    return registry


# Build once at import time (agents are singletons, so this is safe)
_AGENT_REGISTRY: dict = {}


def _ensure_registry() -> dict:
    """Lazy-init the agent registry on first request."""
    global _AGENT_REGISTRY  # noqa: PLW0603
    if not _AGENT_REGISTRY:
        _AGENT_REGISTRY.update(_build_agent_registry())
    return _AGENT_REGISTRY


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/org-chart", response_model=OrgChartResponse)
@limiter.limit(get_user_persona_limit)
async def get_org_chart(request: Request):
    """Return the dynamic organization chart of the hybrid workforce.

    Aggregates:
    1. The Human User (Director)
    2. Available AI Agents with introspection metadata (tools, model, capabilities)
    """
    registry = _ensure_registry()
    nodes: list[OrgNode] = []

    # 1. The Human Director
    user_id = "user-001"
    exec_meta = registry.get("__executive__", {})
    nodes.append(OrgNode(
        id=user_id,
        type="user",
        label="You (Director)",
        role="Human Executive",
        status="active",
        tools=exec_meta.get("tools", []),
        tool_count=exec_meta.get("tool_count", 0),
        capabilities=exec_meta.get("capabilities", ""),
        model=exec_meta.get("model", ""),
    ))

    # 2. Dynamic Agent Discovery from the live agent registry
    import os

    agents_root = os.path.join(os.getcwd(), "app", "agents")

    if os.path.exists(agents_root):
        for item in sorted(os.listdir(agents_root)):
            item_path = os.path.join(agents_root, item)
            if os.path.isdir(item_path) and not item.startswith("__") and item != "tools":
                # Confirm it's a real agent folder
                if os.path.exists(os.path.join(item_path, "agent.py")) or \
                   os.path.exists(os.path.join(item_path, "__init__.py")):

                    agent_name = item.replace("_", " ").title()
                    agent_id = f"agent-{item}"
                    meta = registry.get(item, {})

                    nodes.append(OrgNode(
                        id=agent_id,
                        type="agent",
                        label=f"{agent_name} Agent",
                        role=meta.get("role", "AI Employee"),
                        reports_to=user_id,
                        status="active",
                        tools=meta.get("tools", []),
                        tool_count=meta.get("tool_count", 0),
                        capabilities=meta.get("capabilities", ""),
                        model=meta.get("model", ""),
                    ))

    return OrgChartResponse(nodes=nodes)
