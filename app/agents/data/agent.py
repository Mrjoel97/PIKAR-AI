# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Data Analysis Agent Definition."""

from app.agents.base_agent import PikarAgent as Agent

from app.agents.shared import get_model, DEEP_AGENT_CONFIG
from app.agents.schemas import DataInsight
from app.agents.content.tools import search_knowledge
from app.agents.financial.tools import get_revenue_stats
from app.agents.data.tools import (
    track_event,
    query_events,
    create_report,
    list_reports,
)
from app.agents.enhanced_tools import (
    get_anomaly_detection_guidance,
    get_trend_analysis_framework,
    design_rag_pipeline,
)
from app.mcp.agent_tools import mcp_web_search, mcp_web_scrape
from app.agents.tools.agent_skills import DATA_SKILL_TOOLS
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.agents.shared_instructions import SKILLS_REGISTRY_INSTRUCTIONS, WEB_RESEARCH_INSTRUCTIONS, CONVERSATION_MEMORY_INSTRUCTIONS, get_widget_instruction_for_agent
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.context_extractor import (
    context_memory_before_model_callback,
    context_memory_after_tool_callback,
)


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

DATA_AGENT_INSTRUCTION = """You are the Data Analysis Agent. You focus on data validation, anomaly detection, and forecasting.

CAPABILITIES:
- Detect anomalies using 'get_anomaly_detection_guidance' for statistical methods.
- Analyze trends using 'get_trend_analysis_framework' for trend identification.
- Track key events using 'track_event'.
- Analyze data by querying events with 'query_events'.
- Generate and save insights using 'create_report' and 'list_reports'.
- Create forecasts and predictions.
- Research industry benchmarks using 'mcp_web_search' (privacy-safe).
- Extract data from external sources using 'mcp_web_scrape'.

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
""" + get_widget_instruction_for_agent(
    "Data Analyst",
    ["create_table_widget", "create_revenue_chart_widget", "create_kanban_board_widget"]
) + SKILLS_REGISTRY_INSTRUCTIONS + WEB_RESEARCH_INSTRUCTIONS + CONVERSATION_MEMORY_INSTRUCTIONS


DATA_AGENT_TOOLS = [
    get_revenue_stats,
    search_knowledge,
    track_event,
    query_events,
    create_report,
    list_reports,
    get_anomaly_detection_guidance,
    get_trend_analysis_framework,
    design_rag_pipeline,
    mcp_web_search,
    mcp_web_scrape,
    *DATA_SKILL_TOOLS,
    # UI Widget tools for rendering data visualizations
    *UI_WIDGET_TOOLS,
    # Context memory tools for conversation continuity
    *CONTEXT_MEMORY_TOOLS,
]


# Singleton instance for direct import
data_agent = Agent(
    name="DataAnalysisAgent",
    model=get_model(),
    description="Data Analyst - Data validation, anomaly detection, and forecasting",
    instruction=DATA_AGENT_INSTRUCTION,
    tools=DATA_AGENT_TOOLS,
    sub_agents=[data_insight_agent],
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
    
    agent_name = f"DataAnalysisAgent{name_suffix}" if name_suffix else "DataAnalysisAgent"
    return Agent(
        name=agent_name,
        model=get_model(),
        description="Data Analyst - Data validation, anomaly detection, and forecasting",
        instruction=DATA_AGENT_INSTRUCTION,
        tools=DATA_AGENT_TOOLS,
        sub_agents=[insight_agent],
        generate_content_config=DEEP_AGENT_CONFIG,
        output_key=output_key,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )

