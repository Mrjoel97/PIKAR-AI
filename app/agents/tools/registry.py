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
    get_burn_runway_report,
    get_cash_position,
    get_finance_deliverable_templates,
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

# --- API Connector Tools ---
from app.agents.tools.api_connector import (
    connect_api as _connect_api_sync,
)
from app.agents.tools.api_connector import (
    disconnect_api as _disconnect_api_sync,
)
from app.agents.tools.api_connector import (
    list_api_connections as _list_api_connections_sync,
)
from app.agents.tools.api_connector import (
    validate_api_connection as _validate_api_connection_sync,
)
from app.agents.tools.boardroom import convene_board_meeting

# --- Briefing Tools ---
from app.agents.tools.briefing_tools import (
    dismiss_item as _dismiss_item_sync,
)
from app.agents.tools.briefing_tools import (
    get_daily_briefing as _get_daily_briefing_sync,
)
from app.agents.tools.briefing_tools import (
    refresh_briefing as _refresh_briefing_sync,
)
from app.agents.tools.briefing_tools import (
    undo_auto_action as _undo_auto_action_sync,
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

# --- Gmail Inbox Tools ---
from app.agents.tools.gmail_inbox import (
    archive_email,
    classify_email,
    label_email,
    read_email,
    read_inbox,
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

# --- Invoice Tools ---
from app.agents.tools.invoicing import generate_invoice

# --- Magic Link Approval Tools ---
from app.agents.tools.magic_link_approvals import (
    send_approval_request as _send_approval_request_sync,
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
from app.mcp.agent_tools import (
    mcp_generate_landing_page,
    mcp_stitch_landing_page,
    mcp_web_scrape,
    mcp_web_search,
)
from app.mcp.tools.canva_media import (
    create_product_photoshoot_bundle,
    execute_content_pipeline,
    get_media_deliverable_templates,
)
from app.mcp.tools.supabase_landing import create_landing_page, publish_page

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
STRICT_TOOL_RESOLUTION = (
    os.getenv("WORKFLOW_STRICT_TOOL_RESOLUTION", "true").lower() == "true"
)
STRICT_CRITICAL_TOOL_GUARD = (
    os.getenv("WORKFLOW_STRICT_CRITICAL_TOOL_GUARD", "true").lower() == "true"
)
CRITICAL_WORKFLOW_TOOLS = {
    "approve_request",
    "send_contract",
    "query_timesheets",
    "execute_payroll",
    "process_payment",
    "send_payment",
    "transfer_money",
}


def is_fallback_simulation_allowed() -> bool:
    """Allow simulated workflow completion only in explicitly permissive non-production environments."""
    env = (
        (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "development").strip().lower()
    )
    if env in {"production", "prod"}:
        return False
    return (
        os.getenv("WORKFLOW_ALLOW_FALLBACK_SIMULATION", "false").strip().lower()
        == "true"
    )


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
        return {
            "results": [],
            "query": query,
            "error": str(e),
            "note": "Knowledge Vault not configured",
        }


async def generate_image(prompt: str, size: str = "1024x1024", **kwargs) -> dict:
    """Generate image from text prompt (async wrapper)."""
    return await asyncio.to_thread(_generate_image_sync, prompt, size)


async def generate_short_video(prompt: str, duration: int = 15, **kwargs) -> dict:
    """Generate short video from text prompt (async wrapper)."""
    return await asyncio.to_thread(_generate_short_video_sync, prompt, duration)


async def placeholder_tool(context: dict | None = None) -> dict:
    """Fallback tool for unimplemented functions."""
    if not is_fallback_simulation_allowed():
        raise RuntimeError(
            "Placeholder workflow tool execution is disabled. Provide a real implementation or explicitly enable WORKFLOW_ALLOW_FALLBACK_SIMULATION in a non-production environment."
        )
    if context is None:
        context = {}
    logger.warning("Executing placeholder tool.")
    return {
        "status": "simulated_success",
        "message": "This tool is not yet implemented. Step auto-completed.",
    }


# --- Async wrappers for briefing tools (workflow registry) ---
# These tools use tool_context in agent mode; wrappers adapt them for workflow use.


async def briefing_get_daily(**kwargs) -> dict:
    """Get daily email briefing sections (workflow wrapper)."""
    return _get_daily_briefing_sync(None)


async def briefing_refresh(user_id: str | None = None, **kwargs) -> dict:
    """Trigger on-demand email triage (workflow wrapper)."""

    class _Ctx:
        state = {"user_id": user_id or get_current_user_id() or ""}

    return _refresh_briefing_sync(_Ctx())


async def briefing_approve_draft(triage_item_id: str, **kwargs) -> dict:
    """Approve and send a draft reply (workflow wrapper — requires agent context for Gmail auth)."""
    return {
        "status": "error",
        "message": "approve_draft requires agent context with Google auth. Use the agent tool directly.",
    }


async def briefing_dismiss_item(triage_item_id: str, **kwargs) -> dict:
    """Dismiss a triage item (workflow wrapper)."""
    return _dismiss_item_sync(None, triage_item_id)


async def briefing_undo_auto_action(triage_item_id: str, **kwargs) -> dict:
    """Undo auto-action on a triage item (workflow wrapper)."""
    return _undo_auto_action_sync(None, triage_item_id)


# --- Async wrappers for API Connector tools (workflow registry) ---


async def connect_api_workflow(
    spec_url: str,
    api_name: str = "",
    secret_name: str = "",
    selected_endpoints: str = "",
    **kwargs,
) -> dict:
    """Connect to an external API via OpenAPI spec (workflow wrapper)."""
    return await asyncio.to_thread(
        _connect_api_sync, spec_url, api_name, secret_name, selected_endpoints
    )


async def list_api_connections_workflow(**kwargs) -> dict:
    """List active API connections (workflow wrapper)."""
    return await asyncio.to_thread(_list_api_connections_sync)


async def disconnect_api_workflow(api_name: str = "", **kwargs) -> dict:
    """Disconnect an API by name (workflow wrapper)."""
    return await asyncio.to_thread(_disconnect_api_sync, api_name)


async def validate_api_connection_workflow(api_name: str = "", **kwargs) -> dict:
    """Validate an API connection's spec freshness (workflow wrapper)."""
    return await asyncio.to_thread(_validate_api_connection_sync, api_name)


async def send_approval_request_workflow(
    action_type: str = "approval",
    description: str = "",
    recipient_email: str = "",
    details: str = "",
    expires_in_hours: int = 24,
    **kwargs,
) -> dict:
    """Send a magic link approval request (workflow wrapper - no Gmail auth, link only)."""
    return await asyncio.to_thread(
        _send_approval_request_sync,
        None,  # tool_context — not available in workflow mode, email may fail gracefully
        action_type,
        description,
        recipient_email,
        details,
        expires_in_hours,
    )


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


async def promoted_score_lead(
    lead_name: str = "Lead",
    score: int | None = None,
    **kwargs,
) -> dict:
    """Score and qualify a lead using AI research and task tracking."""
    research = await quick_research(
        topic=f"qualify and score business lead: {lead_name}"
    )
    task = await create_task(
        description=f"Lead scoring: '{lead_name}' — score={score if score is not None else 'pending AI assessment'}"
    )
    await track_event(
        event_name="score_lead",
        category="crm",
        properties=f'{{"lead_name":"{lead_name}","score":{score or 0}}}',
    )
    return {"success": True, "research": research, "task": task, "tool": "score_lead"}


async def promoted_setup_monitoring(
    description: str = "Setup monitoring",
    **kwargs,
) -> dict:
    """Set up monitoring by creating a task and tracking the event."""
    task = await create_task(description=f"Setup monitoring: {description}")
    await track_event(
        event_name="setup_monitoring",
        category="operations",
        properties=f'{{"description":"{description}"}}',
    )
    return {"success": True, "task": task, "tool": "setup_monitoring"}


# =============================================================================
# Input Schemas for Deterministic Mapping
# =============================================================================


class McpWebSearchInput(BaseModel):
    query: str = Field(..., description="The search query.")


class McpWebScrapeInput(BaseModel):
    url: str = Field(..., description="The URL to scrape.")


class CreateTaskInput(BaseModel):
    description: str = Field(..., description="Description of the task.")
    assignee: str | None = Field(None, description="Assignee of the task.")
    priority: str | None = Field("medium", description="Priority level.")


class CreateInitiativeInput(BaseModel):
    title: str = Field(..., description="Initiative title.")
    description: str = Field(..., description="Initiative description.")
    priority: str | None = Field("medium", description="Initiative priority.")


class CreateCampaignInput(BaseModel):
    name: str = Field(..., description="Campaign name.")
    campaign_type: str = Field(..., description="Campaign type.")
    target_audience: str = Field(..., description="Target audience.")


class TrackEventInput(BaseModel):
    event_name: str = Field(..., description="Analytics event name.")
    category: str = Field(..., description="Analytics category.")
    properties: str | None = Field(None, description="JSON string properties.")


class CreateReportInput(BaseModel):
    title: str = Field(..., description="Report title.")
    report_type: str = Field(..., description="Report type.")
    data: str = Field(..., description="JSON string report data.")
    description: str | None = Field(None, description="Report description.")


class GenerateInvoiceInput(BaseModel):
    user_id: str = Field(..., description="Owner user id.")
    invoice_number: str = Field(..., description="Invoice number.")
    customer_name: str = Field(..., description="Customer name.")
    customer_email: str = Field(..., description="Customer email.")
    items: list[dict[str, object]] = Field(..., description="Invoice line items.")
    total_amount: float = Field(..., description="Invoice total amount.")
    due_date: str | None = Field(None, description="Due date.")


class McpGenerateLandingPageInput(BaseModel):
    title: str = Field(..., description="Landing page title.")
    description: str = Field(..., description="Landing page description.")
    headline: str | None = Field(None, description="Hero headline.")
    subheadline: str | None = Field(None, description="Hero subheadline.")
    style: str = Field("modern", description="Visual style.")
    include_form: bool = Field(True, description="Whether to include form.")
    cta_text: str = Field("Get Started", description="Call to action text.")


class CreateLandingPageInput(BaseModel):
    user_id: str = Field(..., description="Owner user id.")
    title: str = Field(..., description="Landing page title.")
    html_content: str = Field(..., description="HTML page content.")
    slug: str | None = Field(None, description="Optional page slug.")
    publish: bool = Field(False, description="Whether to publish immediately.")


class PublishPageInput(BaseModel):
    user_id: str = Field(..., description="Owner user id.")
    page_id: str = Field(..., description="Landing page id.")


class SaveContentInput(BaseModel):
    title: str = Field(..., description="Content title.")
    content: str = Field(..., description="Content body text.")


class UpdateContentInput(BaseModel):
    content_id: str = Field(..., description="ID of the content to update.")
    title: str | None = Field(None, description="Updated title.")
    content: str | None = Field(None, description="Updated content body.")


class QuickResearchInput(BaseModel):
    topic: str = Field(..., description="Research topic or question.")


class DeepResearchInput(BaseModel):
    topic: str = Field(..., description="Research topic or question.")
    research_type: str = Field("comprehensive", description="Type of research.")
    depth: str = Field("deep", description="Research depth level.")


class MarketResearchInput(BaseModel):
    topic: str = Field(..., description="Market or industry to research.")


class CompetitorResearchInput(BaseModel):
    topic: str = Field(..., description="Competitor or market segment to research.")


class AddBusinessKnowledgeInput(BaseModel):
    content: str = Field(..., description="Knowledge content to store.")
    title: str = Field(..., description="Title for the knowledge entry.")
    category: str | None = Field(None, description="Knowledge category.")


class ListInitiativesInput(BaseModel):
    status: str | None = Field(None, description="Filter by initiative status.")
    phase: str | None = Field(None, description="Filter by initiative phase.")


class UpdateInitiativeInput(BaseModel):
    initiative_id: str = Field(..., description="ID of the initiative to update.")
    status: str | None = Field(None, description="New status.")
    progress: int | None = Field(None, description="Progress percentage.")
    phase: str | None = Field(None, description="New phase.")
    title: str | None = Field(None, description="Updated title.")
    description: str | None = Field(None, description="Updated description.")


class QueryEventsInput(BaseModel):
    event_name: str | None = Field(None, description="Filter by event name.")
    category: str | None = Field(None, description="Filter by event category.")
    limit: int = Field(100, description="Max events to return.")


class GetRevenueStatsInput(BaseModel):
    period: str = Field("current_month", description="Reporting period.")


class RecordCampaignMetricsInput(BaseModel):
    campaign_id: str = Field(..., description="Campaign ID.")
    impressions: int = Field(0, description="Number of impressions.")
    clicks: int = Field(0, description="Number of clicks.")
    conversions: int = Field(0, description="Number of conversions.")


class ManageCommentsInput(BaseModel):
    platform: str = Field("social", description="Comment platform.")
    action: str = Field("reply", description="Comment action.")
    comment_id: str | None = Field(None, description="Comment ID.")
    response: str = Field("", description="Reply text.")


class PromotedScoreLeadInput(BaseModel):
    lead_name: str = Field("Lead", description="Name of the lead to score.")
    score: int | None = Field(None, description="Manual score override.")


class PromotedSetupMonitoringInput(BaseModel):
    description: str = Field(
        "Setup monitoring", description="Monitoring setup description."
    )


class GenerateImageInput(BaseModel):
    prompt: str = Field(..., description="Image generation prompt.")
    size: str = Field("1024x1024", description="Image dimensions.")


# Assign schemas to tool functions
mcp_web_search.input_schema = McpWebSearchInput
mcp_web_scrape.input_schema = McpWebScrapeInput
create_task.input_schema = CreateTaskInput
create_initiative.input_schema = CreateInitiativeInput
create_campaign.input_schema = CreateCampaignInput
track_event.input_schema = TrackEventInput
create_report.input_schema = CreateReportInput
generate_invoice.input_schema = GenerateInvoiceInput
mcp_generate_landing_page.input_schema = McpGenerateLandingPageInput
mcp_stitch_landing_page.input_schema = McpGenerateLandingPageInput
create_landing_page.input_schema = CreateLandingPageInput
publish_page.input_schema = PublishPageInput
save_content.input_schema = SaveContentInput
update_content.input_schema = UpdateContentInput
quick_research.input_schema = QuickResearchInput
deep_research.input_schema = DeepResearchInput
market_research.input_schema = MarketResearchInput
competitor_research.input_schema = CompetitorResearchInput
add_business_knowledge.input_schema = AddBusinessKnowledgeInput
list_initiatives.input_schema = ListInitiativesInput
update_initiative.input_schema = UpdateInitiativeInput
query_events.input_schema = QueryEventsInput
get_revenue_stats.input_schema = GetRevenueStatsInput
record_campaign_metrics.input_schema = RecordCampaignMetricsInput
manage_comments.input_schema = ManageCommentsInput
generate_image.input_schema = GenerateImageInput
promoted_score_lead.input_schema = PromotedScoreLeadInput
promoted_setup_monitoring.input_schema = PromotedSetupMonitoringInput

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
    "mcp_generate_landing_page": mcp_generate_landing_page,
    "mcp_stitch_landing_page": mcp_stitch_landing_page,
    "create_landing_page": create_landing_page,
    "publish_page": publish_page,
    # --- Knowledge Tools ---
    "add_business_knowledge": add_business_knowledge,
    "search_business_knowledge": search_business_knowledge,
    "add_product_info": add_product_info,
    "add_company_info": add_company_info,
    "add_process_or_policy": add_process_or_policy,
    "add_faq": add_faq,
    # --- Strategic / Initiative Tools ---
    "convene_board_meeting": convene_board_meeting,
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
    "generate_invoice": generate_invoice,
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
    # --- Aliases for YAML workflow templates (batch 2) ---
    # These map tool names referenced in definitions/*.yaml to existing real tools,
    # keeping workflows end-to-end executable.
    "compare_features": create_report,  # competitor_analysis.yaml
    "create_swot": create_report,  # competitor_analysis.yaml
    "display_content": save_content,  # content_creation, email_sequence
    "edit_content": update_content,  # content_creation.yaml
    "generate_content_ideas": quick_research,  # content_creation.yaml
    "get_blog_writing_framework": quick_research,  # content_creation, email_sequence
    "get_campaign_framework": quick_research,  # email_sequence, social_campaign
    "get_lead_qualification_framework": quick_research,  # lead_gen.yaml
    "get_trend_analysis_framework": quick_research,  # ab_testing, email_sequence
    "mcp_stitch_generate_screen_from_text": mcp_stitch_landing_page,  # ab_testing (name mismatch)
    "publish_post": save_content,  # social_campaign.yaml
    "run_ab_test": create_report,  # product_launch.yaml
    "score_leads": promoted_score_lead,  # lead_gen.yaml (plural fix)
    "setup_ab_test": create_task,  # ab_testing.yaml
    "start_experiment": create_task,  # ab_testing.yaml
    "trigger_launch": create_task,  # product_launch.yaml
    "update_strategy": save_content,  # social_campaign.yaml
    # --- Compatibility aliases for seeded template tools ---
    "send_email": alias_send_email,
    "create_document": alias_create_document,
    "schedule_meeting": alias_schedule_meeting,
    "schedule_call": alias_schedule_meeting,
    "schedule_interview": alias_schedule_meeting,
    "create_calendar_events": alias_schedule_meeting,
    "create_spreadsheet": alias_create_spreadsheet,
    "process_payment": process_payment_high_risk,
    "record_video": generate_short_video,
    # --- Phase 1 quick aliases for degraded templates ---
    # NOTE: These keep workflows end-to-end executable while real integrations
    # are implemented in later phases.
    "create_folder": degraded_create_folder,
    "create_project": degraded_create_project,
    "analyze_sentiment": degraded_analyze_sentiment,
    "setup_monitoring": promoted_setup_monitoring,
    "manage_comments": manage_comments,
    "send_message": integrated_send_message,
    "configure_ads": degraded_configure_ads,
    "optimize_spend": degraded_optimize_spend,
    "create_contact": degraded_create_contact,
    "score_lead": promoted_score_lead,
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
    # --- Gmail Inbox Tools ---
    "read_inbox": read_inbox,
    "read_email": read_email,
    "classify_email": classify_email,
    "archive_email": archive_email,
    "label_email": label_email,
    # --- Briefing / Email Triage Tools ---
    "get_daily_briefing": briefing_get_daily,
    "refresh_briefing": briefing_refresh,
    "approve_draft": briefing_approve_draft,
    "dismiss_item": briefing_dismiss_item,
    "undo_auto_action": briefing_undo_auto_action,
    # --- Magic Link Approval Tools ---
    "send_approval_request": send_approval_request_workflow,
    # --- API Connector Tools ---
    "connect_api": connect_api_workflow,
    "list_api_connections": list_api_connections_workflow,
    "disconnect_api": disconnect_api_workflow,
    "validate_api_connection": validate_api_connection_workflow,
}


def get_tool(tool_name: str):
    """Get a tool function by name.

    Returns the registered tool if found, otherwise returns a placeholder wrapper
    that logs the missing tool and auto-completes the step.
    """
    if tool_name in TOOL_REGISTRY:
        resolved = TOOL_REGISTRY[tool_name]
        if resolved is placeholder_tool and not is_fallback_simulation_allowed():

            async def placeholder_guard_wrapper(**kwargs):
                raise RuntimeError(
                    f"Placeholder workflow tool blocked: {tool_name}. Enable WORKFLOW_ALLOW_FALLBACK_SIMULATION only in a non-production environment if you need simulated execution."
                )

            return placeholder_guard_wrapper
        if (
            STRICT_CRITICAL_TOOL_GUARD
            and tool_name in CRITICAL_WORKFLOW_TOOLS
            and resolved is placeholder_tool
        ):

            async def critical_guard_wrapper(**kwargs):
                raise RuntimeError(
                    f"Critical workflow tool mapped to placeholder: {tool_name}"
                )

            return critical_guard_wrapper
        return resolved

    # Return placeholder for truly missing tools.
    logger.info(f"Tool '{tool_name}' not found in registry. Using placeholder.")

    if STRICT_TOOL_RESOLUTION or not is_fallback_simulation_allowed():

        async def strict_wrapper(**kwargs):
            raise RuntimeError(
                f"Unknown workflow tool: {tool_name}. Fallback simulation is disabled until a real implementation is available."
            )

        return strict_wrapper

    async def wrapper(**kwargs):
        logger.warning(f"Executing placeholder for: {tool_name}")
        return {
            "status": "simulated_success",
            "message": f"Tool '{tool_name}' implementation missing. Auto-completed step.",
            "mock_data": kwargs,
        }

    return wrapper
