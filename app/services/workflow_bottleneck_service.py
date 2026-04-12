# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""WorkflowBottleneckService — Workflow execution bottleneck detection.

Queries workflow_steps and workflow_executions to aggregate per-step
duration statistics, flag bottlenecks (slow, failing, approval-blocked,
outlier), and generate plain-English actionable recommendations.

Usage::

    service = WorkflowBottleneckService()
    result = await service.analyze_bottlenecks(user_id="user-123", days=30)
    # or
    summary = await service.get_workflow_health_summary(user_id="user-123")

Module-level convenience::

    from app.services.workflow_bottleneck_service import analyze_bottlenecks
    result = await analyze_bottlenecks(user_id="user-123")
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.services.base_service import BaseService

logger = logging.getLogger(__name__)

# Thresholds for bottleneck detection
_SLOW_STEP_HOURS = 24.0  # avg duration above this is "slow"
_HIGH_FAILURE_RATE = 0.2  # failure_count / total above this is "high failure"
_APPROVAL_BLOCKED_HOURS = 48.0  # approval-wait avg above this is "approval blocked"
_APPROVAL_BLOCKED_RATE = 0.3  # fraction of approval-wait steps to trigger
_OUTLIER_HOURS = 7 * 24.0  # max duration above this (1 week) is an "outlier"


class WorkflowBottleneckService(BaseService):
    """Service for detecting and reporting workflow execution bottlenecks.

    Aggregates step-level timing data from workflow_steps joined to
    workflow_executions, then produces plain-English recommendations.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze_bottlenecks(
        self,
        user_id: str,
        days: int = 30,
    ) -> dict:
        """Analyze workflow execution data and surface bottlenecks.

        Queries workflow_steps joined with workflow_executions for the
        given user over the last ``days`` days. Aggregates step-level
        stats in Python (Supabase PostgREST does not support GROUP BY),
        flags bottlenecks, and generates recommendations.

        Args:
            user_id: Authenticated user identifier.
            days: Look-back window in days. Defaults to 30.

        Returns:
            dict with keys:
            - step_stats: list of per-step stat dicts
            - bottleneck_count: number of flagged bottleneck steps
            - recommendations: list of recommendation dicts
            - period_days: the days parameter used
        """
        steps, executions = await self._fetch_steps_and_executions(user_id, days)

        if not executions:
            return {
                "step_stats": [],
                "bottleneck_count": 0,
                "recommendations": [],
                "period_days": days,
            }

        step_stats = self._aggregate_step_stats(steps)
        recommendations = self._generate_recommendations(step_stats)
        bottleneck_count = sum(1 for s in step_stats if s["is_bottleneck"])

        return {
            "step_stats": step_stats,
            "bottleneck_count": bottleneck_count,
            "recommendations": recommendations,
            "period_days": days,
        }

    async def get_workflow_health_summary(
        self,
        user_id: str,
        days: int = 30,
    ) -> dict:
        """Return an overall workflow health summary for the user.

        Computes completion rate, average execution time, and the top
        three bottleneck recommendations.

        Args:
            user_id: Authenticated user identifier.
            days: Look-back window in days. Defaults to 30.

        Returns:
            dict with keys:
            - total_executions: total number of workflow executions
            - completed_count: number with status "completed"
            - failed_count: number with status "failed"
            - completion_rate: completed / total (0.0 if total == 0)
            - avg_execution_hours: mean wall-clock hours for completed
            - top_bottlenecks: up to 3 top recommendation dicts
            - period_days: the days parameter used
        """
        steps, executions = await self._fetch_steps_and_executions(user_id, days)

        total = len(executions)
        if total == 0:
            return {
                "total_executions": 0,
                "completed_count": 0,
                "failed_count": 0,
                "completion_rate": 0.0,
                "avg_execution_hours": 0.0,
                "top_bottlenecks": [],
                "period_days": days,
            }

        completed = [e for e in executions if e.get("status") == "completed"]
        failed = [e for e in executions if e.get("status") == "failed"]
        completion_rate = len(completed) / total

        # Compute average wall-clock duration for completed executions
        exec_durations: list[float] = []
        for exc in completed:
            created_at = self._parse_dt(exc.get("created_at"))
            completed_at = self._parse_dt(exc.get("completed_at"))
            if created_at and completed_at and completed_at > created_at:
                exec_durations.append(
                    (completed_at - created_at).total_seconds() / 3600
                )
        avg_execution_hours = (
            sum(exec_durations) / len(exec_durations) if exec_durations else 0.0
        )

        # Bottleneck analysis
        step_stats = self._aggregate_step_stats(steps)
        recommendations = self._generate_recommendations(step_stats)
        top_bottlenecks = recommendations[:3]

        return {
            "total_executions": total,
            "completed_count": len(completed),
            "failed_count": len(failed),
            "completion_rate": completion_rate,
            "avg_execution_hours": avg_execution_hours,
            "top_bottlenecks": top_bottlenecks,
            "period_days": days,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_steps_and_executions(
        self,
        user_id: str,
        days: int,
    ) -> tuple[list[dict], list[dict]]:
        """Fetch workflow steps and executions for the user within the date window.

        Returns a (steps, executions) tuple. Both may be empty lists.
        """
        try:
            # Fetch executions scoped to user within date window
            from datetime import timedelta

            cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()

            exec_response = await self.execute(
                self.client.table("workflow_executions")
                .select("id, user_id, status, created_at, completed_at")
                .eq("user_id", user_id)
                .gte("created_at", cutoff),
                op_name="bottleneck.list_executions",
            )

            executions: list[dict] = exec_response.data if exec_response else []
            if not executions:
                return [], []

            execution_ids = [e["id"] for e in executions]

            # Fetch all steps for those executions
            steps_response = await self.execute(
                self.client.table("workflow_steps")
                .select("id, execution_id, step_name, status, started_at, completed_at")
                .in_("execution_id", execution_ids),
                op_name="bottleneck.list_steps",
            )

            steps: list[dict] = steps_response.data if steps_response else []
            return steps, executions

        except Exception:
            logger.exception("Error fetching workflow data for bottleneck analysis")
            return [], []

    def _aggregate_step_stats(self, steps: list[dict]) -> list[dict]:
        """Aggregate raw step rows into per-step-name statistics.

        Steps without both started_at and completed_at are excluded from
        duration calculations but are still counted for failure_rate.

        Args:
            steps: Raw rows from workflow_steps table.

        Returns:
            List of per-step-name stat dicts, sorted by avg_duration_hours
            descending so the worst offenders appear first.
        """
        # Group rows by step_name
        by_name: dict[str, list[dict]] = {}
        for step in steps:
            name = step.get("step_name") or "unknown"
            by_name.setdefault(name, []).append(step)

        stats: list[dict] = []
        for step_name, rows in by_name.items():
            total_count = len(rows)
            failure_count = sum(1 for r in rows if r.get("status") == "failed")
            approval_wait_count = sum(
                1 for r in rows if r.get("status") == "waiting_approval"
            )

            durations: list[float] = []
            for row in rows:
                started = self._parse_dt(row.get("started_at"))
                completed = self._parse_dt(row.get("completed_at"))
                if started and completed and completed > started:
                    durations.append((completed - started).total_seconds() / 3600)

            avg_duration = sum(durations) / len(durations) if durations else 0.0
            max_duration = max(durations) if durations else 0.0
            failure_rate = failure_count / total_count if total_count else 0.0
            approval_wait_rate = (
                approval_wait_count / total_count if total_count else 0.0
            )

            # Determine bottleneck flags
            is_bottleneck = (
                avg_duration > _SLOW_STEP_HOURS
                or failure_rate > _HIGH_FAILURE_RATE
                or (
                    approval_wait_rate > _APPROVAL_BLOCKED_RATE
                    and avg_duration > _APPROVAL_BLOCKED_HOURS
                )
            )

            stats.append(
                {
                    "step_name": step_name,
                    "avg_duration_hours": avg_duration,
                    "max_duration_hours": max_duration,
                    "execution_count": total_count,
                    "failure_count": failure_count,
                    "failure_rate": failure_rate,
                    "approval_wait_count": approval_wait_count,
                    "approval_wait_rate": approval_wait_rate,
                    "is_bottleneck": is_bottleneck,
                }
            )

        # Sort by avg_duration_hours descending for natural ordering
        stats.sort(key=lambda s: s["avg_duration_hours"], reverse=True)
        return stats

    def _generate_recommendations(
        self,
        step_stats: list[dict],
    ) -> list[dict]:
        """Generate plain-English recommendations for bottleneck steps.

        Checks four independent thresholds per step and emits a
        recommendation for each triggered threshold. Results are sorted
        by severity (high first) then by avg_duration_hours descending.

        Args:
            step_stats: Output of _aggregate_step_stats().

        Returns:
            List of recommendation dicts with keys:
            step_name, type, severity, message, avg_duration_hours,
            metric_value.
        """
        recs: list[dict] = []

        for stat in step_stats:
            name = stat["step_name"]
            avg_h = stat["avg_duration_hours"]
            max_h = stat["max_duration_hours"]
            failure_rate = stat["failure_rate"]
            approval_wait_rate = stat["approval_wait_rate"]

            # --- Slow step (avg > 24h) ---
            if avg_h > _SLOW_STEP_HOURS:
                avg_days = avg_h / 24
                severity = "high" if avg_h > 48 else "medium"
                recs.append(
                    {
                        "step_name": name,
                        "type": "slow",
                        "severity": severity,
                        "message": (
                            f"**{name}** averages {avg_days:.1f} days"
                            " -- consider adding reminders or parallel tracks."
                        ),
                        "avg_duration_hours": avg_h,
                        "metric_value": avg_days,
                    }
                )

            # --- High failure rate (> 20%) ---
            if failure_rate > _HIGH_FAILURE_RATE:
                pct = failure_rate * 100
                severity = "high" if failure_rate > 0.4 else "medium"
                recs.append(
                    {
                        "step_name": name,
                        "type": "failing",
                        "severity": severity,
                        "message": (
                            f"**{name}** fails {pct:.0f}% of the time"
                            " -- review step configuration or add error handling."
                        ),
                        "avg_duration_hours": avg_h,
                        "metric_value": failure_rate,
                    }
                )

            # --- Approval-blocked (avg > 48h AND approval_wait_rate > 30%) ---
            if (
                approval_wait_rate > _APPROVAL_BLOCKED_RATE
                and avg_h > _APPROVAL_BLOCKED_HOURS
            ):
                avg_days = avg_h / 24
                severity = "high" if avg_h > 96 else "medium"
                recs.append(
                    {
                        "step_name": name,
                        "type": "approval_blocked",
                        "severity": severity,
                        "message": (
                            f"**{name}** waits for approval averaging {avg_days:.1f} days"
                            " -- consider auto-approval rules or escalation timers."
                        ),
                        "avg_duration_hours": avg_h,
                        "metric_value": avg_days,
                    }
                )

            # --- Outlier (max > 1 week) ---
            if max_h > _OUTLIER_HOURS:
                max_days = max_h / 24
                recs.append(
                    {
                        "step_name": name,
                        "type": "outlier",
                        "severity": "medium",
                        "message": (
                            f"**{name}** has taken up to {max_days:.0f} days"
                            " in one case -- investigate outliers."
                        ),
                        "avg_duration_hours": avg_h,
                        "metric_value": max_days,
                    }
                )

        # Sort: high severity first, then by avg_duration_hours descending
        recs.sort(
            key=lambda r: (
                0 if r["severity"] == "high" else 1,
                -r["avg_duration_hours"],
            )
        )
        return recs

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        """Parse an ISO-format datetime string to a timezone-aware datetime.

        Returns None if value is None or unparseable.

        Args:
            value: ISO datetime string (with or without timezone).

        Returns:
            Timezone-aware datetime, or None.
        """
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            return None


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


async def analyze_bottlenecks(user_id: str, days: int = 30) -> dict:
    """Analyze workflow bottlenecks for a user.

    Module-level convenience wrapper around WorkflowBottleneckService.

    Args:
        user_id: Authenticated user identifier.
        days: Look-back window in days. Defaults to 30.

    Returns:
        dict with step_stats, bottleneck_count, recommendations, period_days.
    """
    service = WorkflowBottleneckService()
    return await service.analyze_bottlenecks(user_id, days)


__all__ = [
    "WorkflowBottleneckService",
    "analyze_bottlenecks",
]
