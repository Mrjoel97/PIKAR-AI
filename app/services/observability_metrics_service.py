# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""ObservabilityMetricsService — agent latency, error rate, and AI cost computation.

Plan 51-03 / OBS-02, OBS-03, OBS-04. Sibling of BillingMetricsService.

Latency strategy (CONTEXT.md hybrid decision):
- Windows <= 24h: live Python-side percentile computation on agent_telemetry
- Windows > 24h: query pre-computed agent_latency_rollups table
- Spans the boundary: union both

AI cost strategy: on-demand from agent_telemetry (no rollup table needed
at solopreneur scale). Pricing is a Python constant dict updated via code PR.

AI model-to-agent mapping: agent_telemetry does not store the model name.
We use gemini-2.5-pro pricing for all specialized agents as an approximation
because that is the primary model (see app/agents/shared.py). This is
documented as an approximation in the module docstring and class docstring.

Error rate threshold alerting: writes to admin_audit_log when error rate
exceeds OBSERVABILITY_ERROR_RATE_THRESHOLD over OBSERVABILITY_THRESHOLD_WINDOW_MINUTES.

Inherits from :class:`~app.services.base_service.AdminService` because it
runs only inside admin-guarded routes and aggregates across every user, so
it requires the service-role client to bypass RLS.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar

from app.services.admin_audit import log_admin_action
from app.services.base_service import AdminService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

#: 24-hour boundary for the hybrid latency strategy (in hours).
_LIVE_WINDOW_HOURS: int = 24


def _percentile(sorted_values: list[float], p: float) -> float:
    """Compute the p-th percentile from a pre-sorted list.

    Uses linear interpolation between adjacent values (same method as
    PostgreSQL ``percentile_cont``).

    Args:
        sorted_values: List of numeric values sorted in ascending order.
        p: Percentile as a fraction in [0.0, 1.0] (e.g. 0.95 for p95).

    Returns:
        Interpolated percentile value, or 0.0 for an empty list.
    """
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * p
    f = int(k)
    c = f + 1
    if c >= len(sorted_values):
        return sorted_values[f]
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


class ObservabilityMetricsService(AdminService):
    """Agent latency percentiles, error rates, and AI token cost for the admin dashboard.

    All public methods are async and depend only on the ``agent_telemetry`` and
    ``agent_latency_rollups`` tables — no external API dependency.

    AI cost computation is an approximation: ``agent_telemetry`` does not store
    the model name per event. We use ``gemini-2.5-pro`` pricing for all agents
    as the primary model (see CLAUDE.md: "Primary Gemini 2.5 Pro falls back to
    Gemini 2.5 Flash"). The ``AI_MODEL_PRICING`` constant can be updated via a
    code PR when model pricing changes.
    """

    #: (input_cost_per_million_tokens, output_cost_per_million_tokens) in USD.
    #: Source: Google AI pricing as of 2026-04. Update via code PR on price changes.
    AI_MODEL_PRICING: ClassVar[dict[str, tuple[float, float]]] = {
        "gemini-2.5-pro": (1.25, 5.00),
        "gemini-2.5-flash": (0.075, 0.30),
        "gemini-2.5-flash-lite": (0.01875, 0.075),
        "text-embedding-004": (0.0, 0.0),  # Free tier
    }

    #: Error rate fraction above which a threshold breach is recorded in
    #: ``admin_audit_log``. Default 5% (0.05).
    OBSERVABILITY_ERROR_RATE_THRESHOLD: ClassVar[float] = 0.05

    #: Window in minutes for the threshold breach check.
    OBSERVABILITY_THRESHOLD_WINDOW_MINUTES: ClassVar[int] = 10

    # ------------------------------------------------------------------
    # Latency percentiles
    # ------------------------------------------------------------------

    async def compute_latency_percentiles(
        self,
        agent_name: str | None,
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        """Compute p50, p95, p99 latency percentiles for the given time window.

        Hybrid strategy:
        - Window entirely within last 24h → live query on ``agent_telemetry``
        - Window entirely older than 24h → query ``agent_latency_rollups``
        - Window spans the 24h boundary → union both sources

        Args:
            agent_name: Filter to a specific agent, or None for all agents.
            start: Window start (UTC-aware datetime).
            end: Window end (UTC-aware datetime).

        Returns:
            ``{"p50": float, "p95": float, "p99": float,
               "sample_count": int, "error_count": int}``
        """
        now = datetime.now(tz=timezone.utc)
        boundary = now - timedelta(hours=_LIVE_WINDOW_HOURS)

        duration_ms_values: list[float] = []
        sample_count = 0
        error_count = 0

        # Determine which sources to query
        need_live = start >= boundary or end > boundary
        need_rollup = start < boundary

        if need_live:
            live_start = max(start, boundary)
            query = (
                self.client.table("agent_telemetry")
                .select("duration_ms, status")
                .gte("created_at", live_start.isoformat())
                .lte("created_at", end.isoformat())
            )
            if agent_name:
                query = query.eq("agent_name", agent_name)

            result = await execute_async(
                query, op_name="observability.latency.live"
            )
            rows: list[dict] = result.data or []
            for row in rows:
                ms = row.get("duration_ms")
                if ms is not None:
                    duration_ms_values.append(float(ms))
                if row.get("status") == "error":
                    error_count += 1
            sample_count += len(rows)

        if need_rollup:
            rollup_end = min(end, boundary)
            query = (
                self.client.table("agent_latency_rollups")
                .select("p50_ms, p95_ms, p99_ms, sample_count, error_count")
                .gte("bucket_start", start.isoformat())
                .lte("bucket_start", rollup_end.isoformat())
            )
            if agent_name:
                query = query.eq("agent_name", agent_name)

            result = await execute_async(
                query, op_name="observability.latency.rollup"
            )
            rollup_rows: list[dict] = result.data or []
            for row in rollup_rows:
                # For rollup rows, use the pre-computed p50 as a representative
                # value for re-combining percentiles. This is an approximation.
                p50 = row.get("p50_ms")
                if p50 is not None:
                    duration_ms_values.append(float(p50))
                sample_count += row.get("sample_count") or 0
                error_count += row.get("error_count") or 0

        if not duration_ms_values:
            return {
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "sample_count": sample_count,
                "error_count": error_count,
            }

        sorted_vals = sorted(duration_ms_values)
        return {
            "p50": round(_percentile(sorted_vals, 0.50), 2),
            "p95": round(_percentile(sorted_vals, 0.95), 2),
            "p99": round(_percentile(sorted_vals, 0.99), 2),
            "sample_count": sample_count,
            "error_count": error_count,
        }

    # ------------------------------------------------------------------
    # Error rate
    # ------------------------------------------------------------------

    async def compute_error_rate(
        self,
        agent_name: str | None,
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        """Compute error rate by count for the given time window.

        Args:
            agent_name: Filter to a specific agent, or None for all agents.
            start: Window start (UTC-aware datetime).
            end: Window end (UTC-aware datetime).

        Returns:
            ``{"error_rate": float, "error_count": int, "total_count": int}``
            ``error_rate`` is 0.0 when ``total_count`` is 0.
        """
        base_query = (
            self.client.table("agent_telemetry")
            .select("status", count="exact")
            .gte("created_at", start.isoformat())
            .lte("created_at", end.isoformat())
        )
        if agent_name:
            base_query = base_query.eq("agent_name", agent_name)

        # Total count
        total_result = await execute_async(
            base_query, op_name="observability.error_rate.total"
        )
        total_count = total_result.count or 0

        # Error count only
        error_query = (
            self.client.table("agent_telemetry")
            .select("status", count="exact")
            .gte("created_at", start.isoformat())
            .lte("created_at", end.isoformat())
            .eq("status", "error")
        )
        if agent_name:
            error_query = error_query.eq("agent_name", agent_name)

        error_result = await execute_async(
            error_query, op_name="observability.error_rate.errors"
        )
        error_count = error_result.count or 0

        error_rate = error_count / total_count if total_count > 0 else 0.0

        return {
            "error_rate": round(error_rate, 4),
            "error_count": error_count,
            "total_count": total_count,
        }

    # ------------------------------------------------------------------
    # AI cost helpers
    # ------------------------------------------------------------------

    def _compute_cost_for_row(
        self, input_tokens: int | None, output_tokens: int | None
    ) -> float:
        """Compute USD cost for one agent_telemetry row using gemini-2.5-pro pricing.

        Args:
            input_tokens: Number of input tokens (nullable in agent_telemetry).
            output_tokens: Number of output tokens (nullable in agent_telemetry).

        Returns:
            Cost in USD as a float.
        """
        input_price, output_price = self.AI_MODEL_PRICING["gemini-2.5-pro"]
        in_tok = input_tokens or 0
        out_tok = output_tokens or 0
        return (in_tok / 1_000_000) * input_price + (out_tok / 1_000_000) * output_price

    # ------------------------------------------------------------------
    # AI cost by agent
    # ------------------------------------------------------------------

    async def compute_ai_cost_by_agent(
        self, start: datetime, end: datetime
    ) -> dict[str, float]:
        """Sum AI token cost grouped by agent_name for the given window.

        Uses ``gemini-2.5-pro`` pricing as the default approximation since
        ``agent_telemetry`` does not store the model name per event.

        Args:
            start: Window start (UTC-aware datetime).
            end: Window end (UTC-aware datetime).

        Returns:
            ``{agent_name: cost_usd}`` dict, values rounded to 6 decimal places.
        """
        result = await execute_async(
            self.client.table("agent_telemetry")
            .select("agent_name, input_tokens, output_tokens")
            .gte("created_at", start.isoformat())
            .lte("created_at", end.isoformat()),
            op_name="observability.cost.by_agent",
        )
        rows: list[dict] = result.data or []

        costs: dict[str, float] = {}
        for row in rows:
            name = row.get("agent_name") or "unknown"
            cost = self._compute_cost_for_row(
                row.get("input_tokens"), row.get("output_tokens")
            )
            costs[name] = round(costs.get(name, 0.0) + cost, 6)

        return costs

    # ------------------------------------------------------------------
    # AI cost by user
    # ------------------------------------------------------------------

    async def compute_ai_cost_by_user(
        self, start: datetime, end: datetime, top_n: int = 10
    ) -> list[dict[str, Any]]:
        """Sum AI token cost grouped by user_id for the given window.

        Args:
            start: Window start (UTC-aware datetime).
            end: Window end (UTC-aware datetime).
            top_n: Return only the top N users by cost (default 10).

        Returns:
            List of ``{"user_id": str | None, "cost_usd": float}`` dicts,
            sorted descending by cost, truncated to ``top_n`` entries.
        """
        result = await execute_async(
            self.client.table("agent_telemetry")
            .select("user_id, input_tokens, output_tokens")
            .gte("created_at", start.isoformat())
            .lte("created_at", end.isoformat()),
            op_name="observability.cost.by_user",
        )
        rows: list[dict] = result.data or []

        costs: dict[str | None, float] = {}
        for row in rows:
            uid = row.get("user_id")
            cost = self._compute_cost_for_row(
                row.get("input_tokens"), row.get("output_tokens")
            )
            costs[uid] = round(costs.get(uid, 0.0) + cost, 6)

        sorted_costs = sorted(costs.items(), key=lambda x: x[1], reverse=True)
        return [
            {"user_id": uid, "cost_usd": cost}
            for uid, cost in sorted_costs[:top_n]
        ]

    # ------------------------------------------------------------------
    # AI cost by day
    # ------------------------------------------------------------------

    async def compute_ai_cost_by_day(
        self, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        """Sum AI token cost grouped by UTC date for the given window.

        Args:
            start: Window start (UTC-aware datetime).
            end: Window end (UTC-aware datetime).

        Returns:
            List of ``{"date": "YYYY-MM-DD", "cost_usd": float}`` dicts,
            sorted chronologically (oldest first).
        """
        result = await execute_async(
            self.client.table("agent_telemetry")
            .select("created_at, input_tokens, output_tokens")
            .gte("created_at", start.isoformat())
            .lte("created_at", end.isoformat()),
            op_name="observability.cost.by_day",
        )
        rows: list[dict] = result.data or []

        day_costs: dict[str, float] = {}
        for row in rows:
            created_at = row.get("created_at")
            if not created_at:
                continue
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (TypeError, ValueError):
                logger.debug("Skipping unparseable created_at: %r", created_at)
                continue
            day = dt.astimezone(timezone.utc).date().isoformat()
            cost = self._compute_cost_for_row(
                row.get("input_tokens"), row.get("output_tokens")
            )
            day_costs[day] = round(day_costs.get(day, 0.0) + cost, 6)

        return [
            {"date": day, "cost_usd": cost}
            for day, cost in sorted(day_costs.items())
        ]

    # ------------------------------------------------------------------
    # Monthly spend projection
    # ------------------------------------------------------------------

    async def project_monthly_ai_spend(self) -> dict[str, Any]:
        """Project full-month AI spend using 7-day linear extrapolation.

        Fetches the last 7 days of daily cost via ``compute_ai_cost_by_day``.
        Averages the daily cost, multiplies by days remaining in the current
        month, and adds the MTD actual spend.

        Returns:
            ``{"mtd_actual": float, "projected_full_month": float,
               "projection_method": "linear_7day"}``
        """
        now = datetime.now(tz=timezone.utc)
        # Last 7 days including today
        window_start = now - timedelta(days=7)
        daily_costs = await self.compute_ai_cost_by_day(window_start, now)

        mtd_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        mtd_costs = await self.compute_ai_cost_by_day(mtd_start, now)
        mtd_actual = sum(entry["cost_usd"] for entry in mtd_costs)

        # Days remaining in the current month (today counts as "already running")
        from calendar import monthrange
        days_in_month = monthrange(now.year, now.month)[1]
        days_elapsed = now.day  # 1-based
        days_remaining = days_in_month - days_elapsed

        avg_daily = (
            sum(entry["cost_usd"] for entry in daily_costs) / len(daily_costs)
            if daily_costs
            else 0.0
        )
        projected_full_month = round(mtd_actual + avg_daily * days_remaining, 4)

        return {
            "mtd_actual": round(mtd_actual, 4),
            "projected_full_month": projected_full_month,
            "projection_method": "linear_7day",
        }

    # ------------------------------------------------------------------
    # Hourly rollup job
    # ------------------------------------------------------------------

    async def run_hourly_rollup(self) -> dict[str, Any]:
        """Compute the previous hour's latency rollup and upsert into agent_latency_rollups.

        Groups ``agent_telemetry`` rows from the previous full hour by
        ``(agent_name, status)``, computes percentiles in Python, and upserts
        into ``agent_latency_rollups`` (idempotent via unique index on
        ``(agent_name, status, bucket_start)``).

        Returns:
            ``{"buckets_written": int, "bucket_start": str, "bucket_end": str}``
        """
        now = datetime.now(tz=timezone.utc)
        # Previous hour bucket: e.g. if now is 14:37, bucket is 13:00–14:00
        bucket_end = now.replace(minute=0, second=0, microsecond=0)
        bucket_start = bucket_end - timedelta(hours=1)

        result = await execute_async(
            self.client.table("agent_telemetry")
            .select("agent_name, status, duration_ms")
            .gte("created_at", bucket_start.isoformat())
            .lt("created_at", bucket_end.isoformat()),
            op_name="observability.rollup.fetch",
        )
        rows: list[dict] = result.data or []

        # Group by (agent_name, status)
        groups: dict[tuple[str, str], list[float]] = {}
        error_counts: dict[tuple[str, str], int] = {}
        total_durations: dict[tuple[str, str], int] = {}

        for row in rows:
            key = (
                row.get("agent_name") or "unknown",
                row.get("status") or "unknown",
            )
            ms = row.get("duration_ms")
            if ms is not None:
                groups.setdefault(key, []).append(float(ms))
                total_durations[key] = total_durations.get(key, 0) + int(ms)
            else:
                groups.setdefault(key, [])
                total_durations.setdefault(key, 0)

            if row.get("status") == "error":
                error_counts[key] = error_counts.get(key, 0) + 1

        buckets_written = 0
        for (agent, status), durations in groups.items():
            sorted_durations = sorted(durations)
            upsert_row = {
                "agent_name": agent,
                "status": status,
                "bucket_start": bucket_start.isoformat(),
                "bucket_end": bucket_end.isoformat(),
                "sample_count": len(durations),
                "p50_ms": _percentile(sorted_durations, 0.50) if sorted_durations else None,
                "p95_ms": _percentile(sorted_durations, 0.95) if sorted_durations else None,
                "p99_ms": _percentile(sorted_durations, 0.99) if sorted_durations else None,
                "error_count": error_counts.get((agent, status), 0),
                "total_duration_ms": total_durations.get((agent, status), 0),
            }
            await execute_async(
                self.client.table("agent_latency_rollups").upsert(
                    upsert_row,
                    on_conflict="agent_name,status,bucket_start",
                ),
                op_name="observability.rollup.upsert",
            )
            buckets_written += 1

        logger.info(
            "Hourly latency rollup complete: buckets_written=%d bucket=%s",
            buckets_written,
            bucket_start.isoformat(),
        )
        return {
            "buckets_written": buckets_written,
            "bucket_start": bucket_start.isoformat(),
            "bucket_end": bucket_end.isoformat(),
        }

    # ------------------------------------------------------------------
    # Error threshold check
    # ------------------------------------------------------------------

    async def check_error_threshold(self) -> dict[str, Any] | None:
        """Check if error rate exceeds the threshold over the last N minutes.

        If ``error_rate > OBSERVABILITY_ERROR_RATE_THRESHOLD``, writes a
        ``observability.threshold_breach`` record to ``admin_audit_log`` via
        :func:`~app.services.admin_audit.log_admin_action`.

        Returns:
            Breach details dict if threshold exceeded, ``None`` otherwise.
        """
        now = datetime.now(tz=timezone.utc)
        window_start = now - timedelta(minutes=self.OBSERVABILITY_THRESHOLD_WINDOW_MINUTES)

        error_data = await self.compute_error_rate(None, window_start, now)
        error_rate = error_data["error_rate"]

        if error_rate > self.OBSERVABILITY_ERROR_RATE_THRESHOLD:
            # Gather per-agent breakdown to include in audit log
            agent_result = await execute_async(
                self.client.table("agent_telemetry")
                .select("agent_name, status")
                .gte("created_at", window_start.isoformat())
                .lte("created_at", now.isoformat())
                .eq("status", "error"),
                op_name="observability.threshold.breakdown",
            )
            error_rows: list[dict] = agent_result.data or []
            affected_agents = list({row.get("agent_name") for row in error_rows if row.get("agent_name")})

            breach_details: dict[str, Any] = {
                "threshold": self.OBSERVABILITY_ERROR_RATE_THRESHOLD,
                "observed_rate": error_rate,
                "error_count": error_data["error_count"],
                "total_count": error_data["total_count"],
                "affected_agents": affected_agents,
                "time_window_minutes": self.OBSERVABILITY_THRESHOLD_WINDOW_MINUTES,
                "checked_at": now.isoformat(),
            }

            await log_admin_action(
                admin_user_id=None,
                action="observability.threshold_breach",
                target_type="system",
                target_id=None,
                details=breach_details,
                source="monitoring_loop",
            )
            logger.warning(
                "Observability error threshold breach: rate=%.4f threshold=%.4f agents=%s",
                error_rate,
                self.OBSERVABILITY_ERROR_RATE_THRESHOLD,
                affected_agents,
            )
            return breach_details

        return None


__all__ = ["ObservabilityMetricsService"]
