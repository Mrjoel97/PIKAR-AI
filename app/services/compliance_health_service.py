# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""ComplianceHealthService -- Compliance Health Score (0-100).

Computes a composite health score from the user's active risks,
overdue audits, and overdue compliance deadlines.  Returns a
plain-English explanation of what is driving the score so users
can see compliance posture at a glance (LEGAL-01).

Used by the ``get_compliance_health_score`` agent tool.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.base_service import BaseService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Severity deduction map
# ---------------------------------------------------------------------------

_SEVERITY_POINTS: dict[str, int] = {
    "critical": 20,
    "high": 15,
    "medium": 5,
    "low": 2,
}


class ComplianceHealthService(BaseService):
    """Service that computes a compliance health score for a user.

    The score starts at 100 and is reduced by:
    - Active risks (weighted by severity)
    - Overdue audits (scheduled_date in the past, not completed)
    - Overdue compliance deadlines (due_date in the past, not completed)

    All queries are user-scoped via RLS or explicit ``user_id`` filter.
    """

    _risks_table = "compliance_risks"
    _audits_table = "compliance_audits"
    _deadlines_table = "compliance_deadlines"

    def __init__(self, user_token: str | None = None) -> None:
        """Initialize the compliance health service.

        Args:
            user_token: JWT token from the authenticated user.
        """
        super().__init__(user_token)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def compute_health_score(self, user_id: str) -> dict[str, Any]:
        """Compute the compliance health score for a user.

        Args:
            user_id: The UUID of the user whose score to compute.

        Returns:
            Dictionary with keys:
            - score (int): 0-100 compliance health score.
            - explanation (str): Plain-English summary.
            - deductions (list[dict]): Individual deduction items.
            - factors (dict): Counts of each factor category.
        """
        score = 100
        deductions: list[dict[str, Any]] = []

        # 1. Active risks ------------------------------------------------
        risks = await self._fetch_active_risks(user_id)
        for risk in risks:
            severity = (risk.get("severity") or "medium").lower()
            points = _SEVERITY_POINTS.get(severity, 5)
            title = risk.get("title", "Unnamed risk")
            score -= points
            deductions.append(
                {
                    "category": "risk",
                    "severity": severity,
                    "title": title,
                    "points": points,
                    "reason": f"{severity}-severity risk: '{title}' (-{points})",
                }
            )

        # 2. Overdue audits -----------------------------------------------
        overdue_audits = await self._fetch_overdue_audits(user_id)
        for audit in overdue_audits:
            points = 10
            title = audit.get("title", "Unnamed audit")
            score -= points
            deductions.append(
                {
                    "category": "overdue_audit",
                    "title": title,
                    "points": points,
                    "reason": f"overdue audit: '{title}' (-{points})",
                }
            )

        # 3. Overdue deadlines --------------------------------------------
        overdue_deadlines = await self._fetch_overdue_deadlines(user_id)
        for deadline in overdue_deadlines:
            points = 10
            title = deadline.get("title", "Unnamed deadline")
            score -= points
            deductions.append(
                {
                    "category": "overdue_deadline",
                    "title": title,
                    "points": points,
                    "reason": f"overdue deadline: '{title}' (-{points})",
                }
            )

        # 4. Clamp --------------------------------------------------------
        score = max(0, min(100, score))

        # 5. Build explanation --------------------------------------------
        explanation = self._build_explanation(score, deductions)

        return {
            "score": score,
            "explanation": explanation,
            "deductions": deductions,
            "factors": {
                "active_risks": len(risks),
                "overdue_audits": len(overdue_audits),
                "overdue_deadlines": len(overdue_deadlines),
            },
        }

    # ------------------------------------------------------------------
    # Private query helpers
    # ------------------------------------------------------------------

    async def _fetch_active_risks(self, user_id: str) -> list[dict]:
        """Fetch active risks for the user.

        Args:
            user_id: The user UUID.

        Returns:
            List of active risk rows.
        """
        client = self.client
        query = (
            client.table(self._risks_table)
            .select("title,severity")
            .eq("user_id", user_id)
            .eq("status", "active")
        )
        response = await execute_async(query, op_name="health.risks")
        return response.data or []

    async def _fetch_overdue_audits(self, user_id: str) -> list[dict]:
        """Fetch overdue audits (scheduled_date < today, not completed).

        Args:
            user_id: The user UUID.

        Returns:
            List of overdue audit rows.
        """
        client = self.client
        query = (
            client.table(self._audits_table)
            .select("title,scheduled_date,status")
            .eq("user_id", user_id)
            .neq("status", "completed")
            .lt("scheduled_date", _today_iso())
        )
        response = await execute_async(query, op_name="health.overdue_audits")
        return response.data or []

    async def _fetch_overdue_deadlines(self, user_id: str) -> list[dict]:
        """Fetch overdue compliance deadlines (due_date < today, not completed).

        Args:
            user_id: The user UUID.

        Returns:
            List of overdue deadline rows.
        """
        client = self.client
        query = (
            client.table(self._deadlines_table)
            .select("title,due_date,status")
            .eq("user_id", user_id)
            .neq("status", "completed")
            .lt("due_date", _today_iso())
        )
        response = await execute_async(query, op_name="health.overdue_deadlines")
        return response.data or []

    # ------------------------------------------------------------------
    # Explanation builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_explanation(score: int, deductions: list[dict]) -> str:
        """Build a plain-English explanation of the score.

        Args:
            score: The computed 0-100 score.
            deductions: List of deduction dicts with 'reason' keys.

        Returns:
            Human-readable explanation string.
        """
        if not deductions:
            return (
                f"{score}/100 -- Excellent! No active compliance issues found. "
                "All audits are current, no unmitigated risks, and all deadlines are met."
            )

        reasons = [d["reason"] for d in deductions]
        summary = ", ".join(reasons)
        return f"{score}/100 -- {summary}"


def _today_iso() -> str:
    """Return today's date as an ISO string (YYYY-MM-DD).

    Returns:
        Today's date string.
    """
    from datetime import date

    return date.today().isoformat()
