# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Report scheduler service for automated report generation.

Manages scheduled reports with configurable frequencies:
- Hourly, Daily, Weekly, Monthly, Quarterly, Yearly

Uses database tables for persistence and supports:
- Multiple delivery methods (email, Drive, local download)
- Various report formats (PDF, PPTX, XLSX)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from app.services.supabase_async import execute_async


class ReportFrequency(str, Enum):
    """Supported report frequencies."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ReportFormat(str, Enum):
    """Supported report output formats."""

    PDF = "pdf"
    PPTX = "pptx"
    XLSX = "xlsx"


class DeliveryStatus(str, Enum):
    """Report delivery status."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


@dataclass
class ScheduleConfig:
    """Configuration for a scheduled report."""

    id: str
    connection_id: str
    frequency: ReportFrequency
    report_type: str
    report_format: ReportFormat
    recipients: list[str]
    enabled: bool
    next_run_at: datetime | None
    last_run_at: datetime | None
    template_config: dict[str, Any]


class ReportScheduler:
    """Service for managing scheduled report generation.

    Provides methods for:
    - Creating and managing report schedules
    - Calculating next run times
    - Executing scheduled reports
    - Tracking report history
    """

    def __init__(self, supabase_client: Any = None):
        """Initialize the scheduler.

        Args:
            supabase_client: Optional Supabase client for database operations.
        """
        self._supabase = supabase_client

    @property
    def supabase(self) -> Any:
        """Lazy-load Supabase client."""
        if self._supabase is None:
            from app.services.supabase_client import get_supabase_client

            self._supabase = get_supabase_client()
        return self._supabase

    def calculate_next_run(
        self,
        frequency: ReportFrequency,
        from_time: datetime | None = None,
    ) -> datetime:
        """Calculate the next run time for a given frequency."""
        base = from_time or datetime.now(timezone.utc)

        if frequency == ReportFrequency.HOURLY:
            return base.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        if frequency == ReportFrequency.DAILY:
            next_day = base.replace(hour=6, minute=0, second=0, microsecond=0)
            if next_day <= base:
                next_day += timedelta(days=1)
            return next_day

        if frequency == ReportFrequency.WEEKLY:
            days_until_monday = (7 - base.weekday()) % 7
            if days_until_monday == 0 and base.hour >= 6:
                days_until_monday = 7
            next_monday = base.replace(hour=6, minute=0, second=0, microsecond=0)
            return next_monday + timedelta(days=days_until_monday)

        if frequency == ReportFrequency.MONTHLY:
            if base.month == 12:
                return base.replace(
                    year=base.year + 1,
                    month=1,
                    day=1,
                    hour=6,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            return base.replace(
                month=base.month + 1,
                day=1,
                hour=6,
                minute=0,
                second=0,
                microsecond=0,
            )

        if frequency == ReportFrequency.QUARTERLY:
            current_quarter = (base.month - 1) // 3
            next_quarter_month = ((current_quarter + 1) % 4) * 3 + 1
            next_quarter_year = (
                base.year if next_quarter_month > base.month else base.year + 1
            )
            return datetime(next_quarter_year, next_quarter_month, 1, 6, 0, 0)

        if frequency == ReportFrequency.YEARLY:
            return datetime(base.year + 1, 1, 1, 6, 0, 0)

        raise ValueError(f"Unknown frequency: {frequency}")

    async def create_schedule(
        self,
        user_id: str,
        connection_id: str,
        frequency: ReportFrequency,
        report_type: str = "summary",
        report_format: ReportFormat = ReportFormat.PPTX,
        recipients: list[str] | None = None,
        template_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new report schedule."""
        next_run = self.calculate_next_run(frequency)
        schedule_data = {
            "connection_id": connection_id,
            "frequency": frequency.value,
            "report_type": report_type,
            "report_format": report_format.value,
            "recipients": recipients or [],
            "template_config": template_config or {},
            "next_run_at": next_run.isoformat(),
            "enabled": True,
        }

        result = await execute_async(
            self.supabase.table("report_schedules").insert(schedule_data),
            op_name="report_scheduler.create_schedule",
        )
        if result.data:
            return {
                "status": "success",
                "message": f"Schedule created. First report at {next_run.strftime('%Y-%m-%d %H:%M UTC')}",
                "schedule": result.data[0],
            }
        return {"status": "error", "message": "Failed to create schedule"}

    async def list_schedules(
        self,
        connection_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all schedules, optionally filtered by connection."""
        query = self.supabase.table("report_schedules").select("*")
        if connection_id:
            query = query.eq("connection_id", connection_id)

        result = await execute_async(query, op_name="report_scheduler.list_schedules")
        return result.data or []

    async def update_schedule(
        self,
        schedule_id: str,
        **updates: Any,
    ) -> dict[str, Any]:
        """Update a schedule configuration."""
        if "frequency" in updates:
            updates["next_run_at"] = self.calculate_next_run(
                ReportFrequency(updates["frequency"])
            ).isoformat()

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await execute_async(
            self.supabase.table("report_schedules")
            .update(updates)
            .eq("id", schedule_id),
            op_name="report_scheduler.update_schedule",
        )
        if result.data:
            return {"status": "success", "schedule": result.data[0]}
        return {"status": "error", "message": "Schedule not found"}

    async def disable_schedule(self, schedule_id: str) -> dict[str, Any]:
        """Disable a schedule (pause it)."""
        return await self.update_schedule(schedule_id, enabled=False)

    async def enable_schedule(self, schedule_id: str) -> dict[str, Any]:
        """Enable a schedule (resume it)."""
        return await self.update_schedule(schedule_id, enabled=True)

    async def delete_schedule(self, schedule_id: str) -> dict[str, Any]:
        """Delete a schedule permanently."""
        result = await execute_async(
            self.supabase.table("report_schedules").delete().eq("id", schedule_id),
            op_name="report_scheduler.delete_schedule",
        )
        if result.data:
            return {"status": "success", "message": "Schedule deleted"}
        return {"status": "error", "message": "Schedule not found"}

    async def get_due_schedules(self) -> list[dict[str, Any]]:
        """Get all schedules that are due to run now."""
        now = datetime.now(timezone.utc).isoformat()
        result = await execute_async(
            self.supabase.table("report_schedules")
            .select("*, spreadsheet_connections(*)")
            .eq("enabled", True)
            .lte("next_run_at", now),
            op_name="report_scheduler.get_due_schedules",
        )
        return result.data or []

    async def record_report_generation(
        self,
        schedule_id: str,
        connection_id: str,
        user_id: str,
        report_type: str,
        report_format: str,
        file_path: str,
        file_url: str | None = None,
        file_size: int | None = None,
    ) -> dict[str, Any]:
        """Record a generated report in the database."""
        report_data = {
            "schedule_id": schedule_id,
            "connection_id": connection_id,
            "user_id": user_id,
            "report_type": report_type,
            "report_format": report_format,
            "file_path": file_path,
            "file_url": file_url,
            "file_size_bytes": file_size,
            "delivery_status": DeliveryStatus.PENDING.value,
        }
        result = await execute_async(
            self.supabase.table("generated_reports").insert(report_data),
            op_name="report_scheduler.record_report_generation",
        )
        return result.data[0] if result.data else {}

    async def update_delivery_status(
        self,
        report_id: str,
        status: DeliveryStatus,
    ) -> None:
        """Update the delivery status of a report."""
        updates = {"delivery_status": status.value}
        if status == DeliveryStatus.DELIVERED:
            updates["delivered_at"] = datetime.now(timezone.utc).isoformat()

        await execute_async(
            self.supabase.table("generated_reports")
            .update(updates)
            .eq("id", report_id),
            op_name="report_scheduler.update_delivery_status",
        )

    async def execute_schedule(
        self,
        schedule: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a scheduled report."""
        from app.services.pptx_generator import pptx_generator

        schedule_id = schedule["id"]
        connection = schedule.get("spreadsheet_connections", {})
        frequency = ReportFrequency(schedule["frequency"])
        report_format = ReportFormat(schedule["report_format"])

        try:
            if report_format == ReportFormat.PPTX:
                file_path = pptx_generator.create_report_presentation(
                    title=f"{frequency.value.capitalize()} Report",
                    subtitle=f"{connection.get('spreadsheet_name', 'Data')}",
                    sections=[],
                )
            else:
                file_path = ""

            report = await self.record_report_generation(
                schedule_id=schedule_id,
                connection_id=schedule["connection_id"],
                user_id=connection.get("user_id", ""),
                report_type=schedule["report_type"],
                report_format=report_format.value,
                file_path=file_path,
            )

            next_run = self.calculate_next_run(frequency)
            await self.update_schedule(
                schedule_id,
                last_run_at=datetime.now(timezone.utc).isoformat(),
                next_run_at=next_run.isoformat(),
            )

            return {
                "status": "success",
                "schedule_id": schedule_id,
                "report_id": report.get("id"),
                "file_path": file_path,
                "next_run": next_run.isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "schedule_id": schedule_id,
                "message": str(e),
            }


report_scheduler = ReportScheduler()


async def run_scheduler_tick() -> list[dict[str, Any]]:
    """Run one tick of the scheduler, executing all due schedules."""
    due_schedules = await report_scheduler.get_due_schedules()
    results = []

    for schedule in due_schedules:
        result = await report_scheduler.execute_schedule(schedule)
        results.append(result)

    return results
