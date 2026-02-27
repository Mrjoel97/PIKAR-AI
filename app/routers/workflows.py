from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Literal
import logging
import asyncio
import json
import inspect

from app.middleware.rate_limiter import limiter, get_user_persona_limit
from app.app_utils.auth import verify_service_auth
# Reuse authentication pattern
from app.routers.onboarding import get_current_user_id
from app.workflows.engine import get_workflow_engine
from app.workflows.user_workflow_service import get_user_workflow_service
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async
from app.agents.tools.registry import TOOL_REGISTRY
from app.services.feature_flags import (
    is_user_allowed_for_workflow_canary,
    is_workflow_canary_enabled,
    is_workflow_kill_switch_enabled,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["Workflows"])

# Pydantic Models
class WorkflowTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    template_key: Optional[str] = None
    version: Optional[int] = None
    lifecycle_status: Optional[str] = None
    is_generated: Optional[bool] = None
    personas_allowed: Optional[List[str]] = None
    last_published_at: Optional[str] = None

class StartWorkflowRequest(BaseModel):
    template_name: Optional[str] = None
    template_id: Optional[str] = None
    template_version: Optional[int] = None
    topic: str = ""
    run_source: str = "user_ui"

class StartWorkflowResponse(BaseModel):
    execution_id: str
    status: Literal["pending", "running", "waiting_approval"]
    current_step: str
    message: str

class WorkflowHistoryItem(BaseModel):
    id: Optional[str] = None
    execution_id: Optional[str] = None
    phase_name: Optional[str] = None
    step_name: Optional[str] = None
    status: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    phase_index: Optional[int] = None
    step_index: Optional[int] = None
    attempt_count: Optional[int] = None
    phase_key: Optional[str] = None

class WorkflowExecutionResponse(BaseModel):
    execution: Dict[str, Any]
    template_name: str
    history: List[WorkflowHistoryItem]
    current_phase_index: int
    current_step_index: int

class ApproveStepRequest(BaseModel):
    feedback: str = ""

class GenerateWorkflowRequest(BaseModel):
    description: str
    category: str = "custom"


class CreateTemplateRequest(BaseModel):
    name: str
    description: str = ""
    category: str
    phases: List[Dict[str, Any]]
    template_key: Optional[str] = None
    personas_allowed: Optional[List[str]] = None
    is_generated: bool = False


class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    phases: Optional[List[Dict[str, Any]]] = None
    personas_allowed: Optional[List[str]] = None


class CloneTemplateRequest(BaseModel):
    new_name: Optional[str] = None


class CancelExecutionRequest(BaseModel):
    reason: str = "Cancelled by user"


class RetryStepRequest(BaseModel):
    step_id: str

# Endpoints

@router.get("/tool-registry")
@limiter.limit(get_user_persona_limit)
async def list_tool_registry(request: Request):
    tools = sorted(TOOL_REGISTRY.keys())
    return {"tools": tools, "count": len(tools)}

@router.get("/templates", response_model=List[WorkflowTemplateResponse])
@limiter.limit(get_user_persona_limit)
async def list_templates(
    request: Request,
    category: Optional[str] = None,
    lifecycle_status: Optional[str] = None,
    persona: Optional[str] = None,
):
    try:
        engine = get_workflow_engine()
        templates = await engine.list_templates(category=category, lifecycle_status=lifecycle_status, persona=persona)
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
            ) for t in templates
        ]
    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/readiness")
@limiter.limit(get_user_persona_limit)
async def list_workflow_readiness(
    request: Request,
    status: Optional[str] = None,
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
        readiness_rows = (await execute_async(readiness_query, op_name="workflows.readiness.list")).data or []

        result: Dict[str, Any] = {
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
                await execute_async(journeys_query, op_name="workflows.readiness.journeys")
            ).data or []
            result["journey_count"] = len(journeys)
            result["journeys"] = journeys

        return result
    except Exception as e:
        logger.error(f"Error listing workflow readiness: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start", response_model=StartWorkflowResponse)
@limiter.limit(get_user_persona_limit)
async def start_workflow(
    request: Request, 
    workflow_request: StartWorkflowRequest,
    user_id: str = Depends(get_current_user_id)
):
    try:
        if is_workflow_kill_switch_enabled():
            raise HTTPException(status_code=503, detail="Workflow execution is temporarily disabled by kill switch")
        if is_workflow_canary_enabled() and not is_user_allowed_for_workflow_canary(user_id):
            raise HTTPException(status_code=403, detail="Workflow execution is limited to canary users")
        engine = get_workflow_engine()
        # Ensure context is passed correctly
        context = {"topic": workflow_request.topic} if workflow_request.topic else {}
        
        result = await engine.start_workflow(
            user_id=user_id,
            template_name=workflow_request.template_name,
            template_id=workflow_request.template_id,
            template_version=workflow_request.template_version,
            context=context
            if workflow_request.topic
            else {},
            run_source=workflow_request.run_source,
        )
        
        if "error" in result:
            error_code = result.get("error_code")
            status_code = 404
            if error_code == "validation_error":
                status_code = 400
            elif error_code in {"template_archived", "template_not_published", "workflow_not_ready"}:
                status_code = 409
            elif error_code == "workflow_readiness_unavailable":
                status_code = 503
            elif error_code == "workflow_execution_infra_not_configured":
                status_code = 503
            detail: Dict[str, Any] = {
                "message": result["error"],
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
            raise HTTPException(status_code=status_code, detail=detail)

        return StartWorkflowResponse(
            execution_id=result["execution_id"],
            status=result["status"],  # type: ignore[arg-type]
            current_step=result.get("current_step", ""),
            message=result["message"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting workflow: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates/{template_id}")
@limiter.limit(get_user_persona_limit)
async def get_template(request: Request, template_id: str):
    try:
        engine = get_workflow_engine()
        template = await engine.get_template(template_id)
        if "error" in template:
            raise HTTPException(status_code=404, detail=template["error"])
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {str(e)}")
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
        )
        return result
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
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
        logger.error(f"Error updating template: {str(e)}")
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
        result = await engine.clone_template(template_id=template_id, user_id=user_id, new_name=body.new_name)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cloning template: {str(e)}")
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
        logger.error(f"Error publishing template: {str(e)}")
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
        logger.error(f"Error archiving template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates/{template_id}/versions")
@limiter.limit(get_user_persona_limit)
async def list_template_versions(
    request: Request,
    template_id: str,
):
    try:
        engine = get_workflow_engine()
        return await engine.list_template_versions(template_id=template_id)
    except Exception as e:
        logger.error(f"Error listing template versions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}/diff")
@limiter.limit(get_user_persona_limit)
async def diff_template(
    request: Request,
    template_id: str,
    against: str = "published",
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
        logger.error(f"Error diffing template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/executions", response_model=List[Dict[str, Any]])
@limiter.limit(get_user_persona_limit)
async def list_executions(
    request: Request,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id)
):
    try:
        engine = get_workflow_engine()
        executions = await engine.list_executions(
            user_id=user_id, 
            status=status, 
            limit=limit, 
            offset=offset
        )
        return executions
    except Exception as e:
        logger.error(f"Error listing executions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
@limiter.limit(get_user_persona_limit)
async def get_execution(
    request: Request,
    execution_id: str,
    user_id: str = Depends(get_current_user_id)
):
    try:
        engine = get_workflow_engine()
        result = await engine.get_execution_status(execution_id)
        
        # Security check: verify ownership
        if result["execution"]["user_id"] != user_id:
             raise HTTPException(status_code=403, detail="Unauthorized access to workflow execution")
             
        return WorkflowExecutionResponse(
            execution=result["execution"],
            template_name=result.get("template_name", "Unknown"),
            history=result.get("history", []),
            current_phase_index=result.get("current_phase_index", 0),
            current_step_index=result.get("current_step_index", 0)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution: {str(e)}")
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
        result = await engine.cancel_execution(execution_id=execution_id, user_id=user_id, reason=body.reason)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/executions/{execution_id}/advance")
@limiter.limit(get_user_persona_limit)
async def advance_execution(
    request: Request,
    execution_id: str,
    user_id: str = Depends(get_current_user_id),
):
    try:
        engine = get_workflow_engine()
        result = await engine.advance_execution(execution_id=execution_id, user_id=user_id)
        if "error" in result:
            if result["error"] == "Unauthorized":
                raise HTTPException(status_code=403, detail="Unauthorized")
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error advancing execution: {str(e)}")
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
        result = await engine.retry_step(execution_id=execution_id, step_id=body.step_id, user_id=user_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying step: {str(e)}")
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

    async def event_stream():
        while True:
            status = await engine.get_execution_status(execution_id)
            if "error" in status:
                yield f"event: error\ndata: {json.dumps(status)}\n\n"
                break
            if status["execution"].get("user_id") != user_id:
                yield "event: error\ndata: {\"error\":\"Unauthorized\"}\n\n"
                break
            yield f"event: status\ndata: {json.dumps(status)}\n\n"
            if status["execution"].get("status") in ("completed", "failed", "cancelled"):
                break
            await asyncio.sleep(2)

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.post("/executions/{execution_id}/approve")
@limiter.limit(get_user_persona_limit)
async def approve_step(
    request: Request,
    execution_id: str,
    approval_req: ApproveStepRequest,
    user_id: str = Depends(get_current_user_id)
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
        logger.error(f"Error approving step: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

class ExecuteStepRequest(BaseModel):
    execution_id: str
    step_id: str
    tool_name: str
    context: Dict[str, Any] = {}
    step_name: str = ""
    step_description: str = ""


@router.post("/execute-step")
async def execute_workflow_step(
    step_request: ExecuteStepRequest,
    service_auth: bool = Depends(verify_service_auth),
):
    """Execute a single workflow step using the Python tool registry.
    
    Called by the Supabase edge function. Maps workflow context (initiative_id,
    desired_outcomes, timeline, topic, user_id) to the correct tool parameters
    so steps run with reliable, impactful outcomes.
    """
    from app.agents.tools.registry import get_tool
    from app.workflows.step_executor import build_tool_kwargs
    from app.services.request_context import set_current_user_id

    # Set request context so tools that use get_current_user_id() work (e.g. create_initiative, create_task)
    user_id = step_request.context.get("user_id")
    if user_id:
        set_current_user_id(user_id)
    if service_auth:
        logger.info(f"Service-authenticated workflow step execution: {step_request.tool_name}")

    try:
        tool_fn = get_tool(step_request.tool_name)
        kwargs = build_tool_kwargs(
            tool_fn,
            step_request.tool_name,
            step_request.context,
            step_name=step_request.step_name,
            step_description=step_request.step_description,
        )
        if not kwargs and step_request.context:
            # Fallback: pass through context keys that might match tool params (e.g. **kwargs tools)
            kwargs = {k: v for k, v in step_request.context.items() if v is not None}
        tool_result = tool_fn(**kwargs)
        result = await tool_result if inspect.isawaitable(tool_result) else tool_result
        return {
            "success": True,
            "data": result,
            "tool": step_request.tool_name,
        }
    except TypeError as e:
        logger.warning(f"Workflow step tool signature mismatch: {step_request.tool_name} - {e}")
        return {
            "success": False,
            "error": str(e),
            "tool": step_request.tool_name,
            "data": {"executed": False, "message": f"Tool parameter mismatch: {str(e)}"},
        }
    except Exception as e:
        logger.error(f"Error executing workflow step: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "tool": step_request.tool_name,
            "data": {"executed": False, "message": str(e)},
        }


@router.post("/generate")
@limiter.limit(get_user_persona_limit)
async def generate_workflow(
    request: Request,
    gen_request: GenerateWorkflowRequest,
    user_id: str = Depends(get_current_user_id)
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
            context=f"Category: {gen_request.category}. User wants a custom workflow for their specific business needs."
        )
        
        if result.get("success"):
            return {
                "success": True,
                "template_id": result.get("template_id"),
                "name": result.get("name"),
                "phases_count": result.get("phases_count"),
                "message": result.get("message"),
                "category": gen_request.category
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Workflow generation failed: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"Error generating workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user-workflows")
@limiter.limit(get_user_persona_limit)
async def list_user_workflows(
    request: Request,
    pattern_type: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    try:
        service = get_user_workflow_service()
        workflows = await service.list_workflows(user_id=user_id)
        if pattern_type:
            workflows = [w for w in workflows if w.get("workflow_pattern") == pattern_type]
        return workflows
    except Exception as e:
        logger.error(f"Error listing user workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/user-workflows")
@limiter.limit(get_user_persona_limit)
async def save_user_workflow(
    request: Request,
    workflow_data: Dict[str, Any],
    user_id: str = Depends(get_current_user_id)
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
            workflow_config=workflow_data.get("workflow_config", {})
        )
        return saved_workflow
    except Exception as e:
        logger.error(f"Error saving user workflow: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
