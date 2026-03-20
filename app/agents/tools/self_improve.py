"""Self-Improvement Tools - Agent tools for the autonomous iteration system.

These tools enable agents to:
1. Report interaction quality signals (feedback logging)
2. Check their own performance metrics
3. Identify skill gaps from user queries
4. Trigger improvement cycles
5. View improvement history

Inspired by Karpathy's autoresearch: agents participate in their own improvement
loop by reporting signals and consuming improvement recommendations.
"""

import asyncio
import concurrent.futures
import logging
from collections.abc import Callable
from typing import Any

from app.agents.tools.base import agent_tool
from app.skills.registry import AgentID

logger = logging.getLogger(__name__)


# =============================================================================
# Helpers
# =============================================================================


def _run_async(coro):
    """Run an async coroutine from a sync context (ADK tools are sync)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(asyncio.run, coro).result()
        return asyncio.run(coro)
    except Exception as exc:
        logger.warning("Failed to run async operation: %s", exc)
        return None


def _get_logger():
    """Lazy import to avoid circular imports at module load."""
    from app.services.interaction_logger import interaction_logger

    return interaction_logger


def _get_engine():
    """Lazy import to avoid circular imports at module load."""
    from app.services.self_improvement_engine import SelfImprovementEngine

    return SelfImprovementEngine()


# =============================================================================
# Tool Factories (agent-aware, like agent_skills.py pattern)
# =============================================================================


def _create_report_interaction(agent_id: AgentID) -> Callable:
    """Create a tool for agents to log interaction quality signals."""

    @agent_tool
    def report_interaction(
        user_query: str,
        response_summary: str | None = None,
        skill_used: str | None = None,
        task_completed: str | None = None,
    ) -> dict[str, Any]:
        """Report an interaction for the self-improvement system.

        Call this after handling a user request to log quality signals.
        The system uses these signals to improve skills over time.

        Args:
            user_query: What the user asked or requested.
            response_summary: Brief summary of your response (first 200 chars).
            skill_used: Name of the skill you used, if any.
            task_completed: Whether the task was completed: 'yes', 'no', or 'partial'.

        Returns:
            Confirmation that the interaction was logged.
        """
        try:
            il = _get_logger()
            completed = None
            if task_completed:
                completed = task_completed.lower() in ("yes", "true", "1")

            result = _run_async(
                il.log_interaction(
                    agent_id=agent_id.value,
                    user_query=user_query,
                    agent_response_summary=(response_summary or "")[:500],
                    skill_used=skill_used,
                    task_completed=completed,
                )
            )
            return {
                "success": True,
                "message": "Interaction logged for self-improvement analysis.",
                "interaction_id": result.get("id") if result else None,
            }
        except Exception as exc:
            logger.warning("report_interaction failed: %s", exc)
            return {"success": True, "message": "Interaction noted (logging degraded)."}

    return report_interaction


def _create_report_gap(agent_id: AgentID) -> Callable:
    """Create a tool for agents to report skill coverage gaps."""

    @agent_tool
    def report_skill_gap(
        user_query: str,
        closest_skills: str | None = None,
    ) -> dict[str, Any]:
        """Report a skill gap when you lack the knowledge to fully answer a query.

        Call this when a user asks something outside your current skill set.
        The self-improvement system will use this to create new skills.

        Args:
            user_query: The user's question or request you couldn't fully handle.
            closest_skills: Comma-separated names of skills that partially matched.

        Returns:
            Confirmation that the gap was recorded.
        """
        try:
            il = _get_logger()
            matched = (
                [s.strip() for s in closest_skills.split(",")] if closest_skills else []
            )
            _run_async(
                il.log_coverage_gap(
                    agent_id=agent_id.value,
                    user_query=user_query,
                    matched_skills=matched,
                    confidence_score=0.3 if matched else 0.0,
                )
            )
            return {
                "success": True,
                "message": "Skill gap recorded. The system will analyze and potentially create a new skill.",
            }
        except Exception as exc:
            logger.warning("report_skill_gap failed: %s", exc)
            return {"success": True, "message": "Gap noted (logging degraded)."}

    return report_skill_gap


def _create_check_performance(agent_id: AgentID) -> Callable:
    """Create a tool for agents to check their own performance metrics."""

    @agent_tool
    def check_my_performance(
        days: int = 7,
    ) -> dict[str, Any]:
        """Check this agent's performance metrics from the self-improvement system.

        Use this to understand how well your skills are performing and
        where you can improve.

        Args:
            days: Number of days to look back (default 7).

        Returns:
            Performance metrics including skill effectiveness scores and trends.
        """
        try:
            il = _get_logger()
            stats = _run_async(
                il.get_interaction_stats(
                    agent_id=agent_id.value,
                    days=days,
                )
            )
            if not stats:
                return {
                    "success": True,
                    "message": "No interaction data available yet. Keep working and check back later.",
                    "metrics": {},
                }
            return {
                "success": True,
                "agent_id": agent_id.value,
                "period_days": days,
                "metrics": stats,
            }
        except Exception as exc:
            logger.warning("check_my_performance failed: %s", exc)
            return {
                "success": False,
                "error": f"Could not retrieve metrics: {exc}",
            }

    return check_my_performance


def _create_get_improvement_suggestions(agent_id: AgentID) -> Callable:
    """Create a tool for agents to see pending improvement recommendations."""

    @agent_tool
    def get_improvement_suggestions(
        limit: int = 10,
    ) -> dict[str, Any]:
        """Get pending improvement suggestions from the self-improvement engine.

        These are recommendations for how to improve skills, fill gaps,
        or refine agent behavior based on user interaction data.

        Args:
            limit: Maximum number of suggestions to return (default 10).

        Returns:
            List of improvement suggestions with action types and details.
        """
        try:
            engine = _get_engine()
            suggestions = _run_async(
                engine.get_pending_actions(
                    agent_id=agent_id.value,
                    limit=limit,
                )
            )
            if not suggestions:
                return {
                    "success": True,
                    "message": "No pending improvements. The system is running well.",
                    "suggestions": [],
                }
            return {
                "success": True,
                "count": len(suggestions),
                "suggestions": suggestions,
            }
        except Exception as exc:
            logger.warning("get_improvement_suggestions failed: %s", exc)
            return {"success": False, "error": str(exc)}

    return get_improvement_suggestions


def _create_trigger_improvement(agent_id: AgentID) -> Callable:
    """Create a tool for the executive agent to trigger improvement cycles."""

    @agent_tool
    def trigger_improvement_cycle(
        auto_execute: str | None = None,
        days: int = 7,
    ) -> dict[str, Any]:
        """Trigger a self-improvement evaluation cycle.

        This runs the full autoresearch-inspired loop:
        1. Evaluate all skill effectiveness scores
        2. Identify underperformers, gaps, and opportunities
        3. Optionally auto-execute improvements

        Only the Executive Agent should trigger this.

        Args:
            auto_execute: Set to 'yes' to auto-execute safe improvements.
                         Default is evaluation + recommendations only.
            days: Number of days of interaction data to analyze (default 7).

        Returns:
            Summary of the improvement cycle results.
        """
        if agent_id != AgentID.EXEC:
            return {
                "success": False,
                "error": "Only the Executive Agent can trigger improvement cycles.",
            }
        try:
            engine = _get_engine()
            execute = (auto_execute or "").lower() in ("yes", "true", "1")
            result = _run_async(
                engine.run_improvement_cycle(
                    auto_execute=execute,
                    days=days,
                )
            )
            return {
                "success": True,
                "message": "Improvement cycle completed.",
                "results": result or {},
            }
        except Exception as exc:
            logger.warning("trigger_improvement_cycle failed: %s", exc)
            return {"success": False, "error": str(exc)}

    return trigger_improvement_cycle


# =============================================================================
# Public API: Tool set factories
# =============================================================================


def get_self_improve_tools(agent_id: AgentID) -> list:
    """Get the self-improvement tools configured for a specific agent.

    All agents get: report_interaction, report_skill_gap, check_my_performance,
                    get_improvement_suggestions.
    Executive agent also gets: trigger_improvement_cycle.

    Args:
        agent_id: The agent these tools are for.

    Returns:
        List of configured tool functions.
    """
    tools = [
        _create_report_interaction(agent_id),
        _create_report_gap(agent_id),
        _create_check_performance(agent_id),
        _create_get_improvement_suggestions(agent_id),
    ]
    # Only executive can trigger improvement cycles
    if agent_id == AgentID.EXEC:
        tools.append(_create_trigger_improvement(agent_id))
    return tools


# =============================================================================
# Pre-built tool sets for each agent (matching agent_skills.py pattern)
# =============================================================================

EXEC_IMPROVE_TOOLS = get_self_improve_tools(AgentID.EXEC)
FIN_IMPROVE_TOOLS = get_self_improve_tools(AgentID.FIN)
CONT_IMPROVE_TOOLS = get_self_improve_tools(AgentID.CONT)
STRAT_IMPROVE_TOOLS = get_self_improve_tools(AgentID.STRAT)
SALES_IMPROVE_TOOLS = get_self_improve_tools(AgentID.SALES)
MKT_IMPROVE_TOOLS = get_self_improve_tools(AgentID.MKT)
OPS_IMPROVE_TOOLS = get_self_improve_tools(AgentID.OPS)
HR_IMPROVE_TOOLS = get_self_improve_tools(AgentID.HR)
LEGAL_IMPROVE_TOOLS = get_self_improve_tools(AgentID.LEGAL)
SUPP_IMPROVE_TOOLS = get_self_improve_tools(AgentID.SUPP)
DATA_IMPROVE_TOOLS = get_self_improve_tools(AgentID.DATA)


# NOTE: SELF_IMPROVEMENT_INSTRUCTIONS moved to app.agents.shared_instructions
