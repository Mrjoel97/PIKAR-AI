"""Department management and activity endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.rate_limiter import limiter, get_user_persona_limit
from app.routers.onboarding import get_current_user_id
from app.services.department_runner import runner
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/departments')
@limiter.limit(get_user_persona_limit)
async def get_departments(
    request: Request,
    _user_id: str = Depends(get_current_user_id),
):
    """List all departments and their real-time state."""
    supabase = get_service_client()
    res = await execute_async(
        supabase.table('departments').select('*').order('name'),
        op_name='departments.list',
    )
    return res.data


@router.post('/departments/{id}/toggle')
@limiter.limit(get_user_persona_limit)
async def toggle_department(
    request: Request,
    id: str,
    _user_id: str = Depends(get_current_user_id),
):
    """Start or pause a department."""
    supabase = get_service_client()
    curr = await execute_async(
        supabase.table('departments').select('status').eq('id', id).single(),
        op_name='departments.get',
    )
    if not curr.data:
        raise HTTPException(status_code=404, detail='Department not found')

    new_status = 'PAUSED' if curr.data['status'] == 'RUNNING' else 'RUNNING'
    await execute_async(
        supabase.table('departments').update({'status': new_status}).eq('id', id),
        op_name='departments.toggle',
    )
    return {'status': new_status}


@router.post('/departments/tick')
@limiter.limit(get_user_persona_limit)
async def manual_tick(
    request: Request,
    _user_id: str = Depends(get_current_user_id),
):
    """Manually trigger a heartbeat cycle (for testing/demo)."""
    results = await runner.tick()
    return {'results': results}


@router.get('/departments/activity')
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
        supabase.table('departments')
        .select('id, name, type, status, last_heartbeat, state, config')
        .order('name'),
        op_name='departments.activity.list',
    )
    departments = dept_res.data or []

    # 2. Trigger counts per department (enabled only)
    trigger_res = await execute_async(
        supabase.table('proactive_triggers')
        .select('department_id')
        .eq('enabled', True),
        op_name='departments.activity.triggers',
    )
    trigger_counts: dict[str, int] = {}
    for row in trigger_res.data or []:
        did = row.get('department_id')
        if did:
            trigger_counts[did] = trigger_counts.get(did, 0) + 1

    # 3. Recent decisions (last 24h)
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    decision_res = await execute_async(
        supabase.table('department_decision_logs')
        .select('department_id, decision_type, decision_logic, outcome, cycle_timestamp')
        .gte('cycle_timestamp', since)
        .order('cycle_timestamp', desc=True)
        .limit(50),
        op_name='departments.activity.decisions',
    )
    decisions_raw = decision_res.data or []

    decision_counts: dict[str, int] = {}
    for d in decisions_raw:
        did = d.get('department_id')
        if did:
            decision_counts[did] = decision_counts.get(did, 0) + 1

    # 4. Active workflows per department (from department state)
    dept_list = []
    for dept in departments:
        dept_state = dept.get('state') or {}
        pending_wfs = dept_state.get('pending_workflows') or []
        dept_list.append({
            'id': dept['id'],
            'name': dept['name'],
            'type': dept['type'],
            'status': dept['status'],
            'last_heartbeat': dept.get('last_heartbeat'),
            'trigger_count': trigger_counts.get(dept['id'], 0),
            'decision_count_24h': decision_counts.get(dept['id'], 0),
            'active_workflows': len(pending_wfs),
            'last_cycle_metrics': dept_state.get('last_cycle_metrics'),
        })

    # 5. Activity feed — last 10 decisions across all departments
    # Enrich with department name
    dept_name_map = {d['id']: d['name'] for d in departments}
    activity_feed = []
    for d in decisions_raw[:10]:
        activity_feed.append({
            'department_id': d.get('department_id'),
            'department_name': dept_name_map.get(d.get('department_id', ''), 'Unknown'),
            'decision_type': d.get('decision_type'),
            'decision_logic': d.get('decision_logic'),
            'outcome': d.get('outcome'),
            'timestamp': d.get('cycle_timestamp'),
        })

    return {
        'departments': dept_list,
        'activity_feed': activity_feed,
    }
