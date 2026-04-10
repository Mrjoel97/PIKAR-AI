# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Decision Journal ADK tools for the Executive Agent.

Provides tools to log significant business decisions and query past decisions
by topic. Logged decisions also appear in the unified action history for the
cross-agent activity feed.
"""

import logging

from app.services.decision_journal_service import get_decision_journal_service
from app.services.request_context import get_current_user_id
from app.services.unified_action_history_service import log_agent_action

logger = logging.getLogger(__name__)


async def log_decision(
    topic: str,
    decision_text: str,
    rationale: str = "",
    outcome: str = "",
) -> dict:
    """Log a significant business decision for future reference.

    Use whenever a meaningful choice is made about strategy, budget,
    hiring, product direction, partnerships, or operations.

    Args:
        topic: Short topic label (e.g. "Pricing strategy", "Q3 hiring plan").
        decision_text: The actual decision that was made.
        rationale: Why this decision was made.
        outcome: Expected or recorded outcome.

    Returns:
        Dictionary with success status, decision_id, and topic.
    """
    try:
        user_id = get_current_user_id()
        if not user_id:
            return {
                "success": False,
                "error": "No user context available. Please ensure you are logged in.",
            }

        service = get_decision_journal_service()
        result = await service.log_decision(
            user_id=user_id,
            topic=topic,
            decision_text=decision_text,
            rationale=rationale or None,
            outcome=outcome or None,
        )

        if result is None:
            return {"success": False, "error": "Failed to log decision."}

        # Also record in the unified action history for the activity feed
        await log_agent_action(
            user_id,
            "StrategicPlanningAgent",
            "decision_logged",
            f"Decision: {topic}",
            source_type="decision",
            source_id=result["id"],
        )

        return {
            "success": True,
            "decision_id": result["id"],
            "topic": topic,
        }
    except Exception as exc:
        logger.warning("Failed to log decision via tool: %s", exc)
        return {"success": False, "error": f"Could not log decision: {exc}"}


async def query_decisions(topic: str = "") -> dict:
    """Search past business decisions.

    Use when the user asks "What did we decide about X?" or wants to
    recall a previous decision.

    Args:
        topic: Optional keyword to search for in decision topics.
            Leave empty to retrieve recent decisions.

    Returns:
        Dictionary with success status, list of decisions, count, and
        instruction for presenting results.
    """
    try:
        user_id = get_current_user_id()
        if not user_id:
            return {
                "success": False,
                "error": "No user context available. Please ensure you are logged in.",
            }

        service = get_decision_journal_service()
        decisions = await service.query_decisions(
            user_id,
            topic=topic or None,
        )

        return {
            "success": True,
            "decisions": decisions,
            "count": len(decisions),
            "instruction": (
                "Present these decisions clearly with dates, rationale, "
                "and any recorded outcomes."
            ),
        }
    except Exception as exc:
        logger.warning("Failed to query decisions via tool: %s", exc)
        return {"success": False, "error": f"Could not query decisions: {exc}"}


DECISION_JOURNAL_TOOLS = [log_decision, query_decisions]
