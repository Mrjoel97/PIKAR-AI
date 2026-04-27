# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.


from typing import Any, Literal, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.workflow_trigger_service import (
    WorkflowTriggerFrequency,
    WorkflowTriggerType,
    get_workflow_trigger_service,
)

router = APIRouter(prefix="/workflow-triggers", tags=["Workflow Triggers"])

_RequestModel = TypeVar("_RequestModel", bound=BaseModel)


class CreateWorkflowTriggerRequest(BaseModel):
    template_id: str
    trigger_name: str
    trigger_type: Literal["schedule", "event"]
    schedule_frequency: (
        Literal["hourly", "daily", "weekly", "monthly", "quarterly", "yearly"] | None
    ) = None
    event_name: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    run_source: str = "agent_ui"
    queue_mode: str = "followup"
    lane: str = "automation"
    persona: str | None = None


class UpdateWorkflowTriggerRequest(BaseModel):
    trigger_name: str | None = None
    trigger_type: Literal["schedule", "event"] | None = None
    schedule_frequency: (
        Literal["hourly", "daily", "weekly", "monthly", "quarterly", "yearly"] | None
    ) = None
    event_name: str | None = None
    context: dict[str, Any] | None = None
    enabled: bool | None = None
    run_source: str | None = None
    queue_mode: str | None = None
    lane: str | None = None
    persona: str | None = None


class DispatchWorkflowEventRequest(BaseModel):
    event_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    source: str = "user_event"


async def _parse_request_body(
    request: Request, model_cls: type[_RequestModel]
) -> _RequestModel:
    try:
        raw_body = await request.json()
    except ValueError as exc:
        raise RequestValidationError(
            [
                {
                    "loc": ("body",),
                    "msg": "Invalid JSON body",
                    "type": "value_error.jsondecode",
                }
            ]
        ) from exc

    try:
        return model_cls.model_validate(raw_body)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


def _coerce_trigger_type(trigger_type: str | None) -> WorkflowTriggerType | None:
    if trigger_type is None:
        return None
    return WorkflowTriggerType(str(trigger_type).strip().lower())


def _coerce_frequency(frequency: str | None) -> WorkflowTriggerFrequency | None:
    if frequency is None or not str(frequency).strip():
        return None
    return WorkflowTriggerFrequency(str(frequency).strip().lower())


@router.get("")
@limiter.limit(get_user_persona_limit)
async def list_workflow_triggers(
    request: Request,
    template_id: str | None = None,
    enabled: bool | None = None,
    department: str | None = None,
    user_id: str = Depends(get_current_user_id),
):
    service = get_workflow_trigger_service()
    if department is None:
        triggers = await service.list_triggers(
            user_id=user_id, template_id=template_id, enabled=enabled
        )
    else:
        triggers = await service.list_triggers(
            user_id=user_id,
            template_id=template_id,
            enabled=enabled,
            department=department,
        )
    return {"status": "success", "count": len(triggers), "triggers": triggers}


@router.post("")
@limiter.limit(get_user_persona_limit)
async def create_workflow_trigger(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    body = await _parse_request_body(request, CreateWorkflowTriggerRequest)
    service = get_workflow_trigger_service()
    try:
        result = await service.create_trigger(
            user_id=user_id,
            template_id=body.template_id,
            trigger_name=body.trigger_name,
            trigger_type=_coerce_trigger_type(body.trigger_type),
            schedule_frequency=_coerce_frequency(body.schedule_frequency),
            event_name=body.event_name,
            context=body.context,
            enabled=body.enabled,
            run_source=body.run_source,
            queue_mode=body.queue_mode,
            lane=body.lane,
            persona=body.persona,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.patch("/{trigger_id}")
@limiter.limit(get_user_persona_limit)
async def update_workflow_trigger(
    request: Request,
    trigger_id: str,
    user_id: str = Depends(get_current_user_id),
):
    body = await _parse_request_body(request, UpdateWorkflowTriggerRequest)
    updates = body.model_dump(exclude_none=True)
    if "trigger_type" in updates:
        updates["trigger_type"] = _coerce_trigger_type(updates["trigger_type"]).value
    if "schedule_frequency" in updates:
        frequency = _coerce_frequency(updates["schedule_frequency"])
        updates["schedule_frequency"] = frequency.value if frequency else None

    service = get_workflow_trigger_service()
    try:
        result = await service.update_trigger(
            trigger_id=trigger_id, user_id=user_id, updates=updates
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result.get("status") == "error":
        raise HTTPException(
            status_code=404, detail=result.get("message", "Trigger not found")
        )
    return result


@router.delete("/{trigger_id}")
@limiter.limit(get_user_persona_limit)
async def delete_workflow_trigger(
    request: Request,
    trigger_id: str,
    user_id: str = Depends(get_current_user_id),
):
    result = await get_workflow_trigger_service().delete_trigger(
        trigger_id=trigger_id, user_id=user_id
    )
    if result.get("status") == "error":
        raise HTTPException(
            status_code=404, detail=result.get("message", "Trigger not found")
        )
    return result


@router.post("/events/dispatch")
@limiter.limit(get_user_persona_limit)
async def dispatch_workflow_event(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    body = await _parse_request_body(request, DispatchWorkflowEventRequest)
    result = await get_workflow_trigger_service().dispatch_event(
        user_id=user_id,
        event_name=body.event_name,
        payload=body.payload,
        source=body.source,
    )
    return result
