# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PersonaKey = Literal["solopreneur", "startup", "sme", "enterprise"]


@dataclass(frozen=True)
class PersonaPolicy:
    key: PersonaKey
    label: str
    summary: str
    core_objectives: tuple[str, ...]
    default_kpis: tuple[str, ...]
    budget_posture: str
    risk_posture: str
    response_style: str
    approval_posture: str
    planning_horizon: str
    output_contract: str
    delegation_style: str
    preferred_agents: tuple[str, ...]
    routing_priorities: tuple[str, ...]
    anti_patterns: tuple[str, ...]
