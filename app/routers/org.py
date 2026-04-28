# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Organization Chart Router - Dynamic agent introspection endpoint."""


import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Agent -> department mapping for decision log queries
# ---------------------------------------------------------------------------

AGENT_FOLDER_TO_DEPT: dict[str, str] = {
    "financial": "FINANCIAL",
    "content": "CONTENT",
    "strategic": "STRATEGIC",
    "sales": "SALES",
    "marketing": "MARKETING",
    "operations": "OPERATIONS",
    "hr": "HR",
    "compliance": "COMPLIANCE",
    "customer_support": "SUPPORT",
    "data": "DATA",
}

# Workflow template categories that map to agent folders
AGENT_FOLDER_TO_CATEGORY: dict[str, str] = {
    "financial": "financial",
    "content": "content",
    "strategic": "strategic",
    "sales": "sales",
    "marketing": "marketing",
    "operations": "operations",
    "hr": "hr",
    "compliance": "compliance",
    "customer_support": "support",
    "data": "data",
}


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class OrgNode(BaseModel):
    """A single node in the organization chart."""

    id: str
    type: str  # 'user', 'agent'
    label: str
    role: str | None = None
    reports_to: str | None = None  # ID of manager
    status: str = "active"  # 'active', 'idle', 'offline', 'busy'
    # Introspection fields (populated for agent nodes)
    tools: list[str] = []
    tool_kinds: dict[str, str] = {}  # {tool_name: "action"|"knowledge"}
    tool_count: int = 0
    capabilities: str = ""
    model: str = ""
    # Live activity fields
    last_activity_at: str | None = None
    active_workflows: int = 0
    recent_decisions: int = 0


class OrgChartResponse(BaseModel):
    """Full org chart payload."""

    nodes: list[OrgNode]


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


def _get_tool_list(agent) -> list[str]:
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
# Tool kind classification (action vs knowledge)
# ---------------------------------------------------------------------------

_KNOWLEDGE_TOOLS: set[str] = {
    "hubspot_setup_guide",
    "security_checklist",
    "container_deployment_guide",
    "cloud_architecture_guide",
    "seo_fundamentals_guide",
    "product_roadmap_guide",
    "rag_architecture_guide",
    "use_skill",
    "list_available_skills",
    "generate_react_component",
    "build_portfolio",
    "generate_remotion_video",
}


def _build_tool_kinds(tools: list[str]) -> dict[str, str]:
    """Classify each tool as 'action' or 'knowledge'.

    Tools that call ``skills_registry.use_skill()`` or provide guidance are
    classified as ``"knowledge"``; all others are ``"action"``.
    """
    return {
        tool_name: "knowledge" if tool_name in _KNOWLEDGE_TOOLS else "action"
        for tool_name in tools
    }


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
        from app.agent import executive_agent
        from app.agents.specialized_agents import SPECIALIZED_AGENTS

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
        logger.warning(
            "Could not introspect live agents for org-chart; falling back to basic info",
            exc_info=True,
        )

    return registry


# Build once at import time (agents are singletons, so this is safe)
_AGENT_REGISTRY: dict = {}


def _ensure_registry() -> dict:
    """Lazy-init the agent registry on first request."""
    global _AGENT_REGISTRY
    if not _AGENT_REGISTRY:
        _AGENT_REGISTRY.update(_build_agent_registry())
    return _AGENT_REGISTRY


# ---------------------------------------------------------------------------
# Live data helpers
# ---------------------------------------------------------------------------


async def _fetch_last_activity(supabase: Any) -> dict[str, str]:
    """Return a mapping of agent_folder -> ISO timestamp of last session activity.

    Uses the ``sessions`` table ``updated_at`` column.  Each agent folder is
    mapped to its ADK agent name via the registry name_to_folder mapping, but
    since session_events store the ADK Event model (with ``author`` inside
    ``event_data``), we query session_events for the most recent event whose
    ``event_data->>'author'`` matches each agent's ADK name.
    """
    from app.services.supabase_async import execute_async

    # ADK agent names keyed by folder
    adk_names: dict[str, str] = {
        "financial": "FinancialAnalysisAgent",
        "content": "ContentCreationAgent",
        "strategic": "StrategicPlanningAgent",
        "sales": "SalesIntelligenceAgent",
        "marketing": "MarketingCampaignAgent",
        "operations": "OperationsAgent",
        "hr": "HRRecruitmentAgent",
        "compliance": "ComplianceRiskAgent",
        "customer_support": "CustomerSupportAgent",
        "data": "DataAnalyticsAgent",
    }

    result: dict[str, str] = {}
    for folder, adk_name in adk_names.items():
        try:
            res = await execute_async(
                supabase.table("session_events")
                .select("created_at")
                .eq("event_data->>author", adk_name)
                .order("created_at", desc=True)
                .limit(1),
                op_name=f"org.last_activity.{folder}",
                timeout=3.0,
            )
            if res.data:
                result[folder] = res.data[0]["created_at"]
        except Exception:
            logger.debug("Failed to fetch last activity for %s", folder, exc_info=True)
    return result


async def _fetch_active_workflows(supabase: Any) -> dict[str, int]:
    """Return a mapping of agent_folder -> count of running workflow executions.

    Joins ``workflow_executions`` with ``workflow_templates`` on ``template_id``
    and groups by template category.
    """
    from app.services.supabase_async import execute_async

    result: dict[str, int] = {}
    try:
        res = await execute_async(
            supabase.table("workflow_executions")
            .select("template_id, workflow_templates!inner(category)")
            .in_("status", ["running", "pending"]),
            op_name="org.active_workflows",
            timeout=3.0,
        )
        if res.data:
            # Reverse map: category -> folder
            category_to_folder = {v: k for k, v in AGENT_FOLDER_TO_CATEGORY.items()}
            for row in res.data:
                tpl = row.get("workflow_templates") or {}
                cat = (tpl.get("category") or "").lower()
                folder = category_to_folder.get(cat)
                if folder:
                    result[folder] = result.get(folder, 0) + 1
    except Exception:
        logger.debug("Failed to fetch active workflows for org chart", exc_info=True)
    return result


async def _fetch_recent_decisions(supabase: Any) -> dict[str, int]:
    """Return a mapping of agent_folder -> decision count in the last 24 hours.

    Queries ``department_decision_logs`` joined through ``departments`` by type.
    """
    from app.services.supabase_async import execute_async

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    result: dict[str, int] = {}

    # Reverse map: dept type -> folder
    dept_to_folder = {v: k for k, v in AGENT_FOLDER_TO_DEPT.items()}

    try:
        res = await execute_async(
            supabase.table("department_decision_logs")
            .select("department_id, departments!inner(type)")
            .gte("created_at", cutoff),
            op_name="org.recent_decisions",
            timeout=3.0,
        )
        if res.data:
            for row in res.data:
                dept = row.get("departments") or {}
                dept_type = (dept.get("type") or "").upper()
                folder = dept_to_folder.get(dept_type)
                if folder:
                    result[folder] = result.get(folder, 0) + 1
    except Exception:
        logger.debug("Failed to fetch recent decisions for org chart", exc_info=True)
    return result


def _compute_status(last_activity_at: str | None) -> str:
    """Return 'active' if last activity was within the last hour, else 'idle'."""
    if not last_activity_at:
        return "idle"
    try:
        ts = datetime.fromisoformat(last_activity_at.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - ts < timedelta(hours=1):
            return "active"
    except (ValueError, TypeError):
        pass
    return "idle"


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/org-chart", response_model=OrgChartResponse)
@limiter.limit(get_user_persona_limit)
async def get_org_chart(request: Request, _user_id: str = Depends(get_current_user_id)):
    """Return the dynamic organization chart of the hybrid workforce.

    Aggregates:
    1. The Human User (Director)
    2. Available AI Agents with introspection metadata (tools, model, capabilities)
    3. Live activity data (last activity, active workflows, recent decisions)
    """
    registry = _ensure_registry()

    # Fetch live data from Supabase (graceful degradation on failure)
    last_activity: dict[str, str] = {}
    active_workflows: dict[str, int] = {}
    recent_decisions: dict[str, int] = {}

    try:
        from app.services.supabase import get_service_client

        supabase = get_service_client()
        # Run all three queries concurrently
        import asyncio

        activity_task = _fetch_last_activity(supabase)
        workflows_task = _fetch_active_workflows(supabase)
        decisions_task = _fetch_recent_decisions(supabase)
        last_activity, active_workflows, recent_decisions = await asyncio.gather(
            activity_task,
            workflows_task,
            decisions_task,
        )
    except Exception:
        logger.warning(
            "Could not fetch live agent data for org-chart; using defaults",
            exc_info=True,
        )

    nodes: list[OrgNode] = []

    # 1. The Human Director
    user_id = "user-001"
    exec_meta = registry.get("__executive__", {})
    exec_tools = exec_meta.get("tools", [])
    nodes.append(
        OrgNode(
            id=user_id,
            type="user",
            label="You (Director)",
            role="Human Executive",
            status="active",
            tools=exec_tools,
            tool_kinds=_build_tool_kinds(exec_tools),
            tool_count=exec_meta.get("tool_count", 0),
            capabilities=exec_meta.get("capabilities", ""),
            model=exec_meta.get("model", ""),
        )
    )

    # 2. Dynamic Agent Discovery from the live agent registry
    import os

    agents_root = os.path.join(os.getcwd(), "app", "agents")

    if os.path.exists(agents_root):
        for item in sorted(os.listdir(agents_root)):
            item_path = os.path.join(agents_root, item)
            if (
                os.path.isdir(item_path)
                and not item.startswith("__")
                and item != "tools"
            ):
                # Confirm it's a real agent folder
                if os.path.exists(
                    os.path.join(item_path, "agent.py")
                ) or os.path.exists(os.path.join(item_path, "__init__.py")):
                    agent_name = item.replace("_", " ").title()
                    agent_id = f"agent-{item}"
                    meta = registry.get(item, {})

                    agent_last_activity = last_activity.get(item)
                    agent_status = _compute_status(agent_last_activity)
                    agent_tools = meta.get("tools", [])

                    nodes.append(
                        OrgNode(
                            id=agent_id,
                            type="agent",
                            label=f"{agent_name} Agent",
                            role=meta.get("role", "AI Employee"),
                            reports_to=user_id,
                            status=agent_status,
                            tools=agent_tools,
                            tool_kinds=_build_tool_kinds(agent_tools),
                            tool_count=meta.get("tool_count", 0),
                            capabilities=meta.get("capabilities", ""),
                            model=meta.get("model", ""),
                            last_activity_at=agent_last_activity,
                            active_workflows=active_workflows.get(item, 0),
                            recent_decisions=recent_decisions.get(item, 0),
                        )
                    )

    return OrgChartResponse(nodes=nodes)
