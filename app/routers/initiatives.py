# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Initiatives API: templates and create-from-template."""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.middleware.rate_limiter import limiter, get_user_persona_limit
from app.routers.onboarding import get_current_user_id
from app.services.initiative_service import InitiativeService
from app.services.supabase import get_service_client

router = APIRouter(prefix="/initiatives", tags=["Initiatives"])


class CreateFromTemplateRequest(BaseModel):
    template_id: str
    title_override: Optional[str] = None


class CreateFromJourneyRequest(BaseModel):
    journey_id: str
    title_override: Optional[str] = None
    desired_outcomes: Optional[str] = None
    timeline: Optional[str] = None


class CreateChecklistItemRequest(BaseModel):
    title: str
    phase: str
    description: Optional[str] = None
    status: str = "pending"
    owner_user_id: Optional[str] = None
    owner_label: Optional[str] = None
    due_at: Optional[datetime] = None
    evidence: list = Field(default_factory=list)
    sort_order: int = 0
    metadata: Optional[dict] = None


class UpdateChecklistItemRequest(BaseModel):
    title: Optional[str] = None
    phase: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    owner_user_id: Optional[str] = None
    owner_label: Optional[str] = None
    due_at: Optional[datetime] = None
    evidence: Optional[list] = None
    sort_order: Optional[int] = None
    metadata: Optional[dict] = None


@router.get("/templates")
@limiter.limit(get_user_persona_limit)
async def list_initiative_templates(
    request: Request,
    persona: Optional[str] = None,
    category: Optional[str] = None,
):
    """List initiative templates, optionally filtered by persona and category."""
    try:
        service = InitiativeService()
        templates = await service.list_templates(persona=persona, category=category)
        return {"templates": templates, "count": len(templates)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/from-template")
@limiter.limit(get_user_persona_limit)
async def create_initiative_from_template(
    request: Request,
    body: CreateFromTemplateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Create a new initiative from a predefined template."""
    try:
        service = InitiativeService()
        initiative = await service.create_from_template(
            template_id=body.template_id,
            user_id=user_id,
            title_override=body.title_override,
        )
        return {"initiative": initiative, "success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/from-journey")
@limiter.limit(get_user_persona_limit)
async def create_initiative_from_journey(
    request: Request,
    body: CreateFromJourneyRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Create a new initiative from a user journey (fetches journey from DB, then creates initiative)."""
    try:
        from app.services.supabase import get_service_client
        client = get_service_client()
        # Fetch journey (service client can read user_journeys)
        r = client.table("user_journeys").select("*").eq("id", body.journey_id).single().execute()
        if not r.data:
            raise HTTPException(status_code=404, detail="Journey not found")
        journey = r.data
        service = InitiativeService()
        initiative = await service.create_initiative(
            title=body.title_override or journey["title"],
            description=journey.get("description") or f'Initiative based on the "{journey["title"]}" user journey',
            priority="medium",
            user_id=user_id,
            phase="ideation",
            metadata={
                "source": "user_journey",
                "journey_id": journey["id"],
                "journey_title": journey["title"],
                "journey_stages": journey.get("stages") or [],
                "kpis": journey.get("kpis") or [],
                "desired_outcomes": body.desired_outcomes.strip() if isinstance(body.desired_outcomes, str) and body.desired_outcomes.strip() else None,
                "timeline": body.timeline.strip() if isinstance(body.timeline, str) and body.timeline.strip() else None,
            },
        )
        return {"initiative": initiative, "success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{initiative_id}/start-journey-workflow")
@limiter.limit(get_user_persona_limit)
async def start_journey_workflow_for_initiative(
    request: Request,
    initiative_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Start the journey workflow for an initiative created from a user journey.
    Uses the journey's primary workflow template and initiative context (desired_outcomes, timeline).
    """
    try:
        service = InitiativeService()
        initiative = await service.get_initiative(initiative_id, user_id=user_id)
        if not initiative:
            raise HTTPException(status_code=404, detail="Initiative not found")

        metadata = initiative.get("metadata") or {}
        desired_outcomes = metadata.get("desired_outcomes")
        timeline = metadata.get("timeline")

        if not isinstance(desired_outcomes, str) or not desired_outcomes.strip():
            desired_outcomes = "Not specified"
        if not isinstance(timeline, str) or not timeline.strip():
            timeline = "Not specified"
            
        # Update the initiative metadata with the defaults since they were missing

        client = get_service_client()
        journey_id = metadata.get("journey_id")
        if journey_id:
            journey_res = (
                client.table("user_journeys")
                .select("title, primary_workflow_template_name")
                .eq("id", journey_id)
                .limit(1)
                .execute()
            )
            if journey_res.data:
                journey = journey_res.data[0]
                await service.update_initiative(
                    initiative_id,
                    metadata={
                        "journey_id": journey_id,
                        "journey_title": journey.get("title"),
                        "workflow_template_name": journey.get("primary_workflow_template_name"),
                        "desired_outcomes": desired_outcomes,
                        "timeline": timeline,
                    },
                    user_id=user_id,
                )

        from app.services.request_context import set_current_user_id
        from app.agents.strategic.tools import start_journey_workflow as do_start_journey_workflow

        set_current_user_id(user_id)
        result = await do_start_journey_workflow(initiative_id)
        if not result.get("success"):
            if result.get("missing_inputs"):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": result.get("error", "Journey workflow requirements are not satisfied"),
                        "requirements_satisfied": False,
                        "missing_inputs": result.get("missing_inputs", []),
                    },
                )
            error_code = result.get("error_code")
            status_code = 400
            if error_code == "template_not_found":
                status_code = 404
            elif error_code in {"template_archived", "template_not_published", "workflow_not_ready"}:
                status_code = 409
            elif error_code in {"workflow_readiness_unavailable", "workflow_execution_infra_not_configured"}:
                status_code = 503
            detail = {
                "message": result.get("error", "Failed to start journey workflow"),
            }
            if error_code:
                detail["error_code"] = error_code
            if result.get("lifecycle_status"):
                detail["lifecycle_status"] = result.get("lifecycle_status")
            if result.get("readiness") is not None:
                detail["readiness"] = result.get("readiness")
            if result.get("missing_config") is not None:
                detail["missing_config"] = result.get("missing_config")
            if result.get("invalid_config") is not None:
                detail["invalid_config"] = result.get("invalid_config")
            raise HTTPException(
                status_code=status_code,
                detail=detail,
            )
        return {
            "success": True,
            "workflow_execution_id": result.get("workflow_execution_id"),
            "template_name": result.get("template_name"),
            "message": result.get("message", "Journey workflow started."),
            "requirements_satisfied": True,
            "missing_inputs": [],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreateFromBraindumpRequest(BaseModel):
    braindump_id: str


@router.post("/from-braindump")
@limiter.limit(get_user_persona_limit)
async def create_initiative_from_braindump(
    request: Request,
    body: CreateFromBraindumpRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Create a new initiative from a brain dump."""
    try:
        from app.agents.strategic.tools import start_initiative_from_idea
        from app.services.request_context import set_current_user_id
        set_current_user_id(user_id)
        result = await start_initiative_from_idea(braindump_id=body.braindump_id)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{initiative_id}/checklist")
@limiter.limit(get_user_persona_limit)
async def list_checklist_items(
    request: Request,
    initiative_id: str,
    phase: Optional[str] = None,
    status: Optional[str] = None,
    owner_label: Optional[str] = None,
    due_before: Optional[datetime] = None,
    due_after: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "sort_order",
    sort_order: str = "asc",
    user_id: str = Depends(get_current_user_id),
):
    """List persisted checklist items for an initiative."""
    try:
        service = InitiativeService()
        items = await service.list_checklist_items(
            initiative_id=initiative_id,
            user_id=user_id,
            phase=phase,
            status=status,
            owner_label=owner_label,
            due_before=due_before.isoformat() if due_before else None,
            due_after=due_after.isoformat() if due_after else None,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return {"items": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{initiative_id}/checklist")
@limiter.limit(get_user_persona_limit)
async def create_checklist_item(
    request: Request,
    initiative_id: str,
    body: CreateChecklistItemRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Create a persisted checklist item for an initiative."""
    try:
        service = InitiativeService()
        item = await service.create_checklist_item(
            initiative_id=initiative_id,
            user_id=user_id,
            title=body.title,
            phase=body.phase,
            description=body.description,
            status=body.status,
            owner_user_id=body.owner_user_id,
            owner_label=body.owner_label,
            due_at=body.due_at.isoformat() if body.due_at else None,
            evidence=body.evidence,
            sort_order=body.sort_order,
            metadata=body.metadata,
        )
        return {"item": item, "success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{initiative_id}/checklist/{item_id}")
@limiter.limit(get_user_persona_limit)
async def update_checklist_item(
    request: Request,
    initiative_id: str,
    item_id: str,
    body: UpdateChecklistItemRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Update a persisted checklist item for an initiative."""
    try:
        service = InitiativeService()
        item = await service.update_checklist_item(
            initiative_id=initiative_id,
            item_id=item_id,
            user_id=user_id,
            title=body.title,
            phase=body.phase,
            description=body.description,
            status=body.status,
            owner_user_id=body.owner_user_id,
            owner_label=body.owner_label,
            due_at=body.due_at.isoformat() if body.due_at else None,
            evidence=body.evidence,
            sort_order=body.sort_order,
            metadata=body.metadata,
        )
        return {"item": item, "success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{initiative_id}/checklist/{item_id}")
@limiter.limit(get_user_persona_limit)
async def delete_checklist_item(
    request: Request,
    initiative_id: str,
    item_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Delete (soft delete) checklist item."""
    try:
        service = InitiativeService()
        deleted = await service.delete_checklist_item(
            initiative_id=initiative_id,
            item_id=item_id,
            user_id=user_id,
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{initiative_id}/checklist/events")
@limiter.limit(get_user_persona_limit)
async def list_checklist_events(
    request: Request,
    initiative_id: str,
    limit: int = 100,
    offset: int = 0,
    event_type: Optional[str] = None,
    item_id: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    """List checklist audit events for an initiative."""
    try:
        service = InitiativeService()
        events = await service.list_checklist_events(
            initiative_id=initiative_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
            event_type=event_type,
            item_id=item_id,
            actor_user_id=actor_user_id,
        )
        return {"events": events, "count": len(events)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
