"""Concrete workflow operations tools used by seeded workflow templates.

These tools provide non-placeholder implementations for workflow template
actions that do not yet have dedicated product integrations.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.agents.content.tools import save_content, search_knowledge
from app.agents.data.tools import create_report, query_events, track_event
from app.agents.sales.tools import create_task


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default=str)


async def _audit_event(event_name: str, category: str, payload: dict[str, Any]) -> None:
    await track_event(event_name=event_name, category=category, properties=_json(payload))


def _normalize_recipients(recipient: str | list[str] | None) -> list[str]:
    if recipient is None:
        return []
    if isinstance(recipient, str):
        return [recipient] if recipient.strip() else []
    return [value for value in recipient if isinstance(value, str) and value.strip()]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


async def approve_document(
    document_id: str | None = None,
    title: str = "Workflow Document",
    decision: str = "approved",
    approver: str | None = None,
    notes: str = "",
    **kwargs,
) -> dict:
    """Record a document approval decision and create an audit task."""
    task = await create_task(
        description=(
            f"Document {decision}: {title} "
            f"(id={document_id or 'n/a'}, approver={approver or 'workflow-agent'})"
        )
    )
    await _audit_event(
        "approve_document",
        "compliance",
        {
            "document_id": document_id,
            "title": title,
            "decision": decision,
            "approver": approver,
            "notes": notes,
            "kwargs": kwargs,
        },
    )
    return {
        "success": True,
        "status": "completed",
        "tool": "approve_document",
        "approval": {
            "document_id": document_id,
            "title": title,
            "decision": decision,
            "approver": approver or "workflow-agent",
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        },
        "task": task,
    }


async def edit_document(
    document_id: str | None = None,
    title: str = "Workflow Document",
    content: str = "",
    changes: str = "",
    **kwargs,
) -> dict:
    """Persist edited document content as a knowledge artifact."""
    artifact = await save_content(
        title=f"Edited Document: {title}",
        content=content
        or (
            f"document_id={document_id or 'n/a'}\n"
            f"changes={changes or 'No change details provided'}\n"
            f"meta={_json(kwargs)}"
        ),
    )
    await _audit_event(
        "edit_document",
        "content",
        {"document_id": document_id, "title": title, "changes": changes, "kwargs": kwargs},
    )
    return {
        "success": True,
        "status": "completed",
        "tool": "edit_document",
        "artifact": artifact,
    }


async def calculate_score(
    item: str = "Roadmap Item",
    framework: str = "RICE",
    criteria: dict[str, Any] | None = None,
    weights: dict[str, Any] | None = None,
    **kwargs,
) -> dict:
    """Calculate a numeric score using RICE (default) or weighted criteria."""
    criteria = criteria or {}
    weights = weights or {}
    framework_lower = (framework or "RICE").strip().lower()

    if framework_lower == "rice":
        reach = _to_float(criteria.get("reach", kwargs.get("reach")), 1.0)
        impact = _to_float(criteria.get("impact", kwargs.get("impact")), 1.0)
        confidence = _to_float(criteria.get("confidence", kwargs.get("confidence")), 1.0)
        effort = _to_float(criteria.get("effort", kwargs.get("effort")), 1.0)
        effort = effort if effort > 0 else 1.0
        score = (reach * impact * confidence) / effort
        details = {
            "reach": reach,
            "impact": impact,
            "confidence": confidence,
            "effort": effort,
            "formula": "(reach * impact * confidence) / effort",
        }
    else:
        numeric_values: dict[str, float] = {
            key: _to_float(value) for key, value in criteria.items() if isinstance(value, (int, float, str))
        }
        if not numeric_values:
            numeric_values = {
                key: _to_float(value)
                for key, value in kwargs.items()
                if isinstance(value, (int, float, str))
            }

        weighted_total = 0.0
        weight_sum = 0.0
        for key, value in numeric_values.items():
            weight = _to_float(weights.get(key), 1.0)
            weighted_total += value * weight
            weight_sum += weight
        score = weighted_total / weight_sum if weight_sum > 0 else 0.0
        details = {
            "criteria": numeric_values,
            "weights": {key: _to_float(value, 1.0) for key, value in weights.items()},
            "formula": "sum(value * weight) / sum(weight)",
        }

    await _audit_event(
        "calculate_score",
        "analytics",
        {"item": item, "framework": framework, "score": score, "details": details},
    )
    return {
        "success": True,
        "status": "completed",
        "tool": "calculate_score",
        "item": item,
        "framework": framework,
        "score": round(score, 4),
        "details": details,
    }


async def query_feedback(
    source: str = "customer_feedback",
    event_name: str | None = None,
    limit: int = 50,
    **kwargs,
) -> dict:
    """Query feedback events from analytics storage."""
    feedback = await query_events(event_name=event_name, category="feedback", limit=limit)
    events = feedback.get("events", [])
    await _audit_event(
        "query_feedback",
        "feedback",
        {"source": source, "event_name": event_name, "limit": limit, "kwargs": kwargs},
    )
    return {
        "success": bool(feedback.get("success", True)),
        "status": "completed" if feedback.get("success", True) else "failed",
        "tool": "query_feedback",
        "source": source,
        "feedback": events,
        "count": feedback.get("count", len(events)),
    }


async def review_policy(
    policy_name: str = "Company Policy",
    policy_text: str = "",
    policy_id: str | None = None,
    standard: str = "internal",
    **kwargs,
) -> dict:
    """Create a lightweight policy review artifact with basic checks."""
    text_lower = policy_text.lower()
    checks = {
        "has_scope": "scope" in text_lower,
        "has_owner": "owner" in text_lower or "responsible" in text_lower,
        "has_effective_date": "effective" in text_lower and "date" in text_lower,
        "has_exceptions": "exception" in text_lower,
    }
    findings = [name for name, passed in checks.items() if not passed]
    risk_level = "low" if not findings else ("medium" if len(findings) <= 2 else "high")

    artifact = await save_content(
        title=f"Policy Review: {policy_name}",
        content=_json(
            {
                "policy_id": policy_id,
                "standard": standard,
                "checks": checks,
                "missing_sections": findings,
                "risk_level": risk_level,
                "meta": kwargs,
            }
        ),
    )
    await _audit_event(
        "review_policy",
        "compliance",
        {"policy_name": policy_name, "policy_id": policy_id, "risk_level": risk_level},
    )
    return {
        "success": True,
        "status": "completed",
        "tool": "review_policy",
        "policy_name": policy_name,
        "risk_level": risk_level,
        "checks": checks,
        "artifact": artifact,
    }


async def scan_database(
    system_name: str = "primary_db",
    tables: list[str] | None = None,
    scan_focus: str = "schema_and_quality",
    sample_size: int = 100,
    **kwargs,
) -> dict:
    """Record a structured database scan report."""
    report = await create_report(
        title=f"Database Scan: {system_name}",
        report_type="database_scan",
        data=_json(
            {
                "system_name": system_name,
                "tables": tables or [],
                "scan_focus": scan_focus,
                "sample_size": sample_size,
                "meta": kwargs,
            }
        ),
        description="Workflow database scan snapshot.",
    )
    await _audit_event(
        "scan_database",
        "data",
        {
            "system_name": system_name,
            "table_count": len(tables or []),
            "scan_focus": scan_focus,
            "sample_size": sample_size,
        },
    )
    return {
        "success": True,
        "status": "completed",
        "tool": "scan_database",
        "report": report,
    }


async def update_gantt(
    project_name: str = "Workflow Project",
    milestones: list[dict[str, Any]] | None = None,
    timeline: str | None = None,
    **kwargs,
) -> dict:
    """Persist Gantt timeline updates for roadmap workflows."""
    artifact = await save_content(
        title=f"Gantt Update: {project_name}",
        content=_json(
            {
                "project_name": project_name,
                "timeline": timeline,
                "milestones": milestones or [],
                "meta": kwargs,
            }
        ),
    )
    await _audit_event(
        "update_gantt",
        "planning",
        {"project_name": project_name, "milestone_count": len(milestones or [])},
    )
    return {
        "success": True,
        "status": "completed",
        "tool": "update_gantt",
        "artifact": artifact,
        "milestone_count": len(milestones or []),
    }


async def send_guide(
    title: str = "Workflow Guide",
    recipient: str | list[str] | None = None,
    content: str = "",
    **kwargs,
) -> dict:
    """Send or queue a guide distribution action."""
    recipients = _normalize_recipients(recipient)
    task = await create_task(
        description=f"Send guide '{title}' to {recipients or ['pending_recipient']}"
    )
    guide = await save_content(
        title=f"Guide: {title}",
        content=content or _json({"recipients": recipients, "meta": kwargs}),
    )
    await _audit_event("send_guide", "communication", {"title": title, "recipients": recipients})
    return {
        "success": True,
        "status": "completed",
        "tool": "send_guide",
        "task": task,
        "artifact": guide,
        "recipients": recipients,
    }


async def update_asset_log(
    asset_id: str = "",
    action: str = "update",
    owner: str | None = None,
    details: str = "",
    **kwargs,
) -> dict:
    """Append an asset lifecycle entry to reporting storage."""
    report = await create_report(
        title=f"Asset Log Update: {asset_id or 'asset'}",
        report_type="asset_log",
        data=_json(
            {
                "asset_id": asset_id,
                "action": action,
                "owner": owner,
                "details": details,
                "meta": kwargs,
            }
        ),
        description="Asset log updated by workflow.",
    )
    await _audit_event("update_asset_log", "operations", {"asset_id": asset_id, "action": action})
    return {"success": True, "status": "completed", "tool": "update_asset_log", "report": report}


async def update_ledger(
    account: str = "general",
    amount: float | int | None = None,
    entry_type: str = "adjustment",
    description: str = "",
    **kwargs,
) -> dict:
    """Record a ledger update entry."""
    report = await create_report(
        title=f"Ledger Update: {account}",
        report_type="ledger_update",
        data=_json(
            {
                "account": account,
                "amount": _to_float(amount, 0.0),
                "entry_type": entry_type,
                "description": description,
                "meta": kwargs,
            }
        ),
        description="Ledger updated by workflow.",
    )
    await _audit_event("update_ledger", "ledger", {"account": account, "entry_type": entry_type})
    return {"success": True, "status": "completed", "tool": "update_ledger", "report": report}


async def update_settings(
    setting_name: str = "workflow_setting",
    value: Any = None,
    scope: str = "account",
    **kwargs,
) -> dict:
    """Persist a settings update request."""
    artifact = await save_content(
        title=f"Settings Update: {setting_name}",
        content=_json({"setting_name": setting_name, "value": value, "scope": scope, "meta": kwargs}),
    )
    await _audit_event("update_settings", "configuration", {"setting_name": setting_name, "scope": scope})
    return {"success": True, "status": "completed", "tool": "update_settings", "artifact": artifact}


async def manage_comments(
    platform: str = "social",
    action: str = "reply",
    comment_id: str | None = None,
    response: str = "",
    **kwargs,
) -> dict:
    """Track social/community comment handling actions."""
    task = await create_task(
        description=(
            f"Manage comments on {platform}: action={action}, "
            f"comment_id={comment_id or 'n/a'}, response={response or '[no response text]'}"
        )
    )
    await _audit_event(
        "manage_comments",
        "community",
        {"platform": platform, "action": action, "comment_id": comment_id, "kwargs": kwargs},
    )
    return {"success": True, "status": "completed", "tool": "manage_comments", "task": task}


async def query_ledger(account: str | None = None, limit: int = 100, **kwargs) -> dict:
    """Query ledger-related analytics events."""
    result = await query_events(event_name=account, category="ledger", limit=limit)
    await _audit_event("query_ledger", "ledger", {"account": account, "limit": limit, "kwargs": kwargs})
    return {
        "success": bool(result.get("success", True)),
        "status": "completed" if result.get("success", True) else "failed",
        "tool": "query_ledger",
        "entries": result.get("events", []),
        "count": result.get("count", 0),
    }


async def read_docs(query: str = "", limit: int = 5, **kwargs) -> dict:
    """Search knowledge documents using the content search tool."""
    result = search_knowledge(query or kwargs.get("topic") or "workflow docs")
    records = result.get("results", [])[: max(limit, 0)]
    await _audit_event("read_docs", "knowledge", {"query": query, "limit": limit, "kwargs": kwargs})
    return {
        "success": True,
        "status": "completed",
        "tool": "read_docs",
        "documents": records,
        "count": len(records),
    }


async def send_file(
    file_name: str = "workflow_file",
    recipient: str | list[str] | None = None,
    content: str = "",
    **kwargs,
) -> dict:
    """Create a file artifact and queue a send action."""
    recipients = _normalize_recipients(recipient)
    artifact = await save_content(
        title=f"File: {file_name}",
        content=content or _json({"file_name": file_name, "meta": kwargs}),
    )
    task = await create_task(description=f"Send file '{file_name}' to {recipients or ['pending_recipient']}")
    await _audit_event("send_file", "communication", {"file_name": file_name, "recipients": recipients})
    return {
        "success": True,
        "status": "completed",
        "tool": "send_file",
        "artifact": artifact,
        "task": task,
    }


async def submit_form(
    form_name: str = "Workflow Form",
    fields: dict[str, Any] | None = None,
    submitter: str | None = None,
    **kwargs,
) -> dict:
    """Store a form submission payload."""
    payload = {"form_name": form_name, "fields": fields or {}, "submitter": submitter, "meta": kwargs}
    artifact = await save_content(title=f"Form Submission: {form_name}", content=_json(payload))
    await _audit_event("submit_form", "forms", payload)
    return {"success": True, "status": "completed", "tool": "submit_form", "artifact": artifact}


async def update_budget(
    period: str = "current",
    amount: float | int | None = None,
    department: str = "general",
    notes: str = "",
    **kwargs,
) -> dict:
    """Record a budget update as a finance report."""
    report = await create_report(
        title=f"Budget Update: {department} ({period})",
        report_type="budget_update",
        data=_json(
            {
                "period": period,
                "department": department,
                "amount": _to_float(amount, 0.0),
                "notes": notes,
                "meta": kwargs,
            }
        ),
        description="Budget update recorded by workflow.",
    )
    await _audit_event("update_budget", "finance", {"period": period, "department": department})
    return {"success": True, "status": "completed", "tool": "update_budget", "report": report}


async def update_cms(
    page_title: str = "Knowledge Base Page",
    action: str = "update",
    content: str = "",
    **kwargs,
) -> dict:
    """Persist a CMS page update artifact."""
    artifact = await save_content(
        title=f"CMS {action.title()}: {page_title}",
        content=content or _json({"action": action, "page_title": page_title, "meta": kwargs}),
    )
    await _audit_event("update_cms", "content", {"page_title": page_title, "action": action})
    return {"success": True, "status": "completed", "tool": "update_cms", "artifact": artifact}


async def create_pr(
    repo: str = "repo",
    branch: str = "main",
    title: str = "Workflow Pull Request",
    summary: str = "",
    **kwargs,
) -> dict:
    """Create a pull-request planning artifact and execution task."""
    artifact = await save_content(
        title=f"PR Draft: {title}",
        content=_json({"repo": repo, "branch": branch, "summary": summary, "meta": kwargs}),
    )
    task = await create_task(description=f"Open PR in {repo} on {branch}: {title}")
    await _audit_event("create_pr", "engineering", {"repo": repo, "branch": branch, "title": title})
    return {"success": True, "status": "completed", "tool": "create_pr", "artifact": artifact, "task": task}


async def create_record(
    record_type: str = "incident",
    title: str = "Workflow Record",
    details: dict[str, Any] | None = None,
    **kwargs,
) -> dict:
    """Create a durable workflow record."""
    report = await create_report(
        title=f"{record_type.title()} Record: {title}",
        report_type=f"{record_type}_record",
        data=_json({"title": title, "details": details or {}, "meta": kwargs}),
        description="Workflow record created.",
    )
    await _audit_event("create_record", "records", {"record_type": record_type, "title": title})
    return {"success": True, "status": "completed", "tool": "create_record", "report": report}


async def create_tracking_plan(
    plan_name: str = "Tracking Plan",
    events: list[dict[str, Any]] | None = None,
    objective: str = "",
    **kwargs,
) -> dict:
    """Create an analytics tracking plan report."""
    report = await create_report(
        title=f"Tracking Plan: {plan_name}",
        report_type="tracking_plan",
        data=_json({"plan_name": plan_name, "objective": objective, "events": events or [], "meta": kwargs}),
        description="Tracking plan generated by workflow.",
    )
    await _audit_event("create_tracking_plan", "analytics", {"plan_name": plan_name, "event_count": len(events or [])})
    return {"success": True, "status": "completed", "tool": "create_tracking_plan", "report": report}


async def query_bank(account: str | None = None, limit: int = 50, **kwargs) -> dict:
    """Query bank-monitoring events recorded by workflows."""
    result = await query_events(event_name=account, category="bank", limit=limit)
    await _audit_event("query_bank", "finance", {"account": account, "limit": limit, "kwargs": kwargs})
    return {
        "success": bool(result.get("success", True)),
        "status": "completed" if result.get("success", True) else "failed",
        "tool": "query_bank",
        "entries": result.get("events", []),
        "count": result.get("count", 0),
    }


async def update_record(
    record_id: str = "",
    status: str = "updated",
    updates: dict[str, Any] | None = None,
    **kwargs,
) -> dict:
    """Persist record updates in a content artifact."""
    artifact = await save_content(
        title=f"Record Update: {record_id or 'record'}",
        content=_json({"record_id": record_id, "status": status, "updates": updates or {}, "meta": kwargs}),
    )
    task = await create_task(description=f"Record {record_id or 'n/a'} marked as {status}")
    await _audit_event("update_record", "records", {"record_id": record_id, "status": status})
    return {
        "success": True,
        "status": "completed",
        "tool": "update_record",
        "artifact": artifact,
        "task": task,
    }


async def create_form(
    title: str = "Workflow Form",
    description: str = "",
    fields: list[dict[str, Any]] | None = None,
    **kwargs,
) -> dict:
    """Create a form specification artifact for workflow-driven collection."""
    artifact = await save_content(
        title=f"Form Spec: {title}",
        content=_json({"description": description, "fields": fields or [], "meta": kwargs}),
    )
    await _audit_event("create_form", "forms", {"title": title, "field_count": len(fields or [])})
    return {"success": True, "status": "completed", "tool": "create_form", "artifact": artifact}


async def send_form(
    form_id: str | None = None,
    recipient: str | list[str] | None = None,
    channel: str = "email",
    **kwargs,
) -> dict:
    """Queue form distribution to recipients."""
    recipients = _normalize_recipients(recipient)
    task = await create_task(
        description=f"Send form {form_id or '[new-form]'} via {channel} to {recipients or ['pending_recipient']}"
    )
    await _audit_event(
        "send_form",
        "forms",
        {"form_id": form_id, "channel": channel, "recipients": recipients, "kwargs": kwargs},
    )
    return {"success": True, "status": "completed", "tool": "send_form", "task": task}
