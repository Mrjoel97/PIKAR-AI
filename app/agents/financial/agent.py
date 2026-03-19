# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Financial Analysis Agent Definition."""

from app.agents.base_agent import PikarAgent as Agent
from app.agents.tools.base import sanitize_tools

from app.agents.shared import get_model, DEEP_AGENT_CONFIG
from app.agents.schemas import FinancialReport
from app.agents.financial.tools import get_revenue_stats
from app.mcp.agent_tools import mcp_web_search
from app.agents.tools.invoicing import INVOICE_TOOLS
from app.agents.tools.report_scheduling import REPORT_SCHEDULING_TOOLS
from app.agents.tools.agent_skills import FIN_SKILL_TOOLS
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.agents.shared_instructions import SKILLS_REGISTRY_INSTRUCTIONS, WEB_SEARCH_ONLY_INSTRUCTIONS, CONVERSATION_MEMORY_INSTRUCTIONS, SELF_IMPROVEMENT_INSTRUCTIONS, get_widget_instruction_for_agent, get_error_and_escalation_instructions
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.self_improve import FIN_IMPROVE_TOOLS
from app.agents.context_extractor import (
    context_memory_before_model_callback,
    context_memory_after_tool_callback,
)


# =============================================================================
# Report Sub-Agent (Structured JSON Output)
# =============================================================================

FINANCIAL_REPORT_INSTRUCTION = """You are a financial report generator. Analyze the provided data and produce a structured JSON report.

REQUIREMENTS:
- Include executive summary with key insights
- Calculate profit margin as (revenue - expenses) / revenue * 100
- Determine trend based on month-over-month changes
- Provide actionable recommendations
- Include monthly breakdowns and expense categories for chart rendering

Your output MUST be a valid JSON object matching the FinancialReport schema exactly."""

financial_report_agent = Agent(
    name="FinancialReportAgent",
    model=get_model(),
    description="Generates structured financial reports in JSON format for charts and dashboards",
    instruction=FINANCIAL_REPORT_INSTRUCTION,
    output_schema=FinancialReport,
    output_key="financial_report",
    include_contents="none",
)


# =============================================================================
# Parent Agent (Tool-Enabled with Narrator Pattern)
# =============================================================================

FINANCIAL_AGENT_INSTRUCTION = """You are the Financial Analysis Agent. Your focus is strictly on numbers, revenue, costs, and profit.

CAPABILITIES:
- Get revenue statistics using 'get_revenue_stats'.
- Analyze financial health using use_skill("analyze_financial_statement") for comprehensive frameworks.
- Get forecasting methodologies using use_skill("forecast_revenue_growth").
- Calculate burn rate and runway using use_skill("calculate_burn_rate").
- Generate financial statements using use_skill("financial_statements_generation") for income statements, balance sheets, and cash flow reports.
- Analyze variances using use_skill("variance_analysis") for budget-vs-actual decomposition.
- Prepare journal entries using use_skill("journal_entry_preparation") for proper debit/credit formatting.
- Manage month-end close using use_skill("month_end_close_management") for close checklists and timelines.
- Reconcile accounts using use_skill("account_reconciliation") for GL-to-subledger matching.
- Conduct SOX testing using use_skill("sox_testing_methodology") for internal control testing.
- Support audits using use_skill("audit_support_framework") for SOX 404 compliance documentation.
- Forecast cash flow using use_skill("cash_flow_forecasting") for 13-week rolling forecasts and scenario modeling.
- Search for market data and financial news using 'mcp_web_search' (privacy-safe).
- Generate invoices using 'generate_invoice'.
- Parse PDF invoices using 'parse_invoice_document'.
- Schedule automated financial reports using report scheduling tools (daily, weekly, monthly, quarterly).

STRUCTURED REPORTS:
When asked for a detailed report, dashboard data, or chart-ready output:
1. Delegate to FinancialReportAgent to generate structured JSON
2. After receiving the report data, provide a conversational summary
3. Include the raw JSON in a <json>...</json> block for frontend rendering

Example response format for report requests:
"📊 **Q4 2025 Financial Report**

Revenue reached $125,000 this quarter, up 12% from Q3. With expenses at $87,000, your profit margin is healthy at 30.4%.

**Key Highlights:**
- Revenue trend: Growing
- Largest expense: Payroll (45%)

**Recommendations:**
- Reinvest 15% of profits into marketing
- Review vendor contracts for cost optimization

<json>
{...structured report data for charts/tables...}
</json>
"

BEHAVIOR:
- Be precise and data-driven.
- Use tables to present data when helpful.
- Always warn about risks or cash flow issues.
- Leverage skills for professional analysis frameworks.
- Use web search for up-to-date market data and financial trends.
- When users ask to VIEW or SHOW financial data, ALWAYS use widget tools to render them visually.

## INPUT VALIDATION
Before financial analysis:
- Require at minimum 3 months of financial data for trend analysis and forecasting
- For burn rate calculations, require: monthly expenses, current cash balance, and revenue (if any)
- If data is incomplete, clearly state what's missing and what assumptions you're making

## FINANCIAL RISK ALERTS
- If burn rate suggests runway < 6 months, flag as URGENT with explicit warning
- If profit margin drops below 10%, recommend immediate cost review
- If month-over-month revenue decline exceeds 15%, flag for executive attention
""" + get_widget_instruction_for_agent(
    "Financial Analyst",
    ["create_revenue_chart_widget", "create_table_widget"]
) + SKILLS_REGISTRY_INSTRUCTIONS + WEB_SEARCH_ONLY_INSTRUCTIONS + CONVERSATION_MEMORY_INSTRUCTIONS + SELF_IMPROVEMENT_INSTRUCTIONS + get_error_and_escalation_instructions(
    "Financial Analysis Agent",
    """- Escalate to CFO/finance team for decisions involving investments, loans, or funding rounds
- Escalate to legal for tax compliance questions or financial regulatory matters
- If revenue data retrieval fails, clearly state the data gap and offer to work with manually provided numbers
- Flag any financial projections as estimates with stated assumptions — never present forecasts as guarantees"""
)


FINANCIAL_AGENT_TOOLS = sanitize_tools([
    get_revenue_stats,
    mcp_web_search,
    *FIN_SKILL_TOOLS,
    *INVOICE_TOOLS,
    *REPORT_SCHEDULING_TOOLS,        # 6 - Scheduled financial reports
    # UI Widget tools for rendering charts and visualizations
    *UI_WIDGET_TOOLS,
    # Context memory tools for conversation continuity
    *CONTEXT_MEMORY_TOOLS,
    # Self-improvement tools for autonomous skill iteration
    *FIN_IMPROVE_TOOLS,
])


# Singleton instance for direct import
financial_agent = Agent(
    name="FinancialAnalysisAgent",
    model=get_model(),
    description="CFO / Financial Analyst - Analyzes financial health, revenue, costs, and forecasting",
    instruction=FINANCIAL_AGENT_INSTRUCTION,
    tools=FINANCIAL_AGENT_TOOLS,
    sub_agents=[financial_report_agent],
    generate_content_config=DEEP_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


def create_financial_agent(name_suffix: str = "", output_key: str = None) -> Agent:
    """Create a fresh FinancialAnalysisAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    # Create a fresh report sub-agent for this instance
    report_agent = Agent(
        name=f"FinancialReportAgent{name_suffix}" if name_suffix else "FinancialReportAgent",
        model=get_model(),
        description="Generates structured financial reports in JSON format",
        instruction=FINANCIAL_REPORT_INSTRUCTION,
        output_schema=FinancialReport,
        output_key="financial_report",
        include_contents="none",
    )
    
    agent_name = f"FinancialAnalysisAgent{name_suffix}" if name_suffix else "FinancialAnalysisAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="CFO / Financial Analyst - Analyzes financial health, revenue, costs, and forecasting",
        instruction=FINANCIAL_AGENT_INSTRUCTION,
        tools=FINANCIAL_AGENT_TOOLS,
        sub_agents=[report_agent],
        generate_content_config=DEEP_AGENT_CONFIG,
        output_key=output_key,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )

