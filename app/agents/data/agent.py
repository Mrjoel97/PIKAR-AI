# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Data Analysis Agent Definition."""

from app.agents.base_agent import PikarAgent as Agent
from app.agents.content.tools import search_knowledge
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)
from app.agents.data.tools import (
    create_report,
    list_reports,
    query_events,
    track_event,
)
from app.agents.enhanced_tools import design_rag_pipeline
from app.agents.financial.tools import get_revenue_stats
from app.agents.schemas import DataInsight
from app.agents.shared import (
    DEEP_AGENT_CONFIG,
    get_fast_model,
    get_model,
    get_routing_model,
)
from app.agents.shared_instructions import (
    CONVERSATION_MEMORY_INSTRUCTIONS,
    SELF_IMPROVEMENT_INSTRUCTIONS,
    SKILLS_REGISTRY_INSTRUCTIONS,
    WEB_RESEARCH_INSTRUCTIONS,
    get_error_and_escalation_instructions,
    get_widget_instruction_for_agent,
)
from app.agents.tools.agent_skills import DATA_SKILL_TOOLS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.google_sheets import GOOGLE_SHEETS_TOOLS
from app.agents.tools.self_improve import DATA_IMPROVE_TOOLS
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.mcp.agent_tools import mcp_web_scrape, mcp_web_search

# =============================================================================
# Report Sub-Agent (Structured JSON Output)
# =============================================================================

DATA_INSIGHT_INSTRUCTION = """You are a data insight generator. Analyze metrics and produce structured findings.

REQUIREMENTS:
- Compare current vs previous values
- Calculate percentage change
- Detect anomalies using statistical methods
- Provide human-readable insights
- Include time series data for trend charts when available

Your output MUST be a valid JSON object matching the DataInsight schema exactly."""

data_insight_agent = Agent(
    name="DataInsightAgent",
    model=get_model(),
    description="Produces structured data analysis insights for dashboards and reports",
    instruction=DATA_INSIGHT_INSTRUCTION,
    output_schema=DataInsight,
    output_key="data_insight",
    include_contents="none",
)


# =============================================================================
# Parent Agent (Tool-Enabled with Narrator Pattern)
# =============================================================================

DATA_AGENT_INSTRUCTION = (
    """You are the Data Analysis Agent. You focus on data validation, anomaly detection, and forecasting.

CAPABILITIES:
- Detect anomalies using use_skill("anomaly_detection") for statistical methods.
- Analyze trends using use_skill("trend_analysis") for trend identification.
- Write SQL queries using use_skill("sql_query_writing") for optimized, dialect-aware queries.
- Explore datasets using use_skill("data_exploration") for profiling, distributions, and data dictionaries.
- Apply statistical methods using use_skill("statistical_analysis_methods") for hypothesis testing, regression, and time series.
- Create visualizations using use_skill("data_visualization_best_practices") for chart selection and design principles.
- Validate data using use_skill("data_validation_qa") for quality checks and methodology review.
- Build dashboards using use_skill("dashboard_building") for interactive HTML dashboards with charts.
- Run analysis workflows using use_skill("data_analysis_workflow") for end-to-end data projects.
- Track key events using 'track_event'.
- Analyze data by querying events with 'query_events'.
- Generate and save insights using 'create_report' and 'list_reports'.
- Create forecasts and predictions.
- Research industry benchmarks using 'mcp_web_search' (privacy-safe).
- Extract data from external sources using 'mcp_web_scrape'.
- Connect to and analyze Google Sheets spreadsheets for data ingestion and analysis.

STRUCTURED DATA INSIGHTS:
When asked for a detailed metric analysis or dashboard data:
1. Delegate to DataInsightAgent to generate structured JSON
2. After receiving the insight, provide a conversational summary
3. Include the raw JSON in a <json>...</json> block for chart rendering

Example response format for data insights:
"📈 **Metric Analysis: Monthly Active Users**

MAU increased from 12,500 to 14,200 (+13.6%) this month. This is a **stable upward trend** with no anomalies detected.

**Key Insight:**
Growth is consistent with seasonal patterns and recent marketing campaigns.

**Recommendation:**
Continue current acquisition strategy; consider A/B testing new onboarding flows.

<json>
{...structured metric data for charts...}
</json>
"

BEHAVIOR:
- Be data-driven and objective.
- Use proven statistical methods for anomaly detection.
- Always validate data quality before analysis.
- Present findings clearly with visualizations/reports.
- Research external data sources for comparison and validation.
- When users ask to VIEW or SHOW data, ALWAYS use widget tools to render them visually.

## DATA QUALITY CHECKS
Before any analysis, validate:
1. Minimum sample size: 30 observations for trend analysis, 100 for anomaly detection
2. Missing values: flag if >20% of a key field is missing; do not analyze if >50% missing
3. Outliers: flag values beyond 3 standard deviations — investigate before including/excluding
4. Report all assumptions and data quality limitations alongside results

## STATISTICAL REPORTING
- Always report confidence intervals when making forecasts
- Flag results where sample size is insufficient for statistical significance
- Clearly distinguish correlation from causation in trend analysis
"""
    + get_widget_instruction_for_agent(
        "Data Analyst",
        [
            "create_table_widget",
            "create_revenue_chart_widget",
            "create_kanban_board_widget",
        ],
    )
    + SKILLS_REGISTRY_INSTRUCTIONS
    + WEB_RESEARCH_INSTRUCTIONS
    + CONVERSATION_MEMORY_INSTRUCTIONS
    + SELF_IMPROVEMENT_INSTRUCTIONS
    + get_error_and_escalation_instructions(
        "Data Analysis Agent",
        """- Escalate to data engineering if data quality issues indicate a pipeline or ingestion problem
- Escalate to the user if analysis results are ambiguous or could support contradictory conclusions
- If data retrieval tools fail, clearly state what data is unavailable and offer to work with sample/manual data
- Flag anomalies that could indicate fraud, security issues, or system errors for immediate review""",
    )
)


# =============================================================================
# SheetsAgent Sub-Agent (Google Sheets integration)
# =============================================================================

_SHEETS_TOOLS = sanitize_tools(
    [
        *GOOGLE_SHEETS_TOOLS,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_SHEETS_INSTRUCTION = """You are the Google Sheets sub-agent. You handle all spreadsheet operations:
- Create new spreadsheets and worksheets
- Read, write, and update cell data
- Import data into sheets from various sources
- Apply formulas and formatting
- Connect spreadsheets for ongoing data sync
Always verify data types before writing to avoid format errors."""


def _create_sheets_agent(suffix: str = "") -> Agent:
    """Create a Google Sheets sub-agent."""
    return Agent(
        name=f"SheetsAgent{suffix}",
        model=get_fast_model(),
        description="Google Sheets operations — create, read, write, and manage spreadsheet data",
        instruction=_SHEETS_INSTRUCTION,
        tools=_SHEETS_TOOLS,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# =============================================================================
# Data Parent Agent (router — ~15 tools + 2 sub-agents)
# =============================================================================

DATA_AGENT_TOOLS = sanitize_tools(
    [
        get_revenue_stats,
        search_knowledge,
        track_event,
        query_events,
        create_report,
        list_reports,
        design_rag_pipeline,
        mcp_web_search,
        mcp_web_scrape,
        *DATA_SKILL_TOOLS,
        *UI_WIDGET_TOOLS,
        *CONTEXT_MEMORY_TOOLS,
        *DATA_IMPROVE_TOOLS,
    ]
)


# Singleton instance for direct import
data_agent = Agent(
    name="DataAnalysisAgent",
    model=get_routing_model(),
    description="Data Analyst — analysis, reporting, and forecasting (routes to SheetsAgent for spreadsheet ops)",
    instruction=DATA_AGENT_INSTRUCTION,
    tools=DATA_AGENT_TOOLS,
    sub_agents=[data_insight_agent, _create_sheets_agent()],
    generate_content_config=DEEP_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


def create_data_agent(name_suffix: str = "", output_key: str = None) -> Agent:
    """Create a fresh DataAnalysisAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    # Create a fresh insight sub-agent for this instance
    insight_agent = Agent(
        name=f"DataInsightAgent{name_suffix}" if name_suffix else "DataInsightAgent",
        model=get_model(),
        description="Produces structured data analysis insights",
        instruction=DATA_INSIGHT_INSTRUCTION,
        output_schema=DataInsight,
        output_key="data_insight",
        include_contents="none",
    )

    agent_name = (
        f"DataAnalysisAgent{name_suffix}" if name_suffix else "DataAnalysisAgent"
    )
    return Agent(
        name=agent_name,
        model=get_routing_model(),
        description="Data Analyst — analysis, reporting, and forecasting (routes to SheetsAgent for spreadsheet ops)",
        instruction=DATA_AGENT_INSTRUCTION,
        tools=DATA_AGENT_TOOLS,
        sub_agents=[insight_agent, _create_sheets_agent(name_suffix)],
        generate_content_config=DEEP_AGENT_CONFIG,
        output_key=output_key,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
