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
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from app.personas.runtime import (
    filter_workflow_templates_for_persona,
    normalize_allowed_personas,
    resolve_effective_persona,
    workflow_template_has_explicit_persona_scope,
    workflow_template_matches_persona,
)
from app.services.edge_functions import edge_function_client
from app.services.supabase import get_service_client
from app.workflows.contract_defaults import enrich_template_phases_for_execution
from app.workflows.execution_contracts import (
    determine_trust_class,
    extract_evidence_refs,
)
from app.workflows.template_seed_fallback import (
    seed_template_metadata as _seed_template_metadata,
)
from app.workflows.template_validation import validate_template_phases
from supabase import Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Maximum concurrent workflow executions per user.
# Active = status in (pending, running, paused, waiting_approval).
MAX_CONCURRENT_EXECUTIONS_PER_USER = int(
    os.getenv("WORKFLOW_MAX_CONCURRENT_PER_USER", "3")
)


class WorkflowEngine:
    def __init__(self):
        self.client = self._get_supabase()

    def _get_supabase(self) -> Client:
        return get_service_client()

    def _get_persona_enforcement_mode(self) -> str:
        mode = (
            (os.getenv("WORKFLOW_PERSONA_ENFORCEMENT_MODE") or "enforce")
            .strip()
            .lower()
        )
        if mode in {"log", "warn", "advisory"}:
            return "log"
        return "enforce"

    async def _resolve_workflow_persona(
        self, *, user_id: str, persona: str | None
    ) -> str | None:
        return await resolve_effective_persona(persona=persona, user_id=user_id)

    def _should_block_workflow_start_for_persona(
        self,
        *,
        template: dict[str, Any],
        persona: str | None,
        run_source: str,
    ) -> dict[str, Any] | None:
        if not self._is_user_visible_run_source(run_source):
            return None

        normalized_persona = str(persona).strip().lower() if persona else None
        allowed_personas = list(
            normalize_allowed_personas(template.get("personas_allowed"))
        )
        if not normalized_persona or not allowed_personas:
            return None
        if workflow_template_matches_persona(allowed_personas, normalized_persona):
            return None

        detail = {
            "error": f"Workflow '{template.get('name')}' is not available for persona '{normalized_persona}'.",
            "error_code": "workflow_persona_not_allowed",
            "reason_code": "persona_not_allowed",
            "persona": normalized_persona,
            "personas_allowed": allowed_personas,
        }
        if self._get_persona_enforcement_mode() == "log":
            logger.warning(
                "Allowing workflow start despite persona mismatch (mode=log): template=%s persona=%s allowed=%s",
                template.get("name"),
                normalized_persona,
                allowed_personas,
            )
            return None
        return detail

    async def list_templates(
        self,
        category: str | None = None,
        lifecycle_status: str | None = None,
        persona: str | None = None,
    ) -> list[dict]:
        """List available workflow templates."""

        def _apply_persona_filter(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
            filtered_rows = rows
            if category:
                filtered_rows = [
                    row
                    for row in filtered_rows
                    if str(row.get("category", "")).strip().lower() == category.lower()
                ]
            if lifecycle_status:
                filtered_rows = [
                    row
                    for row in filtered_rows
                    if str(row.get("lifecycle_status") or "").strip().lower()
                    == lifecycle_status.lower()
                ]
            return filter_workflow_templates_for_persona(filtered_rows, persona)

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

            logger.info("Executing DB query with 3.0s timeout...")
            res = await asyncio.wait_for(asyncio.to_thread(query.execute), timeout=3.0)

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"DB query success in {duration:.3f}s")
            return _apply_persona_filter(res.data or [])
        except asyncio.TimeoutError:
            duration = (datetime.now() - start_time).total_seconds()
            logger.warning(
                f"Main template query timed out after {duration:.3f}s; skipping legacy check and falling back to seeds immediately"
            )

            fallback_start = datetime.now()
            seeded = _apply_persona_filter(_seed_template_metadata())

            fallback_duration = (datetime.now() - fallback_start).total_seconds()
            logger.info(f"Fallback to seeds took {fallback_duration:.3f}s")
            return seeded
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            msg = str(e)
            logger.error(
                f"Template query failed after {duration:.3f}s with error: {msg}"
            )

            if "column workflow_templates.template_key does not exist" in msg:
                logger.warning(
                    "workflow_templates lifecycle columns missing; using legacy template listing fallback"
                )
                try:
                    query = self.client.table("workflow_templates").select(
                        "id, name, description, category"
                    )
                    if category:
                        query = query.eq("category", category)
                    legacy = await asyncio.wait_for(
                        asyncio.to_thread(query.execute), timeout=3.0
                    )
                    out: list[dict[str, Any]] = []
                    for row in legacy.data:
                        row["template_key"] = None
                        row["version"] = None
                        row["lifecycle_status"] = None
                        row["is_generated"] = None
                        row["personas_allowed"] = None
                        row["published_at"] = None
                        out.append(row)
                    return _apply_persona_filter(out)
                except Exception:
                    logger.warning(
                        "legacy DB listing failed; falling back to seed metadata"
                    )
            else:
                logger.warning(
                    f"template listing query failed ({type(e).__name__}); falling back to seed metadata: {e}"
                )

            return _apply_persona_filter(_seed_template_metadata())

    async def get_template(self, template_id: str) -> dict[str, Any]:
        """Get one workflow template by ID."""
        res = (
            self.client.table("workflow_templates")
            .select("*")
            .eq("id", template_id)
            .limit(1)
            .execute()
        )
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
        phases: list[dict[str, Any]],
        template_key: str | None = None,
        personas_allowed: list[str] | None = None,
        is_generated: bool = False,
        default_persona: str | None = None,
    ) -> dict[str, Any]:
        """Create a new draft template."""
        from app.agents.tools.registry import TOOL_REGISTRY

        normalized_phases = enrich_template_phases_for_execution(
            phases,
            template_name=name,
            category=category,
            persona=default_persona,
            goal=description or name,
            tool_registry=TOOL_REGISTRY,
        )
        validation_errors = validate_template_phases(
            normalized_phases, set(TOOL_REGISTRY.keys())
        )
        if validation_errors:
            return {
                "error": "Invalid workflow template schema",
                "details": validation_errors,
            }

        key = template_key or name.lower().replace(" ", "_")
        # Start at version 1; if key exists, increment.
        existing = (
            self.client.table("workflow_templates")
            .select("version")
            .eq("template_key", key)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        next_version = (existing.data[0]["version"] + 1) if existing.data else 1

        effective_personas_allowed = list(normalize_allowed_personas(personas_allowed))
        if personas_allowed is None and default_persona:
            effective_personas_allowed = list(
                normalize_allowed_personas([default_persona])
            )

        row = {
            "name": name,
            "description": description,
            "category": category,
            "phases": normalized_phases,
            "template_key": key,
            "version": next_version,
            "lifecycle_status": "draft",
            "is_generated": is_generated,
            "personas_allowed": effective_personas_allowed,
            "created_by": user_id,
        }
        inserted = self.client.table("workflow_templates").insert(row).execute()
        template = inserted.data[0]
        await self._audit_template_action(
            template,
            "create_draft",
            user_id=user_id,
            metadata={"is_generated": is_generated},
        )
        return template

    async def update_template_draft(
        self,
        *,
        template_id: str,
        user_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update editable fields on a draft template."""
        current = await self.get_template(template_id)
        if "error" in current:
            return current
        if current.get("created_by") and current.get("created_by") != user_id:
            return {"error": "Only the template owner can edit this draft"}
        if current.get("lifecycle_status") != "draft":
            return {"error": "Only draft templates can be edited"}

        allowed_fields = {
            "name",
            "description",
            "category",
            "phases",
            "personas_allowed",
        }
        patch = {k: v for k, v in updates.items() if k in allowed_fields}
        if "phases" in patch:
            from app.agents.tools.registry import TOOL_REGISTRY

            patch["phases"] = enrich_template_phases_for_execution(
                patch["phases"],
                template_name=str(
                    patch.get("name") or current.get("name") or "Workflow Draft"
                ),
                category=str(
                    patch.get("category") or current.get("category") or "operations"
                ),
                persona=None,
                goal=str(
                    patch.get("description")
                    or current.get("description")
                    or patch.get("name")
                    or current.get("name")
                    or "Workflow draft"
                ),
                tool_registry=TOOL_REGISTRY,
            )
            validation_errors = validate_template_phases(
                patch["phases"], set(TOOL_REGISTRY.keys())
            )
            if validation_errors:
                return {
                    "error": "Invalid workflow template schema",
                    "details": validation_errors,
                }
        if not patch:
            return current
        updated = (
            self.client.table("workflow_templates")
            .update(patch)
            .eq("id", template_id)
            .execute()
        )
        result = updated.data[0]
        await self._audit_template_action(
            result,
            "update_draft",
            user_id=user_id,
            metadata={"fields": sorted(patch.keys())},
        )
        return result

    async def clone_template(
        self,
        *,
        template_id: str,
        user_id: str,
        new_name: str | None = None,
    ) -> dict[str, Any]:
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

    async def publish_template(
        self, *, template_id: str, user_id: str
    ) -> dict[str, Any]:
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
        errors = validate_template_phases(
            tmpl.get("phases") or [], set(TOOL_REGISTRY.keys())
        )
        if errors:
            return {
                "error": "Workflow template validation failed",
                "details": errors[:20],
            }
        if not workflow_template_has_explicit_persona_scope(
            tmpl.get("personas_allowed")
        ):
            return {
                "error": "Workflow template must define personas_allowed before publish",
                "details": [
                    "Set personas_allowed to one or more personas, or use ['all'] for intentional shared templates."
                ],
            }

        updated = (
            self.client.table("workflow_templates")
            .update(
                {
                    "lifecycle_status": "published",
                    "published_by": user_id,
                    "published_at": datetime.now().isoformat(),
                }
            )
            .eq("id", template_id)
            .execute()
        )
        result = updated.data[0]
        await self._audit_template_action(
            result, "publish", user_id=user_id, metadata={}
        )
        return result

    async def archive_template(
        self, *, template_id: str, user_id: str
    ) -> dict[str, Any]:
        """Archive template."""
        tmpl = await self.get_template(template_id)
        if "error" in tmpl:
            return tmpl
        if tmpl.get("created_by") and tmpl.get("created_by") != user_id:
            return {"error": "Only the template owner can archive this template"}
        updated = (
            self.client.table("workflow_templates")
            .update({"lifecycle_status": "archived"})
            .eq("id", template_id)
            .execute()
        )
        result = updated.data[0]
        await self._audit_template_action(
            result, "archive", user_id=user_id, metadata={}
        )
        return result

    async def list_template_versions(self, template_id: str) -> list[dict[str, Any]]:
        """List all versions for template key of template_id."""
        tmpl = await self.get_template(template_id)
        if "error" in tmpl:
            return []
        key = tmpl["template_key"]
        res = (
            self.client.table("workflow_templates")
            .select("*")
            .eq("template_key", key)
            .order("version", desc=True)
            .execute()
        )
        return res.data

    async def diff_template(
        self, *, template_id: str, against: str = "published"
    ) -> dict[str, Any]:
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
            return {
                "template": base,
                "against": None,
                "diff": {"notes": ["No published version found"]},
            }
        target = published.data[0]

        diff: dict[str, Any] = {
            "changed_fields": [],
            "phase_count": {},
            "step_count": {},
        }
        for field in ("name", "description", "category", "personas_allowed"):
            if base.get(field) != target.get(field):
                diff["changed_fields"].append(field)

        base_phases = base.get("phases") or []
        target_phases = target.get("phases") or []
        diff["phase_count"] = {
            "current": len(base_phases),
            "against": len(target_phases),
        }
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

    def _get_execution_infra_guard_error(
        self, *, run_source: str
    ) -> dict[str, Any] | None:
        """Validate callback-path config before creating user-visible executions.

        The edge-function execution path requires backend callback auth when strict execution mode
        is active (which is the default when fallback simulation is disabled). Without these env
        vars, executions can be created and remain stuck in `pending` with no actionable error.
        """
        if not self._is_user_visible_run_source(run_source):
            return None

        strict_tool_resolution = _as_bool(
            os.getenv("WORKFLOW_STRICT_TOOL_RESOLUTION"), default=False
        )
        allow_fallback_simulation = _as_bool(
            os.getenv("WORKFLOW_ALLOW_FALLBACK_SIMULATION"), default=False
        )
        strict_execution_mode = strict_tool_resolution or not allow_fallback_simulation
        if not strict_execution_mode:
            return None

        backend_api_url = (os.getenv("BACKEND_API_URL") or "").strip()
        workflow_service_secret = (os.getenv("WORKFLOW_SERVICE_SECRET") or "").strip()

        missing_config: list[str] = []
        invalid_config: list[str] = []
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

    def _get_workflow_readiness(self, template: dict[str, Any]) -> dict[str, Any]:
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
        template_name: str | None = None,
        template_id: str | None = None,
        template_version: int | None = None,
        context: dict[str, Any] | None = None,
        run_source: str = "user_ui",
        persona: str | None = None,
    ) -> dict[str, Any]:
        """Start a new workflow execution from a template."""
        context = context or {}

        # 1. Get Template
        query = self.client.table("workflow_templates").select("*")
        if template_id:
            query = query.eq("id", template_id)
        elif template_name:
            query = query.eq("name", template_name)
        else:
            return {
                "error": "template_id or template_name is required",
                "error_code": "validation_error",
            }
        if template_version is not None:
            query = query.eq("version", template_version)
        res = query.limit(1).execute()
        if not res.data:
            label = template_id or template_name or "unknown"
            return {
                "error": f"Template '{label}' not found",
                "error_code": "template_not_found",
            }

        template = res.data[0]
        phases = template["phases"]  # JSONB
        lifecycle_status = str(template.get("lifecycle_status") or "").strip().lower()
        if lifecycle_status == "archived":
            return {
                "error": "Template is archived and cannot be started",
                "error_code": "template_archived",
            }

        if (
            self._is_user_visible_run_source(run_source)
            and lifecycle_status != "published"
        ):
            status_label = lifecycle_status or "unknown"
            return {
                "error": (
                    f"Template '{template.get('name')}' is not published for real-user starts "
                    f"(lifecycle_status={status_label})"
                ),
                "error_code": "template_not_published",
                "lifecycle_status": status_label,
            }

        effective_persona = await self._resolve_workflow_persona(
            user_id=user_id, persona=persona
        )
        persona_block = self._should_block_workflow_start_for_persona(
            template=template,
            persona=effective_persona,
            run_source=run_source,
        )
        if persona_block:
            return persona_block

        if self._is_user_visible_run_source(run_source):
            from app.agents.tools.registry import TOOL_REGISTRY

            contract_errors = validate_template_phases(
                phases,
                set(TOOL_REGISTRY.keys()),
                strict_user_visible=True,
                tool_registry=TOOL_REGISTRY,
            )
            if contract_errors:
                reason_codes = sorted(
                    {
                        "unknown_tool"
                        if "unresolved tool" in err
                        else "missing_schema"
                        if "missing typed input schema" in err
                        else "approval_required"
                        if "requires required_approval=true" in err
                        else "missing_integration"
                        if "required_integrations" in err
                        else "workflow_contract_invalid"
                        for err in contract_errors
                    }
                )
                return {
                    "error": (
                        f"Workflow '{template.get('name')}' failed strict execution contract validation. "
                        "Resolve the published template metadata before starting it."
                    ),
                    "error_code": "workflow_contract_invalid",
                    "reason_codes": reason_codes,
                    "details": contract_errors[:20],
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
                    reason_text = (
                        f" Reasons: {', '.join(str(r) for r in reason_codes)}."
                    )
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
                logger.warning(
                    "Readiness gate disabled; allowing start for non-ready workflow: %s",
                    message,
                )

        infra_guard_error = self._get_execution_infra_guard_error(run_source=run_source)
        if infra_guard_error:
            logger.warning(
                "Blocking workflow start for template '%s' due to execution infra config: %s",
                template.get("name"),
                infra_guard_error.get("error"),
            )
            return infra_guard_error

        # Per-user concurrent execution limit
        if MAX_CONCURRENT_EXECUTIONS_PER_USER > 0:
            active_statuses = ["pending", "running", "paused", "waiting_approval"]
            active_query = (
                self.client.table("workflow_executions")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .in_("status", active_statuses)
            )
            active_res = active_query.execute()
            active_count = (
                active_res.count
                if active_res.count is not None
                else len(active_res.data)
            )
            if active_count >= MAX_CONCURRENT_EXECUTIONS_PER_USER:
                logger.warning(
                    "User %s has %d active executions (limit %d), rejecting workflow start",
                    user_id,
                    active_count,
                    MAX_CONCURRENT_EXECUTIONS_PER_USER,
                )
                return {
                    "error": (
                        f"You have {active_count} active workflow(s). "
                        f"Maximum concurrent executions is {MAX_CONCURRENT_EXECUTIONS_PER_USER}. "
                        "Please wait for an existing workflow to complete or cancel one."
                    ),
                    "error_code": "concurrent_execution_limit",
                    "active_count": active_count,
                    "limit": MAX_CONCURRENT_EXECUTIONS_PER_USER,
                }

        execution_context = dict(context)
        if effective_persona and "persona" not in execution_context:
            execution_context["persona"] = effective_persona

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
            "context": execution_context,
        }
        res_exec = (
            self.client.table("workflow_executions").insert(execution_data).execute()
        )
        execution_id = res_exec.data[0]["id"]
        await self._audit_execution_action(
            execution_id=execution_id,
            user_id=user_id,
            action="start",
            metadata={
                "template_id": template.get("id"),
                "template_name": template.get("name"),
                "run_source": run_source,
                "persona": effective_persona,
            },
        )

        # Trigger orchestration directly so Cloud Run request lifecycles do not drop the start callback.
        trigger_result = await edge_function_client.execute_workflow(
            execution_id, action="start"
        )
        if trigger_result.get("error"):
            logger.error(
                "Workflow %s failed to start orchestration: %s",
                execution_id,
                trigger_result,
            )
            self.client.table("workflow_executions").update(
                {
                    "status": "failed",
                    "updated_at": datetime.now().isoformat(),
                }
            ).eq("id", execution_id).execute()
            return {
                "error": "Workflow orchestration failed to start",
                "error_code": "workflow_start_failed",
                "execution_id": execution_id,
                "details": trigger_result,
            }

        first_phase = (
            phases[0]
            if phases
            else {"name": "Workflow", "steps": [{"name": "Starting"}]}
        )
        first_step = first_phase.get("steps", [{}])[0]
        step_desc = (
            first_step.get("description") or first_step.get("name") or "Next step"
        )
        return {
            "execution_id": execution_id,
            "status": "pending",
            "current_step": f"{first_phase.get('name', 'Workflow')}: {first_step.get('name', 'Starting')}",
            "message": f"Workflow queued. Orchestration triggered. Next step: {step_desc}",
        }

    async def get_execution_status(self, execution_id: str) -> dict[str, Any]:
        """Get full status of an execution."""
        res_exec = (
            self.client.table("workflow_executions")
            .select("*, workflow_templates(name, phases)")
            .eq("id", execution_id)
            .execute()
        )
        if not res_exec.data:
            return {"error": "Execution not found"}

        execution = res_exec.data[0]
        template = execution["workflow_templates"]
        template_phases = template.get("phases") or []

        res_steps = (
            self.client.table("workflow_steps")
            .select("*")
            .eq("execution_id", execution_id)
            .order("started_at")
            .execute()
        )
        history: list[dict[str, Any]] = []
        evidence_refs: list[Any] = []

        for step in res_steps.data or []:
            phase_index = step.get("phase_index")
            step_index = step.get("step_index")
            step_definition: dict[str, Any] = {}
            if isinstance(phase_index, int) and isinstance(step_index, int):
                try:
                    step_definition = (
                        template_phases[phase_index].get("steps", [])[step_index] or {}
                    )
                except (IndexError, AttributeError, TypeError):
                    step_definition = {}

            tool_name = str(
                step_definition.get("tool") or step_definition.get("action_type") or ""
            )
            output_data = step.get("output_data") or {}
            execution_meta = (
                output_data.get("_execution_meta")
                if isinstance(output_data, dict)
                else {}
            )
            if not isinstance(execution_meta, dict):
                execution_meta = {}

            resolved_tool_name = execution_meta.get("tool_name") or tool_name
            if isinstance(output_data, dict) and not resolved_tool_name:
                resolved_tool_name = str(output_data.get("tool") or "")

            trust_class = execution_meta.get("trust_class")
            if not trust_class and bool(step_definition.get("required_approval")):
                trust_class = "human_gated"
            if not trust_class and resolved_tool_name:
                trust_class = determine_trust_class(
                    resolved_tool_name, step_definition=step_definition
                )
            verification_status = execution_meta.get("verification_status")
            if not verification_status:
                verification_status = (
                    "failed" if step.get("status") == "failed" else "skipped"
                )
            step_evidence = execution_meta.get("evidence_refs")
            if not isinstance(step_evidence, list):
                step_evidence = extract_evidence_refs(output_data)
            evidence_refs.extend(step_evidence)
            last_failure_reason = execution_meta.get("last_failure_reason") or step.get(
                "error_message"
            )

            history.append(
                {
                    "id": step.get("id"),
                    "execution_id": step.get("execution_id"),
                    "phase_name": step.get("phase_name"),
                    "step_name": step.get("step_name"),
                    "status": step.get("status"),
                    "input_data": step.get("input_data"),
                    "output_data": output_data,
                    "error_message": step.get("error_message"),
                    "started_at": step.get("started_at"),
                    "completed_at": step.get("completed_at"),
                    "created_at": step.get("created_at"),
                    "updated_at": step.get("updated_at"),
                    "phase_index": phase_index,
                    "step_index": step_index,
                    "attempt_count": step.get("attempt_count"),
                    "phase_key": step.get("phase_key"),
                    "tool_name": resolved_tool_name,
                    "trust_class": trust_class,
                    "verification_status": verification_status,
                    "evidence_refs": step_evidence,
                    "last_failure_reason": last_failure_reason,
                }
            )

        trust_summary = self._summarize_execution_trust(history)
        verification_status = trust_summary.get("verification_status") or "not_started"

        return {
            "execution": execution,
            "template_name": template["name"],
            "history": history,
            "current_phase_index": execution["current_phase_index"],
            "current_step_index": execution["current_step_index"],
            "trust_summary": trust_summary,
            "verification_status": verification_status,
            "approval_state": trust_summary.get("approval_state", "not_required"),
            "evidence_refs": evidence_refs,
        }

    def _summarize_execution_trust(
        self, history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        trust_counts: dict[str, int] = {}
        verification_counts: dict[str, int] = {}
        approval_state = "not_required"
        verification_status = "not_started"
        last_failure_reason = None

        for step in history:
            trust_class = str(step.get("trust_class") or "real")
            trust_counts[trust_class] = trust_counts.get(trust_class, 0) + 1

            step_verification = str(step.get("verification_status") or "skipped")
            verification_counts[step_verification] = (
                verification_counts.get(step_verification, 0) + 1
            )

            if trust_class == "human_gated":
                if step.get("status") == "waiting_approval":
                    approval_state = "pending"
                elif approval_state == "not_required":
                    approval_state = "completed"

            if not last_failure_reason and step.get("last_failure_reason"):
                last_failure_reason = step.get("last_failure_reason")

        if verification_counts.get("failed"):
            verification_status = "failed"
        elif approval_state == "pending":
            verification_status = "pending"
        elif verification_counts.get("verified"):
            verification_status = "verified"
        elif verification_counts.get("skipped"):
            verification_status = "skipped"

        return {
            "trust_counts": trust_counts,
            "verification_counts": verification_counts,
            "approval_state": approval_state,
            "verification_status": verification_status,
            "last_failure_reason": last_failure_reason,
        }

    async def list_executions(
        self,
        user_id: str,
        status: str | None = None,
        statuses: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List workflow executions for a user."""
        query = (
            self.client.table("workflow_executions")
            .select("*, workflow_templates(name, phases)")
            .eq("user_id", user_id)
        )

        normalized_statuses = [
            value.strip()
            for value in (statuses or [])
            if isinstance(value, str) and value.strip()
        ]
        if normalized_statuses:
            if len(normalized_statuses) == 1:
                query = query.eq("status", normalized_statuses[0])
            else:
                query = query.in_("status", normalized_statuses)
        elif status:
            query = query.eq("status", status)

        res = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        # Flatten template name for easier consumption if needed,
        # or just return as is matching the join structure.
        # The router expects a list of dicts.
        executions = []
        for exc in res.data:
            tpl = exc.get("workflow_templates") or {}
            exc["template_name"] = tpl.get("name", "Unknown")
            phases = tpl.get("phases")
            exc["total_phases"] = len(phases) if isinstance(phases, list) else None
            executions.append(exc)

        return executions

    async def cancel_execution(
        self, *, execution_id: str, user_id: str, reason: str = ""
    ) -> dict[str, Any]:
        """Cancel running workflow execution."""
        current = await self.get_execution_status(execution_id)
        if "error" in current:
            return current
        execution = current["execution"]
        if execution.get("user_id") != user_id:
            return {"error": "Unauthorized"}
        if execution.get("status") in ("completed", "failed", "cancelled"):
            return {
                "error": f"Cannot cancel execution in status {execution.get('status')}"
            }

        updated = (
            self.client.table("workflow_executions")
            .update(
                {
                    "status": "cancelled",
                    "cancelled_at": datetime.now().isoformat(),
                    "cancel_reason": reason or "Cancelled by user",
                    "completed_at": datetime.now().isoformat(),
                }
            )
            .eq("id", execution_id)
            .execute()
        )
        await self._audit_execution_action(
            execution_id=execution_id,
            user_id=user_id,
            action="cancel",
            metadata={"reason": reason or "Cancelled by user"},
        )
        return {"status": "cancelled", "execution": updated.data[0]}

    async def resume_execution(
        self, *, execution_id: str, user_id: str
    ) -> dict[str, Any]:
        """Resume a failed/paused workflow from the last successful step.

        Finds the last completed step, resets all subsequent failed/skipped steps
        back to pending, flips the execution status to running, and re-triggers
        the edge function orchestrator.
        """
        current = await self.get_execution_status(execution_id)
        if "error" in current:
            return current
        execution = current["execution"]
        if execution.get("user_id") != user_id:
            return {"error": "Unauthorized"}

        resumable_statuses = ("failed", "paused", "cancelled")
        if execution.get("status") not in resumable_statuses:
            return {
                "error": f"Cannot resume execution in status '{execution.get('status')}'. Must be one of: {', '.join(resumable_statuses)}",
                "error_code": "invalid_resume_status",
            }

        # Fetch all steps ordered by phase_index, step_index
        steps_res = (
            self.client.table("workflow_steps")
            .select("*")
            .eq("execution_id", execution_id)
            .order("phase_index")
            .order("step_index")
            .execute()
        )
        steps = steps_res.data or []

        if not steps:
            return {
                "error": "No steps found for this execution",
                "error_code": "no_steps",
            }

        # Find the last completed step index
        last_completed_idx = -1
        for i, step in enumerate(steps):
            if step.get("status") == "completed":
                last_completed_idx = i

        # Reset all steps after the last completed one to pending
        reset_count = 0
        for step in steps[last_completed_idx + 1 :]:
            if step.get("status") in ("failed", "skipped", "cancelled"):
                self.client.table("workflow_steps").update(
                    {
                        "status": "pending",
                        "error_message": None,
                        "started_at": None,
                        "completed_at": None,
                    }
                ).eq("id", step["id"]).execute()
                reset_count += 1

        # Update execution status and resume point
        resume_phase = (
            steps[last_completed_idx]["phase_index"] if last_completed_idx >= 0 else 0
        )
        resume_step = (
            steps[last_completed_idx]["step_index"] if last_completed_idx >= 0 else 0
        )
        self.client.table("workflow_executions").update(
            {
                "status": "running",
                "current_phase_index": resume_phase,
                "current_step_index": resume_step,
                "updated_at": datetime.now().isoformat(),
            }
        ).eq("id", execution_id).execute()

        await self._audit_execution_action(
            execution_id=execution_id,
            user_id=user_id,
            action="resume",
            metadata={
                "resumed_from_step": last_completed_idx,
                "steps_reset": reset_count,
                "previous_status": execution.get("status"),
            },
        )

        # Re-trigger orchestration
        trigger_result = await edge_function_client.execute_workflow(
            execution_id, action="advance"
        )
        if trigger_result.get("error"):
            return {
                "error": trigger_result["error"],
                "error_code": "resume_trigger_failed",
            }

        return {
            "status": "resumed",
            "execution_id": execution_id,
            "steps_reset": reset_count,
            "message": f"Workflow resumed. {reset_count} step(s) reset to pending.",
        }

    async def advance_execution(
        self, *, execution_id: str, user_id: str
    ) -> dict[str, Any]:
        """Advance workflow execution to the next step via edge orchestration."""
        current = await self.get_execution_status(execution_id)
        if "error" in current:
            return current
        execution = current["execution"]
        if execution.get("user_id") != user_id:
            return {"error": "Unauthorized"}
        if execution.get("status") in ("completed", "failed", "cancelled"):
            return {
                "error": f"Cannot advance execution in status {execution.get('status')}"
            }

        await self._audit_execution_action(
            execution_id=execution_id,
            user_id=user_id,
            action="advance",
            metadata={"from_status": execution.get("status")},
        )
        advance_result = await edge_function_client.execute_workflow(
            execution_id, action="advance"
        )
        if advance_result.get("error"):
            return {"error": advance_result["error"]}
        return {"status": "advance_triggered", "execution_id": execution_id}

    async def retry_step(
        self, *, execution_id: str, step_id: str, user_id: str
    ) -> dict[str, Any]:
        """Retry failed/skipped step by creating another attempt record."""
        current = await self.get_execution_status(execution_id)
        if "error" in current:
            return current
        execution = current["execution"]
        if execution.get("user_id") != user_id:
            return {"error": "Unauthorized"}

        step_res = (
            self.client.table("workflow_steps")
            .select("*")
            .eq("id", step_id)
            .eq("execution_id", execution_id)
            .limit(1)
            .execute()
        )
        if not step_res.data:
            return {"error": "Step not found"}
        step = step_res.data[0]
        if step.get("status") not in ("failed", "skipped"):
            return {
                "error": f"Step status must be failed or skipped, got {step.get('status')}"
            }

        attempt = (step.get("attempt_count") or 1) + 1
        updated = (
            self.client.table("workflow_steps")
            .update(
                {
                    "status": "running",
                    "attempt_count": attempt,
                    "error_message": None,
                    "completed_at": None,
                    "started_at": datetime.now().isoformat(),
                    "idempotency_key": f"{execution_id}:{step.get('phase_index', 0)}:{step.get('step_index', 0)}:{attempt}",
                }
            )
            .eq("id", step_id)
            .execute()
        )
        await self._audit_execution_action(
            execution_id=execution_id,
            user_id=user_id,
            action="retry_step",
            metadata={"step_id": step_id, "attempt_count": attempt},
        )
        retry_result = await edge_function_client.execute_workflow(
            execution_id, action="retry"
        )
        if retry_result.get("error"):
            return {"error": retry_result["error"]}
        return {"status": "retry_started", "step": updated.data[0]}

    async def _audit_template_action(
        self,
        template: dict[str, Any],
        action: str,
        *,
        user_id: str,
        metadata: dict[str, Any],
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
        metadata: dict[str, Any],
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
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Approve the current step if it is waiting for approval."""
        status = await self.get_execution_status(execution_id)
        if "error" in status:
            return status

        execution = status["execution"]
        if user_id and execution.get("user_id") != user_id:
            return {"error": "Unauthorized"}

        # Find current active step
        res_step = (
            self.client.table("workflow_steps")
            .select("*")
            .eq("execution_id", execution_id)
            .eq("status", "waiting_approval")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not res_step.data:
            return {"error": "No step is currently waiting for approval"}

        step = res_step.data[0]

        # Mark completed
        self.client.table("workflow_steps").update(
            {
                "status": "completed",
                "output_data": {"approval_message": step_message},
                "completed_at": datetime.now().isoformat(),
            }
        ).eq("id", step["id"]).execute()

        # Advance to next step directly so approval does not rely on a best-effort background callback.
        advance_result = await edge_function_client.execute_workflow(
            execution_id, action="advance"
        )
        if advance_result.get("error"):
            return {"error": advance_result["error"]}

        await self._audit_execution_action(
            execution_id=execution_id,
            action="approve_step",
            user_id=user_id,
            metadata={
                "step_id": step.get("id"),
                "step_name": step.get("step_name"),
                "phase_name": step.get("phase_name"),
                "message": step_message,
            },
        )
        return {
            "status": "approved",
            "message": "Step approved. Workflow execution continuing.",
        }

    async def _advance_workflow(
        self, execution: dict, phases: list[dict]
    ) -> dict[str, Any]:
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
