# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Customer Support Agent — built on PikarBaseAgent (W4 migration).

The agent surface (model, tools, lifecycle callbacks, ops config) is
assembled by :class:`~app.agents.base_agent.PikarBaseAgent` from
``instructions.md`` + ``operations.yaml`` + :func:`build_tools_manifest`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.agents.base_agent import PikarAgent, PikarBaseAgent
from app.agents.customer_support.tools import build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.agents.shared import DEEP_AGENT_CONFIG
from app.skills.registry import AgentID

_AGENT_DIR = Path(__file__).parent
_INSTRUCTIONS_PATH = _AGENT_DIR / "instructions.md"
_OPS_CONFIG_PATH = _AGENT_DIR / "operations.yaml"


def create_customer_support_agent(
    name_suffix: str = "",
    persona: str | None = None,
    *,
    user_id: UUID | None = None,
    persona_id: str | None = None,
    **extra: Any,
) -> PikarBaseAgent:
    """Build a fresh CustomerSupportAgent bound to a user + persona.

    Accepts both the W4 keyword form (``user_id=``, ``persona_id=``) and
    the legacy positional form (``name_suffix``, ``persona``) used by
    ``app/workflows/*.py`` factories.
    """
    _ = name_suffix  # legacy positional arg — name derived from AgentID
    ops = OperationsConfig.load(_OPS_CONFIG_PATH)
    bound_persona = persona_id or persona or "default"
    bound_user = user_id if user_id is not None else uuid4()
    return PikarBaseAgent(
        agent_id=AgentID.SUPP,
        instructions_path=_INSTRUCTIONS_PATH,
        tools_manifest=build_tools_manifest(ops),
        ops_config_path=_OPS_CONFIG_PATH,
        user_id=bound_user,
        persona_id=bound_persona,
        description=(
            "Customer Success Manager - Customer success, proactive support, "
            "communication drafting, and customer health monitoring"
        ),
        generate_content_config=DEEP_AGENT_CONFIG,
        **extra,
    )


# Module-level singleton retained as a sentinel for legacy callers.
customer_support_agent: PikarAgent | None = None


__all__ = ["create_customer_support_agent", "customer_support_agent"]
