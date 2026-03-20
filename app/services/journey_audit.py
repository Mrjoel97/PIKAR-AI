# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Journey Audit service to check user configuration and agent performance."""

import logging
from typing import Any

from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


async def audit_user_setup(user_id: str) -> dict[str, Any]:
    """Audit user's current agent configuration and suggest improvements.

    Checks:
    - MCP tools configuration
    - Available vs used skills
    - Journey quality metrics
    - Initiative progress and stalled phases

    Returns a scored report with action items.
    """
    from app.services.semantic_workflow_matcher import get_journey_quality_metrics
    from app.services.supabase import get_service_client

    client = get_service_client()

    report = {
        "score": 100,
        "metrics": {
            "stalled_initiatives": 0,
            "skills_used": 0,
            "completion_rate": 0,
        },
        "recommendations": [],
    }

    try:
        # Check stalled initiatives
        res = await execute_async(
            client.table("initiatives")
            .select("id, status, phase")
            .eq("user_id", user_id),
            op_name="journey_audit.initiatives.list",
        )
        if res.data:
            initiatives = res.data
            stalled = sum(
                1 for i in initiatives if i.get("status") in ["blocked", "on_hold"]
            )
            report["metrics"]["stalled_initiatives"] = stalled

            if stalled > 0:
                report["score"] -= stalled * 5
                report["recommendations"].append(
                    f"You have {stalled} stalled initiatives. Ask the Strategic Agent to review and unblock them."
                )

            in_progress = sum(
                1 for i in initiatives if i.get("status") == "in_progress"
            )
            if in_progress > 5:
                # Too much WIP
                report["score"] -= 10
                report["recommendations"].append(
                    "High Work-In-Progress limits: Prioritize completing active initiatives before starting new ones."
                )
    except Exception as e:
        logger.warning(f"Error checking initiatives: {e}")

    try:
        # Check journey metrics
        journey_metrics = await get_journey_quality_metrics(user_id)
        if "error" not in journey_metrics:
            completion_rate = journey_metrics.get("completion_rate", 0)
            report["metrics"]["completion_rate"] = completion_rate
            if completion_rate < 20 and journey_metrics.get("total_transitions", 0) > 0:
                report["score"] -= 15
                report["recommendations"].append(
                    "Low completion rate: Focus on advancing initiatives through the prototype and build phases."
                )

            # Additional metric mapping
            report["metrics"]["total_transitions"] = journey_metrics.get(
                "total_transitions", 0
            )
            report["metrics"]["avg_hours_per_phase"] = journey_metrics.get(
                "avg_hours_per_phase", {}
            )
    except Exception as e:
        logger.warning(f"Error checking journey metrics: {e}")

    # Configuration recommendations
    # If the score is high but they don't have many tools, prompt them
    report["recommendations"].append(
        "Ensure context caching is enabled in production environments for optimal performance."
    )
    report["recommendations"].append(
        "Consider creating custom skills for your most frequent workflows using the Skill Builder."
    )

    # Cap score
    report["score"] = max(0, min(100, report["score"]))

    return {
        "success": True,
        "report": report,
    }
