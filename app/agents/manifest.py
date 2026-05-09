# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Single source of truth for each agent's name, model, tools, prompt blocks, and routing description.

This module centralizes the configuration for every agent in the Pikar AI
ecosystem (Executive + 13 specialists) into a single ``MANIFESTS`` dict.
The :class:`AgentManifest` Pydantic model captures the canonical shape; the
companion :mod:`app.agents.manifest_builder` consumes it to construct
``LlmAgent`` instances.

The goal of REGISTRY-01..03 (Phase 96) is to replace the per-agent factory
boilerplate (one ``agent.py`` per domain, each repeating the same
callbacks/config/persona-block plumbing) with a declarative registry that
the rest of the system can introspect.

Specialist factories are NOT removed yet -- they still live in
``app/agents/<domain>/agent.py``. The Executive Agent is the canonical proof
that a manifest-built agent works end-to-end (gated by ``USE_MANIFESTS``).
"""

from __future__ import annotations

import importlib
import logging
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Canonical instruction-block ordering
# =============================================================================
#
# When ``compose_instruction`` assembles the final prompt, blocks are emitted
# in this fixed order regardless of how they appear in the manifest list.
# This keeps every agent's prompt structure consistent and prevents drift
# between the Executive and the specialists.
INSTRUCTION_BLOCK_ORDER: tuple[str, ...] = (
    "skills_registry",
    "web_research",
    "web_search_only",
    "context_memory",
    "self_improvement",
    "tldr_response",
    "intent_clarification",
    "elite_research",
    "braindump_analysis",
    "professional_behavior",
    "cross_agent_help",
    "document_editor",
    "escalation",
    "app_builder_handoff",
    "telemetry",
)


# =============================================================================
# AgentManifest model
# =============================================================================


class AgentManifest(BaseModel):
    """Declarative description of a single Pikar AI agent.

    See module docstring for the role this serves in the v12 architecture.
    """

    name: str
    """Agent class name, e.g. ``FinancialAnalysisAgent``."""

    role_definition: str
    """Short specialist role (one paragraph max). Sits at the top of the prompt."""

    model_profile: Literal["routing", "deep", "creative", "fast"]
    """Selects ``get_routing_model()`` / ``get_model()`` / ``get_fast_model()``."""

    config_profile: Literal["ROUTING", "DEEP", "CREATIVE", "FAST"]
    """Selects ``ROUTING_AGENT_CONFIG`` / ``DEEP_AGENT_CONFIG`` / etc."""

    tool_modules: list[str] = Field(default_factory=list)
    """Module paths whose tools to include. The builder imports each module and
    splats either a ``*_TOOLS`` list export or a single function export named at
    the end. Example: ``"app.agents.tools.context_memory"`` ->
    ``CONTEXT_MEMORY_TOOLS``. Use the ``"module:NAME"`` form to pick a specific
    export name (e.g. ``"app.agents.tools.knowledge:search_knowledge"``)."""

    instruction_blocks: list[str] = Field(default_factory=list)
    """Canonical block names. Composed in :data:`INSTRUCTION_BLOCK_ORDER`."""

    sub_agents: list[str] = Field(default_factory=list)
    """Names referencing other manifests in :data:`MANIFESTS` (registry keys)."""

    callbacks: list[str] = Field(default_factory=lambda: ["context_memory", "tool_progress"])
    """Opt-in: ``"agent_memory"``, ``"handoff_packet"``."""

    output_schema: str | None = None
    """Pydantic class name on ``app.agents.schemas`` for structured output agents."""

    persona_aware: bool = False
    """When True, the builder appends a persona policy block."""

    routing_description: str = ""
    """One line for Executive's AVAILABLE SPECIALISTS section."""

    description: str = ""
    """Short ADK description (shown to peers as routing hint)."""

    include_contents: str | None = None
    """ADK ``include_contents`` override; structured-JSON sub-agents use ``"none"``."""


# =============================================================================
# Tool-module resolution
# =============================================================================


def resolve_tool_modules(modules: list[str]) -> list:
    """Import each module path and collect the ``*_TOOLS`` exports.

    Each entry in ``modules`` is one of:

    - ``"app.agents.tools.context_memory"`` -- imports the module and looks for
      a ``CONTEXT_MEMORY_TOOLS`` (or any single ``*_TOOLS``) attribute.
    - ``"app.agents.tools.knowledge:search_knowledge"`` -- imports the module
      and pulls the named attribute. Useful when a module exports a single
      tool function instead of a ``*_TOOLS`` list.

    Missing modules and missing attributes log a warning and are skipped --
    we never want a typo in a manifest to crash the executive build.

    Args:
        modules: A list of module reference strings.

    Returns:
        A flat list of tool callables.
    """
    flat: list = []
    for ref in modules:
        attr_name: str | None = None
        module_path = ref
        if ":" in ref:
            module_path, attr_name = ref.split(":", 1)

        try:
            mod = importlib.import_module(module_path)
        except Exception as exc:  # pragma: no cover - exercised via warning log
            logger.warning("manifest: failed to import %s: %s", module_path, exc)
            continue

        if attr_name:
            obj = getattr(mod, attr_name, None)
            if obj is None:
                logger.warning(
                    "manifest: %s has no attribute %s", module_path, attr_name
                )
                continue
            if isinstance(obj, list):
                flat.extend(obj)
            else:
                flat.append(obj)
            continue

        # Auto-detect *_TOOLS (or *_TOOLS_LIST) export.
        candidates = [
            name for name in dir(mod)
            if name.endswith("_TOOLS") and isinstance(getattr(mod, name), list)
        ]
        if not candidates:
            logger.warning(
                "manifest: %s has no *_TOOLS export; skipping", module_path
            )
            continue
        # Stable ordering -- in the rare case of multiple, splat all.
        for cand in sorted(candidates):
            flat.extend(getattr(mod, cand))

    return flat


# =============================================================================
# Instruction composition
# =============================================================================


def _resolve_instruction_block(block_name: str, manifest: AgentManifest) -> str:
    """Return the prompt fragment for a canonical block name.

    Lazily imports ``app.agents.shared_instructions`` to avoid an import cycle
    when the manifest module is loaded at app boot.
    """
    from app.agents import shared_instructions as si

    block_map: dict[str, str] = {
        "skills_registry": si.SKILLS_REGISTRY_INSTRUCTIONS,
        "web_research": si.WEB_RESEARCH_INSTRUCTIONS,
        "web_search_only": si.WEB_SEARCH_ONLY_INSTRUCTIONS,
        "context_memory": si.CONVERSATION_MEMORY_INSTRUCTIONS,
        "self_improvement": si.SELF_IMPROVEMENT_INSTRUCTIONS,
        "tldr_response": si.TLDR_RESPONSE_INSTRUCTIONS,
        "intent_clarification": si.INTENT_CLARIFICATION_INSTRUCTIONS,
        "elite_research": si.ELITE_RESEARCH_PERSONA,
        "braindump_analysis": si.BRAINDUMP_ANALYSIS_INSTRUCTIONS,
        "professional_behavior": si.PROFESSIONAL_BEHAVIOR,
        "cross_agent_help": si.CROSS_AGENT_HELP_INSTRUCTIONS,
        "document_editor": si.DOCUMENT_EDITOR_INSTRUCTION,
        "app_builder_handoff": si.APP_BUILDER_HANDOFF_INSTRUCTION,
    }

    if block_name == "escalation":
        # Escalation rules vary per agent; the manifest's role_definition
        # already covers domain context, so we emit the generic envelope.
        return si.get_error_and_escalation_instructions(manifest.name)
    if block_name == "telemetry":
        # Telemetry is wired at the callback layer, not the prompt layer,
        # but we keep the marker so downstream callers can opt in.
        return ""
    return block_map.get(block_name, "")


def compose_instruction(manifest: AgentManifest) -> str:
    """Assemble the full instruction string for an agent.

    Order:
    1. ``role_definition``
    2. Named ``instruction_blocks`` in :data:`INSTRUCTION_BLOCK_ORDER`
    3. Generated ``## AVAILABLE TOOLS`` section listing tool names

    Args:
        manifest: The agent's manifest entry.

    Returns:
        A composed instruction string ready to feed an ``LlmAgent``.
    """
    parts: list[str] = [manifest.role_definition.strip(), ""]

    requested = set(manifest.instruction_blocks)
    for block in INSTRUCTION_BLOCK_ORDER:
        if block in requested:
            chunk = _resolve_instruction_block(block, manifest)
            if chunk:
                parts.append(chunk.strip())
                parts.append("")

    # Generated tool inventory -- helps the model self-select tools.
    tools = resolve_tool_modules(manifest.tool_modules)
    if tools:
        tool_names = []
        for tool in tools:
            name = getattr(tool, "__name__", None) or getattr(tool, "name", None)
            if name and name not in tool_names:
                tool_names.append(str(name))
        if tool_names:
            parts.append("## AVAILABLE TOOLS")
            for name in tool_names:
                parts.append(f"- `{name}`")
            parts.append("")

    return "\n".join(parts).rstrip() + "\n"


# =============================================================================
# Routing-table generation
# =============================================================================


def compose_routing_table(manifests: dict[str, AgentManifest]) -> str:
    """Generate the Executive's AVAILABLE SPECIALISTS block.

    Iterates every manifest with a non-empty ``routing_description`` and
    emits a markdown bullet list. The Executive's own manifest is skipped.

    Args:
        manifests: The full manifest registry (typically :data:`MANIFESTS`).

    Returns:
        A markdown block; empty string if no specialists have descriptions.
    """
    lines: list[str] = ["## AVAILABLE SPECIALISTS", ""]
    have_any = False
    for key, m in manifests.items():
        if key == "executive":
            continue
        if not m.routing_description:
            continue
        lines.append(f"- **{m.name}** - {m.routing_description}")
        have_any = True
    if not have_any:
        return ""
    lines.append("")
    return "\n".join(lines)


# =============================================================================
# MANIFESTS registry
# =============================================================================
#
# Each entry mirrors what the corresponding ``agent.py`` constructs today.
# The role_definition was extracted from the existing instruction strings;
# the bulk of the prompt (capabilities, behavior, gates) still lives in the
# specialist's agent.py. As we migrate specialists onto manifest_builder,
# their long-form instructions move into role_definition here.

MANIFESTS: dict[str, AgentManifest] = {
    # -------------------------------------------------------------------------
    # Executive (central orchestrator)
    # -------------------------------------------------------------------------
    "executive": AgentManifest(
        name="ExecutiveAgent",
        description="Chief of Staff / Central Orchestrator - Primary interface for Pikar AI users",
        role_definition=(
            "You are the Executive Agent for Pikar AI - the Chief of Staff and "
            "Central Orchestrator. You are the primary interface between the user "
            "and Pikar AI's multi-agent ecosystem. Coordinate specialized agents "
            "to accomplish complex tasks and use the tools below to help users "
            "directly when no specialist is needed."
        ),
        model_profile="routing",
        config_profile="ROUTING",
        tool_modules=[
            "app.agents.tools.context_memory",
            "app.agents.tools.deep_research",
            "app.agents.tools.briefing_tools",
            "app.agents.tools.approval_tool",
            "app.agents.tools.magic_link_approvals",
            "app.agents.tools.system_health",
            "app.agents.tools.cross_agent_synthesis",
            "app.agents.tools.decision_journal",
            "app.agents.tools.document_gen",
            "app.agents.tools.onboarding_nudges",
            "app.agents.tools.long_task",
            "app.agents.tools.notifications",
            "app.agents.tools.app_builder",
            "app.agents.tools.workflows",
            "app.agents.tools.ui_widgets",
            "app.agents.tools.configuration",
            "app.agents.tools.agent_skills:EXEC_SKILL_TOOLS",
            "app.orchestration.knowledge_tools:KNOWLEDGE_INJECTION_TOOLS",
        ],
        instruction_blocks=[
            "skills_registry",
            "context_memory",
            "self_improvement",
            "tldr_response",
            "intent_clarification",
            "escalation",
        ],
        sub_agents=[
            "financial",
            "content",
            "strategic",
            "sales",
            "marketing",
            "operations",
            "hr",
            "compliance",
            "customer_support",
            "data",
            "data_reporting",
            "research",
        ],
        callbacks=["context_memory", "tool_progress"],
        persona_aware=True,
        routing_description="",
    ),
    # -------------------------------------------------------------------------
    # Financial
    # -------------------------------------------------------------------------
    "financial": AgentManifest(
        name="FinancialAnalysisAgent",
        description="CFO / Financial Analyst - Analyzes financial health, revenue, costs, and forecasting",
        role_definition=(
            "You are the Financial Analysis Agent. Your focus is strictly on "
            "numbers, revenue, costs, profit, and forecasting. Be precise and "
            "data-driven; flag risks proactively; never present forecasts as "
            "guarantees."
        ),
        model_profile="deep",
        config_profile="DEEP",
        tool_modules=[
            "app.agents.financial.tools",
            "app.agents.tools.agent_skills:FIN_SKILL_TOOLS",
            "app.agents.tools.invoicing",
            "app.agents.tools.report_scheduling",
            "app.agents.tools.ui_widgets",
            "app.agents.tools.context_memory",
            "app.agents.tools.self_improve:FIN_IMPROVE_TOOLS",
            "app.agents.tools.graph_tools",
            "app.agents.tools.system_knowledge:search_system_knowledge",
            "app.agents.tools.document_gen",
            "app.agents.tools.stripe_tools",
            "app.agents.tools.shopify_tools",
            "app.agents.tools.quick_research",
            "app.mcp.agent_tools:mcp_web_search",
        ],
        instruction_blocks=[
            "skills_registry",
            "web_search_only",
            "context_memory",
            "self_improvement",
            "escalation",
            "app_builder_handoff",
        ],
        sub_agents=["financial_report"],
        callbacks=["context_memory", "tool_progress"],
        persona_aware=True,
        routing_description="Finance, revenue, costs, forecasting, invoicing, Stripe/Shopify analytics, financial health scoring",
    ),
    "financial_report": AgentManifest(
        name="FinancialReportAgent",
        description="Generates structured financial reports in JSON format for charts and dashboards",
        role_definition=(
            "You are a financial report generator. Analyze the provided data and "
            "produce a structured JSON report. Calculate profit margin as "
            "(revenue - expenses) / revenue * 100. Determine trend based on "
            "month-over-month changes. Output MUST match the FinancialReport "
            "schema exactly."
        ),
        model_profile="deep",
        config_profile="DEEP",
        output_schema="FinancialReport",
        include_contents="none",
        callbacks=[],  # output_schema agents skip callbacks (ADK constraint)
        routing_description="",
    ),
    # -------------------------------------------------------------------------
    # Content (LlmAgent director with 3 sub-agents)
    # -------------------------------------------------------------------------
    "content": AgentManifest(
        name="ContentCreationAgent",
        description=(
            "CMO / Creative Director - Understands content requests, delegates "
            "to Video Director, Graphic Designer, and Copywriter sub-agents."
        ),
        role_definition=(
            "You are the Content Director - CMO and Creative Director for the "
            "content creation team. Understand the user's content request, plan "
            "the deliverables, and delegate to your specialized sub-agents "
            "(VideoDirectorAgent, GraphicDesignerAgent, CopywriterAgent). "
            "Use the one-shot fast path for simple posts; use the full pipeline "
            "for campaigns and multi-asset bundles."
        ),
        model_profile="creative",
        config_profile="CREATIVE",
        tool_modules=[
            "app.agents.content.tools",
            "app.agents.tools.knowledge:search_knowledge",
            "app.agents.tools.brand_profile",
            "app.agents.tools.creative_brief",
            "app.agents.tools.art_direction",
            "app.workflows.content_pipeline:CONTENT_PIPELINE_TOOLS",
            "app.agents.tools.context_memory",
            "app.agents.tools.self_improve:CONT_IMPROVE_TOOLS",
            "app.agents.tools.graph_tools",
            "app.agents.tools.system_knowledge:search_system_knowledge",
            "app.agents.tools.document_gen",
            "app.agents.tools.document_editor",
            "app.agents.tools.quick_research",
            "app.agents.tools.brain_dump",
        ],
        instruction_blocks=[
            "context_memory",
            "self_improvement",
            "document_editor",
            "escalation",
            "app_builder_handoff",
        ],
        sub_agents=["content_video_director", "content_graphic_designer", "content_copywriter"],
        callbacks=["context_memory", "tool_progress"],
        persona_aware=True,
        routing_description="Content creation - blog posts, social copy, video ads, graphics, UGC, full campaign bundles",
    ),
    "content_video_director": AgentManifest(
        name="VideoDirectorAgent",
        description="Handles high-quality video generation, UGC ads, orchestrating Veo 3, Remotion, and complete ad pipelines.",
        role_definition=(
            "You are the Video Director Agent, specializing exclusively in "
            "creating high-quality marketing videos, promos, and commercials. "
            "Wait for explicit instructions to create."
        ),
        model_profile="creative",
        config_profile="CREATIVE",
        tool_modules=[
            "app.mcp.tools.canva_media:execute_content_pipeline",
            "app.mcp.tools.canva_media:create_video_with_veo",
            "app.mcp.tools.canva_media:create_video",
            "app.agents.tools.art_direction",
            "app.agents.tools.context_memory",
        ],
        instruction_blocks=["context_memory"],
        callbacks=["context_memory", "tool_progress"],
        routing_description="",
    ),
    "content_graphic_designer": AgentManifest(
        name="GraphicDesignerAgent",
        description="Handles visual assets such as images, mix boards, infographics, and posters via generate_image / generate_images.",
        role_definition=(
            "You are the Graphic Designer Agent. You specialize exclusively in "
            "creating stunning static visuals: mix boards, posters, infographics, "
            "and social media images. Wait for explicit instructions."
        ),
        model_profile="creative",
        config_profile="CREATIVE",
        tool_modules=[
            "app.agents.enhanced_tools:generate_image",
            "app.agents.enhanced_tools:generate_images",
            "app.agents.enhanced_tools:generate_react_component",
            "app.agents.enhanced_tools:build_portfolio",
            "app.agents.tools.art_direction",
            "app.agents.tools.ui_widgets",
            "app.agents.tools.context_memory",
        ],
        instruction_blocks=["context_memory"],
        callbacks=["context_memory", "tool_progress"],
        routing_description="",
    ),
    "content_copywriter": AgentManifest(
        name="CopywriterAgent",
        description="Handles marketing copy, SEO blogs, social media captions, ad copy (Google/Meta), UGC scripts, frameworks, and web research.",
        role_definition=(
            "You are the Copywriter Agent. You specialize exclusively in "
            "generating textual content: SEO blogs, social media copy, landing "
            "page copy, ad copy, and overall campaign strategies."
        ),
        model_profile="creative",
        config_profile="CREATIVE",
        tool_modules=[
            "app.agents.tools.knowledge:search_knowledge",
            "app.agents.content.tools",
            "app.agents.marketing.tools",
            "app.agents.tools.ad_copy_tools",
            "app.agents.tools.agent_skills:CONT_SKILL_TOOLS",
            "app.agents.tools.context_memory",
            "app.mcp.agent_tools:mcp_web_search",
            "app.mcp.agent_tools:mcp_web_scrape",
            "app.mcp.agent_tools:mcp_generate_landing_page",
        ],
        instruction_blocks=["skills_registry", "web_research", "context_memory"],
        callbacks=["context_memory", "tool_progress"],
        routing_description="",
    ),
    # -------------------------------------------------------------------------
    # Strategic (router with 4 sub-agents)
    # -------------------------------------------------------------------------
    "strategic": AgentManifest(
        name="StrategicPlanningAgent",
        description="Chief Strategy Officer - routes to 4 sub-agents: research, brain dump, knowledge vault, initiative ops",
        role_definition=(
            "You are the Strategic Planning Agent. You help set long-term goals "
            "(OKRs) and track initiatives through the 5-phase Initiative "
            "Framework: Ideation -> Validation -> Prototype -> Build -> Scale. "
            "Auto-create initiatives from ideas, delegate research and "
            "brainstorming to the appropriate sub-agent, and force users to "
            "prioritize."
        ),
        model_profile="routing",
        config_profile="DEEP",
        tool_modules=[
            "app.agents.strategic.tools",
            "app.agents.tools.boardroom:convene_board_meeting",
            "app.agents.tools.skill_builder:create_operational_skill",
            "app.agents.enhanced_tools:product_roadmap_guide",
            "app.agents.tools.brain_dump",
            "app.agents.tools.briefing_tools",
            "app.agents.tools.agent_skills:STRAT_SKILL_TOOLS",
            "app.agents.tools.adaptive_workflows",
            "app.agents.tools.ui_widgets",
            "app.agents.tools.context_memory",
            "app.agents.tools.self_improve:STRAT_IMPROVE_TOOLS",
            "app.agents.tools.graph_tools",
            "app.agents.tools.system_knowledge:search_system_knowledge",
            "app.agents.tools.document_gen",
            "app.mcp.agent_tools:mcp_web_search",
            "app.mcp.agent_tools:mcp_web_scrape",
        ],
        instruction_blocks=[
            "skills_registry",
            "web_research",
            "context_memory",
            "self_improvement",
            "elite_research",
            "escalation",
            "app_builder_handoff",
        ],
        sub_agents=[],  # BraindumpPipeline + ResearchSuite + custom subs handled in factory
        callbacks=["context_memory", "tool_progress"],
        persona_aware=True,
        routing_description="Strategy, OKRs, initiatives, brainstorming, market research, board meetings, business validation",
    ),
    # -------------------------------------------------------------------------
    # Sales
    # -------------------------------------------------------------------------
    "sales": AgentManifest(
        name="SalesIntelligenceAgent",
        description="Head of Sales - Deal scoring, lead analysis, and sales enablement",
        role_definition=(
            "You are the Sales Intelligence Agent. You focus on deal scoring, "
            "sales enablement, lead analysis, and CRM-aware actions. Use the "
            "structured LeadScoringAgent for qualified output; use HubSpot "
            "context before answering deal questions; never commit to contract "
            "terms without explicit user approval."
        ),
        model_profile="deep",
        config_profile="DEEP",
        tool_modules=[
            "app.agents.sales.tools",
            "app.agents.tools.hubspot_tools",
            "app.agents.tools.agent_skills:SALES_SKILL_TOOLS",
            "app.agents.tools.ui_widgets",
            "app.agents.tools.context_memory",
            "app.agents.tools.self_improve:SALES_IMPROVE_TOOLS",
            "app.agents.tools.graph_tools",
            "app.agents.tools.system_knowledge:search_system_knowledge",
            "app.agents.tools.document_gen",
            "app.agents.tools.calendar_tool",
            "app.agents.tools.pipeline_dashboard",
            "app.agents.tools.sales_followup",
            "app.agents.tools.proposal_generator",
            "app.agents.tools.quick_research",
            "app.mcp.agent_tools:mcp_web_search",
            "app.mcp.agent_tools:mcp_web_scrape",
        ],
        instruction_blocks=[
            "skills_registry",
            "web_research",
            "context_memory",
            "self_improvement",
            "escalation",
            "app_builder_handoff",
        ],
        sub_agents=["sales_lead_scoring"],
        callbacks=["context_memory", "tool_progress"],
        persona_aware=True,
        routing_description="Sales pipelines, lead scoring (BANT/MEDDIC/CHAMP), HubSpot CRM, proposals, follow-up emails",
    ),
    "sales_lead_scoring": AgentManifest(
        name="LeadScoringAgent",
        description="Scores and qualifies leads with structured JSON output for CRM integration",
        role_definition=(
            "You are a lead scoring specialist. Apply BANT, MEDDIC, or CHAMP. "
            "Score each criterion individually, calculate overall 0-100 score, "
            "determine qualification status, and output a valid LeadQualification "
            "JSON object."
        ),
        model_profile="deep",
        config_profile="DEEP",
        output_schema="LeadQualification",
        include_contents="none",
        callbacks=[],
        routing_description="",
    ),
    # -------------------------------------------------------------------------
    # Marketing (router with 6 sub-agents)
    # -------------------------------------------------------------------------
    "marketing": AgentManifest(
        name="MarketingAutomationAgent",
        description="Marketing Director - routes to 6 specialist sub-agents: campaigns, email, ads, audiences, SEO, and social",
        role_definition=(
            "You are the Marketing Automation Agent - the Marketing Director. "
            "You coordinate 6 specialist sub-agents (CampaignAgent, "
            "EmailMarketingAgent, AdPlatformAgent, AudienceAgent, SEOAgent, "
            "SocialMediaAgent) to handle all marketing operations. You are a "
            "routing agent: delegate domain-specific work and never auto-approve "
            "ad spend above the configured cap."
        ),
        model_profile="routing",
        config_profile="ROUTING",
        tool_modules=[
            "app.agents.tools.deep_research",
            "app.mcp.agent_tools:mcp_web_search",
            "app.mcp.agent_tools:mcp_web_scrape",
            "app.mcp.agent_tools:mcp_generate_landing_page",
            "app.mcp.agent_tools:mcp_stitch_landing_page",
            "app.mcp.tools.stitch:configure_stitch_api_key",
            "app.agents.tools.agent_skills:MKT_SKILL_TOOLS",
            "app.agents.tools.document_gen",
            "app.agents.tools.ui_widgets",
            "app.agents.tools.brand_profile",
            "app.agents.tools.context_memory",
            "app.agents.tools.self_improve:MKT_IMPROVE_TOOLS",
            "app.agents.tools.graph_tools",
            "app.agents.tools.system_knowledge:search_system_knowledge",
            "app.agents.tools.shopify_tools:SHOPIFY_ANALYTICS_TOOLS",
            "app.agents.tools.attribution_tools",
            "app.agents.tools.quick_research",
        ],
        instruction_blocks=[
            "web_research",
            "skills_registry",
            "context_memory",
            "self_improvement",
            "escalation",
            "app_builder_handoff",
        ],
        sub_agents=[],  # 6 sub-agents constructed in marketing/agent.py factory
        callbacks=["context_memory", "tool_progress"],
        persona_aware=True,
        routing_description="Marketing campaigns, ads (Google/Meta), email sequences, audiences, SEO, social publishing",
    ),
    # -------------------------------------------------------------------------
    # Operations (router with ConfigurationAgent sub-agent)
    # -------------------------------------------------------------------------
    "operations": AgentManifest(
        name="OperationsOptimizationAgent",
        description="COO / Operations Manager - process improvement, infrastructure, and configuration (routes to ConfigurationAgent for setup tasks)",
        role_definition=(
            "You are the Operations Optimization Agent. You focus on process "
            "improvement, bottleneck identification, rollout planning, "
            "vendor/SaaS cost tracking, PM tool integration (Linear/Asana), "
            "outbound webhooks, and notification routing. You also have the "
            "unique ability to create new operational skills for yourself and "
            "other agents."
        ),
        model_profile="routing",
        config_profile="DEEP",
        tool_modules=[
            "app.agents.tools.skill_builder:create_operational_skill",
            "app.agents.sales.tools",
            "app.agents.enhanced_tools:security_checklist",
            "app.agents.enhanced_tools:container_deployment_guide",
            "app.agents.enhanced_tools:cloud_architecture_guide",
            "app.mcp.agent_tools:mcp_web_search",
            "app.agents.tools.agent_skills:OPS_SKILL_TOOLS",
            "app.agents.tools.inventory",
            "app.agents.tools.context_memory",
            "app.agents.tools.self_improve:OPS_IMPROVE_TOOLS",
            "app.agents.tools.graph_tools",
            "app.agents.tools.system_knowledge:search_system_knowledge",
            "app.agents.tools.document_gen",
            "app.agents.tools.pm_task_tools",
            "app.agents.tools.communication_tools",
            "app.agents.tools.calendar_tool",
            "app.agents.tools.webhook_tools",
            "app.agents.tools.ops_tools",
            "app.agents.tools.quick_research",
        ],
        instruction_blocks=[
            "skills_registry",
            "web_search_only",
            "context_memory",
            "self_improvement",
            "escalation",
            "app_builder_handoff",
        ],
        sub_agents=[],  # ConfigurationAgent built in operations/agent.py
        callbacks=["context_memory", "tool_progress"],
        persona_aware=True,
        routing_description="Operations, processes, SOPs, PM tools (Linear/Asana), webhooks, notifications, vendor tracking, integrations setup",
    ),
    # -------------------------------------------------------------------------
    # HR
    # -------------------------------------------------------------------------
    "hr": AgentManifest(
        name="HRRecruitmentAgent",
        description="Human Resources Manager - Hiring, candidate evaluation, and employee management",
        role_definition=(
            "You are the HR & Recruitment Agent. You focus on hiring, candidate "
            "evaluation, and employee management. Apply strict bias and fairness "
            "guardrails: evaluate only on job-relevant competencies, document "
            "decisions, never auto-reject. Use STAR-method interview questions "
            "consistently across candidates."
        ),
        model_profile="routing",
        config_profile="DEEP",
        tool_modules=[
            "app.agents.tools.knowledge:search_knowledge",
            "app.agents.hr.tools",
            "app.agents.tools.agent_skills:HR_SKILL_TOOLS",
            "app.agents.tools.calendar_tool",
            "app.agents.tools.ui_widgets",
            "app.agents.tools.context_memory",
            "app.agents.tools.self_improve:HR_IMPROVE_TOOLS",
            "app.agents.tools.graph_tools",
            "app.agents.tools.system_knowledge:search_system_knowledge",
            "app.agents.tools.document_gen",
            "app.agents.tools.quick_research",
            "app.mcp.agent_tools:mcp_web_search",
        ],
        instruction_blocks=[
            "skills_registry",
            "web_search_only",
            "context_memory",
            "self_improvement",
            "escalation",
            "app_builder_handoff",
        ],
        sub_agents=[],
        callbacks=["context_memory", "tool_progress"],
        persona_aware=True,
        routing_description="HR, recruitment, job postings, candidate evaluation, interviews, onboarding, compensation benchmarking",
    ),
    # -------------------------------------------------------------------------
    # Compliance
    # -------------------------------------------------------------------------
    "compliance": AgentManifest(
        name="ComplianceRiskAgent",
        description="Legal Counsel - Compliance, risk assessment, and legal guidance",
        role_definition=(
            "You are the Compliance & Risk Agent. You focus on legal compliance, "
            "risk assessment, contract review, and regulatory guidance. Be "
            "thorough and conservative on risk. Use structured frameworks. "
            "Never provide definitive legal advice -- always recommend "
            "qualified legal counsel for material decisions."
        ),
        model_profile="deep",
        config_profile="DEEP",
        tool_modules=[
            "app.agents.tools.knowledge:search_knowledge",
            "app.agents.compliance.tools",
            "app.agents.tools.agent_skills:LEGAL_SKILL_TOOLS",
            "app.agents.tools.ui_widgets",
            "app.agents.tools.context_memory",
            "app.agents.tools.self_improve:LEGAL_IMPROVE_TOOLS",
            "app.agents.tools.graph_tools",
            "app.agents.tools.system_knowledge:search_system_knowledge",
            "app.agents.tools.document_gen",
            "app.agents.tools.quick_research",
            "app.mcp.agent_tools:mcp_web_search",
            "app.mcp.agent_tools:mcp_web_scrape",
        ],
        instruction_blocks=[
            "skills_registry",
            "web_research",
            "context_memory",
            "self_improvement",
            "escalation",
            "app_builder_handoff",
        ],
        sub_agents=["compliance_risk_report"],
        callbacks=["context_memory", "tool_progress"],
        persona_aware=True,
        routing_description="Compliance, legal review, risk assessment, GDPR/CCPA/HIPAA/SOX, contracts, audits, regulatory updates",
    ),
    "compliance_risk_report": AgentManifest(
        name="RiskReportAgent",
        description="Produces structured risk assessment reports for risk registers and dashboards",
        role_definition=(
            "You are a risk assessment specialist. Assign category, severity, "
            "probability, and impact score (1-25). Provide mitigation strategy. "
            "Output MUST match the RiskAssessment schema exactly."
        ),
        model_profile="deep",
        config_profile="DEEP",
        output_schema="RiskAssessment",
        include_contents="none",
        callbacks=[],
        routing_description="",
    ),
    # -------------------------------------------------------------------------
    # Customer Support
    # -------------------------------------------------------------------------
    "customer_support": AgentManifest(
        name="CustomerSupportAgent",
        description="Customer Success Manager - Customer success, proactive support, communication drafting, and customer health monitoring",
        role_definition=(
            "You are the Customer Success Manager. You focus on customer "
            "success, proactive support, communication drafting, knowledge "
            "base management, and customer health monitoring. Be empathetic; "
            "use sentiment analysis to prioritize negative experiences; "
            "proactively identify churn risks."
        ),
        model_profile="routing",
        config_profile="DEEP",
        tool_modules=[
            "app.agents.tools.knowledge:search_knowledge",
            "app.agents.customer_support.tools",
            "app.agents.tools.agent_skills:SUPP_SKILL_TOOLS",
            "app.agents.tools.ui_widgets",
            "app.agents.tools.context_memory",
            "app.agents.tools.self_improve:SUPP_IMPROVE_TOOLS",
            "app.agents.tools.graph_tools",
            "app.agents.tools.system_knowledge:search_system_knowledge",
            "app.agents.tools.document_gen",
            "app.agents.tools.quick_research",
            "app.mcp.agent_tools:mcp_web_search",
        ],
        instruction_blocks=[
            "skills_registry",
            "web_search_only",
            "context_memory",
            "self_improvement",
            "escalation",
            "app_builder_handoff",
        ],
        sub_agents=[],
        callbacks=["context_memory", "tool_progress"],
        persona_aware=True,
        routing_description="Customer support, tickets, churn risk, FAQ generation, response drafting, customer health dashboards",
    ),
    # -------------------------------------------------------------------------
    # Data Analysis
    # -------------------------------------------------------------------------
    "data": AgentManifest(
        name="DataAnalysisAgent",
        description="Data Analyst - analysis, reporting, and forecasting (routes to SheetsAgent for spreadsheet ops)",
        role_definition=(
            "You are the Data Analysis Agent. You focus on data validation, "
            "anomaly detection, cohort analysis, and forecasting. Apply "
            "statistical rigor: minimum sample sizes, confidence intervals, "
            "and clear distinction between correlation and causation. Use "
            "natural-language data queries first; fall back to individual "
            "tools only when needed."
        ),
        model_profile="routing",
        config_profile="DEEP",
        tool_modules=[
            "app.agents.data.tools",
            "app.agents.financial.tools:get_revenue_stats",
            "app.agents.tools.knowledge:search_knowledge",
            "app.agents.enhanced_tools:rag_architecture_guide",
            "app.agents.tools.agent_skills:DATA_SKILL_TOOLS",
            "app.agents.tools.ui_widgets",
            "app.agents.tools.context_memory",
            "app.agents.tools.self_improve:DATA_IMPROVE_TOOLS",
            "app.agents.tools.graph_tools",
            "app.agents.tools.system_knowledge:search_system_knowledge",
            "app.agents.tools.data_io",
            "app.agents.tools.document_gen",
            "app.agents.tools.external_db_tools",
            "app.agents.tools.quick_research",
            "app.mcp.agent_tools:mcp_web_search",
            "app.mcp.agent_tools:mcp_web_scrape",
        ],
        instruction_blocks=[
            "skills_registry",
            "web_research",
            "context_memory",
            "self_improvement",
            "escalation",
            "app_builder_handoff",
        ],
        sub_agents=["data_insight"],
        callbacks=["context_memory", "tool_progress"],
        persona_aware=True,
        routing_description="Data analysis, NL queries, cohorts, anomaly detection, forecasting, weekly reports, external DB queries, GA4/analytics",
    ),
    "data_insight": AgentManifest(
        name="DataInsightAgent",
        description="Produces structured data analysis insights for dashboards and reports",
        role_definition=(
            "You are a data insight generator. Compare current vs previous "
            "values, calculate percentage change, detect anomalies, and produce "
            "a DataInsight JSON object."
        ),
        model_profile="deep",
        config_profile="DEEP",
        output_schema="DataInsight",
        include_contents="none",
        callbacks=[],
        routing_description="",
    ),
    # -------------------------------------------------------------------------
    # Data Reporting
    # -------------------------------------------------------------------------
    "data_reporting": AgentManifest(
        name="DataReportingAgent",
        description="Automated spreadsheet analysis, custom sheet creation, and report generation for sales, expenses, inventory, KPIs, and time tracking",
        role_definition=(
            "You are the Data Reporting Agent, specialized in spreadsheet "
            "analysis and automated report generation. Connect to Google "
            "Sheets, design custom tracking structures, and generate hourly/"
            "daily/weekly/monthly/quarterly/yearly reports. Always prioritize "
            "actionable insights over raw data."
        ),
        model_profile="deep",
        config_profile="DEEP",
        tool_modules=[
            "app.agents.enhanced_tools:use_skill",
            "app.agents.enhanced_tools:list_available_skills",
            "app.agents.tools.google_sheets",
            "app.agents.tools.document_gen",
            "app.agents.tools.report_scheduling",
            "app.agents.tools.gmail",
            "app.agents.tools.calendar_tool",
            "app.agents.tools.docs",
            "app.agents.tools.forms",
            "app.agents.tools.context_memory",
            "app.agents.tools.quick_research",
        ],
        instruction_blocks=[
            "context_memory",
            "skills_registry",
            "self_improvement",
            "escalation",
            "app_builder_handoff",
        ],
        sub_agents=["data_report_generator"],
        callbacks=["context_memory", "tool_progress"],
        persona_aware=True,
        routing_description="Spreadsheet reporting, custom sheet creation, scheduled reports (PDF/PPTX/XLSX), email delivery, customer feedback forms",
    ),
    "data_report_generator": AgentManifest(
        name="ReportGeneratorAgent",
        description="Generates structured JSON reports from spreadsheet data",
        role_definition=(
            "You are a Report Generator that produces structured JSON reports. "
            "Analyze spreadsheet data and produce executive summary, trend "
            "analysis, key metrics, and recommendations. Output MUST match the "
            "DataInsight schema."
        ),
        model_profile="deep",
        config_profile="DEEP",
        output_schema="DataInsight",
        include_contents="none",
        callbacks=[],
        routing_description="",
    ),
    # -------------------------------------------------------------------------
    # Research
    # -------------------------------------------------------------------------
    "research": AgentManifest(
        name="ResearchAgent",
        description="Research Intelligence Agent - multi-track research, knowledge graph, continuous intelligence",
        role_definition=(
            "You are the Research Intelligence Agent. You handle multi-track "
            "research workflows, query planning, parallel track execution, "
            "synthesis, knowledge-graph writing, persona-aware synthesis, and "
            "continuous monitoring. Track cost across runs and route adaptively."
        ),
        model_profile="deep",
        config_profile="DEEP",
        tool_modules=[
            "app.agents.research.tools.query_planner",
            "app.agents.research.tools.track_runner",
            "app.agents.research.tools.synthesizer",
            "app.agents.research.tools.graph_writer",
            "app.agents.research.tools.cost_tracker",
            "app.agents.research.tools.adaptive_router",
            "app.agents.research.tools.monitoring_tools",
            "app.agents.research.tools.persona_synthesizer",
            "app.agents.tools.graph_tools",
            "app.agents.tools.context_memory",
        ],
        instruction_blocks=["context_memory"],
        sub_agents=[],
        callbacks=["context_memory", "tool_progress"],
        persona_aware=False,
        routing_description="Deep multi-track research, knowledge graph synthesis, continuous monitoring, persona-aware insight generation",
    ),
    # -------------------------------------------------------------------------
    # Admin (separate platform-management agent; not in Executive's sub_agents)
    # -------------------------------------------------------------------------
    "admin": AgentManifest(
        name="AdminAgent",
        description=(
            "AI admin assistant for Pikar-AI platform management - "
            "routes to 5 specialist sub-agents: system health, users, billing, governance, and knowledge"
        ),
        role_definition=(
            "You are the AdminAgent - the Pikar-AI platform management console. "
            "You are a routing agent: delegate to SystemHealthAgent, "
            "UserManagementAgent, BillingAgent, GovernanceAgent, or "
            "KnowledgeAgent based on intent. Enforce autonomy tiers (AUTO / "
            "CONFIRM / BLOCKED) at the tool layer."
        ),
        model_profile="routing",
        config_profile="FAST",
        tool_modules=[],  # parent has NO tools - pure router
        instruction_blocks=["context_memory", "app_builder_handoff"],
        sub_agents=[],  # 5 admin sub-agents constructed in admin/agent.py
        callbacks=["context_memory", "tool_progress"],
        persona_aware=False,
        routing_description="",
    ),
}


__all__ = [
    "AgentManifest",
    "INSTRUCTION_BLOCK_ORDER",
    "MANIFESTS",
    "compose_instruction",
    "compose_routing_table",
    "resolve_tool_modules",
]
