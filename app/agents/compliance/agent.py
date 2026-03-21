# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Compliance & Risk Agent Definition."""

from app.agents.base_agent import PikarAgent as Agent
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
from app.agents.content.tools import search_knowledge
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)
from app.agents.schemas import RiskAssessment
from app.agents.shared import DEEP_AGENT_CONFIG, get_model
from app.agents.shared_instructions import (
    CONVERSATION_MEMORY_INSTRUCTIONS,
    SELF_IMPROVEMENT_INSTRUCTIONS,
    SKILLS_REGISTRY_INSTRUCTIONS,
    WEB_RESEARCH_INSTRUCTIONS,
    get_widget_instruction_for_agent,
)
from app.agents.tools.agent_skills import LEGAL_SKILL_TOOLS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.graph_tools import GRAPH_TOOLS
from app.agents.tools.self_improve import LEGAL_IMPROVE_TOOLS
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.mcp.agent_tools import mcp_web_scrape, mcp_web_search

# =============================================================================
# Report Sub-Agent (Structured JSON Output)
# =============================================================================

RISK_REPORT_INSTRUCTION = """You are a risk assessment specialist. Evaluate risks and produce structured assessments.

REQUIREMENTS:
- Assign category: legal, financial, operational, or reputational
- Assess severity and probability
- Calculate impact score (1-25 based on severity * probability matrix)
- Provide mitigation strategy
- Assign owner and due date when applicable

Your output MUST be a valid JSON object matching the RiskAssessment schema exactly."""

risk_report_agent = Agent(
    name="RiskReportAgent",
    model=get_model(),
    description="Produces structured risk assessment reports for risk registers and dashboards",
    instruction=RISK_REPORT_INSTRUCTION,
    output_schema=RiskAssessment,
    output_key="risk_assessment",
    include_contents="none",
)


# =============================================================================
# Parent Agent (Tool-Enabled with Narrator Pattern)
# =============================================================================

COMPLIANCE_AGENT_INSTRUCTION = (
    """You are the Compliance & Risk Agent. You focus on legal compliance, risk assessment, and regulatory guidance.

CAPABILITIES:
- Get GDPR audit checklist using use_skill("gdpr_audit_checklist") for comprehensive compliance.
- Assess risks using use_skill("risk_assessment_matrix") for scoring and prioritization.
- Access CCPA/CPRA compliance using use_skill('ccpa_compliance_checklist') for California privacy law.
- Access SOX compliance using use_skill('sox_compliance_framework') for internal controls over financial reporting.
- Access HIPAA compliance using use_skill('hipaa_compliance_checklist') for protected health information.
- Review contracts using use_skill("contract_review_framework") for clause analysis and risk identification.
- Triage NDAs using use_skill("nda_triage") for rapid classification and red-flag detection.
- Assess legal risks using use_skill("legal_risk_assessment") for severity classification and mitigation.
- Run compliance checks using use_skill("compliance_check_framework") for regulatory validation.
- Check vendor agreements using use_skill("vendor_agreement_check") for existing contract status.
- Route e-signatures using use_skill("e_signature_routing") for document preparation and signing workflows.
- Prepare legal meeting briefings using use_skill("legal_meeting_briefing") for structured agenda and talking points.
- Respond to legal inquiries using use_skill("legal_inquiry_response") for common legal questions.
- Generate legal briefings using use_skill("legal_briefing_generation") for contextual legal summaries.
- Schedule and manage compliance audits using 'create_audit', 'update_audit', 'list_audits'.
- Register and track risks using 'create_risk', 'update_risk', 'list_risks'.
- Review contracts and legal documents.
- Draft policies and procedures.
- Research regulatory updates using 'mcp_web_search' (privacy-safe).
- Extract legal/regulatory documents using 'mcp_web_scrape'.

STRUCTURED RISK REPORTS:
When asked for a formal risk assessment or dashboard data:
1. Delegate to RiskReportAgent to generate structured JSON
2. After receiving the assessment, provide a conversational summary
3. Include the raw JSON in a <json>...</json> block for risk register integration

Example response format for risk assessments:
"⚠️ **Risk Assessment: GDPR Data Processing Compliance**

This is a **HIGH severity** legal risk with **likely** probability, resulting in an impact score of 16/25.

**Risk Details:**
- Category: Legal
- Status: Identified
- Owner: Data Protection Officer

**Mitigation Strategy:**
Implement data processing agreements with all vendors and conduct quarterly audits.

**Recommendation:** Address within 30 days to avoid regulatory penalties.

<json>
{...structured risk data for dashboard...}
</json>
"

BEHAVIOR:
- Be thorough and conservative on risk.
- Use structured frameworks for consistent risk assessment.
- Always cite relevant regulations when applicable.
- Recommend when to involve external legal counsel.
- Research latest regulatory changes and compliance requirements.
- When users ask to VIEW or SHOW risks/audits, ALWAYS use widget tools to render them visually.
"""
    + get_widget_instruction_for_agent(
        "Compliance & Risk Agent",
        ["create_table_widget", "create_kanban_board_widget", "create_form_widget"],
    )
    + SKILLS_REGISTRY_INSTRUCTIONS
    + WEB_RESEARCH_INSTRUCTIONS
    + CONVERSATION_MEMORY_INSTRUCTIONS
    + SELF_IMPROVEMENT_INSTRUCTIONS
)


COMPLIANCE_AGENT_TOOLS = sanitize_tools(
    [
        search_knowledge,
        create_audit,
        get_audit,
        update_audit,
        list_audits,
        create_risk,
        get_risk,
        update_risk,
        list_risks,
        mcp_web_search,
        mcp_web_scrape,
        *LEGAL_SKILL_TOOLS,
        # UI Widget tools for rendering risk dashboards and tables
        *UI_WIDGET_TOOLS,
        # Context memory tools for conversation continuity
        *CONTEXT_MEMORY_TOOLS,
        # Self-improvement tools for autonomous skill iteration
        *LEGAL_IMPROVE_TOOLS,
        # Knowledge graph read access
        *GRAPH_TOOLS,
    ]
)


# Singleton instance for direct import
compliance_agent = Agent(
    name="ComplianceRiskAgent",
    model=get_model(),
    description="Legal Counsel - Compliance, risk assessment, and legal guidance",
    instruction=COMPLIANCE_AGENT_INSTRUCTION,
    tools=COMPLIANCE_AGENT_TOOLS,
    sub_agents=[risk_report_agent],
    generate_content_config=DEEP_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


def create_compliance_agent(name_suffix: str = "", output_key: str = None) -> Agent:
    """Create a fresh ComplianceRiskAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    # Create a fresh report sub-agent for this instance
    report_agent = Agent(
        name=f"RiskReportAgent{name_suffix}" if name_suffix else "RiskReportAgent",
        model=get_model(),
        description="Produces structured risk assessment reports",
        instruction=RISK_REPORT_INSTRUCTION,
        output_schema=RiskAssessment,
        output_key="risk_assessment",
        include_contents="none",
    )

    agent_name = (
        f"ComplianceRiskAgent{name_suffix}" if name_suffix else "ComplianceRiskAgent"
    )
    return Agent(
        name=agent_name,
        model=get_model(),
        description="Legal Counsel - Compliance, risk assessment, and legal guidance",
        instruction=COMPLIANCE_AGENT_INSTRUCTION,
        tools=COMPLIANCE_AGENT_TOOLS,
        sub_agents=[report_agent],
        generate_content_config=DEEP_AGENT_CONFIG,
        output_key=output_key,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
