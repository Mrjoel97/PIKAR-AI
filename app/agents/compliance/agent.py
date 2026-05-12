# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Compliance & Risk Agent — built on PikarBaseAgent (W4 migration).

The director surface (model, tools, lifecycle callbacks, ops config) is
assembled by :class:`~app.agents.base_agent.PikarBaseAgent` from
``instructions.md`` + ``operations.yaml`` + :func:`build_tools_manifest`.

The RiskReportAgent sub-agent stays as a plain :class:`PikarAgent` —
it's a structured-output specialist (``output_schema=RiskAssessment``,
``include_contents="none"``) that ADK forbids from registering
lifecycle callbacks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.agents.base_agent import PikarAgent, PikarBaseAgent
from app.agents.compliance.tools import build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.schemas import RiskAssessment
from app.agents.shared import DEEP_AGENT_CONFIG, get_model
from app.skills.registry import AgentID

_AGENT_DIR = Path(__file__).parent
_INSTRUCTIONS_PATH = _AGENT_DIR / "instructions.md"
_OPS_CONFIG_PATH = _AGENT_DIR / "operations.yaml"


_RISK_REPORT_INSTRUCTION = """You are a risk assessment specialist. Evaluate risks and produce structured assessments.

REQUIREMENTS:
- Assign category: legal, financial, operational, or reputational
- Assess severity and probability
- Calculate impact score (1-25 based on severity * probability matrix)
- Provide mitigation strategy
- Assign owner and due date when applicable

Your output MUST be a valid JSON object matching the RiskAssessment schema exactly."""


def _create_risk_report_agent() -> PikarAgent:
    """Build a structured-output RiskReportAgent.

    Memory-callback exception: ADK forbids before_model_callback /
    after_tool_callback when ``output_schema`` is set.
    """
    return PikarAgent(
        name="RiskReportAgent",
        model=get_model(),
        description="Produces structured risk assessment reports for risk registers and dashboards",
        instruction=_RISK_REPORT_INSTRUCTION,
        output_schema=RiskAssessment,
        output_key="risk_assessment",
        include_contents="none",
    )


def create_compliance_agent(
    name_suffix: str = "",
    output_key: str | None = None,
    persona: str | None = None,
    *,
    user_id: UUID | None = None,
    persona_id: str | None = None,
    **extra: Any,
) -> PikarBaseAgent:
    """Build a fresh ComplianceRiskAgent bound to a user + persona."""
    _ = name_suffix  # legacy positional arg — name derived from AgentID
    ops = OperationsConfig.load(_OPS_CONFIG_PATH)
    bound_persona = persona_id or persona or "default"
    bound_user = user_id if user_id is not None else uuid4()
    return PikarBaseAgent(
        agent_id=AgentID.LEGAL,
        instructions_path=_INSTRUCTIONS_PATH,
        tools_manifest=build_tools_manifest(ops),
        ops_config_path=_OPS_CONFIG_PATH,
        user_id=bound_user,
        persona_id=bound_persona,
        description="Legal Counsel - Compliance, risk assessment, and legal guidance",
        generate_content_config=DEEP_AGENT_CONFIG,
        output_key=output_key,
        sub_agents=[_create_risk_report_agent()],
        **extra,
    )


# Module-level singleton retained as a sentinel for legacy callers.
compliance_agent: PikarAgent | None = None


__all__ = ["create_compliance_agent", "compliance_agent"]
