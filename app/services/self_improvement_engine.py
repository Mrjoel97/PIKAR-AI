# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Self-Improvement Engine - Autoresearch-inspired autonomous skill improvement.

This engine periodically evaluates skill effectiveness from interaction data,
identifies underperformers and coverage gaps, and triggers autonomous
improvements (refinement, creation, or deprecation).  It mirrors the
autoresearch loop: evaluate -> identify -> execute -> validate.

Tables used:
    interaction_logs   - raw interaction data with feedback signals
    skill_scores       - computed effectiveness scores per skill per period
    improvement_actions - recommended / executed improvement actions
    coverage_gaps      - unresolved user-need gaps
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.self_improvement_settings import (
    get_self_improvement_settings,
    update_self_improvement_settings,
)
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async
from app.skills.custom_skills_service import CustomSkillsService
from app.skills.registry import skills_registry
from supabase import Client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SYSTEM_USER_ID = "system:self-improvement-engine"

# Effectiveness weight vector (must sum to 1.0)
_W_POSITIVE = 0.35
_W_COMPLETION = 0.30
_W_ESCALATION = 0.20
_W_RETRY = 0.15

# Thresholds
_UNDERPERFORMER_THRESHOLD = 0.4
_UNDERPERFORMER_MIN_USES = 5
_HIGH_PERFORMER_THRESHOLD = 0.8
_DECLINING_CONSECUTIVE_PERIODS = 2
_UNUSED_DAYS = 30


class SelfImprovementEngine:
    """Core autoresearch-inspired self-improvement engine for Pikar-AI.

    Instantiate freely -- each instance holds its own Supabase client
    but shares the global skills registry.

    Example::

        engine = SelfImprovementEngine()
        summary = await engine.run_improvement_cycle(days=7, auto_execute=False)
    """

    def __init__(self) -> None:
        self.client: Client = get_service_client()
        self.custom_skills_svc = CustomSkillsService()

    # ==================================================================
    # 1. evaluate_skills  --  the "val_bpb" equivalent
    # ==================================================================

    async def evaluate_skills(self, days: int = 7) -> list[dict[str, Any]]:
        """Score each skill's effectiveness over *days* from interaction data.

        Computes a weighted composite ``effectiveness_score`` and persists
        results into the ``skill_scores`` table.

        Returns:
            List of score dicts (one per skill that had interactions).
        """
        now = datetime.now(tz=timezone.utc)
        period_start = (now - timedelta(days=days)).isoformat()
        period_end = now.isoformat()

        # Previous period for trend comparison
        prev_start = (now - timedelta(days=days * 2)).isoformat()
        prev_end = period_start

        # ------ fetch current-period interactions ------
        current_logs = await self._fetch_interaction_logs(period_start, period_end)
        prev_logs = await self._fetch_interaction_logs(prev_start, prev_end)

        current_by_skill = self._group_by_skill(current_logs)
        prev_by_skill = self._group_by_skill(prev_logs)

        scores: list[dict[str, Any]] = []

        for skill_name, interactions in current_by_skill.items():
            metrics = self._compute_metrics(interactions)
            effectiveness = (
                _W_POSITIVE * metrics["positive_rate"]
                + _W_COMPLETION * metrics["completion_rate"]
                + _W_ESCALATION * (1.0 - metrics["escalation_rate"])
                + _W_RETRY * (1.0 - metrics["retry_rate"])
            )

            # Compare with previous period
            prev_effectiveness: float | None = None
            if skill_name in prev_by_skill:
                pm = self._compute_metrics(prev_by_skill[skill_name])
                prev_effectiveness = (
                    _W_POSITIVE * pm["positive_rate"]
                    + _W_COMPLETION * pm["completion_rate"]
                    + _W_ESCALATION * (1.0 - pm["escalation_rate"])
                    + _W_RETRY * (1.0 - pm["retry_rate"])
                )

            score_delta = (
                round(effectiveness - prev_effectiveness, 4)
                if prev_effectiveness is not None
                else None
            )
            if score_delta is not None:
                if score_delta > 0.02:
                    trend = "improving"
                elif score_delta < -0.02:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "new"

            record = {
                "skill_name": skill_name,
                "period_start": period_start,
                "period_end": period_end,
                "total_uses": metrics["total"],
                "positive_rate": round(metrics["positive_rate"], 4),
                "completion_rate": round(metrics["completion_rate"], 4),
                "escalation_rate": round(metrics["escalation_rate"], 4),
                "retry_rate": round(metrics["retry_rate"], 4),
                "effectiveness_score": round(effectiveness, 4),
                "score_delta": score_delta,
                "trend": trend,
                "evaluated_at": now.isoformat(),
            }

            # Persist to DB
            try:
                await execute_async(
                    self.client.table("skill_scores").insert(record),
                    op_name="self_improvement.insert_score",
                )
            except Exception:
                logger.exception("Failed to insert skill score for %s", skill_name)

            scores.append(record)

        logger.info("Evaluated %d skills over %d-day period", len(scores), days)
        return scores

    # ==================================================================
    # 2. identify_improvements  --  find what to improve
    # ==================================================================

    async def identify_improvements(
        self,
        scores: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Analyze scores and gaps to generate improvement recommendations.

        Categories of recommendations:
        - ``skill_refined``  : underperforming skills (score < 0.4, uses > 5)
        - ``skill_created``  : unresolved coverage gaps
        - ``investigate``    : declining skills for 2+ consecutive periods
        - ``skill_demoted``  : unused skills (0 uses in 30 days)
        - ``pattern_extract``: high performers to learn from

        Returns:
            List of recommended action dicts.
        """
        if scores is None:
            scores = await self._fetch_latest_scores()

        actions: list[dict[str, Any]] = []

        scores_by_name: dict[str, dict] = {s["skill_name"]: s for s in scores}

        # --- Underperformers ---
        for s in scores:
            if (
                s["effectiveness_score"] < _UNDERPERFORMER_THRESHOLD
                and s["total_uses"] >= _UNDERPERFORMER_MIN_USES
            ):
                actions.append(
                    self._make_action(
                        skill_name=s["skill_name"],
                        action_type="skill_refined",
                        reason=(
                            f"Effectiveness {s['effectiveness_score']:.2f} below "
                            f"threshold {_UNDERPERFORMER_THRESHOLD} with "
                            f"{s['total_uses']} uses"
                        ),
                        priority="high",
                        metadata={"effectiveness_score": s["effectiveness_score"]},
                    )
                )

        # --- Coverage gaps ---
        try:
            gap_resp = await execute_async(
                self.client.table("coverage_gaps")
                .select("*")
                .eq("resolved", False)
                .order("created_at", desc=True)
                .limit(50),
                op_name="self_improvement.fetch_gaps",
            )
            gaps = gap_resp.data or []
        except Exception:
            logger.warning("Could not fetch coverage gaps", exc_info=True)
            gaps = []

        # Group similar gaps by category
        gap_groups: dict[str, list[dict]] = defaultdict(list)
        for g in gaps:
            gap_groups[g.get("category", "general")].append(g)

            # Emit research event for unresolved gap
            try:
                from app.services.research_event_bus import get_event_bus

                bus = get_event_bus()
                domain = self._agent_id_to_domain(g.get("agent_id", ""))
                await bus.emit(
                    topic=g.get("user_query", ""),
                    domain=domain,
                    trigger_type="coverage_gap",
                    suggested_depth="deep",
                    priority="high",
                    source_agent=g.get("agent_id"),
                    metadata={
                        "gap_id": str(g.get("id", "")),
                        "occurrence_count": g.get("occurrence_count", 1),
                    },
                )
            except Exception as e:
                logger.debug("Research event for gap failed (non-blocking): %s", e)

        for category, group in gap_groups.items():
            if len(group) >= 2:
                descriptions = [g.get("description", "") for g in group[:5]]
                actions.append(
                    self._make_action(
                        skill_name=None,
                        action_type="skill_created",
                        reason=(
                            f"{len(group)} unresolved coverage gaps in "
                            f"'{category}' category"
                        ),
                        priority="medium",
                        metadata={
                            "category": category,
                            "gap_descriptions": descriptions,
                            "gap_ids": [g["id"] for g in group],
                        },
                    )
                )

        # --- Declining skills (2+ consecutive periods) ---
        try:
            declining_resp = await execute_async(
                self.client.table("skill_scores")
                .select("skill_name, trend, evaluated_at")
                .eq("trend", "declining")
                .order("evaluated_at", desc=True)
                .limit(200),
                op_name="self_improvement.fetch_declining",
            )
            declining_rows = declining_resp.data or []
        except Exception:
            logger.warning("Could not fetch declining scores", exc_info=True)
            declining_rows = []

        decline_counts: dict[str, int] = defaultdict(int)
        for row in declining_rows:
            decline_counts[row["skill_name"]] += 1

        for skill_name, count in decline_counts.items():
            if count >= _DECLINING_CONSECUTIVE_PERIODS:
                actions.append(
                    self._make_action(
                        skill_name=skill_name,
                        action_type="investigate",
                        reason=(
                            f"Declining trend for {count} consecutive evaluation "
                            f"periods"
                        ),
                        priority="medium",
                        metadata={"consecutive_declines": count},
                    )
                )

        # --- Unused skills (0 uses in last 30 days) ---
        all_skill_names = set(skills_registry.list_names())
        used_skill_names = set(scores_by_name.keys())

        # Also check against a wider window to avoid false positives
        recently_used = await self._fetch_used_skill_names(days=_UNUSED_DAYS)
        unused = all_skill_names - used_skill_names - recently_used

        for skill_name in unused:
            actions.append(
                self._make_action(
                    skill_name=skill_name,
                    action_type="skill_demoted",
                    reason=f"No uses in the last {_UNUSED_DAYS} days",
                    priority="low",
                    metadata={},
                )
            )

        # --- High performers (extract patterns) ---
        for s in scores:
            if s["effectiveness_score"] >= _HIGH_PERFORMER_THRESHOLD:
                actions.append(
                    self._make_action(
                        skill_name=s["skill_name"],
                        action_type="pattern_extract",
                        reason=(
                            f"High effectiveness {s['effectiveness_score']:.2f} - "
                            f"extract patterns for other skills"
                        ),
                        priority="low",
                        metadata={"effectiveness_score": s["effectiveness_score"]},
                    )
                )

        # Persist all actions
        for action in actions:
            try:
                await execute_async(
                    self.client.table("improvement_actions").insert(action),
                    op_name="self_improvement.insert_action",
                )
            except Exception:
                logger.exception(
                    "Failed to insert improvement action: %s", action.get("action_type")
                )

        logger.info("Identified %d improvement actions", len(actions))
        return actions

    # ==================================================================
    # 3. execute_improvement  --  the autonomous iteration
    # ==================================================================

    async def execute_improvement(
        self,
        action: dict[str, Any],
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute a single improvement action.

        Dispatches by ``action_type``:
        - ``skill_created``  : generate new skill via Gemini + CustomSkillsService
        - ``skill_refined``  : rewrite skill knowledge via Gemini
        - ``skill_demoted``  : deactivate an underperforming skill
        - ``gap_identified`` : log for human review
        - others             : mark as applied (no-op)

        Args:
            action: The improvement action dict to execute.
            actor_id: Identity of who triggered execution.  Defaults to
                ``_SYSTEM_USER_ID`` for auto-executed actions.  Admin-approved
                actions pass the admin's user_id.

        Returns:
            Updated action dict with execution results.
        """
        effective_actor = actor_id or _SYSTEM_USER_ID
        action_type = action.get("action_type", "")
        action_id = action.get("id")
        result: dict[str, Any] = {"action_id": action_id, "action_type": action_type}

        try:
            if action_type == "skill_created":
                result = await self._execute_skill_created(action)
            elif action_type == "skill_refined":
                result = await self._execute_skill_refined(action)
            elif action_type == "skill_demoted":
                result = await self._execute_skill_demoted(action)
            elif action_type == "gap_identified":
                result = await self._execute_gap_identified(action)
            else:
                result["detail"] = f"No handler for action_type={action_type}"

            result["status"] = "applied"
        except Exception:
            logger.exception("Failed to execute improvement action %s", action_id)
            result["status"] = "failed"
            result["error"] = "Execution failed; see logs."

        # Update action record in DB
        if action_id:
            try:
                await execute_async(
                    self.client.table("improvement_actions")
                    .update(
                        {
                            "status": result["status"],
                            "executed_at": datetime.now(tz=timezone.utc).isoformat(),
                            "result_metadata": result,
                        }
                    )
                    .eq("id", action_id),
                    op_name="self_improvement.update_action",
                )
            except Exception:
                logger.exception("Failed to update action record %s", action_id)

        # Governance audit logging (fire-and-forget, never raises)
        if result.get("status") == "applied":
            try:
                from app.services.governance_service import get_governance_service

                gov = get_governance_service()
                await gov.log_event(
                    user_id=effective_actor,
                    action_type="self_improvement_action_executed",
                    resource_type="improvement_action",
                    resource_id=str(action_id) if action_id else None,
                    details={
                        "action_type": action_type,
                        "skill_name": action.get("skill_name"),
                        "trigger_reason": action.get("trigger_reason") or action.get("reason"),
                        "effectiveness_before": action.get("effectiveness_before"),
                        "effectiveness_after": None,
                    },
                )
            except Exception:
                logger.warning(
                    "Failed to write governance audit for action %s (non-fatal)",
                    action_id,
                    exc_info=True,
                )

        return result

    # ==================================================================
    # 4. run_improvement_cycle  --  full autoresearch loop
    # ==================================================================

    async def run_improvement_cycle(
        self,
        *,
        auto_execute: bool = False,
        evaluation_period: str = "daily",
        days: int = 7,
    ) -> dict[str, Any]:
        """Orchestrate a full evaluate -> identify -> execute cycle.

        When ``auto_execute`` is True, the engine reads admin settings from
        :func:`get_self_improvement_settings` to determine risk-tiered
        execution behavior:

        - If ``auto_execute_enabled`` is True **and** the action's
          ``action_type`` is in ``auto_execute_risk_tiers``: execute
          immediately.
        - If ``auto_execute_enabled`` is True **and** the action's
          ``action_type`` is **not** in ``auto_execute_risk_tiers``: set
          status to ``pending_approval`` (do NOT execute).
        - If ``auto_execute_enabled`` is False: set **all** actions to
          ``pending_approval`` (do NOT execute any).

        Args:
            auto_execute: If True, consult admin settings for risk-tiered
                execution.  If False, just evaluate and recommend.
            evaluation_period: Label for the period (informational).
            days: Number of days to evaluate over.

        Returns:
            Summary dict with ``scores_computed``, ``improvements_found``,
            ``improvements_executed``, and ``improvements_pending_approval``
            counts.
        """
        cycle_start = time.perf_counter()
        self._total_gemini_latency_ms = 0.0

        logger.info(
            "Starting improvement cycle: period=%s, days=%d, auto_execute=%s",
            evaluation_period,
            days,
            auto_execute,
        )

        # Step 1: Evaluate
        scores = await self.evaluate_skills(days=days)

        # Step 2: Identify
        improvements = await self.identify_improvements(scores=scores)

        # Step 3: Risk-tiered execution
        executed_count = 0
        pending_approval_count = 0

        if auto_execute:
            # Read admin settings for risk-tier gating
            settings = await get_self_improvement_settings()
            auto_enabled = settings.get("auto_execute_enabled", False)
            risk_tiers = settings.get(
                "auto_execute_risk_tiers", ["skill_demoted", "pattern_extract"]
            )

            for action in improvements:
                action_type = action.get("action_type", "")
                action_id = action.get("id")

                if auto_enabled and action_type in risk_tiers:
                    # Low-risk: execute immediately
                    await self.execute_improvement(action)
                    executed_count += 1
                else:
                    # High-risk or auto_execute disabled: queue for approval
                    pending_approval_count += 1
                    if action_id:
                        try:
                            await execute_async(
                                self.client.table("improvement_actions")
                                .update({"status": "pending_approval"})
                                .eq("id", action_id),
                                op_name="self_improvement.set_pending_approval",
                            )
                        except Exception:
                            logger.exception(
                                "Failed to set pending_approval for action %s",
                                action_id,
                            )

        cycle_duration_ms = round((time.perf_counter() - cycle_start) * 1000, 2)

        summary = {
            "evaluation_period": evaluation_period,
            "days": days,
            "auto_execute": auto_execute,
            "scores_computed": len(scores),
            "improvements_found": len(improvements),
            "improvements_executed": executed_count,
            "improvements_pending_approval": pending_approval_count,
            "cycle_duration_ms": cycle_duration_ms,
            "gemini_call_latency_ms": round(self._total_gemini_latency_ms, 2),
            "actions_executed_total": executed_count,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

        logger.info(
            "self_improvement.cycle_complete cycle_duration_ms=%.2f gemini_call_latency_ms=%.2f "
            "actions_executed_total=%d actions_pending_approval=%d",
            cycle_duration_ms,
            self._total_gemini_latency_ms,
            executed_count,
            pending_approval_count,
        )

        # Step 4: Circuit breaker check (after evaluation and execution)
        try:
            await self._check_circuit_breaker()
        except Exception:
            logger.warning(
                "Circuit breaker check failed (non-fatal)", exc_info=True
            )

        return summary

    # ==================================================================
    # 4b. Circuit breaker  --  auto-disable on regression
    # ==================================================================

    async def _check_circuit_breaker(self) -> None:
        """Check for consecutive effectiveness regressions and disable auto_execute.

        Queries the two most recent ``skill_scores`` evaluation snapshots,
        computes average effectiveness per snapshot, and compares them.  If the
        current snapshot is >5% lower than the previous, it counts as a
        regression.

        A ``circuit_breaker_consecutive_regressions`` counter in
        ``self_improvement_settings`` tracks consecutive regression cycles.
        After 2 consecutive regressions the circuit breaker trips:

        - ``auto_execute_enabled`` is set to ``False``.
        - A WARNING log is emitted.
        - A ``governance_audit_log`` entry is written.

        Non-regression cycles reset the counter to 0.
        """
        # Fetch the two most recent evaluation snapshots
        try:
            resp = await execute_async(
                self.client.table("skill_scores")
                .select("skill_name, effectiveness_score, evaluated_at")
                .order("evaluated_at", desc=True)
                .limit(500),
                op_name="self_improvement.circuit_breaker_scores",
            )
            rows = resp.data or []
        except Exception:
            logger.warning("Circuit breaker: could not fetch scores", exc_info=True)
            return

        if not rows:
            return

        # Group scores by evaluated_at to identify distinct snapshots
        snapshots: dict[str, list[float]] = {}
        for row in rows:
            ts = row.get("evaluated_at", "")
            score = row.get("effectiveness_score", 0.0)
            snapshots.setdefault(ts, []).append(score)

        # Sort snapshot timestamps newest-first
        sorted_timestamps = sorted(snapshots.keys(), reverse=True)
        if len(sorted_timestamps) < 2:
            return  # Not enough snapshots to compare

        current_ts = sorted_timestamps[0]
        previous_ts = sorted_timestamps[1]

        current_scores = snapshots[current_ts]
        previous_scores = snapshots[previous_ts]

        current_avg = sum(current_scores) / len(current_scores)
        previous_avg = sum(previous_scores) / len(previous_scores)

        # Read current regression counter from settings
        settings = await get_self_improvement_settings()
        consecutive = settings.get("circuit_breaker_consecutive_regressions", 0)
        if not isinstance(consecutive, int):
            try:
                consecutive = int(consecutive)
            except (ValueError, TypeError):
                consecutive = 0

        delta = previous_avg - current_avg
        is_significant_regression = delta > 0.05  # >5%

        if is_significant_regression:
            consecutive += 1
        else:
            consecutive = 0

        # Persist the updated counter
        await update_self_improvement_settings(
            key="circuit_breaker_consecutive_regressions",
            value=consecutive,
            updated_by="system:circuit-breaker",
        )

        if consecutive >= 2:
            # Trip the circuit breaker
            logger.warning(
                "Circuit breaker tripped: auto_execute disabled after %d "
                "consecutive regressions (delta=%.4f)",
                consecutive,
                delta,
            )

            await update_self_improvement_settings(
                key="auto_execute_enabled",
                value=False,
                updated_by="system:circuit-breaker",
            )

            # Governance audit log
            try:
                from app.services.governance_service import get_governance_service

                gov = get_governance_service()
                await gov.log_event(
                    user_id="system:circuit-breaker",
                    action_type="self_improvement_circuit_breaker",
                    resource_type="self_improvement_settings",
                    details={
                        "consecutive_regressions": consecutive,
                        "current_avg_effectiveness": round(current_avg, 4),
                        "previous_avg_effectiveness": round(previous_avg, 4),
                        "regression_delta": round(delta, 4),
                        "action": "auto_execute_disabled",
                    },
                )
            except Exception:
                logger.warning(
                    "Failed to write circuit breaker audit log (non-fatal)",
                    exc_info=True,
                )

    # ==================================================================
    # 5. validate_improvement  --  the keep/discard check
    # ==================================================================

    async def validate_improvement(self, action_id: str) -> dict[str, Any]:
        """Validate whether an applied improvement actually helped.

        Compares the skill's effectiveness_score before and after the
        improvement. If the score regressed, the action is reverted where
        possible.

        Returns:
            Validation result dict.
        """
        # Fetch the action record
        try:
            action_resp = await execute_async(
                self.client.table("improvement_actions")
                .select("*")
                .eq("id", action_id)
                .single(),
                op_name="self_improvement.fetch_action",
            )
            action = action_resp.data
        except Exception:
            logger.exception("Could not fetch action %s for validation", action_id)
            return {
                "action_id": action_id,
                "status": "error",
                "detail": "Action not found",
            }

        if not action:
            return {
                "action_id": action_id,
                "status": "error",
                "detail": "Action not found",
            }

        skill_name = action.get("skill_name")
        if not skill_name:
            # Non-skill actions (e.g. gap_identified) -- just mark validated
            await self._update_action_status(action_id, "validated")
            return {
                "action_id": action_id,
                "status": "validated",
                "detail": "No skill to validate",
            }

        executed_at = action.get("executed_at")
        if not executed_at:
            return {
                "action_id": action_id,
                "status": "error",
                "detail": "Action was never executed",
            }

        # Get effectiveness *before* (most recent score before execution)
        effectiveness_before = await self._get_effectiveness_before(
            skill_name, executed_at
        )
        # Get effectiveness *after* (most recent score after execution)
        effectiveness_after = await self._get_effectiveness_after(
            skill_name, executed_at
        )

        result: dict[str, Any] = {
            "action_id": action_id,
            "skill_name": skill_name,
            "effectiveness_before": effectiveness_before,
            "effectiveness_after": effectiveness_after,
        }

        if effectiveness_after is None:
            # Not enough post-execution data yet
            result["status"] = "pending"
            result["detail"] = "Insufficient post-execution data for validation"
            return result

        improved = effectiveness_after >= (effectiveness_before or 0.0)

        if improved:
            result["status"] = "validated"
            result["detail"] = (
                f"Score improved from {effectiveness_before} to {effectiveness_after}"
            )
            await self._update_action_status(action_id, "validated")
        else:
            result["status"] = "reverted"
            result["detail"] = (
                f"Score regressed from {effectiveness_before} to {effectiveness_after}"
            )
            # Attempt to undo the change
            await self._attempt_revert(action)
            await self._update_action_status(action_id, "reverted")

        # Persist before/after scores on the action record
        try:
            await execute_async(
                self.client.table("improvement_actions")
                .update(
                    {
                        "effectiveness_before": effectiveness_before,
                        "effectiveness_after": effectiveness_after,
                        "status": result["status"],
                        "validated_at": datetime.now(tz=timezone.utc).isoformat(),
                    }
                )
                .eq("id", action_id),
                op_name="self_improvement.update_validation",
            )
        except Exception:
            logger.exception("Failed to persist validation result for %s", action_id)

        logger.info(
            "Validation for action %s: %s (%.4f -> %s)",
            action_id,
            result["status"],
            effectiveness_before or 0.0,
            effectiveness_after,
        )
        return result

    # ==================================================================
    # Private helpers  --  data fetching
    # ==================================================================

    async def _fetch_interaction_logs(
        self, period_start: str, period_end: str
    ) -> list[dict]:
        """Fetch interaction_logs within the given ISO-8601 time window."""
        try:
            resp = await execute_async(
                self.client.table("interaction_logs")
                .select("*")
                .gte("created_at", period_start)
                .lte("created_at", period_end)
                .order("created_at", desc=False)
                .limit(5000),
                op_name="self_improvement.fetch_logs",
            )
            return resp.data or []
        except Exception:
            logger.exception("Failed to fetch interaction logs")
            return []

    async def _fetch_latest_scores(self) -> list[dict]:
        """Return the most recent skill_scores (last evaluation)."""
        try:
            resp = await execute_async(
                self.client.table("skill_scores")
                .select("*")
                .order("evaluated_at", desc=True)
                .limit(500),
                op_name="self_improvement.fetch_scores",
            )
            rows = resp.data or []
            # Deduplicate: keep only the latest record per skill
            seen: dict[str, dict] = {}
            for r in rows:
                name = r["skill_name"]
                if name not in seen:
                    seen[name] = r
            return list(seen.values())
        except Exception:
            logger.exception("Failed to fetch latest scores")
            return []

    async def _fetch_used_skill_names(self, days: int) -> set[str]:
        """Return set of skill names that appeared in interaction_logs recently."""
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
        try:
            resp = await execute_async(
                self.client.table("interaction_logs")
                .select("skill_name")
                .gte("created_at", cutoff)
                .limit(5000),
                op_name="self_improvement.fetch_used_skills",
            )
            return {r["skill_name"] for r in (resp.data or []) if r.get("skill_name")}
        except Exception:
            logger.exception("Failed to fetch used skill names")
            return set()

    async def _get_effectiveness_before(
        self, skill_name: str, executed_at: str
    ) -> float | None:
        """Get the most recent effectiveness_score before a given timestamp."""
        try:
            resp = await execute_async(
                self.client.table("skill_scores")
                .select("effectiveness_score")
                .eq("skill_name", skill_name)
                .lt("evaluated_at", executed_at)
                .order("evaluated_at", desc=True)
                .limit(1),
                op_name="self_improvement.score_before",
            )
            if resp.data:
                return resp.data[0]["effectiveness_score"]
        except Exception:
            logger.warning("Could not fetch pre-execution score for %s", skill_name)
        return None

    async def _get_effectiveness_after(
        self, skill_name: str, executed_at: str
    ) -> float | None:
        """Get the most recent effectiveness_score after a given timestamp."""
        try:
            resp = await execute_async(
                self.client.table("skill_scores")
                .select("effectiveness_score")
                .eq("skill_name", skill_name)
                .gt("evaluated_at", executed_at)
                .order("evaluated_at", desc=True)
                .limit(1),
                op_name="self_improvement.score_after",
            )
            if resp.data:
                return resp.data[0]["effectiveness_score"]
        except Exception:
            logger.warning("Could not fetch post-execution score for %s", skill_name)
        return None

    # ------------------------------------------------------------------
    # Private helpers  --  metrics computation
    # ------------------------------------------------------------------

    @staticmethod
    def _group_by_skill(logs: list[dict]) -> dict[str, list[dict]]:
        """Group interaction log rows by ``skill_name``."""
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in logs:
            skill_name = row.get("skill_name")
            if skill_name:
                grouped[skill_name].append(row)
        return grouped

    @staticmethod
    def _compute_metrics(interactions: list[dict]) -> dict[str, float]:
        """Compute rate metrics from a list of interactions for one skill."""
        total = len(interactions)
        if total == 0:
            return {
                "total": 0,
                "positive_rate": 0.0,
                "completion_rate": 0.0,
                "escalation_rate": 0.0,
                "retry_rate": 0.0,
            }

        feedback_count = sum(1 for i in interactions if i.get("feedback") is not None)
        positive_count = sum(1 for i in interactions if i.get("feedback") == "positive")
        completed_count = sum(
            1 for i in interactions if i.get("task_completed") is True
        )
        escalated_count = sum(1 for i in interactions if i.get("was_escalated") is True)
        followup_count = sum(1 for i in interactions if i.get("had_followup") is True)

        positive_rate = positive_count / feedback_count if feedback_count > 0 else 0.5
        completion_rate = completed_count / total
        escalation_rate = escalated_count / total
        retry_rate = followup_count / total

        return {
            "total": total,
            "positive_rate": positive_rate,
            "completion_rate": completion_rate,
            "escalation_rate": escalation_rate,
            "retry_rate": retry_rate,
        }

    # ------------------------------------------------------------------
    # Private helpers  --  action factory
    # ------------------------------------------------------------------

    @staticmethod
    def _make_action(
        *,
        skill_name: str | None,
        action_type: str,
        reason: str,
        priority: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Build an improvement_actions record dict."""
        return {
            "skill_name": skill_name,
            "action_type": action_type,
            "reason": reason,
            "priority": priority,
            "status": "pending",
            "metadata": metadata,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Private helpers  --  execution handlers
    # ------------------------------------------------------------------

    async def _execute_skill_created(self, action: dict) -> dict[str, Any]:
        """Generate and create a new skill from coverage gap patterns."""
        meta = action.get("metadata", {})
        category = meta.get("category", "general")
        gap_descriptions = meta.get("gap_descriptions", [])

        prompt = (
            "You are an AI skill designer for a multi-agent business system. "
            "Users have reported the following unresolved needs:\n\n"
            + "\n".join(f"- {d}" for d in gap_descriptions)
            + "\n\n"
            f"Category: {category}\n\n"
            "Design a new skill to address these gaps. Respond with EXACTLY "
            "this format (no markdown fences):\n"
            "NAME: <short skill name using snake_case>\n"
            "DESCRIPTION: <one-sentence description>\n"
            "KNOWLEDGE: <detailed knowledge/instructions the agent should "
            "follow when using this skill, 3-5 paragraphs>\n"
        )

        generated = await self._generate_with_gemini(prompt)
        if not generated:
            return {
                "action_id": action.get("id"),
                "action_type": "skill_created",
                "detail": "Gemini unavailable; skipped skill creation.",
            }

        parsed = self._parse_skill_generation(generated)
        if not parsed:
            return {
                "action_id": action.get("id"),
                "action_type": "skill_created",
                "detail": "Could not parse Gemini response.",
                "raw_response": generated[:500],
            }

        # Create the skill via CustomSkillsService
        try:
            skill_record = await self.custom_skills_svc.create_custom_skill(
                user_id=_SYSTEM_USER_ID,
                name=parsed["name"],
                description=parsed["description"],
                category=category,
                agent_ids=[],  # Available to all agents
                knowledge=parsed["knowledge"],
                metadata={
                    "created_by": "self_improvement_engine",
                    "source_gaps": meta.get("gap_ids", []),
                },
            )

            # Mark related coverage gaps as resolved
            for gap_id in meta.get("gap_ids", []):
                try:
                    await execute_async(
                        self.client.table("coverage_gaps")
                        .update({"resolved": True, "resolved_by": parsed["name"]})
                        .eq("id", gap_id),
                        op_name="self_improvement.resolve_gap",
                    )
                except Exception:
                    logger.warning("Could not resolve gap %s", gap_id)

            return {
                "action_id": action.get("id"),
                "action_type": "skill_created",
                "skill_name": parsed["name"],
                "skill_id": skill_record.get("id"),
                "detail": f"Created new skill: {parsed['name']}",
            }
        except Exception:
            logger.exception("Failed to create skill from gap")
            raise

    async def _execute_skill_refined(self, action: dict) -> dict[str, Any]:
        """Refine an existing skill's knowledge using Gemini.

        Persists the new version to ``skill_versions`` with ``is_active=True``
        while deactivating the previous active row, then updates the in-memory
        registry.  DB failures are caught so the in-memory update still happens
        as a best-effort fallback.
        """
        skill_name = action.get("skill_name", "")
        skill = skills_registry.get(skill_name)

        if not skill:
            return {
                "action_id": action.get("id"),
                "action_type": "skill_refined",
                "detail": f"Skill '{skill_name}' not found in registry.",
            }

        # Fetch recent negative interactions for context
        neg_interactions = await self._fetch_negative_interactions(skill_name)
        negative_patterns = "\n".join(
            f"- {n.get('user_query', 'N/A')}: {n.get('feedback_comment', 'negative')}"
            for n in neg_interactions[:10]
        )

        prompt = (
            "You are refining an AI agent skill that is underperforming.\n\n"
            f"Skill name: {skill.name}\n"
            f"Description: {skill.description}\n"
            f"Category: {skill.category}\n\n"
            f"Current knowledge:\n{skill.knowledge or '(none)'}\n\n"
            f"Recent negative interaction patterns:\n{negative_patterns or '(none)'}\n\n"
            "Write improved, more detailed knowledge/instructions for this skill. "
            "Address the failure patterns above. Keep the same purpose but make "
            "the guidance more specific, actionable, and robust.\n\n"
            "Respond with ONLY the improved knowledge text (no headers or labels)."
        )

        improved_knowledge = await self._generate_with_gemini(prompt)
        if not improved_knowledge:
            return {
                "action_id": action.get("id"),
                "action_type": "skill_refined",
                "detail": "Gemini unavailable; skipped skill refinement.",
            }

        # Store previous knowledge for potential revert
        previous_knowledge = skill.knowledge

        # Bump version
        old_version = skill.version or "1.0.0"
        parts = old_version.split(".")
        try:
            parts[-1] = str(int(parts[-1]) + 1)
        except (ValueError, IndexError):
            parts = ["1", "0", "1"]
        new_version = ".".join(parts)

        # --- Persist to skill_versions (DB write-through) ---
        previous_version_id: str | None = None
        new_version_id: str | None = None
        try:
            # 1. Find current active version for this skill
            active_resp = await execute_async(
                self.client.table("skill_versions")
                .select("id, previous_version_id")
                .eq("skill_name", skill_name)
                .eq("is_active", True)
                .limit(1),
                op_name="self_improvement.refined_find_active",
            )
            if active_resp.data:
                previous_version_id = active_resp.data[0]["id"]

                # 2. Deactivate the previous active version
                await execute_async(
                    self.client.table("skill_versions")
                    .update({"is_active": False})
                    .eq("id", previous_version_id),
                    op_name="self_improvement.refined_deactivate",
                )

            # 3. Insert the new version
            insert_resp = await execute_async(
                self.client.table("skill_versions").insert(
                    {
                        "skill_name": skill_name,
                        "version": new_version,
                        "knowledge": improved_knowledge.strip(),
                        "previous_version_id": previous_version_id,
                        "source_action_id": action.get("id"),
                        "created_by": _SYSTEM_USER_ID,
                        "is_active": True,
                        "metadata": {
                            "effectiveness_before": action.get("metadata", {}).get(
                                "effectiveness_score"
                            ),
                        },
                    }
                ),
                op_name="self_improvement.refined_insert_version",
            )
            if insert_resp.data:
                new_version_id = insert_resp.data[0].get("id")
        except Exception:
            logger.warning(
                "Failed to persist skill version for '%s'; "
                "in-memory update will proceed as fallback",
                skill_name,
                exc_info=True,
            )

        # --- Update in-memory registry ---
        skill.knowledge = improved_knowledge.strip()
        skill.version = new_version
        skill.changelog = "Auto-refined by self-improvement engine"

        return {
            "action_id": action.get("id"),
            "action_type": "skill_refined",
            "skill_name": skill_name,
            "previous_knowledge_length": len(previous_knowledge or ""),
            "new_knowledge_length": len(improved_knowledge),
            "new_version": skill.version,
            "new_version_id": new_version_id,
            "detail": f"Refined skill '{skill_name}' to v{skill.version}",
        }

    async def _execute_skill_demoted(self, action: dict) -> dict[str, Any]:
        """Deactivate an underperforming or unused skill."""
        skill_name = action.get("skill_name", "")

        # Try to deactivate in custom_skills table if it exists there
        try:
            resp = await execute_async(
                self.client.table("custom_skills")
                .select("id, user_id")
                .eq("name", skill_name)
                .eq("is_active", True)
                .limit(1),
                op_name="self_improvement.find_custom_skill",
            )
            if resp.data:
                record = resp.data[0]
                await self.custom_skills_svc.deactivate_skill(
                    user_id=record["user_id"],
                    skill_id=record["id"],
                )
                return {
                    "action_id": action.get("id"),
                    "action_type": "skill_demoted",
                    "skill_name": skill_name,
                    "detail": f"Deactivated custom skill '{skill_name}'",
                }
        except Exception:
            logger.warning(
                "Could not deactivate custom skill %s; may be a built-in",
                skill_name,
            )

        # For built-in skills, we just log it -- built-ins need manual removal
        return {
            "action_id": action.get("id"),
            "action_type": "skill_demoted",
            "skill_name": skill_name,
            "detail": (
                f"Skill '{skill_name}' flagged for demotion. "
                "Built-in skills require manual review."
            ),
        }

    async def _execute_gap_identified(self, action: dict) -> dict[str, Any]:
        """Log a coverage gap for human review without auto-creating a skill."""
        return {
            "action_id": action.get("id"),
            "action_type": "gap_identified",
            "detail": ("Gap logged for human review: " + action.get("reason", "")),
        }

    # ------------------------------------------------------------------
    # Private helpers  --  Gemini integration
    # ------------------------------------------------------------------

    async def _generate_with_gemini(self, prompt: str) -> str | None:
        """Generate text using the async Gemini client.

        Uses ``client.aio.models.generate_content`` so the FastAPI event loop
        is never blocked.  Records per-call latency on
        ``self._last_gemini_latency_ms`` for telemetry aggregation.

        Returns None if the genai library is unavailable or the call fails.
        """
        try:
            import google.genai as genai

            client = genai.Client()
            start = time.perf_counter()
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._last_gemini_latency_ms = round(elapsed_ms, 2)
            self._total_gemini_latency_ms = (
                getattr(self, "_total_gemini_latency_ms", 0.0)
                + self._last_gemini_latency_ms
            )
            return response.text
        except ImportError:
            logger.info("google.genai not available; skipping AI-powered improvement")
            self._last_gemini_latency_ms = 0.0
            return None
        except Exception:
            logger.exception("Gemini generation failed")
            self._last_gemini_latency_ms = 0.0
            return None

    @staticmethod
    def _parse_skill_generation(text: str) -> dict[str, str] | None:
        """Parse the NAME/DESCRIPTION/KNOWLEDGE format from Gemini output."""
        result: dict[str, str] = {}
        lines = text.strip().splitlines()

        current_key: str | None = None
        current_lines: list[str] = []

        for line in lines:
            upper = line.strip().upper()
            matched_key: str | None = None
            for prefix in ("NAME:", "DESCRIPTION:", "KNOWLEDGE:"):
                if upper.startswith(prefix):
                    matched_key = prefix[:-1].lower()
                    break

            if matched_key:
                # Save previous key
                if current_key:
                    result[current_key] = "\n".join(current_lines).strip()
                current_key = matched_key
                # Extract content after the prefix
                colon_idx = line.index(":") + 1
                current_lines = [line[colon_idx:].strip()]
            elif current_key:
                current_lines.append(line)

        # Save last key
        if current_key:
            result[current_key] = "\n".join(current_lines).strip()

        if all(k in result for k in ("name", "description", "knowledge")):
            return result
        return None

    # ------------------------------------------------------------------
    # Private helpers  --  negative interaction fetch
    # ------------------------------------------------------------------

    async def _fetch_negative_interactions(
        self, skill_name: str, limit: int = 20
    ) -> list[dict]:
        """Fetch recent negative-feedback interactions for a skill."""
        try:
            resp = await execute_async(
                self.client.table("interaction_logs")
                .select("user_query, feedback, feedback_comment")
                .eq("skill_name", skill_name)
                .eq("feedback", "negative")
                .order("created_at", desc=True)
                .limit(limit),
                op_name="self_improvement.fetch_negative",
            )
            return resp.data or []
        except Exception:
            logger.warning("Could not fetch negative interactions for %s", skill_name)
            return []

    # ------------------------------------------------------------------
    # Private helpers  --  status updates & revert
    # ------------------------------------------------------------------

    async def _update_action_status(self, action_id: str, status: str) -> None:
        """Update the status field on an improvement_actions record."""
        try:
            await execute_async(
                self.client.table("improvement_actions")
                .update({"status": status})
                .eq("id", action_id),
                op_name="self_improvement.update_status",
            )
        except Exception:
            logger.exception(
                "Failed to update action status %s -> %s", action_id, status
            )

    async def _attempt_revert(self, action: dict) -> None:
        """Best-effort revert of an improvement action.

        For refined skills, reads the previous version from ``skill_versions``
        and restores it (both DB and in-memory).  For created skills, deactivates
        the custom skill.  DB failures are caught so the engine never crashes.
        """
        action_type = action.get("action_type", "")
        result_meta = action.get("result_metadata", {})

        if action_type == "skill_created":
            skill_id = result_meta.get("skill_id")
            if skill_id:
                try:
                    await self.custom_skills_svc.deactivate_skill(
                        user_id=_SYSTEM_USER_ID,
                        skill_id=skill_id,
                    )
                    logger.info("Reverted skill creation: deactivated %s", skill_id)
                except Exception:
                    logger.warning("Could not deactivate reverted skill %s", skill_id)
        elif action_type == "skill_refined":
            skill_name = action.get("skill_name", "")
            try:
                # 1. Find the current active version
                active_resp = await execute_async(
                    self.client.table("skill_versions")
                    .select("id, previous_version_id")
                    .eq("skill_name", skill_name)
                    .eq("is_active", True)
                    .limit(1),
                    op_name="self_improvement.revert_find_active",
                )

                if not active_resp.data:
                    logger.warning(
                        "No active skill_versions row for '%s'; cannot revert",
                        skill_name,
                    )
                    return

                current_row = active_resp.data[0]
                current_id = current_row["id"]
                previous_version_id = current_row.get("previous_version_id")

                if not previous_version_id:
                    logger.warning(
                        "Skill '%s' has no previous_version_id; cannot revert",
                        skill_name,
                    )
                    return

                # 2. Fetch the previous version row
                prev_resp = await execute_async(
                    self.client.table("skill_versions")
                    .select("*")
                    .eq("id", previous_version_id)
                    .single(),
                    op_name="self_improvement.revert_fetch_prev",
                )
                prev_data = prev_resp.data
                if not prev_data:
                    logger.warning(
                        "Previous version %s not found for skill '%s'",
                        previous_version_id,
                        skill_name,
                    )
                    return

                # 3. Deactivate the current active version
                await execute_async(
                    self.client.table("skill_versions")
                    .update({"is_active": False})
                    .eq("id", current_id),
                    op_name="self_improvement.revert_deactivate",
                )

                # 4. Activate the previous version
                await execute_async(
                    self.client.table("skill_versions")
                    .update({"is_active": True})
                    .eq("id", previous_version_id),
                    op_name="self_improvement.revert_activate",
                )

                # 5. Restore in-memory registry
                skill = skills_registry.get(skill_name)
                if skill:
                    old_version = skill.version
                    skill.knowledge = prev_data["knowledge"]
                    skill.version = prev_data["version"]
                    logger.info(
                        "Reverted skill '%s' from v%s to v%s",
                        skill_name,
                        old_version,
                        prev_data["version"],
                    )
                else:
                    logger.warning(
                        "Skill '%s' not in registry; DB reverted but "
                        "in-memory state unchanged",
                        skill_name,
                    )
            except Exception:
                logger.warning(
                    "Failed to revert skill refinement for '%s'",
                    skill_name,
                    exc_info=True,
                )
        else:
            logger.info("No revert logic for action_type=%s", action_type)

    def _agent_id_to_domain(self, agent_id: str) -> str:
        """Map agent_id back to domain name for research events."""
        mapping = {
            "FIN": "financial",
            "CON": "content",
            "STR": "strategic",
            "SAL": "sales",
            "MKT": "marketing",
            "OPS": "operations",
            "HR": "hr",
            "CMP": "compliance",
            "CUS": "customer_support",
            "DAT": "data",
            "EXEC": "strategic",
        }
        return mapping.get(agent_id, "strategic")


# ======================================================================
# Module-level convenience function
# ======================================================================


async def run_improvement_cycle(
    *,
    auto_execute: bool = False,
    evaluation_period: str = "daily",
    days: int = 7,
) -> dict[str, Any]:
    """Create a :class:`SelfImprovementEngine` and run a full cycle.

    This is the simplest entry-point for scheduled jobs or one-off runs::

        from app.services.self_improvement_engine import run_improvement_cycle
        summary = await run_improvement_cycle(days=7, auto_execute=True)
    """
    engine = SelfImprovementEngine()
    return await engine.run_improvement_cycle(
        auto_execute=auto_execute,
        evaluation_period=evaluation_period,
        days=days,
    )
