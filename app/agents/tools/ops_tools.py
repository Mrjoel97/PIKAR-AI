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


OPS_ANALYSIS_TOOLS = [
    analyze_workflow_bottlenecks,
    get_workflow_health,
    generate_sop_document,
]
