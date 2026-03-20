"""Workflow trigger orchestration service.

Provides durable schedule- and event-based workflow triggers backed by the
workflow mission kernel and ai_jobs queue.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class WorkflowTriggerType(str, Enum):
    SCHEDULE = "schedule"
    EVENT = "event"


class WorkflowTriggerFrequency(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class WorkflowTriggerConfig:
    id: str
    user_id: str
    template_id: str
    trigger_name: str
    trigger_type: WorkflowTriggerType
    schedule_frequency: WorkflowTriggerFrequency | None
    event_name: str | None
    enabled: bool
    run_source: str
    context: dict[str, Any]
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_event_at: datetime | None
    queue_mode: str
    lane: str
    persona: str | None


class WorkflowTriggerService:
    """Manage persistent workflow triggers and queued trigger executions."""

    def __init__(self, supabase_client: Any = None):
        self._supabase = supabase_client

    @property
    def supabase(self) -> Any:
        if self._supabase is None:
            self._supabase = get_service_client()
        return self._supabase

    def calculate_next_run(
        self,
        frequency: WorkflowTriggerFrequency,
        from_time: datetime | None = None,
    ) -> datetime:
        base = from_time or datetime.now(timezone.utc)
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)

        if frequency == WorkflowTriggerFrequency.HOURLY:
            return base.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        if frequency == WorkflowTriggerFrequency.DAILY:
            next_day = base.replace(hour=6, minute=0, second=0, microsecond=0)
            if next_day <= base:
                next_day += timedelta(days=1)
            return next_day

        if frequency == WorkflowTriggerFrequency.WEEKLY:
            days_until_monday = (7 - base.weekday()) % 7
            if days_until_monday == 0 and base.hour >= 6:
                days_until_monday = 7
            next_monday = base.replace(hour=6, minute=0, second=0, microsecond=0)
            return next_monday + timedelta(days=days_until_monday)

        if frequency == WorkflowTriggerFrequency.MONTHLY:
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
                month=base.month + 1, day=1, hour=6, minute=0, second=0, microsecond=0
            )

        if frequency == WorkflowTriggerFrequency.QUARTERLY:
            current_quarter = (base.month - 1) // 3
            next_quarter_month = ((current_quarter + 1) % 4) * 3 + 1
            next_quarter_year = (
                base.year if next_quarter_month > base.month else base.year + 1
            )
            return datetime(
                next_quarter_year, next_quarter_month, 1, 6, 0, 0, tzinfo=timezone.utc
            )

        if frequency == WorkflowTriggerFrequency.YEARLY:
            return datetime(base.year + 1, 1, 1, 6, 0, 0, tzinfo=timezone.utc)

        raise ValueError(f"Unknown workflow trigger frequency: {frequency}")

    async def create_trigger(
        self,
        *,
        user_id: str,
        template_id: str,
        trigger_name: str,
        trigger_type: WorkflowTriggerType,
        schedule_frequency: WorkflowTriggerFrequency | None = None,
        event_name: str | None = None,
        context: dict[str, Any] | None = None,
        enabled: bool = True,
        run_source: str = "agent_ui",
        queue_mode: str = "followup",
        lane: str = "automation",
        persona: str | None = None,
    ) -> dict[str, Any]:
        self._validate_trigger_inputs(
            trigger_type, schedule_frequency=schedule_frequency, event_name=event_name
        )

        normalized_schedule_frequency = (
            schedule_frequency if trigger_type == WorkflowTriggerType.SCHEDULE else None
        )
        normalized_event_name = (
            str(event_name).strip()
            if trigger_type == WorkflowTriggerType.EVENT and event_name
            else None
        )

        next_run_at = None
        if (
            trigger_type == WorkflowTriggerType.SCHEDULE
            and enabled
            and normalized_schedule_frequency is not None
        ):
            next_run_at = self.calculate_next_run(
                normalized_schedule_frequency
            ).isoformat()

        row = {
            "user_id": user_id,
            "template_id": template_id,
            "trigger_name": trigger_name,
            "trigger_type": trigger_type.value,
            "schedule_frequency": normalized_schedule_frequency.value
            if normalized_schedule_frequency
            else None,
            "event_name": normalized_event_name,
            "context": context or {},
            "enabled": enabled,
            "run_source": run_source,
            "queue_mode": queue_mode,
            "lane": lane,
            "persona": persona,
            "next_run_at": next_run_at,
        }
        result = await execute_async(
            self.supabase.table("workflow_triggers").insert(row),
            op_name="workflow_trigger_service.create_trigger",
        )
        return {"status": "success", "trigger": result.data[0] if result.data else row}

    async def list_triggers(
        self,
        *,
        user_id: str,
        template_id: str | None = None,
        enabled: bool | None = None,
        department: str | None = None,
    ) -> list[dict[str, Any]]:
        query = (
            self.supabase.table("workflow_triggers")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        if template_id:
            query = query.eq("template_id", template_id)
        if enabled is not None:
            query = query.eq("enabled", enabled)
        if department:
            query = query.contains("context", {"department": department})
        result = await execute_async(
            query, op_name="workflow_trigger_service.list_triggers"
        )
        return result.data or []

    async def update_trigger(
        self,
        *,
        trigger_id: str,
        user_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        current = await self.get_trigger(trigger_id=trigger_id, user_id=user_id)
        if not current:
            return {"status": "error", "message": "Trigger not found"}

        patch = dict(updates)
        raw_trigger_type = patch.get("trigger_type") or current["trigger_type"]
        if isinstance(raw_trigger_type, WorkflowTriggerType):
            trigger_type = raw_trigger_type
        else:
            trigger_type = WorkflowTriggerType(str(raw_trigger_type))

        schedule_frequency = patch.get("schedule_frequency") or current.get(
            "schedule_frequency"
        )
        if isinstance(schedule_frequency, WorkflowTriggerFrequency):
            schedule_frequency_enum = schedule_frequency
        elif isinstance(schedule_frequency, str) and schedule_frequency:
            schedule_frequency_enum = WorkflowTriggerFrequency(schedule_frequency)
        else:
            schedule_frequency_enum = None
        event_name = (
            patch.get("event_name")
            if "event_name" in patch
            else current.get("event_name")
        )
        self._validate_trigger_inputs(
            trigger_type,
            schedule_frequency=schedule_frequency_enum,
            event_name=event_name,
        )

        enabled = bool(patch.get("enabled", current.get("enabled", True)))
        if trigger_type == WorkflowTriggerType.SCHEDULE:
            patch["event_name"] = None
            if enabled and schedule_frequency_enum is not None:
                patch.setdefault(
                    "next_run_at",
                    self.calculate_next_run(schedule_frequency_enum).isoformat(),
                )
            elif enabled is False:
                patch["next_run_at"] = None
        elif trigger_type == WorkflowTriggerType.EVENT:
            patch["schedule_frequency"] = None
            patch["next_run_at"] = None
        elif enabled is False:
            patch["next_run_at"] = None

        result = await execute_async(
            self.supabase.table("workflow_triggers")
            .update(patch)
            .eq("id", trigger_id)
            .eq("user_id", user_id),
            op_name="workflow_trigger_service.update_trigger",
        )
        if not result.data:
            return {"status": "error", "message": "Trigger not found"}
        return {"status": "success", "trigger": result.data[0]}

    async def delete_trigger(self, *, trigger_id: str, user_id: str) -> dict[str, Any]:
        result = await execute_async(
            self.supabase.table("workflow_triggers")
            .delete()
            .eq("id", trigger_id)
            .eq("user_id", user_id),
            op_name="workflow_trigger_service.delete_trigger",
        )
        if not result.data:
            return {"status": "error", "message": "Trigger not found"}
        return {"status": "success", "trigger": result.data[0]}

    async def get_trigger(
        self, *, trigger_id: str, user_id: str
    ) -> dict[str, Any] | None:
        result = await execute_async(
            self.supabase.table("workflow_triggers")
            .select("*")
            .eq("id", trigger_id)
            .eq("user_id", user_id)
            .limit(1),
            op_name="workflow_trigger_service.get_trigger",
        )
        rows = result.data or []
        return rows[0] if rows else None

    async def get_due_triggers(
        self, now: datetime | None = None
    ) -> list[dict[str, Any]]:
        effective_now = (now or datetime.now(timezone.utc)).isoformat()
        result = await execute_async(
            self.supabase.table("workflow_triggers")
            .select("*")
            .eq("enabled", True)
            .eq("trigger_type", WorkflowTriggerType.SCHEDULE.value)
            .lte("next_run_at", effective_now),
            op_name="workflow_trigger_service.get_due_triggers",
        )
        return result.data or []

    async def run_trigger_scheduler_tick(self) -> list[dict[str, Any]]:
        due_triggers = await self.get_due_triggers()
        results: list[dict[str, Any]] = []
        for trigger in due_triggers:
            result = await self._queue_trigger_job(trigger, reason="schedule")
            results.append(result)

            frequency_value = trigger.get("schedule_frequency")
            if not frequency_value:
                continue
            next_run = self.calculate_next_run(
                WorkflowTriggerFrequency(str(frequency_value))
            )
            await execute_async(
                self.supabase.table("workflow_triggers")
                .update(
                    {
                        "last_run_at": datetime.now(timezone.utc).isoformat(),
                        "next_run_at": next_run.isoformat(),
                    }
                )
                .eq("id", trigger["id"]),
                op_name="workflow_trigger_service.bump_schedule",
            )
        return results

    async def dispatch_event(
        self,
        *,
        user_id: str,
        event_name: str,
        payload: dict[str, Any] | None = None,
        source: str = "user_event",
    ) -> dict[str, Any]:
        payload = payload or {}
        query = (
            self.supabase.table("workflow_triggers")
            .select("*")
            .eq("user_id", user_id)
            .eq("enabled", True)
            .eq("trigger_type", WorkflowTriggerType.EVENT.value)
            .eq("event_name", event_name)
        )
        result = await execute_async(
            query, op_name="workflow_trigger_service.dispatch_event.lookup"
        )
        triggers = result.data or []

        job_results: list[dict[str, Any]] = []
        for trigger in triggers:
            job_results.append(
                await self._queue_trigger_job(
                    trigger, reason="event", event_name=event_name, payload=payload
                )
            )
            await execute_async(
                self.supabase.table("workflow_triggers")
                .update({"last_event_at": datetime.now(timezone.utc).isoformat()})
                .eq("id", trigger["id"]),
                op_name="workflow_trigger_service.dispatch_event.bump",
            )

        event_row = {
            "user_id": user_id,
            "event_name": event_name,
            "payload": payload,
            "source": source,
            "handled_trigger_count": len(triggers),
            "status": "queued" if triggers else "ignored",
        }
        try:
            insert_result = await execute_async(
                self.supabase.table("workflow_trigger_events").insert(event_row),
                op_name="workflow_trigger_service.dispatch_event.log",
            )
            persisted_event = insert_result.data[0] if insert_result.data else event_row
        except Exception as exc:
            logger.warning("Failed to persist workflow trigger event log: %s", exc)
            persisted_event = event_row

        return {
            "status": "queued" if triggers else "ignored",
            "event": persisted_event,
            "matched_trigger_count": len(triggers),
            "job_results": job_results,
        }

    async def execute_trigger_job(self, input_data: dict[str, Any]) -> dict[str, Any]:
        from app.autonomy.agent_kernel import get_agent_kernel
        from app.workflows.engine import get_workflow_engine

        user_id = str(input_data.get("user_id") or "")
        template_id = str(input_data.get("template_id") or "")
        if not user_id or not template_id:
            return {
                "status": "error",
                "message": "workflow trigger job missing user_id or template_id",
            }

        trigger_context = dict(input_data.get("context") or {})
        trigger_context.setdefault(
            "trigger",
            {
                "id": input_data.get("trigger_id"),
                "type": input_data.get("trigger_type"),
                "reason": input_data.get("reason"),
                "event_name": input_data.get("event_name"),
            },
        )
        payload = input_data.get("payload")
        if (
            isinstance(payload, dict)
            and payload
            and "event_payload" not in trigger_context
        ):
            trigger_context["event_payload"] = payload

        kernel = get_agent_kernel(workflow_engine=get_workflow_engine())
        result = await kernel.start_workflow_mission(
            user_id=user_id,
            template_id=template_id,
            context=trigger_context,
            run_source=str(input_data.get("run_source") or "agent_ui"),
            persona=input_data.get("persona"),
            queue_mode=str(input_data.get("queue_mode") or "followup"),
            lane=str(input_data.get("lane") or "automation"),
        )
        if "error" in result:
            return {
                "status": "error",
                "trigger_id": input_data.get("trigger_id"),
                "result": result,
                "message": result.get("error"),
            }
        return {
            "status": "success",
            "trigger_id": input_data.get("trigger_id"),
            "execution_id": result.get("execution_id"),
            "result": result,
        }

    async def _queue_trigger_job(
        self,
        trigger: dict[str, Any],
        *,
        reason: str,
        event_name: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        input_data = {
            "trigger_id": trigger.get("id"),
            "user_id": trigger.get("user_id"),
            "template_id": trigger.get("template_id"),
            "trigger_type": trigger.get("trigger_type"),
            "context": trigger.get("context") or {},
            "run_source": trigger.get("run_source") or "agent_ui",
            "queue_mode": trigger.get("queue_mode") or "followup",
            "lane": trigger.get("lane") or "automation",
            "persona": trigger.get("persona"),
            "reason": reason,
            "event_name": event_name,
            "payload": payload or {},
        }
        result = await execute_async(
            self.supabase.table("ai_jobs").insert(
                {
                    "user_id": trigger.get("user_id"),
                    "job_type": "workflow_trigger_start",
                    "status": "pending",
                    "priority": 8,
                    "input_data": input_data,
                }
            ),
            op_name="workflow_trigger_service.queue_trigger_job",
        )
        job = (
            result.data[0]
            if result.data
            else {"job_type": "workflow_trigger_start", "input_data": input_data}
        )
        return {"status": "queued", "trigger_id": trigger.get("id"), "job": job}

    def _validate_trigger_inputs(
        self,
        trigger_type: WorkflowTriggerType,
        *,
        schedule_frequency: WorkflowTriggerFrequency | None,
        event_name: str | None,
    ) -> None:
        if trigger_type == WorkflowTriggerType.SCHEDULE and schedule_frequency is None:
            raise ValueError("schedule_frequency is required for schedule triggers")
        if (
            trigger_type == WorkflowTriggerType.EVENT
            and not str(event_name or "").strip()
        ):
            raise ValueError("event_name is required for event triggers")


_workflow_trigger_service: WorkflowTriggerService | None = None


def get_workflow_trigger_service() -> WorkflowTriggerService:
    global _workflow_trigger_service
    if _workflow_trigger_service is None:
        _workflow_trigger_service = WorkflowTriggerService()
    return _workflow_trigger_service


async def run_workflow_trigger_scheduler_tick() -> list[dict[str, Any]]:
    return await get_workflow_trigger_service().run_trigger_scheduler_tick()


__all__ = [
    "WorkflowTriggerConfig",
    "WorkflowTriggerFrequency",
    "WorkflowTriggerService",
    "WorkflowTriggerType",
    "get_workflow_trigger_service",
    "run_workflow_trigger_scheduler_tick",
]
