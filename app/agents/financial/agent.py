# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Financial Analysis Agent — built on PikarBaseAgent (W2 pilot).

The agent surface (model, tools, lifecycle callbacks, ops config) is
assembled by :class:`~app.agents.base_agent.PikarBaseAgent` from
``instructions.md`` + ``operations.yaml`` + :func:`build_tools_manifest`.

Backward-compat path: legacy workflow factories (``app/workflows/*.py``)
call ``create_financial_agent()`` positionally with ``name_suffix``,
``output_key``, and ``persona``. Those callers still get a working
agent — we route them through the same :class:`PikarBaseAgent` factory
with synthesized identity, since pre-W2 the agent was rebuilt fresh
per workflow step anyway.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.agents.base_agent import PikarAgent, PikarBaseAgent
from app.agents.financial.tools import build_tools_manifest
from app.agents.runtime.operations_config import OperationsConfig
from app.skills.registry import AgentID

_AGENT_DIR = Path(__file__).parent
_INSTRUCTIONS_PATH = _AGENT_DIR / "instructions.md"
_OPS_CONFIG_PATH = _AGENT_DIR / "operations.yaml"


def create_financial_agent(
    name_suffix: str = "",
    output_key: str | None = None,
    persona: str | None = None,
    *,
    user_id: UUID | None = None,
    persona_id: str | None = None,
    **extra: Any,
) -> PikarBaseAgent:
    """Build a fresh FinancialAnalysisAgent bound to a user + persona.

    Accepts both the W2 keyword form (``user_id=``, ``persona_id=``) and
    the legacy positional form (``name_suffix``, ``output_key``,
    ``persona``) used by ``app/workflows/*.py`` factories. Legacy callers
    get a synthesized ``user_id`` so the agent boots; the workflow engine
    re-binds the per-user context at invocation time.
    """
    ops = OperationsConfig.load(_OPS_CONFIG_PATH)
    bound_persona = persona_id or persona or "default"
    bound_user = user_id if user_id is not None else uuid4()
    return PikarBaseAgent(
        agent_id=AgentID.FIN,
        instructions_path=_INSTRUCTIONS_PATH,
        tools_manifest=build_tools_manifest(ops),
        ops_config_path=_OPS_CONFIG_PATH,
        user_id=bound_user,
        persona_id=bound_persona,
        output_key=output_key,
        **extra,
    )


# Module-level singleton retained as a sentinel for legacy callers
# (``specialized_agents.SPECIALIZED_AGENTS`` filters out ``None``).
financial_agent: PikarAgent | None = None


__all__ = ["create_financial_agent", "financial_agent"]
