# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Degraded workflow tool implementations that create real artifacts.

These tools intentionally avoid external service dependencies while still
producing durable records (tasks/content/reports/audits/events) so workflow
executions are observable and useful.
"""

import json
from datetime import date

from app.agents.compliance.tools import create_audit
from app.agents.content.tools import save_content
from app.agents.data.tools import create_report, query_events, track_event
from app.agents.marketing.tools import create_campaign
from app.agents.sales.tools import create_task
from app.agents.strategic.tools import create_initiative
from app.agents.tools.deep_research import quick_research


def _props(payload: dict) -> str:
    return json.dumps(payload, default=str)


async def _audit_event(event_name: str, category: str, payload: dict) -> None:
    await track_event(
        event_name=event_name, category=category, properties=_props(payload)
    )


async def create_folder(name: str = "Workflow Folder", **kwargs) -> dict:
    artifact = await save_content(
        title=f"Folder: {name}", content=f"Created logical folder '{name}'."
    )
    await _audit_event("create_folder", "content", {"name": name, "kwargs": kwargs})
    return {
        "success": True,
        "status": "degraded_completed",
        "artifact": artifact,
        "tool": "create_folder",
    }


async def create_project(
    name: str = "Workflow Project", description: str = "", **kwargs
) -> dict:
    artifact = await create_initiative(
        title=name, description=description or f"Project created by workflow: {name}"
    )
    await _audit_event("create_project", "operations", {"name": name, "kwargs": kwargs})
    return {
        "success": True,
        "status": "degraded_completed",
        "artifact": artifact,
        "tool": "create_project",
    }


async def analyze_sentiment(query: str = "", **kwargs) -> dict:
    research = await quick_research(
        topic=f"sentiment analysis: {query or 'workflow context'}"
    )
    await _audit_event(
        "analyze_sentiment", "research", {"query": query, "kwargs": kwargs}
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "research": research,
        "tool": "analyze_sentiment",
    }


async def setup_monitoring(description: str = "Setup monitoring", **kwargs) -> dict:
    task = await create_task(description=f"Setup monitoring: {description}")
    await _audit_event(
        "setup_monitoring", "operations", {"description": description, "kwargs": kwargs}
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "setup_monitoring",
    }


async def configure_ads(
    name: str = "Ad Campaign", target_audience: str = "General audience", **kwargs
) -> dict:
    campaign = await create_campaign(
        name=name, campaign_type="paid_ads", target_audience=target_audience
    )
    await _audit_event(
        "configure_ads", "marketing", {"name": name, "target_audience": target_audience}
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "campaign": campaign,
        "tool": "configure_ads",
    }


async def optimize_spend(
    name: str = "Spend Optimization",
    target_audience: str = "General audience",
    **kwargs,
) -> dict:
    campaign = await create_campaign(
        name=name, campaign_type="optimization", target_audience=target_audience
    )
    await _audit_event(
        "optimize_spend",
        "marketing",
        {"name": name, "target_audience": target_audience},
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "campaign": campaign,
        "tool": "optimize_spend",
    }


async def create_contact(
    name: str = "New Contact", email: str | None = None, **kwargs
) -> dict:
    task = await create_task(
        description=f"CRM: create contact '{name}' ({email or 'no-email'})"
    )
    await _audit_event(
        "create_contact", "crm", {"name": name, "email": email, "kwargs": kwargs}
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "create_contact",
    }


async def score_lead(
    lead_name: str = "Lead", score: int | None = None, **kwargs
) -> dict:
    task = await create_task(
        description=f"CRM: score lead '{lead_name}' with score={score if score is not None else 'n/a'}"
    )
    await _audit_event(
        "score_lead", "crm", {"lead_name": lead_name, "score": score, "kwargs": kwargs}
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "score_lead",
    }


async def query_crm(limit: int = 50, **kwargs) -> dict:
    events = await query_events(category="crm", limit=limit)
    await _audit_event("query_crm", "crm", {"limit": limit, "kwargs": kwargs})
    return {
        "success": True,
        "status": "degraded_completed",
        "results": events,
        "tool": "query_crm",
    }


# DEPRECATED: Real implementation in app/services/forecast_service.py (Phase 60 FIN-06)
# Registry entries now point to _real_generate_forecast in registry.py.
async def generate_forecast(
    title: str = "Forecast", context: str = "", **kwargs
) -> dict:
    report = await create_report(
        title=f"Forecast: {title}",
        report_type="forecast",
        data=_props({"context": context, "inputs": kwargs}),
        description="Generated by degraded forecast tool",
    )
    await _audit_event(
        "generate_forecast", "finance", {"title": title, "context": context}
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "report": report,
        "tool": "generate_forecast",
    }


# DEPRECATED: Real implementation in app/services/forecast_service.py (Phase 60 FIN-06)
# Registry entries now point to _real_create_forecast in registry.py.
async def create_forecast(title: str = "Forecast", context: str = "", **kwargs) -> dict:
    return await generate_forecast(title=title, context=context, **kwargs)


async def create_vendor(name: str = "Vendor", **kwargs) -> dict:
    task = await create_task(description=f"Vendor onboarding: {name}")
    await _audit_event("create_vendor", "operations", {"name": name, "kwargs": kwargs})
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "create_vendor",
    }


async def update_inventory(
    item: str = "Inventory item", quantity: int | None = None, **kwargs
) -> dict:
    task = await create_task(
        description=f"Operations: update inventory for {item} quantity={quantity if quantity is not None else 'n/a'}"
    )
    await _audit_event(
        "update_inventory",
        "operations",
        {"item": item, "quantity": quantity, "kwargs": kwargs},
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "update_inventory",
    }


async def create_po(
    vendor: str = "Vendor", amount: float | None = None, **kwargs
) -> dict:
    task = await create_task(
        description=f"Operations: create PO for {vendor}, amount={amount if amount is not None else 'n/a'}"
    )
    await _audit_event(
        "create_po",
        "operations",
        {"vendor": vendor, "amount": amount, "kwargs": kwargs},
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "create_po",
    }


async def log_shipment(reference: str = "shipment", **kwargs) -> dict:
    task = await create_task(description=f"Operations: log shipment {reference}")
    await _audit_event(
        "log_shipment", "operations", {"reference": reference, "kwargs": kwargs}
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "log_shipment",
    }


async def verify_po(reference: str = "po", **kwargs) -> dict:
    task = await create_task(description=f"Operations: verify PO {reference}")
    await _audit_event(
        "verify_po", "operations", {"reference": reference, "kwargs": kwargs}
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "verify_po",
    }


async def book_travel(
    traveler: str = "Team member", itinerary: str = "", **kwargs
) -> dict:
    task = await create_task(
        description=f"Travel: book travel for {traveler}. {itinerary}".strip()
    )
    await _audit_event(
        "book_travel",
        "operations",
        {"traveler": traveler, "itinerary": itinerary, "kwargs": kwargs},
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "book_travel",
    }


async def process_expense(
    expense_title: str = "Expense", amount: float | None = None, **kwargs
) -> dict:
    task = await create_task(
        description=f"Expense: process {expense_title}, amount={amount if amount is not None else 'n/a'}"
    )
    await _audit_event(
        "process_expense",
        "finance",
        {"expense_title": expense_title, "amount": amount, "kwargs": kwargs},
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "process_expense",
    }


async def assign_training(
    training_name: str = "Training Module", assignee: str = "Team", **kwargs
) -> dict:
    task = await create_task(
        description=f"Training: assign '{training_name}' to {assignee}"
    )
    await _audit_event(
        "assign_training",
        "hr",
        {"training_name": training_name, "assignee": assignee, "kwargs": kwargs},
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "assign_training",
    }


async def post_job_board(role: str = "Open Role", **kwargs) -> dict:
    task = await create_task(description=f"Job posting: publish role '{role}'")
    await _audit_event("post_job_board", "hr", {"role": role, "kwargs": kwargs})
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "post_job_board",
    }


async def query_analytics(
    event_name: str | None = None, limit: int = 100, **kwargs
) -> dict:
    events = await query_events(
        event_name=event_name, category="analytics", limit=limit
    )
    await _audit_event(
        "query_analytics",
        "analytics",
        {"event_name": event_name, "limit": limit, "kwargs": kwargs},
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "results": events,
        "tool": "query_analytics",
    }


async def query_usage(
    event_name: str | None = None, limit: int = 100, **kwargs
) -> dict:
    events = await query_events(event_name=event_name, category="usage", limit=limit)
    await _audit_event(
        "query_usage",
        "analytics",
        {"event_name": event_name, "limit": limit, "kwargs": kwargs},
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "results": events,
        "tool": "query_usage",
    }


async def create_alert(
    message: str = "Workflow alert", severity: str = "info", **kwargs
) -> dict:
    task = await create_task(description=f"Alert [{severity}]: {message}")
    await _audit_event(
        "create_alert",
        "operations",
        {"message": message, "severity": severity, "kwargs": kwargs},
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "create_alert",
    }


async def update_subscription(
    plan: str = "default", status: str = "updated", **kwargs
) -> dict:
    await _audit_event(
        "subscription_update",
        "billing",
        {"plan": plan, "status": status, "kwargs": kwargs},
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "message": f"Subscription marked as {status} for plan {plan}",
        "tool": "update_subscription",
    }


async def upload_document(name: str = "document", content: str = "", **kwargs) -> dict:
    artifact = await save_content(
        title=f"Document: {name}", content=content or f"Uploaded document '{name}'."
    )
    await _audit_event("upload_document", "content", {"name": name, "kwargs": kwargs})
    return {
        "success": True,
        "status": "degraded_completed",
        "artifact": artifact,
        "tool": "upload_document",
    }


async def upload_file(name: str = "file", content: str = "", **kwargs) -> dict:
    artifact = await save_content(
        title=f"Document: {name}", content=content or f"Uploaded file '{name}'."
    )
    await _audit_event("upload_file", "content", {"name": name, "kwargs": kwargs})
    return {
        "success": True,
        "status": "degraded_completed",
        "artifact": artifact,
        "tool": "upload_file",
    }


async def ocr_document(
    name: str = "document", extracted_text: str = "", **kwargs
) -> dict:
    artifact = await save_content(
        title=f"Document OCR: {name}",
        content=extracted_text or f"OCR extraction completed for '{name}'.",
    )
    await _audit_event("ocr_document", "content", {"name": name, "kwargs": kwargs})
    return {
        "success": True,
        "status": "degraded_completed",
        "artifact": artifact,
        "tool": "ocr_document",
    }


async def run_audit(
    title: str = "Workflow Audit", scope: str = "workflow", **kwargs
) -> dict:
    audit = await create_audit(
        title=title,
        scope=scope,
        auditor="workflow-engine",
        scheduled_date=date.today().isoformat(),
    )
    await _audit_event(
        "run_audit", "compliance", {"title": title, "scope": scope, "kwargs": kwargs}
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "audit": audit,
        "tool": "run_audit",
    }


async def run_test(name: str = "Workflow Test", **kwargs) -> dict:
    task = await create_task(description=f"Test: {name}")
    await _audit_event("run_test", "quality", {"name": name, "kwargs": kwargs})
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "run_test",
    }


async def test_scenario(name: str = "Scenario Test", **kwargs) -> dict:
    task = await create_task(description=f"Test scenario: {name}")
    await _audit_event("test_scenario", "quality", {"name": name, "kwargs": kwargs})
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "test_scenario",
    }


async def create_checklist(name: str = "Checklist", **kwargs) -> dict:
    task = await create_task(description=f"Checklist: create '{name}'")
    await _audit_event(
        "create_checklist", "operations", {"name": name, "kwargs": kwargs}
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "create_checklist",
    }


async def run_checklist(name: str = "Checklist", **kwargs) -> dict:
    task = await create_task(description=f"Checklist: run '{name}'")
    await _audit_event("run_checklist", "operations", {"name": name, "kwargs": kwargs})
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "run_checklist",
    }


async def create_task_list(name: str = "Task List", **kwargs) -> dict:
    task = await create_task(description=f"Task list: create '{name}'")
    await _audit_event(
        "create_task_list", "operations", {"name": name, "kwargs": kwargs}
    )
    return {
        "success": True,
        "status": "degraded_completed",
        "task": task,
        "tool": "create_task_list",
    }


async def record_notes(
    title: str = "Workflow Notes", content: str = "", **kwargs
) -> dict:
    artifact = await save_content(
        title=f"Notes: {title}",
        content=content or "Notes captured during workflow execution.",
    )
    await _audit_event("record_notes", "content", {"title": title, "kwargs": kwargs})
    return {
        "success": True,
        "status": "degraded_completed",
        "artifact": artifact,
        "tool": "record_notes",
    }
