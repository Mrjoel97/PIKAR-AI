# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Operations Analysis Tools for the Operations Agent.

Agent-callable tools that wrap WorkflowBottleneckService for bottleneck
detection and workflow health reporting, plus SOP document generation.

Follows the sync-wrapper pattern from inventory.py — uses asyncio event loop
to call async service methods from the synchronous ADK tool interface.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SOP Generation helpers
# ---------------------------------------------------------------------------


def _format_sop_as_text(sop: dict[str, Any]) -> str:
    """Format a SOP dict as a readable markdown document.

    Args:
        sop: Structured SOP dict from generate_sop_document.

    Returns:
        Markdown-formatted SOP string suitable for chat response.
    """
    lines: list[str] = []

    lines.append(f"# {sop['title']}")
    lines.append(f"\n**Document ID:** {sop['document_id']}")
    lines.append(f"**Version:** {sop['version']}")
    lines.append(f"**Effective Date:** {sop['effective_date']}")
    lines.append(f"**Department:** {sop['department']}")

    lines.append("\n---\n")
    lines.append("## Purpose")
    lines.append(sop["purpose"])

    lines.append("\n## Scope")
    scope = sop["scope"]
    applies = ", ".join(scope["applies_to"])
    lines.append(f"**Applies to:** {applies}")
    lines.append(f"**Triggered when:** {scope['triggers']}")

    lines.append("\n## Procedure")
    for step in sop["procedure"]:
        lines.append(
            f"{step['step_number']}. **{step['action']}**  "
            f"*(Responsible: {step['responsible']})*"
        )

    lines.append("\n## Quality Checks")
    for check in sop["quality_checks"]:
        lines.append(f"- {check}")

    lines.append("\n## Revision History")
    lines.append("| Version | Date | Author | Changes |")
    lines.append("|---------|------|--------|---------|")
    for rev in sop["revision_history"]:
        lines.append(
            f"| {rev['version']} | {rev['date']} | {rev['author']} | {rev['changes']} |"
        )

    return "\n".join(lines)


def analyze_workflow_bottlenecks(user_id: str, days: int = 30) -> dict:
    """Analyze workflow execution data to find bottlenecks and generate recommendations.

    Returns step-level performance stats, bottleneck flags, and plain-English
    recommendations for the user. Steps averaging more than 24 hours, failing
    more than 20% of the time, or stuck waiting for approval for more than 48
    hours are flagged as bottlenecks.

    Args:
        user_id: Authenticated user identifier.
        days: Look-back window in days. Defaults to 30.

    Returns:
        dict with step_stats, bottleneck_count, recommendations, period_days.
    """
    from app.services.workflow_bottleneck_service import WorkflowBottleneckService

    service = WorkflowBottleneckService()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(service.analyze_bottlenecks(user_id, days))


def get_workflow_health(user_id: str) -> dict:
    """Get overall workflow health summary including completion rate, average execution time, and top bottleneck recommendations.

    Returns a high-level overview of how well workflows are running for the
    user: what fraction complete successfully, how long they take on average,
    and the top three issues to address.

    Args:
        user_id: Authenticated user identifier.

    Returns:
        dict with total_executions, completion_rate, avg_execution_hours,
        top_bottlenecks (up to 3), and period_days.
    """
    from app.services.workflow_bottleneck_service import WorkflowBottleneckService

    service = WorkflowBottleneckService()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(service.get_workflow_health_summary(user_id))


# ---------------------------------------------------------------------------
# SOP Generation Tool
# ---------------------------------------------------------------------------


def generate_sop_document(
    process_name: str,
    process_description: str,
    steps: list[str],
    roles: list[str] | None = None,
    department: str = "Operations",
) -> dict[str, Any]:
    """Generate a formal Standard Operating Procedure (SOP) document from a process description.

    Returns a structured SOP with purpose, scope, roles, numbered procedure
    steps, quality checks, and an option to create a workflow template from it.

    Args:
        process_name: Short name of the process (e.g., "Customer Complaint Handling").
        process_description: Narrative description of what the process does and why.
        steps: Ordered list of procedure step descriptions.
        roles: Optional list of role names responsible for each step. If provided,
            roles are assigned cyclically to procedure steps. If omitted, all
            steps default to "Assigned team member".
        department: Department that owns this SOP (default "Operations").

    Returns:
        Dict with keys:

        - ``status``: ``"success"`` or ``"error"``
        - ``sop``: Structured SOP dict with all standard sections.
        - ``formatted_text``: Markdown-formatted SOP for direct inclusion in a response.
        - ``suggestion``: Offer to create a workflow template from the SOP steps.
    """
    try:
        now = datetime.now(tz=timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%Y%m%d%H%M%S")

        # Build department prefix (first 3 uppercase chars, stripped of spaces)
        dept_prefix = department.upper().replace(" ", "")[:3]
        document_id = f"SOP-{dept_prefix}-{timestamp}"

        # Build procedure steps with role assignment
        procedure: list[dict[str, Any]] = []
        for i, step in enumerate(steps):
            if roles:
                responsible = roles[i % len(roles)]
            else:
                responsible = "Assigned team member"
            procedure.append(
                {
                    "step_number": i + 1,
                    "action": step,
                    "responsible": responsible,
                }
            )

        sop: dict[str, Any] = {
            "document_id": document_id,
            "title": f"{process_name} Standard Operating Procedure",
            "version": "1.0",
            "effective_date": today_str,
            "department": department,
            "purpose": process_description,
            "scope": {
                "applies_to": roles or ["All team members"],
                "triggers": f"When {process_name.lower()} needs to be performed",
            },
            "procedure": procedure,
            "quality_checks": [
                "Verify all steps completed in order",
                "Confirm outputs match expected results",
                "Document any deviations from procedure",
            ],
            "revision_history": [
                {
                    "version": "1.0",
                    "date": today_str,
                    "author": "Operations Agent",
                    "changes": "Initial creation",
                }
            ],
        }

        return {
            "status": "success",
            "sop": sop,
            "formatted_text": _format_sop_as_text(sop),
            "suggestion": (
                "I can create a workflow template from this SOP so it can be "
                "tracked automatically. Would you like me to do that?"
            ),
        }

    except Exception as exc:
        logger.exception("SOP generation failed for process: %s", process_name)
        return {"status": "error", "message": f"SOP generation failed: {exc}"}


# ---------------------------------------------------------------------------
# Vendor / SaaS Cost Tracking Tools
# ---------------------------------------------------------------------------


def track_vendor_subscription(
    user_id: str,
    name: str,
    category: str,
    monthly_cost: float,
    billing_cycle: str = "monthly",
    renewal_date: str | None = None,
    trial_end_date: str | None = None,
    notes: str | None = None,
) -> dict:
    """Add or track a SaaS subscription or vendor cost.

    Categories: project_management, communication, analytics, marketing,
    design, development, crm, accounting, storage, security, other.

    Args:
        user_id: Authenticated user identifier.
        name: Display name for the subscription (e.g. "Slack", "GitHub").
        category: Subscription category from the list above.
        monthly_cost: Equivalent monthly cost in user's currency.
        billing_cycle: One of "monthly", "quarterly", "annual".
        renewal_date: Next renewal or billing date (ISO date string, e.g. "2026-06-01").
        trial_end_date: Trial expiry date (ISO date string, e.g. "2026-05-01").
        notes: Optional free-text notes about the subscription.

    Returns:
        dict with the saved subscription record.
    """
    from app.services.vendor_cost_service import VendorCostService

    service = VendorCostService()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        service.add_subscription(
            user_id=user_id,
            name=name,
            category=category,
            monthly_cost=monthly_cost,
            billing_cycle=billing_cycle,
            renewal_date=renewal_date,
            trial_end_date=trial_end_date,
            notes=notes,
        )
    )


def list_vendor_costs(user_id: str) -> dict:
    """List all tracked SaaS subscriptions and vendor costs with total monthly spend, category breakdown, trial expiry warnings, and consolidation suggestions.

    Returns a consolidated view of all active subscriptions grouped by category,
    the total monthly and annual spend, any trials expiring in the next 7 days,
    and plain-English consolidation suggestions when the user has multiple tools
    in the same category.

    Args:
        user_id: Authenticated user identifier.

    Returns:
        dict with total_monthly, total_annual_estimate, by_category, trial_expiring,
        and consolidation_suggestions.
    """
    from app.services.vendor_cost_service import VendorCostService

    service = VendorCostService()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(service.get_cost_summary(user_id))


# ---------------------------------------------------------------------------
# Shopify Inventory Alert Tools
# ---------------------------------------------------------------------------


def check_shopify_inventory(user_id: str) -> dict:
    """Check Shopify inventory levels and return products that are below their configured stock threshold.

    Also triggers reorder alert notifications for low-stock items so the user
    receives a warning in their notification feed.

    Args:
        user_id: Authenticated user identifier (must have Shopify connected).

    Returns:
        dict with low_stock_products (list), alerts_sent (int), and suggestion (str).
    """
    from app.services.shopify_service import ShopifyService

    service = ShopifyService()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        low_stock = loop.run_until_complete(service.get_low_stock_products(user_id))
        alerts_sent = loop.run_until_complete(service.check_inventory_alerts(user_id))
    except Exception as exc:
        logger.exception("Shopify inventory check failed for user %s", user_id)
        return {"status": "error", "message": str(exc)}

    suggestion = ""
    if low_stock:
        names = [p.get("title", "Unknown") for p in low_stock[:3]]
        more = len(low_stock) - 3
        name_list = ", ".join(names)
        if more > 0:
            name_list += f" and {more} more"
        suggestion = (
            f"Consider reordering: {name_list}. "
            "Review recent sales velocity to determine optimal reorder quantities."
        )
    else:
        suggestion = "All products are above their configured stock thresholds."

    return {
        "low_stock_products": low_stock,
        "alerts_sent": alerts_sent,
        "suggestion": suggestion,
    }


def set_inventory_threshold(user_id: str, product_id: str, threshold: int) -> dict:
    """Set the low-stock alert threshold for a specific Shopify product.

    When inventory drops below this number, you'll receive an alert in your
    notification feed and the Operations Agent will proactively notify you.

    Args:
        user_id: Authenticated user identifier.
        product_id: UUID of the Shopify product row to configure.
        threshold: New minimum stock level that triggers an alert.

    Returns:
        dict with the updated product row or confirmation.
    """
    from app.services.shopify_service import ShopifyService

    service = ShopifyService()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            service.set_alert_threshold(user_id, product_id, threshold)
        )
    except Exception as exc:
        logger.exception(
            "set_alert_threshold failed for user %s product %s", user_id, product_id
        )
        return {"status": "error", "message": str(exc)}

    return {**result, "status": "success", "threshold_set": threshold}


OPS_ANALYSIS_TOOLS = [
    analyze_workflow_bottlenecks,
    get_workflow_health,
    generate_sop_document,
    track_vendor_subscription,
    list_vendor_costs,
    check_shopify_inventory,
    set_inventory_threshold,
]
