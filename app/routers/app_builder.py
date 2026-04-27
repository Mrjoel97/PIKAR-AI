# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""App Builder router — project creation, GSD stage transitions, and screen generation."""

import json
import logging
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.design_brief_service import _generate_build_plan, run_design_research
from app.services.iteration_service import (
    _get_locked_design_markdown,
    edit_screen_variant,
)
from app.services.multi_page_service import build_all_pages, inject_navigation_links
from app.services.screen_generation_service import (
    generate_device_variant,
    generate_screen_variants,
)
from app.services.ship_service import ship_project
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


class IterateScreenRequest(BaseModel):
    """Request body for iterating on an existing screen variant via Stitch edit_screens."""

    change_description: str


class UpdateSitemapRequest(BaseModel):
    """Request body for updating the project sitemap and clearing the stale build plan."""

    sitemap: list[dict]


class ShipRequest(BaseModel):
    """Request body for shipping a project — generate selected output targets."""

    targets: list[Literal["react", "pwa", "capacitor", "video"]]


@router.post("/app-builder/projects", status_code=201)
@limiter.limit(get_user_persona_limit)
async def create_project(
    request: Request,
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
@limiter.limit(get_user_persona_limit)
async def get_project(
    request: Request,
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
@limiter.limit(get_user_persona_limit)
async def advance_stage(
    request: Request,
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
@limiter.limit(get_user_persona_limit)
async def research_project(
    request: Request,
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
@limiter.limit(get_user_persona_limit)
async def approve_brief(
    request: Request,
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
@limiter.limit(get_user_persona_limit)
async def generate_screen(
    request: Request,
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

        service = await get_stitch_service(user_id)
        stitch_proj = await service.call_tool(
            "create_project", {"name": project.get("title", "App")}
        )
        stitch_project_id = stitch_proj.get("id") or stitch_proj.get("projectId", "")
        supabase.table("app_projects").update(
            {"stitch_project_id": stitch_project_id}
        ).eq("id", project_id).eq("user_id", user_id).execute()

    from app.services.prompt_enhancer import enhance_prompt

    raw_prompt = _build_generation_prompt(body.screen_name, body.page_slug, design_system)
    prompt = await enhance_prompt(raw_prompt)

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
@limiter.limit(get_user_persona_limit)
async def generate_screen_device_variant(
    request: Request,
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
@limiter.limit(get_user_persona_limit)
async def list_screen_variants(
    request: Request,
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
@limiter.limit(get_user_persona_limit)
async def select_variant(
    request: Request,
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


# ---------------------------------------------------------------------------
# POST /app-builder/projects/{project_id}/screens/{screen_id}/iterate  (SSE)
# ---------------------------------------------------------------------------


@router.post("/app-builder/projects/{project_id}/screens/{screen_id}/iterate")
@limiter.limit(get_user_persona_limit)
async def iterate_screen(
    request: Request,
    project_id: str,
    screen_id: str,
    body: IterateScreenRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> StreamingResponse:
    """Stream screen iteration as Server-Sent Events via Stitch edit_screens.

    Fetches the project's stitch_project_id and the currently selected variant's
    stitch_screen_id, computes the next iteration number server-side, and streams
    edit_screen_variant events. Optionally injects the locked design system as a
    prompt prefix to maintain visual consistency.
    """
    supabase = get_service_client()

    # Fetch project to get stitch_project_id
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

    # Fetch the currently selected variant for this screen
    variant_result = (
        supabase.table("screen_variants")
        .select("stitch_screen_id, iteration")
        .eq("screen_id", screen_id)
        .eq("user_id", user_id)
        .eq("is_selected", True)
        .limit(1)
        .execute()
    )
    if not variant_result.data:
        raise HTTPException(status_code=404, detail="No selected variant found for this screen")

    selected_variant = variant_result.data[0]
    stitch_screen_id = selected_variant.get("stitch_screen_id") or ""

    # Compute next iteration server-side: MAX(iteration) + 1
    max_result = (
        supabase.table("screen_variants")
        .select("iteration")
        .eq("screen_id", screen_id)
        .order("iteration", desc=True)
        .limit(1)
        .execute()
    )
    current_max = 1
    if max_result.data:
        current_max = max_result.data[0].get("iteration", 1)
    next_iteration = current_max + 1

    # Fetch locked design system markdown (None if unlocked)
    design_system_markdown = await _get_locked_design_markdown(project_id, user_id)

    async def event_generator():
        """Yield SSE-formatted lines from the iteration generator."""
        async for event in edit_screen_variant(
            project_id=project_id,
            screen_id=screen_id,
            user_id=user_id,
            stitch_project_id=stitch_project_id,
            stitch_screen_id=stitch_screen_id,
            change_description=body.change_description,
            design_system_markdown=design_system_markdown,
            iteration_number=next_iteration,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GET /app-builder/projects/{project_id}/screens/{screen_id}/history
# ---------------------------------------------------------------------------


@router.get("/app-builder/projects/{project_id}/screens/{screen_id}/history")
@limiter.limit(get_user_persona_limit)
async def screen_history(
    request: Request,
    project_id: str,
    screen_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> list:
    """Return all variants for a screen ordered by iteration DESC then created_at DESC.

    Verifies project ownership before returning results.
    """
    supabase = get_service_client()

    # Verify project ownership
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
        .order("iteration", desc=True)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


# ---------------------------------------------------------------------------
# POST /app-builder/projects/{project_id}/screens/{screen_id}/rollback/{variant_id}
# ---------------------------------------------------------------------------


@router.post(
    "/app-builder/projects/{project_id}/screens/{screen_id}/rollback/{variant_id}"
)
@limiter.limit(get_user_persona_limit)
async def rollback_variant(
    request: Request,
    project_id: str,
    screen_id: str,
    variant_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Roll back to a specific screen variant by selecting it and deselecting all others.

    Uses the same deselect-all / select-one pattern as the existing select_variant
    endpoint. Verifies project ownership before performing updates.
    """
    supabase = get_service_client()

    # Verify project ownership
    proj_check = (
        supabase.table("app_projects")
        .select("id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not proj_check.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Deselect all variants for this screen
    supabase.table("screen_variants").update({"is_selected": False}).eq(
        "screen_id", screen_id
    ).execute()

    # Select the rollback target (scoped to user_id for safety)
    supabase.table("screen_variants").update({"is_selected": True}).eq(
        "id", variant_id
    ).eq("user_id", user_id).execute()

    return {"success": True, "selected_variant_id": variant_id}


# ---------------------------------------------------------------------------
# POST /app-builder/projects/{project_id}/screens/{screen_id}/approve
# ---------------------------------------------------------------------------


@router.post("/app-builder/projects/{project_id}/screens/{screen_id}/approve")
@limiter.limit(get_user_persona_limit)
async def approve_screen(
    request: Request,
    project_id: str,
    screen_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Set app_screens.approved=True for the given screen.

    Does NOT advance the GSD stage — stage advancement is a separate explicit user
    action via the existing PATCH /stage endpoint after all screens are approved.
    """
    supabase = get_service_client()

    # Update app_screens.approved for this screen (scoped to user_id)
    supabase.table("app_screens").update({"approved": True}).eq(
        "id", screen_id
    ).eq("user_id", user_id).execute()

    return {"success": True, "screen_id": screen_id, "approved": True}


# ---------------------------------------------------------------------------
# POST /app-builder/projects/{project_id}/build-all  (SSE)
# ---------------------------------------------------------------------------


@router.post("/app-builder/projects/{project_id}/build-all")
@limiter.limit(get_user_persona_limit)
async def build_all(
    request: Request,
    project_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> StreamingResponse:
    """Stream multi-page build progress as Server-Sent Events via the baton loop.

    Fetches the project's sitemap and stitch_project_id, retrieves the locked
    design system markdown, then streams ``build_all_pages`` events. After the
    final ``build_complete`` event, calls ``inject_navigation_links`` to rewrite
    inter-page nav hrefs. The nav injection step is non-fatal.
    """
    supabase = get_service_client()
    result = (
        supabase.table("app_projects")
        .select("sitemap, stitch_project_id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    project = result.data
    sitemap: list[dict] = project.get("sitemap") or []
    stitch_project_id: str = project.get("stitch_project_id") or ""

    design_markdown = await _get_locked_design_markdown(project_id, user_id)
    if design_markdown is None:
        design_markdown = ""

    async def event_generator():
        """Yield SSE-formatted lines from build_all_pages; inject nav links at end."""
        last_build_complete: dict | None = None
        async for event in build_all_pages(
            project_id=project_id,
            user_id=user_id,
            sitemap=sitemap,
            design_markdown=design_markdown,
            stitch_project_id=stitch_project_id,
        ):
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("step") == "build_complete":
                last_build_complete = event

        if last_build_complete is not None:
            screens = last_build_complete.get("screens", [])
            try:
                await inject_navigation_links(screens, user_id, project_id)
            except Exception:
                logger.warning("inject_navigation_links failed — non-fatal, skipping")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GET /app-builder/projects/{project_id}/screens
# ---------------------------------------------------------------------------


@router.get("/app-builder/projects/{project_id}/screens")
@limiter.limit(get_user_persona_limit)
async def list_project_screens(
    request: Request,
    project_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> list:
    """Return all app_screens for a project with each screen's selected variant html_url.

    Runs two sequential queries — one for screens ordered by order_index, one for
    selected variants — then merges html_url onto each screen dict before returning.
    Supabase REST does not support cross-table joins so the merge is done Python-side.
    """
    supabase = get_service_client()

    # Fetch all screens for this project (user ownership enforced)
    screens_result = (
        supabase.table("app_screens")
        .select("id, name, page_slug, device_type, order_index, approved")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .order("order_index")
        .execute()
    )
    screens: list[dict] = screens_result.data or []
    if not screens:
        return []

    # Fetch selected variants for all screens in this project
    screen_ids = [s["id"] for s in screens]
    variants_result = (
        supabase.table("screen_variants")
        .select("screen_id, html_url")
        .eq("is_selected", True)
        .execute()
    )
    all_selected: list[dict] = variants_result.data or []

    # Build lookup: screen_id -> html_url
    html_url_map: dict[str, str] = {
        v["screen_id"]: v.get("html_url", "")
        for v in all_selected
        if v.get("screen_id") in screen_ids
    }

    # Merge html_url into each screen dict
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "page_slug": s["page_slug"],
            "device_type": s.get("device_type"),
            "order_index": s.get("order_index"),
            "approved": s.get("approved", False),
            "html_url": html_url_map.get(s["id"], ""),
        }
        for s in screens
    ]


# ---------------------------------------------------------------------------
# PATCH /app-builder/projects/{project_id}/sitemap
# ---------------------------------------------------------------------------


@router.patch("/app-builder/projects/{project_id}/sitemap")
@limiter.limit(get_user_persona_limit)
async def update_sitemap(
    request: Request,
    project_id: str,
    body: UpdateSitemapRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Update the project sitemap and clear the stale build plan.

    Replaces ``app_projects.sitemap`` with the new value and sets ``build_plan``
    to ``[]`` so a subsequent ``POST /build-all`` will rebuild from scratch with
    the revised page set.
    """
    supabase = get_service_client()

    result = (
        supabase.table("app_projects")
        .update({"sitemap": body.sitemap, "build_plan": []})
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"success": True, "sitemap": body.sitemap}


# ---------------------------------------------------------------------------
# POST /app-builder/projects/{project_id}/ship  (SSE)
# ---------------------------------------------------------------------------


@router.post("/app-builder/projects/{project_id}/ship")
@limiter.limit(get_user_persona_limit)
async def ship(
    request: Request,
    project_id: str,
    body: ShipRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> StreamingResponse:
    """Stream ship stage progress as Server-Sent Events.

    Validates that the project exists and belongs to the requesting user, then
    streams ``ship_project`` events for each selected output target. Events include
    ``target_started``, ``target_complete`` (with download URL), ``target_failed``
    (with error string), and a final ``ship_complete`` (with downloads dict).
    Individual target failures do not abort the remaining targets.
    """
    supabase = get_service_client()
    proj_result = (
        supabase.table("app_projects")
        .select("id")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not proj_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    async def event_generator():
        """Yield SSE-formatted lines from the ship_project async generator."""
        async for event in ship_project(project_id, user_id, body.targets):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# POST /app-builder/projects/{project_id}/start-autopilot
# ---------------------------------------------------------------------------


class StartAutopilotRequest(BaseModel):
    """Body for POST /app-builder/projects/<id>/start-autopilot."""

    session_id: str


@router.post("/app-builder/projects/{project_id}/start-autopilot")
@limiter.limit(get_user_persona_limit)
async def start_autopilot(
    request: Request,
    project_id: str,
    body: StartAutopilotRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Kick off autopilot for a project.

    Idempotent: returns 409 if autopilot is already running for this project.
    Returns the updated project row on success.
    """
    supabase = get_service_client()
    result = (
        supabase.table("app_projects")
        .select("id, autopilot_status, stage")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    current = result.data.get("autopilot_status") or "idle"
    if current not in ("idle", "failed", "done"):
        raise HTTPException(
            status_code=409,
            detail=f"Autopilot is already active for this project (state={current}).",
        )

    update = (
        supabase.table("app_projects")
        .update(
            {
                "autopilot_status": "running",
                "autopilot_session_id": body.session_id,
                "autopilot_error": None,
            }
        )
        .eq("id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    # NOTE: actual orchestrator task is scheduled in Task 9.
    # For now, the endpoint just transitions state synchronously.
    return update.data[0]
