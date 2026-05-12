# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Strategic Planning Agent — built on PikarBaseAgent (W4 migration).

The director surface (model, tools, lifecycle callbacks, ops config) is
assembled by :class:`~app.agents.base_agent.PikarBaseAgent` from
``instructions.md`` + ``strategic.yaml`` + :func:`build_tools_manifest`.

Strategic is the most complex of the W4 routers: it wires **four**
sub-agents into the director's ``sub_agents=`` slot.

  - ``BraindumpPipeline`` — a :class:`SequentialAgent` orchestrating
    transcription -> parallel insight + action extraction. Stays on
    the legacy ADK path because :class:`SequentialAgent` and
    :class:`ParallelAgent` are not :class:`PikarAgent` subclasses.
  - ``ResearchSuite`` — a :class:`ParallelAgent` running market,
    competitive, and consumer research in parallel. Same legacy path.
  - ``KnowledgeVaultAgent`` — a plain :class:`PikarAgent` knowledge
    base manager with the standard memory callbacks.
  - ``InitiativeOpsAgent`` — a plain :class:`PikarAgent` lifecycle
    operator for the 5-phase initiative framework.

Inline-migrating the latter two to PikarBaseAgent would add scope
without simplifying the wiring (they are not structured-output
specialists and they don't load their own ``operations.yaml``); they
stay as :class:`PikarAgent` instances, mirroring how operations
handles its ``ConfigurationAgent`` sub-agent.

Module size note: this file deliberately exceeds the 150-LOC soft
target because it owns four sub-agent factories. The director-only
portion (everything after ``# === Director factory ===``) is still
well under the budget.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.agents.base_agent import PikarAgent, PikarBaseAgent
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
    tool_progress_before_tool_callback,
)
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.shared import DEEP_AGENT_CONFIG, get_fast_model, get_model
from app.agents.strategic.subagents import (
    create_braindump_pipeline,
    create_research_suite,
)
from app.agents.strategic.tools import (
    advance_initiative_phase,
    approve_workflow_step,
    build_tools_manifest,
    create_initiative_from_template,
    get_workflow_status,
    journey_metrics,
    list_initiative_templates,
    orchestrate_initiative_phase,
    start_initiative_from_idea,
    start_journey_workflow,
    suggest_workflows,
)
from app.agents.tools.base import sanitize_tools
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.orchestration.knowledge_tools import KNOWLEDGE_INJECTION_TOOLS
from app.skills.registry import AgentID

_AGENT_DIR = Path(__file__).parent
_INSTRUCTIONS_PATH = _AGENT_DIR / "instructions.md"
_OPS_CONFIG_PATH = _AGENT_DIR / "strategic.yaml"


# =============================================================================
# Sub-agents kept on legacy PikarAgent path
# =============================================================================

_KNOWLEDGE_INSTRUCTION = """You are the Knowledge Vault sub-agent. You manage the business knowledge base:
- Add business knowledge, product info, company info, processes/policies, and FAQs
- List and search existing knowledge entries
Always categorize knowledge appropriately and include enough context for future retrieval."""


def _create_knowledge_agent(suffix: str = "") -> PikarAgent:
    """Create a Knowledge Vault sub-agent (legacy PikarAgent path)."""
    tools = sanitize_tools([*KNOWLEDGE_INJECTION_TOOLS, *CONTEXT_MEMORY_TOOLS])
    return PikarAgent(
        name=f"KnowledgeVaultAgent{suffix}",
        model=get_fast_model(),
        description=(
            "Knowledge base management - add and organize business knowledge, "
            "products, policies, and FAQs"
        ),
        instruction=_KNOWLEDGE_INSTRUCTION,
        tools=tools,
        before_model_callback=context_memory_before_model_callback,
        before_tool_callback=tool_progress_before_tool_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


_INITIATIVE_OPS_INSTRUCTION = """You are the Initiative Operations sub-agent. You handle initiative lifecycle execution:
- Start initiatives from ideas or templates
- Advance initiatives through the 5-phase framework (Ideation -> Validation -> Prototype -> Build -> Scale)
- Orchestrate initiative phases with workflow automation
- Start journey workflows and suggest relevant workflows
- Track journey quality metrics
- Check workflow status and approve workflow steps
Always verify the current phase before advancing to ensure prerequisites are met."""


def _create_initiative_ops_agent(suffix: str = "") -> PikarAgent:
    """Create an Initiative Operations sub-agent (legacy PikarAgent path)."""
    tools = sanitize_tools(
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
    return PikarAgent(
        name=f"InitiativeOpsAgent{suffix}",
        model=get_model(),
        description=(
            "Initiative lifecycle - start, advance, orchestrate initiatives "
            "and journey workflows"
        ),
        instruction=_INITIATIVE_OPS_INSTRUCTION,
        tools=tools,
        before_model_callback=context_memory_before_model_callback,
        before_tool_callback=tool_progress_before_tool_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def _build_strategic_sub_agents(suffix: str = "") -> list[Any]:
    """Build all four sub-agents wired into the strategic director."""
    return [
        create_braindump_pipeline(),
        create_research_suite(),
        _create_knowledge_agent(suffix),
        _create_initiative_ops_agent(suffix),
    ]


# =============================================================================
# Director factory
# =============================================================================


def create_strategic_agent(
    name_suffix: str = "",
    output_key: str | None = None,
    persona: str | None = None,
    *,
    user_id: UUID | None = None,
    persona_id: str | None = None,
    **extra: Any,
) -> PikarBaseAgent:
    """Build a fresh StrategicPlanningAgent bound to a user + persona.

    Strategic is a routing director with four sub-agents
    (BraindumpPipeline, ResearchSuite, KnowledgeVaultAgent,
    InitiativeOpsAgent). They are constructed fresh per invocation so
    ADK's single-parent constraint does not leak across runs.
    """
    _ = name_suffix  # legacy positional arg - name derived from AgentID
    ops = OperationsConfig.load(_OPS_CONFIG_PATH)
    bound_persona = persona_id or persona or "default"
    bound_user = user_id if user_id is not None else uuid4()
    return PikarBaseAgent(
        agent_id=AgentID.STRAT,
        instructions_path=_INSTRUCTIONS_PATH,
        tools_manifest=build_tools_manifest(ops),
        ops_config_path=_OPS_CONFIG_PATH,
        user_id=bound_user,
        persona_id=bound_persona,
        description=(
            "Chief Strategy Officer - routes to 4 sub-agents: research, "
            "brain dump, knowledge vault, initiative ops"
        ),
        generate_content_config=DEEP_AGENT_CONFIG,
        output_key=output_key,
        sub_agents=_build_strategic_sub_agents(name_suffix),
        **extra,
    )


# Module-level singleton retained as a sentinel for legacy callers.
strategic_agent: PikarAgent | None = None


__all__ = ["create_strategic_agent", "strategic_agent"]
