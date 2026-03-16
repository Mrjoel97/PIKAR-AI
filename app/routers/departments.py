from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.rate_limiter import limiter, get_user_persona_limit
from app.routers.onboarding import get_current_user_id
from app.services.department_runner import runner
from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

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
