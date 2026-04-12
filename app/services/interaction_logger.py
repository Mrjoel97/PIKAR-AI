# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""InteractionLogger - Fire-and-forget interaction logging for self-improvement.

This service logs every agent interaction to Supabase for later analysis by
the evaluation engine. All write operations are fire-and-forget: exceptions
are caught and logged as warnings, never propagated to callers.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.request_context import get_current_user_id
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async
from supabase import Client

logger = logging.getLogger(__name__)


class InteractionLogger:
    """Central service for logging agent interactions and coverage gaps.

    Singleton pattern -- use the module-level ``interaction_logger`` instance.

    Tables:
        interaction_logs  -- one row per agent interaction
        coverage_gaps     -- queries where no skill matched well
    """

    _instance: InteractionLogger | None = None

    def __new__(cls) -> InteractionLogger:
        """Singleton pattern to ensure one global logger."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            self._client: Client = get_service_client()
            self._interactions_table = "interaction_logs"
            self._gaps_table = "coverage_gaps"
            self._initialized = True

    # ==========================
    # Interaction Logging
    # ==========================

    async def log_interaction(
        self,
        agent_id: str,
        user_query: str,
        *,
        agent_response_summary: str | None = None,
        skill_used: str | None = None,
        skill_category: str | None = None,
        session_id: str | None = None,
        response_tokens: int | None = None,
        response_time_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
        research_used: bool = False,
        research_depth: str = "none",
        research_job_id: str | None = None,
        graph_entities_hit: int = 0,
        graph_freshness_avg: float | None = None,
        task_completed: bool | None = None,
        was_escalated: bool = False,
        had_followup: bool = False,
        user_feedback: str | None = None,
    ) -> str | None:
        """Log a single agent interaction.

        This is fire-and-forget: all exceptions are caught and logged as
        warnings so callers are never affected by logging failures.

        Args:
            agent_id: Which agent handled the interaction (e.g. "FIN", "MKT").
            user_query: The raw user query text.
            agent_response_summary: First 500 chars of the agent response.
            skill_used: Name of the skill invoked, if any.
            skill_category: Category of the skill invoked, if any.
            session_id: Session identifier for grouping interactions.
            response_tokens: Token count of the agent response.
            response_time_ms: Wall-clock response time in milliseconds.
            metadata: Arbitrary JSON metadata for analysis.
            task_completed: Whether the user's task was completed.
            was_escalated: Whether the interaction was escalated to a human.
            had_followup: Whether the user asked a follow-up question.
            user_feedback: One of 'positive', 'negative', or 'neutral'.

        Returns:
            The UUID string of the inserted row on success, None on failure.
        """
        try:
            user_id = get_current_user_id()

            # Truncate response summary to 500 chars
            if agent_response_summary and len(agent_response_summary) > 500:
                agent_response_summary = agent_response_summary[:500]

            data: dict[str, Any] = {
                "agent_id": agent_id,
                "user_query": user_query,
                "agent_response_summary": agent_response_summary,
                "skill_used": skill_used,
                "skill_category": skill_category,
                "session_id": session_id,
                "response_tokens": response_tokens,
                "response_time_ms": response_time_ms,
                "metadata": metadata or {},
                "user_id": user_id,
                "research_used": research_used,
                "research_depth": research_depth,
                "graph_entities_hit": graph_entities_hit,
            }
            if research_job_id is not None:
                data["research_job_id"] = research_job_id
            if graph_freshness_avg is not None:
                data["graph_freshness_avg"] = graph_freshness_avg
            if task_completed is not None:
                data["task_completed"] = task_completed
            if was_escalated:
                data["was_escalated"] = was_escalated
            if had_followup:
                data["had_followup"] = had_followup
            if user_feedback is not None:
                data["user_feedback"] = user_feedback

            response = await execute_async(
                self._client.table(self._interactions_table).insert(data),
                op_name="interaction_logger.log_interaction",
            )
            if response.data:
                return response.data[0]["id"]
            return None
        except Exception:
            logger.warning(
                "Failed to log interaction for agent=%s skill=%s",
                agent_id,
                skill_used,
                exc_info=True,
            )
            return None

    # ==========================
    # Upsert / Update Latest
    # ==========================

    async def update_latest_interaction(
        self,
        session_id: str,
        agent_id: str,
        *,
        task_completed: bool | None = None,
        was_escalated: bool | None = None,
        had_followup: bool | None = None,
        user_feedback: str | None = None,
        skill_used: str | None = None,
        agent_response_summary: str | None = None,
    ) -> bool:
        """Update the most-recent interaction row for a (session_id, agent_id) pair.

        This prevents duplicate inserts when the agent tool reports signals
        after the SSE logger has already created the initial row.

        Args:
            session_id: The session to look up.
            agent_id: The agent whose row to update.
            task_completed: Whether the task was completed.
            was_escalated: Whether the interaction was escalated.
            had_followup: Whether the user asked a follow-up.
            user_feedback: One of 'positive', 'negative', 'neutral'.
            skill_used: Name of the skill used.
            agent_response_summary: Brief summary of the response.

        Returns:
            True if a row was found and updated, False otherwise.
        """
        try:
            # Find the most-recent row for this session + agent
            existing = await execute_async(
                self._client.table(self._interactions_table)
                .select("id")
                .eq("session_id", session_id)
                .eq("agent_id", agent_id)
                .order("created_at", desc=True)
                .limit(1),
                op_name="interaction_logger.update_latest.select",
            )

            if not existing.data:
                return False

            row_id = existing.data[0]["id"]

            # Build update payload from non-None kwargs
            update_data: dict[str, Any] = {}
            if task_completed is not None:
                update_data["task_completed"] = task_completed
            if was_escalated is not None:
                update_data["was_escalated"] = was_escalated
            if had_followup is not None:
                update_data["had_followup"] = had_followup
            if user_feedback is not None:
                update_data["user_feedback"] = user_feedback
            if skill_used is not None:
                update_data["skill_used"] = skill_used
            if agent_response_summary is not None:
                update_data["agent_response_summary"] = agent_response_summary[:500]

            if not update_data:
                return True  # Nothing to update, but row exists

            await execute_async(
                self._client.table(self._interactions_table)
                .update(update_data)
                .eq("id", row_id),
                op_name="interaction_logger.update_latest.update",
            )
            return True
        except Exception:
            logger.warning(
                "Failed to update latest interaction for session=%s agent=%s",
                session_id,
                agent_id,
                exc_info=True,
            )
            return False

    # ==========================
    # Feedback Recording
    # ==========================

    async def record_feedback(
        self,
        interaction_id: str,
        feedback: str,
        *,
        was_escalated: bool = False,
        had_followup: bool = False,
        task_completed: bool | None = None,
    ) -> None:
        """Record user feedback on a previously-logged interaction.

        Args:
            interaction_id: The ``id`` of the interaction_logs row.
            feedback: One of 'positive', 'negative', or 'neutral'.
            was_escalated: Whether the interaction was escalated to a human.
            had_followup: Whether the user asked a follow-up question.
            task_completed: Whether the original task was completed.
        """
        try:
            update_data: dict[str, Any] = {
                "user_feedback": feedback,
                "was_escalated": was_escalated,
                "had_followup": had_followup,
            }
            if task_completed is not None:
                update_data["task_completed"] = task_completed

            await execute_async(
                self._client.table(self._interactions_table)
                .update(update_data)
                .eq("id", interaction_id),
                op_name="interaction_logger.record_feedback",
            )
        except Exception:
            logger.warning(
                "Failed to record feedback for interaction=%s",
                interaction_id,
                exc_info=True,
            )

    # ==========================
    # Coverage Gap Tracking
    # ==========================

    async def log_coverage_gap(
        self,
        agent_id: str,
        user_query: str,
        matched_skills: list[str],
        confidence_score: float,
    ) -> None:
        """Record a query where no skill matched well.

        Deduplicates within the last 7 days: if a similar query already
        exists for the same agent, the existing row's ``occurrence_count``
        is incremented instead of inserting a new row.

        Args:
            agent_id: The agent that received the unmatched query.
            user_query: The raw query text.
            matched_skills: Partial-match skill names (may be empty).
            confidence_score: Best match confidence (0.0 -- 1.0).
        """
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

            # Check for an existing gap with the same query text + agent
            existing = await execute_async(
                self._client.table(self._gaps_table)
                .select("id, occurrence_count")
                .eq("agent_id", agent_id)
                .eq("user_query", user_query)
                .gte("created_at", cutoff)
                .limit(1),
                op_name="interaction_logger.log_coverage_gap.check",
            )

            if existing.data:
                # Increment existing row
                row = existing.data[0]
                new_count = (row.get("occurrence_count") or 1) + 1
                await execute_async(
                    self._client.table(self._gaps_table)
                    .update(
                        {
                            "occurrence_count": new_count,
                            "confidence_score": confidence_score,
                            "matched_skills": matched_skills,
                        }
                    )
                    .eq("id", row["id"]),
                    op_name="interaction_logger.log_coverage_gap.increment",
                )
            else:
                # Insert new row
                data: dict[str, Any] = {
                    "agent_id": agent_id,
                    "user_query": user_query,
                    "matched_skills": matched_skills,
                    "confidence_score": confidence_score,
                    "occurrence_count": 1,
                    "user_id": get_current_user_id(),
                }
                await execute_async(
                    self._client.table(self._gaps_table).insert(data),
                    op_name="interaction_logger.log_coverage_gap.insert",
                )
        except Exception:
            logger.warning(
                "Failed to log coverage gap for agent=%s query=%s",
                agent_id,
                user_query[:80],
                exc_info=True,
            )

    # ==========================
    # Query / Analysis
    # ==========================

    async def get_recent_interactions(
        self,
        *,
        agent_id: str | None = None,
        skill_name: str | None = None,
        feedback: str | None = None,
        limit: int = 100,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Query recent interactions for analysis.

        Args:
            agent_id: Filter by agent (e.g. "FIN"). None returns all.
            skill_name: Filter by skill name. None returns all.
            feedback: Filter by feedback type ('positive'/'negative'/'neutral').
            limit: Maximum rows to return.
            days: Look-back period in days.

        Returns:
            List of interaction_logs rows, newest first.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        query = (
            self._client.table(self._interactions_table)
            .select("*")
            .gte("created_at", cutoff)
        )

        if agent_id:
            query = query.eq("agent_id", agent_id)
        if skill_name:
            query = query.eq("skill_used", skill_name)
        if feedback:
            query = query.eq("user_feedback", feedback)

        response = await execute_async(
            query.order("created_at", desc=True).limit(limit),
            op_name="interaction_logger.get_recent_interactions",
        )
        return response.data

    async def get_interaction_stats(
        self,
        *,
        skill_name: str | None = None,
        agent_id: str | None = None,
        days: int = 7,
    ) -> dict[str, Any]:
        """Aggregate stats for the evaluation engine.

        Args:
            skill_name: Limit stats to a specific skill. None for all.
            agent_id: Limit stats to a specific agent. None for all.
            days: Look-back period in days.

        Returns:
            Dictionary with keys:
                total_interactions  -- int
                feedback_breakdown  -- {"positive": N, "negative": N, "neutral": N, "none": N}
                skill_usage_counts  -- {skill_name: count, ...}
                top_gaps            -- list of top coverage gaps
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        # ---- interactions ----
        interactions_query = (
            self._client.table(self._interactions_table)
            .select("skill_used, user_feedback")
            .gte("created_at", cutoff)
        )
        if skill_name:
            interactions_query = interactions_query.eq("skill_used", skill_name)
        if agent_id:
            interactions_query = interactions_query.eq("agent_id", agent_id)

        interactions_resp = await execute_async(
            interactions_query,
            op_name="interaction_logger.get_interaction_stats.interactions",
        )
        rows: list[dict[str, Any]] = interactions_resp.data or []

        # Compute feedback breakdown
        feedback_breakdown: dict[str, int] = {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "none": 0,
        }
        skill_usage_counts: dict[str, int] = {}

        for row in rows:
            fb = row.get("user_feedback")
            if fb in feedback_breakdown:
                feedback_breakdown[fb] += 1
            else:
                feedback_breakdown["none"] += 1

            skill = row.get("skill_used")
            if skill:
                skill_usage_counts[skill] = skill_usage_counts.get(skill, 0) + 1

        # ---- coverage gaps ----
        gaps_query = (
            self._client.table(self._gaps_table)
            .select("user_query, agent_id, confidence_score, occurrence_count")
            .gte("created_at", cutoff)
        )
        if agent_id:
            gaps_query = gaps_query.eq("agent_id", agent_id)

        gaps_resp = await execute_async(
            gaps_query.order("occurrence_count", desc=True).limit(20),
            op_name="interaction_logger.get_interaction_stats.gaps",
        )

        return {
            "total_interactions": len(rows),
            "feedback_breakdown": feedback_breakdown,
            "skill_usage_counts": skill_usage_counts,
            "top_gaps": gaps_resp.data or [],
        }


# Module-level singleton instance
interaction_logger = InteractionLogger()
