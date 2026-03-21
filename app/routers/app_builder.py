"""App Builder router — project creation and GSD stage transitions."""

import logging
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routers.onboarding import get_current_user_id
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
