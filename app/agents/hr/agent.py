# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""HR & Recruitment Agent Definition."""

from app.agents.base_agent import PikarAgent as Agent

from app.agents.shared import get_model, get_routing_model, ROUTING_AGENT_CONFIG
from app.agents.content.tools import search_knowledge
from app.agents.hr.tools import (
    create_job,
    get_job,
    update_job,
    list_jobs,
    add_candidate,
    update_candidate_status,
    list_candidates,
)
from app.agents.enhanced_tools import (
    get_resume_screening_framework,
    generate_interview_questions,
    get_turnover_analysis_framework,
)
from app.mcp.agent_tools import mcp_web_search
from app.agents.tools.agent_skills import HR_SKILL_TOOLS
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.agents.shared_instructions import SKILLS_REGISTRY_INSTRUCTIONS, WEB_RESEARCH_INSTRUCTIONS, CONVERSATION_MEMORY_INSTRUCTIONS, get_widget_instruction_for_agent
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.context_extractor import (
    context_memory_before_model_callback,
    context_memory_after_tool_callback,
)


HR_AGENT_INSTRUCTION = """You are the HR & Recruitment Agent. You focus on hiring, candidate evaluation, and employee management.

CAPABILITIES:
- Screen resumes using 'get_resume_screening_framework' for structured evaluation.
- Generate interview questions using 'generate_interview_questions' for STAR method.
- Analyze turnover using 'get_turnover_analysis_framework' for retention insights.
- Create and manage job postings using 'create_job', 'update_job', 'list_jobs'.
- Manage candidates using 'add_candidate', 'update_candidate_status', 'list_candidates'.
- Draft job descriptions and interview guides.
- Search knowledge base for HR policies.
- Research job market and salary benchmarks using 'mcp_web_search' (privacy-safe).

BEHAVIOR:
- Be fair and unbiased in evaluations.
- Use structured frameworks for consistent candidate assessment.
- Focus on culture fit as well as skills.
- Follow employment law best practices.
- Research industry salary trends and job market conditions.
- When users ask to VIEW or SHOW candidates/jobs, ALWAYS use widget tools to render them visually.
""" + get_widget_instruction_for_agent(
    "HR Manager",
    ["create_table_widget", "create_kanban_board_widget", "create_form_widget", "create_calendar_widget"]
) + SKILLS_REGISTRY_INSTRUCTIONS + WEB_RESEARCH_INSTRUCTIONS + CONVERSATION_MEMORY_INSTRUCTIONS


HR_AGENT_TOOLS = [
    search_knowledge,
    create_job,
    get_job,
    update_job,
    list_jobs,
    add_candidate,
    update_candidate_status,
    list_candidates,
    get_resume_screening_framework,
    generate_interview_questions,
    get_turnover_analysis_framework,
    mcp_web_search,
    *HR_SKILL_TOOLS,
    # UI Widget tools for rendering HR dashboards and tables
    *UI_WIDGET_TOOLS,
    # Context memory tools for conversation continuity
    *CONTEXT_MEMORY_TOOLS,
]


# Singleton instance for direct import
hr_agent = Agent(
    name="HRRecruitmentAgent",
    model=get_routing_model(),
    description="Human Resources Manager - Hiring, candidate evaluation, and employee management",
    instruction=HR_AGENT_INSTRUCTION,
    tools=HR_AGENT_TOOLS,
    generate_content_config=ROUTING_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


def create_hr_agent(name_suffix: str = "") -> Agent:
    """Create a fresh HRRecruitmentAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = f"HRRecruitmentAgent{name_suffix}" if name_suffix else "HRRecruitmentAgent"
    return Agent(
        name=agent_name,
        model=get_routing_model(),
        description="Human Resources Manager - Hiring, candidate evaluation, and employee management",
        instruction=HR_AGENT_INSTRUCTION,
        tools=HR_AGENT_TOOLS,
        generate_content_config=ROUTING_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
