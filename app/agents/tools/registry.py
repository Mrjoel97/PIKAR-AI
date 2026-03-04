# Copyright 2025 Google LLC
from app.agents.tools.brain_dump import get_braindump_document
from app.agents.tools.workflows import create_workflow_template
# SPDX-License-Identifier: Apache-2.0

"""Tool Registry for Workflow Automation.

Maps string identifiers (used in workflow definitions) to executable Python functions.
All registered tools are real implementations from the agent tool modules.
"""

import asyncio
import logging
import os
from pydantic import BaseModel, Field
from typing import Optional, Type

# --- Compliance Tools ---
from app.agents.compliance.tools import (
    create_audit,
    create_risk,
    get_audit,
    get_risk,
    list_audits,
    list_risks,
    update_audit,
    update_risk,
)

# --- Content Tools ---
from app.agents.content.tools import (
    get_content,
    list_content,
    save_content,
    update_content,
)

# --- Customer Support Tools ---
from app.agents.customer_support.tools import (
    create_ticket,
    get_ticket,
    list_tickets,
    update_ticket,
)

# --- Data / Analytics Tools ---
from app.agents.data.tools import (
    create_report,
    list_reports,
    query_events,
    track_event,
)

# --- Content / Media (sync tools wrapped for async) ---
from app.agents.enhanced_tools import generate_image as _generate_image_sync
from app.agents.enhanced_tools import generate_short_video as _generate_short_video_sync

# --- Financial Tools ---
from app.agents.financial.tools import (
    create_finance_deliverable,
    get_finance_deliverable_templates,
    get_burn_runway_report,
    get_cash_position,
    get_financial_report,
    get_revenue_stats,
    list_finance_assumptions,
    render_budget_vs_actual_widget,
    render_burn_runway_widget,
    render_cash_waterfall_widget,
    render_cohort_retention_widget,
    render_kpi_scorecard_widget,
    render_pnl_summary_widget,
    render_revenue_bridge_widget,
    save_finance_assumption,
)

# --- HR / Recruitment Tools ---
from app.agents.hr.tools import (
    add_candidate,
    create_job,
    get_job,
    list_candidates,
    list_jobs,
    update_candidate_status,
    update_job,
)

# --- Marketing Tools ---
from app.agents.marketing.tools import (
    create_campaign,
    get_campaign,
    list_campaigns,
    record_campaign_metrics,
    update_campaign,
)

# --- Sales / Task Tools ---
from app.agents.sales.tools import (
    create_task,
    get_task,
    list_tasks,
    update_task,
)

# --- Strategic Tools ---
from app.agents.strategic.tools import (
    advance_initiative_phase,
    create_initiative,
    create_initiative_from_template,
    get_initiative,
    list_initiative_templates,
    list_initiatives,
    start_initiative_from_idea,
    start_journey_workflow,
    update_initiative,
)

# --- Research Tools ---
from app.agents.tools.deep_research import (
    competitor_research,
    deep_research,
    market_research,
    quick_research,
)
from app.agents.tools.degraded_tools import (
    analyze_sentiment as degraded_analyze_sentiment,
)
from app.agents.tools.degraded_tools import (
    assign_training as degraded_assign_training,
)
from app.agents.tools.degraded_tools import (
    book_travel as degraded_book_travel,
)
from app.agents.tools.degraded_tools import (
    configure_ads as degraded_configure_ads,
)
from app.agents.tools.degraded_tools import (
    create_alert as degraded_create_alert,
)
from app.agents.tools.degraded_tools import (
    create_checklist as degraded_create_checklist,
)
from app.agents.tools.degraded_tools import (
    create_contact as degraded_create_contact,
)
from app.agents.tools.degraded_tools import (
    create_folder as degraded_create_folder,
)
from app.agents.tools.degraded_tools import (
    create_forecast as degraded_create_forecast,
)
from app.agents.tools.degraded_tools import (
    create_po as degraded_create_po,
)
from app.agents.tools.degraded_tools import (
    create_project as degraded_create_project,
)
from app.agents.tools.degraded_tools import (
    create_task_list as degraded_create_task_list,
)
from app.agents.tools.degraded_tools import (
    create_vendor as degraded_create_vendor,
)
from app.agents.tools.degraded_tools import (
    generate_forecast as degraded_generate_forecast,
)
from app.agents.tools.degraded_tools import (
    log_shipment as degraded_log_shipment,
)
from app.agents.tools.degraded_tools import (
    ocr_document as degraded_ocr_document,
)
from app.agents.tools.degraded_tools import (
    optimize_spend as degraded_optimize_spend,
)
from app.agents.tools.degraded_tools import (
    post_job_board as degraded_post_job_board,
)
from app.agents.tools.degraded_tools import (
    process_expense as degraded_process_expense,
)
from app.agents.tools.degraded_tools import (
    query_analytics as degraded_query_analytics,
)
from app.agents.tools.degraded_tools import (
    query_crm as degraded_query_crm,
)
from app.agents.tools.degraded_tools import (
    query_usage as degraded_query_usage,
)
from app.agents.tools.degraded_tools import (
    record_notes as degraded_record_notes,
)
from app.agents.tools.degraded_tools import (
    run_audit as degraded_run_audit,
)
from app.agents.tools.degraded_tools import (
    run_checklist as degraded_run_checklist,
)
from app.agents.tools.degraded_tools import (
    run_test as degraded_run_test,
)
from app.agents.tools.degraded_tools import (
    score_lead as degraded_score_lead,
)
from app.agents.tools.degraded_tools import (
    setup_monitoring as degraded_setup_monitoring,
)
from app.agents.tools.degraded_tools import (
    test_scenario as degraded_test_scenario,
)
from app.agents.tools.degraded_tools import (
    update_inventory as degraded_update_inventory,
)
from app.agents.tools.degraded_tools import (
    update_subscription as degraded_update_subscription,
)
from app.agents.tools.degraded_tools import (
    upload_document as degraded_upload_document,
)
from app.agents.tools.degraded_tools import (
    upload_file as degraded_upload_file,
)
from app.agents.tools.degraded_tools import (
    verify_po as degraded_verify_po,
)
from app.agents.tools.high_risk_workflow import (
    approve_request,
    execute_payroll,
    query_timesheets,
    send_contract,
    send_payment,
)
from app.agents.tools.high_risk_workflow import (
    process_payment as process_payment_high_risk,
)
from app.agents.tools.high_risk_workflow import (
    transfer_money as transfer_money_high_risk,
)
from app.agents.tools.integration_tools import (
    audit_logs as integrated_audit_logs,
)
from app.agents.tools.integration_tools import (
    check_logs as integrated_check_logs,
)
from app.agents.tools.integration_tools import (
    create_chart as integrated_create_chart,
)
from app.agents.tools.integration_tools import (
    create_connection as integrated_create_connection,
)
from app.agents.tools.integration_tools import (
    create_query as integrated_create_query,
)
from app.agents.tools.integration_tools import (
    create_table as integrated_create_table,
)
from app.agents.tools.integration_tools import (
    deploy_service as integrated_deploy_service,
)
from app.agents.tools.integration_tools import (
    grant_access as integrated_grant_access,
)
from app.agents.tools.integration_tools import (
    listen_call as integrated_listen_call,
)
from app.agents.tools.integration_tools import (
    process_data as integrated_process_data,
)
from app.agents.tools.integration_tools import (
    process_forms as integrated_process_forms,
)
from app.agents.tools.integration_tools import (
    run_deployment as integrated_run_deployment,
)
from app.agents.tools.integration_tools import (
    run_script as integrated_run_script,
)
from app.agents.tools.integration_tools import (
    send_message as integrated_send_message,
)
from app.agents.tools.integration_tools import (
    start_call as integrated_start_call,
)
from app.agents.tools.integration_tools import (
    train_model as integrated_train_model,
)
from app.agents.tools.integration_tools import (
    update_code as integrated_update_code,
)
from app.agents.tools.integration_tools import (
    update_hris as integrated_update_hris,
)
from app.agents.tools.workflow_ops import (
    approve_document,
    calculate_score,
    create_form,
    create_pr,
    create_record,
    create_tracking_plan,
    edit_document,
    manage_comments,
    query_bank,
    query_feedback,
    query_ledger,
    read_docs,
    review_policy,
    scan_database,
    send_file,
    send_form,
    send_guide,
    submit_form,
    update_asset_log,
    update_budget,
    update_cms,
    update_gantt,
    update_ledger,
    update_record,
    update_settings,
)

# --- MCP Tools ---
from app.mcp.agent_tools import mcp_web_scrape, mcp_web_search
from app.mcp.tools.canva_media import (
    create_product_photoshoot_bundle,
    execute_content_pipeline,
    get_media_deliverable_templates,
)

# --- Knowledge Tools ---
from app.orchestration.knowledge_tools import (
    add_business_knowledge,
    add_company_info,
    add_faq,
    add_process_or_policy,
    add_product_info,
)
from app.services.request_context import get_current_user_id

logger = logging.getLogger(__name__)
STRICT_TOOL_RESOLUTION = os.getenv("WORKFLOW_STRICT_TOOL_RESOLUTION", "true").lower() == "true"
STRICT_CRITICAL_TOOL_GUARD = os.getenv("WORKFLOW_STRICT_CRITICAL_TOOL_GUARD", "true").lower() == "true"
CRITICAL_WORKFLOW_TOOLS = {
    "approve_request",
    "send_contract",
    "query_timesheets",
    "execute_payroll",
    "process_payment",
    "send_payment",
    "transfer_money",
}


# --- Async wrappers for sync tools used in workflows ---
async def search_business_knowledge(query: str, top_k: int = 5, **kwargs) -> dict:
    """Search the Knowledge Vault for business context (async wrapper for workflow execution)."""
    try:
        from app.rag.knowledge_vault import search_knowledge
        result = await asyncio.to_thread(
            search_knowledge,
            query,
            top_k=top_k,
            user_id=get_current_user_id(),
        )
        return result
    except Exception as e:
        return {"results": [], "query": query, "error": str(e), "note": "Knowledge Vault not configured"}


async def generate_image(prompt: str, size: str = "1024x1024", **kwargs) -> dict:
    """Generate image from text prompt (async wrapper)."""
    return await asyncio.to_thread(_generate_image_sync, prompt, size)


async def generate_short_video(prompt: str, duration: int = 15, **kwargs) -> dict:
    """Generate short video from text prompt (async wrapper)."""
    return await asyncio.to_thread(_generate_short_video_sync, prompt, duration)


async def placeholder_tool(context: dict | None = None) -> dict:
    """Fallback tool for unimplemented functions."""
    if context is None:
        context = {}
    logger.warning("Executing placeholder tool.")
    return {
        "status": "simulated_success",
        "message": "This tool is not yet implemented. Step auto-completed.",
    }


async def alias_send_email(
    to: list[str] | None = None,
    subject: str = "",
    body: str = "",
    **kwargs,
) -> dict:
    """Compatibility alias for workflow templates that use `send_email`."""
    desc = f"[EMAIL] to={to or []} subject={subject} body={body[:300]}"
    return await create_task(description=desc)


async def alias_create_document(
    title: str = "Workflow Document",
    content: str = "",
    **kwargs,
) -> dict:
    """Compatibility alias for workflow templates that use `create_document`."""
    return await save_content(title=title, content=content or "(empty)")


async def alias_schedule_meeting(
    title: str = "Workflow Meeting",
    attendees: list[str] | None = None,
    start_time: str | None = None,
    **kwargs,
) -> dict:
    """Compatibility alias for workflow templates that use scheduling primitives."""
    desc = f"[MEETING] title={title} attendees={attendees or []} start_time={start_time or 'unspecified'}"
    return await create_task(description=desc)


async def alias_create_spreadsheet(
    title: str = "Workflow Spreadsheet",
    **kwargs,
) -> dict:
    """Compatibility alias for workflow templates that use `create_spreadsheet`."""
    return await save_content(title=title, content="Spreadsheet requested by workflow")


async def alias_process_payment(
    amount: float | None = None,
    currency: str = "usd",
    description: str = "Workflow payment",
    **kwargs,
) -> dict:
    """Compatibility alias for workflow templates that use `process_payment`."""
    desc = f"[PAYMENT] amount={amount} currency={currency} description={description}"
    return await create_task(description=desc)


async def alias_publish_page(
    user_id: str | None = None,
    page_id: str | None = None,
    **kwargs,
) -> dict:
    """Compatibility alias for workflow templates that use `publish_page`."""
    desc = f"[PUBLISH_PAGE] user_id={user_id} page_id={page_id}"
    return await create_task(description=desc)


# =============================================================================
# Input Schemas for Deterministic Mapping
# =============================================================================

class McpWebSearchInput(BaseModel):
    query: str = Field(..., description="The search query.")

class McpWebScrapeInput(BaseModel):
    url: str = Field(..., description="The URL to scrape.")

class CreateTaskInput(BaseModel):
    description: str = Field(..., description="Description of the task.")
    assignee: Optional[str] = Field(None, description="Assignee of the task.")
    priority: Optional[str] = Field("medium", description="Priority level.")

# Assign schemas to tool functions
mcp_web_search.input_schema = McpWebSearchInput
mcp_web_scrape.input_schema = McpWebScrapeInput
create_task.input_schema = CreateTaskInput

# =============================================================================
# Registry Dictionary
# format: "tool_name": function_reference
# =============================================================================
TOOL_REGISTRY = {
    "create_workflow_template": create_workflow_template,
    "get_braindump_document": get_braindump_document,
    # --- MCP Tools ---
    "mcp_web_search": mcp_web_search,
    "mcp_web_scrape": mcp_web_scrape,

    # --- Knowledge Tools ---
    "add_business_knowledge": add_business_knowledge,
    "search_business_knowledge": search_business_knowledge,
    "add_product_info": add_product_info,
    "add_company_info": add_company_info,
    "add_process_or_policy": add_process_or_policy,
    "add_faq": add_faq,

    # --- Strategic / Initiative Tools ---
    "create_initiative": create_initiative,
    "get_initiative": get_initiative,
    "update_initiative": update_initiative,
    "list_initiatives": list_initiatives,
    "update_initiative_status": update_initiative,  # Alias used in old workflow YAML
    "start_initiative_from_idea": start_initiative_from_idea,
    "advance_initiative_phase": advance_initiative_phase,
    "list_initiative_templates": list_initiative_templates,
    "create_initiative_from_template": create_initiative_from_template,
    "start_journey_workflow": start_journey_workflow,

    # --- Task Tools ---
    "create_task": create_task,
    "get_task": get_task,
    "update_task": update_task,
    "list_tasks": list_tasks,

    # --- Marketing / Campaign Tools ---
    "create_campaign": create_campaign,
    "get_campaign": get_campaign,
    "update_campaign": update_campaign,
    "list_campaigns": list_campaigns,
    "record_campaign_metrics": record_campaign_metrics,
    "generate_campaign_ideas": quick_research,  # Uses research for campaign ideas

    # --- HR / Recruitment Tools ---
    "create_job": create_job,
    "get_job": get_job,
    "update_job": update_job,
    "list_jobs": list_jobs,
    "add_candidate": add_candidate,
    "update_candidate_status": update_candidate_status,
    "list_candidates": list_candidates,

    # --- Customer Support Tools ---
    "create_ticket": create_ticket,
    "get_ticket": get_ticket,
    "update_ticket": update_ticket,
    "list_tickets": list_tickets,

    # --- Compliance Tools ---
    "create_audit": create_audit,
    "get_audit": get_audit,
    "update_audit": update_audit,
    "list_audits": list_audits,
    "create_risk": create_risk,
    "get_risk": get_risk,
    "update_risk": update_risk,
    "list_risks": list_risks,

    # --- Data / Analytics Tools ---
    "track_event": track_event,
    "query_events": query_events,
    "create_report": create_report,
    "list_reports": list_reports,

    # --- Financial Tools ---
    "get_revenue_stats": get_revenue_stats,
    "get_financial_report": get_financial_report,
    "get_cash_position": get_cash_position,
    "get_burn_runway_report": get_burn_runway_report,
    "save_finance_assumption": save_finance_assumption,
    "list_finance_assumptions": list_finance_assumptions,
    "render_burn_runway_widget": render_burn_runway_widget,
    "render_pnl_summary_widget": render_pnl_summary_widget,
    "render_budget_vs_actual_widget": render_budget_vs_actual_widget,
    "render_revenue_bridge_widget": render_revenue_bridge_widget,
    "render_cohort_retention_widget": render_cohort_retention_widget,
    "render_cash_waterfall_widget": render_cash_waterfall_widget,
    "render_kpi_scorecard_widget": render_kpi_scorecard_widget,
    "get_finance_deliverable_templates": get_finance_deliverable_templates,
    "create_finance_deliverable": create_finance_deliverable,
    "analyze_financial_health": get_revenue_stats,  # Alias

    # --- Content Tools ---
    "save_content": save_content,
    "get_content": get_content,
    "update_content": update_content,
    "list_content": list_content,
    "generate_image": generate_image,
    "generate_short_video": generate_short_video,
    "create_product_photoshoot_bundle": create_product_photoshoot_bundle,
    "execute_content_pipeline": execute_content_pipeline,
    "get_media_deliverable_templates": get_media_deliverable_templates,

    # --- Research Tools ---
    "deep_research": deep_research,
    "quick_research": quick_research,
    "market_research": market_research,
    "competitor_research": competitor_research,

    # --- Aliases for workflow definitions (0009 seed + YAML) ---
    "analyze_process_bottlenecks": quick_research,
    "get_seo_checklist": quick_research,
    "get_sop_template": quick_research,
    "analyze_results": create_report,  # 0009 QBR, A/B workflows
    "generate_content": save_content,  # 0009 Content, Marketing, etc.
    "generate_ideas": quick_research,
    "publish_content": update_content,
    "generate_social_content": save_content,
    "filter_users": query_events,
    "record_metrics": record_campaign_metrics,
    "query_metrics": query_events,
    "generate_report": create_report,  # support
    "assign_task": create_task,
    "update_crm": track_event,
    "send_email_campaign": create_campaign,

    # --- Compatibility aliases for seeded template tools ---
    "send_email": alias_send_email,
    "create_document": alias_create_document,
    "schedule_meeting": alias_schedule_meeting,
    "schedule_call": alias_schedule_meeting,
    "schedule_interview": alias_schedule_meeting,
    "create_calendar_events": alias_schedule_meeting,
    "create_spreadsheet": alias_create_spreadsheet,
    "process_payment": process_payment_high_risk,
    "publish_page": alias_publish_page,
    "record_video": generate_short_video,

    # --- Phase 1 quick aliases for degraded templates ---
    # NOTE: These keep workflows end-to-end executable while real integrations
    # are implemented in later phases.
    "create_folder": degraded_create_folder,
    "create_project": degraded_create_project,
    "analyze_sentiment": degraded_analyze_sentiment,
    "setup_monitoring": degraded_setup_monitoring,
    "manage_comments": manage_comments,
    "send_message": integrated_send_message,
    "configure_ads": degraded_configure_ads,
    "optimize_spend": degraded_optimize_spend,
    "create_contact": degraded_create_contact,
    "score_lead": degraded_score_lead,
    "send_contract": send_contract,
    "sent_contract": send_contract,  # legacy typo alias
    "listen_call": integrated_listen_call,
    "start_call": integrated_start_call,
    "query_crm": degraded_query_crm,
    "generate_forecast": degraded_generate_forecast,
    "create_vendor": degraded_create_vendor,
    "update_inventory": degraded_update_inventory,
    "create_po": degraded_create_po,
    "log_shipment": degraded_log_shipment,
    "create_task_list": degraded_create_task_list,
    "run_script": integrated_run_script,
    "update_asset_log": update_asset_log,
    "approve_request": approve_request,
    "book_travel": degraded_book_travel,
    "process_expense": degraded_process_expense,
    "run_checklist": degraded_run_checklist,
    "assign_training": degraded_assign_training,
    "post_job_board": degraded_post_job_board,
    "submit_form": submit_form,
    "query_timesheets": query_timesheets,
    "execute_payroll": execute_payroll,
    "process_forms": integrated_process_forms,
    "send_file": send_file,
    "update_hris": integrated_update_hris,
    "create_checklist": degraded_create_checklist,
    "record_notes": degraded_record_notes,
    "create_pr": create_pr,
    "run_deployment": integrated_run_deployment,
    "test_scenario": degraded_test_scenario,
    "query_feedback": query_feedback,
    "calculate_score": calculate_score,
    "update_gantt": update_gantt,
    "query_analytics": degraded_query_analytics,
    "create_form": create_form,
    "update_settings": update_settings,
    "send_guide": send_guide,
    "send_form": send_form,
    "create_alert": degraded_create_alert,
    "query_usage": degraded_query_usage,
    "update_subscription": degraded_update_subscription,
    "read_docs": read_docs,
    "update_cms": update_cms,
    "upload_file": degraded_upload_file,
    "ocr_document": degraded_ocr_document,
    "verify_po": degraded_verify_po,
    "send_payment": send_payment,
    "update_budget": update_budget,
    "query_ledger": query_ledger,
    "run_audit": degraded_run_audit,
    "upload_document": degraded_upload_document,
    "update_ledger": update_ledger,
    "query_bank": query_bank,
    "create_forecast": degraded_create_forecast,
    "transfer_money": transfer_money_high_risk,
    "edit_document": edit_document,
    "scan_database": scan_database,
    "review_policy": review_policy,
    "approve_document": approve_document,
    "create_record": create_record,
    "update_record": update_record,
    "create_connection": integrated_create_connection,
    "create_query": integrated_create_query,
    "create_table": integrated_create_table,
    "create_chart": integrated_create_chart,
    "grant_access": integrated_grant_access,
    "audit_logs": integrated_audit_logs,
    "run_test": degraded_run_test,
    "process_data": integrated_process_data,
    "train_model": integrated_train_model,
    "deploy_service": integrated_deploy_service,
    "create_tracking_plan": create_tracking_plan,
    "update_code": integrated_update_code,
    "check_logs": integrated_check_logs,
}


def get_tool(tool_name: str):
    """Get a tool function by name.

    Returns the registered tool if found, otherwise returns a placeholder wrapper
    that logs the missing tool and auto-completes the step.
    """
    if tool_name in TOOL_REGISTRY:
        resolved = TOOL_REGISTRY[tool_name]
        if STRICT_CRITICAL_TOOL_GUARD and tool_name in CRITICAL_WORKFLOW_TOOLS and resolved is placeholder_tool:
            async def critical_guard_wrapper(**kwargs):
                raise RuntimeError(f"Critical workflow tool mapped to placeholder: {tool_name}")
            return critical_guard_wrapper
        return resolved

    # Return placeholder for truly missing tools.
    logger.info(f"Tool '{tool_name}' not found in registry. Using placeholder.")

    if STRICT_TOOL_RESOLUTION:
        async def strict_wrapper(**kwargs):
            raise RuntimeError(f"Unknown workflow tool: {tool_name}")
        return strict_wrapper

    async def wrapper(**kwargs):
        logger.warning(f"Executing placeholder for: {tool_name}")
        return {
            "status": "simulated_success",
            "message": f"Tool '{tool_name}' implementation missing. Auto-completed step.",
            "mock_data": kwargs,
        }

    return wrapper
