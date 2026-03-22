"""App Builder router — project creation, GSD stage transitions, and screen generation."""

import json
import logging
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.routers.onboarding import get_current_user_id
from app.services.design_brief_service import _generate_build_plan, run_design_research
from app.services.screen_generation_service import (
    generate_device_variant,
    generate_screen_variants,
)
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


class GenerateScreenRequest(BaseModel):
    """Request body for generating screen variants via Stitch MCP."""

    screen_name: str
    page_slug: str
    num_variants: int = 3


class GenerateDeviceVariantRequest(BaseModel):
    """Request body for generating a device-specific screen variant."""

    device_type: Literal["MOBILE", "TABLET"]
    prompt_used: str


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
    ).eq("project_id", project_id).eq("user_id", user_id).execute()

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


# ---------------------------------------------------------------------------
# Screen generation helpers
# ---------------------------------------------------------------------------


def _build_generation_prompt(
    screen_name: str,
    page_slug: str,
    design_system: dict,
) -> str:
    """Build a Stitch-optimised generation prompt from screen info and design tokens.

    Args:
        screen_name: Human-readable screen name (e.g. "Home Page").
        page_slug: URL slug (e.g. "home") for context.
        design_system: Design system JSONB dict with colors and typography.

    Returns:
        A single prompt string with design constraints injected.
    """
    parts = [f"Generate a {screen_name} page"]
    if design_system:
        colors = design_system.get("colors", [])
        if colors:
            palette = ", ".join(
                c.get("hex", "") for c in colors if isinstance(c, dict) and c.get("hex")
            )
            if palette:
                parts.append(f"Color palette: {palette}")
        typo = design_system.get("typography", {})
        if typo:
            heading = typo.get("heading", "")
            body = typo.get("body", "")
            if heading or body:
                parts.append(f"Heading font: {heading}, Body font: {body}")
    return ". ".join(parts)


# ---------------------------------------------------------------------------
# POST /app-builder/projects/{project_id}/generate-screen  (SSE)
# ---------------------------------------------------------------------------


@router.post("/app-builder/projects/{project_id}/generate-screen")
async def generate_screen(
    project_id: str,
    body: GenerateScreenRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> StreamingResponse:
    """Stream screen variant generation as Server-Sent Events.

    Fetches the project's design system and stitch_project_id, builds a
    design-system-aware prompt, then streams generate_screen_variants events.
    If the project has no stitch_project_id yet, creates one via Stitch and
    persists it before generation begins.
    """
    supabase = get_service_client()
    result = (
        supabase.table("app_projects")
        .select("title, build_plan, design_system, status, stitch_project_id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    project = result.data
    design_system = project.get("design_system") or {}
    stitch_project_id = project.get("stitch_project_id") or ""

    # Create a Stitch project on first screen generation if not already present
    if not stitch_project_id:
        from app.services.stitch_mcp import get_stitch_service

        service = get_stitch_service()
        stitch_proj = await service.call_tool(
            "create_project", {"name": project.get("title", "App")}
        )
        stitch_project_id = stitch_proj.get("id") or stitch_proj.get("projectId", "")
        supabase.table("app_projects").update(
            {"stitch_project_id": stitch_project_id}
        ).eq("id", project_id).eq("user_id", user_id).execute()

    prompt = _build_generation_prompt(body.screen_name, body.page_slug, design_system)

    async def event_generator():
        """Yield SSE-formatted lines from the variant generator."""
        async for event in generate_screen_variants(
            project_id=project_id,
            user_id=user_id,
            screen_name=body.screen_name,
            page_slug=body.page_slug,
            prompt=prompt,
            stitch_project_id=stitch_project_id,
            num_variants=body.num_variants,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# POST /app-builder/projects/{project_id}/screens/{screen_id}/generate-device-variant  (SSE)
# ---------------------------------------------------------------------------


@router.post(
    "/app-builder/projects/{project_id}/screens/{screen_id}/generate-device-variant"
)
async def generate_screen_device_variant(
    project_id: str,
    screen_id: str,
    body: GenerateDeviceVariantRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> StreamingResponse:
    """Stream device-specific variant generation as Server-Sent Events.

    Verifies ownership of the parent screen, then streams generate_device_variant
    events for the requested device type (MOBILE or TABLET).
    """
    supabase = get_service_client()

    # Fetch the project to get stitch_project_id
    proj_result = (
        supabase.table("app_projects")
        .select("stitch_project_id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not proj_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    stitch_project_id = proj_result.data.get("stitch_project_id") or ""

    # Verify screen ownership
    screen_result = (
        supabase.table("app_screens")
        .select("id, user_id")
        .eq("id", screen_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not screen_result.data:
        raise HTTPException(status_code=404, detail="Screen not found")

    async def event_generator():
        """Yield SSE-formatted lines from the device variant generator."""
        async for event in generate_device_variant(
            screen_id=screen_id,
            user_id=user_id,
            prompt=body.prompt_used,
            stitch_project_id=stitch_project_id,
            device_type=body.device_type,
            project_id=project_id,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GET /app-builder/projects/{project_id}/screens/{screen_id}/variants
# ---------------------------------------------------------------------------


@router.get("/app-builder/projects/{project_id}/screens/{screen_id}/variants")
async def list_screen_variants(
    project_id: str,
    screen_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> list:
    """Return all variants for a screen, ordered by variant_index ascending."""
    supabase = get_service_client()

    # Verify the project belongs to the requesting user
    proj_check = (
        supabase.table("app_projects")
        .select("id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not proj_check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    result = (
        supabase.table("screen_variants")
        .select("*")
        .eq("screen_id", screen_id)
        .order("variant_index")
        .execute()
    )
    return result.data or []


# ---------------------------------------------------------------------------
# PATCH /app-builder/projects/{project_id}/screens/{screen_id}/variants/{variant_id}/select
# ---------------------------------------------------------------------------


@router.patch(
    "/app-builder/projects/{project_id}/screens/{screen_id}/variants/{variant_id}/select"
)
async def select_variant(
    project_id: str,
    screen_id: str,
    variant_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Mark one variant as selected and deselect all others for this screen.

    Performs two updates atomically (Supabase does not support transactions
    over REST, so deselect-all runs first then select-one).
    """
    supabase = get_service_client()

    # Deselect all variants for this screen
    supabase.table("screen_variants").update({"is_selected": False}).eq(
        "screen_id", screen_id
    ).execute()

    # Select the chosen variant (scoped to user_id for safety)
    supabase.table("screen_variants").update({"is_selected": True}).eq(
        "id", variant_id
    ).eq("user_id", user_id).execute()

    return {"success": True, "selected_variant_id": variant_id}
