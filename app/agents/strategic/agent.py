# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Strategic Planning Agent Definition."""

from app.agents.base_agent import PikarAgent as Agent
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)
from app.agents.enhanced_tools import product_roadmap_guide
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
from app.agents.strategic.tools import (
    advance_initiative_phase,
    create_initiative,
    create_initiative_from_template,
    get_initiative,
    journey_metrics,
    list_initiative_templates,
    list_initiatives,
    start_initiative_from_idea,
    start_journey_workflow,
    suggest_workflows,
    update_initiative,
)
from app.agents.tools.adaptive_workflows import ADAPTIVE_TOOLS
from app.agents.tools.agent_skills import STRAT_SKILL_TOOLS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.boardroom import convene_board_meeting
from app.agents.tools.brain_dump import (
    get_braindump_document,
    process_brain_dump,
    process_brainstorm_conversation,
)
from app.agents.tools.briefing_tools import BRIEFING_TOOLS
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS
from app.agents.tools.graph_tools import GRAPH_TOOLS
from app.agents.tools.self_improve import STRAT_IMPROVE_TOOLS
from app.agents.tools.skill_builder import create_operational_skill
from app.agents.tools.system_knowledge import (
    search_system_knowledge,  # Phase 12.1: system knowledge
)
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS
from app.agents.tools.workflows import approve_workflow_step, get_workflow_status
from app.mcp.agent_tools import mcp_web_scrape, mcp_web_search
from app.orchestration.knowledge_tools import KNOWLEDGE_INJECTION_TOOLS
from app.personas.prompt_fragments import build_persona_policy_block
from app.workflows.initiative_orchestrator import orchestrate_initiative_phase

STRATEGIC_AGENT_INSTRUCTION = (
    """You are the Strategic Planning Agent. You help set long-term goals (OKRs) and track initiatives through the 5-phase Initiative Framework.

## INITIATIVE FRAMEWORK (5 Phases)
Every initiative goes through these phases:
1. **Ideation and Empathy** - Capture idea, define problem, identify audience
2. **Validation and Research** - Market research, competitor analysis, feasibility
3. **Prototype and Test** - Build MVP, test with users, iterate
4. **Build Product/Service** - Full implementation, resource allocation, execution
5. **Scale Business** - Growth strategy, marketing, optimization

## AUTO-INITIATIVE DETECTION
When a user shares a business idea, product concept, or service idea:
1. Acknowledge the idea enthusiastically
2. Auto-create an initiative using `start_initiative_from_idea`
3. Render the initiative dashboard widget to show the new initiative
4. Guide the user through Phase 1 (Ideation and Empathy)
5. Ask clarifying questions to flesh out the idea

## BRAIN DUMP & BRAINSTORMING processing
**Scenario A: Audio/Video File Upload**
When the user uploads a "Brain Dump" audio/video file (indicated by a system message with a file path):
1. **ACKNOWLEDGE**: Immediately tell the user you've received the recording and are starting the analysis (e.g., "I've received your brain dump. I'm starting the transcription and analysis now...").
2. **DELEGATE**: Delegate to the `BraindumpPipeline` subagent. It will handle transcription and parallel analysis (Insights and Action Items) and its results will appear in the chat.
3. **CONCLUSION**: Once the sub-agents finish, summarize the key takeaways.
4. **AUTO-STRATEGY**: Automatically invoke the `use_skill` tool with `skill_name="comprehensive_business_strategy"` to begin generating a full business strategy. Follow its pacing instructions.

**Scenario B: Interactive Brainstorming**
When the user enters "Brainstorm Mode" or asks to brainstorm an idea:
1. Adopt an "Interviewer" persona. Ask probing questions one by one to flesh out the idea (e.g., "Whose problem are we fitting?", "How is this different from X?").
2. **STATUS UPDATES**: Periodically remind the user that you are capturing their thoughts into a structured validation plan.
3. **DO NOT** create an initiative yet unless explicitly asked.
4. When the user says they are done or clicks "Conclude", OR when you receive a system message containing the session transcript:
5. Call `process_brainstorm_conversation` with the transcript.
6. Present the resulting "Validation Plan" to the user and confirm it's been saved to the Knowledge Vault.
7. Ask if they want to turn this plan into a formal Initiative.
8. You can also use `ResearchSuite` to validate the brainstormed ideas.

**Scenario C: Saved Brain Dump Reopened in Chat**
When the user provides a brain dump document ID from the Brain Dump interface:
1. Use `get_braindump_document` to retrieve the exact markdown document by ID.
2. Summarize what it contains (Transcript, Brain Dump, Validation Plan, or Research).
3. Continue with validation and research from that document context.

## ELITE RESEARCH SUITE
When the user asks for "research", "market analysis", "competitor deep dives", or to "create a plan" for an idea:
1. Delegate to the `ResearchSuite`. This suite consists of three specialized agents:
   - **MarketAnalystAgent**: TAM/SAM/SOM and growth trends.
   - **CompetitiveResearcherAgent**: Competitors, moats, and SWOT.
   - **ConsumerExpertAgent**: Personas and journey maps.
2. The results will be generated in parallel. Synthesize these elite findings into a cohesive strategy.
3. Also trigger the `use_skill` tool with `skill_name="comprehensive_business_strategy"` for the full 11-section playbook.

## CAPABILITIES:
- Delegate complex processing to `BraindumpPipeline` and `ResearchSuite`.
- Create initiatives using `create_initiative` or auto-create from ideas using `start_initiative_from_idea`.
- View initiative details using `get_initiative`.
- Update initiative status, progress, and phase using `update_initiative`.
- Advance initiative to next phase using `advance_initiative_phase`.
- List all initiatives using `list_initiatives`.
- Browse and use templates using `list_initiative_templates` and `create_initiative_from_template`.
- For initiatives created from a Workflow Journey: ... (standard logic).
- Research market trends using `mcp_web_search` (privacy-safe).
- Extract competitor information using `mcp_web_scrape`.
- Design new standard operating procedures using `generate_workflow_template`.
- Get product roadmap guidance using `product_roadmap_guide`.
- Create new strategic skills and workflows using `create_operational_skill` when existing capabilities are insufficient.
- Convene a boardroom debate using `convene_board_meeting` when the user asks for a board meeting, strategic debate, or multi-perspective analysis. The tool runs a 2-round debate between CMO, CFO, and CEO personas and produces a Board Packet with recommendations, risks, and next steps.

## STATUS VOCABULARY:
not_started, in_progress, completed, blocked, on_hold

## BEHAVIOR:
- Focus on the "Why" and "How".
- Force the user to prioritize - not everything can be #1.
- Think long-term and strategic.
- Track progress on all active initiatives.
- Use web search for market intelligence and competitive analysis.
- When users ask to VIEW or SHOW initiatives, ALWAYS use widget tools to render them visually.
- When a user shares an idea, ALWAYS use `start_initiative_from_idea` to auto-create it.
- Guide users through the initiative phases, asking for input at approval gates.

## INITIATIVE QUALITY GATES
Before advancing an initiative to the next phase, verify:
- **Phase 1→2**: Problem statement defined, target audience identified, at least 3 assumptions listed for validation
- **Phase 2→3**: Market research completed (TAM/SAM/SOM), at least 2 competitors analyzed, feasibility assessment documented
- **Phase 3→4**: MVP defined, user testing plan created, success metrics established
- **Phase 4→5**: Core product built, initial user feedback collected, unit economics calculated
If prerequisites are not met, inform the user what's missing before advancing.
"""
    + get_widget_instruction_for_agent(
        "Strategic Planning Agent",
        [
            "create_initiative_dashboard_widget",
            "create_kanban_board_widget",
            "create_product_launch_widget",
            "create_workflow_builder_widget",
        ],
    )
    + SKILLS_REGISTRY_INSTRUCTIONS
    + WEB_RESEARCH_INSTRUCTIONS
    + CONVERSATION_MEMORY_INSTRUCTIONS
    + SELF_IMPROVEMENT_INSTRUCTIONS
    + get_error_and_escalation_instructions(
        "Strategic Planning Agent",
        """- Escalate to the user if an initiative has been blocked for more than 2 weeks with no resolution path
- Escalate to finance/CFO if an initiative requires investment exceeding the user's stated budget
- If brain dump transcription fails, offer manual summary entry as a fallback
- For research results that are contradictory or inconclusive, present both sides and let the user decide""",
    )
)


# =============================================================================
# Sub-Agent Definitions
# =============================================================================

# --- KnowledgeVaultAgent (7 tools) — manages the business knowledge base ---
_KNOWLEDGE_TOOLS = sanitize_tools(
    [
        *KNOWLEDGE_INJECTION_TOOLS,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_KNOWLEDGE_INSTRUCTION = """You are the Knowledge Vault sub-agent. You manage the business knowledge base:
- Add business knowledge, product info, company info, processes/policies, and FAQs
- List and search existing knowledge entries
Always categorize knowledge appropriately and include enough context for future retrieval."""


def _create_knowledge_agent(suffix: str = "") -> Agent:
    """Create a Knowledge Vault sub-agent."""
    return Agent(
        name=f"KnowledgeVaultAgent{suffix}",
        model=get_fast_model(),
        description="Knowledge base management — add and organize business knowledge, products, policies, and FAQs",
        instruction=_KNOWLEDGE_INSTRUCTION,
        tools=_KNOWLEDGE_TOOLS,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# --- InitiativeOpsAgent (10 tools) — handles initiative lifecycle operations ---
_INITIATIVE_OPS_TOOLS = sanitize_tools(
    [
        start_initiative_from_idea,
        advance_initiative_phase,
        list_initiative_templates,
        create_initiative_from_template,
        orchestrate_initiative_phase,
        get_workflow_status,
        approve_workflow_step,
        start_journey_workflow,
        suggest_workflows,
        journey_metrics,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_INITIATIVE_OPS_INSTRUCTION = """You are the Initiative Operations sub-agent. You handle initiative lifecycle execution:
- Start initiatives from ideas or templates
- Advance initiatives through the 5-phase framework (Ideation → Validation → Prototype → Build → Scale)
- Orchestrate initiative phases with workflow automation
- Start journey workflows and suggest relevant workflows
- Track journey quality metrics
- Check workflow status and approve workflow steps
Always verify the current phase before advancing to ensure prerequisites are met."""


def _create_initiative_ops_agent(suffix: str = "") -> Agent:
    """Create an Initiative Operations sub-agent."""
    return Agent(
        name=f"InitiativeOpsAgent{suffix}",
        model=get_model(),
        description="Initiative lifecycle — start, advance, orchestrate initiatives and journey workflows",
        instruction=_INITIATIVE_OPS_INSTRUCTION,
        tools=_INITIATIVE_OPS_TOOLS,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


# =============================================================================
# Strategic Parent Agent (router — ~15 tools + 4 sub-agents)
# =============================================================================

STRATEGIC_AGENT_TOOLS = sanitize_tools(
    [
        # Initiative CRUD (parent handles direct queries)
        create_initiative,
        start_initiative_from_idea,
        get_initiative,
        update_initiative,
        list_initiatives,
        # Brain dump & brainstorm (direct — quick access)
        get_braindump_document,
        process_brainstorm_conversation,
        process_brain_dump,
        # Strategic tools
        convene_board_meeting,
        create_operational_skill,
        product_roadmap_guide,
        mcp_web_search,
        mcp_web_scrape,
        # Briefing (daily executive briefing)
        *BRIEFING_TOOLS,
        # Cross-cutting
        *STRAT_SKILL_TOOLS,
        *ADAPTIVE_TOOLS,
        *UI_WIDGET_TOOLS,
        *CONTEXT_MEMORY_TOOLS,
        *STRAT_IMPROVE_TOOLS,
        # Knowledge graph read access
        *GRAPH_TOOLS,
        # Phase 12.1: system knowledge
        search_system_knowledge,
        # Phase 40: document generation (PDF reports, pitch decks)
        *DOCUMENT_GEN_TOOLS,
    ]
)


from app.agents.strategic.subagents import (
    create_braindump_pipeline,
    create_research_suite,
)


def _build_strategic_sub_agents(suffix: str = ""):
    """Build all 4 sub-agents for StrategicPlanningAgent."""
    return [
        create_braindump_pipeline(),
        create_research_suite(),
        _create_knowledge_agent(suffix),
        _create_initiative_ops_agent(suffix),
    ]


_STRATEGIC_SUB_AGENTS = _build_strategic_sub_agents()

# Singleton instance for direct import
strategic_agent = Agent(
    name="StrategicPlanningAgent",
    model=get_routing_model(),
    description="Chief Strategy Officer — routes to 4 sub-agents: research, brain dump, knowledge vault, initiative ops",
    instruction=STRATEGIC_AGENT_INSTRUCTION,
    tools=STRATEGIC_AGENT_TOOLS,
    sub_agents=_STRATEGIC_SUB_AGENTS,
    generate_content_config=DEEP_AGENT_CONFIG,
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


def create_strategic_agent(
    name_suffix: str = "",
    output_key: str = None,
    persona: str | None = None,
) -> Agent:
    """Create a fresh StrategicPlanningAgent instance for workflow use.

    Args:
        name_suffix: Optional suffix to differentiate agent instances in workflows.
        output_key: Optional key to store structured output in session state.
        persona: Optional persona tier (solopreneur, startup, sme, enterprise).
            When provided, persona-specific behavioral instructions are appended
            to the agent's system prompt.
    """
    agent_name = (
        f"StrategicPlanningAgent{name_suffix}"
        if name_suffix
        else "StrategicPlanningAgent"
    )
    instruction = STRATEGIC_AGENT_INSTRUCTION
    persona_block = build_persona_policy_block(
        persona, agent_name="StrategicPlanningAgent"
    )
    if persona_block:
        instruction = instruction + "\n\n" + persona_block
    return Agent(
        name=agent_name,
        model=get_routing_model(),
        description="Chief Strategy Officer — routes to 4 sub-agents: research, brain dump, knowledge vault, initiative ops",
        instruction=instruction,
        tools=STRATEGIC_AGENT_TOOLS,
        sub_agents=_build_strategic_sub_agents(name_suffix),
        generate_content_config=DEEP_AGENT_CONFIG,
        output_key=output_key,
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
