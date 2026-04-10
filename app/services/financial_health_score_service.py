# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""FinancialHealthScoreService - Composite 0-100 financial health score.

Computes a weighted score from five factors:
  - Revenue trend (25%)
  - Runway months (25%)
  - Cash flow ratio (20%)
  - Invoice collection rate (15%)
  - Burn stability (15%)

Returns a color-coded score with a plain-English explanation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.agents.financial.tools import get_burn_runway_report, get_cash_position
from app.services.base_service import BaseService
from app.services.financial_service import FinancialService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Factor weights (must sum to 1.0)
WEIGHTS = {
    "revenue_trend": 0.25,
    "runway_months": 0.25,
    "cash_flow_ratio": 0.20,
    "collection_rate": 0.15,
    "burn_stability": 0.15,
}


def _score_revenue_trend(current: float, previous: float) -> float:
    """Score revenue trend 0-100 based on month-over-month growth.

    Args:
        current: Current month revenue.
        previous: Previous month revenue.

    Returns:
        Score from 0 to 100.
    """
    if previous <= 0 and current <= 0:
        return 0.0
    if previous <= 0:
        # Had no revenue last month, now have some -- strong growth signal
        return 100.0
    growth = (current - previous) / previous
    if growth >= 0.20:
        return 100.0
    if growth >= 0.10:
        return 85.0
    if growth >= 0.0:
        return 70.0
    if growth >= -0.10:
        return 50.0
    if growth >= -0.20:
        return 30.0
    return 10.0


def _score_runway(runway_months: float | None) -> float:
    """Score runway 0-100 based on months of runway remaining.

    Args:
        runway_months: Months of runway, or None if incalculable.

    Returns:
        Score from 0 to 100.
    """
    if runway_months is None:
        return 50.0  # Indeterminate -- no burn means no burn risk
    if runway_months >= 12:
        return 100.0
    if runway_months >= 6:
        return 70.0
    if runway_months >= 3:
        return 40.0
    return 10.0


def _score_cash_flow_ratio(inflows: float, outflows: float) -> float:
    """Score cash flow ratio 0-100 based on inflows/outflows.

    Args:
        inflows: Total inflows.
        outflows: Total outflows.

    Returns:
        Score from 0 to 100.
    """
    if outflows <= 0:
        return 100.0 if inflows > 0 else 50.0
    ratio = inflows / outflows
    if ratio >= 1.5:
        return 100.0
    if ratio >= 1.2:
        return 80.0
    if ratio >= 1.0:
        return 60.0
    if ratio >= 0.8:
        return 40.0
    if ratio >= 0.5:
        return 20.0
    return 10.0


def _score_collection_rate(paid: int, total: int) -> float:
    """Score invoice collection rate 0-100.

    Args:
        paid: Number of paid invoices.
        total: Total non-draft invoices.

    Returns:
        Score from 0 to 100.
    """
    if total <= 0:
        return 50.0  # No invoices -- neutral
    rate = paid / total
    if rate >= 0.90:
        return 100.0
    if rate >= 0.75:
        return 80.0
    if rate >= 0.60:
        return 60.0
    if rate >= 0.40:
        return 40.0
    return 20.0


def _score_burn_stability(burn: float, runway: float | None) -> float:
    """Score burn stability 0-100 based on burn rate relative to runway.

    Low burn with long runway is stable. High burn with short runway is unstable.

    Args:
        burn: Monthly burn rate.
        runway: Runway months, or None.

    Returns:
        Score from 0 to 100.
    """
    if burn <= 0:
        return 100.0  # No burn is maximally stable
    if runway is None:
        return 50.0
    if runway >= 12:
        return 100.0
    if runway >= 6:
        return 70.0
    if runway >= 3:
        return 40.0
    return 10.0


def _generate_explanation(score: int, color: str, factors: dict) -> str:
    """Generate a plain-English explanation of the financial health score.

    Args:
        score: The computed score (0-100).
        color: The color code (green/yellow/red).
        factors: Dict of individual factor scores.

    Returns:
        Human-readable explanation string.
    """
    parts: list[str] = []

    if color == "green":
        parts.append(f"Your financial health is strong (score: {score}/100).")
    elif color == "yellow":
        parts.append(
            f"Your financial health is moderate (score: {score}/100) and could use attention."
        )
    else:
        parts.append(
            f"Your financial health needs urgent attention (score: {score}/100)."
        )

    # Highlight strong factors
    strong = [k for k, v in factors.items() if v >= 70]
    if strong:
        labels = {
            "revenue_trend": "revenue is trending well",
            "runway_months": "you have healthy runway",
            "cash_flow_ratio": "cash flow is positive",
            "collection_rate": "invoice collection is solid",
            "burn_stability": "burn rate is stable",
        }
        strengths = [labels.get(k, k) for k in strong]
        parts.append("Strengths: " + ", ".join(strengths) + ".")

    # Highlight weak factors
    weak = [k for k, v in factors.items() if v < 40]
    if weak:
        labels = {
            "revenue_trend": "revenue is declining",
            "runway_months": "runway is critically low",
            "cash_flow_ratio": "cash outflows exceed inflows",
            "collection_rate": "invoice collection rate is low",
            "burn_stability": "burn rate is unsustainable",
        }
        concerns = [labels.get(k, k) for k in weak]
        parts.append("Concerns: " + ", ".join(concerns) + ".")

    return " ".join(parts)


def _check_insufficient_data(
    current_revenue: float,
    last_revenue: float,
    cash: float,
    inflows: float,
    outflows: float,
    burn: float,
    runway: float | None,
    total_invoices: int,
) -> bool:
    """Check if we have essentially no financial data to score.

    Returns True if data is insufficient for meaningful scoring.
    """
    no_revenue = current_revenue == 0 and last_revenue == 0
    no_cash = cash == 0 and inflows == 0 and outflows == 0
    no_burn = burn == 0 and runway is None
    no_invoices = total_invoices == 0
    return no_revenue and no_cash and no_burn and no_invoices


class FinancialHealthScoreService(BaseService):
    """Service for computing composite financial health scores.

    Aggregates data from revenue stats, cash position, burn/runway,
    and invoice collection into a single 0-100 score with color coding
    and plain-English explanation.
    """

    def __init__(self, user_token: str | None = None):
        """Initialize the financial health score service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)

    async def compute_health_score(self, user_id: str) -> dict:
        """Compute a composite financial health score for the user.

        Fetches revenue stats, cash position, burn/runway, and invoice
        collection data, then computes a weighted 0-100 score.

        Args:
            user_id: The user ID to compute the score for.

        Returns:
            Dict with score, color, explanation, factors, and computed_at.
        """
        # 1. Revenue trend: current vs last month
        fin_service = FinancialService()
        current_stats = await fin_service.get_revenue_stats("current_month")
        last_stats = await fin_service.get_revenue_stats("last_month")
        current_revenue = float(current_stats.get("revenue", 0))
        last_revenue = float(last_stats.get("revenue", 0))

        # 2. Cash position (inflows/outflows)
        cash_data = await get_cash_position()
        cash = float(cash_data.get("cash_position", 0))
        inflows = float(cash_data.get("inflows", 0))
        outflows = float(cash_data.get("outflows", 0))

        # 3. Burn & runway
        runway_data = await get_burn_runway_report()
        burn = float(runway_data.get("monthly_burn", 0))
        runway = runway_data.get("runway_months")
        if runway is not None:
            runway = float(runway)

        # 4. Invoice collection rate
        paid_count = 0
        total_count = 0
        try:
            query = self.client.table("invoices").select("id, status")
            query = query.eq("user_id", user_id)
            query = query.neq("status", "draft")
            response = await execute_async(query, op_name="invoices.collection_rate")
            rows = response.data or []
            total_count = len(rows)
            paid_count = sum(1 for r in rows if r.get("status") == "paid")
        except Exception as e:
            logger.warning("Failed to fetch invoice collection rate: %s", e)

        # Check for insufficient data
        if _check_insufficient_data(
            current_revenue, last_revenue, cash, inflows, outflows,
            burn, runway, total_count,
        ):
            return {
                "score": 50,
                "color": "yellow",
                "explanation": (
                    "Insufficient data to compute a meaningful financial health score. "
                    "Add financial records, invoices, and revenue data for an accurate assessment."
                ),
                "factors": {
                    "revenue_trend": 50.0,
                    "runway_months": 50.0,
                    "cash_flow_ratio": 50.0,
                    "collection_rate": 50.0,
                    "burn_stability": 50.0,
                },
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }

        # 5. Compute individual factor scores (each 0-100)
        factors = {
            "revenue_trend": _score_revenue_trend(current_revenue, last_revenue),
            "runway_months": _score_runway(runway),
            "cash_flow_ratio": _score_cash_flow_ratio(inflows, outflows),
            "collection_rate": _score_collection_rate(paid_count, total_count),
            "burn_stability": _score_burn_stability(burn, runway),
        }

        # 6. Weighted sum
        weighted_sum = sum(
            factors[k] * WEIGHTS[k] for k in WEIGHTS
        )
        score = max(0, min(100, round(weighted_sum)))

        # 7. Color coding
        if score >= 70:
            color = "green"
        elif score >= 40:
            color = "yellow"
        else:
            color = "red"

        # 8. Explanation
        explanation = _generate_explanation(score, color, factors)

        return {
            "score": score,
            "color": color,
            "explanation": explanation,
            "factors": factors,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def save_snapshot(self, user_id: str, result: dict) -> dict:
        """Persist a health score snapshot to the database.

        Args:
            user_id: The user ID.
            result: The compute_health_score result dict.

        Returns:
            The inserted row data.
        """
        payload = {
            "user_id": user_id,
            "score": result["score"],
            "color": result["color"],
            "explanation": result["explanation"],
            "factors": result["factors"],
            "computed_at": result.get("computed_at", datetime.now(timezone.utc).isoformat()),
        }
        response = await execute_async(
            self.client.table("financial_health_snapshots").insert(payload),
            op_name="financial_health_snapshots.insert",
        )
        return (response.data or [payload])[0]

    async def get_latest_snapshot(self, user_id: str) -> dict | None:
        """Retrieve the most recent health score snapshot for the user.

        Args:
            user_id: The user ID.

        Returns:
            The latest snapshot dict, or None if no snapshots exist.
        """
        response = await execute_async(
            self.client.table("financial_health_snapshots")
            .select("*")
            .eq("user_id", user_id)
            .order("computed_at", desc=True)
            .limit(1),
            op_name="financial_health_snapshots.latest",
        )
        rows = response.data or []
        return rows[0] if rows else None


def compute_health_score():
    """Module-level convenience reference for the service method.

    Note: Actual usage should instantiate FinancialHealthScoreService
    and call compute_health_score on the instance.
    """
    return FinancialHealthScoreService
