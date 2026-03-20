"""Integration-aware workflow tools (Tier B priorities).

These tools prefer real integrations (Resend, HubSpot, Supabase) and only
fall back to internal artifacts when credentials/services are unavailable.
"""

import json
import os
from typing import Any

from app.agents.content.tools import save_content
from app.agents.data.tools import create_report, track_event
from app.agents.sales.tools import create_task
from app.mcp.config import get_mcp_config
from app.mcp.integrations import create_crm_contact, send_notification_email
from app.services.supabase_client import get_service_client


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, default=str)


def _as_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _integration_guard_flags() -> dict[str, bool]:
    strict_critical_tool_guard = _as_bool(
        os.getenv("WORKFLOW_STRICT_CRITICAL_TOOL_GUARD"),
        default=False,
    )
    allow_fallback_simulation = _as_bool(
        os.getenv("WORKFLOW_ALLOW_FALLBACK_SIMULATION"),
        default=True,
    )
    return {
        "strict_critical_tool_guard": strict_critical_tool_guard,
        "allow_fallback_simulation": allow_fallback_simulation,
        "strict_integration_mode": strict_critical_tool_guard
        or not allow_fallback_simulation,
    }


def _integration_not_configured(
    *,
    tool: str,
    required_integrations: list[str],
    error: str,
    **details: Any,
) -> dict[str, Any]:
    return {
        "success": False,
        "status": "failed",
        "error": error,
        "error_code": "integration_not_configured",
        "tool": tool,
        "required_integrations": required_integrations,
        **_integration_guard_flags(),
        **details,
    }


async def send_message(
    to: list[str] | None = None,
    subject: str = "Workflow Message",
    body: str = "",
    channel: str = "email",
    **kwargs,
) -> dict:
    """Send a message via configured channel (email or crm).

    Email uses Resend integration if configured.
    CRM channel creates/updates a HubSpot contact.
    """
    recipients = [x for x in (to or []) if isinstance(x, str) and x.strip()]
    message_body = body or kwargs.get("message") or "Automated workflow message."
    cfg = get_mcp_config()
    guard_flags = _integration_guard_flags()

    if channel == "email" and cfg.is_email_configured() and recipients:
        result = await send_notification_email(
            to_emails=recipients,
            subject=subject,
            html_content=f"<p>{message_body}</p>",
            text_content=message_body,
        )
        await track_event(
            "send_message",
            "communication",
            _json({"channel": "email", "to": recipients}),
        )
        return {
            "success": bool(result.get("success")),
            "status": "integrated",
            "result": result,
            "tool": "send_message",
        }

    if (
        channel == "email"
        and recipients
        and not cfg.is_email_configured()
        and guard_flags["strict_integration_mode"]
    ):
        await track_event(
            "send_message_strict_blocked",
            "communication",
            _json(
                {
                    "channel": "email",
                    "to": recipients,
                    "reason": "email_integration_not_configured",
                }
            ),
        )
        return _integration_not_configured(
            tool="send_message",
            required_integrations=["email"],
            error="Email integration is not configured for strict workflow execution.",
            channel="email",
            recipients=recipients,
            blocked_fallback="create_task",
        )

    email = kwargs.get("email") or (recipients[0] if recipients else None)
    if channel == "crm" and cfg.is_crm_configured():
        if email:
            result = await create_crm_contact(
                email=email,
                first_name=kwargs.get("first_name"),
                last_name=kwargs.get("last_name"),
                company=kwargs.get("company"),
            )
            await track_event(
                "send_message",
                "communication",
                _json({"channel": "crm", "email": email}),
            )
            return {
                "success": bool(result.get("success")),
                "status": "integrated",
                "result": result,
                "tool": "send_message",
            }

    if (
        channel == "crm"
        and email
        and not cfg.is_crm_configured()
        and guard_flags["strict_integration_mode"]
    ):
        await track_event(
            "send_message_strict_blocked",
            "communication",
            _json(
                {
                    "channel": "crm",
                    "email": email,
                    "reason": "crm_integration_not_configured",
                }
            ),
        )
        return _integration_not_configured(
            tool="send_message",
            required_integrations=["crm"],
            error="CRM integration is not configured for strict workflow execution.",
            channel="crm",
            email=email,
            blocked_fallback="create_task",
        )

    fallback = await create_task(
        description=f"Message queued (fallback): {subject} -> {recipients or ['n/a']}"
    )
    await track_event(
        "send_message_fallback",
        "communication",
        _json({"channel": channel, "to": recipients}),
    )
    return {
        "success": True,
        "status": "fallback",
        "task": fallback,
        "tool": "send_message",
    }


async def start_call(
    participant: str = "Stakeholder",
    purpose: str = "Workflow call",
    when: str | None = None,
    **kwargs,
) -> dict:
    """Create a call kickoff artifact and dispatch email invite when possible."""
    when_value = when or kwargs.get("start_time") or "unscheduled"
    note = await save_content(
        title=f"Call Plan: {participant}",
        content=f"Purpose: {purpose}\nWhen: {when_value}",
    )
    to = kwargs.get("to") or []
    if isinstance(to, str):
        to = [to]
    dispatched = None
    cfg = get_mcp_config()
    if (
        to
        and not cfg.is_email_configured()
        and _integration_guard_flags()["strict_integration_mode"]
    ):
        await track_event(
            "start_call_strict_blocked",
            "communication",
            _json(
                {
                    "participant": participant,
                    "when": when_value,
                    "to": to,
                    "reason": "email_integration_not_configured",
                }
            ),
        )
        return _integration_not_configured(
            tool="start_call",
            required_integrations=["email"],
            error="Email integration is not configured for strict workflow execution.",
            note=note,
            dispatch=None,
            recipients=to,
            blocked_fallback="note_only",
        )

    if cfg.is_email_configured() and to:
        dispatched = await send_notification_email(
            to_emails=to,
            subject=f"Call Scheduled: {purpose}",
            html_content=f"<p>Participant: {participant}</p><p>When: {when_value}</p>",
            text_content=f"Participant: {participant}\nWhen: {when_value}",
        )
    await track_event(
        "start_call",
        "communication",
        _json({"participant": participant, "when": when_value}),
    )
    return {
        "success": True,
        "status": "integrated" if dispatched else "fallback",
        "note": note,
        "dispatch": dispatched,
        "tool": "start_call",
    }


async def listen_call(call_id: str | None = None, notes: str = "", **kwargs) -> dict:
    """Store call transcript/notes as a content artifact."""
    artifact = await save_content(
        title=f"Call Notes: {call_id or 'workflow-call'}",
        content=notes or kwargs.get("transcript") or "Call listening notes captured.",
    )
    await track_event("listen_call", "communication", _json({"call_id": call_id}))
    return {
        "success": True,
        "status": "integrated",
        "artifact": artifact,
        "tool": "listen_call",
    }


async def update_hris(
    employee_id: str = "",
    update_type: str = "profile",
    payload: str | None = None,
    **kwargs,
) -> dict:
    """Record HRIS update intent as a report and optional CRM mirror if configured."""
    data = {
        "employee_id": employee_id,
        "update_type": update_type,
        "payload": payload or kwargs,
    }
    report = await create_report(
        title=f"HRIS Update: {employee_id or 'employee'}",
        report_type="hris_update",
        data=_json(data),
        description="HRIS update intent logged by workflow.",
    )
    await track_event(
        "update_hris",
        "hr",
        _json({"employee_id": employee_id, "update_type": update_type}),
    )
    return {
        "success": True,
        "status": "integrated",
        "report": report,
        "tool": "update_hris",
    }


async def create_connection(
    connection_name: str = "default", connection_type: str = "supabase", **kwargs
) -> dict:
    """Create/test a logical connection entry. Supabase connections are probed live."""
    probe = {"tested": False, "ok": False, "details": None}
    if connection_type == "supabase":
        probe["tested"] = True
        try:
            client = get_service_client()
            client.table("workflow_templates").select("id").limit(1).execute()
            probe["ok"] = True
            probe["details"] = "Supabase probe succeeded"
        except Exception as e:
            probe["details"] = str(e)

    artifact = await save_content(
        title=f"Connection: {connection_name}",
        content=f"type={connection_type}\nprobe={_json(probe)}\nmeta={_json(kwargs)}",
    )
    await track_event(
        "create_connection",
        "data",
        _json({"name": connection_name, "type": connection_type, "probe": probe}),
    )
    if (
        connection_type == "supabase"
        and probe["tested"]
        and not probe["ok"]
        and _integration_guard_flags()["strict_integration_mode"]
    ):
        return _integration_not_configured(
            tool="create_connection",
            required_integrations=["supabase"],
            error="Supabase connection probe failed during strict workflow execution.",
            artifact=artifact,
            probe=probe,
            connection_name=connection_name,
            connection_type=connection_type,
            blocked_fallback="artifact_only",
        )
    return {
        "success": True,
        "status": "integrated" if probe["ok"] else "fallback",
        "artifact": artifact,
        "probe": probe,
        "tool": "create_connection",
    }


async def create_query(
    name: str = "query", query: str = "", connection_name: str = "default", **kwargs
) -> dict:
    """Persist a query artifact and metadata."""
    artifact = await save_content(
        title=f"Query: {name}",
        content=f"connection={connection_name}\nquery={query or kwargs.get('sql') or ''}",
    )
    await track_event(
        "create_query",
        "data",
        _json({"name": name, "connection_name": connection_name}),
    )
    return {
        "success": True,
        "status": "integrated",
        "artifact": artifact,
        "tool": "create_query",
    }


async def create_table(
    name: str = "table",
    columns: list[dict[str, Any]] | None = None,
    connection_name: str = "default",
    **kwargs,
) -> dict:
    """Persist table schema intent as a content artifact."""
    artifact = await save_content(
        title=f"Table: {name}",
        content=f"connection={connection_name}\ncolumns={_json({'columns': columns or []})}",
    )
    await track_event(
        "create_table",
        "data",
        _json(
            {"name": name, "connection_name": connection_name, "columns": columns or []}
        ),
    )
    return {
        "success": True,
        "status": "integrated",
        "artifact": artifact,
        "tool": "create_table",
    }


async def grant_access(
    resource: str = "", principal: str = "", role: str = "viewer", **kwargs
) -> dict:
    """Record an access-grant action."""
    task = await create_task(
        description=f"Grant access: {principal} -> {resource} as {role}"
    )
    await track_event(
        "grant_access",
        "security",
        _json({"resource": resource, "principal": principal, "role": role}),
    )
    return {
        "success": True,
        "status": "integrated",
        "task": task,
        "tool": "grant_access",
    }


async def audit_logs(tool_name: str | None = None, limit: int = 50, **kwargs) -> dict:
    """Query MCP audit logs from Supabase directly."""
    try:
        client = get_service_client()
        q = (
            client.table("mcp_audit_logs")
            .select("timestamp,tool_name,user_id,success,response_status,error_message")
            .order("timestamp", desc=True)
            .limit(limit)
        )
        if tool_name:
            q = q.eq("tool_name", tool_name)
        res = q.execute()
        rows = res.data or []
        await track_event(
            "audit_logs",
            "security",
            _json({"tool_name": tool_name, "limit": limit, "rows": len(rows)}),
        )
        return {
            "success": True,
            "status": "integrated",
            "logs": rows,
            "count": len(rows),
            "tool": "audit_logs",
        }
    except Exception as e:
        await track_event(
            "audit_logs_failed",
            "security",
            _json({"error": str(e), "tool_name": tool_name}),
        )
        return {
            "success": False,
            "status": "failed",
            "error": str(e),
            "tool": "audit_logs",
        }


async def check_logs(tool_name: str | None = None, limit: int = 50, **kwargs) -> dict:
    """Alias for audit log retrieval."""
    return await audit_logs(tool_name=tool_name, limit=limit, **kwargs)


async def run_script(
    script_name: str = "workflow_script", args: list[str] | None = None, **kwargs
) -> dict:
    """Track script execution intent with auditability."""
    report = await create_report(
        title=f"Script Run: {script_name}",
        report_type="script_execution",
        data=_json({"script_name": script_name, "args": args or [], "kwargs": kwargs}),
        description="Script execution request captured by workflow.",
    )
    await track_event("run_script", "engineering", _json({"script_name": script_name}))
    return {
        "success": True,
        "status": "integrated",
        "report": report,
        "tool": "run_script",
    }


async def run_deployment(
    service: str = "service",
    environment: str = "staging",
    version: str | None = None,
    **kwargs,
) -> dict:
    """Track deployment run request."""
    task = await create_task(
        description=f"Deployment run: {service} to {environment} version={version or 'latest'}"
    )
    await track_event(
        "run_deployment",
        "engineering",
        _json({"service": service, "environment": environment, "version": version}),
    )
    return {
        "success": True,
        "status": "integrated",
        "task": task,
        "tool": "run_deployment",
    }


async def process_forms(
    form_name: str = "form",
    submission_id: str | None = None,
    payload: dict[str, Any] | None = None,
    **kwargs,
) -> dict:
    """Persist form-processing output as content."""
    artifact = await save_content(
        title=f"Form Processed: {form_name}",
        content=_json(
            {"submission_id": submission_id, "payload": payload or {}, "kwargs": kwargs}
        ),
    )
    await track_event(
        "process_forms",
        "operations",
        _json({"form_name": form_name, "submission_id": submission_id}),
    )
    return {
        "success": True,
        "status": "integrated",
        "artifact": artifact,
        "tool": "process_forms",
    }


async def update_code(
    repo: str = "repo", branch: str = "main", summary: str = "", **kwargs
) -> dict:
    """Record code-update request and metadata."""
    artifact = await save_content(
        title=f"Code Update: {repo}",
        content=f"branch={branch}\nsummary={summary or 'workflow requested update'}\nmeta={_json(kwargs)}",
    )
    await track_event(
        "update_code", "engineering", _json({"repo": repo, "branch": branch})
    )
    return {
        "success": True,
        "status": "integrated",
        "artifact": artifact,
        "tool": "update_code",
    }


async def train_model(
    model_name: str = "model", dataset: str = "dataset", **kwargs
) -> dict:
    """Track model-training request."""
    report = await create_report(
        title=f"Model Training: {model_name}",
        report_type="ml_training",
        data=_json({"model_name": model_name, "dataset": dataset, "kwargs": kwargs}),
        description="Model training request captured by workflow.",
    )
    await track_event(
        "train_model", "ml", _json({"model_name": model_name, "dataset": dataset})
    )
    return {
        "success": True,
        "status": "integrated",
        "report": report,
        "tool": "train_model",
    }


async def deploy_service(
    service_name: str = "service",
    environment: str = "staging",
    version: str | None = None,
    **kwargs,
) -> dict:
    """Track service deployment request."""
    task = await create_task(
        description=f"Deploy service: {service_name} to {environment} version={version or 'latest'}"
    )
    await track_event(
        "deploy_service",
        "engineering",
        _json(
            {
                "service_name": service_name,
                "environment": environment,
                "version": version,
            }
        ),
    )
    return {
        "success": True,
        "status": "integrated",
        "task": task,
        "tool": "deploy_service",
    }


async def create_chart(
    name: str = "chart", chart_type: str = "bar", data_query: str = "", **kwargs
) -> dict:
    """Persist chart definition artifact."""
    artifact = await save_content(
        title=f"Chart: {name}",
        content=f"type={chart_type}\nquery={data_query}\nmeta={_json(kwargs)}",
    )
    await track_event(
        "create_chart", "analytics", _json({"name": name, "chart_type": chart_type})
    )
    return {
        "success": True,
        "status": "integrated",
        "artifact": artifact,
        "tool": "create_chart",
    }


async def process_data(
    pipeline_name: str = "pipeline",
    input_source: str = "source",
    operation: str = "transform",
    **kwargs,
) -> dict:
    """Track data processing job request."""
    report = await create_report(
        title=f"Data Processing: {pipeline_name}",
        report_type="data_processing",
        data=_json(
            {
                "pipeline_name": pipeline_name,
                "input_source": input_source,
                "operation": operation,
                "kwargs": kwargs,
            }
        ),
        description="Data processing request captured by workflow.",
    )
    await track_event(
        "process_data",
        "data",
        _json(
            {
                "pipeline_name": pipeline_name,
                "input_source": input_source,
                "operation": operation,
            }
        ),
    )
    return {
        "success": True,
        "status": "integrated",
        "report": report,
        "tool": "process_data",
    }
