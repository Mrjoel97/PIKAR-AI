# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Workflow template effectiveness scoring — Pillar 2 of the eval harness.

Mirrors ``app/services/self_improvement_engine.py`` for workflow templates:
rolls up ``workflow_executions`` + ``workflow_steps`` telemetry over a window
into a per-version effectiveness score, computes a delta against the previous
window, and persists to ``workflow_template_scores``.

Weights (sum to 1.0):
    completion_rate     0.50  — primary success signal
    1 - error_rate      0.20  — explicit failures penalised
    1 - retry_rate      0.15  — steps re-attempted (attempt_count > 1)
    1 - escalation_rate 0.15  — SLA escalations

These weights intentionally differ from the skill formula in
``self_improvement_engine.py``: workflows have no user-feedback proxy in v1
(no thumbs-up surface yet), so the weight on "positive_rate" is absent and
re-distributed across completion + the negative-signal complements.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Composite weights (must sum to 1.0).
_W_COMPLETION = 0.50
_W_ERROR = 0.20
_W_RETRY = 0.15
_W_ESCALATION = 0.15

# Trend thresholds (mirror SelfImprovementEngine).
_TREND_EPSILON = 0.02


async def evaluate_workflow_templates(days: int = 7) -> dict[str, Any]:
    """Score every workflow template version over the last *days* days.

    Returns a summary suitable for inclusion in the scheduled-cron response.
    """
    client = get_service_client()
    now = datetime.now(tz=timezone.utc)
    period_start_dt = now - timedelta(days=days)
    period_start = period_start_dt.isoformat()
    period_end = now.isoformat()
    evaluation_period = f"{now.strftime('%Y-%m-%d')}_daily"

    try:
        exec_resp = await execute_async(
            client.table("workflow_executions")
            .select(
                "id, user_id, template_id, template_version_id, status, started_at"
            )
            .gte("started_at", period_start)
            .lte("started_at", period_end),
            op_name="workflow_template_scoring.fetch_executions",
        )
        executions = exec_resp.data or []
    except Exception:
        logger.exception("Failed fetching workflow_executions for scoring")
        return {
            "scored": 0,
            "errors": 1,
            "evaluation_period": evaluation_period,
        }

    if not executions:
        return {
            "scored": 0,
            "evaluation_period": evaluation_period,
            "detail": "no_executions_in_window",
        }

    # Fetch step telemetry for the in-window executions.
    execution_ids = [e["id"] for e in executions if e.get("id")]
    step_rows: list[dict[str, Any]] = []
    if execution_ids:
        try:
            step_resp = await execute_async(
                client.table("workflow_steps")
                .select("execution_id, attempt_count, sla_status")
                .in_("execution_id", execution_ids),
                op_name="workflow_template_scoring.fetch_steps",
            )
            step_rows = step_resp.data or []
        except Exception:
            logger.warning(
                "Failed fetching workflow_steps for scoring — retry/escalation "
                "rates will be 0 for this run",
                exc_info=True,
            )

    # Pre-index steps by execution to compute per-run retry / escalation.
    steps_by_exec: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in step_rows:
        exec_id = s.get("execution_id")
        if exec_id:
            steps_by_exec[exec_id].append(s)

    # Group executions by (template_id, template_version_id).
    groups: dict[tuple[str, str | None], list[dict[str, Any]]] = defaultdict(list)
    for e in executions:
        tpl_id = e.get("template_id")
        ver_id = e.get("template_version_id")  # may be None for legacy runs
        if not tpl_id:
            continue
        groups[(tpl_id, ver_id)].append(e)

    scored_count = 0
    error_count = 0

    for (template_id, template_version_id), runs in groups.items():
        try:
            metrics = _compute_metrics(runs, steps_by_exec)
            effectiveness = _composite(metrics)

            # Trend vs previous row for same (template_id, version).
            previous = await _fetch_previous_score(
                client, template_id, template_version_id
            )
            score_delta, trend = _trend(effectiveness, previous)

            record = {
                "template_id": template_id,
                "template_version_id": template_version_id,
                "evaluation_period": evaluation_period,
                "period_start": period_start,
                "period_end": period_end,
                "total_runs": metrics["total"],
                "unique_users": metrics["unique_users"],
                "completion_rate": round(metrics["completion_rate"], 4),
                "error_rate": round(metrics["error_rate"], 4),
                "retry_rate": round(metrics["retry_rate"], 4),
                "escalation_rate": round(metrics["escalation_rate"], 4),
                "effectiveness_score": round(effectiveness, 4),
                "score_delta": score_delta,
                "trend": trend,
                "evaluated_at": now.isoformat(),
                "metadata": {
                    "period_start": period_start,
                    "period_end": period_end,
                    "days": days,
                },
            }

            await execute_async(
                client.table("workflow_template_scores").upsert(
                    record,
                    on_conflict="template_id,template_version_id,evaluation_period",
                ),
                op_name="workflow_template_scoring.upsert_score",
            )
            scored_count += 1
        except Exception:
            logger.exception(
                "Failed scoring template %s version %s",
                template_id,
                template_version_id,
            )
            error_count += 1

    logger.info(
        "workflow_template_scoring scored=%d errors=%d period=%s",
        scored_count,
        error_count,
        evaluation_period,
    )
    return {
        "scored": scored_count,
        "errors": error_count,
        "evaluation_period": evaluation_period,
        "groups_evaluated": len(groups),
    }


# =====================================================================
# Pure helpers (exposed for unit testing)
# =====================================================================


def _compute_metrics(
    runs: list[dict[str, Any]],
    steps_by_exec: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Aggregate raw run + step rows into rate metrics.

    Edge cases:
      - A run with no step rows contributes 0 to retry and escalation
        numerators (we cannot conclude it had retries or escalations).
      - 'completed' status counts toward completion; 'failed' counts toward
        errors.  Other statuses (running, cancelled, etc.) count toward
        total but not toward completion or error.
    """
    total = len(runs)
    completed = 0
    failed = 0
    retried = 0
    escalated = 0
    unique_users: set[str] = set()

    for r in runs:
        if r.get("user_id"):
            unique_users.add(r["user_id"])
        status = r.get("status")
        if status == "completed":
            completed += 1
        elif status == "failed":
            failed += 1
        steps = steps_by_exec.get(r.get("id"), [])
        if any((s.get("attempt_count") or 0) > 1 for s in steps):
            retried += 1
        if any(s.get("sla_status") == "escalated" for s in steps):
            escalated += 1

    return {
        "total": total,
        "unique_users": len(unique_users),
        "completion_rate": completed / total if total else 0.0,
        "error_rate": failed / total if total else 0.0,
        "retry_rate": retried / total if total else 0.0,
        "escalation_rate": escalated / total if total else 0.0,
    }


def _composite(metrics: dict[str, float]) -> float:
    """Weighted composite — see module docstring for weight rationale."""
    return (
        _W_COMPLETION * metrics["completion_rate"]
        + _W_ERROR * (1.0 - metrics["error_rate"])
        + _W_RETRY * (1.0 - metrics["retry_rate"])
        + _W_ESCALATION * (1.0 - metrics["escalation_rate"])
    )


async def _fetch_previous_score(
    client: Any, template_id: str, template_version_id: str | None
) -> float | None:
    """Return the previous evaluated_at row's effectiveness_score, or None."""
    try:
        query = (
            client.table("workflow_template_scores")
            .select("effectiveness_score")
            .eq("template_id", template_id)
            .order("evaluated_at", desc=True)
            .limit(1)
        )
        if template_version_id is None:
            query = query.is_("template_version_id", "null")
        else:
            query = query.eq("template_version_id", template_version_id)
        resp = await execute_async(
            query, op_name="workflow_template_scoring.fetch_previous"
        )
        rows = resp.data or []
        if rows:
            return float(rows[0].get("effectiveness_score") or 0.0)
    except Exception:
        logger.debug(
            "previous score lookup failed for template %s",
            template_id,
            exc_info=True,
        )
    return None


def _trend(
    effectiveness: float, previous: float | None
) -> tuple[float | None, str]:
    """Compute score_delta + categorical trend label."""
    if previous is None:
        return None, "new"
    delta = round(effectiveness - previous, 4)
    if delta > _TREND_EPSILON:
        return delta, "improving"
    if delta < -_TREND_EPSILON:
        return delta, "declining"
    return delta, "stable"
