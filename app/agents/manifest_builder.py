# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Build LlmAgent instances from :class:`AgentManifest` declarations.

This is the canonical proof that ``MANIFESTS`` is sufficient to construct a
production agent: the Executive currently switches between this builder and
its legacy factory via the ``USE_MANIFESTS`` env flag.

For specialist agents the legacy ``create_<domain>_agent`` factories remain
authoritative; the manifests are landed alongside as the migration target.
"""

from __future__ import annotations

import logging

from app.agents import shared as shared_models
from app.agents.base_agent import PikarAgent as Agent
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
    tool_progress_before_tool_callback,
)
from app.agents.handoff_packet import handoff_packet_before_agent_callback
from app.agents.manifest import (
    MANIFESTS,
    AgentManifest,
    compose_instruction,
    resolve_tool_modules,
)
from app.agents.tools.base import sanitize_tools as _sanitize
from app.agents.tools.tool_timing import apply_timing
from app.personas.prompt_fragments import build_persona_policy_block

logger = logging.getLogger(__name__)


# =============================================================================
# Profile resolution
# =============================================================================


def _resolve_model(profile: str):
    """Map ``model_profile`` to the appropriate factory call.

    The factories live in ``app.agents.shared``. We resolve at call time so
    every ``build_agent`` invocation respects the live model_failover state.
    """
    if profile == "routing":
        return shared_models.get_routing_model()
    if profile == "fast":
        return shared_models.get_fast_model()
    # "deep" and "creative" both resolve to the standard Gemini model;
    # the per-config tuning (temperature, max tokens) handles creativity.
    return shared_models.get_model()


def _resolve_config(profile: str):
    """Map ``config_profile`` to the GenerateContentConfig instance."""
    return getattr(shared_models, f"{profile}_AGENT_CONFIG")


def _resolve_output_schema(name: str | None):
    """Look up a Pydantic schema class on ``app.agents.schemas`` by name."""
    if not name:
        return None
    from app.agents import schemas  # local import keeps the manifest module light

    return getattr(schemas, name, None)


# =============================================================================
# Public builder
# =============================================================================


def build_agent(
    manifest: AgentManifest,
    persona: str | None = None,
    name_suffix: str = "",
) -> Agent:
    """Construct an :class:`Agent` (LlmAgent) from a manifest.

    Args:
        manifest: The manifest to materialize.
        persona: Optional persona tier (solopreneur/startup/sme/enterprise).
            Applied only when ``manifest.persona_aware`` is True.
        name_suffix: Optional suffix appended to ``manifest.name`` -- mirrors
            the convention used by the legacy factory functions when an agent
            is reused inside a workflow pipeline.

    Returns:
        A new ``PikarAgent`` instance with no parent assignment.
    """
    name = f"{manifest.name}{name_suffix}" if name_suffix else manifest.name

    # ---- output_schema fast path -------------------------------------------
    # ADK forbids before_model_callback / after_tool_callback on agents with
    # output_schema. These agents run in pure structured-JSON mode.
    if manifest.output_schema:
        schema_cls = _resolve_output_schema(manifest.output_schema)
        return Agent(
            name=name,
            model=_resolve_model(manifest.model_profile),
            description=manifest.description or manifest.role_definition[:120],
            instruction=manifest.role_definition,
            output_schema=schema_cls,
            output_key=_default_output_key(manifest),
            include_contents=manifest.include_contents or "none",
        )

    # ---- Tools --------------------------------------------------------------
    tools = resolve_tool_modules(manifest.tool_modules)
    tools = _sanitize(apply_timing(tools)) if tools else []

    # ---- Instruction (compose -> persona) -----------------------------------
    instruction = compose_instruction(manifest)
    if manifest.persona_aware and persona:
        block = build_persona_policy_block(persona, agent_name=manifest.name)
        if block:
            instruction = instruction + "\n\n" + block

    # ---- Sub-agents ---------------------------------------------------------
    sub_agents = []
    for sub_key in manifest.sub_agents:
        sub_manifest = MANIFESTS.get(sub_key)
        if sub_manifest is None:
            logger.warning(
                "manifest_builder: sub-agent key %s missing from MANIFESTS", sub_key
            )
            continue
        sub_agents.append(build_agent(sub_manifest, persona=persona))

    # ---- Callbacks ----------------------------------------------------------
    before_model = None
    before_tool = None
    after_tool = None
    before_agent = None
    if "context_memory" in manifest.callbacks:
        before_model = context_memory_before_model_callback
        after_tool = context_memory_after_tool_callback
    if "tool_progress" in manifest.callbacks:
        before_tool = tool_progress_before_tool_callback
    if "handoff_packet" in manifest.callbacks:
        before_agent = handoff_packet_before_agent_callback

    return Agent(
        name=name,
        model=_resolve_model(manifest.model_profile),
        description=manifest.description or manifest.role_definition[:120],
        instruction=instruction,
        tools=tools,
        sub_agents=sub_agents,
        generate_content_config=_resolve_config(manifest.config_profile),
        before_agent_callback=before_agent,
        before_model_callback=before_model,
        before_tool_callback=before_tool,
        after_tool_callback=after_tool,
    )


def _default_output_key(manifest: AgentManifest) -> str:
    """Best-effort output_key for structured-JSON sub-agents.

    Mirrors the existing convention: ``FinancialReport`` -> ``financial_report``.
    """
    schema = manifest.output_schema or ""
    out: list[str] = []
    for i, ch in enumerate(schema):
        if ch.isupper() and i > 0:
            out.append("_")
        out.append(ch.lower())
    return "".join(out) or "output"


__all__ = ["build_agent"]
