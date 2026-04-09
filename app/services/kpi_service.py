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
    global _kpi_service_instance
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
    Each KPI dict includes label, value, unit, and subtitle fields.
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
            ``{ "persona": str, "kpis": list[{"label", "value", "unit", "subtitle"}] }``
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
    # Solopreneur KPIs  (4 total)
    # ------------------------------------------------------------------

    async def _solopreneur_kpis(self, *, user_id: str) -> list[dict[str, Any]]:
        """Compute solopreneur KPIs: Revenue, Weekly Pipeline, Content Created, Connected Integrations."""
        revenue = await self._solopreneur_revenue(user_id=user_id)
        pipeline = await self._solopreneur_weekly_pipeline(user_id=user_id)
        content = await self._solopreneur_content_created(user_id=user_id)
        integrations = await self._solopreneur_connected_integrations(user_id=user_id)
        return [revenue, pipeline, content, integrations]

    async def _solopreneur_revenue(self, *, user_id: str) -> dict[str, Any]:
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
                total = sum(float(r.get("total_amount") or 0) for r in order_rows)
        return {
            "label": "Revenue",
            "value": self._format_currency(total),
            "unit": "currency",
            "subtitle": "No revenue yet — complete your first sale to see this update",
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
            "subtitle": "Add contacts in opportunity/qualified stage to see pipeline value",
        }

    async def _solopreneur_content_created(self, *, user_id: str) -> dict[str, Any]:
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
            "label": "Content Created",
            "value": str(count),
            "unit": "pieces",
            "subtitle": "Create content bundles to track your weekly output",
        }

    async def _solopreneur_connected_integrations(
        self, *, user_id: str
    ) -> dict[str, Any]:
        """Count connected integrations from user_integrations table."""
        rows = await self._safe_rows(
            self.client.table("user_integrations")
            .select("id")
            .eq("user_id", user_id)
            .eq("status", "connected")
        )
        count = len(rows)
        return {
            "label": "Connected Integrations",
            "value": str(count),
            "unit": "integrations",
            "subtitle": "Connect apps like Gmail, Stripe, or Calendly to unlock automation",
        }

    # ------------------------------------------------------------------
    # Startup KPIs  (4 total)
    # ------------------------------------------------------------------

    async def _startup_kpis(self, *, user_id: str) -> list[dict[str, Any]]:
        """Compute startup KPIs: Revenue, Pipeline Value, Team Size, Growth Rate (MoM)."""
        revenue = await self._startup_revenue(user_id=user_id)
        pipeline = await self._startup_pipeline_value(user_id=user_id)
        team = await self._startup_team_size(user_id=user_id)
        growth = await self._startup_growth_rate(user_id=user_id)
        return [revenue, pipeline, team, growth]

    async def _startup_revenue(self, *, user_id: str) -> dict[str, Any]:
        """Sum total_amount of paid orders this calendar month."""
        now = self._now_utc()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rows = await self._safe_rows(
            self.client.table("orders")
            .select("total_amount")
            .eq("user_id", user_id)
            .eq("status", "paid")
            .gte("created_at", month_start.isoformat())
        )
        total = sum(float(r.get("total_amount") or 0) for r in rows)
        return {
            "label": "Revenue",
            "value": self._format_currency(total),
            "unit": "currency",
            "subtitle": "No paid orders this month yet — close your first deal",
        }

    async def _startup_pipeline_value(self, *, user_id: str) -> dict[str, Any]:
        """Sum estimated_value of contacts in opportunity/qualified stages."""
        rows = await self._safe_rows(
            self.client.table("contacts")
            .select("estimated_value")
            .eq("user_id", user_id)
            .in_("lifecycle_stage", ["opportunity", "qualified"])
        )
        total = sum(float(r.get("estimated_value") or 0) for r in rows)
        return {
            "label": "Pipeline Value",
            "value": self._format_currency(total),
            "unit": "currency",
            "subtitle": "Qualify contacts to build your sales pipeline",
        }

    async def _startup_team_size(self, *, user_id: str) -> dict[str, Any]:
        """Count workspace members for the user's workspace."""
        rows = await self._safe_rows(
            self.client.table("workspace_members").select("id").eq("user_id", user_id)
        )
        count = len(rows)
        return {
            "label": "Team Size",
            "value": str(count),
            "unit": "members",
            "subtitle": "Invite team members to your workspace to see headcount",
        }

    async def _startup_growth_rate(self, *, user_id: str) -> dict[str, Any]:
        """Compute month-over-month revenue growth percentage."""
        now = self._now_utc()
        current_month_start = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
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

        return {
            "label": "Growth Rate (MoM)",
            "value": value,
            "unit": "percent",
            "subtitle": "Revenue growth will appear once you have two months of data",
        }

    # ------------------------------------------------------------------
    # SME KPIs  (4 total)
    # ------------------------------------------------------------------

    async def _sme_kpis(self, *, user_id: str) -> list[dict[str, Any]]:
        """Compute SME KPIs: Revenue, Active Departments, Compliance Score, Open Tasks."""
        revenue = await self._sme_revenue(user_id=user_id)
        depts = await self._sme_active_departments()
        compliance = await self._sme_compliance_score(user_id=user_id)
        tasks = await self._sme_open_tasks(user_id=user_id)
        return [revenue, depts, compliance, tasks]

    async def _sme_revenue(self, *, user_id: str) -> dict[str, Any]:
        """Sum total_amount of paid orders this calendar month."""
        now = self._now_utc()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rows = await self._safe_rows(
            self.client.table("orders")
            .select("total_amount")
            .eq("user_id", user_id)
            .eq("status", "paid")
            .gte("created_at", month_start.isoformat())
        )
        total = sum(float(r.get("total_amount") or 0) for r in rows)
        return {
            "label": "Revenue",
            "value": self._format_currency(total),
            "unit": "currency",
            "subtitle": "No paid orders this month — configure your billing integration",
        }

    async def _sme_active_departments(self) -> dict[str, Any]:
        """Count departments with RUNNING status."""
        all_rows = await self._safe_rows(
            self.client.table("departments").select("id,status")
        )
        running = sum(1 for r in all_rows if r.get("status") == "RUNNING")
        return {
            "label": "Active Departments",
            "value": str(running),
            "unit": "departments",
            "subtitle": "Set departments to RUNNING to track active operational units",
        }

    async def _sme_compliance_score(self, *, user_id: str) -> dict[str, Any]:
        """Compute percentage of compliance risks that are mitigated or resolved."""
        rows = await self._safe_rows(
            self.client.table("compliance_risks")
            .select("id,status")
            .eq("user_id", user_id)
        )
        total = len(rows)
        resolved = sum(1 for r in rows if r.get("status") in {"mitigated", "resolved"})
        return {
            "label": "Compliance Score",
            "value": self._pct(resolved, total),
            "unit": "percent",
            "subtitle": "Log compliance risks and resolve them to improve your score",
        }

    async def _sme_open_tasks(self, *, user_id: str) -> dict[str, Any]:
        """Count open tasks for the user."""
        rows = await self._safe_rows(
            self.client.table("tasks")
            .select("id")
            .eq("user_id", user_id)
            .eq("status", "open")
        )
        count = len(rows)
        return {
            "label": "Open Tasks",
            "value": str(count),
            "unit": "tasks",
            "subtitle": "Create tasks to track team work items and deadlines",
        }

    # ------------------------------------------------------------------
    # Enterprise KPIs  (4 total)
    # ------------------------------------------------------------------

    async def _enterprise_kpis(self, *, user_id: str) -> list[dict[str, Any]]:
        """Compute enterprise KPIs: Portfolio Health %, Risk Score, Total Revenue, Department Count."""
        portfolio = await self._enterprise_portfolio_health(user_id=user_id)
        risk = await self._enterprise_risk_score(user_id=user_id)
        revenue = await self._enterprise_total_revenue(user_id=user_id)
        depts = await self._enterprise_department_count()
        return [portfolio, risk, revenue, depts]

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
        value = f"{round(on_track / total * 100)}%" if total > 0 else "0%"
        return {
            "label": "Portfolio Health %",
            "value": value,
            "unit": "percent",
            "subtitle": "Create strategic initiatives and track progress to measure portfolio health",
        }

    async def _enterprise_risk_score(self, *, user_id: str) -> dict[str, Any]:
        """Percentage of compliance_risks with a non-null mitigation_plan."""
        rows = await self._safe_rows(
            self.client.table("compliance_risks")
            .select("id,mitigation_plan")
            .eq("user_id", user_id)
        )
        total = len(rows)
        with_plan = sum(1 for r in rows if r.get("mitigation_plan"))
        return {
            "label": "Risk Score",
            "value": self._pct(with_plan, total),
            "unit": "percent",
            "subtitle": "Add mitigation plans to compliance risks to improve your risk score",
        }

    async def _enterprise_total_revenue(self, *, user_id: str) -> dict[str, Any]:
        """Sum total_amount of all paid orders all time."""
        rows = await self._safe_rows(
            self.client.table("orders")
            .select("total_amount")
            .eq("user_id", user_id)
            .eq("status", "paid")
        )
        total = sum(float(r.get("total_amount") or 0) for r in rows)
        return {
            "label": "Total Revenue",
            "value": self._format_currency(total),
            "unit": "currency",
            "subtitle": "Connect your billing to track cumulative revenue across all time",
        }

    async def _enterprise_department_count(self) -> dict[str, Any]:
        """Count all departments."""
        rows = await self._safe_rows(self.client.table("departments").select("id"))
        count = len(rows)
        return {
            "label": "Department Count",
            "value": str(count),
            "unit": "departments",
            "subtitle": "Add departments to your org chart to see the full structure",
        }
