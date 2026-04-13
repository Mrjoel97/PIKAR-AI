# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Feature adoption tool for the AdminAgent (Phase 69).

Provides the ``get_feature_adoption`` admin tool that surfaces per-agent
tool usage metrics via ``FeatureAdoptionService``.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.admin.tools._autonomy import check_autonomy as _check_autonomy
from app.services.feature_adoption_service import FeatureAdoptionService

logger = logging.getLogger(__name__)

_ACTION_NAME = "get_feature_adoption"


async def get_feature_adoption(
    days: int = 30,
    user_id: str | None = None,
) -> dict[str, Any]:
    """Return per-agent feature adoption metrics from tool_telemetry.

    Shows which agents and tools are actively used, helping admins understand
    capability adoption patterns across the platform.

    Autonomy tier: auto (read-only analytics).

    Args:
        days: Look-back window in days (default 30).
        user_id: Optional UUID to restrict metrics to a single user. When None,
            returns platform-wide adoption across all users.

    Returns:
        Dict with:
        - ``agent_adoption``: list of per-agent metrics (agent_name,
          unique_tools_used, total_calls, top_tools, unique_users when platform-wide)
        - ``total_agents_active``: number of distinct active agents
        - ``total_unique_tools``: number of distinct tools seen
        - ``period_days``: the look-back window used
        On blocked autonomy tier: ``{"error": "..."}``
    """
    gate = await _check_autonomy(_ACTION_NAME)
    if gate is not None:
        return gate

    service = FeatureAdoptionService()
    return await service.compute_adoption(days=days, user_id=user_id)
