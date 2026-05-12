# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Operations Optimization Agent — built on PikarBaseAgent (W4 migration).

The director surface (model, tools, lifecycle callbacks, ops config) is
assembled by :class:`~app.agents.base_agent.PikarBaseAgent` from
``instructions.md`` + ``operations.yaml`` + :func:`build_tools_manifest`.

The ConfigurationAgent sub-agent stays as a plain :class:`PikarAgent`
with its own toolset — it's an internal specialist of operations, not
a standalone director.
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
from app.agents.enhanced_tools import audit_user_setup_tool
from app.agents.operations.tools import build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.shared import DEEP_AGENT_CONFIG, get_fast_model
from app.agents.tools.api_connector import API_CONNECTOR_TOOLS
from app.agents.tools.base import sanitize_tools
from app.agents.tools.configuration import CONFIGURATION_TOOLS
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.integration_setup import INTEGRATION_SETUP_TOOLS
from app.skills.registry import AgentID

_AGENT_DIR = Path(__file__).parent
_INSTRUCTIONS_PATH = _AGENT_DIR / "instructions.md"
_OPS_CONFIG_PATH = _AGENT_DIR / "operations.yaml"


_CONFIG_TOOLS = sanitize_tools(
    [
        *CONFIGURATION_TOOLS,
        *API_CONNECTOR_TOOLS,
        *INTEGRATION_SETUP_TOOLS,
        audit_user_setup_tool,
        *CONTEXT_MEMORY_TOOLS,
    ]
)

_CONFIG_INSTRUCTION = """You are the Configuration & Integration sub-agent. You help users set up tools and manage API connections:
- Guide users through available tools and their setup (get_available_tools, get_tool_setup_guide)
- Explain tool benefits and recommend tools for specific goals
- Save API keys for external services (save_user_api_key)
- Connect, list, validate, and disconnect external APIs via OpenAPI specs
- Check integration status and guide setup
- Audit user setup to identify gaps
Always verify API keys are valid before saving. Never expose secrets in responses."""


def _create_config_agent() -> PikarAgent:
    """Create a Configuration & Integration sub-agent."""
    return PikarAgent(
        name="ConfigurationAgent",
        model=get_fast_model(),
        description="Tool setup, API key management, and external API connections — configure integrations and audit system health",
        instruction=_CONFIG_INSTRUCTION,
        tools=_CONFIG_TOOLS,
        before_model_callback=context_memory_before_model_callback,
        before_tool_callback=tool_progress_before_tool_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )


def create_operations_agent(
    name_suffix: str = "",
    persona: str | None = None,
    *,
    user_id: UUID | None = None,
    persona_id: str | None = None,
    **extra: Any,
) -> PikarBaseAgent:
    """Build a fresh OperationsOptimizationAgent bound to a user + persona."""
    _ = name_suffix  # legacy positional arg — name derived from AgentID
    ops = OperationsConfig.load(_OPS_CONFIG_PATH)
    bound_persona = persona_id or persona or "default"
    bound_user = user_id if user_id is not None else uuid4()
    return PikarBaseAgent(
        agent_id=AgentID.OPS,
        instructions_path=_INSTRUCTIONS_PATH,
        tools_manifest=build_tools_manifest(ops),
        ops_config_path=_OPS_CONFIG_PATH,
        user_id=bound_user,
        persona_id=bound_persona,
        description=(
            "COO / Operations Manager - process improvement, infrastructure, "
            "and configuration (routes to ConfigurationAgent for setup tasks)"
        ),
        generate_content_config=DEEP_AGENT_CONFIG,
        sub_agents=[_create_config_agent()],
        **extra,
    )


# Module-level singleton retained as a sentinel for legacy callers.
operations_agent: PikarAgent | None = None


__all__ = ["create_operations_agent", "operations_agent"]
