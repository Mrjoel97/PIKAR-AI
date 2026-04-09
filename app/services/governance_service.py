# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Governance service for enterprise audit trail, portfolio health, and approval chains.

Provides:
- Audit event logging to the governance_audit_log table (never raises).
- Portfolio health score computation from initiatives and compliance_risks data.
- Multi-level approval chain creation, decision recording, and status queries.

All database operations use the service-role client (bypasses RLS) with
execute_async for non-blocking execution.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Default three-step approval chain definition
_DEFAULT_CHAIN_STEPS = [
    {"step_order": 1, "role_label": "reviewer"},
    {"step_order": 2, "role_label": "approver"},
    {"step_order": 3, "role_label": "executive"},
]


class GovernanceService:
    """Service for governance audit logging, portfolio health, and approval chains.

    Uses the service-role Supabase client to bypass RLS. Business-logic
    permission checks are enforced in the calling router layer.
    """

    def __init__(self) -> None:
        """Initialise the service with the Supabase service client."""
        self.client = get_service_client()

    # ------------------------------------------------------------------
    # Audit logging (GOV-01)
    # ------------------------------------------------------------------

    async def log_event(
        self,
        user_id: str,
        action_type: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Insert a governance audit event.

        Uses the service-role client and NEVER raises — audit failures must
        not interrupt the calling operation. Errors are logged at ERROR level.

        Args:
            user_id: UUID of the user who performed the action.
            action_type: Dot-namespaced action label (e.g. 'initiative.created').
            resource_type: Resource category (e.g. 'initiative', 'workflow').
            resource_id: Identifier of the affected resource, or None.
            details: Extra JSONB context (old/new values, parameters, etc.).
            ip_address: Client IP for compliance purposes, or None.
        """
        row: dict[str, Any] = {
            "user_id": user_id,
            "action_type": action_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
        }
        try:
            await execute_async(
                self.client.table("governance_audit_log").insert(row),
                op_name="governance.log_event",
            )
            logger.debug(
                "Governance audit: user=%s action=%s resource=%s/%s",
                user_id,
                action_type,
                resource_type,
                resource_id,
            )
        except Exception as exc:
            logger.error(
                "Failed to write governance audit log action='%s' user='%s': %s",
                action_type,
                user_id,
                exc,
            )

    async def get_audit_log(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        action_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return paginated governance audit log rows for a user.

        Results are ordered by created_at DESC. An optional action_type filter
        restricts rows to a specific action category.

        Args:
            user_id: UUID of the user whose log to retrieve.
            limit: Maximum number of rows to return (default 50).
            offset: Row offset for pagination (default 0).
            action_type: Optional filter for a specific action_type value.

        Returns:
            List of audit log row dicts ordered newest-first.
        """
        query = (
            self.client.table("governance_audit_log")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if action_type is not None:
            query = query.eq("action_type", action_type)

        result = await execute_async(query, op_name="governance.audit_log")
        return result.data or []

    # ------------------------------------------------------------------
    # Portfolio health score (GOV-02)
    # ------------------------------------------------------------------

    async def compute_portfolio_health(self, user_id: str) -> dict[str, Any]:
        """Compute a weighted portfolio health score (0-100) for a user.

        Three weighted components plus three enrichment metrics are each computed
        independently; a failure in any single component returns 0 / empty data
        for that component without crashing the overall computation.

        Weighted components:
        - Initiative completion rate (40 %): completed / all active initiatives.
        - Risk coverage (30 %): initiatives with mitigation plans / all risks.
        - Resource allocation (30 %): initiatives with assigned owner / total.

        Enrichment (non-scoring):
        - Initiative breakdown: counts per status (in_progress, completed, blocked, not_started).
        - Workflow success rate: percentage of completed workflow_executions.
        - Revenue trend: current and prior month paid order amounts.

        Args:
            user_id: UUID of the user whose portfolio to evaluate.

        Returns:
            Dict with keys ``score`` (int 0-100) and ``components`` sub-dict
            containing ``initiative_completion``, ``risk_coverage``,
            ``resource_allocation``, ``initiative_breakdown``,
            ``workflow_success_rate``, and ``revenue_trend``.
        """
        from datetime import (
            UTC,
            datetime,
        )

        initiative_completion: float = 0.0
        risk_coverage: float = 0.0
        resource_allocation: float = 0.0
        initiative_breakdown: dict[str, int] = {
            "in_progress": 0,
            "completed": 0,
            "blocked": 0,
            "not_started": 0,
            "total": 0,
        }
        workflow_success_rate: int = 0
        current_rev: float = 0.0
        prior_rev: float = 0.0

        # --- Initiative completion rate (40%) + breakdown ---
        try:
            active_statuses = ("in_progress", "blocked", "not_started", "completed")
            init_result = await execute_async(
                self.client.table("initiatives")
                .select("id, status")
                .eq("user_id", user_id)
                .in_("status", list(active_statuses)),
                op_name="governance.health_initiatives",
            )
            rows = init_result.data or []
            total_active = len(rows)
            initiative_breakdown["total"] = total_active
            for r in rows:
                status = r.get("status", "")
                if status in initiative_breakdown:
                    initiative_breakdown[status] += 1
            if total_active > 0:
                completed_count = initiative_breakdown["completed"]
                initiative_completion = (completed_count / total_active) * 100.0
        except Exception as exc:
            logger.error("governance.compute_portfolio_health initiative query failed: %s", exc)

        # --- Risk coverage (30%) ---
        try:
            risk_result = await execute_async(
                self.client.table("compliance_risks")
                .select("id, mitigation_plan")
                .eq("user_id", user_id),
                op_name="governance.health_risks",
            )
            risk_rows = risk_result.data or []
            total_risks = len(risk_rows)
            if total_risks > 0:
                covered = sum(
                    1 for r in risk_rows if r.get("mitigation_plan") is not None
                )
                risk_coverage = (covered / total_risks) * 100.0
        except Exception as exc:
            logger.error("governance.compute_portfolio_health risk query failed: %s", exc)

        # --- Resource allocation (30%) ---
        try:
            alloc_result = await execute_async(
                self.client.table("initiatives")
                .select("id, owner_user_id")
                .eq("user_id", user_id),
                op_name="governance.health_allocation",
            )
            alloc_rows = alloc_result.data or []
            total_initiatives = len(alloc_rows)
            if total_initiatives > 0:
                assigned = sum(
                    1 for r in alloc_rows if r.get("owner_user_id") is not None
                )
                resource_allocation = (assigned / total_initiatives) * 100.0
        except Exception as exc:
            logger.error("governance.compute_portfolio_health allocation query failed: %s", exc)

        # --- Workflow success rate (enrichment only — not weighted) ---
        try:
            wf_result = await execute_async(
                self.client.table("workflow_executions")
                .select("id, status")
                .eq("user_id", user_id),
                op_name="governance.health_workflow_success",
            )
            wf_rows = wf_result.data or []
            total_wf = len(wf_rows)
            if total_wf > 0:
                completed_wf = sum(1 for r in wf_rows if r.get("status") == "completed")
                workflow_success_rate = round(completed_wf / total_wf * 100)
        except Exception as exc:
            logger.error("governance.compute_portfolio_health workflow query failed: %s", exc)

        # --- Revenue trend (enrichment only — not weighted) ---
        try:
            now = datetime.now(UTC)
            # Current month: from 1st of current month
            current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Prior month: from 1st of prior month to start of current month
            if now.month == 1:
                prior_month_start = now.replace(
                    year=now.year - 1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0
                )
            else:
                prior_month_start = now.replace(
                    month=now.month - 1, day=1, hour=0, minute=0, second=0, microsecond=0
                )

            curr_result = await execute_async(
                self.client.table("orders")
                .select("amount")
                .eq("user_id", user_id)
                .eq("status", "paid")
                .gte("created_at", current_month_start.isoformat()),
                op_name="governance.health_revenue_current",
            )
            current_rev = sum(float(r.get("amount", 0)) for r in (curr_result.data or []))

            prior_result = await execute_async(
                self.client.table("orders")
                .select("amount")
                .eq("user_id", user_id)
                .eq("status", "paid")
                .gte("created_at", prior_month_start.isoformat())
                .lt("created_at", current_month_start.isoformat()),
                op_name="governance.health_revenue_prior",
            )
            prior_rev = sum(float(r.get("amount", 0)) for r in (prior_result.data or []))
        except Exception as exc:
            logger.error("governance.compute_portfolio_health revenue query failed: %s", exc)

        score = round(
            initiative_completion * 0.40
            + risk_coverage * 0.30
            + resource_allocation * 0.30
        )

        return {
            "score": score,
            "components": {
                "initiative_completion": round(initiative_completion, 1),
                "risk_coverage": round(risk_coverage, 1),
                "resource_allocation": round(resource_allocation, 1),
                "initiative_breakdown": initiative_breakdown,
                "workflow_success_rate": workflow_success_rate,
                "revenue_trend": {
                    "current_month": round(current_rev, 2),
                    "prior_month": round(prior_rev, 2),
                },
            },
        }

    # ------------------------------------------------------------------
    # Approval chain management (GOV-04)
    # ------------------------------------------------------------------

    async def create_approval_chain(
        self,
        user_id: str,
        action_type: str,
        resource_id: str | None = None,
        resource_label: str | None = None,
        steps: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create an approval chain with its steps.

        If ``steps`` is not provided, a default three-step chain is created
        (reviewer → approver → executive). Custom steps must be a list of
        dicts with a ``role_label`` key and an optional ``approver_user_id``.

        Args:
            user_id: UUID of the user requesting the action.
            action_type: Category of action requiring approval (e.g. 'data_export').
            resource_id: Identifier of the resource the action targets, or None.
            resource_label: Human-readable label for display, or None.
            steps: Custom step definitions, or None to use the 3-step default.

        Returns:
            The created chain dict including a nested ``steps`` list.
        """
        chain_row: dict[str, Any] = {
            "user_id": user_id,
            "action_type": action_type,
            "resource_id": resource_id,
            "resource_label": resource_label,
            "status": "pending",
        }
        chain_result = await execute_async(
            self.client.table("approval_chains")
            .insert(chain_row)
            .select("*"),
            op_name="governance.create_chain",
        )
        chain = (chain_result.data or [{}])[0]
        chain_id = chain["id"]

        step_definitions = steps if steps else _DEFAULT_CHAIN_STEPS
        step_rows = [
            {
                "chain_id": chain_id,
                "step_order": idx + 1 if steps else s["step_order"],
                "role_label": s["role_label"],
                "approver_user_id": s.get("approver_user_id"),
                "status": "pending",
            }
            for idx, s in enumerate(step_definitions)
        ]
        steps_result = await execute_async(
            self.client.table("approval_chain_steps").insert(step_rows).select("*"),
            op_name="governance.create_chain_steps",
        )
        chain["steps"] = steps_result.data or []

        logger.info(
            "Created approval chain=%s type=%s user=%s steps=%d",
            chain_id,
            action_type,
            user_id,
            len(chain["steps"]),
        )
        return chain

    async def get_pending_chains(self, user_id: str) -> list[dict[str, Any]]:
        """Return all pending approval chains owned by a user, with steps.

        Args:
            user_id: UUID of the user whose pending chains to retrieve.

        Returns:
            List of chain dicts each containing a nested ``steps`` list,
            ordered by created_at DESC.
        """
        chains_result = await execute_async(
            self.client.table("approval_chains")
            .select("*")
            .eq("user_id", user_id)
            .eq("status", "pending")
            .order("created_at", desc=True),
            op_name="governance.pending_chains",
        )
        chains = chains_result.data or []
        if not chains:
            return []

        chain_ids = [c["id"] for c in chains]
        steps_result = await execute_async(
            self.client.table("approval_chain_steps")
            .select("*")
            .in_("chain_id", chain_ids)
            .order("step_order"),
            op_name="governance.pending_chains_steps",
        )
        steps_by_chain: dict[str, list[dict[str, Any]]] = {}
        for step in steps_result.data or []:
            steps_by_chain.setdefault(step["chain_id"], []).append(step)

        for chain in chains:
            chain["steps"] = steps_by_chain.get(chain["id"], [])
        return chains

    async def decide_step(
        self,
        chain_id: str,
        step_order: int,
        approver_user_id: str,
        decision: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Record a decision on a single approval chain step.

        Updates the step status and cascades to the parent chain:
        - ``rejected``: chain is immediately resolved as rejected.
        - ``approved`` on the last step: chain is resolved as approved.
        - ``approved`` on an intermediate step: chain stays pending.

        An audit event is written regardless of the chain outcome.

        Args:
            chain_id: UUID of the parent approval chain.
            step_order: The step number being decided.
            approver_user_id: UUID of the user recording the decision.
            decision: Either ``'approved'`` or ``'rejected'``.
            comment: Optional justification text.

        Returns:
            The updated chain dict including all steps.
        """
        now_iso = datetime.now(UTC).isoformat()

        # Update the step
        await execute_async(
            self.client.table("approval_chain_steps")
            .update(
                {
                    "status": decision,
                    "decided_at": now_iso,
                    "approver_user_id": approver_user_id,
                    "comment": comment,
                }
            )
            .eq("chain_id", chain_id)
            .eq("step_order", step_order),
            op_name="governance.decide_step_update",
        )

        # Determine whether to resolve the parent chain
        if decision == "rejected":
            await execute_async(
                self.client.table("approval_chains")
                .update({"status": "rejected", "resolved_at": now_iso})
                .eq("id", chain_id),
                op_name="governance.decide_step_reject_chain",
            )
        elif decision == "approved":
            # Check if this is the last step
            steps_result = await execute_async(
                self.client.table("approval_chain_steps")
                .select("step_order")
                .eq("chain_id", chain_id)
                .order("step_order", desc=True)
                .limit(1),
                op_name="governance.decide_step_max_order",
            )
            max_order = (steps_result.data or [{}])[0].get("step_order", 0)
            if step_order >= max_order:
                await execute_async(
                    self.client.table("approval_chains")
                    .update({"status": "approved", "resolved_at": now_iso})
                    .eq("id", chain_id),
                    op_name="governance.decide_step_approve_chain",
                )

        # Audit log the decision (non-raising)
        await self.log_event(
            user_id=approver_user_id,
            action_type="approval.decided",
            resource_type="approval_chain",
            resource_id=chain_id,
            details={"step_order": step_order, "decision": decision, "comment": comment},
        )

        return await self.get_chain_status(chain_id) or {}

    async def get_chain_status(self, chain_id: str) -> dict[str, Any] | None:
        """Return an approval chain with all its steps, or None if not found.

        Args:
            chain_id: UUID of the approval chain to retrieve.

        Returns:
            Chain dict with nested ``steps`` list, or None if not found.
        """
        chain_result = await execute_async(
            self.client.table("approval_chains").select("*").eq("id", chain_id),
            op_name="governance.chain_status",
        )
        rows = chain_result.data or []
        if not rows:
            return None
        chain = rows[0]

        steps_result = await execute_async(
            self.client.table("approval_chain_steps")
            .select("*")
            .eq("chain_id", chain_id)
            .order("step_order"),
            op_name="governance.chain_status_steps",
        )
        chain["steps"] = steps_result.data or []
        return chain


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_governance_service_instance: GovernanceService | None = None


def get_governance_service() -> GovernanceService:
    """Return the module-level GovernanceService singleton.

    Creates the instance on first call. Thread-safe for async contexts
    (single event loop; no concurrent init race).

    Returns:
        The shared GovernanceService instance.
    """
    global _governance_service_instance
    if _governance_service_instance is None:
        _governance_service_instance = GovernanceService()
    return _governance_service_instance
