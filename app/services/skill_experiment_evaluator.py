# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Skill experiment evaluator — promotion/revert decisions for the A/B harness.

Runs at the end of the scheduled self-improvement cycle.  For each
``skill_experiments`` row in ``state='running'``:

1. Aggregates ``interaction_logs`` grouped by ``variant`` ('control' vs 'treatment').
2. Computes a per-interaction quality Bernoulli signal:
       quality = (task_completed AND user_feedback != 'negative')
                 OR (user_feedback = 'positive')
3. Runs a two-proportion z-test on the quality rate.
4. Decides:
    - PROMOTE when z > +1.96 AND (p_treatment - p_control) >= min_effect_size
    - REVERT when z < -1.96 (any significant regression — fast rollback on harm)
    - INCONCLUSIVE-REVERT when sample budget or max_duration_days exhausted
    - CONTINUE otherwise

Promote flips ``is_active`` on the candidate ``skill_versions`` row, marks the
experiment ``promoted``, writes an ``improvement_actions`` row with
``action_type='skill_promoted', status='validated'``, calls
``skills_registry.reload_skill_from_db()`` to refresh the in-memory skill, and
emits a governance audit event.

Revert and inconclusive-revert leave the control active and mark the candidate
``metadata.reverted=true``.  No autonomous changes ever happen without a
significant statistical signal in the data the evaluator just collected.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Mirrors _SYSTEM_USER_ID in self_improvement_engine.py — kept duplicated to
# avoid an import cycle.  The governance audit writer silently swallows the
# UUID parse failure that this non-UUID actor produces, matching the pattern
# already used by the engine.
_SYSTEM_USER_ID = "system:self-improvement-engine"

# Decision thresholds.  These are fallbacks — every experiment row carries its
# own min_samples_per_arm / max_samples_per_arm / max_duration_days / alpha /
# min_effect_size and those take precedence.
_DEFAULT_MIN_SAMPLES = 50
_DEFAULT_MAX_SAMPLES = 500
_DEFAULT_MAX_DURATION_DAYS = 14
_DEFAULT_ALPHA = 0.05
_DEFAULT_MIN_EFFECT_SIZE = 0.05

# Two-sided z critical value at alpha=0.05.  Hard-coded because experiments
# may set alpha but we never recompute the critical value without scipy.
_Z_CRIT_TWO_SIDED_05 = 1.96


class SkillExperimentEvaluator:
    """Evaluator that decides the fate of running skill experiments.

    Stateless apart from the Supabase client.  Safe to instantiate per call.
    """

    def __init__(self) -> None:
        self.client = get_service_client()

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def evaluate_running_experiments(self) -> dict[str, Any]:
        """Evaluate every running experiment and dispatch decisions.

        Returns a summary dict suitable for inclusion in the cron response.
        """
        try:
            resp = await execute_async(
                self.client.table("skill_experiments")
                .select(
                    "id, skill_name, control_version_id, candidate_version_id, "
                    "source_action_id, min_samples_per_arm, max_samples_per_arm, "
                    "max_duration_days, alpha, min_effect_size, started_at, metadata"
                )
                .eq("state", "running"),
                op_name="skill_experiment.fetch_running",
            )
            rows = resp.data or []
        except Exception:
            logger.exception("Failed to fetch running experiments")
            return {
                "experiments_evaluated": 0,
                "promoted": 0,
                "reverted": 0,
                "inconclusive": 0,
                "still_running": 0,
                "errors": 1,
            }

        promoted = 0
        reverted = 0
        inconclusive = 0
        still_running = 0
        decisions: list[dict[str, Any]] = []

        for exp in rows:
            try:
                decision = await self._evaluate_one(exp)
                decisions.append(decision)
                outcome = decision.get("outcome")
                if outcome == "promoted":
                    promoted += 1
                elif outcome == "reverted":
                    reverted += 1
                elif outcome == "inconclusive_reverted":
                    inconclusive += 1
                else:
                    still_running += 1
            except Exception:
                logger.exception(
                    "Failed evaluating experiment %s — leaving running",
                    exp.get("id"),
                )
                still_running += 1

        return {
            "experiments_evaluated": len(rows),
            "promoted": promoted,
            "reverted": reverted,
            "inconclusive": inconclusive,
            "still_running": still_running,
            "decisions": decisions,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Single experiment
    # ------------------------------------------------------------------

    async def _evaluate_one(self, exp: dict[str, Any]) -> dict[str, Any]:
        """Decide on a single running experiment."""
        exp_id = exp["id"]
        skill_name = exp["skill_name"]
        min_samples = int(exp.get("min_samples_per_arm") or _DEFAULT_MIN_SAMPLES)
        max_samples = int(exp.get("max_samples_per_arm") or _DEFAULT_MAX_SAMPLES)
        max_duration_days = int(
            exp.get("max_duration_days") or _DEFAULT_MAX_DURATION_DAYS
        )
        min_effect_size = float(
            exp.get("min_effect_size") or _DEFAULT_MIN_EFFECT_SIZE
        )

        # Collect per-arm aggregates.
        agg = await self._aggregate_arms(exp_id)
        n_c, q_c = agg["control"]
        n_t, q_t = agg["treatment"]

        decision_base = {
            "experiment_id": exp_id,
            "skill_name": skill_name,
            "n_control": n_c,
            "n_treatment": n_t,
            "p_control": _safe_rate(q_c, n_c),
            "p_treatment": _safe_rate(q_t, n_t),
        }

        # Deadline check (independent of sample count).
        duration_expired = _duration_expired(exp.get("started_at"), max_duration_days)

        # Continue if either arm hasn't reached the minimum sample size and
        # the deadline hasn't passed.
        if (n_c < min_samples or n_t < min_samples) and not duration_expired:
            decision_base["outcome"] = "running"
            decision_base["decision_reason"] = "below_min_samples"
            return decision_base

        # Stat test: two-proportion z-test on the quality rate.
        z = _two_proportion_z(q_c, n_c, q_t, n_t)
        decision_base["z"] = z

        if z is None:
            # Both arms empty or pooled p == 0: cannot test.  Treat as inconclusive
            # if duration expired, else keep waiting.
            if duration_expired:
                decision_base["decision_reason"] = "inconclusive_no_signal"
                return await self._apply_revert(exp, decision_base, inconclusive=True)
            decision_base["outcome"] = "running"
            decision_base["decision_reason"] = "no_signal_yet"
            return decision_base

        p_diff = decision_base["p_treatment"] - decision_base["p_control"]
        decision_base["p_diff"] = p_diff

        # Significant regression — revert regardless of effect size.
        if z < -_Z_CRIT_TWO_SIDED_05:
            decision_base["decision_reason"] = "significant_regression"
            return await self._apply_revert(exp, decision_base, inconclusive=False)

        # Significant lift AND meaningful effect size — promote.
        if z > _Z_CRIT_TWO_SIDED_05 and p_diff >= min_effect_size:
            decision_base["decision_reason"] = "significant_lift"
            return await self._apply_promote(exp, decision_base)

        # Sample budget exhausted or duration expired without a verdict —
        # inconclusive revert (do-no-harm bias).
        if (n_c >= max_samples and n_t >= max_samples) or duration_expired:
            decision_base["decision_reason"] = (
                "inconclusive_max_samples" if not duration_expired else "inconclusive_low_traffic"
            )
            return await self._apply_revert(exp, decision_base, inconclusive=True)

        # Otherwise, keep collecting.
        decision_base["outcome"] = "running"
        decision_base["decision_reason"] = "no_decision_yet"
        return decision_base

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    async def _aggregate_arms(self, exp_id: str) -> dict[str, tuple[int, int]]:
        """Return per-arm (n, quality) over the experiment's lifetime."""
        try:
            resp = await execute_async(
                self.client.table("interaction_logs")
                .select("variant, task_completed, user_feedback")
                .eq("experiment_id", exp_id)
                .not_.is_("variant", "null"),
                op_name="skill_experiment.aggregate_arms",
            )
            rows = resp.data or []
        except Exception:
            logger.warning(
                "Failed to aggregate interactions for experiment %s",
                exp_id,
                exc_info=True,
            )
            return {"control": (0, 0), "treatment": (0, 0)}

        n_c = n_t = 0
        q_c = q_t = 0
        for r in rows:
            variant = r.get("variant")
            quality = _interaction_quality(
                r.get("task_completed"), r.get("user_feedback")
            )
            if variant == "control":
                n_c += 1
                q_c += quality
            elif variant == "treatment":
                n_t += 1
                q_t += quality
        return {"control": (n_c, q_c), "treatment": (n_t, q_t)}

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------

    async def _apply_promote(
        self, exp: dict[str, Any], decision: dict[str, Any]
    ) -> dict[str, Any]:
        """Flip is_active to the candidate; mark experiment promoted; audit."""
        exp_id = exp["id"]
        skill_name = exp["skill_name"]
        control_id = exp["control_version_id"]
        candidate_id = exp["candidate_version_id"]
        p_control = decision["p_control"]
        p_treatment = decision["p_treatment"]

        # Atomicity: do candidate-active first (constraint allows brief overlap
        # because is_active=true on both would violate the unique partial
        # index — so we must deactivate the control before activating the
        # candidate).  If the deactivate succeeds but the activate fails the
        # skill is left with NO active version, which the registry handles
        # gracefully (falls back to None and the skill is treated as missing).
        try:
            await execute_async(
                self.client.table("skill_versions")
                .update({"is_active": False})
                .eq("id", control_id),
                op_name="skill_experiment.promote_deactivate_control",
            )
            await execute_async(
                self.client.table("skill_versions")
                .update({"is_active": True})
                .eq("id", candidate_id),
                op_name="skill_experiment.promote_activate_candidate",
            )
        except Exception:
            logger.exception(
                "Failed flipping is_active for experiment %s — leaving running",
                exp_id,
            )
            decision["outcome"] = "running"
            decision["decision_reason"] = "promote_db_error"
            return decision

        # Mark the experiment promoted.
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        try:
            await execute_async(
                self.client.table("skill_experiments")
                .update(
                    {
                        "state": "promoted",
                        "decided_at": now_iso,
                        "decision_reason": decision["decision_reason"],
                    }
                )
                .eq("id", exp_id),
                op_name="skill_experiment.promote_mark_state",
            )
        except Exception:
            logger.warning(
                "Failed marking experiment %s promoted (DB roll-forward inconsistent)",
                exp_id,
                exc_info=True,
            )

        # Insert a skill_promoted action with before/after.
        try:
            await execute_async(
                self.client.table("improvement_actions").insert(
                    {
                        "action_type": "skill_promoted",
                        "skill_name": skill_name,
                        "trigger_reason": (
                            f"A/B experiment {exp_id} significant lift "
                            f"(p_c={p_control:.3f}, p_t={p_treatment:.3f}, "
                            f"z={decision['z']:.2f})"
                        ),
                        "status": "validated",
                        "effectiveness_before": p_control,
                        "effectiveness_after": p_treatment,
                        "details": {
                            "experiment_id": exp_id,
                            "control_version_id": control_id,
                            "candidate_version_id": candidate_id,
                            "n_control": decision["n_control"],
                            "n_treatment": decision["n_treatment"],
                        },
                    }
                ),
                op_name="skill_experiment.promote_insert_action",
            )
        except Exception:
            logger.warning(
                "Failed inserting skill_promoted action for experiment %s",
                exp_id,
                exc_info=True,
            )

        # Mark the originating action validated.
        source_action_id = exp.get("source_action_id")
        if source_action_id:
            try:
                await execute_async(
                    self.client.table("improvement_actions")
                    .update(
                        {
                            "status": "validated",
                            "effectiveness_after": p_treatment,
                        }
                    )
                    .eq("id", source_action_id),
                    op_name="skill_experiment.promote_close_source_action",
                )
            except Exception:
                logger.warning(
                    "Failed closing source action %s for experiment %s",
                    source_action_id,
                    exp_id,
                    exc_info=True,
                )

        # Refresh the in-memory skill so subsequent requests serve the new
        # active version's knowledge.  Lazy import to avoid loading the
        # registry at module-import time.
        try:
            from app.skills.registry import skills_registry

            skills_registry.reload_skill_from_db(skill_name)
        except Exception:
            logger.warning(
                "reload_skill_from_db failed after promote for %s",
                skill_name,
                exc_info=True,
            )

        await self._audit(
            action_type="self_improvement.experiment_promoted",
            resource_id=exp_id,
            details={
                "skill_name": skill_name,
                "candidate_version_id": candidate_id,
                "control_version_id": control_id,
                **{k: v for k, v in decision.items() if k != "outcome"},
            },
        )

        decision["outcome"] = "promoted"
        return decision

    async def _apply_revert(
        self,
        exp: dict[str, Any],
        decision: dict[str, Any],
        *,
        inconclusive: bool,
    ) -> dict[str, Any]:
        """Mark experiment reverted; flag candidate row; audit."""
        exp_id = exp["id"]
        skill_name = exp["skill_name"]
        candidate_id = exp["candidate_version_id"]

        now_iso = datetime.now(tz=timezone.utc).isoformat()
        state_label = "reverted"  # Same state for both — distinguished by reason.

        try:
            await execute_async(
                self.client.table("skill_experiments")
                .update(
                    {
                        "state": state_label,
                        "decided_at": now_iso,
                        "decision_reason": decision["decision_reason"],
                    }
                )
                .eq("id", exp_id),
                op_name="skill_experiment.revert_mark_state",
            )
        except Exception:
            logger.warning(
                "Failed marking experiment %s reverted",
                exp_id,
                exc_info=True,
            )

        # Flag the candidate skill_versions row.  We don't change is_active —
        # it's already false (control was untouched).  This metadata flag
        # exists so dashboards can distinguish reverted candidates from
        # historical inactive versions.
        try:
            await execute_async(
                self.client.table("skill_versions")
                .update(
                    {
                        "metadata": {
                            "reverted": True,
                            "reverted_at": now_iso,
                            "reverted_reason": decision["decision_reason"],
                            "experiment_id": exp_id,
                        }
                    }
                )
                .eq("id", candidate_id),
                op_name="skill_experiment.revert_flag_candidate",
            )
        except Exception:
            logger.warning(
                "Failed flagging candidate version %s as reverted",
                candidate_id,
                exc_info=True,
            )

        # Close out the originating improvement_actions row.
        source_action_id = exp.get("source_action_id")
        if source_action_id:
            try:
                await execute_async(
                    self.client.table("improvement_actions")
                    .update(
                        {
                            "status": "reverted",
                            "effectiveness_after": decision.get("p_treatment"),
                            "result_metadata": {
                                "experiment_id": exp_id,
                                "decision_reason": decision["decision_reason"],
                                "inconclusive": inconclusive,
                            },
                        }
                    )
                    .eq("id", source_action_id),
                    op_name="skill_experiment.revert_close_source_action",
                )
            except Exception:
                logger.warning(
                    "Failed closing source action %s after revert",
                    source_action_id,
                    exc_info=True,
                )

        # Drop the in-memory experiment cache so the next call resolves to
        # active (control) without waiting for TTL.
        try:
            from app.skills.registry import skills_registry

            skills_registry._invalidate_experiment(skill_name)
        except Exception:
            logger.debug(
                "registry invalidation skipped for %s",
                skill_name,
                exc_info=True,
            )

        await self._audit(
            action_type=(
                "self_improvement.experiment_inconclusive_reverted"
                if inconclusive
                else "self_improvement.experiment_reverted"
            ),
            resource_id=exp_id,
            details={
                "skill_name": skill_name,
                "candidate_version_id": candidate_id,
                **{k: v for k, v in decision.items() if k != "outcome"},
            },
        )

        decision["outcome"] = (
            "inconclusive_reverted" if inconclusive else "reverted"
        )
        return decision

    # ------------------------------------------------------------------
    # Audit helper
    # ------------------------------------------------------------------

    async def _audit(
        self, *, action_type: str, resource_id: str, details: dict[str, Any]
    ) -> None:
        """Fire-and-forget governance audit write."""
        try:
            from app.services.governance_service import get_governance_service

            gov = get_governance_service()
            await gov.log_event(
                user_id=_SYSTEM_USER_ID,
                action_type=action_type,
                resource_type="skill_experiment",
                resource_id=resource_id,
                details=details,
            )
        except Exception:
            logger.debug(
                "audit write failed for %s (non-fatal)",
                action_type,
                exc_info=True,
            )


# =====================================================================
# Pure helpers (exposed for unit testing)
# =====================================================================


def _interaction_quality(task_completed: Any, user_feedback: Any) -> int:
    """Map a row to a 0/1 quality outcome.

    quality = 1 iff:
        (task_completed AND user_feedback != 'negative')
        OR user_feedback == 'positive'
    """
    fb = user_feedback if isinstance(user_feedback, str) else None
    if fb == "positive":
        return 1
    if task_completed is True and fb != "negative":
        return 1
    return 0


def _safe_rate(numerator: int, denominator: int) -> float:
    """Defensive division — returns 0.0 when denominator is 0."""
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _two_proportion_z(
    q_c: int, n_c: int, q_t: int, n_t: int
) -> float | None:
    """Compute the two-proportion z statistic.

    Returns None when the test cannot be performed (empty arm or zero
    pooled variance).  Sign convention: positive z means treatment > control.
    """
    if n_c <= 0 or n_t <= 0:
        return None
    p_c = q_c / n_c
    p_t = q_t / n_t
    pooled = (q_c + q_t) / (n_c + n_t)
    if pooled <= 0 or pooled >= 1:
        # No variance — every outcome is identical.
        return None
    se = math.sqrt(pooled * (1 - pooled) * (1 / n_c + 1 / n_t))
    if se == 0:
        return None
    return (p_t - p_c) / se


def _duration_expired(started_at: Any, max_duration_days: int) -> bool:
    """Whether the experiment started more than max_duration_days ago."""
    if not started_at:
        return False
    try:
        if isinstance(started_at, str):
            # Supabase returns ISO with optional 'Z' or '+00:00'.
            normalised = started_at.replace("Z", "+00:00")
            started = datetime.fromisoformat(normalised)
        else:
            started = started_at
    except (TypeError, ValueError):
        return False
    now = datetime.now(tz=timezone.utc)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = (now - started).total_seconds()
    return elapsed >= max_duration_days * 86400
