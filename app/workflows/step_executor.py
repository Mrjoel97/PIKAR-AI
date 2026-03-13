# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Step Executor for Workflow Automation.

Centralizes the logic for executing a single workflow step, including
strict argument mapping, trust labeling, and verification.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from app.agents.tools.registry import get_tool
from app.services.supabase_client import get_service_client
from app.workflows.execution_contracts import (
    WorkflowContractError,
    build_tool_kwargs,
    determine_trust_class,
    extract_evidence_refs,
    verify_step_output,
)

logger = logging.getLogger(__name__)


class StepExecutor:
    """Handles execution of a single workflow step with strict mapping."""

    def __init__(self, supabase_client=None):
        self.client = supabase_client or get_service_client()

    @staticmethod
    def _normalize_output(
        output: Any,
        *,
        tool_name: str,
        trust_class: str,
        verification_status: str,
        evidence_refs: list[Any],
        last_failure_reason: str | None = None,
        reason_code: str | None = None,
    ) -> dict[str, Any]:
        payload = dict(output) if isinstance(output, dict) else {"result": output}
        payload.setdefault("tool", tool_name)
        payload["_execution_meta"] = {
            "tool_name": tool_name,
            "trust_class": trust_class,
            "verification_status": verification_status,
            "evidence_refs": evidence_refs,
            "last_failure_reason": last_failure_reason,
            "reason_code": reason_code,
        }
        return payload

    async def execute_step(self, step: Dict, workflow_engine=None) -> Dict[str, Any]:
        """Execute a single workflow step with strict schema-based validation."""
        step_id = step["id"]
        tool_name = step["tool_name"]
        execution_id = step["execution_id"]
        step_definition = step.get("step_definition") or {}

        logger.info("StepExecutor: Executing Step %s (%s)", step_id, tool_name)

        try:
            tool_func = get_tool(tool_name)
            workflow_record = step.get("workflow_executions") or {}
            workflow_context = workflow_record.get("context") or {}
            input_data = step.get("input_data") or {}
            run_source = workflow_record.get("run_source") or workflow_context.get("run_source") or "user_ui"
            merged_context = {**workflow_context, **input_data}

            kwargs = build_tool_kwargs(
                tool_func,
                tool_name,
                merged_context,
                step_name=step.get("step_name") or "",
                step_description=step.get("description") or "",
                step_definition=step_definition,
                run_source=run_source,
            )

            if asyncio.iscoroutinefunction(tool_func):
                output = await tool_func(**kwargs)
            else:
                output = tool_func(**kwargs)

            verification = verify_step_output(output, step_definition=step_definition)
            if verification["status"] == "failed":
                raise WorkflowContractError(
                    "Step verification failed.",
                    reason_code="verification_failed",
                    details={"errors": verification.get("errors") or []},
                )

            trust_class = determine_trust_class(tool_name, step_definition=step_definition)
            result_payload = self._normalize_output(
                output,
                tool_name=tool_name,
                trust_class=trust_class,
                verification_status=verification["status"],
                evidence_refs=extract_evidence_refs(output),
            )

            self.client.table("workflow_steps").update(
                {
                    "status": "completed",
                    "output_data": result_payload,
                    "completed_at": datetime.now().isoformat(),
                    "error_message": None,
                }
            ).eq("id", step_id).execute()

            logger.info("StepExecutor: Step %s completed successfully.", step_id)

            if workflow_engine:
                from app.workflows.engine import WorkflowEngine

                if isinstance(workflow_engine, WorkflowEngine):
                    status = await workflow_engine.get_execution_status(execution_id)
                    if "error" not in status:
                        template_phases = status["execution"]["workflow_templates"]["phases"]
                        await workflow_engine._advance_workflow(status["execution"], template_phases)

            return result_payload

        except WorkflowContractError as exc:
            logger.error("StepExecutor: Step %s contract failure: %s", step_id, exc, exc_info=True)
            failure_payload = self._normalize_output(
                {"executed": False, "message": str(exc)},
                tool_name=tool_name,
                trust_class=determine_trust_class(tool_name, step_definition=step_definition),
                verification_status="failed",
                evidence_refs=[],
                last_failure_reason=str(exc),
                reason_code=exc.reason_code,
            )
            self.client.table("workflow_steps").update(
                {
                    "status": "failed",
                    "error_message": str(exc),
                    "output_data": failure_payload,
                }
            ).eq("id", step_id).execute()
            raise
        except Exception as exc:
            logger.error("StepExecutor: Step %s failed: %s", step_id, exc, exc_info=True)
            failure_payload = self._normalize_output(
                {"executed": False, "message": str(exc)},
                tool_name=tool_name,
                trust_class=determine_trust_class(tool_name, step_definition=step_definition),
                verification_status="failed",
                evidence_refs=[],
                last_failure_reason=str(exc),
                reason_code="step_execution_failed",
            )
            self.client.table("workflow_steps").update(
                {
                    "status": "failed",
                    "error_message": str(exc),
                    "output_data": failure_payload,
                }
            ).eq("id", step_id).execute()
            raise
