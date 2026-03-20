"""Autonomous department cycle runner.

Orchestrates proactive triggers, inter-department requests, and workflow
lifecycle tracking for each RUNNING department.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Guardrails: max workflows each department may launch per cycle
# ---------------------------------------------------------------------------
MAX_WORKFLOWS_PER_CYCLE: dict[str, int] = {
    "SALES": 3,
    "MARKETING": 2,
    "SUPPORT": 5,
    "OPERATIONS": 2,
    "CONTENT": 2,
    "STRATEGIC": 1,
    "FINANCIAL": 1,
    "HR": 1,
    "COMPLIANCE": 1,
    "DATA": 3,
}


class DepartmentRunner:
    """Orchestrates the autonomous execution of Departments."""

    def __init__(self) -> None:
        self.supabase = get_service_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def tick(self) -> list[dict[str, Any]]:
        """Run one cycle for all RUNNING departments."""
        try:
            res = await execute_async(
                self.supabase.table("departments").select("*").eq("status", "RUNNING"),
                op_name="department_runner.list_running",
            )
            departments = res.data or []
            logger.info(
                "Department Runner ticking... found %s active departments",
                len(departments),
            )

            results: list[dict[str, Any]] = []
            for dept in departments:
                if self._should_run(dept):
                    result = await self.run_department_cycle(dept)
                    results.append(result)
                else:
                    results.append(
                        {"dept_id": dept["id"], "activity": "Skipped (interval)"}
                    )
            return results
        except Exception as e:
            logger.error("Department Runner failed: %s", e)
            raise

    # ------------------------------------------------------------------
    # Interval gate
    # ------------------------------------------------------------------

    def _should_run(self, dept: dict[str, Any]) -> bool:
        """Check if enough time has passed since the last heartbeat."""
        last_heartbeat_str = dept.get("last_heartbeat")
        if not last_heartbeat_str:
            return True

        config = dept.get("config") or {}
        interval_mins = config.get("check_interval_mins", 60)
        try:
            interval_mins = int(interval_mins)
        except (TypeError, ValueError):
            logger.warning(
                "Department %s has invalid check_interval_mins=%r; defaulting to run",
                dept.get("id"),
                interval_mins,
            )
            return True

        if interval_mins <= 0:
            return True

        try:
            last_heartbeat = datetime.fromisoformat(
                str(last_heartbeat_str).replace("Z", "+00:00")
            )
        except ValueError:
            logger.warning(
                "Department %s has invalid last_heartbeat=%r; defaulting to run",
                dept.get("id"),
                last_heartbeat_str,
            )
            return True

        if last_heartbeat.tzinfo is None:
            last_heartbeat = last_heartbeat.replace(tzinfo=timezone.utc)

        next_run_time = last_heartbeat + timedelta(minutes=interval_mins)
        return datetime.now(timezone.utc) >= next_run_time

    # ------------------------------------------------------------------
    # Main dispatcher
    # ------------------------------------------------------------------

    async def run_department_cycle(self, dept: dict[str, Any]) -> dict[str, Any]:
        """Execute logic for a specific department type."""
        dept_id = dept["id"]
        dept_type = dept["type"]
        state = dept.get("state") or {}

        logger.info("Running cycle for %s (%s)", dept["name"], dept_type)
        new_state = state.copy()
        activity_log = f"Processed cycle for {dept_type}"

        try:
            if dept_type == "SALES":
                activity_log = await self._run_sales_cycle(state, new_state)
            elif dept_type == "MARKETING":
                activity_log = await self._run_marketing_cycle(state, new_state)
            elif dept_type == "CONTENT":
                activity_log = await self._run_content_cycle(state, new_state)
            elif dept_type == "STRATEGIC":
                activity_log = await self._run_strategic_cycle(state, new_state)
            elif dept_type == "DATA":
                activity_log = await self._run_data_cycle(state, new_state)
            elif dept_type == "FINANCIAL":
                activity_log = await self._run_financial_cycle(state, new_state)
            elif dept_type == "SUPPORT":
                activity_log = await self._run_support_cycle(state, new_state)
            elif dept_type == "HR":
                activity_log = await self._run_hr_cycle(state, new_state)
            elif dept_type == "COMPLIANCE":
                activity_log = await self._run_compliance_cycle(state, new_state)
            elif dept_type == "OPERATIONS":
                activity_log = await self._run_operations_cycle(state, new_state)
            else:
                activity_log = f"Unknown department type: {dept_type}"
        except Exception as e:
            logger.error("Error in %s cycle: %s", dept_type, e)
            activity_log = f"Error: {e!s}"

        await execute_async(
            self.supabase.table("departments")
            .update(
                {
                    "state": new_state,
                    "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", dept_id),
            op_name="department_runner.update_department",
        )
        return {"dept_id": dept_id, "activity": activity_log}

    # ------------------------------------------------------------------
    # Shared core cycle — all 10 departments delegate here
    # ------------------------------------------------------------------

    async def _core_cycle(
        self,
        dept_type: str,
        state: dict[str, Any],
        new_state: dict[str, Any],
    ) -> str:
        """Shared cycle logic for all departments."""
        dept_id = state.get("dept_id")
        decisions: list[dict[str, Any]] = []

        # Phase 1: Handle incoming inter-department requests
        inter_dept = await self._handle_inter_dept_requests(dept_id, new_state)
        decisions.extend(inter_dept)

        # Phase 2: Evaluate proactive triggers
        triggered = await self._evaluate_triggers(dept_id, dept_type, state, new_state)
        decisions.extend(triggered)

        # Phase 3: Monitor pending workflow completions
        completed = await self._check_workflow_completions(state, new_state)
        decisions.extend(completed)

        # Phase 4: Log all decisions
        for d in decisions:
            await self._log_decision(dept_id, d)

        # Phase 5: Update cycle metrics
        new_state["last_cycle_metrics"] = {
            "triggers_evaluated": sum(
                1
                for d in decisions
                if d.get("decision_type") in ("trigger_matched", "trigger_skipped")
            ),
            "workflows_launched": sum(
                1 for d in decisions if d.get("decision_type") == "workflow_launched"
            ),
            "workflows_completed": sum(
                1 for d in decisions if d.get("decision_type") == "workflow_completed"
            ),
            "escalations": sum(
                1 for d in decisions if d.get("decision_type") == "escalated"
            ),
            "inter_dept_handled": len(inter_dept),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if not decisions:
            await self._log_decision(
                dept_id,
                {
                    "decision_type": "no_action",
                    "decision_logic": f"{dept_type} cycle completed, no triggers matched",
                    "outcome": "skipped",
                },
            )

        launched = new_state["last_cycle_metrics"]["workflows_launched"]
        return f"{dept_type} cycle: {len(decisions)} decisions, {launched} workflows launched"

    # ------------------------------------------------------------------
    # Phase 1: Inter-department requests
    # ------------------------------------------------------------------

    async def _handle_inter_dept_requests(
        self,
        dept_id: str | None,
        new_state: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Handle pending inter-department requests addressed to this department.

        For requests whose context includes a ``workflow_template``, a new
        workflow execution is created and tracked.  All other requests are
        acknowledged so the sending department knows they were received.
        """
        if not dept_id:
            return []

        decisions: list[dict[str, Any]] = []
        try:
            res = await execute_async(
                self.supabase.table("inter_dept_requests")
                .select("*")
                .eq("to_department_id", dept_id)
                .eq("status", "pending"),
                op_name="department_runner.get_inter_dept_pending",
            )
            requests = res.data or []

            for req in requests:
                req_context = req.get("context") or {}
                template_id = req_context.get("workflow_template")

                if template_id:
                    # Launch a workflow from the template
                    wf_id = await self._launch_workflow_for_request(
                        req, template_id, dept_id, new_state
                    )
                    update_payload: dict[str, Any] = {
                        "status": "in_progress",
                    }
                    if wf_id:
                        update_payload["assigned_workflow_id"] = wf_id

                    await execute_async(
                        self.supabase.table("inter_dept_requests")
                        .update(update_payload)
                        .eq("id", req["id"]),
                        op_name="department_runner.progress_inter_dept",
                    )
                    decisions.append(
                        {
                            "decision_type": "workflow_launched",
                            "decision_logic": (
                                f"Launched workflow from template {template_id} "
                                f"for inter-dept request '{req.get('request_type')}' "
                                f"from department {req.get('from_department_id')}"
                            ),
                            "action_taken": {
                                "request_id": req["id"],
                                "workflow_execution_id": wf_id,
                                "template_id": template_id,
                            },
                            "outcome": "launched",
                        }
                    )
                else:
                    # No workflow template — just acknowledge
                    await execute_async(
                        self.supabase.table("inter_dept_requests")
                        .update({"status": "acknowledged"})
                        .eq("id", req["id"]),
                        op_name="department_runner.ack_inter_dept",
                    )
                    decisions.append(
                        {
                            "decision_type": "inter_dept_acknowledged",
                            "decision_logic": (
                                f"Acknowledged request '{req.get('request_type')}' "
                                f"from department {req.get('from_department_id')}"
                            ),
                            "action_taken": {
                                "request_id": req["id"],
                                "request_type": req.get("request_type"),
                                "from_department_id": req.get("from_department_id"),
                            },
                            "outcome": "acknowledged",
                        }
                    )
        except Exception as e:
            logger.warning(
                "Failed to handle inter-dept requests for %s: %s", dept_id, e
            )

        return decisions

    async def _launch_workflow_for_request(
        self,
        req: dict[str, Any],
        template_id: str,
        dept_id: str,
        new_state: dict[str, Any] | None,
    ) -> str | None:
        """Create a workflow execution for an inter-department request.

        Returns the new workflow execution ID, or ``None`` on failure.
        """
        req_context = req.get("context") or {}
        workflow_name = req_context.get(
            "workflow_name",
            f"Inter-dept: {req.get('request_type', 'request')}",
        )

        exec_data: dict[str, Any] = {
            "template_id": template_id,
            "name": workflow_name,
            "status": "pending",
            "current_phase_index": 0,
            "current_step_index": 0,
            "context": {
                "inter_dept_request_id": req["id"],
                "from_department_id": req.get("from_department_id"),
                "department_id": dept_id,
                "auto_launched": True,
                **{k: v for k, v in req_context.items() if k != "workflow_template"},
            },
        }
        user_id = req_context.get("user_id")
        if user_id:
            exec_data["user_id"] = user_id

        try:
            res = await execute_async(
                self.supabase.table("workflow_executions")
                .insert(exec_data)
                .select("id"),
                op_name="department_runner.launch_inter_dept_workflow",
            )
            wf_id = res.data[0]["id"] if res.data else None

            # Track in pending_workflows if state dict was provided
            if wf_id and new_state is not None:
                pending = new_state.get("pending_workflows") or []
                pending.append(
                    {
                        "workflow_execution_id": wf_id,
                        "inter_dept_request_id": req["id"],
                        "launched_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                new_state["pending_workflows"] = pending

            return wf_id
        except Exception as e:
            logger.error(
                "Failed to launch workflow for inter-dept request %s: %s",
                req["id"],
                e,
            )
            return None

    # ------------------------------------------------------------------
    # Phase 2: Proactive triggers
    # ------------------------------------------------------------------

    async def _evaluate_triggers(
        self,
        dept_id: str | None,
        dept_type: str,
        state: dict[str, Any],
        new_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Evaluate all enabled proactive triggers for a department."""
        if not dept_id:
            return []

        decisions: list[dict[str, Any]] = []
        workflows_launched_this_cycle = 0
        max_workflows = MAX_WORKFLOWS_PER_CYCLE.get(dept_type, 2)

        try:
            res = await execute_async(
                self.supabase.table("proactive_triggers")
                .select("*")
                .eq("department_id", dept_id)
                .eq("enabled", True),
                op_name="department_runner.get_triggers",
            )
            triggers = res.data or []
        except Exception as e:
            logger.warning("Failed to fetch triggers for %s: %s", dept_id, e)
            return []

        for trigger in triggers:
            try:
                trigger_id = trigger["id"]
                trigger_name = trigger.get("name", "unnamed")

                # --- Cooldown check ---
                cooldown_hours = trigger.get("cooldown_hours", 24)
                last_triggered = trigger.get("last_triggered_at")
                if last_triggered:
                    try:
                        last_dt = datetime.fromisoformat(
                            str(last_triggered).replace("Z", "+00:00")
                        )
                        if last_dt.tzinfo is None:
                            last_dt = last_dt.replace(tzinfo=timezone.utc)
                        cooldown_end = last_dt + timedelta(hours=cooldown_hours)
                        if datetime.now(timezone.utc) < cooldown_end:
                            decisions.append(
                                {
                                    "decision_type": "trigger_skipped",
                                    "trigger_id": trigger_id,
                                    "decision_logic": (
                                        f"Trigger '{trigger_name}' still in cooldown "
                                        f"until {cooldown_end.isoformat()}"
                                    ),
                                    "outcome": "cooldown",
                                }
                            )
                            continue
                    except (ValueError, TypeError):
                        pass  # Treat unparseable as no cooldown

                # --- Condition evaluation ---
                condition_config = trigger.get("condition_config") or {}
                condition_type = trigger.get("condition_type", "metric_threshold")
                matched, explanation = self._evaluate_condition(
                    condition_type, condition_config, state
                )

                if not matched:
                    decisions.append(
                        {
                            "decision_type": "trigger_skipped",
                            "trigger_id": trigger_id,
                            "decision_logic": (
                                f"Trigger '{trigger_name}' condition not met: {explanation}"
                            ),
                            "outcome": "condition_unmet",
                        }
                    )
                    continue

                # --- Rate-limit check ---
                if workflows_launched_this_cycle >= max_workflows:
                    decisions.append(
                        {
                            "decision_type": "trigger_skipped",
                            "trigger_id": trigger_id,
                            "decision_logic": (
                                f"Trigger '{trigger_name}' matched but rate limit "
                                f"reached ({max_workflows} workflows/cycle)"
                            ),
                            "outcome": "rate_limited",
                        }
                    )
                    continue

                # --- Execute action ---
                action_decisions, wf_launched = await self._execute_trigger_action(
                    trigger, new_state
                )
                decisions.extend(action_decisions)
                workflows_launched_this_cycle += wf_launched

                # Update last_triggered_at
                await execute_async(
                    self.supabase.table("proactive_triggers")
                    .update(
                        {"last_triggered_at": datetime.now(timezone.utc).isoformat()}
                    )
                    .eq("id", trigger_id),
                    op_name="department_runner.update_trigger_ts",
                )

                decisions.append(
                    {
                        "decision_type": "trigger_matched",
                        "trigger_id": trigger_id,
                        "decision_logic": f"Trigger '{trigger_name}' matched: {explanation}",
                        "outcome": "executed",
                    }
                )

            except Exception as e:
                logger.error("Error evaluating trigger %s: %s", trigger.get("id"), e)
                decisions.append(
                    {
                        "decision_type": "trigger_error",
                        "trigger_id": trigger.get("id"),
                        "decision_logic": f"Error evaluating trigger: {e!s}",
                        "outcome": "error",
                    }
                )

        return decisions

    # ------------------------------------------------------------------
    # Condition evaluator
    # ------------------------------------------------------------------

    def _evaluate_condition(
        self,
        condition_type: str,
        condition_config: dict[str, Any],
        state: dict[str, Any],
    ) -> tuple[bool, str]:
        """Evaluate a trigger condition against current state.

        Returns (matched, explanation).
        """
        try:
            if condition_type == "metric_threshold":
                return self._eval_metric_threshold(condition_config, state)
            if condition_type == "time_based":
                return self._eval_time_based(condition_config)
            if condition_type == "event_count":
                return self._eval_event_count(condition_config, state)
        except Exception as e:
            return False, f"Condition evaluation error: {e!s}"

        return False, f"Unknown condition type: {condition_type}"

    def _eval_metric_threshold(
        self, config: dict[str, Any], state: dict[str, Any]
    ) -> tuple[bool, str]:
        """Compare a metric_key in state against a threshold."""
        metric_key = config.get("metric_key", "")
        threshold = config.get("threshold")
        operator = config.get("operator", "gte")  # gte, lte, gt, lt, eq

        # Look up the metric value in state (support dotted keys like "metrics.leads")
        value = state
        for part in metric_key.split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break

        if value is None:
            return False, f"Metric '{metric_key}' not found in state"

        try:
            value = float(value)
            threshold = float(threshold)
        except (TypeError, ValueError):
            return False, f"Non-numeric metric or threshold: {value!r} vs {threshold!r}"

        ops = {
            "gte": value >= threshold,
            "lte": value <= threshold,
            "gt": value > threshold,
            "lt": value < threshold,
            "eq": value == threshold,
        }
        matched = ops.get(operator, False)
        return matched, f"{metric_key}={value} {operator} {threshold} -> {matched}"

    def _eval_time_based(self, config: dict[str, Any]) -> tuple[bool, str]:
        """Check if enough time has elapsed since a reference timestamp."""
        reference_iso = config.get("reference_timestamp")
        min_elapsed_hours = config.get("min_elapsed_hours", 0)

        if not reference_iso:
            return True, "No reference timestamp; condition passes by default"

        try:
            ref_dt = datetime.fromisoformat(str(reference_iso).replace("Z", "+00:00"))
            if ref_dt.tzinfo is None:
                ref_dt = ref_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return False, f"Unparseable reference_timestamp: {reference_iso!r}"

        elapsed = datetime.now(timezone.utc) - ref_dt
        elapsed_hours = elapsed.total_seconds() / 3600
        matched = elapsed_hours >= float(min_elapsed_hours)
        return matched, f"Elapsed {elapsed_hours:.1f}h vs required {min_elapsed_hours}h"

    def _eval_event_count(
        self, config: dict[str, Any], state: dict[str, Any]
    ) -> tuple[bool, str]:
        """Check if an event count in state exceeds a threshold."""
        event_key = config.get("event_key", "")
        min_count = config.get("min_count", 1)

        # Look up event count in state
        value = state
        for part in event_key.split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break

        if value is None:
            return False, f"Event key '{event_key}' not found in state"

        try:
            count = int(value)
        except (TypeError, ValueError):
            return False, f"Non-integer event count: {value!r}"

        matched = count >= int(min_count)
        return matched, f"{event_key}={count} vs min_count={min_count}"

    # ------------------------------------------------------------------
    # Trigger action executor
    # ------------------------------------------------------------------

    async def _execute_trigger_action(
        self,
        trigger: dict[str, Any],
        new_state: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], int]:
        """Execute the action defined by a trigger.

        Returns (decisions, workflows_launched_count).
        """
        action_type = trigger.get("action_type", "notify")
        action_config = trigger.get("action_config") or {}
        trigger_id = trigger["id"]
        trigger_name = trigger.get("name", "unnamed")
        dept_id = trigger.get("department_id")
        decisions: list[dict[str, Any]] = []
        workflows_launched = 0

        try:
            if action_type == "launch_workflow":
                template_id = action_config.get("template_id")
                workflow_name = action_config.get(
                    "workflow_name", f"Auto: {trigger_name}"
                )
                context_overrides = action_config.get("context", {})

                if template_id:
                    # Create a workflow execution entry
                    exec_data = {
                        "template_id": template_id,
                        "name": workflow_name,
                        "status": "pending",
                        "current_phase_index": 0,
                        "current_step_index": 0,
                        "context": {
                            "trigger_id": trigger_id,
                            "department_id": dept_id,
                            "auto_launched": True,
                            **context_overrides,
                        },
                    }
                    # user_id is required; use a system user or the dept config
                    user_id = action_config.get("user_id")
                    if user_id:
                        exec_data["user_id"] = user_id

                    res = await execute_async(
                        self.supabase.table("workflow_executions")
                        .insert(exec_data)
                        .select("id"),
                        op_name="department_runner.launch_workflow",
                    )
                    wf_id = res.data[0]["id"] if res.data else None

                    # Track in pending_workflows
                    pending = new_state.get("pending_workflows") or []
                    pending.append(
                        {
                            "workflow_execution_id": wf_id,
                            "trigger_id": trigger_id,
                            "launched_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    new_state["pending_workflows"] = pending
                    workflows_launched += 1

                    decisions.append(
                        {
                            "decision_type": "workflow_launched",
                            "trigger_id": trigger_id,
                            "decision_logic": (
                                f"Launched workflow '{workflow_name}' "
                                f"from template {template_id}"
                            ),
                            "action_taken": {
                                "workflow_execution_id": wf_id,
                                "template_id": template_id,
                            },
                            "outcome": "launched",
                        }
                    )
                else:
                    decisions.append(
                        {
                            "decision_type": "trigger_error",
                            "trigger_id": trigger_id,
                            "decision_logic": "launch_workflow action missing template_id",
                            "outcome": "error",
                        }
                    )

            elif action_type == "escalate":
                target_dept_id = action_config.get("target_department_id")
                # Resolve target by department type when UUID is not known
                to_dept_type = action_config.get("to_department_type")
                if not target_dept_id and to_dept_type:
                    target_dept_id = await self._resolve_department_id(to_dept_type)

                request_type = action_config.get("request_type", "escalation")
                payload = action_config.get("payload", {})
                priority = action_config.get("priority", 3)

                if target_dept_id:
                    await execute_async(
                        self.supabase.table("inter_dept_requests").insert(
                            {
                                "from_department_id": dept_id,
                                "to_department_id": target_dept_id,
                                "request_type": request_type,
                                "context": {
                                    "trigger_id": trigger_id,
                                    "trigger_name": trigger_name,
                                    **payload,
                                },
                                "priority": priority,
                                "status": "pending",
                            }
                        ),
                        op_name="department_runner.create_escalation",
                    )
                    decisions.append(
                        {
                            "decision_type": "escalated",
                            "trigger_id": trigger_id,
                            "decision_logic": (
                                f"Escalated '{request_type}' to department "
                                f"{target_dept_id}"
                            ),
                            "action_taken": {
                                "target_department_id": target_dept_id,
                                "request_type": request_type,
                            },
                            "outcome": "escalated",
                        }
                    )
                else:
                    decisions.append(
                        {
                            "decision_type": "trigger_error",
                            "trigger_id": trigger_id,
                            "decision_logic": (
                                "escalate action missing target_department_id "
                                "and could not resolve to_department_type"
                            ),
                            "outcome": "error",
                        }
                    )

            elif action_type == "notify":
                message = action_config.get(
                    "message", f"Trigger '{trigger_name}' fired"
                )
                severity = action_config.get("severity", "info")

                # Log as a decision; real notification integration can be added later
                decisions.append(
                    {
                        "decision_type": "notification_sent",
                        "trigger_id": trigger_id,
                        "decision_logic": f"Notification: {message}",
                        "action_taken": {
                            "message": message,
                            "severity": severity,
                        },
                        "outcome": "notified",
                    }
                )

            else:
                decisions.append(
                    {
                        "decision_type": "trigger_error",
                        "trigger_id": trigger_id,
                        "decision_logic": f"Unknown action_type: {action_type}",
                        "outcome": "error",
                    }
                )

        except Exception as e:
            logger.error("Error executing trigger action %s: %s", trigger_id, e)
            decisions.append(
                {
                    "decision_type": "trigger_error",
                    "trigger_id": trigger_id,
                    "decision_logic": f"Action execution error: {e!s}",
                    "outcome": "error",
                }
            )

        return decisions, workflows_launched

    # ------------------------------------------------------------------
    # Phase 3: Workflow completion tracking
    # ------------------------------------------------------------------

    async def _check_workflow_completions(
        self,
        state: dict[str, Any],
        new_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Check status of pending workflows and reconcile state."""
        pending = list(state.get("pending_workflows") or [])
        if not pending:
            return []

        decisions: list[dict[str, Any]] = []
        still_pending: list[dict[str, Any]] = []

        for pw in pending:
            wf_id = pw.get("workflow_execution_id")
            if not wf_id:
                continue

            try:
                res = await execute_async(
                    self.supabase.table("workflow_executions")
                    .select("id, status, context")
                    .eq("id", wf_id),
                    op_name="department_runner.check_wf_status",
                )
                rows = res.data or []
                if not rows:
                    # Workflow execution was deleted; drop from pending
                    decisions.append(
                        {
                            "decision_type": "workflow_missing",
                            "decision_logic": f"Workflow {wf_id} no longer exists",
                            "action_taken": {"workflow_execution_id": wf_id},
                            "outcome": "removed",
                        }
                    )
                    continue

                wf = rows[0]
                wf_status = wf.get("status", "unknown")

                if wf_status in ("completed",):
                    # Update linked initiative if present
                    wf_context = wf.get("context") or {}
                    initiative_id = wf_context.get("initiative_id")
                    if initiative_id:
                        try:
                            await execute_async(
                                self.supabase.table("initiatives")
                                .update({"operational_state": "workflow_completed"})
                                .eq("id", initiative_id),
                                op_name="department_runner.update_initiative",
                            )
                        except Exception as e:
                            logger.warning(
                                "Failed to update initiative %s: %s", initiative_id, e
                            )

                    decisions.append(
                        {
                            "decision_type": "workflow_completed",
                            "decision_logic": f"Workflow {wf_id} completed",
                            "action_taken": {
                                "workflow_execution_id": wf_id,
                                "initiative_id": initiative_id,
                            },
                            "outcome": "completed",
                        }
                    )

                elif wf_status in ("failed", "cancelled"):
                    decisions.append(
                        {
                            "decision_type": "workflow_failed",
                            "decision_logic": (
                                f"Workflow {wf_id} ended with status '{wf_status}'"
                            ),
                            "action_taken": {"workflow_execution_id": wf_id},
                            "outcome": wf_status,
                        }
                    )

                else:
                    # Still running/pending — keep tracking
                    still_pending.append(pw)

            except Exception as e:
                logger.warning("Error checking workflow %s: %s", wf_id, e)
                still_pending.append(pw)  # Keep tracking on transient errors

        new_state["pending_workflows"] = still_pending
        return decisions

    # ------------------------------------------------------------------
    # Phase 4: Decision logging
    # ------------------------------------------------------------------

    async def _log_decision(
        self, dept_id: str | None, decision: dict[str, Any]
    ) -> None:
        """Insert a record into department_decision_logs."""
        if not dept_id:
            return

        row = {
            "department_id": dept_id,
            "cycle_timestamp": datetime.now(timezone.utc).isoformat(),
            "decision_type": decision.get("decision_type", "unknown"),
            "decision_logic": decision.get("decision_logic"),
            "action_taken": decision.get("action_taken"),
            "outcome": decision.get("outcome"),
        }
        trigger_id = decision.get("trigger_id")
        if trigger_id:
            row["trigger_id"] = trigger_id

        try:
            await execute_async(
                self.supabase.table("department_decision_logs").insert(row),
                op_name="department_runner.log_decision",
            )
        except Exception as e:
            logger.warning("Failed to log decision for dept %s: %s", dept_id, e)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _resolve_department_id(self, dept_type: str) -> str | None:
        """Look up a department UUID by its type (e.g. 'STRATEGIC')."""
        try:
            res = await execute_async(
                self.supabase.table("departments")
                .select("id")
                .eq("type", dept_type)
                .limit(1),
                op_name="department_runner.resolve_dept_id",
            )
            rows = res.data or []
            return rows[0]["id"] if rows else None
        except Exception as e:
            logger.warning("Failed to resolve department type %s: %s", dept_type, e)
            return None

    # ------------------------------------------------------------------
    # Per-department cycle methods — all delegate to _core_cycle
    # ------------------------------------------------------------------

    async def _run_sales_cycle(
        self, state: dict[str, Any], new_state: dict[str, Any]
    ) -> str:
        """Run autonomous cycle for the Sales department."""
        return await self._core_cycle("SALES", state, new_state)

    async def _run_marketing_cycle(
        self, state: dict[str, Any], new_state: dict[str, Any]
    ) -> str:
        """Run autonomous cycle for the Marketing department."""
        return await self._core_cycle("MARKETING", state, new_state)

    async def _run_content_cycle(
        self, state: dict[str, Any], new_state: dict[str, Any]
    ) -> str:
        """Run autonomous cycle for the Content department."""
        return await self._core_cycle("CONTENT", state, new_state)

    async def _run_strategic_cycle(
        self, state: dict[str, Any], new_state: dict[str, Any]
    ) -> str:
        """Run autonomous cycle for the Strategic department."""
        return await self._core_cycle("STRATEGIC", state, new_state)

    async def _run_data_cycle(
        self, state: dict[str, Any], new_state: dict[str, Any]
    ) -> str:
        """Run autonomous cycle for the Data department."""
        return await self._core_cycle("DATA", state, new_state)

    async def _run_financial_cycle(
        self, state: dict[str, Any], new_state: dict[str, Any]
    ) -> str:
        """Run autonomous cycle for the Financial department."""
        return await self._core_cycle("FINANCIAL", state, new_state)

    async def _run_support_cycle(
        self, state: dict[str, Any], new_state: dict[str, Any]
    ) -> str:
        """Run autonomous cycle for the Customer Support department."""
        return await self._core_cycle("SUPPORT", state, new_state)

    async def _run_hr_cycle(
        self, state: dict[str, Any], new_state: dict[str, Any]
    ) -> str:
        """Run autonomous cycle for the HR department."""
        return await self._core_cycle("HR", state, new_state)

    async def _run_compliance_cycle(
        self, state: dict[str, Any], new_state: dict[str, Any]
    ) -> str:
        """Run autonomous cycle for the Compliance department."""
        return await self._core_cycle("COMPLIANCE", state, new_state)

    async def _run_operations_cycle(
        self, state: dict[str, Any], new_state: dict[str, Any]
    ) -> str:
        """Run autonomous cycle for the Operations department."""
        return await self._core_cycle("OPERATIONS", state, new_state)


runner = DepartmentRunner()
