# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Agents module - Contains all AI agent definitions.

The package init is intentionally empty so that importing any sub-module
(``app.agents.admin``, ``app.agents.tools.*``, etc.) does NOT cascade into
``app.agents.specialized_agents`` and instantiate all 10 specialized agents
at import time. That eager construction was costing ~14s of CPU before
gunicorn workers could accept TCP, which caused Cloud Run startup-probe
timeouts.

For specific agents, import directly from the source module, e.g.:

    from app.agents.specialized_agents import SPECIALIZED_AGENTS, financial_agent
    from app.agents.financial import create_financial_agent
"""

__all__: list[str] = []


def __getattr__(name: str):
    """Lazy backward-compat shim — proxy unknown attribute access to the
    specialized_agents re-export module so legacy ``from app.agents import X``
    callers (if any reappear) still work without paying the import cost
    until first access."""
    if name in {
        "SPECIALIZED_AGENTS",
        "compliance_agent",
        "content_agent",
        "customer_support_agent",
        "data_agent",
        "financial_agent",
        "hr_agent",
        "marketing_agent",
        "operations_agent",
        "sales_agent",
        "strategic_agent",
    }:
        from app.agents import specialized_agents as _spec

        return getattr(_spec, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
