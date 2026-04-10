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
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Financial Analysis Agent Definition."""

from app.agents.base_agent import PikarAgent as Agent
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)
from app.agents.financial.tools import (
    generate_financial_forecast,
    get_financial_health_score,
    get_revenue_stats,
    run_financial_scenario,
)
from app.agents.schemas import FinancialReport
from app.agents.shared import DEEP_AGENT_CONFIG, get_model
from app.agents.shared_instructions import (
    CONVERSATION_MEMORY_INSTRUCTIONS,
    SELF_IMPROVEMENT_INSTRUCTIONS,
    SKILLS_REGISTRY_INSTRUCTIONS,
    WEB_SEARCH_ONLY_INSTRUCTIONS,
    get_error_and_escalation_instructions,
    get_widget_instruction_for_agent,
)
from app.agents.tools.agent_skills import FIN_SKILL_TOOLS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS
from app.agents.tools.graph_tools import GRAPH_TOOLS
from app.agents.tools.invoicing import INVOICE_TOOLS
from app.agents.tools.report_scheduling import REPORT_SCHEDULING_TOOLS
from app.agents.tools.self_improve import FIN_IMPROVE_TOOLS
from app.agents.tools.shopify_tools import SHOPIFY_TOOLS
from app.agents.tools.stripe_tools import STRIPE_TOOLS
from app.agents.tools.system_knowledge import (
    search_system_knowledge,  # Phase 12.1: system knowledge
)
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.mcp.agent_tools import mcp_web_search
from app.personas.prompt_fragments import build_persona_policy_block

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

FINANCIAL_AGENT_INSTRUCTION = (
    """You are the Financial Analysis Agent. Your focus is strictly on numbers, revenue, costs, and profit.

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

## FINANCIAL HEALTH SCORE
When users ask about their financial health, overall financial position, or "how am I doing financially":
- Call get_financial_health_score() to get the 0-100 score with explanation
- Present the score prominently with the color indicator
- Explain what factors are driving the score up or down
- If score < 40, proactively suggest specific actions to improve

## SCENARIO MODELING
When users ask "what if" questions about finances (hiring, costs, revenue changes):
- Use run_financial_scenario() with the appropriate scenario_type
- For "What if I hire 2 people?": scenario_type="hire", count=2, amount=5000 (ask user for salary if not specified, default $5,000/mo)
- For "What if we lose 10% of customers?": scenario_type="lose_customers", percentage=10
- For "What about a new $3k/mo tool?": scenario_type="new_expense", amount=3000
- Present both baseline and scenario side-by-side
- Highlight the month where cash goes negative (if applicable)
- Always note this is a projection based on current trends, not a guarantee

## FINANCIAL FORECASTING
When users ask for forecasts, projections, or "what will revenue look like":
- Use generate_financial_forecast() for data-driven projections
- Mention the confidence level (high/medium/low) and how much historical data was used
- If confidence is low (< 3 months data), clearly state the forecast is speculative
- Combine with scenario modeling if the user has specific what-if questions

## CONNECTED FINANCIAL DATA
When the user has connected Stripe or Shopify:
- Use get_stripe_revenue_summary() for real revenue data from Stripe instead of manual records
- Use get_shopify_analytics() for e-commerce metrics (revenue, AOV, top products, order trends)
- Use get_low_stock_products() to proactively alert about inventory issues
- Use trigger_stripe_sync() if the user reports missing recent transactions
- Always indicate when data comes from a connected integration vs manual records

## INVOICE FOLLOW-UP
When the daily briefing includes overdue invoices, or when a user asks about outstanding invoices:
- Mention the overdue invoice count and total outstanding amount
- Present the generated follow-up email drafts
- Offer to customize or send the drafts
- If no overdue invoices, confirm the user's invoicing is current

## TAX AWARENESS
When the daily briefing includes a tax reminder, or when a user asks about taxes:
- Present the quarterly estimated tax amount with the calculation basis
- Note the next deadline
- Remind this is an estimate and recommend consulting a tax professional for precise figures
- Offer to adjust the estimated tax rate if the user's effective rate differs from 25%
"""
    + get_widget_instruction_for_agent(
        "Financial Analyst", ["create_revenue_chart_widget", "create_table_widget"]
    )
    + SKILLS_REGISTRY_INSTRUCTIONS
    + WEB_SEARCH_ONLY_INSTRUCTIONS
    + CONVERSATION_MEMORY_INSTRUCTIONS
    + SELF_IMPROVEMENT_INSTRUCTIONS
    + get_error_and_escalation_instructions(
        "Financial Analysis Agent",
        """- Escalate to CFO/finance team for decisions involving investments, loans, or funding rounds
- Escalate to legal for tax compliance questions or financial regulatory matters
- If revenue data retrieval fails, clearly state the data gap and offer to work with manually provided numbers
- Flag any financial projections as estimates with stated assumptions — never present forecasts as guarantees""",
    )
)


FINANCIAL_AGENT_TOOLS = sanitize_tools(
    [
        get_revenue_stats,
        get_financial_health_score,
        run_financial_scenario,
        generate_financial_forecast,
        mcp_web_search,
        *FIN_SKILL_TOOLS,
        *INVOICE_TOOLS,
        *REPORT_SCHEDULING_TOOLS,  # 6 - Scheduled financial reports
        # UI Widget tools for rendering charts and visualizations
        *UI_WIDGET_TOOLS,
        # Context memory tools for conversation continuity
        *CONTEXT_MEMORY_TOOLS,
        # Self-improvement tools for autonomous skill iteration
        *FIN_IMPROVE_TOOLS,
        # Knowledge graph read access
        *GRAPH_TOOLS,
        # Phase 12.1: system knowledge
        search_system_knowledge,
        # Phase 40: document generation (PDF reports, pitch decks)
        *DOCUMENT_GEN_TOOLS,
        # Phase 41: Stripe revenue sync + Shopify e-commerce
        *STRIPE_TOOLS,
        *SHOPIFY_TOOLS,
    ]
)


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


def create_financial_agent(
    name_suffix: str = "",
    output_key: str = None,
    persona: str | None = None,
) -> Agent:
    """Create a fresh FinancialAnalysisAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.
        output_key: Optional key to store structured output in session state.
        persona: Optional persona tier (solopreneur, startup, sme, enterprise).
            When provided, persona-specific behavioral instructions are appended
            to the agent's system prompt.

    Returns:
        A new Agent instance with no parent assignment.
    """
    # Create a fresh report sub-agent for this instance
    report_agent = Agent(
        name=f"FinancialReportAgent{name_suffix}"
        if name_suffix
        else "FinancialReportAgent",
        model=get_model(),
        description="Generates structured financial reports in JSON format",
        instruction=FINANCIAL_REPORT_INSTRUCTION,
        output_schema=FinancialReport,
        output_key="financial_report",
        include_contents="none",
    )

    agent_name = (
        f"FinancialAnalysisAgent{name_suffix}"
        if name_suffix
        else "FinancialAnalysisAgent"
    )
    instruction = FINANCIAL_AGENT_INSTRUCTION
    persona_block = build_persona_policy_block(
        persona, agent_name="FinancialAnalysisAgent"
    )
    if persona_block:
        instruction = instruction + "\n\n" + persona_block
    return Agent(
        name=agent_name,
        model=get_model(),
        description="CFO / Financial Analyst - Analyzes financial health, revenue, costs, and forecasting",
        instruction=instruction,
        tools=FINANCIAL_AGENT_TOOLS,
        sub_agents=[report_agent],
        generate_content_config=DEEP_AGENT_CONFIG,
        output_key=output_key,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
