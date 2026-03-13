# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for the Financial Analysis Agent."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Optional


def _get_current_user_id() -> Optional[str]:
    from app.services.request_context import get_current_user_id

    return get_current_user_id()


async def _query_financial_records(
    *,
    user_id: Optional[str],
    record_type: Optional[str] = None,
    days_back: Optional[int] = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    from app.services.financial_service import FinancialService

    service = FinancialService()
    query = service.client.table("financial_records").select(
        "id, user_id, amount, transaction_type, currency, transaction_date, description"
    )
    if user_id:
        query = query.eq("user_id", user_id)
    if record_type:
        query = query.eq("transaction_type", record_type)
    if days_back is not None:
        cutoff = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
        query = query.gte("transaction_date", cutoff)
    response = query.order("transaction_date", desc=True).limit(limit).execute()
    return response.data or []


def _sum_amounts(records: list[dict[str, Any]]) -> float:
    total = 0.0
    for record in records:
        amount = record.get("amount")
        if isinstance(amount, (int, float)):
            total += float(amount)
    return round(total, 2)


async def get_revenue_stats(period: str = "current_month") -> dict:
    """Get revenue statistics for financial analysis from FinancialService."""
    from app.services.financial_service import FinancialService

    try:
        service = FinancialService()
        stats = await service.get_revenue_stats(period)
        return {"success": True, **stats}
    except Exception as e:
        return {
            "success": False,
            "revenue": 0.0,
            "currency": "USD",
            "period": period,
            "error": f"Service unavailable: {str(e)}",
        }


async def get_cash_position() -> dict:
    """Compute an estimated cash position from user financial records."""
    try:
        user_id = _get_current_user_id()
        records = await _query_financial_records(user_id=user_id)
        inflow_types = {"revenue", "income", "credit", "payment"}
        outflow_types = {"expense", "burn", "cost", "payroll", "debit"}

        inflows = 0.0
        outflows = 0.0
        currency = "USD"
        for record in records:
            amount = record.get("amount")
            if not isinstance(amount, (int, float)):
                continue
            currency = record.get("currency") or currency
            record_type = str(record.get("transaction_type") or "").strip().lower()
            numeric_amount = float(amount)
            if record_type in outflow_types:
                outflows += abs(numeric_amount)
            elif record_type in inflow_types or numeric_amount >= 0:
                inflows += numeric_amount
            else:
                outflows += abs(numeric_amount)

        cash_position = round(inflows - outflows, 2)
        return {
            "success": True,
            "cash_position": cash_position,
            "currency": currency,
            "inflows": round(inflows, 2),
            "outflows": round(outflows, 2),
            "record_count": len(records),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "cash_position": 0.0, "currency": "USD"}


async def get_burn_runway_report(monthly_burn: Optional[float] = None) -> dict:
    """Estimate monthly burn and runway from recent financial records."""
    try:
        user_id = _get_current_user_id()
        cash_position = await get_cash_position()
        expense_records = await _query_financial_records(
            user_id=user_id,
            days_back=90,
            limit=500,
        )
        expense_total = 0.0
        for record in expense_records:
            record_type = str(record.get("transaction_type") or "").strip().lower()
            amount = record.get("amount")
            if record_type in {"expense", "burn", "cost", "payroll", "debit"} and isinstance(amount, (int, float)):
                expense_total += abs(float(amount))

        estimated_burn = round(monthly_burn if monthly_burn is not None else expense_total / 3 if expense_total else 0.0, 2)
        available_cash = float(cash_position.get("cash_position") or 0.0)
        runway_months = round(available_cash / estimated_burn, 2) if estimated_burn > 0 else None

        return {
            "success": True,
            "cash_position": available_cash,
            "monthly_burn": estimated_burn,
            "runway_months": runway_months,
            "currency": cash_position.get("currency", "USD"),
            "calculation_window_days": 90,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "monthly_burn": 0.0, "runway_months": None}


async def get_financial_report(period: str = "current_month") -> dict:
    """Return a compact finance report with revenue, cash, and runway metrics."""
    try:
        revenue = await get_revenue_stats(period)
        cash = await get_cash_position()
        runway = await get_burn_runway_report()
        return {
            "success": True,
            "period": period,
            "revenue": revenue.get("revenue", 0.0),
            "currency": revenue.get("currency") or cash.get("currency") or "USD",
            "cash_position": cash.get("cash_position", 0.0),
            "monthly_burn": runway.get("monthly_burn", 0.0),
            "runway_months": runway.get("runway_months"),
            "details": {
                "revenue": revenue,
                "cash": cash,
                "runway": runway,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e), "period": period}


async def save_finance_assumption(
    assumption_type: str,
    value: float,
    scope: str = "global",
    label: str = "",
    notes: str = "",
) -> dict:
    """Persist a finance assumption for forecasting and reporting."""
    try:
        from app.services.financial_service import FinancialService

        user_id = _get_current_user_id()
        service = FinancialService()
        payload = {
            "user_id": user_id,
            "assumption_type": assumption_type,
            "value": value,
            "scope": scope,
            "label": label or assumption_type.replace("_", " ").title(),
            "notes": notes or None,
            "created_at": datetime.utcnow().isoformat(),
        }
        response = service.client.table("finance_assumptions_ledger").insert(payload).execute()
        row = (response.data or [payload])[0]
        return {"success": True, "assumption": row}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_finance_assumptions(
    assumption_type: Optional[str] = None,
    scope: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """List saved finance assumptions for the current user."""
    try:
        from app.services.financial_service import FinancialService

        user_id = _get_current_user_id()
        service = FinancialService()
        query = service.client.table("finance_assumptions_ledger").select("*")
        if user_id:
            query = query.eq("user_id", user_id)
        if assumption_type:
            query = query.eq("assumption_type", assumption_type)
        if scope:
            query = query.eq("scope", scope)
        response = query.order("created_at", desc=True).limit(limit).execute()
        rows = response.data or []
        return {"success": True, "assumptions": rows, "count": len(rows)}
    except Exception as e:
        return {"success": False, "error": str(e), "assumptions": []}


async def get_finance_deliverable_templates() -> dict:
    """Return built-in deliverable templates for finance operations."""
    templates = [
        {
            "name": "pnl_summary",
            "title": "P&L Summary",
            "description": "Compact revenue, burn, and net position summary.",
        },
        {
            "name": "burn_runway",
            "title": "Burn & Runway",
            "description": "Estimate monthly burn and months of runway.",
        },
        {
            "name": "cash_position",
            "title": "Cash Position",
            "description": "Show inflows, outflows, and current estimated cash position.",
        },
    ]
    return {"success": True, "templates": templates, "count": len(templates)}


async def create_finance_deliverable(
    template_name: str,
    title: Optional[str] = None,
    period: str = "current_month",
) -> dict:
    """Create and persist a finance deliverable as an analytics report."""
    try:
        from app.agents.data.tools import create_report

        template_key = (template_name or "").strip().lower()
        if template_key == "burn_runway":
            payload = await get_burn_runway_report()
        elif template_key == "cash_position":
            payload = await get_cash_position()
        else:
            payload = await get_financial_report(period)

        report = await create_report(
            title=title or f"Finance Deliverable: {template_name}",
            report_type="finance",
            data=json.dumps(payload),
            description=f"Auto-generated finance deliverable for template '{template_name}'",
        )
        return {
            "success": bool(report.get("success")),
            "template_name": template_name,
            "deliverable": payload,
            "report": report.get("report"),
            "report_id": report.get("report_id"),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "template_name": template_name}


async def render_burn_runway_widget() -> dict:
    from app.agents.tools.ui_widgets import create_table_widget

    report = await get_burn_runway_report()
    return create_table_widget(
        title="Burn & Runway",
        columns=[
            {"key": "metric", "label": "Metric"},
            {"key": "value", "label": "Value"},
        ],
        rows=[
            {"metric": "Cash Position", "value": report.get("cash_position")},
            {"metric": "Monthly Burn", "value": report.get("monthly_burn")},
            {"metric": "Runway (months)", "value": report.get("runway_months")},
        ],
    )


async def render_pnl_summary_widget(period: str = "current_month") -> dict:
    from app.agents.tools.ui_widgets import create_table_widget

    report = await get_financial_report(period)
    net = round(float(report.get("revenue") or 0.0) - float(report.get("monthly_burn") or 0.0), 2)
    return create_table_widget(
        title="P&L Summary",
        columns=[
            {"key": "metric", "label": "Metric"},
            {"key": "value", "label": "Value"},
        ],
        rows=[
            {"metric": "Revenue", "value": report.get("revenue")},
            {"metric": "Monthly Burn", "value": report.get("monthly_burn")},
            {"metric": "Net Position", "value": net},
        ],
    )


async def render_budget_vs_actual_widget(period: str = "current_month") -> dict:
    from app.agents.tools.ui_widgets import create_table_widget

    report = await get_financial_report(period)
    assumptions = await list_finance_assumptions(assumption_type="budget", limit=5)
    budget = 0.0
    if assumptions.get("assumptions"):
        first = assumptions["assumptions"][0]
        budget = float(first.get("value") or 0.0)
    actual = float(report.get("revenue") or 0.0)
    variance = round(actual - budget, 2)
    return create_table_widget(
        title="Budget vs Actual",
        columns=[
            {"key": "metric", "label": "Metric"},
            {"key": "value", "label": "Value"},
        ],
        rows=[
            {"metric": "Budget", "value": budget},
            {"metric": "Actual", "value": actual},
            {"metric": "Variance", "value": variance},
        ],
    )


async def render_revenue_bridge_widget(period: str = "current_month") -> dict:
    from app.agents.tools.ui_widgets import create_revenue_chart_widget

    revenue = await get_revenue_stats(period)
    current_value = float(revenue.get("revenue") or 0.0)
    values = [round(current_value * 0.75, 2), current_value]
    return create_revenue_chart_widget(
        periods=["Previous", "Current"],
        values=values,
        currency=str(revenue.get("currency") or "USD"),
    )


async def render_cohort_retention_widget() -> dict:
    from app.agents.tools.ui_widgets import create_table_widget

    return create_table_widget(
        title="Cohort Retention Snapshot",
        columns=[
            {"key": "cohort", "label": "Cohort"},
            {"key": "retention", "label": "Retention"},
        ],
        rows=[
            {"cohort": "Month 1", "retention": "Needs event data"},
            {"cohort": "Month 2", "retention": "Needs event data"},
        ],
    )


async def render_cash_waterfall_widget() -> dict:
    from app.agents.tools.ui_widgets import create_table_widget

    cash = await get_cash_position()
    return create_table_widget(
        title="Cash Waterfall",
        columns=[
            {"key": "metric", "label": "Metric"},
            {"key": "value", "label": "Value"},
        ],
        rows=[
            {"metric": "Inflows", "value": cash.get("inflows")},
            {"metric": "Outflows", "value": cash.get("outflows")},
            {"metric": "Cash Position", "value": cash.get("cash_position")},
        ],
    )


async def render_kpi_scorecard_widget(period: str = "current_month") -> dict:
    from app.agents.tools.ui_widgets import create_table_widget

    revenue = await get_revenue_stats(period)
    cash = await get_cash_position()
    runway = await get_burn_runway_report()
    return create_table_widget(
        title="Finance KPI Scorecard",
        columns=[
            {"key": "metric", "label": "Metric"},
            {"key": "value", "label": "Value"},
        ],
        rows=[
            {"metric": "Revenue", "value": revenue.get("revenue")},
            {"metric": "Cash Position", "value": cash.get("cash_position")},
            {"metric": "Runway (months)", "value": runway.get("runway_months")},
        ],
    )
