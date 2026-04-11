# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Cross-channel attribution agent tools.

Two agent-callable tools that surface unified marketing-channel performance
and ROAS-based budget reallocation recommendations via
``CrossChannelAttributionService``. Used by the parent MarketingAgent to
answer strategic questions like "which channel drives the most revenue?"
and "how should I reallocate my budget?".
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_user_id() -> str | None:
    """Extract the current user ID from the request-scoped context."""
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


async def get_cross_channel_attribution(days: int = 30) -> dict[str, Any]:
    """Return unified cross-channel attribution across Google Ads, Meta Ads, email, organic.

    Use this tool when the user asks about cross-channel performance,
    "which marketing channel is best", blended ROAS, or where revenue is
    coming from.

    Args:
        days: Lookback window in days (default 30).

    Returns:
        Dict with per-channel breakdown (spend, conversions, revenue, ROAS,
        cpa, share_of_revenue_pct), totals (spend, revenue, blended_roas),
        the period covered, and a plain-English ``summary_text`` the agent
        should paraphrase in its reply.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.cross_channel_attribution_service import (
            CrossChannelAttributionService,
        )

        svc = CrossChannelAttributionService()
        return await svc.get_attribution(user_id, days=days)
    except Exception as exc:
        logger.exception(
            "get_cross_channel_attribution failed for user=%s", user_id
        )
        return {"error": f"Failed to build cross-channel attribution: {exc}"}


async def get_budget_recommendation(days: int = 30) -> dict[str, Any]:
    """Return a ROAS-based budget reallocation recommendation across channels.

    Use this tool when the user asks "how should I allocate my budget", "where
    should I spend more", "which channel should I cut", or similar budget
    optimization questions.

    Args:
        days: Lookback window in days (default 30).

    Returns:
        Dict with ``recommendation_text`` (plain-English suggestion), the
        proposed ``shift_from`` and ``shift_to`` channels, ``expected_impact``,
        full ``channels`` attribution data, and an ``action_available`` flag.
        If no reallocation is useful (single channel or well-balanced ROAS),
        ``action_available`` is False and ``recommendation_text`` explains why.
    """
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}

    try:
        from app.services.cross_channel_attribution_service import (
            CrossChannelAttributionService,
        )

        svc = CrossChannelAttributionService()
        return await svc.get_budget_recommendation(user_id, days=days)
    except Exception as exc:
        logger.exception(
            "get_budget_recommendation failed for user=%s", user_id
        )
        return {"error": f"Failed to build budget recommendation: {exc}"}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

ATTRIBUTION_TOOLS = [
    get_cross_channel_attribution,
    get_budget_recommendation,
]

__all__ = [
    "ATTRIBUTION_TOOLS",
    "get_budget_recommendation",
    "get_cross_channel_attribution",
]
