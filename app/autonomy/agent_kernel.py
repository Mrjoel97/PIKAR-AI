"""Shared agent-kernel primitives for mission-oriented workflow execution."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Optional, Protocol

from app.workflows.engine import get_workflow_engine

logger = logging.getLogger(__name__)


@dataclass
class WorkflowMissionRequest:
    """Normalized workflow mission request handled by the agent kernel."""

    user_id: str
    template_name: Optional[str] = None
    template_id: Optional[str] = None
    template_version: Optional[int] = None
    context: dict[str, Any] = field(default_factory=dict)
    run_source: str = "user_ui"
    persona: Optional[str] = None
    session_id: Optional[str] = None
    parent_run_id: Optional[str] = None
    queue_mode: str = "followup"
    lane: str = "session"


class WorkflowMissionHook(Protocol):
    """Lifecycle hooks for kernel-managed workflow starts."""

    async def before_start(self, request: WorkflowMissionRequest) -> WorkflowMissionRequest:
        ...

    async def after_start(
        self,
        request: WorkflowMissionRequest,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        ...


class WorkflowMissionHookAdapter:
    """Convenience base class for no-op mission hooks."""

    async def before_start(self, request: WorkflowMissionRequest) -> WorkflowMissionRequest:
        return request

    async def after_start(
        self,
        request: WorkflowMissionRequest,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        return result


class WorkflowMissionMetadataHook(WorkflowMissionHookAdapter):
    """Persist lightweight kernel metadata into workflow context and responses."""

    async def before_start(self, request: WorkflowMissionRequest) -> WorkflowMissionRequest:
        kernel_metadata = dict(request.context.get("_agent_kernel") or {})
        kernel_metadata.update(
            {
                "lane": request.lane,
                "queue_mode": request.queue_mode,
            }
        )
        if request.session_id:
            kernel_metadata["session_id"] = request.session_id
        if request.parent_run_id:
            kernel_metadata["parent_run_id"] = request.parent_run_id
        if request.persona:
            kernel_metadata["persona"] = request.persona
        if request.template_name:
            kernel_metadata["template_name"] = request.template_name
        if request.template_id:
            kernel_metadata["template_id"] = request.template_id
        request.context = {**request.context, "_agent_kernel": kernel_metadata}
        return request

    async def after_start(
        self,
        request: WorkflowMissionRequest,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        mission_id = result.get("execution_id") or result.get("workflow_execution_id")
        result.setdefault(
            "mission",
            {
                "kind": "workflow",
                "mission_id": mission_id,
                "session_id": request.session_id,
                "parent_run_id": request.parent_run_id,
                "queue_mode": request.queue_mode,
                "lane": request.lane,
                "template_name": request.template_name,
                "template_id": request.template_id,
            },
        )
        return result


class WorkflowMissionLoggingHook(WorkflowMissionHookAdapter):
    """Emit consistent kernel-level mission logs."""

    async def before_start(self, request: WorkflowMissionRequest) -> WorkflowMissionRequest:
        logger.info(
            "AgentKernel starting workflow mission template=%s template_id=%s run_source=%s lane=%s queue_mode=%s session_id=%s",
            request.template_name,
            request.template_id,
            request.run_source,
            request.lane,
            request.queue_mode,
            request.session_id,
        )
        return request

    async def after_start(
        self,
        request: WorkflowMissionRequest,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if "error" in result:
            logger.warning(
                "AgentKernel workflow mission blocked template=%s template_id=%s error=%s",
                request.template_name,
                request.template_id,
                result.get("error"),
            )
        else:
            logger.info(
                "AgentKernel workflow mission started template=%s template_id=%s execution_id=%s",
                request.template_name,
                request.template_id,
                result.get("execution_id") or result.get("workflow_execution_id"),
            )
        return result


class WorkflowLifecycleEventHook(WorkflowMissionHookAdapter):
    """Emit internal workflow lifecycle events for durable trigger orchestration."""

    async def after_start(
        self,
        request: WorkflowMissionRequest,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if "error" in result:
            return result
        if request.context.get("trigger"):
            return result

        from app.services.workflow_trigger_service import get_workflow_trigger_service

        payload = {
            "execution_id": result.get("execution_id") or result.get("workflow_execution_id"),
            "template_id": request.template_id,
            "template_name": request.template_name,
            "run_source": request.run_source,
            "persona": request.persona,
            "session_id": request.session_id,
            "lane": request.lane,
            "queue_mode": request.queue_mode,
        }
        try:
            await get_workflow_trigger_service().dispatch_event(
                user_id=request.user_id,
                event_name="workflow.started",
                payload=payload,
                source="workflow_hook",
            )
        except Exception as exc:
            logger.warning("Failed to dispatch workflow lifecycle event: %s", exc)

        return result


class AgentKernel:
    """Shared control-plane abstraction for mission-oriented workflow execution."""

    def __init__(self, workflow_engine=None, workflow_hooks: Optional[list[WorkflowMissionHook]] = None):
        self._workflow_engine = workflow_engine
        self._workflow_hooks = list(
            workflow_hooks
            or [
                WorkflowMissionMetadataHook(),
                WorkflowMissionLoggingHook(),
                WorkflowLifecycleEventHook(),
            ]
        )

    @property
    def workflow_engine(self):
        if self._workflow_engine is None:
            self._workflow_engine = get_workflow_engine()
        return self._workflow_engine

    def register_workflow_hook(self, hook: WorkflowMissionHook) -> None:
        self._workflow_hooks.append(hook)

    async def start_workflow_mission(
        self,
        *,
        user_id: str,
        template_name: Optional[str] = None,
        template_id: Optional[str] = None,
        template_version: Optional[int] = None,
        context: Optional[dict[str, Any]] = None,
        run_source: str = "user_ui",
        persona: Optional[str] = None,
        session_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        queue_mode: str = "followup",
        lane: str = "session",
    ) -> dict[str, Any]:
        request = WorkflowMissionRequest(
            user_id=user_id,
            template_name=template_name,
            template_id=template_id,
            template_version=template_version,
            context=dict(context or {}),
            run_source=run_source,
            persona=persona,
            session_id=session_id,
            parent_run_id=parent_run_id,
            queue_mode=queue_mode,
            lane=lane,
        )

        for hook in self._workflow_hooks:
            request = await hook.before_start(request)

        result = await self.workflow_engine.start_workflow(
            user_id=request.user_id,
            template_name=request.template_name,
            template_id=request.template_id,
            template_version=request.template_version,
            context=request.context,
            run_source=request.run_source,
            persona=request.persona,
        )

        normalized_result = dict(result)
        for hook in self._workflow_hooks:
            normalized_result = await hook.after_start(request, normalized_result)
        return normalized_result


def get_agent_kernel(
    *,
    workflow_engine=None,
    workflow_hooks: Optional[list[WorkflowMissionHook]] = None,
) -> AgentKernel:
    """Return a fresh kernel instance for the current orchestration path."""

    return AgentKernel(workflow_engine=workflow_engine, workflow_hooks=workflow_hooks)


