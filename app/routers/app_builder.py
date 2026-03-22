"""App Builder router — project creation and GSD stage transitions."""

import json
import logging
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.routers.onboarding import get_current_user_id
from app.services.design_brief_service import _generate_build_plan, run_design_research
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter()

APP_BUILDER_STAGES = Literal[
    "questioning", "research", "brief", "building", "verifying", "shipping", "done"
]


class ProjectCreateRequest(BaseModel):
    """Request body for creating a new app project."""

    title: str
    creative_brief: dict = {}


class StageAdvanceRequest(BaseModel):
    """Request body for advancing the build session stage."""

    stage: APP_BUILDER_STAGES


class ApproveBriefRequest(BaseModel):
    """Payload for approving the design brief and locking the design system."""

    design_system: dict
    sitemap: list[dict]
    raw_markdown: str


@router.post("/app-builder/projects", status_code=201)
async def create_project(
    body: ProjectCreateRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Create a new app project and linked build session at stage='questioning'."""
    supabase = get_service_client()
    project_id = str(uuid.uuid4())
    project_data = {
        "id": project_id,
        "user_id": user_id,
        "title": body.title,
        "status": "draft",
        "stage": "questioning",
        "creative_brief": body.creative_brief,
    }
    result = supabase.table("app_projects").insert(project_data).execute()
    supabase.table("build_sessions").insert(
        {
            "project_id": project_id,
            "user_id": user_id,
            "stage": "questioning",
            "state": {"answers": body.creative_brief},
            "messages": [],
        }
    ).execute()
    return result.data[0]


@router.get("/app-builder/projects/{project_id}")
async def get_project(
    project_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Fetch a single app project by ID, scoped to the requesting user."""
    supabase = get_service_client()
    result = (
        supabase.table("app_projects")
        .select("*")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return result.data[0]


@router.patch("/app-builder/projects/{project_id}/stage")
async def advance_stage(
    project_id: str,
    body: StageAdvanceRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Advance the GSD stage on both app_projects and build_sessions."""
    supabase = get_service_client()
    result = (
        supabase.table("app_projects")
        .update({"stage": body.stage})
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    supabase.table("build_sessions").update({"stage": body.stage}).eq(
        "project_id", project_id
    ).eq("user_id", user_id).execute()
    return result.data[0]


@router.post("/app-builder/projects/{project_id}/research")
async def research_project(
    project_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> StreamingResponse:
    """Stream design research progress as Server-Sent Events.

    Fetches the project's creative brief, runs parallel Tavily web research,
    synthesises a design system via Gemini Flash, and streams progress events.
    """
    supabase = get_service_client()
    result = (
        supabase.table("app_projects")
        .select("creative_brief, stage")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    project = result.data
    creative_brief = project.get("creative_brief") or {}

    async def event_generator():
        """Iterate research steps and yield SSE-formatted data lines."""
        async for event in run_design_research(
            creative_brief=creative_brief,
            project_id=project_id,
            user_id=user_id,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/app-builder/projects/{project_id}/approve-brief")
async def approve_brief(
    project_id: str,
    body: ApproveBriefRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Lock the design system, generate a build plan, and advance stage to 'building'.

    This endpoint is the explicit approval gate between the research phase and
    screen generation. Once called the design system is locked and the build plan
    is persisted — no further design changes are allowed without creating a new project.
    """
    supabase = get_service_client()

    # Lock the design system row
    supabase.table("design_systems").update(
        {
            "locked": True,
            "colors": body.design_system.get("colors", {}),
            "typography": body.design_system.get("typography", {}),
            "spacing": body.design_system.get("spacing", {}),
            "raw_markdown": body.raw_markdown,
        }
    ).eq("project_id", project_id).execute()

    # Generate the phased build plan
    build_plan = await _generate_build_plan(body.sitemap, body.design_system)

    # Advance app_projects to building stage
    supabase.table("app_projects").update(
        {
            "design_system": body.design_system,
            "sitemap": body.sitemap,
            "build_plan": build_plan,
            "stage": "building",
            "status": "generating",
        }
    ).eq("id", project_id).eq("user_id", user_id).execute()

    # Advance the linked build session
    supabase.table("build_sessions").update({"stage": "building"}).eq(
        "project_id", project_id
    ).execute()

    return {"success": True, "build_plan": build_plan, "stage": "building"}
