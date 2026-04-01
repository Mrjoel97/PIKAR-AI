# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

import asyncio
import inspect
import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.tools.registry import TOOL_REGISTRY
from app.app_utils.auth import verify_service_auth
from app.autonomy.agent_kernel import get_agent_kernel as build_agent_kernel
from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.personas.runtime import resolve_request_persona

# Reuse authentication pattern
from app.routers.onboarding import get_current_user_id
from app.services.feature_flags import (
    is_user_allowed_for_workflow_canary,
    is_workflow_canary_enabled,
    is_workflow_kill_switch_enabled,
)
from app.services.sse_connection_limits import (
    SSERejectReason,
    release_sse_connection,
    try_acquire_sse_connection,
)
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async
from app.workflows.contract_defaults import list_contract_safe_tool_names
from app.workflows.engine import get_workflow_engine
from app.workflows.user_workflow_service import get_user_workflow_service

logger = logging.getLogger(__name__)


def _get_agent_kernel():
    """Return the shared workflow mission kernel for router-level starts."""
    return build_agent_kernel(workflow_engine=get_workflow_engine())


router = APIRouter(prefix="/workflows", tags=["Workflows"])


def _parse_execution_status_filters(
    status: str | None, statuses: str | None
) -> list[str] | None:
    raw_values: list[str] = []
    if statuses:
        raw_values.extend(part.strip() for part in statuses.split(","))
    elif status:
        raw_values.append(str(status).strip())

    normalized = [value for value in raw_values if value]
    if not normalized:
        return None
    return list(dict.fromkeys(normalized))


SSE_RESPONSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


# Pydantic Models
class WorkflowTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    template_key: str | None = None
    version: int | None = None
    lifecycle_status: str | None = None
    is_generated: bool | None = None
    personas_allowed: list[str] | None = None
    last_published_at: str | None = None


class StartWorkflowRequest(BaseModel):
    template_name: str | None = None
    template_id: str | None = None
    template_version: int | None = None
    topic: str = ""


class StartWorkflowResponse(BaseModel):
    execution_id: str
    status: Literal["pending", "running", "waiting_approval"]
    current_step: str
    message: str


class WorkflowHistoryItem(BaseModel):
    id: str | None = None
    execution_id: str | None = None
    phase_name: str | None = None
    step_name: str | None = None
    status: str | None = None
    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    phase_index: int | None = None
    step_index: int | None = None
    attempt_count: int | None = None
    phase_key: str | None = None
    tool_name: str | None = None
    trust_class: str | None = None
    verification_status: str | None = None
    evidence_refs: list[Any] | None = None
    last_failure_reason: str | None = None


class WorkflowExecutionResponse(BaseModel):
    execution: dict[str, Any]
    template_name: str
    history: list[WorkflowHistoryItem]
    current_phase_index: int
    current_step_index: int
    trust_summary: dict[str, Any] | None = None
    verification_status: str | None = None
    approval_state: str | None = None
    evidence_refs: list[Any] | None = None


class ApproveStepRequest(BaseModel):
    feedback: str = ""


class GenerateWorkflowRequest(BaseModel):
    description: str
    category: str = "custom"


class CreateTemplateRequest(BaseModel):
    name: str
    description: str = ""
    category: str
    phases: list[dict[str, Any]]
    template_key: str | None = None
    personas_allowed: list[str] | None = None
    is_generated: bool = False


class UpdateTemplateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    phases: list[dict[str, Any]] | None = None
    personas_allowed: list[str] | None = None


class CloneTemplateRequest(BaseModel):
    new_name: str | None = None


class CancelExecutionRequest(BaseModel):
    reason: str = "Cancelled by user"


class RetryStepRequest(BaseModel):
    step_id: str


# Endpoints


@router.get("/tool-registry")
@limiter.limit(get_user_persona_limit)
async def list_tool_registry(request: Request):
    tools = list_contract_safe_tool_names(tool_registry=TOOL_REGISTRY)
    return {"tools": tools, "count": len(tools), "mode": "publishable"}


@router.get("/templates", response_model=list[WorkflowTemplateResponse])
@limiter.limit(get_user_persona_limit)
async def list_templates(
    request: Request,
    category: str | None = None,
    lifecycle_status: str | None = None,
    persona: str | None = None,
):
    try:
        engine = get_workflow_engine()
        effective_persona = resolve_request_persona(request, explicit_persona=persona)
        templates = await engine.list_templates(
            category=category,
            lifecycle_status=lifecycle_status,
            persona=effective_persona,
        )
        return [
            WorkflowTemplateResponse(
                id=t["id"],
                name=t["name"],
                description=t["description"],
                category=t["category"],
                template_key=t.get("template_key"),
                version=t.get("version"),
                lifecycle_status=t.get("lifecycle_status"),
                is_generated=t.get("is_generated"),
                personas_allowed=t.get("personas_allowed"),
                last_published_at=t.get("published_at"),
            )
            for t in templates
        ]
    except Exception as e:
        logger.error(f"Error listing templates: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/readiness")
@limiter.limit(get_user_persona_limit)
async def list_workflow_readiness(
    request: Request,
    status: str | None = None,
    include_journeys: bool = False,
):
    """Return workflow readiness registry rows and optional journey readiness view."""
    try:
        client = get_service_client()
        readiness_query = (
            client.table("workflow_readiness")
            .select(
                "template_id, template_name, template_version, status, "
                "required_integrations, requires_human_gate, readiness_owner, "
                "reason_codes, notes, updated_at"
            )
            .order("template_name")
        )
        if status:
            readiness_query = readiness_query.eq("status", status)
        readiness_rows = (
            await execute_async(readiness_query, op_name="workflows.readiness.list")
        ).data or []

        result: dict[str, Any] = {
            "status": "success",
            "count": len(readiness_rows),
            "workflows": readiness_rows,
        }

        if include_journeys:
            journeys_query = (
                client.table("journey_readiness")
                .select("*")
                .order("persona")
                .order("title")
            )
            journeys = (
                await execute_async(
                    journeys_query, op_name="workflows.readiness.journeys"
                )
            ).data or []
            result["journey_count"] = len(journeys)
            result["journeys"] = journeys

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing workflow readiness: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", response_model=StartWorkflowResponse)
@limiter.limit(get_user_persona_limit)
async def start_workflow(
    request: Request,
    workflow_request: StartWorkflowRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        if is_workflow_kill_switch_enabled():
            raise HTTPException(
                status_code=503,
                detail="Workflow execution is temporarily disabled by kill switch",
            )
        if is_workflow_canary_enabled() and not is_user_allowed_for_workflow_canary(
            user_id
        ):
            raise HTTPException(
                status_code=403, detail="Workflow execution is limited to canary users"
            )

        kernel = _get_agent_kernel()
        context = {"topic": workflow_request.topic} if workflow_request.topic else {}
        effective_persona = resolve_request_persona(request)

        result = await kernel.start_workflow_mission(
            user_id=user_id,
            template_name=workflow_request.template_name,
            template_id=workflow_request.template_id,
            template_version=workflow_request.template_version,
            context=context if workflow_request.topic else {},
            run_source="user_ui",
            persona=effective_persona,
        )

        if "error" in result:
            error_code = result.get("error_code")
            status_code = 404
            if error_code == "validation_error":
                status_code = 400
            elif error_code in {
                "template_archived",
                "template_not_published",
                "workflow_not_ready",
                "workflow_contract_invalid",
            }:
                status_code = 409
            elif error_code == "workflow_persona_not_allowed":
                status_code = 403
            elif error_code in {
                "workflow_readiness_unavailable",
                "workflow_execution_infra_not_configured",
            }:
                status_code = 503

            detail: dict[str, Any] = {"message": result["error"]}
            if error_code:
                detail["error_code"] = error_code
            if result.get("lifecycle_status"):
                detail["lifecycle_status"] = result.get("lifecycle_status")
            if result.get("readiness") is not None:
                detail["readiness"] = result.get("readiness")
            if result.get("reason_codes") is not None:
                detail["reason_codes"] = result.get("reason_codes")
            if result.get("details") is not None:
                detail["details"] = result.get("details")
            if result.get("reason_code") is not None:
                detail["reason_code"] = result.get("reason_code")
            if result.get("persona") is not None:
                detail["persona"] = result.get("persona")
            if result.get("personas_allowed") is not None:
                detail["personas_allowed"] = result.get("personas_allowed")
            if result.get("missing_config") is not None:
                detail["missing_config"] = result.get("missing_config")
            if result.get("invalid_config") is not None:
                detail["invalid_config"] = result.get("invalid_config")
            raise HTTPException(status_code=status_code, detail=detail)

        return StartWorkflowResponse(
            execution_id=result["execution_id"],
            status=result["status"],  # type: ignore[arg-type]
            current_step=result.get("current_step", ""),
            message=result["message"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting workflow: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates/{template_id}")
@limiter.limit(get_user_persona_limit)
async def get_template(request: Request, template_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        engine = get_workflow_engine()
        template = await engine.get_template(template_id)
        if "error" in template:
            raise HTTPException(status_code=404, detail=template["error"])
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates")
@limiter.limit(get_user_persona_limit)
async def create_template(
    request: Request,
    body: CreateTemplateRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = get_workflow_engine()
        result = await engine.create_template(
            user_id=user_id,
            name=body.name,
            description=body.description,
            category=body.category,
            phases=body.phases,
            template_key=body.template_key,
            personas_allowed=body.personas_allowed,
            is_generated=body.is_generated,
            default_persona=resolve_request_persona(request),
        )
        if "error" in result:
            raise HTTPException(
                status_code=400,
                detail={"message": result["error"], "details": result.get("details")},
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/templates/{template_id}")
@limiter.limit(get_user_persona_limit)
async def update_template(
    request: Request,
    template_id: str,
    body: UpdateTemplateRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = get_workflow_engine()
        result = await engine.update_template_draft(
            template_id=template_id,
            user_id=user_id,
            updates=body.model_dump(exclude_none=True),
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/templates/{template_id}/clone")
@limiter.limit(get_user_persona_limit)
async def clone_template(
    request: Request,
    template_id: str,
    body: CloneTemplateRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = get_workflow_engine()
        result = await engine.clone_template(
            template_id=template_id, user_id=user_id, new_name=body.new_name
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cloning template: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/templates/{template_id}/publish")
@limiter.limit(get_user_persona_limit)
async def publish_template(
    request: Request,
    template_id: str,
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = get_workflow_engine()
        result = await engine.publish_template(template_id=template_id, user_id=user_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing template: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/templates/{template_id}/archive")
@limiter.limit(get_user_persona_limit)
async def archive_template(
    request: Request,
    template_id: str,
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = get_workflow_engine()
        result = await engine.archive_template(template_id=template_id, user_id=user_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving template: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates/{template_id}/versions")
@limiter.limit(get_user_persona_limit)
async def list_template_versions(
    request: Request,
    template_id: str,
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = get_workflow_engine()
        return await engine.list_template_versions(template_id=template_id)
    except Exception as e:
        logger.error(f"Error listing template versions: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}/diff")
@limiter.limit(get_user_persona_limit)
async def diff_template(
    request: Request,
    template_id: str,
    against: str = "published",
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = get_workflow_engine()
        result = await engine.diff_template(template_id=template_id, against=against)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error diffing template: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/stats")
@limiter.limit(get_user_persona_limit)
async def get_execution_stats(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Aggregated workflow execution stats for the observability widget."""
    try:
        client = get_service_client()

        # Fetch all executions for this user (last 90 days would be ideal, but
        # Supabase PostgREST doesn't support date arithmetic easily, so we fetch
        # recent executions with a reasonable limit).
        res = (
            client.table("workflow_executions")
            .select("id, status, created_at, completed_at, name")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        executions = res.data or []

        # Count by status
        status_counts: dict[str, int] = {}
        for exc in executions:
            s = exc.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1

        total = len(executions)
        completed = status_counts.get("completed", 0)
        failed = status_counts.get("failed", 0)
        running = status_counts.get("running", 0) + status_counts.get("pending", 0)
        cancelled = status_counts.get("cancelled", 0)

        failure_rate = round((failed / total) * 100, 1) if total > 0 else 0.0
        success_rate = round((completed / total) * 100, 1) if total > 0 else 0.0

        # Fetch step-level stats for failed steps (last 50 failures for drill-down)
        failed_exec_ids = [e["id"] for e in executions if e.get("status") == "failed"][
            :20
        ]
        top_failing_tools: dict[str, int] = {}
        if failed_exec_ids:
            steps_res = (
                client.table("workflow_steps")
                .select("tool_name, error_message")
                .in_("execution_id", failed_exec_ids)
                .eq("status", "failed")
                .limit(100)
                .execute()
            )
            for step in steps_res.data or []:
                tool = step.get("tool_name") or "unknown"
                top_failing_tools[tool] = top_failing_tools.get(tool, 0) + 1

        # Sort failing tools by count desc
        top_failing_sorted = sorted(
            top_failing_tools.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # Recent failures for display
        recent_failures = [
            {
                "id": e["id"],
                "name": e.get("name", ""),
                "created_at": e.get("created_at"),
            }
            for e in executions
            if e.get("status") == "failed"
        ][:5]

        # Duration metrics — fetch completed steps with output_data
        completed_exec_ids = [
            e["id"] for e in executions if e.get("status") == "completed"
        ][:30]
        duration_stats: dict[str, Any] = {"avg_ms": 0, "p95_ms": 0, "slowest_tools": []}
        if completed_exec_ids:
            dur_steps_res = (
                client.table("workflow_steps")
                .select("tool_name, output_data")
                .in_("execution_id", completed_exec_ids)
                .eq("status", "completed")
                .limit(500)
                .execute()
            )
            durations: list[int] = []
            tool_durations: dict[str, list[int]] = {}
            for s in dur_steps_res.data or []:
                meta = (s.get("output_data") or {}).get("_execution_meta") or {}
                d = meta.get("duration_ms")
                if d is not None and isinstance(d, (int, float)):
                    d_int = int(d)
                    durations.append(d_int)
                    tool = s.get("tool_name") or "unknown"
                    tool_durations.setdefault(tool, []).append(d_int)

            if durations:
                durations.sort()
                duration_stats["avg_ms"] = int(sum(durations) / len(durations))
                p95_idx = int(len(durations) * 0.95)
                duration_stats["p95_ms"] = durations[min(p95_idx, len(durations) - 1)]
                # Slowest tools by average duration
                tool_avgs = [
                    {"tool": t, "avg_ms": int(sum(ds) / len(ds)), "count": len(ds)}
                    for t, ds in tool_durations.items()
                ]
                tool_avgs.sort(key=lambda x: x["avg_ms"], reverse=True)
                duration_stats["slowest_tools"] = tool_avgs[:5]

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "cancelled": cancelled,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "top_failing_tools": [
                {"tool": t, "count": c} for t, c in top_failing_sorted
            ],
            "recent_failures": recent_failures,
            "status_breakdown": status_counts,
            "duration": duration_stats,
        }
    except Exception as e:
        logger.error(f"Error getting execution stats: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions", response_model=list[dict[str, Any]])
@limiter.limit(get_user_persona_limit)
async def list_executions(
    request: Request,
    status: str | None = None,
    statuses: str | None = None,
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = get_workflow_engine()
        executions = await engine.list_executions(
            user_id=user_id,
            status=status,
            statuses=_parse_execution_status_filters(status, statuses),
            limit=limit,
            offset=offset,
        )
        return executions
    except Exception as e:
        logger.error(f"Error listing executions: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
@limiter.limit(get_user_persona_limit)
async def get_execution(
    request: Request, execution_id: str, user_id: str = Depends(get_current_user_id)
):
    try:
        # Issue #13: Check ownership BEFORE fetching full execution data
        client = get_service_client()
        ownership_res = (
            client.table("workflow_executions")
            .select("user_id")
            .eq("id", execution_id)
            .execute()
        )
        if not ownership_res.data:
            raise HTTPException(status_code=404, detail="Execution not found")
        if ownership_res.data[0]["user_id"] != user_id:
            raise HTTPException(
                status_code=403, detail="Unauthorized access to workflow execution"
            )

        engine = get_workflow_engine()
        result = await engine.get_execution_status(execution_id)

        return WorkflowExecutionResponse(
            execution=result["execution"],
            template_name=result.get("template_name", "Unknown"),
            history=result.get("history", []),
            current_phase_index=result.get("current_phase_index", 0),
            current_step_index=result.get("current_step_index", 0),
            trust_summary=result.get("trust_summary"),
            verification_status=result.get("verification_status"),
            approval_state=result.get("approval_state"),
            evidence_refs=result.get("evidence_refs"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution: {e!s}")
        raise HTTPException(status_code=404, detail="Execution not found")


@router.post("/executions/{execution_id}/cancel")
@limiter.limit(get_user_persona_limit)
async def cancel_execution(
    request: Request,
    execution_id: str,
    body: CancelExecutionRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = get_workflow_engine()
        result = await engine.cancel_execution(
            execution_id=execution_id, user_id=user_id, reason=body.reason
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/executions/{execution_id}/resume")
@limiter.limit(get_user_persona_limit)
async def resume_execution(
    request: Request,
    execution_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Resume a failed/paused workflow from the last successful step."""
    try:
        engine = get_workflow_engine()
        result = await engine.resume_execution(
            execution_id=execution_id, user_id=user_id
        )
        if "error" in result:
            if result["error"] == "Unauthorized":
                raise HTTPException(status_code=403, detail="Unauthorized")
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming execution: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/executions/{execution_id}/timeline")
@limiter.limit(get_user_persona_limit)
async def get_execution_timeline(
    request: Request,
    execution_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Step-level timeline data for the execution timeline widget."""
    try:
        client = get_service_client()

        # Verify ownership
        exec_res = (
            client.table("workflow_executions")
            .select("id, user_id, status, name, created_at, completed_at, context")
            .eq("id", execution_id)
            .execute()
        )
        if not exec_res.data:
            raise HTTPException(status_code=404, detail="Execution not found")
        execution = exec_res.data[0]
        if execution["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Fetch all steps ordered by phase_index, step_index
        steps_res = (
            client.table("workflow_steps")
            .select(
                "id, phase_name, step_name, status, started_at, completed_at, "
                "phase_index, step_index, error_message, output_data"
            )
            .eq("execution_id", execution_id)
            .order("phase_index")
            .order("step_index")
            .execute()
        )

        steps = []
        for s in steps_res.data or []:
            output = s.get("output_data") or {}
            meta = output.get("_execution_meta", {}) if isinstance(output, dict) else {}
            duration_ms = meta.get("duration_ms") if isinstance(meta, dict) else None
            tool_name = (
                meta.get("tool_name") if isinstance(meta, dict) else None
            ) or ""

            steps.append(
                {
                    "id": s["id"],
                    "phase_name": s["phase_name"],
                    "step_name": s["step_name"],
                    "status": s["status"],
                    "started_at": s.get("started_at"),
                    "completed_at": s.get("completed_at"),
                    "phase_index": s.get("phase_index"),
                    "step_index": s.get("step_index"),
                    "duration_ms": duration_ms,
                    "tool_name": tool_name,
                    "error_message": s.get("error_message"),
                }
            )

        # Check for chaining metadata
        context = execution.get("context") or {}
        chain_info = None
        if context.get("_parent_execution_id"):
            chain_info = {
                "parent_execution_id": context["_parent_execution_id"],
                "parent_template_name": context.get("_parent_template_name"),
                "chain_depth": context.get("_chain_depth", 0),
            }

        return {
            "execution_id": execution_id,
            "name": execution.get("name"),
            "status": execution["status"],
            "created_at": execution.get("created_at"),
            "completed_at": execution.get("completed_at"),
            "steps": steps,
            "chain_info": chain_info,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching timeline: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/executions/{execution_id}/advance")
@limiter.limit(get_user_persona_limit)
async def advance_execution(
    request: Request,
    execution_id: str,
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = get_workflow_engine()
        result = await engine.advance_execution(
            execution_id=execution_id, user_id=user_id
        )
        if "error" in result:
            if result["error"] == "Unauthorized":
                raise HTTPException(status_code=403, detail="Unauthorized")
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error advancing execution: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/executions/{execution_id}/retry-step")
@limiter.limit(get_user_persona_limit)
async def retry_step(
    request: Request,
    execution_id: str,
    body: RetryStepRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = get_workflow_engine()
        result = await engine.retry_step(
            execution_id=execution_id, step_id=body.step_id, user_id=user_id
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying step: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/executions/{execution_id}/events")
@limiter.limit(get_user_persona_limit)
async def execution_events(
    request: Request,
    execution_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """SSE stream for workflow execution status snapshots."""
    engine = get_workflow_engine()
    _sse_result = await try_acquire_sse_connection(
        user_id,
        stream_name="workflow",
    )
    acquired_connection, _active_connections, connection_limit = _sse_result
    if not acquired_connection:
        if _sse_result.reason == SSERejectReason.SERVER_BACKPRESSURE:
            raise HTTPException(
                status_code=503,
                detail="Server at capacity. Too many active SSE connections globally.",
            )
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many active SSE connections for this user. "
                f"Limit: {connection_limit}."
            ),
        )

    try:
        # Issue #26: Verify ownership BEFORE entering the SSE stream loop
        client = get_service_client()
        ownership_res = (
            client.table("workflow_executions")
            .select("user_id")
            .eq("id", execution_id)
            .execute()
        )
        if not ownership_res.data:
            await release_sse_connection(user_id, stream_name="workflow")
            raise HTTPException(status_code=404, detail="Execution not found")
        if ownership_res.data[0]["user_id"] != user_id:
            await release_sse_connection(user_id, stream_name="workflow")
            raise HTTPException(
                status_code=403, detail="Unauthorized access to workflow execution"
            )

        async def event_stream():
            try:
                yield ": connected\n\n"
                while True:
                    if await request.is_disconnected():
                        break
                    status = await engine.get_execution_status(execution_id)
                    if "error" in status:
                        yield f"event: error\ndata: {json.dumps(status)}\n\n"
                        break
                    yield f"event: status\ndata: {json.dumps(status)}\n\n"
                    if status["execution"].get("status") in (
                        "completed",
                        "failed",
                        "cancelled",
                    ):
                        break
                    await asyncio.sleep(2)
            finally:
                await release_sse_connection(user_id, stream_name="workflow")

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers=SSE_RESPONSE_HEADERS,
        )
    except Exception:
        await release_sse_connection(user_id, stream_name="workflow")
        raise


@router.post("/executions/{execution_id}/approve")
@limiter.limit(get_user_persona_limit)
async def approve_step(
    request: Request,
    execution_id: str,
    approval_req: ApproveStepRequest,
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = get_workflow_engine()
        result = await engine.approve_step(
            execution_id,
            step_message=approval_req.feedback or "Approved by user",
            user_id=user_id,
        )
        if "error" in result:
            if result["error"] == "Unauthorized":
                raise HTTPException(status_code=403, detail="Unauthorized")
            raise HTTPException(status_code=400, detail=result["error"])
        return {"status": "success", "message": "Step approved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving step: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


class ExecuteStepRequest(BaseModel):
    execution_id: str
    step_id: str
    tool_name: str
    context: dict[str, Any] = {}
    step_name: str = ""
    step_description: str = ""
    step_definition: dict[str, Any] | None = None
    run_source: str = "user_ui"


@router.post("/execute-step")
async def execute_workflow_step(
    step_request: ExecuteStepRequest,
    service_auth: bool = Depends(verify_service_auth),
):
    """Execute a single workflow step using the Python tool registry."""
    from app.agents.tools.registry import get_tool
    from app.services.request_context import (
        set_current_session_id,
        set_current_user_id,
        set_current_workflow_execution_id,
    )
    from app.workflows.execution_contracts import (
        WorkflowContractError,
        build_tool_kwargs,
        determine_trust_class,
        extract_evidence_refs,
        verify_step_output,
    )

    def _normalize_payload(
        output: Any,
        *,
        trust_class: str,
        verification_status: str,
        last_failure_reason: str | None = None,
        reason_code: str | None = None,
    ) -> dict[str, Any]:
        payload = dict(output) if isinstance(output, dict) else {"result": output}
        payload.setdefault("tool", step_request.tool_name)
        payload["_execution_meta"] = {
            "tool_name": step_request.tool_name,
            "trust_class": trust_class,
            "verification_status": verification_status,
            "evidence_refs": extract_evidence_refs(payload),
            "last_failure_reason": last_failure_reason,
            "reason_code": reason_code,
        }
        return payload

    user_id = step_request.context.get("user_id")
    if user_id:
        set_current_user_id(user_id)
    session_id = step_request.context.get("session_id")
    set_current_session_id(session_id if isinstance(session_id, str) else None)
    set_current_workflow_execution_id(step_request.execution_id)
    if service_auth:
        logger.info(
            f"Service-authenticated workflow step execution: {step_request.tool_name}"
        )

    try:
        tool_fn = get_tool(step_request.tool_name)
        kwargs = build_tool_kwargs(
            tool_fn,
            step_request.tool_name,
            step_request.context,
            step_name=step_request.step_name,
            step_description=step_request.step_description,
            step_definition=step_request.step_definition,
            run_source=step_request.run_source,
        )
        tool_result = tool_fn(**kwargs)
        result = await tool_result if inspect.isawaitable(tool_result) else tool_result
        verification = verify_step_output(
            result, step_definition=step_request.step_definition
        )
        if verification["status"] == "failed":
            raise WorkflowContractError(
                "Step verification failed.",
                reason_code="verification_failed",
                details={"errors": verification.get("errors") or []},
            )
        trust_class = determine_trust_class(
            step_request.tool_name,
            step_definition=step_request.step_definition,
        )
        payload = _normalize_payload(
            result,
            trust_class=trust_class,
            verification_status=verification["status"],
        )
        return {
            "success": True,
            "data": payload,
            "tool": step_request.tool_name,
            "trust_class": trust_class,
            "verification_status": verification["status"],
            "evidence_refs": payload["_execution_meta"]["evidence_refs"],
        }
    except WorkflowContractError as e:
        logger.warning(
            f"Workflow step contract failure: {step_request.tool_name} - {e}"
        )
        trust_class = determine_trust_class(
            step_request.tool_name,
            step_definition=step_request.step_definition,
        )
        payload = _normalize_payload(
            {"executed": False, "message": str(e)},
            trust_class=trust_class,
            verification_status="failed",
            last_failure_reason=str(e),
            reason_code=e.reason_code,
        )
        return {
            "success": False,
            "error": str(e),
            "reason_code": e.reason_code,
            "tool": step_request.tool_name,
            "data": payload,
        }
    except Exception as e:
        logger.error(f"Error executing workflow step: {e!s}")
        trust_class = determine_trust_class(
            step_request.tool_name,
            step_definition=step_request.step_definition,
        )
        payload = _normalize_payload(
            {"executed": False, "message": str(e)},
            trust_class=trust_class,
            verification_status="failed",
            last_failure_reason=str(e),
            reason_code="step_execution_failed",
        )
        return {
            "success": False,
            "error": str(e),
            "reason_code": "step_execution_failed",
            "tool": step_request.tool_name,
            "data": payload,
        }
    finally:
        set_current_session_id(None)
        set_current_workflow_execution_id(None)
        if user_id:
            set_current_user_id(None)


@router.post("/generate")
@limiter.limit(get_user_persona_limit)
async def generate_workflow(
    request: Request,
    gen_request: GenerateWorkflowRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Generate a custom workflow using AI based on user description.

    Uses the WorkflowGenerator to create a tailored workflow template
    that can be saved and executed later.
    """
    try:
        from app.workflows.generator import get_workflow_generator

        generator = get_workflow_generator()
        result = await generator.generate_workflow(
            user_id=user_id,
            goal=gen_request.description,
            context=f"Category: {gen_request.category}. User wants a custom workflow for their specific business needs.",
            category=gen_request.category,
            persona=resolve_request_persona(request),
        )

        if result.get("success"):
            return {
                "success": True,
                "template_id": result.get("template_id"),
                "name": result.get("name"),
                "phases_count": result.get("phases_count"),
                "message": result.get("message"),
                "category": gen_request.category,
                "lifecycle_status": result.get("lifecycle_status"),
                "published": result.get("published", False),
                "publish_error": result.get("publish_error"),
                "publish_details": result.get("publish_details"),
            }
        raise HTTPException(
            status_code=500,
            detail=f"Workflow generation failed: {result.get('error', 'Unknown error')}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-workflows")
@limiter.limit(get_user_persona_limit)
async def list_user_workflows(
    request: Request,
    pattern_type: str | None = None,
    user_id: str = Depends(get_current_user_id),
):
    try:
        service = get_user_workflow_service()
        workflows = await service.list_workflows(
            user_id=user_id,
            persona_scope=resolve_request_persona(request),
        )
        if pattern_type:
            workflows = [
                w for w in workflows if w.get("workflow_pattern") == pattern_type
            ]
        return workflows
    except Exception as e:
        logger.error(f"Error listing user workflows: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user-workflows")
@limiter.limit(get_user_persona_limit)
async def save_user_workflow(
    request: Request,
    workflow_data: dict[str, Any],
    user_id: str = Depends(get_current_user_id),
):
    try:
        service = get_user_workflow_service()
        workflow_data["user_id"] = user_id
        saved_workflow = await service.save_workflow(
            user_id=user_id,
            workflow_name=workflow_data.get("workflow_name"),
            workflow_pattern=workflow_data.get("workflow_pattern"),
            agent_ids=workflow_data.get("agent_ids", []),
            request_pattern=workflow_data.get("request_pattern", ""),
            workflow_config=workflow_data.get("workflow_config", {}),
            persona_scope=resolve_request_persona(request),
        )
        return saved_workflow
    except Exception as e:
        logger.error(f"Error saving user workflow: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


@limiter.limit(get_user_persona_limit)
async def save_user_workflow(
    request: Request,
    workflow_data: dict[str, Any],
    user_id: str = Depends(get_current_user_id),
):
    try:
        service = get_user_workflow_service()
        # Ensure user_id is injected into data
        workflow_data["user_id"] = user_id
        # Unpack arguments as required by service.save_workflow
        saved_workflow = await service.save_workflow(
            user_id=user_id,
            workflow_name=workflow_data.get("workflow_name"),
            workflow_pattern=workflow_data.get("workflow_pattern"),
            agent_ids=workflow_data.get("agent_ids", []),
            request_pattern=workflow_data.get("request_pattern", ""),
            workflow_config=workflow_data.get("workflow_config", {}),
        )
        return saved_workflow
    except Exception as e:
        logger.error(f"Error saving user workflow: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


class StartExecutionRequest(BaseModel):
    """Request to start an existing pending execution (used by workflow chaining)."""

    execution_id: str


@router.post("/start-execution")
async def start_pending_execution(
    req: StartExecutionRequest,
    service_auth: bool = Depends(verify_service_auth),
):
    """Start a pending workflow execution. Used by edge function for workflow chaining."""
    from app.services.edge_functions import edge_function_client

    engine = get_workflow_engine()

    # Verify the execution exists and is pending
    result = (
        engine.client.table("workflow_executions")
        .select("id, status, template_id, user_id")
        .eq("id", req.execution_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Execution not found")

    execution = result.data[0]
    if execution["status"] != "pending":
        return {
            "success": True,
            "execution_id": req.execution_id,
            "status": execution["status"],
            "message": "Already started",
        }

    # Trigger via edge function
    ef_result = await edge_function_client.execute_workflow(
        req.execution_id, action="start"
    )
    if "error" in ef_result:
        raise HTTPException(status_code=500, detail=ef_result["error"])

    return {"success": True, "execution_id": req.execution_id, "status": "started"}
