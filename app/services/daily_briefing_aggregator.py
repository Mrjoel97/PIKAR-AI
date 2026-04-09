# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Daily Briefing Aggregator.

Assembles the four sections of a proactive daily briefing:

1. **Pending approvals** -- count of approval_requests with status PENDING.
2. **KPI changes** -- comparison of latest two ``dashboard_summaries`` snapshots,
   reporting metrics with >5 % change.
3. **Stalled initiatives** -- initiatives in ``active``/``in_progress`` status
   that have not been updated in the last 7 days.
4. **Upcoming deadlines** -- tasks due within the next 7 days.

Usage::

    from app.services.daily_briefing_aggregator import aggregate_daily_briefing

    briefing = await aggregate_daily_briefing(user_id)
    # {
    #   "pending_approvals": 3,
    #   "kpi_changes": [...],
    #   "stalled_initiatives": [...],
    #   "upcoming_deadlines": [...],
    # }
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------


async def aggregate_daily_briefing(user_id: str) -> dict[str, Any]:
    """Aggregate all four briefing sections for a single user.

    Args:
        user_id: Supabase user ID.

    Returns:
        Dict with keys ``pending_approvals`` (int), ``kpi_changes`` (list),
        ``stalled_initiatives`` (list), and ``upcoming_deadlines`` (list).

    """
    client = get_service_client()
    now = datetime.now(timezone.utc)

    # --- 1. Pending approvals (count) ---
    approvals_result = await execute_async(
        client.table("approval_requests")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("status", "PENDING"),
        op_name="briefing.approvals_count",
    )
    pending_approvals: int = approvals_result.count or 0

    # --- 2. KPI changes (latest two dashboard snapshots) ---
    kpi_changes: list[dict[str, Any]] = []
    try:
        kpi_result = await execute_async(
            client.table("dashboard_summaries")
            .select("metrics,created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(2),
            op_name="briefing.kpi_snapshots",
        )
        kpi_rows = kpi_result.data or []
        if len(kpi_rows) >= 2:
            current_metrics: dict = kpi_rows[0].get("metrics") or {}
            previous_metrics: dict = kpi_rows[1].get("metrics") or {}
            kpi_changes = _compute_kpi_changes(current_metrics, previous_metrics)
    except Exception:
        logger.warning("Could not fetch KPI data for user %s", user_id)

    # --- 3. Stalled initiatives (not updated in 7+ days) ---
    stalled_initiatives: list[dict[str, Any]] = []
    try:
        cutoff = (now - timedelta(days=7)).isoformat()
        stalled_result = await execute_async(
            client.table("initiatives")
            .select("title,updated_at")
            .eq("user_id", user_id)
            .in_("status", ["active", "in_progress"])
            .lt("updated_at", cutoff),
            op_name="briefing.stalled_initiatives",
        )
        for row in stalled_result.data or []:
            updated_str = row.get("updated_at", "")
            if updated_str:
                updated_dt = datetime.fromisoformat(updated_str)
                days_stalled = (now - updated_dt).days
            else:
                days_stalled = 0
            stalled_initiatives.append(
                {"title": row.get("title", "Untitled"), "days_stalled": days_stalled}
            )
    except Exception:
        logger.warning("Could not fetch stalled initiatives for user %s", user_id)

    # --- 4. Upcoming deadlines (due within 7 days) ---
    upcoming_deadlines: list[dict[str, Any]] = []
    try:
        deadline_start = now.isoformat()
        deadline_end = (now + timedelta(days=7)).isoformat()
        deadlines_result = await execute_async(
            client.table("tasks")
            .select("title,due_date")
            .eq("user_id", user_id)
            .in_("status", ["pending", "in_progress"])
            .gte("due_date", deadline_start)
            .lte("due_date", deadline_end)
            .order("due_date"),
            op_name="briefing.upcoming_deadlines",
        )
        for row in deadlines_result.data or []:
            due_str = row.get("due_date", "")
            if due_str:
                due_dt = datetime.fromisoformat(due_str)
                days_until = max(0, (due_dt - now).days)
            else:
                days_until = 0
            upcoming_deadlines.append(
                {
                    "title": row.get("title", "Untitled"),
                    "due_date": due_str,
                    "days_until": days_until,
                }
            )
    except Exception:
        logger.warning("Could not fetch upcoming deadlines for user %s", user_id)

    return {
        "pending_approvals": pending_approvals,
        "kpi_changes": kpi_changes,
        "stalled_initiatives": stalled_initiatives,
        "upcoming_deadlines": upcoming_deadlines,
    }


# ---------------------------------------------------------------------------
# KPI helpers
# ---------------------------------------------------------------------------

_KPI_CHANGE_THRESHOLD = 0.05  # 5 %


def _compute_kpi_changes(
    current: dict[str, Any],
    previous: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare two metric snapshots and return significant changes.

    Only numeric metrics with >5 % delta are included.

    Args:
        current: Latest metrics dict.
        previous: Previous metrics dict.

    Returns:
        List of dicts with ``metric``, ``previous``, ``current``, ``direction``,
        and ``pct_change`` keys.

    """
    changes: list[dict[str, Any]] = []
    all_keys = set(current.keys()) | set(previous.keys())

    for key in sorted(all_keys):
        cur_val = current.get(key)
        prev_val = previous.get(key)

        # Skip non-numeric values
        if not isinstance(cur_val, (int, float)) or not isinstance(
            prev_val, (int, float)
        ):
            continue

        if prev_val == 0:
            if cur_val == 0:
                continue
            pct_change = 1.0  # 100 % change from zero
        else:
            pct_change = abs(cur_val - prev_val) / abs(prev_val)

        if pct_change < _KPI_CHANGE_THRESHOLD:
            continue

        if cur_val > prev_val:
            direction = "up"
        elif cur_val < prev_val:
            direction = "down"
        else:
            direction = "flat"

        changes.append(
            {
                "metric": key,
                "previous": prev_val,
                "current": cur_val,
                "direction": direction,
                "pct_change": round(pct_change * 100, 1),
            }
        )

    return changes


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def format_briefing_plain_text(briefing_data: dict[str, Any]) -> str:
    """Format aggregated briefing data into plain-text summary.

    Uses a casual but professional tone suitable for Slack/Teams/email.

    Args:
        briefing_data: Dict from ``aggregate_daily_briefing``.

    Returns:
        Human-readable plain-text string.

    """
    lines: list[str] = ["Good morning! Here's your business snapshot:\n"]

    # Pending approvals
    approvals = briefing_data.get("pending_approvals", 0)
    if approvals:
        lines.append(
            f"* {approvals} approval{'s' if approvals != 1 else ''} waiting for you"
        )

    # KPI changes
    for change in briefing_data.get("kpi_changes", []):
        metric = change["metric"].replace("_", " ").title()
        direction = "up" if change["direction"] == "up" else "down"
        lines.append(
            f"* {metric} is {direction} {change['pct_change']}% "
            f"from yesterday ({change['previous']} -> {change['current']})"
        )

    # Stalled initiatives
    stalled = briefing_data.get("stalled_initiatives", [])
    if stalled:
        count = len(stalled)
        lines.append(
            f"* {count} initiative{'s' if count != 1 else ''} "
            f"{'have' if count != 1 else 'has'}n't moved in over a week"
        )
        for item in stalled:
            lines.append(f"  - {item['title']} ({item['days_stalled']} days stalled)")

    # Upcoming deadlines
    deadlines = briefing_data.get("upcoming_deadlines", [])
    if deadlines:
        count = len(deadlines)
        lines.append(f"* {count} task{'s' if count != 1 else ''} due this week")
        for item in deadlines:
            lines.append(f"  - {item['title']} (in {item['days_until']} days)")

    if len(lines) == 1:
        lines.append("* Nothing urgent today -- all clear!")

    app_url = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
    lines.extend(
        [
            "",
            f"Open Pikar AI: {app_url}/dashboard",
            "",
            "---",
            "This briefing was generated by Pikar AI.",
            f"Manage preferences: {app_url}/settings/notifications",
        ]
    )

    return "\n".join(lines)


def format_briefing_blocks(briefing_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Format aggregated briefing data into Slack Block Kit blocks.

    Args:
        briefing_data: Dict from ``aggregate_daily_briefing``.

    Returns:
        List of Slack Block Kit block dicts.

    """
    blocks: list[dict[str, Any]] = []

    # Header
    blocks.append(
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Daily Business Briefing",
            },
        }
    )

    # Pending approvals
    approvals = briefing_data.get("pending_approvals", 0)
    if approvals:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Pending Approvals:* {approvals}",
                },
            }
        )

    # KPI changes
    kpi_changes = briefing_data.get("kpi_changes", [])
    if kpi_changes:
        kpi_lines = ["*KPI Changes:*"]
        for change in kpi_changes:
            metric = change["metric"].replace("_", " ").title()
            arrow = "^" if change["direction"] == "up" else "v"
            kpi_lines.append(
                f"{arrow} {metric}: {change['previous']} -> {change['current']} "
                f"({change['pct_change']}%)"
            )
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(kpi_lines)},
            }
        )

    # Stalled initiatives
    stalled = briefing_data.get("stalled_initiatives", [])
    if stalled:
        stalled_lines = ["*Stalled Initiatives:*"]
        for item in stalled:
            stalled_lines.append(f"- {item['title']} ({item['days_stalled']} days)")
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(stalled_lines)},
            }
        )

    # Upcoming deadlines
    deadlines = briefing_data.get("upcoming_deadlines", [])
    if deadlines:
        deadline_lines = ["*Upcoming Deadlines:*"]
        for item in deadlines:
            deadline_lines.append(f"- {item['title']} (in {item['days_until']} days)")
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(deadline_lines)},
            }
        )

    # Divider + CTA
    app_url = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open Dashboard"},
                    "url": f"{app_url}/dashboard",
                    "style": "primary",
                },
            ],
        }
    )

    return blocks
