# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""A2A Protocol API Router.

Provides REST endpoints for:
- Task status querying
- Agent registry CRUD
- Agent health checks
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import limiter, get_user_persona_limit
from app.routers.onboarding import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/a2a", tags=["A2A Protocol"])


# ── Request/Response Models ─────────────────────────────────────────────

class RegisterAgentRequest(BaseModel):
    name: str
    url: str
    description: str = ""
    auth_token: Optional[str] = None
    tags: Optional[List[str]] = None
    auto_discover: bool = True


class AgentResponse(BaseModel):
    id: Optional[str] = None
    name: str
    url: str
    description: str = ""
    status: str = "registered"
    capabilities: Optional[Dict[str, Any]] = None
    skills: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    last_health_check: Optional[str] = None


# ── Task Endpoints ──────────────────────────────────────────────────────

@router.get("/tasks/{task_id}")
@limiter.limit(get_user_persona_limit)
async def get_task_status(
    request: Request,
    task_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Query the status of an A2A task by ID."""
    try:
        from app.persistence.supabase_task_store import SupabaseTaskStore

        store = SupabaseTaskStore()
        task = store.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
        return task.model_dump(mode="json")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
@limiter.limit(get_user_persona_limit)
async def list_tasks(
    request: Request,
    status: Optional[str] = None,
    limit: int = 50,
    user_id: str = Depends(get_current_user_id),
):
    """List A2A tasks with optional status filter."""
    try:
        from app.services.supabase_client import get_service_client

        client = get_service_client()
        query = client.table("a2a_tasks").select("task_id, status, created_at, updated_at")

        if status:
            query = query.eq("status", status)

        res = query.order("updated_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Agent Registry Endpoints ───────────────────────────────────────────

@router.post("/agents/register")
@limiter.limit(get_user_persona_limit)
async def register_agent(
    request: Request,
    body: RegisterAgentRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Register an external A2A agent in the registry."""
    try:
        from app.a2a.registry import get_agent_registry

        registry = get_agent_registry()
        result = await registry.register(
            name=body.name,
            url=body.url,
            description=body.description,
            auth_token=body.auth_token,
            tags=body.tags,
            auto_discover=body.auto_discover,
        )
        return result
    except Exception as e:
        logger.error(f"Error registering agent: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agents")
@limiter.limit(get_user_persona_limit)
async def list_agents(
    request: Request,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    skill: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    """List registered A2A agents."""
    try:
        from app.a2a.registry import get_agent_registry

        registry = get_agent_registry()
        agents = await registry.list_agents(status=status, tag=tag, skill=skill)
        return agents
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}")
@limiter.limit(get_user_persona_limit)
async def get_agent(
    request: Request,
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get details of a registered agent."""
    try:
        from app.a2a.registry import get_agent_registry

        registry = get_agent_registry()
        agent = await registry.get(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_id}")
@limiter.limit(get_user_persona_limit)
async def unregister_agent(
    request: Request,
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Remove an agent from the registry."""
    try:
        from app.a2a.registry import get_agent_registry

        registry = get_agent_registry()
        deleted = await registry.unregister(agent_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"status": "deleted", "id": agent_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering agent: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/agents/{agent_id}/health-check")
@limiter.limit(get_user_persona_limit)
async def health_check_agent(
    request: Request,
    agent_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Run a health check on a registered agent."""
    try:
        from app.a2a.registry import get_agent_registry

        registry = get_agent_registry()
        result = await registry.health_check(agent_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error health-checking agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/send")
@limiter.limit(get_user_persona_limit)
async def send_to_agent(
    request: Request,
    agent_id: str,
    body: Dict[str, Any],
    user_id: str = Depends(get_current_user_id),
):
    """Send a message to a registered external agent and get the response."""
    try:
        from app.a2a.registry import get_agent_registry
        from app.a2a.client import A2AClient

        registry = get_agent_registry()
        agent = await registry.get(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        text = body.get("text", body.get("message", ""))
        if not text:
            raise HTTPException(status_code=400, detail="'text' or 'message' field required")

        async with A2AClient(agent["url"], auth_token=agent.get("auth_token")) as client:
            result = await client.send_message(
                text,
                context=body.get("context"),
                task_id=body.get("task_id"),
            )
            return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending to agent {agent_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Agent communication failed: {e}")
