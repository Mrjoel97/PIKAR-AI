# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""KPI computation service — per-persona real-time metrics from Supabase tables."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

_KNOWN_PERSONAS = {"solopreneur", "startup", "sme", "enterprise"}

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_kpi_service_instance: KpiService | None = None


def get_kpi_service() -> KpiService:
    """Return the shared KpiService singleton."""
    global _kpi_service_instance  # noqa: PLW0603
    if _kpi_service_instance is None:
        _kpi_service_instance = KpiService()
    return _kpi_service_instance


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class KpiService:
    """Compute persona-specific KPIs from live Supabase data.

    Each public method call queries several Supabase tables and returns a
    structured payload suitable for the ``GET /kpis/persona`` endpoint.
    """

    def __init__(self) -> None:
        """Initialise with a Supabase service-role client."""
        self.client = get_service_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def compute_kpis(
        self,
        *,
        user_id: str,
        persona: str,
    ) -> dict[str, Any]:
        """Return computed KPIs for the given user and persona.

        Args:
            user_id: The authenticated user's UUID.
            persona: One of solopreneur | startup | sme | enterprise.
                     Unknown values fall back to solopreneur.

        Returns:
            ``{ "persona": str, "kpis": list[{"label", "value", "unit"}] }``
        """
        effective = persona.lower().strip() if persona else ""
        if effective not in _KNOWN_PERSONAS:
            effective = "solopreneur"

        dispatch = {
            "solopreneur": self._solopreneur_kpis,
            "startup": self._startup_kpis,
            "sme": self._sme_kpis,
            "enterprise": self._enterprise_kpis,
        }
        kpis = await dispatch[effective](user_id=user_id)
        return {"persona": effective, "kpis": kpis}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _safe_rows(self, query: Any) -> list[dict[str, Any]]:
        """Execute a Supabase query and return rows; return [] on any error."""
        try:
            response = await execute_async(query, op_name="kpi_service.query")
            return response.data or []
        except Exception:
            return []

    def _format_currency(self, amount: float | None, currency: str = "USD") -> str:
        """Format a float as a currency string, e.g. ``$5,000``."""
        if amount is None:
            return "$0"
        symbol = "$" if currency.upper() == "USD" else f"{currency.upper()} "
        return f"{symbol}{amount:,.0f}"

    def _pct(self, numerator: int, denominator: int) -> str:
        """Return an integer percentage string like ``42%``."""
        if denominator == 0:
            return "0%"
        return f"{round(numerator / denominator * 100)}%"

    def _now_utc(self) -> datetime:
        """Return the current UTC datetime."""
        return datetime.now(tz=timezone.utc)

    # ------------------------------------------------------------------
    # Solopreneur KPIs
    # ------------------------------------------------------------------

    async def _solopreneur_kpis(self, *, user_id: str) -> list[dict[str, Any]]:
        """Compute solopreneur KPIs: Cash Collected, Weekly Pipeline, Content Consistency."""
        cash = await self._solopreneur_cash_collected(user_id=user_id)
        pipeline = await self._solopreneur_weekly_pipeline(user_id=user_id)
        consistency = await self._solopreneur_content_consistency(user_id=user_id)
        return [cash, pipeline, consistency]

    async def _solopreneur_cash_collected(self, *, user_id: str) -> dict[str, Any]:
        """Sum total_amount of paid orders linked to paid invoices for the user."""
        invoice_rows = await self._safe_rows(
            self.client.table("invoices")
            .select("order_id")
            .eq("user_id", user_id)
            .eq("status", "paid")
        )
        total = 0.0
        if invoice_rows:
            order_ids = [r["order_id"] for r in invoice_rows if r.get("order_id")]
            if order_ids:
                order_rows = await self._safe_rows(
                    self.client.table("orders")
                    .select("total_amount")
                    .eq("user_id", user_id)
                    .eq("status", "paid")
                    .in_("id", order_ids)
                )
                total = sum(
                    float(r.get("total_amount") or 0) for r in order_rows
                )
        return {
            "label": "Cash Collected",
            "value": self._format_currency(total),
            "unit": "currency",
        }

    async def _solopreneur_weekly_pipeline(self, *, user_id: str) -> dict[str, Any]:
        """Sum estimated_value of contacts in opportunity/qualified stages."""
        rows = await self._safe_rows(
            self.client.table("contacts")
            .select("estimated_value")
            .eq("user_id", user_id)
            .in_("lifecycle_stage", ["opportunity", "qualified"])
        )
        total = sum(float(r.get("estimated_value") or 0) for r in rows)
        return {
            "label": "Weekly Pipeline",
            "value": self._format_currency(total),
            "unit": "currency",
        }

    async def _solopreneur_content_consistency(self, *, user_id: str) -> dict[str, Any]:
        """Count content_bundles created in the last 7 days."""
        seven_days_ago = (self._now_utc() - timedelta(days=7)).isoformat()
        rows = await self._safe_rows(
            self.client.table("content_bundles")
            .select("id")
            .eq("user_id", user_id)
            .gte("created_at", seven_days_ago)
        )
        count = len(rows)
        return {
            "label": "Content Consistency",
            "value": f"{count} this week",
            "unit": "pieces",
        }

    # ------------------------------------------------------------------
    # Startup KPIs
    # ------------------------------------------------------------------

    async def _startup_kpis(self, *, user_id: str) -> list[dict[str, Any]]:
        """Compute startup KPIs: MRR Growth, Activation & Conversion, Experiment Velocity."""
        mrr = await self._startup_mrr_growth(user_id=user_id)
        conversion = await self._startup_activation_conversion(user_id=user_id)
        velocity = await self._startup_experiment_velocity(user_id=user_id)
        return [mrr, conversion, velocity]

    async def _startup_mrr_growth(self, *, user_id: str) -> dict[str, Any]:
        """Compute month-over-month revenue growth percentage."""
        now = self._now_utc()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prior_month_end = current_month_start - timedelta(seconds=1)
        prior_month_start = prior_month_end.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        current_rows = await self._safe_rows(
            self.client.table("orders")
            .select("total_amount")
            .eq("user_id", user_id)
            .eq("status", "paid")
            .gte("created_at", current_month_start.isoformat())
        )
        prior_rows = await self._safe_rows(
            self.client.table("orders")
            .select("total_amount")
            .eq("user_id", user_id)
            .eq("status", "paid")
            .gte("created_at", prior_month_start.isoformat())
            .lt("created_at", current_month_start.isoformat())
        )

        current_rev = sum(float(r.get("total_amount") or 0) for r in current_rows)
        prior_rev = sum(float(r.get("total_amount") or 0) for r in prior_rows)

        if prior_rev == 0:
            value = "+0%"
        else:
            pct = round((current_rev - prior_rev) / prior_rev * 100)
            value = f"+{pct}%" if pct >= 0 else f"{pct}%"

        return {"label": "MRR Growth", "value": value, "unit": "percent"}

    async def _startup_activation_conversion(self, *, user_id: str) -> dict[str, Any]:
        """Compute percentage of contacts who are customers."""
        all_rows = await self._safe_rows(
            self.client.table("contacts").select("id,lifecycle_stage").eq("user_id", user_id)
        )
        total = len(all_rows)
        customers = sum(1 for r in all_rows if r.get("lifecycle_stage") == "customer")
        return {
            "label": "Activation & Conversion",
            "value": self._pct(customers, total),
            "unit": "percent",
        }

    async def _startup_experiment_velocity(self, *, user_id: str) -> dict[str, Any]:
        """Count completed workflow_executions in the last 7 days."""
        seven_days_ago = (self._now_utc() - timedelta(days=7)).isoformat()
        rows = await self._safe_rows(
            self.client.table("workflow_executions")
            .select("id")
            .eq("user_id", user_id)
            .eq("status", "completed")
            .gte("completed_at", seven_days_ago)
        )
        return {
            "label": "Experiment Velocity",
            "value": str(len(rows)),
            "unit": "per week",
        }

    # ------------------------------------------------------------------
    # SME KPIs
    # ------------------------------------------------------------------

    async def _sme_kpis(self, *, user_id: str) -> list[dict[str, Any]]:
        """Compute SME KPIs: Department Performance, Process Cycle Time, Margin & Compliance."""
        dept = await self._sme_department_performance()
        cycle = await self._sme_process_cycle_time(user_id=user_id)
        compliance = await self._sme_margin_compliance(user_id=user_id)
        return [dept, cycle, compliance]

    async def _sme_department_performance(self) -> dict[str, Any]:
        """Compute percentage of departments with RUNNING status."""
        all_rows = await self._safe_rows(
            self.client.table("departments").select("id,status")
        )
        total = len(all_rows)
        running = sum(1 for r in all_rows if r.get("status") == "RUNNING")
        return {
            "label": "Department Performance",
            "value": self._pct(running, total),
            "unit": "percent",
        }

    async def _sme_process_cycle_time(self, *, user_id: str) -> dict[str, Any]:
        """Compute average workflow completion time in hours."""
        rows = await self._safe_rows(
            self.client.table("workflow_executions")
            .select("created_at,completed_at")
            .eq("user_id", user_id)
            .eq("status", "completed")
            .not_.is_("completed_at", "null")
        )
        durations: list[float] = []
        for row in rows:
            try:
                start = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(row["completed_at"].replace("Z", "+00:00"))
                diff_hours = (end - start).total_seconds() / 3600
                if diff_hours >= 0:
                    durations.append(diff_hours)
            except Exception:
                continue

        if not durations:
            value = "0 hrs"
        else:
            avg = sum(durations) / len(durations)
            value = f"{avg:.1f} hrs"

        return {"label": "Process Cycle Time", "value": value, "unit": "hours"}

    async def _sme_margin_compliance(self, *, user_id: str) -> dict[str, Any]:
        """Compute percentage of compliance risks that are mitigated or resolved."""
        rows = await self._safe_rows(
            self.client.table("compliance_risks")
            .select("id,status")
            .eq("user_id", user_id)
        )
        total = len(rows)
        resolved = sum(
            1 for r in rows if r.get("status") in {"mitigated", "resolved"}
        )
        return {
            "label": "Margin & Compliance",
            "value": self._pct(resolved, total),
            "unit": "percent",
        }

    # ------------------------------------------------------------------
    # Enterprise KPIs
    # ------------------------------------------------------------------

    async def _enterprise_kpis(self, *, user_id: str) -> list[dict[str, Any]]:
        """Compute enterprise KPIs: Portfolio Health, Risk & Control Coverage, Reporting Quality."""
        portfolio = await self._enterprise_portfolio_health(user_id=user_id)
        risk = await self._enterprise_risk_control_coverage(user_id=user_id)
        reporting = await self._enterprise_reporting_quality(user_id=user_id)
        return [portfolio, risk, reporting]

    async def _enterprise_portfolio_health(self, *, user_id: str) -> dict[str, Any]:
        """Score: in-progress initiatives with progress >= 50 / total active initiatives."""
        rows = await self._safe_rows(
            self.client.table("initiatives")
            .select("id,status,progress")
            .eq("user_id", user_id)
            .in_("status", ["in_progress", "blocked", "not_started"])
        )
        total = len(rows)
        on_track = sum(
            1
            for r in rows
            if r.get("status") == "in_progress" and int(r.get("progress") or 0) >= 50
        )
        score = round(on_track / total * 100) if total > 0 else 0
        return {
            "label": "Portfolio Health",
            "value": str(score),
            "unit": "score",
        }

    async def _enterprise_risk_control_coverage(self, *, user_id: str) -> dict[str, Any]:
        """Percentage of compliance_risks with a non-null mitigation_plan."""
        rows = await self._safe_rows(
            self.client.table("compliance_risks")
            .select("id,mitigation_plan")
            .eq("user_id", user_id)
        )
        total = len(rows)
        with_plan = sum(1 for r in rows if r.get("mitigation_plan"))
        return {
            "label": "Risk & Control Coverage",
            "value": self._pct(with_plan, total),
            "unit": "percent",
        }

    async def _enterprise_reporting_quality(self, *, user_id: str) -> dict[str, Any]:
        """Count user_reports created this calendar month."""
        now = self._now_utc()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rows = await self._safe_rows(
            self.client.table("user_reports")
            .select("id")
            .eq("user_id", user_id)
            .gte("created_at", month_start.isoformat())
        )
        return {
            "label": "Reporting Quality",
            "value": str(len(rows)),
            "unit": "reports",
        }
