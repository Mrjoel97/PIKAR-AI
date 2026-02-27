# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Workflow step executor: maps workflow context to tool parameters.

Ensures tools invoked by the workflow engine receive the correct arguments
from context (initiative_id, desired_outcomes, timeline, topic, etc.) instead
of raw **kwargs that cause TypeErrors.
"""

import inspect
import logging
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


def _get(ctx: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """First non-None value from context for the given keys."""
    for k in keys:
        v = ctx.get(k)
        if v is not None and (not isinstance(v, str) or v.strip()):
            return v
    return default


def _str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip() or ""


def build_context_derived_kwargs(
    tool_name: str,
    context: Dict[str, Any],
    step_name: str = "",
    step_description: str = "",
) -> Dict[str, Any]:
    """Build a candidate kwargs dict from workflow context for the given tool.

    Uses initiative_id, desired_outcomes, timeline, topic, user_id when present.
    Step name/description are used as fallbacks for title, description, query, etc.
    """
    c = context
    topic = _str(_get(c, "topic", default=""))
    outcomes = _str(_get(c, "desired_outcomes", default=""))
    timeline = _str(_get(c, "timeline", default=""))
    initiative_id = _get(c, "initiative_id")
    user_id = _get(c, "user_id")
    desc = _str(step_description or outcomes or topic)
    title = _str(step_name or topic or "Workflow step")

    # Per-tool mapping: context keys -> parameter names and values
    # Only include keys that the tool actually accepts (filtered later).
    candidates: Dict[str, Any] = {}

    if tool_name == "create_initiative":
        candidates["title"] = title or "Workflow initiative"
        candidates["description"] = desc or "Created from workflow"
        candidates["priority"] = _get(c, "priority", default="medium")

    elif tool_name == "get_initiative":
        if initiative_id:
            candidates["initiative_id"] = initiative_id
        else:
            candidates["initiative_id"] = _get(c, "initiative_id")  # may be None; tool will error

    elif tool_name == "update_initiative":
        if initiative_id:
            candidates["initiative_id"] = initiative_id
        candidates["desired_outcomes"] = outcomes or None
        candidates["timeline"] = timeline or None
        candidates["status"] = _get(c, "status")
        candidates["progress"] = _get(c, "progress")
        candidates["phase"] = _get(c, "phase")
        candidates["title"] = _get(c, "title") or title
        candidates["description"] = _get(c, "description") or desc

    elif tool_name in ("list_initiatives", "list_initiative_templates"):
        candidates["status"] = _get(c, "status")
        candidates["phase"] = _get(c, "phase")
        if tool_name == "list_initiative_templates":
            candidates["persona"] = _get(c, "persona")

    elif tool_name == "start_initiative_from_idea":
        candidates["idea"] = topic or outcomes or desc
        candidates["context"] = desc

    elif tool_name == "advance_initiative_phase":
        if initiative_id:
            candidates["initiative_id"] = initiative_id

    elif tool_name == "start_journey_workflow":
        if initiative_id:
            candidates["initiative_id"] = initiative_id

    elif tool_name == "create_task":
        candidates["description"] = desc or title or "Workflow task"

    elif tool_name == "send_email":
        candidates["to"] = _get(c, "to") or _get(c, "recipients") or []
        candidates["subject"] = _get(c, "subject") or title or "Workflow update"
        candidates["body"] = _get(c, "body") or desc or "Workflow notification"

    elif tool_name == "create_document":
        candidates["title"] = _get(c, "title") or title or "Workflow Document"
        candidates["content"] = _get(c, "content") or desc or outcomes or topic or ""

    elif tool_name in ("schedule_meeting", "schedule_call", "schedule_interview", "create_calendar_events"):
        candidates["title"] = _get(c, "title") or title or "Workflow Meeting"
        candidates["attendees"] = _get(c, "attendees") or _get(c, "to") or []
        candidates["start_time"] = _get(c, "start_time")

    elif tool_name == "create_spreadsheet":
        candidates["title"] = _get(c, "title") or title or "Workflow Spreadsheet"

    elif tool_name == "process_payment":
        candidates["amount"] = _get(c, "amount")
        candidates["currency"] = _get(c, "currency", default="usd")
        candidates["description"] = _get(c, "description") or desc or "Workflow payment"
        candidates["customer_email"] = _get(c, "customer_email") or _get(c, "email")

    elif tool_name == "send_payment":
        candidates["payee"] = _get(c, "payee") or _get(c, "vendor") or _get(c, "recipient") or "Vendor"
        candidates["amount"] = _get(c, "amount")
        candidates["currency"] = _get(c, "currency", default="usd")
        candidates["reference"] = _get(c, "reference") or _get(c, "invoice_number")

    elif tool_name == "transfer_money":
        candidates["from_account"] = _get(c, "from_account") or "operating"
        candidates["to_account"] = _get(c, "to_account") or "reserve"
        candidates["amount"] = _get(c, "amount")
        candidates["currency"] = _get(c, "currency", default="usd")

    elif tool_name == "send_contract":
        candidates["recipient_email"] = _get(c, "recipient_email") or _get(c, "email") or _get(c, "to")
        candidates["recipient_name"] = _get(c, "recipient_name") or _get(c, "name")
        candidates["contract_title"] = _get(c, "contract_title") or title or "Agreement"
        candidates["contract_body"] = _get(c, "contract_body") or desc or "Standard terms"
        candidates["effective_date"] = _get(c, "effective_date")

    elif tool_name == "approve_request":
        candidates["request_type"] = _get(c, "request_type") or title or "workflow_request"
        candidates["requester"] = _get(c, "requester") or _get(c, "requested_by") or "workflow-user"
        candidates["justification"] = _get(c, "justification") or desc
        candidates["amount"] = _get(c, "amount")
        candidates["approver"] = _get(c, "approver")
        candidates["priority"] = _get(c, "priority", default="normal")

    elif tool_name == "query_timesheets":
        candidates["pay_period"] = _get(c, "pay_period") or _get(c, "period") or timeline or "current_month"
        candidates["department"] = _get(c, "department")

    elif tool_name == "execute_payroll":
        candidates["pay_period"] = _get(c, "pay_period") or _get(c, "period") or timeline or "current_month"
        candidates["total_amount"] = _get(c, "total_amount") or _get(c, "amount")
        candidates["currency"] = _get(c, "currency", default="usd")
        candidates["approved_by"] = _get(c, "approved_by") or _get(c, "approver")

    elif tool_name == "publish_page":
        candidates["user_id"] = _get(c, "user_id")
        candidates["page_id"] = _get(c, "page_id")

    elif tool_name in ("get_task", "update_task"):
        candidates["task_id"] = _get(c, "task_id")
        if tool_name == "update_task":
            candidates["status"] = _get(c, "status", default="in_progress")

    elif tool_name == "list_tasks":
        candidates["status"] = _get(c, "status")

    elif tool_name == "save_content":
        candidates["title"] = title or "Workflow content"
        candidates["content"] = desc or outcomes or topic or "(No content)"

    elif tool_name in ("get_content", "update_content"):
        candidates["content_id"] = _get(c, "content_id")
        if tool_name == "update_content":
            candidates["title"] = _get(c, "title") or title
            candidates["content"] = _get(c, "content") or desc

    elif tool_name == "list_content":
        candidates["content_type"] = _get(c, "content_type")

    elif tool_name == "track_event":
        candidates["event_name"] = _str(step_name or "workflow_step")
        candidates["category"] = _get(c, "category", default="workflow")
        props = _get(c, "properties")
        if props is None and (topic or outcomes):
            import json
            candidates["properties"] = json.dumps({"topic": topic, "desired_outcomes": outcomes[:500]})
        else:
            candidates["properties"] = props

    elif tool_name == "query_events":
        candidates["event_name"] = _get(c, "event_name")
        candidates["category"] = _get(c, "category", default="workflow")
        candidates["limit"] = _get(c, "limit", default=100)

    elif tool_name == "create_report":
        candidates["title"] = title or "Workflow report"
        candidates["report_type"] = _get(c, "report_type", default="workflow")
        import json
        candidates["data"] = json.dumps({k: v for k, v in c.items() if k not in ("user_id",)})
        candidates["description"] = desc or None

    elif tool_name == "list_reports":
        candidates["report_type"] = _get(c, "report_type")

    elif tool_name == "get_revenue_stats":
        candidates["period"] = _get(c, "period", default="current_month")

    elif tool_name in ("mcp_web_search", "mcp_web_scrape"):
        candidates["query"] = topic or desc or title or "workflow research"
        if tool_name == "mcp_web_search":
            candidates["max_results"] = _get(c, "max_results", default=5)
            candidates["search_depth"] = _get(c, "search_depth", default="basic")

    elif tool_name in ("deep_research", "quick_research", "market_research", "competitor_research"):
        candidates["topic"] = topic or desc or title or "workflow research"
        if user_id:
            candidates["user_id"] = user_id
        if tool_name == "deep_research":
            candidates["research_type"] = _get(c, "research_type", default="comprehensive")
            candidates["depth"] = _get(c, "depth", default="deep")
        if tool_name == "competitor_research":
            candidates["competitors"] = _get(c, "competitors")

    elif tool_name == "add_business_knowledge":
        candidates["content"] = outcomes or desc or topic or "Workflow context"
        candidates["title"] = title or "Workflow knowledge"
        candidates["category"] = _get(c, "category")

    elif tool_name in ("add_product_info", "add_company_info", "add_process_or_policy", "add_faq"):
        candidates["content"] = outcomes or desc or topic or ""
        candidates["title"] = title or tool_name.replace("_", " ").title()

    elif tool_name == "create_campaign":
        candidates["name"] = title or topic or "Workflow campaign"
        candidates["campaign_type"] = _get(c, "campaign_type", default="marketing")
        candidates["target_audience"] = outcomes or _get(c, "target_audience", default="General")

    elif tool_name in (
        "send_message",
        "start_call",
        "listen_call",
        "run_script",
        "run_deployment",
        "update_hris",
        "process_forms",
        "update_code",
        "train_model",
        "deploy_service",
        "create_connection",
        "create_query",
        "create_table",
        "create_chart",
        "process_data",
        "grant_access",
        "audit_logs",
        "check_logs",
        "create_folder",
        "create_project",
        "analyze_sentiment",
        "setup_monitoring",
        "configure_ads",
        "optimize_spend",
        "create_contact",
        "score_lead",
        "query_crm",
        "generate_forecast",
        "create_forecast",
        "create_vendor",
        "update_inventory",
        "create_po",
        "log_shipment",
        "verify_po",
        "book_travel",
        "process_expense",
        "assign_training",
        "post_job_board",
        "query_analytics",
        "query_usage",
        "create_alert",
        "update_subscription",
        "ocr_document",
        "upload_document",
        "upload_file",
        "run_audit",
        "run_test",
        "test_scenario",
        "create_checklist",
        "run_checklist",
        "create_task_list",
        "record_notes",
    ):
        candidates["name"] = _get(c, "name") or _get(c, "title") or title or "Workflow artifact"
        candidates["title"] = _get(c, "title") or title or "Workflow artifact"
        candidates["subject"] = _get(c, "subject") or title or "Workflow message"
        candidates["description"] = _get(c, "description") or desc or "Workflow generated action"
        candidates["body"] = _get(c, "body") or desc or outcomes or topic
        candidates["to"] = _get(c, "to") or _get(c, "recipients") or []
        candidates["channel"] = _get(c, "channel", default="email")
        candidates["participant"] = _get(c, "participant") or _get(c, "name")
        candidates["purpose"] = _get(c, "purpose") or desc or title
        candidates["when"] = _get(c, "when") or _get(c, "start_time") or timeline
        candidates["call_id"] = _get(c, "call_id")
        candidates["notes"] = _get(c, "notes") or desc
        candidates["script_name"] = _get(c, "script_name") or _get(c, "name") or title
        candidates["args"] = _get(c, "args") or []
        candidates["service"] = _get(c, "service") or _get(c, "service_name")
        candidates["environment"] = _get(c, "environment") or _get(c, "env") or "staging"
        candidates["version"] = _get(c, "version")
        candidates["employee_id"] = _get(c, "employee_id")
        candidates["update_type"] = _get(c, "update_type")
        candidates["payload"] = _get(c, "payload")
        candidates["form_name"] = _get(c, "form_name") or _get(c, "name")
        candidates["submission_id"] = _get(c, "submission_id")
        candidates["repo"] = _get(c, "repo") or _get(c, "repository")
        candidates["branch"] = _get(c, "branch") or "main"
        candidates["summary"] = _get(c, "summary") or desc
        candidates["model_name"] = _get(c, "model_name") or _get(c, "name")
        candidates["dataset"] = _get(c, "dataset")
        candidates["service_name"] = _get(c, "service_name") or _get(c, "service")
        candidates["connection_name"] = _get(c, "connection_name") or _get(c, "name")
        candidates["connection_type"] = _get(c, "connection_type", default="supabase")
        candidates["query"] = _get(c, "query") or _get(c, "sql") or topic or desc
        candidates["columns"] = _get(c, "columns")
        candidates["chart_type"] = _get(c, "chart_type") or _get(c, "type") or "bar"
        candidates["data_query"] = _get(c, "data_query") or _get(c, "query")
        candidates["pipeline_name"] = _get(c, "pipeline_name") or _get(c, "name")
        candidates["input_source"] = _get(c, "input_source") or _get(c, "source")
        candidates["operation"] = _get(c, "operation")
        candidates["resource"] = _get(c, "resource")
        candidates["principal"] = _get(c, "principal") or _get(c, "user")
        candidates["role"] = _get(c, "role")
        candidates["tool_name"] = _get(c, "tool_name")
        candidates["content"] = _get(c, "content") or desc or outcomes or topic
        candidates["message"] = _get(c, "message") or desc or title
        candidates["context"] = _get(c, "context") or desc or outcomes or topic
        candidates["query"] = _get(c, "query") or topic or desc
        candidates["target_audience"] = _get(c, "target_audience") or outcomes or "General"
        candidates["lead_name"] = _get(c, "lead_name") or _get(c, "name") or title
        candidates["email"] = _get(c, "email")
        candidates["vendor"] = _get(c, "vendor") or _get(c, "name")
        candidates["item"] = _get(c, "item") or _get(c, "resource")
        candidates["reference"] = _get(c, "reference") or _get(c, "invoice_number") or _get(c, "po_number")
        candidates["traveler"] = _get(c, "traveler") or _get(c, "name")
        candidates["itinerary"] = _get(c, "itinerary") or timeline
        candidates["expense_title"] = _get(c, "expense_title") or title
        candidates["training_name"] = _get(c, "training_name") or title
        candidates["assignee"] = _get(c, "assignee") or _get(c, "owner")
        candidates["role"] = _get(c, "role") or title
        candidates["event_name"] = _get(c, "event_name")
        candidates["severity"] = _get(c, "severity", default="info")
        candidates["plan"] = _get(c, "plan") or _get(c, "subscription_plan")
        candidates["status"] = _get(c, "status")
        candidates["scope"] = _get(c, "scope") or "workflow"
        candidates["score"] = _get(c, "score")
        candidates["quantity"] = _get(c, "quantity")
        candidates["amount"] = _get(c, "amount")
        candidates["limit"] = _get(c, "limit", default=100)

    elif tool_name in ("get_campaign", "update_campaign", "record_campaign_metrics"):
        candidates["campaign_id"] = _get(c, "campaign_id")
        if tool_name == "update_campaign":
            candidates["status"] = _get(c, "status")
            candidates["name"] = _get(c, "name")
        if tool_name == "record_campaign_metrics":
            candidates["impressions"] = _get(c, "impressions", default=0)
            candidates["clicks"] = _get(c, "clicks", default=0)
            candidates["conversions"] = _get(c, "conversions", default=0)

    elif tool_name == "list_campaigns":
        candidates["status"] = _get(c, "status")
        candidates["campaign_type"] = _get(c, "campaign_type")

    else:
        # Generic: pass through common keys; filter by signature in build_tool_kwargs
        for key in ("initiative_id", "topic", "desired_outcomes", "timeline", "query", "title", "description", "content", "user_id"):
            if key in c and c[key] is not None:
                candidates[key] = c[key]
        if not candidates and (topic or desc):
            candidates["query"] = topic or desc
            candidates["topic"] = topic or desc
            candidates["title"] = title
            candidates["description"] = desc

    return candidates


def build_tool_kwargs(
    tool_fn: Callable,
    tool_name: str,
    context: Dict[str, Any],
    step_name: str = "",
    step_description: str = "",
) -> Dict[str, Any]:
    """Build kwargs for the given tool from workflow context.

    - Derives candidate kwargs from context (initiative_id, topic, desired_outcomes, etc.).
    - Filters to only parameter names the tool accepts.
    - Drops None values for optional params so tool defaults apply (unless the tool requires them).
    """
    try:
        sig = inspect.signature(tool_fn)
    except (ValueError, TypeError) as e:
        # Some callables don't support signature inspection
        logger.debug(f"Could not get signature for tool {tool_name}: {e}")
        sig = None
    param_names = set(sig.parameters.keys()) if sig else set()

    candidates = build_context_derived_kwargs(tool_name, context, step_name, step_description)

    out: Dict[str, Any] = {}
    for name, value in candidates.items():
        if name not in param_names:
            continue
        if value is None:
            param = sig.parameters.get(name) if sig else None
            if param is not None and param.default is inspect.Parameter.empty:
                continue  # required param missing; skip so tool will get TypeError with clear message
        out[name] = value

    return out
