# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Compliance & Risk Agent Definition."""

from google.adk.agents import Agent

from app.agents.shared import get_model
from app.agents.schemas import RiskAssessment
from app.agents.content.tools import search_knowledge
from app.agents.compliance.tools import (
    create_audit,
    get_audit,
    update_audit,
    list_audits,
    create_risk,
    get_risk,
    update_risk,
    list_risks,
)
from app.agents.enhanced_tools import (
    use_skill,
    list_available_skills,
    get_gdpr_audit_checklist,
    get_risk_assessment_matrix,
)
from app.mcp.agent_tools import mcp_web_search, mcp_web_scrape


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

COMPLIANCE_AGENT_INSTRUCTION = """You are the Compliance & Risk Agent. You focus on legal compliance, risk assessment, and regulatory guidance.

CAPABILITIES:
- Get GDPR audit checklist using 'get_gdpr_audit_checklist' for comprehensive compliance.
- Assess risks using 'get_risk_assessment_matrix' for scoring and prioritization.
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
- Research latest regulatory changes and compliance requirements."""


COMPLIANCE_AGENT_TOOLS = [
    search_knowledge,
    create_audit,
    get_audit,
    update_audit,
    list_audits,
    create_risk,
    get_risk,
    update_risk,
    list_risks,
    get_gdpr_audit_checklist,
    get_risk_assessment_matrix,
    mcp_web_search,
    mcp_web_scrape,
    use_skill,
    list_available_skills,
]


# Singleton instance for direct import
compliance_agent = Agent(
    name="ComplianceRiskAgent",
    model=get_model(),
    description="Legal Counsel - Compliance, risk assessment, and legal guidance",
    instruction=COMPLIANCE_AGENT_INSTRUCTION,
    tools=COMPLIANCE_AGENT_TOOLS,
    sub_agents=[risk_report_agent],
)


def create_compliance_agent(name_suffix: str = "") -> Agent:
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
    
    agent_name = f"ComplianceRiskAgent{name_suffix}" if name_suffix else "ComplianceRiskAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="Legal Counsel - Compliance, risk assessment, and legal guidance",
        instruction=COMPLIANCE_AGENT_INSTRUCTION,
        tools=COMPLIANCE_AGENT_TOOLS,
        sub_agents=[report_agent],
    )

