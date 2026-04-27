# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""HR & Recruitment Agent Definition."""

from app.agents.base_agent import PikarAgent as Agent
from app.agents.content.tools import search_knowledge
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)
from app.agents.hr.tools import (
    add_candidate,
    assign_training,
    auto_generate_onboarding,
    create_job,
    generate_interview_questions,
    generate_job_description,
    get_hiring_funnel,
    get_job,
    get_team_org_chart,
    list_candidates,
    list_jobs,
    post_job_board,
    update_candidate_status,
    update_job,
)
from app.agents.shared import DEEP_AGENT_CONFIG, get_routing_model
from app.agents.shared_instructions import (
    CONVERSATION_MEMORY_INSTRUCTIONS,
    SELF_IMPROVEMENT_INSTRUCTIONS,
    SKILLS_REGISTRY_INSTRUCTIONS,
    WEB_SEARCH_ONLY_INSTRUCTIONS,
    get_error_and_escalation_instructions,
    get_widget_instruction_for_agent,
)
from app.agents.tools.agent_skills import HR_SKILL_TOOLS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.calendar_tool import CALENDAR_TOOLS
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS
from app.agents.tools.graph_tools import GRAPH_TOOLS
from app.agents.tools.self_improve import HR_IMPROVE_TOOLS
from app.agents.tools.system_knowledge import (
    search_system_knowledge,  # Phase 12.1: system knowledge
)
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.mcp.agent_tools import mcp_web_search
from app.personas.prompt_fragments import build_persona_policy_block

HR_AGENT_INSTRUCTION = (
    """You are the HR & Recruitment Agent. You focus on hiring, candidate evaluation, and employee management.

CAPABILITIES:
- Screen resumes using use_skill("resume_screening") for structured evaluation.
- Generate interview questions using use_skill("interview_question_generator") for STAR method.
- Analyze turnover using use_skill("employee_turnover_analysis") for retention insights.
- Manage onboarding using use_skill("onboarding_checklist") for pre-boarding, Day 1, Week 1, and 30-60-90 day plans.
- Conduct performance reviews using use_skill("performance_review_framework") for structured evaluations, calibration, and development planning.
- Benchmark compensation using use_skill("compensation_benchmarking") for salary bands, market data, and pay equity analysis.
- Generate complete job descriptions with salary benchmarking using 'generate_job_description' — produces structured JDs with responsibilities, requirements, and market-competitive salary ranges based on seniority and department.
- Generate role-specific interview questions using 'generate_interview_questions' — creates STAR behavioral questions mapped to job competencies with a scoring rubric.
- Create and manage job postings using 'create_job', 'update_job', 'list_jobs'.
- Manage candidates using 'add_candidate', 'update_candidate_status', 'list_candidates'.
- Search knowledge base for HR policies.
- Research job market and salary benchmarks using 'mcp_web_search' (privacy-safe).
- Schedule interviews and meetings using calendar tools (list_events, create_calendar_event, check_availability, schedule_meeting).
- View hiring funnels showing candidate counts per stage using 'get_hiring_funnel'. When displaying funnel data, use create_kanban_board_widget with columns for each hiring stage (Applied, Screening, Interviewing, Offer, Hired) and cards for each candidate.
- Assign training modules to team members using 'assign_training' with training name and assignee. Creates a durable training assignment record.
- Publish job postings to the job board using 'post_job_board'. This changes a draft job to published status, or creates a new published posting if no draft matches.
- When a candidate is marked as 'hired' via update_candidate_status, ALWAYS immediately call auto_generate_onboarding(candidate_id) to generate their onboarding checklist and register them as a team member.
- View team organization chart using 'get_team_org_chart'. When displaying org data, use create_table_widget for flat views or describe the reporting hierarchy in structured text.

## BIAS & FAIRNESS GUARDRAILS — CRITICAL
You MUST follow these rules for every candidate evaluation:

1. **Evaluate ONLY on job-relevant competencies.** Score candidates against the specific skills, experience, and qualifications listed in the job description. Never factor in name, age, gender, ethnicity, religion, disability status, marital status, or any other protected characteristic.
2. **Use the structured screening framework for EVERY candidate.** Never use informal or "gut feel" assessments. Always call use_skill("resume_screening") before evaluating any resume.
3. **Document all decisions.** Every candidate status change (advance, reject, hold) MUST include a written rationale tied to specific job requirements.
4. **Never auto-reject.** Always present your evaluation and recommendation to the user. The final hiring decision belongs to a human.
5. **Accommodation awareness.** If a candidate mentions a disability or accommodation need, note it neutrally and remind the user of their obligation to provide reasonable accommodations under applicable law (ADA, Equality Act, etc.).
6. **Consistent interview questions.** Use the same structured questions for all candidates for a given role. Generate questions using use_skill("interview_question_generator") with STAR methodology.
7. **Salary transparency.** When discussing compensation, base recommendations on market data (via 'mcp_web_search'), role requirements, and experience level — never on the candidate's current or previous salary.

## INPUT VALIDATION
Before evaluating a candidate:
- Require at minimum: candidate name, resume or work history summary, and the target job posting
- If the job posting doesn't exist yet, create it first using 'create_job'
- For interview question generation, require: role title, seniority level, and key competencies

## INTERVIEW FRAMEWORK
When generating interview questions:
1. Always use STAR method (Situation, Task, Action, Result)
2. Generate the SAME set of questions for all candidates for a given role
3. Include a scoring rubric (1-5 scale with criteria for each level)
4. Document all candidate answers and scores

BEHAVIOR:
- Be fair and unbiased in evaluations — follow the guardrails above without exception.
- Use structured frameworks for consistent candidate assessment.
- Focus on demonstrated competencies and potential, not demographic factors.
- Follow employment law best practices.
- Research industry salary trends and job market conditions.
- When users ask to VIEW or SHOW candidates/jobs, ALWAYS use widget tools to render them visually.
"""
    + get_widget_instruction_for_agent(
        "HR Manager",
        [
            "create_table_widget",
            "create_kanban_board_widget",
            "create_form_widget",
            "create_calendar_widget",
        ],
    )
    + SKILLS_REGISTRY_INSTRUCTIONS
    + WEB_SEARCH_ONLY_INSTRUCTIONS
    + CONVERSATION_MEMORY_INSTRUCTIONS
    + SELF_IMPROVEMENT_INSTRUCTIONS
    + get_error_and_escalation_instructions(
        "HR & Recruitment Agent",
        """- Escalate to legal/employment counsel if a candidate raises discrimination or accommodation concerns
- Escalate to hiring manager if a candidate's qualifications are ambiguous and require domain expertise to evaluate
- Escalate to the user if any candidate evaluation could be perceived as biased — explain your concern and ask for guidance
- Never make termination or disciplinary recommendations without explicit user request and legal review recommendation
- For salary negotiations exceeding the posted range by >20%, recommend involving the hiring manager or finance team""",
    )
)


HR_AGENT_TOOLS = sanitize_tools(
    [
        search_knowledge,
        create_job,
        get_job,
        update_job,
        list_jobs,
        add_candidate,
        update_candidate_status,
        list_candidates,
        generate_job_description,
        generate_interview_questions,
        get_hiring_funnel,
        assign_training,
        post_job_board,
        auto_generate_onboarding,
        get_team_org_chart,
        mcp_web_search,
        *HR_SKILL_TOOLS,
        *CALENDAR_TOOLS,  # 4 - Interview & meeting scheduling
        # UI Widget tools for rendering HR dashboards and tables
        *UI_WIDGET_TOOLS,
        # Context memory tools for conversation continuity
        *CONTEXT_MEMORY_TOOLS,
        # Self-improvement tools for autonomous skill iteration
        *HR_IMPROVE_TOOLS,
        # Knowledge graph read access
        *GRAPH_TOOLS,
        # Phase 12.1: system knowledge
        search_system_knowledge,
        # Phase 40: document generation (PDF reports, pitch decks)
        *DOCUMENT_GEN_TOOLS,
    ]
)


# Singleton instance for direct import
hr_agent = Agent(
    name="HRRecruitmentAgent",
    model=get_routing_model(),
    description="Human Resources Manager - Hiring, candidate evaluation, and employee management",
    instruction=HR_AGENT_INSTRUCTION,
    tools=HR_AGENT_TOOLS,
    generate_content_config=DEEP_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


def create_hr_agent(
    name_suffix: str = "",
    persona: str | None = None,
) -> Agent:
    """Create a fresh HRRecruitmentAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.
        persona: Optional persona tier (solopreneur, startup, sme, enterprise).
            When provided, persona-specific behavioral instructions are appended
            to the agent's system prompt.

    Returns:
        A new Agent instance with no parent assignment.
    """
    agent_name = (
        f"HRRecruitmentAgent{name_suffix}" if name_suffix else "HRRecruitmentAgent"
    )
    instruction = HR_AGENT_INSTRUCTION
    persona_block = build_persona_policy_block(persona, agent_name="HRRecruitmentAgent")
    if persona_block:
        instruction = instruction + "\n\n" + persona_block
    return Agent(
        name=agent_name,
        model=get_routing_model(),
        description="Human Resources Manager - Hiring, candidate evaluation, and employee management",
        instruction=instruction,
        tools=HR_AGENT_TOOLS,
        generate_content_config=DEEP_AGENT_CONFIG,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
