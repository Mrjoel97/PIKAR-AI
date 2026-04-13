# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""CustomerHealthService - Computes customer health dashboard metrics.

Aggregates ticket data into a health dashboard with open tickets,
resolution time, sentiment trends, and churn risk assessment.
"""

from __future__ import annotations

from app.services.support_ticket_service import SupportTicketService


class CustomerHealthService:
    """Computes customer health metrics from ticket data."""

    def __init__(self) -> None:
        """Initialize with a SupportTicketService instance."""
        self._ticket_service = SupportTicketService()

    async def get_health_dashboard(self, user_id: str | None = None) -> dict:
        """Get comprehensive customer health dashboard.

        Computes metrics from real ticket data using defined heuristics.

        Args:
            user_id: Optional user ID to scope the query.

        Returns:
            Dict with:
            - open_tickets: count of open tickets
            - avg_resolution_time_hours: average time to resolve (float or None)
            - sentiment_summary: {positive: N, neutral: N, negative: N}
            - churn_risk_level: 'low', 'medium', or 'high' based on heuristics
            - churn_risk_factors: list of strings explaining the risk assessment
            - total_tickets: total ticket count
            - resolution_rate: percentage of tickets resolved (float, 0.0-100.0)
        """
        stats = await self._ticket_service.get_ticket_stats(user_id=user_id)

        open_tickets: int = stats["open_count"]
        resolved_count: int = stats["resolved_count"]
        total_count: int = stats["total_count"]
        avg_resolution_hours: float | None = stats["avg_resolution_hours"]
        sentiment_breakdown: dict[str, int] = stats["sentiment_breakdown"]

        # Resolution rate as a percentage
        resolution_rate = (
            round(resolved_count / total_count * 100.0, 1) if total_count > 0 else 0.0
        )

        # Negative sentiment percentage
        negative_count = sentiment_breakdown.get("negative", 0)
        negative_pct = (
            (negative_count / total_count * 100.0) if total_count > 0 else 0.0
        )

        # Churn risk heuristics
        churn_risk_factors: list[str] = []
        high_risk = False
        medium_risk = False

        # HIGH risk checks
        if open_tickets > 5:
            high_risk = True
            churn_risk_factors.append(f"{open_tickets} unresolved tickets")
        if negative_pct > 50:
            high_risk = True
            churn_risk_factors.append(f"{negative_pct:.0f}% negative sentiment")
        if avg_resolution_hours is not None and avg_resolution_hours > 48:
            high_risk = True
            churn_risk_factors.append(
                f"Average resolution time {avg_resolution_hours:.1f}h (exceeds 48h threshold)"
            )

        # MEDIUM risk checks (only if not already high)
        if not high_risk:
            if open_tickets > 2:
                medium_risk = True
                churn_risk_factors.append(f"{open_tickets} unresolved tickets")
            if negative_pct > 30:
                medium_risk = True
                churn_risk_factors.append(f"{negative_pct:.0f}% negative sentiment")
            if avg_resolution_hours is not None and avg_resolution_hours > 24:
                medium_risk = True
                churn_risk_factors.append(
                    f"Average resolution time {avg_resolution_hours:.1f}h (exceeds 24h threshold)"
                )

        if high_risk:
            churn_risk_level = "high"
        elif medium_risk:
            churn_risk_level = "medium"
        else:
            churn_risk_level = "low"

        return {
            "open_tickets": open_tickets,
            "avg_resolution_time_hours": avg_resolution_hours,
            "sentiment_summary": sentiment_breakdown,
            "churn_risk_level": churn_risk_level,
            "churn_risk_factors": churn_risk_factors,
            "total_tickets": total_count,
            "resolution_rate": resolution_rate,
        }


__all__ = ["CustomerHealthService"]
