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

"""Pikar AI Executive Agent - Central Orchestrator for Business Operations.

This module implements the Executive Agent, which serves as the primary
interface for users and orchestrates tasks across specialized agents.
"""

import logging
import os
from pathlib import Path

from app.agents.base_agent import PikarAgent as Agent
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
    tool_progress_before_tool_callback,
)
from app.agents.enhanced_tools import audit_user_setup_tool
from app.agents.shared import (
    ROUTING_AGENT_CONFIG,
    get_fallback_model,
    get_routing_model,
)

# Import shared instruction blocks for consistent behavior across agents
from app.agents.shared_instructions import (
    CONVERSATION_MEMORY_INSTRUCTIONS,
    INTENT_CLARIFICATION_INSTRUCTIONS,
    SELF_IMPROVEMENT_INSTRUCTIONS,
    SKILLS_REGISTRY_INSTRUCTIONS,
    TLDR_RESPONSE_INSTRUCTIONS,
    get_error_and_escalation_instructions,
)

# NOTE: SPECIALIZED_AGENTS and the google.adk.apps imports are intentionally
# loaded lazily inside __getattr__ below. Importing specialized_agents at
# module top instantiates 10 sub-agents (~3.4s) before the FastAPI worker
# can accept TCP, which causes Cloud Run startup-probe TCP timeouts.
# Import Skill tools for accessing and creating skills (agent-aware)
from app.agents.tools.agent_skills import EXEC_SKILL_TOOLS
from app.agents.tools.app_builder import APP_BUILDER_TOOLS

# Import in-chat approval tools (request + async wait) for the inline
# Approve/Reject card pattern (ARTIFACT-03 / ARTIFACT-04)
from app.agents.tools.approval_tool import APPROVAL_TOOLS
from app.agents.tools.base import sanitize_tools as _sanitize
from app.agents.tools.brain_dump import get_braindump_document

# Import briefing tools for daily email triage
from app.agents.tools.briefing_tools import BRIEFING_TOOLS

# Import Configuration tools for helping users set up MCP tools
from app.agents.tools.configuration import CONFIGURATION_TOOLS

# Import context memory tools and callbacks for conversation continuity
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS

# Import cross-agent business synthesis tool
from app.agents.tools.cross_agent_synthesis import CROSS_AGENT_SYNTHESIS_TOOLS

# Import decision journal tools for logging and querying past decisions
from app.agents.tools.decision_journal import DECISION_JOURNAL_TOOLS

# Import Deep Research tools for intelligent research behavior
from app.agents.tools.deep_research import DEEP_RESEARCH_TOOLS

# Import document generation tools (PDF reports, PowerPoint pitch decks)
from app.agents.tools.document_gen import DOCUMENT_GEN_TOOLS

# Import long-running job handoff tool (LONGTASK-01)
from app.agents.tools.long_task import LONG_TASK_TOOLS

# Import magic link approval tools for email-based approve/reject flows
from app.agents.tools.magic_link_approvals import MAGIC_LINK_TOOLS

# Import notification tools
from app.agents.tools.notifications import NOTIFICATION_TOOLS

# Import onboarding nudge tools for new user guidance
from app.agents.tools.onboarding_nudges import ONBOARDING_NUDGE_TOOLS

# Import system health monitoring tool
from app.agents.tools.system_health import SYSTEM_HEALTH_TOOLS

# Import tool timing for telemetry
from app.agents.tools.tool_timing import apply_timing

# Import UI widget tools for agent-to-UI feature
from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS

# Import workflow tools
from app.agents.tools.workflows import WORKFLOW_TOOLS

# Import knowledge injection tools
from app.orchestration.knowledge_tools import KNOWLEDGE_INJECTION_TOOLS
from app.personas.prompt_fragments import build_persona_policy_block

_ENABLE_CONTEXT_CACHE = os.getenv("ENABLE_CONTEXT_CACHE", "true").lower() == "true"

# REGISTRY-03: gate manifest-built Executive on a per-deploy flag so we can
# fall back to the legacy factory if the manifest path regresses. Default ON
# for the Executive only -- specialist agents stay on their own factories
# until their manifests have been validated end-to-end.
_USE_MANIFESTS = os.getenv("USE_MANIFESTS", "true").lower() == "true"

logger = logging.getLogger(__name__)

# Telemetry / Journey Discovery

# from google.adk.events import ToolCallEvent, ToolOutputEvent
# from google.adk.runtime import InvocationContext

# Configure Vertex AI
# os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "my-project-pk-484623")
# os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
# os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")


# =============================================================================
# Global Business Tools
# =============================================================================


async def search_business_knowledge(query: str) -> dict:
    """Search the Knowledge Vault for relevant business information.

    This tool queries the RAG system to find context and information
    about the business, products, customers, and historical decisions.
    The search is scoped to the current request's user via request
    context, so RLS-filtered RPCs return that user's documents.

    Args:
        query: The search query to find relevant business knowledge.

    Returns:
        Dictionary containing search results with relevant context.
    """
    try:
        from app.rag.knowledge_vault import search_knowledge
        from app.services.request_context import get_current_user_id

        user_id = get_current_user_id()
        return await search_knowledge(query, top_k=5, user_id=user_id)
    except Exception as exc:
        logger.exception("search_business_knowledge failed")
        return {
            "results": [],
            "query": query,
            "error": str(exc),
            "note": "Knowledge Vault search failed",
        }


async def update_initiative_status(initiative_id: str, status: str) -> dict:
    """Updates the status of a business initiative or project.

    Args:
        initiative_id: The unique identifier of the initiative.
        status: The new status (e.g., 'in_progress', 'completed', 'blocked').

    Returns:
        Dictionary confirming the update.
    """
    logger.info(f"Updating initiative {initiative_id} to {status}")
    try:
        from app.services.initiative_service import InitiativeService

        service = InitiativeService()
        updated = await service.update_initiative(initiative_id, status=status)
        return {
            "success": True,
            "initiative_id": initiative_id,
            "new_status": status,
            "initiative": updated,
        }
    except Exception as e:
        logger.error("Failed to update initiative %s: %s", initiative_id, e)
        return {"success": False, "initiative_id": initiative_id, "error": str(e)}


async def create_task(description: str, assignee: str, priority: str) -> dict:
    """Creates a new task in the task management system.

    Args:
        description: Clear description of what needs to be done.
        assignee: Who should work on this task (use 'unassigned' if no specific person).
        priority: Task priority - must be one of: low, medium, high, urgent.

    Returns:
        Dictionary with the created task details including task_id, description,
        assignee, priority, and status.
    """
    logger.info(f"Creating task '{description}' assigned to {assignee}")
    try:
        from app.services.task_service import TaskService

        service = TaskService()
        task_desc = f"{description} [assignee={assignee}, priority={priority}]"
        record = await service.create_task(description=task_desc)
        return {
            "success": True,
            "task_id": record.get("id"),
            "description": description,
            "assignee": assignee,
            "priority": priority,
            "status": record.get("status", "pending"),
        }
    except Exception as e:
        logger.error("Failed to create task: %s", e)
        return {"success": False, "description": description, "error": str(e)}


# NOTE: Orchestration tools removed - ADK handles delegation natively via sub_agents


# =============================================================================
# Executive Agent Definition
# =============================================================================

# Load executive instruction from external template file for easier maintenance
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_EXECUTIVE_INSTRUCTION_PATH = _PROMPTS_DIR / "executive_instruction.txt"

if _EXECUTIVE_INSTRUCTION_PATH.exists():
    _EXEC_BASE = _EXECUTIVE_INSTRUCTION_PATH.read_text(encoding="utf-8")
else:
    # Fallback inline instruction if template file is missing
    logger.warning(
        "Executive instruction template not found at %s, using minimal fallback",
        _EXECUTIVE_INSTRUCTION_PATH,
    )
    _EXEC_BASE = """You are the Executive Agent for Pikar AI - the Chief of Staff and Central Orchestrator.
You are the primary interface between the user and Pikar AI's multi-agent ecosystem.
Coordinate specialized agents to accomplish complex tasks. Use available tools to help users.
"""

# Compose final instruction from base template + shared instruction blocks
# This keeps the exec agent in sync with updates to shared blocks used by all agents
EXECUTIVE_INSTRUCTION = (
    _EXEC_BASE
    + SKILLS_REGISTRY_INSTRUCTIONS
    + CONVERSATION_MEMORY_INSTRUCTIONS
    + SELF_IMPROVEMENT_INSTRUCTIONS
    + TLDR_RESPONSE_INSTRUCTIONS
    + INTENT_CLARIFICATION_INSTRUCTIONS
    + get_error_and_escalation_instructions(
        "Executive Agent",
        """- Escalate to the user when a delegated specialist agent returns an error or unexpected result
- Escalate to the user when a task requires cross-domain coordination that affects budget, legal standing, or public reputation
- If multiple specialist agents return conflicting recommendations, synthesize and present the trade-offs rather than picking one silently
- Never auto-approve workflows that involve financial transactions, public communications, or hiring decisions
- If a specialist agent is unavailable (model error, timeout), inform the user and suggest an alternative approach""",
    )
)

_EXECUTIVE_TOOLS = _sanitize(
    apply_timing(
        [
            search_business_knowledge,
            get_braindump_document,
            update_initiative_status,
            create_task,
            audit_user_setup_tool,
            *KNOWLEDGE_INJECTION_TOOLS,
            *NOTIFICATION_TOOLS,
            *APP_BUILDER_TOOLS,
            *WORKFLOW_TOOLS,
            *UI_WIDGET_TOOLS,
            *EXEC_SKILL_TOOLS,
            *CONFIGURATION_TOOLS,
            *CONTEXT_MEMORY_TOOLS,
            *DEEP_RESEARCH_TOOLS,
            *BRIEFING_TOOLS,
            *APPROVAL_TOOLS,
            *MAGIC_LINK_TOOLS,
            *SYSTEM_HEALTH_TOOLS,
            *CROSS_AGENT_SYNTHESIS_TOOLS,
            *DECISION_JOURNAL_TOOLS,
            *DOCUMENT_GEN_TOOLS,
            *ONBOARDING_NUDGE_TOOLS,
            *LONG_TASK_TOOLS,
        ]
    )
)


# TODO(handoff-packet): Wire HandoffPacket emission on the routing path.
# `app/agents/handoff_packet.py` defines a typed envelope (intent, evidence,
# constraints, expected_output_shape, source_agent, target_agent,
# correlation_id) that specialists should receive when the Executive
# delegates. The shape, session-state read/write helpers
# (write_handoff / read_handoff / apply_handoff_to_prompt), the read-side
# wiring in context_memory_before_model_callback, AND the write-side
# before_agent_callback (handoff_packet_before_agent_callback) are already
# in place — see specialist agents (e.g. data_reporting_agent,
# research_agent) which register the callback. The remaining deferred
# work here is to emit a richer Executive-side packet (with explicit
# evidence/constraints derived from the router's chosen target sub_agent)
# so the synthesized fallback packet is replaced with a routing-aware one.
# Out of scope for this PR.
def _build_executive_agent_legacy(model, sub_agents=None, persona: str | None = None):
    """Build the Executive Agent with the given model and sub-agents list (legacy path).

    Args:
        model: The language model to use for the executive agent.
        sub_agents: Optional list of sub-agent instances.
        persona: Optional persona tier (solopreneur, startup, sme, enterprise).
            When provided, persona-specific policy block is appended to the
            executive instruction to shape tone, routing priorities, and output.
    """
    instruction = EXECUTIVE_INSTRUCTION
    persona_block = build_persona_policy_block(
        persona, agent_name="ExecutiveAgent", include_routing=True
    )
    if persona_block:
        instruction = instruction + "\n\n" + persona_block
    return Agent(
        name="ExecutiveAgent",
        model=model,
        description="Chief of Staff / Central Orchestrator - Primary interface for Pikar AI users",
        instruction=instruction,
        tools=_EXECUTIVE_TOOLS,
        sub_agents=sub_agents if sub_agents is not None else [],
        generate_content_config=ROUTING_AGENT_CONFIG,
        # Context memory callbacks for persistent user fact storage
        before_model_callback=context_memory_before_model_callback,
        before_tool_callback=tool_progress_before_tool_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def _build_executive_agent_from_manifest(
    model, sub_agents=None, persona: str | None = None
):
    """Build the Executive Agent from ``MANIFESTS["executive"]`` (REGISTRY-03).

    The manifest-resolved tool list is replaced with the canonical
    ``_EXECUTIVE_TOOLS`` so behavior matches the legacy build exactly. The
    executive's external instruction template (``executive_instruction.txt``)
    is still authoritative for the long-form prompt body; the manifest's
    ``role_definition`` is used only for the leading paragraph and the
    structured instruction blocks. We splice the legacy ``EXECUTIVE_INSTRUCTION``
    in to keep the production prompt byte-identical until the template is
    migrated into ``role_definition``.
    """
    from app.agents.manifest import MANIFESTS
    from app.agents.manifest_builder import build_agent

    manifest = MANIFESTS["executive"]
    agent = build_agent(manifest, persona=persona)

    # Authoritative-prompt override -- the legacy template carries the full
    # routing playbook the manifest cannot easily express until we move the
    # template into role_definition. Manifest-resolved tool plumbing,
    # callbacks, and sub_agent wiring still come from the builder.
    instruction = EXECUTIVE_INSTRUCTION
    persona_block = build_persona_policy_block(
        persona, agent_name="ExecutiveAgent", include_routing=True
    )
    if persona_block:
        instruction = instruction + "\n\n" + persona_block
    agent.instruction = instruction
    agent.model = model
    agent.tools = _EXECUTIVE_TOOLS
    if sub_agents is not None:
        agent.sub_agents = sub_agents
    return agent


def _build_executive_agent(model, sub_agents=None, persona: str | None = None):
    """Build the Executive Agent (manifest path with legacy fallback).

    Routes to :func:`_build_executive_agent_from_manifest` when
    ``USE_MANIFESTS=true`` (default). Falls back to
    :func:`_build_executive_agent_legacy` otherwise. Either path produces a
    functionally equivalent agent today; the manifest path is the canonical
    target as REGISTRY-04+ migrate sub-agents over.
    """
    if _USE_MANIFESTS:
        try:
            return _build_executive_agent_from_manifest(
                model, sub_agents=sub_agents, persona=persona
            )
        except Exception:
            logger.exception(
                "Manifest-built Executive failed; falling back to legacy factory"
            )
    return _build_executive_agent_legacy(model, sub_agents=sub_agents, persona=persona)


def _build_fallback_sub_agents(persona: str | None = None):
    """Create fresh sub-agent instances for the fallback agent.

    ADK enforces that each agent instance can only have one parent.
    The primary agent already "owns" the singleton sub-agents, so the fallback
    must create new instances via factory functions to avoid the
    'already has parent' validation error.

    Args:
        persona: Optional persona tier passed through to each sub-agent factory.
    """
    from app.agents.specialized_agents import (
        create_compliance_agent,
        create_content_agent,
        create_customer_support_agent,
        create_data_agent,
        create_financial_agent,
        create_hr_agent,
        create_marketing_agent,
        create_operations_agent,
        create_research_agent,
        create_sales_agent,
        create_strategic_agent,
    )

    return [
        create_financial_agent("_fb", persona=persona),
        create_content_agent("_fb", persona=persona),
        create_strategic_agent("_fb", persona=persona),
        create_sales_agent("_fb", persona=persona),
        create_marketing_agent("_fb", persona=persona),
        create_operations_agent("_fb", persona=persona),
        create_hr_agent("_fb", persona=persona),
        create_compliance_agent("_fb", persona=persona),
        create_customer_support_agent("_fb", persona=persona),
        create_data_agent("_fb", persona=persona),
        create_research_agent("_fb"),
    ]


def create_executive_agent(persona: str | None = None, model_override=None):
    """Create a fresh ExecutiveAgent for a single request (prevents context leaks).

    Args:
        persona: Optional persona tier. When provided, the executive agent and
            its sub-agents will use persona-aware instructions.
        model_override: Optional model instance for the parent router (e.g. a
            LiteLlm built from the user's BYOK config). Sub-agents keep their
            default Gemini variants.
    """
    from app.agents.specialized_agents import SPECIALIZED_AGENTS

    return _build_executive_agent(
        model_override if model_override is not None else get_routing_model(),
        sub_agents=SPECIALIZED_AGENTS,
        persona=persona,
    )


def create_executive_agent_fallback(persona: str | None = None):
    """Create a fallback ExecutiveAgent for a single request.

    Args:
        persona: Optional persona tier passed through to all sub-agents.
    """
    return _build_executive_agent(
        get_fallback_model(),
        sub_agents=_build_fallback_sub_agents(persona=persona),
        persona=persona,
    )


# ---------------------------------------------------------------------------
# Lazy module attributes
# ---------------------------------------------------------------------------
# The five legacy singletons -- executive_agent, executive_agent_fallback,
# root_agent, app, app_fallback -- are built on first attribute access via
# PEP 562 __getattr__ instead of at module import time. Eager construction
# took ~14s of CPU (10 specialized sub-agents + their tool trees), which
# pushed FastAPI worker readiness past Cloud Run's startup-probe TCP timeout.
# Built singletons are cached, so subsequent accesses are O(1).

APP_NAME = "agents"  # Must match directory where agent is loaded from (app/agents/)

_executive_agent: "Agent | None" = None
_executive_agent_fallback: "Agent | None" = None
_executive_agent_shadow_candidate: "Agent | None" = None
_app = None  # google.adk.apps.App
_app_fallback = None  # google.adk.apps.App
_app_shadow_candidate = None  # google.adk.apps.App


def __getattr__(name: str):
    global _executive_agent, _executive_agent_fallback, _app, _app_fallback
    global _executive_agent_shadow_candidate, _app_shadow_candidate

    if name in ("executive_agent", "root_agent"):
        if _executive_agent is None:
            from app.agents.specialized_agents import SPECIALIZED_AGENTS

            _executive_agent = _build_executive_agent(
                get_routing_model(), sub_agents=SPECIALIZED_AGENTS
            )
        return _executive_agent

    if name == "executive_agent_fallback":
        if _executive_agent_fallback is None:
            _executive_agent_fallback = _build_executive_agent(
                get_fallback_model(), sub_agents=_build_fallback_sub_agents()
            )
        return _executive_agent_fallback

    if name == "executive_agent_shadow_candidate":
        # W3 Section B (B-Alpha-Plus): build the OPPOSITE variant of what
        # production uses so the shadow router can compare the two.
        if _executive_agent_shadow_candidate is None:
            from app.agents.specialized_agents import SPECIALIZED_AGENTS

            if _USE_MANIFESTS:
                _executive_agent_shadow_candidate = _build_executive_agent_legacy(
                    get_routing_model(), sub_agents=SPECIALIZED_AGENTS
                )
            else:
                _executive_agent_shadow_candidate = (
                    _build_executive_agent_from_manifest(
                        get_routing_model(), sub_agents=SPECIALIZED_AGENTS
                    )
                )
        return _executive_agent_shadow_candidate

    if name == "app":
        if _app is None:
            from google.adk.agents.context_cache_config import ContextCacheConfig
            from google.adk.apps import App
            from google.adk.apps.app import EventsCompactionConfig

            _app = App(
                root_agent=__getattr__("executive_agent"),
                name=APP_NAME,
                context_cache_config=(
                    ContextCacheConfig(
                        min_tokens=2048,
                        ttl_seconds=int(
                            os.getenv("VERTEX_CONTEXT_CACHE_TTL_S", "3600")
                        ),
                    )
                    if _ENABLE_CONTEXT_CACHE
                    else None
                ),
                events_compaction_config=EventsCompactionConfig(
                    compaction_interval=80, overlap_size=30
                ),
            )
        return _app

    if name == "app_fallback":
        if _app_fallback is None:
            from google.adk.apps import App
            from google.adk.apps.app import EventsCompactionConfig

            _app_fallback = App(
                root_agent=__getattr__("executive_agent_fallback"),
                name=APP_NAME,
                events_compaction_config=EventsCompactionConfig(
                    compaction_interval=80, overlap_size=30
                ),
            )
        return _app_fallback

    if name == "app_shadow_candidate":
        if _app_shadow_candidate is None:
            from google.adk.apps import App
            from google.adk.apps.app import EventsCompactionConfig

            _app_shadow_candidate = App(
                root_agent=__getattr__("executive_agent_shadow_candidate"),
                name=APP_NAME,
                events_compaction_config=EventsCompactionConfig(
                    compaction_interval=80, overlap_size=30
                ),
            )
        return _app_shadow_candidate

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
