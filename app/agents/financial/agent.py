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

from google.adk.agents import Agent

from app.agents.shared import get_model
from app.agents.schemas import FinancialReport
from app.agents.financial.tools import get_revenue_stats
from app.agents.enhanced_tools import (
    use_skill,
    list_available_skills,
    analyze_financial_health,
    get_revenue_forecast_guidance,
    calculate_burn_rate_guidance,
)
from app.mcp.agent_tools import mcp_web_search
from app.agents.tools.invoicing import INVOICE_TOOLS


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
- Analyze financial health using 'analyze_financial_health' for comprehensive frameworks.
- Get forecasting methodologies using 'get_revenue_forecast_guidance'.
- Calculate burn rate and runway using 'calculate_burn_rate_guidance'.
- Search for market data and financial news using 'mcp_web_search' (privacy-safe).
- Access any skill using 'use_skill' with the skill name.
- Generate invoices using 'generate_invoice'.
- Parse PDF invoices using 'parse_invoice_document'.

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
- Use web search for up-to-date market data and financial trends."""


FINANCIAL_AGENT_TOOLS = [
    get_revenue_stats,
    analyze_financial_health,
    get_revenue_forecast_guidance,
    calculate_burn_rate_guidance,
    mcp_web_search,
    use_skill,
    list_available_skills,
    *INVOICE_TOOLS,
]


# Singleton instance for direct import
financial_agent = Agent(
    name="FinancialAnalysisAgent",
    model=get_model(),
    description="CFO / Financial Analyst - Analyzes financial health, revenue, costs, and forecasting",
    instruction=FINANCIAL_AGENT_INSTRUCTION,
    tools=FINANCIAL_AGENT_TOOLS,
    sub_agents=[financial_report_agent],
)


def create_financial_agent(name_suffix: str = "") -> Agent:
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
    )

