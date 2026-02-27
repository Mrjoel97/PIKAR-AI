# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Specialized subagents for Strategic Planning."""

from app.agents.base_agent import PikarAgent as Agent
from google.adk.agents import ParallelAgent, SequentialAgent
from app.agents.shared import get_model, DEEP_AGENT_CONFIG, FAST_AGENT_CONFIG

from app.agents.shared_instructions import (
    ELITE_RESEARCH_PERSONA,
    BRAINDUMP_ANALYSIS_INSTRUCTIONS,
    CONVERSATION_MEMORY_INSTRUCTIONS,
    get_widget_instruction_for_agent,
)
from app.agents.tools.brain_dump import get_braindump_transcript, save_braindump_analysis
from app.agents.tools.deep_research import DEEP_RESEARCH_TOOLS
from app.mcp.agent_tools import mcp_web_scrape, mcp_web_search
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.context_extractor import (
    context_memory_before_model_callback,
    context_memory_after_tool_callback,
)


# ==========================================
# 1. BRAINDUMP SUITE
# ==========================================

# Transcriber Agent - Focuses on high-fidelity audio/video processing
BRAINDUMP_TRANSCRIBER_INSTRUCTION = (
    BRAINDUMP_ANALYSIS_INSTRUCTIONS
    + """
You are the Braindump Transcriber. Your primary goal is to convert audio/video files into a perfect transcript.
1. **SPEAK**: Start by telling the user you are transcribing their recording (e.g., "I'm transcribing your recording now...").
2. **TOOL**: Use `get_braindump_transcript` to get the raw text from the file.
3. **OUTPUT**: Present the full transcript clearly to the user once it's ready.
"""
    + CONVERSATION_MEMORY_INSTRUCTIONS
)


def create_braindump_transcriber():
    return Agent(
        name="BraindumpTranscriber",
        model=get_model(),
        description="Transcribes raw audio/video brain dumps into structured text.",
        instruction=BRAINDUMP_TRANSCRIBER_INSTRUCTION,
        tools=[get_braindump_transcript, *CONTEXT_MEMORY_TOOLS],
        generate_content_config=DEEP_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# Insight Agent - Focuses on themes and business logic
BRAINDUMP_INSIGHT_INSTRUCTION = (
    BRAINDUMP_ANALYSIS_INSTRUCTIONS
    + """
You are the Strategic Insight Analyst. Use the provided transcript to extract strategic insights.
1. **SPEAK**: Tell the user you are analyzing the transcript for themes and insights.
2. **ANALYZE**: Extract Core Business Idea, Themes, Market Assumptions, and Gaps.
3. **OUTPUT**: Present these insights clearly in the chat.
4. **SAVE**: You MUST use `save_braindump_analysis` to save your findings to the Knowledge Vault (category: "Brain Dump Analysis").
"""
    + CONVERSATION_MEMORY_INSTRUCTIONS
)


def create_braindump_insight_agent():
    return Agent(
        name="StrategicInsightAgent",
        model=get_model(),
        description="Extracts strategic themes and business logic from braindump transcripts.",
        instruction=BRAINDUMP_INSIGHT_INSTRUCTION,
        tools=[save_braindump_analysis, *CONTEXT_MEMORY_TOOLS],
        generate_content_config=DEEP_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# Action Item Agent - Focuses on tactical execution
ACTION_ITEM_INSTRUCTION = (
    BRAINDUMP_ANALYSIS_INSTRUCTIONS
    + """
You are the Execution Architect. Use the provided transcript to build an action-oriented validation plan.
1. **SPEAK**: Tell the user you are creating a validation plan and action items.
2. **ANALYZE**: Extract Immediate Action Items, Next-Step Experiments, Resource Requirements, and Risks.
3. **OUTPUT**: Present this plan clearly in the chat.
4. **SAVE**: You MUST use `save_braindump_analysis` to save the plan to the Knowledge Vault (category: "Validation Plan").
"""
    + CONVERSATION_MEMORY_INSTRUCTIONS
)


def create_action_item_agent():
    return Agent(
        name="ExecutionArchitectAgent",
        model=get_model(),
        description="Converts raw ideas into actionable tasks and experiments.",
        instruction=ACTION_ITEM_INSTRUCTION,
        tools=[save_braindump_analysis, *CONTEXT_MEMORY_TOOLS],
        generate_content_config=DEEP_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def create_braindump_processing_suite():
    return ParallelAgent(
        name="BraindumpProcessingSuite",
        description="Processes braindump transcript for insights and actions concurrently.",
        sub_agents=[create_braindump_insight_agent(), create_action_item_agent()],
    )


def create_braindump_pipeline():
    return SequentialAgent(
        name="BraindumpPipeline",
        description="End-to-end braindump processing: Transcribe -> Parallel Analysis",
        sub_agents=[create_braindump_transcriber(), create_braindump_processing_suite()],
    )


# ==========================================
# 2. RESEARCH SUITE (ELITE PERSONA)
# ==========================================

# Market Analyst - TAM/SAM/SOM & Trends
MARKET_ANALYST_INSTRUCTION = (
    ELITE_RESEARCH_PERSONA
    + """
You are the Market Analyst (McKinsey/Goldman Sachs level).
Your job is to provide:
- Market Sizing (TAM, SAM, SOM) with top-down/bottom-up methodology.
- Macro/Micro Industry Trends (Regulatory, Tech, Social).
- 5-year CAGR projections.

**SAVE RESULTS**: Use `save_braindump_analysis` with category="Research" to save your report.
"""
    + get_widget_instruction_for_agent(
        "Market Analyst", ["create_table_widget", "create_revenue_chart_widget"]
    )
    + CONVERSATION_MEMORY_INSTRUCTIONS
)


def create_market_analyst_agent():
    return Agent(
        name="MarketAnalystAgent",
        model=get_model(),
        description="Provides elite market sizing, trend analysis, and industry forecasts.",
        instruction=MARKET_ANALYST_INSTRUCTION,
        tools=[
            save_braindump_analysis,
            *DEEP_RESEARCH_TOOLS,
            mcp_web_search,
            *CONTEXT_MEMORY_TOOLS,
        ],
        generate_content_config=DEEP_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# Competitive Researcher - Moats & SWOT
COMPETITIVE_RESEARCHER_INSTRUCTION = (
    ELITE_RESEARCH_PERSONA
    + """
You are the Competitive Strategy Expert (Bain/Deloitte level).
Your job is to provide:
- Deep dive into Direct and Indirect Competitors.
- White Space Analysis (Gaps in the market).
- Competitive Moats & Defensive Strategy.
- Porter's Five Forces & SWOT Analysis.

**SAVE RESULTS**: Use `save_braindump_analysis` with category="Research" to save your report.
"""
    + get_widget_instruction_for_agent("Competitive Researcher", ["create_table_widget"])
    + CONVERSATION_MEMORY_INSTRUCTIONS
)


def create_competitive_researcher_agent():
    return Agent(
        name="CompetitiveResearcherAgent",
        model=get_model(),
        description="Analyzes the competitive landscape, moats, and strategic positioning.",
        instruction=COMPETITIVE_RESEARCHER_INSTRUCTION,
        tools=[
            save_braindump_analysis,
            *DEEP_RESEARCH_TOOLS,
            mcp_web_scrape,
            *CONTEXT_MEMORY_TOOLS,
        ],
        generate_content_config=DEEP_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# Consumer Persona Expert
CONSUMER_EXPERT_INSTRUCTION = (
    ELITE_RESEARCH_PERSONA
    + """
You are the Consumer Research Specialist.
Your job is to provide:
- 4 Detailed Customer Personas (Demographics, Psychographics, Pain Points).
- Full Customer Journey Mapping (Awareness to Churn).
- Emotional Curve Visualization (text-based).

**SAVE RESULTS**: Use `save_braindump_analysis` with category="Research" to save your report.
"""
    + get_widget_instruction_for_agent("Consumer Expert", ["create_table_widget"])
    + CONVERSATION_MEMORY_INSTRUCTIONS
)


def create_consumer_expert_agent():
    return Agent(
        name="ConsumerExpertAgent",
        model=get_model(),
        description="Builds detailed customer personas and maps end-to-end user journeys.",
        instruction=CONSUMER_EXPERT_INSTRUCTION,
        tools=[save_braindump_analysis, *DEEP_RESEARCH_TOOLS, *CONTEXT_MEMORY_TOOLS],
        generate_content_config=DEEP_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def create_research_suite():
    return ParallelAgent(
        name="ResearchSuite",
        description="Elite cross-functional research team providing market, competitive, and consumer analysis in parallel.",
        sub_agents=[
            create_market_analyst_agent(),
            create_competitive_researcher_agent(),
            create_consumer_expert_agent(),
        ],
    )


# Singletons for generic use (will be used by StrategicPlanningAgent)
braindump_pipeline = create_braindump_pipeline()
research_suite = create_research_suite()
