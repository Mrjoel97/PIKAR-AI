# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Onboarding Nudge ADK tool for the Executive Agent.

Provides a tool that checks whether the current user has any contextual
onboarding nudges to display. Should be called at the start of
conversations for users in their first 7 days.
"""

import logging

from app.services.onboarding_nudge_service import get_onboarding_nudge_service
from app.services.request_context import get_current_user_id

logger = logging.getLogger(__name__)


async def check_onboarding_nudges() -> dict:
    """Check if the current user has any onboarding nudges.

    Call this at the START of every conversation for users in their
    first 7 days. If nudges exist, weave them naturally into your
    response.

    Returns:
        Dictionary with has_nudges flag, list of nudges, and an
        instruction for how to present them conversationally.
    """
    try:
        user_id = get_current_user_id()
        if not user_id:
            return {
                "has_nudges": False,
                "nudges": [],
                "instruction": "No user context available.",
            }

        service = get_onboarding_nudge_service()
        nudges = await service.check_nudges(user_id)

        return {
            "has_nudges": len(nudges) > 0,
            "nudges": nudges,
            "instruction": (
                "If nudges exist, naturally mention them in your response. "
                "Don't be pushy -- frame as helpful suggestions. Example: "
                "'By the way, I noticed you haven't tried [X] yet -- "
                "it's a quick win that [benefit].'"
            ),
        }
    except Exception as exc:
        logger.warning("Failed to check onboarding nudges: %s", exc)
        return {
            "has_nudges": False,
            "nudges": [],
            "instruction": f"Could not check nudges: {exc}",
        }


ONBOARDING_NUDGE_TOOLS = [check_onboarding_nudges]
