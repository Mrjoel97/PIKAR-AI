# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Initiatives API: templates and create-from-template."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.personas.runtime import resolve_request_persona
from app.routers.onboarding import get_current_user_id
from app.services.governance_service import get_governance_service
from app.services.initiative_operational_state import normalize_operational_state
from app.services.initiative_service import InitiativeService
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async
from app.services.workspace_data_filter import get_workspace_user_ids

router = APIRouter(prefix="/initiatives", tags=["Initiatives"])


class CreateFromTemplateRequest(BaseModel):
    template_id: str
    title_override: str | None = None


class CreateFromJourneyRequest(BaseModel):
    journey_id: str
    title_override: str | None = None
    desired_outcomes: str | None = None
    timeline: str | None = None


class CreateChecklistItemRequest(BaseModel):
    title: str
    phase: str
    description: str | None = None
    status: str = "pending"
    owner_user_id: str | None = None
    owner_label: str | None = None
    due_at: datetime | None = None
    evidence: list = Field(default_factory=list)
    sort_order: int = 0
    metadata: dict | None = None


class UpdateChecklistItemRequest(BaseModel):
    title: str | None = None
    phase: str | None = None
    description: str | None = None
    status: str | None = None
    owner_user_id: str | None = None
    owner_label: str | None = None
    due_at: datetime | None = None
    evidence: list | None = None
    sort_order: int | None = None
    metadata: dict | None = None


class UpdateInitiativeRequest(BaseModel):
    status: str | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    title: str | None = None
    description: str | None = None
    phase: str | None = None
    phase_progress: dict[str, int] | None = None
    metadata: dict | None = None
    workflow_execution_id: str | None = None


async def _hydrate_initiative_context(initiative: dict[str, Any]) -> dict[str, Any]:
    hydrated = dict(initiative or {})
    metadata = hydrated.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
        hydrated["metadata"] = metadata

    hydrated["journey_outcomes_prompt"] = None
    journey_id = metadata.get("journey_id")
    if not isinstance(journey_id, str) or not journey_id:
        return hydrated

    try:
        response = await execute_async(
            get_service_client()
            .table("user_journeys")
            .select("outcomes_prompt")
            .eq("id", journey_id)
            .limit(1),
            op_name="initiatives.user_journeys.prompt",
        )
    except Exception:
        return hydrated

    rows = response.data or []
    if rows:
        hydrated["journey_outcomes_prompt"] = rows[0].get("outcomes_prompt")
    return hydrated


@router.get("/templates")
@limiter.limit(get_user_persona_limit)
async def list_initiative_templates(
    request: Request,
    persona: str | None = None,
    category: str | None = None,
):
    """List initiative templates, optionally filtered by persona and category."""
    try:
        service = InitiativeService()
        effective_persona = resolve_request_persona(request, explicit_persona=persona)
        templates = await service.list_templates(
            persona=effective_persona, category=category
        )
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
        governance = get_governance_service()
        await governance.log_event(
            user_id=user_id,
            action_type="initiative.created",
            resource_type="initiative",
            resource_id=initiative.get("id") if isinstance(initiative, dict) else None,
            details={"title": initiative.get("title") if isinstance(initiative, dict) else None, "source": "template"},
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
        client = get_service_client()
        # Fetch journey (service client can read user_journeys)
        r = await execute_async(
            client.table("user_journeys")
            .select("*")
            .eq("id", body.journey_id)
            .single(),
            op_name="initiatives.user_journeys.get",
        )
        if not r.data:
            raise HTTPException(status_code=404, detail="Journey not found")
        journey = r.data
        service = InitiativeService()
        initiative = await service.create_initiative(
            title=body.title_override or journey["title"],
            description=journey.get("description")
            or f'Initiative based on the "{journey["title"]}" user journey',
            priority="medium",
            user_id=user_id,
            phase="ideation",
            metadata={
                "source": "user_journey",
                "journey_id": journey["id"],
                "journey_title": journey["title"],
                "journey_stages": journey.get("stages") or [],
                "kpis": journey.get("kpis") or [],
                "desired_outcomes": body.desired_outcomes.strip()
                if isinstance(body.desired_outcomes, str)
                and body.desired_outcomes.strip()
                else None,
                "timeline": body.timeline.strip()
                if isinstance(body.timeline, str) and body.timeline.strip()
                else None,
            },
        )
        governance = get_governance_service()
        await governance.log_event(
            user_id=user_id,
            action_type="initiative.created",
            resource_type="initiative",
            resource_id=initiative.get("id") if isinstance(initiative, dict) else None,
            details={"title": initiative.get("title") if isinstance(initiative, dict) else None, "source": "user_journey"},
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
            journey_res = await execute_async(
                client.table("user_journeys")
                .select("title, primary_workflow_template_name")
                .eq("id", journey_id)
                .limit(1),
                op_name="initiatives.user_journeys.workflow_context",
            )
            if journey_res.data:
                journey = journey_res.data[0]
                await service.update_initiative(
                    initiative_id,
                    metadata={
                        "journey_id": journey_id,
                        "journey_title": journey.get("title"),
                        "workflow_template_name": journey.get(
                            "primary_workflow_template_name"
                        ),
                        "desired_outcomes": desired_outcomes,
                        "timeline": timeline,
                    },
                    user_id=user_id,
                )

        from app.agents.strategic.tools import (
            start_journey_workflow as do_start_journey_workflow,
        )
        from app.services.request_context import set_current_user_id

        set_current_user_id(user_id)
        result = await do_start_journey_workflow(initiative_id)
        if not result.get("success"):
            if result.get("missing_inputs"):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": result.get(
                            "error", "Journey workflow requirements are not satisfied"
                        ),
                        "requirements_satisfied": False,
                        "missing_inputs": result.get("missing_inputs", []),
                    },
                )
            error_code = result.get("error_code")
            status_code = 400
            if error_code == "template_not_found":
                status_code = 404
            elif error_code in {
                "template_archived",
                "template_not_published",
                "workflow_not_ready",
                "workflow_contract_invalid",
            }:
                status_code = 409
            elif error_code in {
                "workflow_readiness_unavailable",
                "workflow_execution_infra_not_configured",
            }:
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
            if result.get("blockers") is not None:
                detail["blockers"] = result.get("blockers")
            if result.get("trust_summary") is not None:
                detail["trust_summary"] = result.get("trust_summary")
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
            "blockers": result.get("blockers", []),
            "trust_summary": result.get("trust_summary", {}),
            "verification_status": result.get("verification_status"),
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


@router.get("")
@limiter.limit(get_user_persona_limit)
async def list_initiatives(
    request: Request,
    status: str | None = None,
    phase: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    user_id: str = Depends(get_current_user_id),
):
    """List initiatives with operational state surfaced for the UI.

    For workspace members, returns initiatives from all co-members so invited
    users see shared content on their dashboard.
    """
    try:
        scoped_user_ids = await get_workspace_user_ids(user_id)
        if len(scoped_user_ids) > 1:
            # Workspace-scoped read: use a direct query with .in_() to include
            # initiatives from all workspace members. Write operations (create,
            # update, delete) remain user-specific via InitiativeService.
            client = get_service_client()
            query = (
                client.table("initiatives")
                .select("*")
                .in_("user_id", scoped_user_ids)
            )
            if status:
                query = query.eq("status", status)
            if phase:
                query = query.eq("phase", phase)
            if priority:
                query = query.eq("priority", priority)
            response = await execute_async(
                query.order("created_at", desc=True).limit(limit),
                op_name="initiatives.list.workspace",
            )
            initiatives = [normalize_operational_state(row) for row in (response.data or [])]
        else:
            service = InitiativeService()
            initiatives = await service.list_initiatives(
                status=status,
                phase=phase,
                priority=priority,
                limit=limit,
                user_id=user_id,
            )
        return {"success": True, "initiatives": initiatives, "count": len(initiatives)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{initiative_id}")
@limiter.limit(get_user_persona_limit)
async def get_initiative(
    request: Request,
    initiative_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get a single initiative with operational state surfaced for the UI."""
    try:
        service = InitiativeService()
        initiative = await service.get_initiative(initiative_id, user_id=user_id)
        initiative = await _hydrate_initiative_context(initiative)
        return {"success": True, "initiative": initiative}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{initiative_id}")
@limiter.limit(get_user_persona_limit)
async def update_initiative(
    request: Request,
    initiative_id: str,
    body: UpdateInitiativeRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Update a single initiative via the authenticated API contract."""
    try:
        supabase = get_service_client()
        payload = body.model_dump(exclude_none=True)
        updates = {k: v for k, v in payload.items() if k != "metadata"}
        if updates:
            result = (
                supabase.table("initiatives")
                .update(updates)
                .eq("id", initiative_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not result.data:
                raise HTTPException(
                    status_code=404, detail="Initiative not found or access denied"
                )
        service = InitiativeService()
        if payload:
            initiative = await service.update_initiative(
                initiative_id,
                user_id=user_id,
                **payload,
            )
        else:
            initiative = await service.get_initiative(initiative_id, user_id=user_id)
        initiative = await _hydrate_initiative_context(initiative)
        return {"success": True, "initiative": initiative}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{initiative_id}")
@limiter.limit(get_user_persona_limit)
async def delete_initiative(
    request: Request,
    initiative_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Delete a single initiative via the authenticated API contract."""
    try:
        service = InitiativeService()
        deleted = await service.delete_initiative(initiative_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Initiative not found")
        governance = get_governance_service()
        await governance.log_event(
            user_id=user_id,
            action_type="initiative.deleted",
            resource_type="initiative",
            resource_id=initiative_id,
            details={},
        )
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{initiative_id}/checklist")
@limiter.limit(get_user_persona_limit)
async def list_checklist_items(
    request: Request,
    initiative_id: str,
    phase: str | None = None,
    status: str | None = None,
    owner_label: str | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
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
        supabase = get_service_client()
        # Verify the checklist item belongs to this user's initiative
        item_res = (
            supabase.table("checklist_items")
            .select("id, initiative_id")
            .eq("id", item_id)
            .single()
            .execute()
        )
        if not item_res.data:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        # Check initiative ownership
        initiative_res = (
            supabase.table("initiatives")
            .select("id")
            .eq("id", item_res.data["initiative_id"])
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        if not initiative_res.data:
            raise HTTPException(status_code=403, detail="Access denied")
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
    event_type: str | None = None,
    item_id: str | None = None,
    actor_user_id: str | None = None,
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
