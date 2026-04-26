# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Report scheduling tools for agents.

Provides tools for creating, managing, and viewing scheduled reports.
"""

from typing import Any, Literal

# Tool context type
ToolContextType = Any


def _resolve_connection_id(
    tool_context: ToolContextType,
    spreadsheet_id: str | None,
) -> str | None:
    """Resolve the persisted spreadsheet connection for the active user."""
    connection_id = tool_context.state.get("connection_id")
    if connection_id:
        return connection_id
    user_id = tool_context.state.get("user_id")
    if not user_id or not spreadsheet_id:
        return None
    from app.services.spreadsheet_connection_service import SpreadsheetConnectionService

    connection = SpreadsheetConnectionService().get_connection(
        user_id=user_id,
        spreadsheet_id=spreadsheet_id,
    )
    if connection and connection.get("id"):
        tool_context.state["connection_id"] = connection["id"]
        return connection["id"]
    return None


async def schedule_report(
    tool_context: ToolContextType,
    frequency: Literal["hourly", "daily", "weekly", "monthly", "quarterly", "yearly"],
    report_format: Literal["pptx", "pdf", "xlsx"] = "pptx",
    recipients: list[str] | None = None,
    spreadsheet_id: str | None = None,
) -> dict[str, Any]:
    """Schedule automated report generation.

    Use this to set up recurring reports for the user's connected spreadsheet.

    Args:
        tool_context: Agent tool context.
        frequency: How often to generate reports:
            - hourly: Every hour
            - daily: Every day at 6 AM UTC
            - weekly: Every Monday at 6 AM UTC
            - monthly: First of each month
            - quarterly: First of each quarter
            - yearly: January 1st
        report_format: Output format (pptx, pdf, xlsx).
        recipients: Email addresses to receive the reports.
        spreadsheet_id: Optional spreadsheet ID. Uses connected sheet if not provided.

    Returns:
        Dict with schedule confirmation and next run time.
    """
    from app.services.report_scheduler import (
        ReportFormat,
        ReportFrequency,
        report_scheduler,
    )

    try:
        # Get connected spreadsheet if not specified
        if not spreadsheet_id:
            spreadsheet_id = tool_context.state.get("connected_spreadsheet_id")

        if not spreadsheet_id:
            return {
                "status": "error",
                "message": "No spreadsheet connected. Connect a spreadsheet first.",
            }

        connection_id = _resolve_connection_id(tool_context, spreadsheet_id)
        if not connection_id:
            return {
                "status": "error",
                "message": "Spreadsheet not registered in database. Reconnect it so reporting can store a reusable connection.",
            }

        user_id = tool_context.state.get("user_id", "")

        # Create the schedule
        result = await report_scheduler.create_schedule(
            user_id=user_id,
            connection_id=connection_id,
            frequency=ReportFrequency(frequency),
            report_format=ReportFormat(report_format),
            recipients=recipients or [],
        )

        return result

    except Exception as e:
        return {"status": "error", "message": f"Failed to create schedule: {e}"}


async def list_report_schedules(
    tool_context: ToolContextType,
    spreadsheet_id: str | None = None,
) -> dict[str, Any]:
    """List all scheduled reports for a spreadsheet.

    Args:
        tool_context: Agent tool context.
        spreadsheet_id: Optional filter by spreadsheet.

    Returns:
        Dict with list of schedules.
    """
    from app.services.report_scheduler import report_scheduler

    try:
        if not spreadsheet_id:
            spreadsheet_id = tool_context.state.get("connected_spreadsheet_id")

        if not spreadsheet_id:
            return {
                "status": "error",
                "message": "No spreadsheet connected. Connect a spreadsheet first.",
            }

        connection_id = _resolve_connection_id(tool_context, spreadsheet_id)
        if not connection_id:
            return {
                "status": "error",
                "message": "Spreadsheet not registered in database. Reconnect it so reporting can store a reusable connection.",
            }

        schedules = await report_scheduler.list_schedules(connection_id)

        return {
            "status": "success",
            "count": len(schedules),
            "schedules": [
                {
                    "id": s["id"],
                    "frequency": s["frequency"],
                    "format": s["report_format"],
                    "enabled": s["enabled"],
                    "next_run": s.get("next_run_at"),
                    "last_run": s.get("last_run_at"),
                    "recipients": s.get("recipients", []),
                }
                for s in schedules
            ],
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to list schedules: {e}"}


async def update_report_schedule(
    tool_context: ToolContextType,
    schedule_id: str,
    frequency: Literal["hourly", "daily", "weekly", "monthly", "quarterly", "yearly"]
    | None = None,
    report_format: Literal["pptx", "pdf", "xlsx"] | None = None,
    recipients: list[str] | None = None,
    enabled: bool | None = None,
) -> dict[str, Any]:
    """Update a scheduled report configuration.

    Args:
        tool_context: Agent tool context.
        schedule_id: ID of the schedule to update.
        frequency: New frequency (optional).
        report_format: New format (optional).
        recipients: New recipient list (optional).
        enabled: Enable/disable the schedule (optional).

    Returns:
        Dict with updated schedule details.
    """
    from app.services.report_scheduler import report_scheduler

    try:
        updates = {}
        if frequency:
            updates["frequency"] = frequency
        if report_format:
            updates["report_format"] = report_format
        if recipients is not None:
            updates["recipients"] = recipients
        if enabled is not None:
            updates["enabled"] = enabled

        if not updates:
            return {"status": "error", "message": "No updates provided"}

        result = await report_scheduler.update_schedule(schedule_id, **updates)
        return result

    except Exception as e:
        return {"status": "error", "message": f"Failed to update schedule: {e}"}


async def pause_report_schedule(
    tool_context: ToolContextType,
    schedule_id: str,
) -> dict[str, Any]:
    """Pause a scheduled report (can be resumed later).

    Args:
        tool_context: Agent tool context.
        schedule_id: ID of the schedule to pause.

    Returns:
        Dict with confirmation.
    """
    from app.services.report_scheduler import report_scheduler

    try:
        result = await report_scheduler.disable_schedule(schedule_id)
        if result.get("status") == "success":
            return {"status": "success", "message": "Report schedule paused"}
        return result
    except Exception as e:
        return {"status": "error", "message": f"Failed to pause schedule: {e}"}


async def resume_report_schedule(
    tool_context: ToolContextType,
    schedule_id: str,
) -> dict[str, Any]:
    """Resume a paused scheduled report.

    Args:
        tool_context: Agent tool context.
        schedule_id: ID of the schedule to resume.

    Returns:
        Dict with confirmation and next run time.
    """
    from app.services.report_scheduler import report_scheduler

    try:
        result = await report_scheduler.enable_schedule(schedule_id)
        if result.get("status") == "success":
            schedule = result.get("schedule", {})
            return {
                "status": "success",
                "message": "Report schedule resumed",
                "next_run": schedule.get("next_run_at"),
            }
        return result
    except Exception as e:
        return {"status": "error", "message": f"Failed to resume schedule: {e}"}


async def delete_report_schedule(
    tool_context: ToolContextType,
    schedule_id: str,
) -> dict[str, Any]:
    """Delete a scheduled report permanently.

    Args:
        tool_context: Agent tool context.
        schedule_id: ID of the schedule to delete.

    Returns:
        Dict with confirmation.
    """
    from app.services.report_scheduler import report_scheduler

    try:
        result = await report_scheduler.delete_schedule(schedule_id)
        return result
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete schedule: {e}"}


# Export all scheduling tools
REPORT_SCHEDULING_TOOLS = [
    schedule_report,
    list_report_schedules,
    update_report_schedule,
    pause_report_schedule,
    resume_report_schedule,
    delete_report_schedule,
]
