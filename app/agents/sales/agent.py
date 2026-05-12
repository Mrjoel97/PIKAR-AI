# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Sales Intelligence Agent — built on PikarBaseAgent (W4 migration).

The director surface (model, tools, lifecycle callbacks, ops config) is
assembled by :class:`~app.agents.base_agent.PikarBaseAgent` from
``instructions.md`` + ``operations.yaml`` + :func:`build_tools_manifest`.

The LeadScoringAgent sub-agent stays as a plain :class:`PikarAgent` —
it's a structured-output specialist (``output_schema=LeadQualification``,
``include_contents="none"``) that ADK forbids from registering
lifecycle callbacks. The director wires it as ``sub_agents=[...]`` via
``**extra``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.agents.base_agent import PikarAgent, PikarBaseAgent
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.sales.tools import build_tools_manifest
from app.agents.schemas import LeadQualification
from app.agents.shared import DEEP_AGENT_CONFIG, get_model
from app.skills.registry import AgentID

_AGENT_DIR = Path(__file__).parent
_INSTRUCTIONS_PATH = _AGENT_DIR / "instructions.md"
_OPS_CONFIG_PATH = _AGENT_DIR / "operations.yaml"


_LEAD_SCORING_INSTRUCTION = """You are a lead scoring specialist. Evaluate leads and produce structured qualification assessments.

REQUIREMENTS:
- Apply the specified framework (BANT, MEDDIC, or CHAMP)
- Score each criterion individually
- Calculate overall score (0-100)
- Determine qualification status and priority
- Provide specific next steps

Your output MUST be a valid JSON object matching the LeadQualification schema exactly."""


def _create_lead_scoring_agent() -> PikarAgent:
    """Build a structured-output LeadScoringAgent.

    Memory-callback exception: ADK forbids before_model_callback /
    after_tool_callback when ``output_schema`` is set, so this sub-agent
    intentionally has no callbacks. The parent director carries the
    user context that drives scoring.
    """
    return PikarAgent(
        name="LeadScoringAgent",
        model=get_model(),
        description="Scores and qualifies leads with structured JSON output for CRM integration",
        instruction=_LEAD_SCORING_INSTRUCTION,
        output_schema=LeadQualification,
        output_key="lead_qualification",
        include_contents="none",
    )


def create_sales_agent(
    name_suffix: str = "",
    output_key: str | None = None,
    persona: str | None = None,
    *,
    user_id: UUID | None = None,
    persona_id: str | None = None,
    **extra: Any,
) -> PikarBaseAgent:
    """Build a fresh SalesIntelligenceAgent bound to a user + persona."""
    _ = name_suffix  # legacy positional arg — name derived from AgentID
    ops = OperationsConfig.load(_OPS_CONFIG_PATH)
    bound_persona = persona_id or persona or "default"
    bound_user = user_id if user_id is not None else uuid4()
    return PikarBaseAgent(
        agent_id=AgentID.SALES,
        instructions_path=_INSTRUCTIONS_PATH,
        tools_manifest=build_tools_manifest(ops),
        ops_config_path=_OPS_CONFIG_PATH,
        user_id=bound_user,
        persona_id=bound_persona,
        description="Head of Sales - Deal scoring, lead analysis, and sales enablement",
        generate_content_config=DEEP_AGENT_CONFIG,
        output_key=output_key,
        sub_agents=[_create_lead_scoring_agent()],
        **extra,
    )


# Module-level singleton retained as a sentinel for legacy callers.
sales_agent: PikarAgent | None = None


__all__ = ["create_sales_agent", "sales_agent"]
