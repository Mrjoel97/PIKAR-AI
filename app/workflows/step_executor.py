# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Step Executor for Workflow Automation.

Centralizes the logic for executing a single workflow step, including
strict argument mapping, trust labeling, verification, step-level timeouts,
automatic retry with exponential backoff, conditional execution, duration
tracking, and graceful degradation for non-critical steps.
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Any

# Default timeout for a single step execution (seconds).
# Override per-step via step_definition.timeout_seconds or globally via env.
DEFAULT_STEP_TIMEOUT_SECONDS = int(os.getenv("WORKFLOW_STEP_TIMEOUT_SECONDS", "300"))

# Retry defaults (overridable per-step in step_definition).
DEFAULT_MAX_RETRIES = 0  # No automatic retry by default
DEFAULT_RETRY_DELAY_SECONDS = 5
DEFAULT_RETRY_BACKOFF_MULTIPLIER = 2.0

# Reason codes that should NOT be retried (permanent failures).
NON_RETRYABLE_REASON_CODES = frozenset(
    {
        "verification_failed",
        "missing_required_input",
        "unknown_tool",
        "schema_mismatch",
    }
)

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


def _resolve_condition_value(path: str, context: dict[str, Any]) -> Any:
    """Resolve a dotted path like 'prev.status' or 'context.campaign_id' from context."""
    parts = path.strip().split(".")
    current = context
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def evaluate_run_condition(condition: dict[str, Any], context: dict[str, Any]) -> bool:
    """Evaluate a step run_condition against workflow context.

    Supported condition formats:
        {"field": "prev.status", "equals": "completed"}
        {"field": "context.campaign_id", "not_equals": None}
        {"field": "prev.output.count", "greater_than": 0}
        {"any_of": [<condition>, <condition>, ...]}
        {"all_of": [<condition>, <condition>, ...]}

    Returns True if the step should execute, False to skip.
    """
    if not condition or not isinstance(condition, dict):
        return True

    # Compound conditions
    if "any_of" in condition:
        return any(evaluate_run_condition(c, context) for c in condition["any_of"])
    if "all_of" in condition:
        return all(evaluate_run_condition(c, context) for c in condition["all_of"])

    field = condition.get("field")
    if not field:
        return True

    value = _resolve_condition_value(field, context)

    if "equals" in condition:
        return value == condition["equals"]
    if "not_equals" in condition:
        return value != condition["not_equals"]
    if "greater_than" in condition:
        try:
            return float(value) > float(condition["greater_than"])
        except (TypeError, ValueError):
            return False
    if "less_than" in condition:
        try:
            return float(value) < float(condition["less_than"])
        except (TypeError, ValueError):
            return False
    if "in" in condition:
        return value in condition["in"]
    if "not_in" in condition:
        return value not in condition["not_in"]
    if "exists" in condition:
        return (value is not None) == condition["exists"]

    return True


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
        duration_ms: int | None = None,
        attempt: int = 1,
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
            "duration_ms": duration_ms,
            "attempt": attempt,
        }
        return payload

    async def _invoke_tool(
        self, tool_func, kwargs: dict[str, Any], timeout_seconds: int
    ) -> Any:
        """Invoke a tool function (sync or async) with timeout."""
        if asyncio.iscoroutinefunction(tool_func):
            coro = tool_func(**kwargs)
        else:
            coro = asyncio.to_thread(tool_func, **kwargs)

        return await asyncio.wait_for(coro, timeout=timeout_seconds)

    async def execute_step(self, step: dict, workflow_engine=None) -> dict[str, Any]:
        """Execute a single workflow step with full production capabilities.

        Features:
        - Strict schema-based argument mapping
        - Configurable timeouts (per-step or global)
        - Automatic retry with exponential backoff
        - Conditional execution (skip based on prior output)
        - Duration tracking (duration_ms on every step)
        - Graceful degradation (on_failure: skip for non-critical steps)
        """
        step_id = step["id"]
        tool_name = step["tool_name"]
        execution_id = step["execution_id"]
        step_definition = step.get("step_definition") or {}

        logger.info("StepExecutor: Executing Step %s (%s)", step_id, tool_name)

        # ── Conditional execution gate ──────────────────────────────────
        run_condition = step_definition.get("run_condition")
        if run_condition:
            workflow_record = step.get("workflow_executions") or {}
            condition_context = {
                **(workflow_record.get("context") or {}),
                **(step.get("input_data") or {}),
            }
            # Add previous step output under "prev" key if available
            prev_output = step.get("prev_step_output")
            if prev_output:
                condition_context["prev"] = prev_output

            if not evaluate_run_condition(run_condition, condition_context):
                logger.info(
                    "StepExecutor: Step %s skipped (run_condition evaluated to false)",
                    step_id,
                )
                skip_payload = self._normalize_output(
                    {"executed": False, "message": "Skipped: run_condition was false"},
                    tool_name=tool_name,
                    trust_class=determine_trust_class(
                        tool_name, step_definition=step_definition
                    ),
                    verification_status="skipped",
                    evidence_refs=[],
                    duration_ms=0,
                )
                self.client.table("workflow_steps").update(
                    {
                        "status": "skipped",
                        "output_data": skip_payload,
                        "completed_at": datetime.now().isoformat(),
                        "error_message": None,
                    }
                ).eq("id", step_id).execute()

                # Advance workflow even when skipping
                if workflow_engine:
                    await self._try_advance(workflow_engine, execution_id)
                return skip_payload

        # ── Prepare execution context ───────────────────────────────────
        try:
            tool_func = get_tool(tool_name)
            workflow_record = step.get("workflow_executions") or {}
            workflow_context = workflow_record.get("context") or {}
            input_data = step.get("input_data") or {}
            run_source = (
                workflow_record.get("run_source")
                or workflow_context.get("run_source")
                or "user_ui"
            )
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
        except Exception as exc:
            # Preparation failures are non-retryable
            return await self._handle_failure(
                step_id=step_id,
                tool_name=tool_name,
                step_definition=step_definition,
                exc=exc,
                reason_code="step_preparation_failed",
                duration_ms=0,
                attempt=1,
                workflow_engine=workflow_engine,
                execution_id=execution_id,
            )

        # ── Retry configuration ─────────────────────────────────────────
        timeout_seconds = (
            step_definition.get("timeout_seconds") or DEFAULT_STEP_TIMEOUT_SECONDS
        )
        max_retries = (
            step_definition.get("max_retries")
            if step_definition.get("max_retries") is not None
            else DEFAULT_MAX_RETRIES
        )
        retry_delay = (
            step_definition.get("retry_delay_seconds") or DEFAULT_RETRY_DELAY_SECONDS
        )
        retry_backoff = (
            step_definition.get("retry_backoff_multiplier")
            or DEFAULT_RETRY_BACKOFF_MULTIPLIER
        )
        on_failure = step_definition.get("on_failure", "fail")  # "fail" or "skip"

        last_exc = None
        attempt = 0

        # ── Execution loop with retry ───────────────────────────────────
        while attempt <= max_retries:
            attempt += 1
            t0 = time.monotonic()

            try:
                # Update attempt count in DB
                self.client.table("workflow_steps").update(
                    {"attempt_count": attempt}
                ).eq("id", step_id).execute()

                output = await self._invoke_tool(tool_func, kwargs, timeout_seconds)

                duration_ms = int((time.monotonic() - t0) * 1000)

                # ── Verification ────────────────────────────────────────
                verification = verify_step_output(
                    output, step_definition=step_definition
                )
                if verification["status"] == "failed":
                    raise WorkflowContractError(
                        "Step verification failed.",
                        reason_code="verification_failed",
                        details={"errors": verification.get("errors") or []},
                    )

                # ── Success ─────────────────────────────────────────────
                trust_class = determine_trust_class(
                    tool_name, step_definition=step_definition
                )
                result_payload = self._normalize_output(
                    output,
                    tool_name=tool_name,
                    trust_class=trust_class,
                    verification_status=verification["status"],
                    evidence_refs=extract_evidence_refs(output),
                    duration_ms=duration_ms,
                    attempt=attempt,
                )

                self.client.table("workflow_steps").update(
                    {
                        "status": "completed",
                        "output_data": result_payload,
                        "completed_at": datetime.now().isoformat(),
                        "error_message": None,
                    }
                ).eq("id", step_id).execute()

                logger.info(
                    "StepExecutor: Step %s completed (attempt %d, %dms).",
                    step_id,
                    attempt,
                    duration_ms,
                )

                if workflow_engine:
                    await self._try_advance(workflow_engine, execution_id)

                return result_payload

            except asyncio.TimeoutError:
                last_exc = WorkflowContractError(
                    f"Step '{tool_name}' timed out after {timeout_seconds}s",
                    reason_code="step_timeout",
                    details={"timeout_seconds": timeout_seconds, "step_id": step_id},
                )
                logger.warning(
                    "StepExecutor: Step %s timed out (attempt %d/%d)",
                    step_id,
                    attempt,
                    max_retries + 1,
                )

            except WorkflowContractError as exc:
                last_exc = exc
                # Non-retryable contract errors break immediately
                if exc.reason_code in NON_RETRYABLE_REASON_CODES:
                    logger.error(
                        "StepExecutor: Step %s non-retryable failure: %s",
                        step_id,
                        exc,
                    )
                    break
                logger.warning(
                    "StepExecutor: Step %s contract error (attempt %d/%d): %s",
                    step_id,
                    attempt,
                    max_retries + 1,
                    exc,
                )

            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "StepExecutor: Step %s failed (attempt %d/%d): %s",
                    step_id,
                    attempt,
                    max_retries + 1,
                    exc,
                )

            # ── Retry delay (if more attempts remain) ───────────────────
            if attempt <= max_retries:
                delay = retry_delay * (retry_backoff ** (attempt - 1))
                logger.info(
                    "StepExecutor: Step %s retrying in %.1fs (attempt %d/%d)",
                    step_id,
                    delay,
                    attempt + 1,
                    max_retries + 1,
                )
                await asyncio.sleep(delay)

        # ── All attempts exhausted ──────────────────────────────────────
        duration_ms = int((time.monotonic() - t0) * 1000) if "t0" in dir() else 0

        return await self._handle_failure(
            step_id=step_id,
            tool_name=tool_name,
            step_definition=step_definition,
            exc=last_exc,
            reason_code=getattr(last_exc, "reason_code", "step_execution_failed"),
            duration_ms=duration_ms,
            attempt=attempt,
            workflow_engine=workflow_engine,
            execution_id=execution_id,
            on_failure=on_failure,
        )

    async def _handle_failure(
        self,
        *,
        step_id: str,
        tool_name: str,
        step_definition: dict,
        exc: Exception | None,
        reason_code: str,
        duration_ms: int,
        attempt: int,
        workflow_engine=None,
        execution_id: str = "",
        on_failure: str = "fail",
    ) -> dict[str, Any]:
        """Handle step failure with optional graceful degradation."""
        error_msg = str(exc) if exc else "Unknown error"
        trust_class = determine_trust_class(tool_name, step_definition=step_definition)

        failure_payload = self._normalize_output(
            {"executed": False, "message": error_msg},
            tool_name=tool_name,
            trust_class=trust_class,
            verification_status="failed",
            evidence_refs=[],
            last_failure_reason=error_msg,
            reason_code=reason_code,
            duration_ms=duration_ms,
            attempt=attempt,
        )

        # Graceful degradation: on_failure="skip" marks step as skipped, not failed
        if on_failure == "skip":
            logger.warning(
                "StepExecutor: Step %s failed but on_failure=skip, degrading gracefully. Error: %s",
                step_id,
                error_msg,
            )
            failure_payload["_execution_meta"]["degraded"] = True
            self.client.table("workflow_steps").update(
                {
                    "status": "skipped",
                    "error_message": f"[degraded] {error_msg}",
                    "output_data": failure_payload,
                    "completed_at": datetime.now().isoformat(),
                }
            ).eq("id", step_id).execute()

            # Continue workflow despite failure
            if workflow_engine:
                await self._try_advance(workflow_engine, execution_id)
            return failure_payload

        # Normal failure: mark as failed and raise
        logger.error(
            "StepExecutor: Step %s permanently failed: %s", step_id, exc, exc_info=True
        )
        self.client.table("workflow_steps").update(
            {
                "status": "failed",
                "error_message": error_msg,
                "output_data": failure_payload,
            }
        ).eq("id", step_id).execute()

        if exc:
            raise exc
        raise WorkflowContractError(error_msg, reason_code=reason_code)

    async def execute_parallel_steps(
        self,
        steps: list[dict],
        workflow_engine=None,
    ) -> list[dict[str, Any]]:
        """Execute multiple steps concurrently via asyncio.gather.

        Steps with parallel=true in their step_definition are grouped and
        executed simultaneously. Each step's success/failure is independent —
        one failing step doesn't cancel the others (unless on_failure="fail"
        propagates to the workflow level).

        Args:
            steps: List of step dicts to execute in parallel.
            workflow_engine: Optional engine for post-step advancement.

        Returns:
            List of result payloads (one per step, in input order).
        """
        if not steps:
            return []

        if len(steps) == 1:
            result = await self.execute_step(steps[0], workflow_engine)
            return [result]

        logger.info(
            "StepExecutor: Executing %d steps in parallel: %s",
            len(steps),
            [s.get("tool_name", "?") for s in steps],
        )

        async def _safe_execute(step: dict) -> dict[str, Any]:
            """Execute a step, catching exceptions to allow gather to continue."""
            try:
                return await self.execute_step(step, workflow_engine=None)
            except Exception as exc:
                # Step already marked as failed in DB by execute_step
                return {
                    "executed": False,
                    "message": str(exc),
                    "tool": step.get("tool_name", "unknown"),
                    "_execution_meta": {
                        "tool_name": step.get("tool_name", "unknown"),
                        "verification_status": "failed",
                        "reason_code": getattr(
                            exc, "reason_code", "step_execution_failed"
                        ),
                    },
                }

        results = await asyncio.gather(*[_safe_execute(s) for s in steps])

        # After all parallel steps complete, advance the workflow once
        if workflow_engine:
            execution_id = steps[0].get("execution_id", "")
            if execution_id:
                await self._try_advance(workflow_engine, execution_id)

        return list(results)

    async def _try_advance(self, workflow_engine, execution_id: str) -> None:
        """Attempt to advance the workflow after step completion/skip."""
        try:
            from app.workflows.engine import WorkflowEngine

            if isinstance(workflow_engine, WorkflowEngine):
                status = await workflow_engine.get_execution_status(execution_id)
                if "error" not in status:
                    template_phases = status["execution"]["workflow_templates"][
                        "phases"
                    ]
                    await workflow_engine._advance_workflow(
                        status["execution"], template_phases
                    )
        except Exception as exc:
            logger.error(
                "StepExecutor: Failed to advance workflow %s: %s", execution_id, exc
            )
