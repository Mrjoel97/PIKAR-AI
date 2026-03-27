# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Document generation tools for agents.

Provides tools for creating PowerPoint presentations and PDF reports.
"""

from datetime import datetime
from typing import Any

from app.services.pptx_generator import pptx_generator

# Tool context type - uses Any since ToolContext is internal to ADK
ToolContextType = Any


def generate_presentation(
    tool_context: ToolContextType,
    title: str,
    subtitle: str = "",
    slides: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate a PowerPoint presentation.

    Use this to create presentations for reports, proposals, or pitch decks.

    Args:
        tool_context: Agent tool context.
        title: Main title for the presentation.
        subtitle: Optional subtitle.
        slides: List of slide configurations, each with:
            - title: Slide title
            - type: "bullets" | "table" | "summary"
            - content: List of bullet points (for bullets/summary)
            - headers: Column headers (for table)
            - rows: Data rows (for table)

    Returns:
        Dict with file path and download information.
    """
    try:
        filepath = pptx_generator.create_report_presentation(
            title=title,
            subtitle=subtitle,
            sections=slides or [],
        )

        return {
            "status": "success",
            "message": f"Created presentation: {title}",
            "file_path": filepath,
            "file_type": "pptx",
            "download_ready": True,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to create presentation: {e}"}


def generate_daily_report_pptx(
    tool_context: ToolContextType,
    date: str | None = None,
    metrics: dict[str, Any] | None = None,
    highlights: list[str] | None = None,
    concerns: list[str] | None = None,
    recommendations: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a daily report PowerPoint.

    Use this for end-of-day summaries with key metrics and highlights.

    Args:
        tool_context: Agent tool context.
        date: Report date (defaults to today).
        metrics: Key-value dict of metrics.
        highlights: List of positive highlights.
        concerns: Optional list of concerns.
        recommendations: Optional action items.

    Returns:
        Dict with file path.
    """
    try:
        report_date = date or datetime.now().strftime("%B %d, %Y")

        filepath = pptx_generator.create_daily_report(
            date=report_date,
            metrics=metrics or {},
            highlights=highlights or ["No highlights recorded"],
            concerns=concerns,
            recommendations=recommendations,
        )

        return {
            "status": "success",
            "message": f"Created daily report for {report_date}",
            "file_path": filepath,
            "file_type": "pptx",
            "download_ready": True,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to create daily report: {e}"}


def generate_weekly_report_pptx(
    tool_context: ToolContextType,
    week_range: str,
    summary: str,
    metrics_comparison: list[dict[str, Any]],
    achievements: list[str],
    next_week_priorities: list[str],
) -> dict[str, Any]:
    """Generate a weekly report PowerPoint.

    Use this for weekly summaries with trend analysis and comparisons.

    Args:
        tool_context: Agent tool context.
        week_range: Week range (e.g., "Jan 20 - Jan 26, 2026").
        summary: Executive summary text.
        metrics_comparison: List of {metric, previous, current, change}.
        achievements: Week's achievements.
        next_week_priorities: Priorities for next week.

    Returns:
        Dict with file path.
    """
    try:
        filepath = pptx_generator.create_weekly_report(
            week_range=week_range,
            summary=summary,
            metrics_comparison=metrics_comparison,
            achievements=achievements,
            next_week_priorities=next_week_priorities,
        )

        return {
            "status": "success",
            "message": f"Created weekly report for {week_range}",
            "file_path": filepath,
            "file_type": "pptx",
            "download_ready": True,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to create weekly report: {e}"}


# Export all document generation tools
DOCUMENT_GENERATION_TOOLS = [
    generate_presentation,
    generate_daily_report_pptx,
    generate_weekly_report_pptx,
]
