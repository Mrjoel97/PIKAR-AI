# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Cross-Agent Business Synthesis Tool for the Executive Agent.

Provides a holistic view of business health by gathering data from
Financial, Sales, Marketing, and Data domains in parallel.
"""

import logging

from app.services.cross_agent_synthesis_service import (
    get_cross_agent_synthesis_service,
)
from app.services.request_context import get_current_user_id

logger = logging.getLogger(__name__)


async def synthesize_business_health(time_range_days: int = 7) -> dict:
    """Get a holistic view of business health across all domains.

    Call this when the user asks broad questions like "How is my business
    doing?", "Give me an overview", "What's the state of things?", or
    "How are we performing?". Gathers data from Financial, Sales,
    Marketing, and Data domains in parallel and returns a unified
    health snapshot.

    Args:
        time_range_days: How many days back to analyze (default 7).

    Returns:
        Dictionary with success status, health_snapshot containing
        domain sections, and an instruction for response synthesis.
    """
    try:
        user_id = get_current_user_id()
        if not user_id:
            return {
                "success": False,
                "error": "No user context available. Please ensure you are logged in.",
            }

        service = get_cross_agent_synthesis_service()
        result = await service.gather_business_health(
            user_id, time_range_days=time_range_days
        )

        return {
            "success": True,
            "health_snapshot": result,
            "sections": list(result.keys()),
            "instruction": (
                "Synthesize these findings into a coherent, conversational "
                "business health summary. Lead with the most important insight. "
                "Use plain English, not raw data dumps."
            ),
        }
    except Exception as exc:
        logger.warning("Failed to synthesize business health: %s", exc)
        return {
            "success": False,
            "error": f"Could not gather business health data: {exc}",
        }


CROSS_AGENT_SYNTHESIS_TOOLS = [synthesize_business_health]
