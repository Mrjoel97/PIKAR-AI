# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Department management and activity endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.department_runner import runner
from app.services.department_task_service import get_department_task_service
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

# ---------------------------------------------------------------------------
# Request models for department task endpoints
# ---------------------------------------------------------------------------

_ALLOWED_TASK_PERSONAS = frozenset({"sme", "enterprise", "startup"})


class CreateDepartmentTaskRequest(BaseModel):
    """Payload for creating a cross-department task handoff."""

    title: str
    from_department_id: str
    to_department_id: str
    description: str | None = None
    priority: str = "medium"
    due_date: str | None = None
    assigned_to: str | None = None


class UpdateTaskStatusRequest(BaseModel):
    """Payload for transitioning a department task's status."""

    status: str


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/departments")
@limiter.limit(get_user_persona_limit)
async def get_departments(
    request: Request,
    _user_id: str = Depends(get_current_user_id),
):
    """List all departments and their real-time state."""
    supabase = get_service_client()
    res = await execute_async(
        supabase.table("departments").select("*").order("name"),
        op_name="departments.list",
    )
    return res.data


@router.post("/departments/{id}/toggle")
@limiter.limit(get_user_persona_limit)
async def toggle_department(
    request: Request,
    id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Start or pause a department."""
    supabase = get_service_client()
    # Check user has admin/enterprise persona
    user_resp = (
        supabase.table("users").select("persona").eq("id", user_id).single().execute()
    )
    if not user_resp.data or user_resp.data.get("persona") not in (
        "enterprise",
        "startup",
    ):
        raise HTTPException(
            status_code=403,
            detail="Only enterprise and startup users can manage departments",
        )
    curr = await execute_async(
        supabase.table("departments").select("status").eq("id", id).single(),
        op_name="departments.get",
    )
    if not curr.data:
        raise HTTPException(status_code=404, detail="Department not found")

    new_status = "PAUSED" if curr.data["status"] == "RUNNING" else "RUNNING"
    await execute_async(
        supabase.table("departments").update({"status": new_status}).eq("id", id),
        op_name="departments.toggle",
    )
    return {"status": new_status}


@router.post("/departments/tick")
@limiter.limit(get_user_persona_limit)
async def manual_tick(
    request: Request,
    _user_id: str = Depends(get_current_user_id),
):
    """Manually trigger a heartbeat cycle (for testing/demo)."""
    results = await runner.tick()
    return {"results": results}


@router.get("/departments/activity")
@limiter.limit(get_user_persona_limit)
async def get_department_activity(
    request: Request,
    _user_id: str = Depends(get_current_user_id),
):
    """Get live department activity for the dashboard widget.

    Returns departments with status, trigger counts, recent decisions,
    and active workflow counts.
    """
    supabase = get_service_client()

    # 1. All departments
    dept_res = await execute_async(
        supabase.table("departments")
        .select("id, name, type, status, last_heartbeat, state, config")
        .order("name"),
        op_name="departments.activity.list",
    )
    departments = dept_res.data or []

    # 2. Trigger counts per department (enabled only)
    trigger_res = await execute_async(
        supabase.table("proactive_triggers")
        .select("department_id")
        .eq("enabled", True),
        op_name="departments.activity.triggers",
    )
    trigger_counts: dict[str, int] = {}
    for row in trigger_res.data or []:
        did = row.get("department_id")
        if did:
            trigger_counts[did] = trigger_counts.get(did, 0) + 1

    # 3. Recent decisions (last 24h)
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    decision_res = await execute_async(
        supabase.table("department_decision_logs")
        .select(
            "department_id, decision_type, decision_logic, outcome, cycle_timestamp"
        )
        .gte("cycle_timestamp", since)
        .order("cycle_timestamp", desc=True)
        .limit(50),
        op_name="departments.activity.decisions",
    )
    decisions_raw = decision_res.data or []

    decision_counts: dict[str, int] = {}
    for d in decisions_raw:
        did = d.get("department_id")
        if did:
            decision_counts[did] = decision_counts.get(did, 0) + 1

    # 4. Active workflows per department (from department state)
    dept_list = []
    for dept in departments:
        dept_state = dept.get("state") or {}
        pending_wfs = dept_state.get("pending_workflows") or []
        dept_list.append(
            {
                "id": dept["id"],
                "name": dept["name"],
                "type": dept["type"],
                "status": dept["status"],
                "last_heartbeat": dept.get("last_heartbeat"),
                "trigger_count": trigger_counts.get(dept["id"], 0),
                "decision_count_24h": decision_counts.get(dept["id"], 0),
                "active_workflows": len(pending_wfs),
                "last_cycle_metrics": dept_state.get("last_cycle_metrics"),
            }
        )

    # 5. Activity feed — last 10 decisions across all departments
    # Enrich with department name
    dept_name_map = {d["id"]: d["name"] for d in departments}
    activity_feed = []
    for d in decisions_raw[:10]:
        activity_feed.append(
            {
                "department_id": d.get("department_id"),
                "department_name": dept_name_map.get(
                    d.get("department_id", ""), "Unknown"
                ),
                "decision_type": d.get("decision_type"),
                "decision_logic": d.get("decision_logic"),
                "outcome": d.get("outcome"),
                "timestamp": d.get("cycle_timestamp"),
            }
        )

    return {
        "departments": dept_list,
        "activity_feed": activity_feed,
    }


@router.get("/departments/triggers")
@limiter.limit(get_user_persona_limit)
async def get_triggers(
    request: Request,
    _user_id: str = Depends(get_current_user_id),
):
    """List all proactive triggers with department name enrichment."""
    supabase = get_service_client()
    trigger_res = await execute_async(
        supabase.table("proactive_triggers")
        .select(
            "id, department_id, name, condition_type, action_type, enabled, last_triggered_at, cooldown_hours, max_triggers_per_day"
        )
        .order("created_at", desc=True),
        op_name="departments.triggers.list",
    )
    return trigger_res.data or []


@router.put("/departments/triggers/{trigger_id}")
@limiter.limit(get_user_persona_limit)
async def toggle_trigger(
    request: Request,
    trigger_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Enable or disable a proactive trigger."""
    supabase = get_service_client()
    # Check user has admin/enterprise persona
    user_resp = (
        supabase.table("users").select("persona").eq("id", user_id).single().execute()
    )
    if not user_resp.data or user_resp.data.get("persona") not in (
        "enterprise",
        "startup",
    ):
        raise HTTPException(
            status_code=403,
            detail="Only enterprise and startup users can manage departments",
        )
    curr = await execute_async(
        supabase.table("proactive_triggers")
        .select("enabled")
        .eq("id", trigger_id)
        .single(),
        op_name="departments.triggers.get",
    )
    if not curr.data:
        raise HTTPException(status_code=404, detail="Trigger not found")

    new_enabled = not curr.data["enabled"]
    await execute_async(
        supabase.table("proactive_triggers")
        .update({"enabled": new_enabled})
        .eq("id", trigger_id),
        op_name="departments.triggers.toggle",
    )
    return {"enabled": new_enabled}


@router.get("/departments/decision-log")
@limiter.limit(get_user_persona_limit)
async def get_decision_log(
    request: Request,
    _user_id: str = Depends(get_current_user_id),
    hours: int = Query(default=24, le=168),
):
    """Get recent department decision logs enriched with department names."""
    supabase = get_service_client()
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    # Fetch decisions
    decision_res = await execute_async(
        supabase.table("department_decision_logs")
        .select(
            "id, department_id, cycle_timestamp, decision_type, decision_logic, outcome, error_message"
        )
        .gte("cycle_timestamp", since)
        .order("cycle_timestamp", desc=True)
        .limit(100),
        op_name="departments.decision_log",
    )
    decisions = decision_res.data or []

    # Enrich with department names
    dept_ids = list({d["department_id"] for d in decisions if d.get("department_id")})
    dept_name_map: dict[str, str] = {}
    if dept_ids:
        dept_res = await execute_async(
            supabase.table("departments").select("id, name").in_("id", dept_ids),
            op_name="departments.decision_log.names",
        )
        for d in dept_res.data or []:
            dept_name_map[d["id"]] = d["name"]

    for decision in decisions:
        decision["department_name"] = dept_name_map.get(
            decision.get("department_id", ""), "Unknown"
        )

    return decisions


@router.get("/departments/requests")
@limiter.limit(get_user_persona_limit)
async def get_inter_dept_requests(
    request: Request,
    _user_id: str = Depends(get_current_user_id),
):
    """List inter-department requests enriched with department names."""
    supabase = get_service_client()
    req_res = await execute_async(
        supabase.table("inter_dept_requests")
        .select(
            "id, from_department_id, to_department_id, request_type, priority, status, created_at"
        )
        .order("created_at", desc=True)
        .limit(50),
        op_name="departments.requests.list",
    )
    requests = req_res.data or []

    # Enrich with department names
    dept_ids = list(
        {r.get("from_department_id") for r in requests if r.get("from_department_id")}
        | {r.get("to_department_id") for r in requests if r.get("to_department_id")}
    )
    dept_name_map: dict[str, str] = {}
    if dept_ids:
        dept_res = await execute_async(
            supabase.table("departments").select("id, name").in_("id", dept_ids),
            op_name="departments.requests.names",
        )
        for d in dept_res.data or []:
            dept_name_map[d["id"]] = d["name"]

    for req in requests:
        req["from_department_name"] = dept_name_map.get(
            req.get("from_department_id", ""), "Unknown"
        )
        req["to_department_name"] = dept_name_map.get(
            req.get("to_department_id", ""), "Unknown"
        )

    return requests


# ---------------------------------------------------------------------------
# Department task endpoints (cross-department handoffs)
# ---------------------------------------------------------------------------


@router.post("/departments/tasks")
@limiter.limit(get_user_persona_limit)
async def create_department_task(
    request: Request,
    body: CreateDepartmentTaskRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Create a cross-department task handoff.

    Requires SME, enterprise, or startup persona. The authenticated user
    becomes the ``created_by`` owner of the task.
    """
    supabase = get_service_client()
    user_resp = (
        supabase.table("users").select("persona").eq("id", user_id).single().execute()
    )
    if (
        not user_resp.data
        or user_resp.data.get("persona") not in _ALLOWED_TASK_PERSONAS
    ):
        raise HTTPException(
            status_code=403,
            detail="Only SME, enterprise, and startup users can create department tasks",
        )

    svc = get_department_task_service()
    try:
        task = await svc.create_task(
            title=body.title,
            from_department_id=body.from_department_id,
            to_department_id=body.to_department_id,
            created_by=user_id,
            description=body.description,
            priority=body.priority,
            due_date=body.due_date,
            assigned_to=body.assigned_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return task


@router.get("/departments/{dept_id}/tasks")
@limiter.limit(get_user_persona_limit)
async def list_department_tasks(
    request: Request,
    dept_id: str,
    direction: str = Query(default="inbound", pattern="^(inbound|outbound)$"),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    _user_id: str = Depends(get_current_user_id),
):
    """List tasks for a department.

    Args:
        dept_id: UUID of the department.
        direction: "inbound" (tasks sent TO this dept) or "outbound"
                   (tasks sent FROM this dept). Default "inbound".
        status: Optional filter — one of pending, in_progress, completed, cancelled.
        limit: Maximum number of tasks to return (1-100, default 50).

    Returns:
        List of enriched task dicts with department names.
    """
    svc = get_department_task_service()
    return await svc.list_tasks(
        dept_id,
        direction=direction,
        status=status,
        limit=limit,
    )


@router.patch("/departments/tasks/{task_id}/status")
@limiter.limit(get_user_persona_limit)
async def update_department_task_status(
    request: Request,
    task_id: str,
    body: UpdateTaskStatusRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Update the status of a department task.

    Transitions the task to one of: pending, in_progress, completed, cancelled.
    If transitioning to completed, the ``completed_at`` timestamp is recorded.
    """
    svc = get_department_task_service()
    try:
        updated = await svc.update_task_status(task_id, body.status, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Department task not found")
    return updated


@router.get("/departments/health")
@limiter.limit(get_user_persona_limit)
async def get_department_health(
    request: Request,
    _user_id: str = Depends(get_current_user_id),
):
    """Get health summary for all departments.

    Queries the ``department_health_summary`` view which computes a
    green / yellow / red health status per department based on the 30-day
    task completion rate (>80% green, 50-80% yellow, <50% red).
    Departments with no tasks in the past 30 days default to green.

    Returns:
        List of dicts with department_id, department_name, department_type,
        department_status, active_tasks, completed_30d, total_30d,
        health_status.
    """
    svc = get_department_task_service()
    return await svc.get_department_health()
