# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Workflow Engine.

Executes structured workflows defined in the database.
Handles phase transitions, step execution, and approval gates.
"""

import asyncio
import logging
import os
from copy import deepcopy
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
from datetime import datetime

from supabase import Client
from app.services.supabase import get_service_client
from app.services.edge_functions import edge_function_client
from app.workflows.template_seed_fallback import (
    seed_template_metadata as _seed_template_metadata,
)
from app.workflows.template_validation import validate_template_phases

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

class WorkflowEngine:
    def __init__(self):
        self.client = self._get_supabase()

    def _get_supabase(self) -> Client:
        return get_service_client()

    async def list_templates(
        self,
        category: Optional[str] = None,
        lifecycle_status: Optional[str] = None,
        persona: Optional[str] = None,
    ) -> List[Dict]:
        """List available workflow templates."""
        # Prefer lifecycle-aware schema (migration 0051), but gracefully fall back
        # to legacy schema or seed metadata so template listing remains available.
        try:
            start_time = datetime.now()
            logger.info(f"Starting list_templates query at {start_time}")
            
            query = self.client.table("workflow_templates").select(
                "id, name, description, category, template_key, version, lifecycle_status, is_generated, personas_allowed, published_at"
            )
            if category:
                query = query.eq("category", category)
            if lifecycle_status:
                query = query.eq("lifecycle_status", lifecycle_status)
            if persona:
                # Supabase JSONB containment filter
                query = query.contains("personas_allowed", [persona])
            
            # Avoid hanging UI on remote DB latency.
            logger.info("Executing DB query with 3.0s timeout...")
            res = await asyncio.wait_for(asyncio.to_thread(query.execute), timeout=3.0)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"DB query success in {duration:.3f}s")
            return res.data
        except asyncio.TimeoutError:
            duration = (datetime.now() - start_time).total_seconds()
            logger.warning(f"Main template query timed out after {duration:.3f}s; skipping legacy check and falling back to seeds immediately")
            
            fallback_start = datetime.now()
            seeded = _seed_template_metadata()
            if category:
                seeded = [t for t in seeded if str(t.get("category", "")).lower() == category.lower()]
            
            fallback_duration = (datetime.now() - fallback_start).total_seconds()
            logger.info(f"Fallback to seeds took {fallback_duration:.3f}s")
            return seeded
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            msg = str(e)
            logger.error(f"Template query failed after {duration:.3f}s with error: {msg}")
            
            # Only try legacy query if we know it's a schema issue (missing columns)
            if "column workflow_templates.template_key does not exist" in msg:
                logger.warning("workflow_templates lifecycle columns missing; using legacy template listing fallback")
                try:
                    query = self.client.table("workflow_templates").select("id, name, description, category")
                    if category:
                        query = query.eq("category", category)
                    legacy = await asyncio.wait_for(asyncio.to_thread(query.execute), timeout=3.0)
                    out: List[Dict[str, Any]] = []
                    for row in legacy.data:
                        row["template_key"] = None
                        row["version"] = None
                        row["lifecycle_status"] = None
                        row["is_generated"] = None
                        row["personas_allowed"] = None
                        row["published_at"] = None
                        out.append(row)
                    return out
                except Exception:
                    logger.warning("legacy DB listing failed; falling back to seed metadata")
            else:
                logger.warning(f"template listing query failed ({type(e).__name__}); falling back to seed metadata: {e}")

            seeded = _seed_template_metadata()
            if category:
                seeded = [t for t in seeded if str(t.get("category", "")).lower() == category.lower()]
            return seeded

    async def get_template(self, template_id: str) -> Dict[str, Any]:
        """Get one workflow template by ID."""
        res = self.client.table("workflow_templates").select("*").eq("id", template_id).limit(1).execute()
        if not res.data:
            return {"error": "Template not found"}
        return res.data[0]

    async def create_template(
        self,
        *,
        user_id: str,
        name: str,
        description: str,
        category: str,
        phases: List[Dict[str, Any]],
        template_key: Optional[str] = None,
        personas_allowed: Optional[List[str]] = None,
        is_generated: bool = False,
    ) -> Dict[str, Any]:
        """Create a new draft template."""
        from app.agents.tools.registry import TOOL_REGISTRY

        validation_errors = validate_template_phases(phases, set(TOOL_REGISTRY.keys()))
        if validation_errors:
            return {"error": "Invalid workflow template schema", "details": validation_errors}

        key = template_key or name.lower().replace(" ", "_")
        # Start at version 1; if key exists, increment.
        existing = self.client.table("workflow_templates").select("version").eq("template_key", key).order(
            "version", desc=True
        ).limit(1).execute()
        next_version = (existing.data[0]["version"] + 1) if existing.data else 1

        row = {
            "name": name,
            "description": description,
            "category": category,
            "phases": phases,
            "template_key": key,
            "version": next_version,
            "lifecycle_status": "draft",
            "is_generated": is_generated,
            "personas_allowed": personas_allowed or [],
            "created_by": user_id,
        }
        inserted = self.client.table("workflow_templates").insert(row).execute()
        template = inserted.data[0]
        await self._audit_template_action(template, "create_draft", user_id=user_id, metadata={"is_generated": is_generated})
        return template

    async def update_template_draft(
        self,
        *,
        template_id: str,
        user_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update editable fields on a draft template."""
        current = await self.get_template(template_id)
        if "error" in current:
            return current
        if current.get("created_by") and current.get("created_by") != user_id:
            return {"error": "Only the template owner can edit this draft"}
        if current.get("lifecycle_status") != "draft":
            return {"error": "Only draft templates can be edited"}

        allowed_fields = {"name", "description", "category", "phases", "personas_allowed"}
        patch = {k: v for k, v in updates.items() if k in allowed_fields}
        if "phases" in patch:
            from app.agents.tools.registry import TOOL_REGISTRY

            validation_errors = validate_template_phases(patch["phases"], set(TOOL_REGISTRY.keys()))
            if validation_errors:
                return {"error": "Invalid workflow template schema", "details": validation_errors}
        if not patch:
            return current
        updated = self.client.table("workflow_templates").update(patch).eq("id", template_id).execute()
        result = updated.data[0]
        await self._audit_template_action(result, "update_draft", user_id=user_id, metadata={"fields": sorted(patch.keys())})
        return result

    async def clone_template(
        self,
        *,
        template_id: str,
        user_id: str,
        new_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Clone template into a new draft version with same template_key."""
        src = await self.get_template(template_id)
        if "error" in src:
            return src
        if src.get("created_by") and src.get("created_by") != user_id:
            return {"error": "Only the template owner can clone this draft"}
        clone_name = new_name or f"{src['name']} (Draft)"
        return await self.create_template(
            user_id=user_id,
            name=clone_name,
            description=src.get("description", ""),
            category=src.get("category", "operations"),
            phases=deepcopy(src.get("phases", [])),
            template_key=src.get("template_key"),
            personas_allowed=deepcopy(src.get("personas_allowed") or []),
            is_generated=bool(src.get("is_generated")),
        )

    async def publish_template(self, *, template_id: str, user_id: str) -> Dict[str, Any]:
        """Publish draft template after workflow validation checks."""
        from app.agents.tools.registry import TOOL_REGISTRY

        tmpl = await self.get_template(template_id)
        if "error" in tmpl:
            return tmpl
        if tmpl.get("created_by") and tmpl.get("created_by") != user_id:
            return {"error": "Only the template owner can publish this draft"}
        if tmpl.get("lifecycle_status") != "draft":
            return {"error": "Only draft templates can be published"}

        # Guardrail: validate this template payload before allowing publish.
        errors = validate_template_phases(tmpl.get("phases") or [], set(TOOL_REGISTRY.keys()))
        if errors:
            return {"error": "Workflow template validation failed", "details": errors[:20]}

        updated = self.client.table("workflow_templates").update(
            {
                "lifecycle_status": "published",
                "published_by": user_id,
                "published_at": datetime.now().isoformat(),
            }
        ).eq("id", template_id).execute()
        result = updated.data[0]
        await self._audit_template_action(result, "publish", user_id=user_id, metadata={})
        return result

    async def archive_template(self, *, template_id: str, user_id: str) -> Dict[str, Any]:
        """Archive template."""
        tmpl = await self.get_template(template_id)
        if "error" in tmpl:
            return tmpl
        if tmpl.get("created_by") and tmpl.get("created_by") != user_id:
            return {"error": "Only the template owner can archive this template"}
        updated = self.client.table("workflow_templates").update({"lifecycle_status": "archived"}).eq("id", template_id).execute()
        result = updated.data[0]
        await self._audit_template_action(result, "archive", user_id=user_id, metadata={})
        return result

    async def list_template_versions(self, template_id: str) -> List[Dict[str, Any]]:
        """List all versions for template key of template_id."""
        tmpl = await self.get_template(template_id)
        if "error" in tmpl:
            return []
        key = tmpl["template_key"]
        res = self.client.table("workflow_templates").select("*").eq("template_key", key).order("version", desc=True).execute()
        return res.data

    async def diff_template(self, *, template_id: str, against: str = "published") -> Dict[str, Any]:
        """Compute shallow template diff for phases/metadata."""
        base = await self.get_template(template_id)
        if "error" in base:
            return base

        if against != "published":
            return {"error": "Unsupported diff target"}

        published = (
            self.client.table("workflow_templates")
            .select("*")
            .eq("template_key", base["template_key"])
            .eq("lifecycle_status", "published")
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        if not published.data:
            return {"template": base, "against": None, "diff": {"notes": ["No published version found"]}}
        target = published.data[0]

        diff: Dict[str, Any] = {"changed_fields": [], "phase_count": {}, "step_count": {}}
        for field in ("name", "description", "category", "personas_allowed"):
            if base.get(field) != target.get(field):
                diff["changed_fields"].append(field)

        base_phases = base.get("phases") or []
        target_phases = target.get("phases") or []
        diff["phase_count"] = {"current": len(base_phases), "against": len(target_phases)}
        diff["step_count"] = {
            "current": sum(len(p.get("steps", [])) for p in base_phases),
            "against": sum(len(p.get("steps", [])) for p in target_phases),
        }
        return {"template": base, "against": target, "diff": diff}

    def _is_readiness_gate_enabled(self) -> bool:
        """Whether workflow starts should enforce readiness status checks."""
        return _as_bool(os.getenv("WORKFLOW_ENFORCE_READINESS_GATE"), default=True)

    def _is_user_visible_run_source(self, run_source: str) -> bool:
        """Whether the start request is from a real user-facing surface."""
        normalized = (run_source or "").strip().lower()
        return normalized in {"user_ui", "agent_ui"}

    def _get_execution_infra_guard_error(self, *, run_source: str) -> Optional[Dict[str, Any]]:
        """Validate callback-path config before creating user-visible executions.

        The edge-function execution path requires backend callback auth when strict execution mode
        is active (which is the default when fallback simulation is disabled). Without these env
        vars, executions can be created and remain stuck in `pending` with no actionable error.
        """
        if not self._is_user_visible_run_source(run_source):
            return None

        strict_tool_resolution = _as_bool(os.getenv("WORKFLOW_STRICT_TOOL_RESOLUTION"), default=False)
        allow_fallback_simulation = _as_bool(os.getenv("WORKFLOW_ALLOW_FALLBACK_SIMULATION"), default=False)
        strict_execution_mode = strict_tool_resolution or not allow_fallback_simulation
        if not strict_execution_mode:
            return None

        backend_api_url = (os.getenv("BACKEND_API_URL") or "").strip()
        workflow_service_secret = (os.getenv("WORKFLOW_SERVICE_SECRET") or "").strip()

        missing_config: List[str] = []
        invalid_config: List[str] = []
        if not backend_api_url:
            missing_config.append("BACKEND_API_URL")
        else:
            try:
                parsed = urlparse(backend_api_url)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    invalid_config.append("BACKEND_API_URL")
            except Exception:
                invalid_config.append("BACKEND_API_URL")
        if not workflow_service_secret:
            missing_config.append("WORKFLOW_SERVICE_SECRET")

        if not missing_config and not invalid_config:
            return None

        details = []
        if missing_config:
            details.append(f"missing: {', '.join(missing_config)}")
        if invalid_config:
            details.append(f"invalid: {', '.join(invalid_config)}")
        detail_text = "; ".join(details)
        return {
            "error": (
                "Workflow execution infrastructure is not configured for strict execution mode "
                f"({detail_text}). Configure BACKEND_API_URL and WORKFLOW_SERVICE_SECRET, or "
                "explicitly allow fallback simulation for non-strict environments."
            ),
            "error_code": "workflow_execution_infra_not_configured",
            "missing_config": missing_config,
            "invalid_config": invalid_config,
            "strict_execution_mode": strict_execution_mode,
            "strict_tool_resolution": strict_tool_resolution,
            "allow_fallback_simulation": allow_fallback_simulation,
        }

    def _get_workflow_readiness(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Load readiness metadata for a workflow template."""
        template_id = template.get("id")
        if not template_id:
            return {"error": "Template missing id for readiness lookup"}

        try:
            res = (
                self.client.table("workflow_readiness")
                .select(
                    "template_id, template_name, template_version, status, "
                    "required_integrations, requires_human_gate, readiness_owner, "
                    "reason_codes, notes, updated_at"
                )
                .eq("template_id", template_id)
                .limit(1)
                .execute()
            )
            if not res.data:
                return {"error": "No readiness record found for template"}
            return res.data[0]
        except Exception as exc:
            return {"error": str(exc)}

    async def start_workflow(
        self,
        user_id: str,
        template_name: Optional[str] = None,
        template_id: Optional[str] = None,
        template_version: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        run_source: str = "user_ui",
    ) -> Dict[str, Any]:
        """Start a new workflow execution from a template."""
        context = context or {}

        # 1. Get Template
        query = self.client.table("workflow_templates").select("*")
        if template_id:
            query = query.eq("id", template_id)
        elif template_name:
            query = query.eq("name", template_name)
        else:
            return {"error": "template_id or template_name is required", "error_code": "validation_error"}
        if template_version is not None:
            query = query.eq("version", template_version)
        res = query.limit(1).execute()
        if not res.data:
            label = template_id or template_name or "unknown"
            return {"error": f"Template '{label}' not found", "error_code": "template_not_found"}

        template = res.data[0]
        phases = template["phases"]  # JSONB
        lifecycle_status = str(template.get("lifecycle_status") or "").strip().lower()
        if lifecycle_status == "archived":
            return {"error": "Template is archived and cannot be started", "error_code": "template_archived"}

        if self._is_user_visible_run_source(run_source) and lifecycle_status != "published":
            status_label = lifecycle_status or "unknown"
            return {
                "error": (
                    f"Template '{template.get('name')}' is not published for real-user starts "
                    f"(lifecycle_status={status_label})"
                ),
                "error_code": "template_not_published",
                "lifecycle_status": status_label,
            }

        # 1b. Readiness gate (when enabled, non-ready templates are blocked).
        readiness = self._get_workflow_readiness(template)
        gate_enabled = self._is_readiness_gate_enabled()
        if "error" in readiness:
            logger.warning(
                "Workflow readiness lookup failed for template '%s': %s",
                template.get("name"),
                readiness["error"],
            )
            if gate_enabled:
                return {
                    "error": f"Workflow readiness check failed: {readiness['error']}",
                    "error_code": "workflow_readiness_unavailable",
                }
        else:
            readiness_status = readiness.get("status")
            if readiness_status != "ready":
                reason_codes = readiness.get("reason_codes") or []
                reason_text = ""
                if isinstance(reason_codes, list) and reason_codes:
                    reason_text = f" Reasons: {', '.join(str(r) for r in reason_codes)}."
                message = (
                    f"Workflow '{template.get('name')}' is not ready for execution "
                    f"(status={readiness_status}).{reason_text}"
                )
                if gate_enabled:
                    return {
                        "error": message,
                        "error_code": "workflow_not_ready",
                        "readiness": readiness,
                    }
                logger.warning("Readiness gate disabled; allowing start for non-ready workflow: %s", message)

        infra_guard_error = self._get_execution_infra_guard_error(run_source=run_source)
        if infra_guard_error:
            logger.warning(
                "Blocking workflow start for template '%s' due to execution infra config: %s",
                template.get("name"),
                infra_guard_error.get("error"),
            )
            return infra_guard_error

        # 2. Create execution in pending state.
        # The edge function owns first-step creation and progression.
        execution_data = {
            "user_id": user_id,
            "template_id": template["id"],
            "template_version": template.get("version"),
            "started_by": user_id,
            "run_source": run_source,
            "name": f"{template['name']} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "status": "pending",
            "current_phase_index": 0,
            "current_step_index": 0,
            "context": context,
        }
        res_exec = self.client.table("workflow_executions").insert(execution_data).execute()
        execution_id = res_exec.data[0]["id"]

        # 3. Trigger edge orchestration; edge handles first-step insertion idempotently.
        asyncio.create_task(edge_function_client.execute_workflow(execution_id, action="start"))

        first_phase = phases[0] if phases else {"name": "Workflow", "steps": [{"name": "Starting"}]}
        first_step = first_phase.get("steps", [{}])[0]
        step_desc = first_step.get("description") or first_step.get("name") or "Next step"
        return {
            "execution_id": execution_id,
            "status": "pending",
            "current_step": f"{first_phase.get('name', 'Workflow')}: {first_step.get('name', 'Starting')}",
            "message": f"Workflow queued. Orchestration triggered. Next step: {step_desc}",
        }

    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get full status of an execution."""
        res_exec = self.client.table("workflow_executions").select("*, workflow_templates(name, phases)").eq("id", execution_id).execute()
        if not res_exec.data:
            return {"error": "Execution not found"}
            
        execution = res_exec.data[0]
        template = execution['workflow_templates']
        
        # Get history with stable fields for API/UX consumers.
        res_steps = self.client.table("workflow_steps").select("*").eq("execution_id", execution_id).order("started_at").execute()
        history: List[Dict[str, Any]] = []
        for step in res_steps.data or []:
            history.append(
                {
                    "id": step.get("id"),
                    "execution_id": step.get("execution_id"),
                    "phase_name": step.get("phase_name"),
                    "step_name": step.get("step_name"),
                    "status": step.get("status"),
                    "input_data": step.get("input_data"),
                    "output_data": step.get("output_data"),
                    "error_message": step.get("error_message"),
                    "started_at": step.get("started_at"),
                    "completed_at": step.get("completed_at"),
                    "created_at": step.get("created_at"),
                    "updated_at": step.get("updated_at"),
                    "phase_index": step.get("phase_index"),
                    "step_index": step.get("step_index"),
                    "attempt_count": step.get("attempt_count"),
                    "phase_key": step.get("phase_key"),
                }
            )

        return {
            "execution": execution,
            "template_name": template['name'],
            "history": history,
            "current_phase_index": execution['current_phase_index'],
            "current_step_index": execution['current_step_index']
        }

    async def list_executions(self, user_id: str, status: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """List workflow executions for a user."""
        query = self.client.table("workflow_executions")\
            .select("*, workflow_templates(name)")\
            .eq("user_id", user_id)
            
        if status:
            query = query.eq("status", status)
            
        res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        # Flatten template name for easier consumption if needed, 
        # or just return as is matching the join structure.
        # The router expects a list of dicts.
        executions = []
        for exc in res.data:
            exc["template_name"] = exc["workflow_templates"]["name"] if exc.get("workflow_templates") else "Unknown"
            executions.append(exc)
            
        return executions

    async def cancel_execution(self, *, execution_id: str, user_id: str, reason: str = "") -> Dict[str, Any]:
        """Cancel running workflow execution."""
        current = await self.get_execution_status(execution_id)
        if "error" in current:
            return current
        execution = current["execution"]
        if execution.get("user_id") != user_id:
            return {"error": "Unauthorized"}
        if execution.get("status") in ("completed", "failed", "cancelled"):
            return {"error": f"Cannot cancel execution in status {execution.get('status')}"}

        updated = self.client.table("workflow_executions").update(
            {
                "status": "cancelled",
                "cancelled_at": datetime.now().isoformat(),
                "cancel_reason": reason or "Cancelled by user",
                "completed_at": datetime.now().isoformat(),
            }
        ).eq("id", execution_id).execute()
        await self._audit_execution_action(
            execution_id=execution_id,
            user_id=user_id,
            action="cancel",
            metadata={"reason": reason or "Cancelled by user"},
        )
        return {"status": "cancelled", "execution": updated.data[0]}

    async def advance_execution(self, *, execution_id: str, user_id: str) -> Dict[str, Any]:
        """Advance workflow execution to the next step via edge orchestration."""
        current = await self.get_execution_status(execution_id)
        if "error" in current:
            return current
        execution = current["execution"]
        if execution.get("user_id") != user_id:
            return {"error": "Unauthorized"}
        if execution.get("status") in ("completed", "failed", "cancelled"):
            return {"error": f"Cannot advance execution in status {execution.get('status')}"}

        await self._audit_execution_action(
            execution_id=execution_id,
            user_id=user_id,
            action="advance",
            metadata={"from_status": execution.get("status")},
        )
        asyncio.create_task(edge_function_client.execute_workflow(execution_id, action="advance"))
        return {"status": "advance_triggered", "execution_id": execution_id}

    async def retry_step(self, *, execution_id: str, step_id: str, user_id: str) -> Dict[str, Any]:
        """Retry failed/skipped step by creating another attempt record."""
        current = await self.get_execution_status(execution_id)
        if "error" in current:
            return current
        execution = current["execution"]
        if execution.get("user_id") != user_id:
            return {"error": "Unauthorized"}

        step_res = self.client.table("workflow_steps").select("*").eq("id", step_id).eq("execution_id", execution_id).limit(1).execute()
        if not step_res.data:
            return {"error": "Step not found"}
        step = step_res.data[0]
        if step.get("status") not in ("failed", "skipped"):
            return {"error": f"Step status must be failed or skipped, got {step.get('status')}"}

        attempt = (step.get("attempt_count") or 1) + 1
        updated = self.client.table("workflow_steps").update(
            {
                "status": "running",
                "attempt_count": attempt,
                "error_message": None,
                "completed_at": None,
                "started_at": datetime.now().isoformat(),
                "idempotency_key": f"{execution_id}:{step.get('phase_index', 0)}:{step.get('step_index', 0)}:{attempt}",
            }
        ).eq("id", step_id).execute()
        await self._audit_execution_action(
            execution_id=execution_id,
            user_id=user_id,
            action="retry_step",
            metadata={"step_id": step_id, "attempt_count": attempt},
        )
        asyncio.create_task(edge_function_client.execute_workflow(execution_id, action="retry"))
        return {"status": "retry_started", "step": updated.data[0]}

    async def _audit_template_action(
        self,
        template: Dict[str, Any],
        action: str,
        *,
        user_id: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Best-effort audit write."""
        try:
            self.client.table("workflow_template_audit").insert(
                {
                    "template_id": template["id"],
                    "template_key": template.get("template_key", ""),
                    "version": template.get("version", 1),
                    "action": action,
                    "actor_user_id": user_id,
                    "metadata": metadata,
                }
            ).execute()
        except Exception as e:
            logger.warning(f"Template audit write failed: {e}")

    async def _audit_execution_action(
        self,
        *,
        execution_id: str,
        user_id: str,
        action: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Best-effort execution audit write."""
        try:
            self.client.table("workflow_execution_audit").insert(
                {
                    "execution_id": execution_id,
                    "actor_user_id": user_id,
                    "action": action,
                    "metadata": metadata,
                }
            ).execute()
        except Exception as e:
            logger.warning(f"Execution audit write failed: {e}")

    async def approve_step(
        self,
        execution_id: str,
        step_message: str = "Approved by user",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Approve the current step if it is waiting for approval."""
        status = await self.get_execution_status(execution_id)
        if "error" in status:
            return status

        execution = status["execution"]
        if user_id and execution.get("user_id") != user_id:
            return {"error": "Unauthorized"}

        # Find current active step
        res_step = self.client.table("workflow_steps").select("*")\
            .eq("execution_id", execution_id)\
            .eq("status", "waiting_approval")\
            .order("created_at", desc=True)\
            .limit(1).execute()
            
        if not res_step.data:
            return {"error": "No step is currently waiting for approval"}
            
        step = res_step.data[0]
        
        # Mark completed
        self.client.table("workflow_steps").update({
            "status": "completed",
            "output_data": {"approval_message": step_message},
            "completed_at": datetime.now().isoformat()
        }).eq("id", step["id"]).execute()
        
        # Advance to next step
        # Trigger the workflow execution to proceed
        asyncio.create_task(edge_function_client.execute_workflow(execution_id, action="advance"))
        
        return {
            "status": "approved", 
            "message": "Step approved. Workflow execution continuing in background."
        }

    async def _advance_workflow(self, execution: Dict, phases: List[Dict]) -> Dict[str, Any]:
        """Move to the next step using Edge Function.
        
        Deprecated: Logic is now handled by 'execute-workflow' Edge Function.
        This method is kept for manual invocation compatibility if needed, 
        but should ideally delegate to the EF.
        """
        await edge_function_client.execute_workflow(execution["id"], action="advance")
        return {"status": "processing", "message": "Workflow advancement triggered"}

# Singleton
_engine = None
def get_workflow_engine():
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
