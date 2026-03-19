from fastapi import APIRouter, Depends, HTTPException, Request
from app.middleware.rate_limiter import limiter, get_user_persona_limit
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.personas.runtime import resolve_request_persona
from app.routers.approvals import get_pending_approvals
from app.routers.onboarding import get_current_user_id
from app.routers.org import get_org_chart
from app.services.dashboard_summary_service import get_dashboard_summary_service
from app.services.supabase import get_service_client

router = APIRouter()


class AgentSummary(BaseModel):
    label: str
    role: Optional[str] = None
    status: str = 'active'


class BriefingData(BaseModel):
    greeting: str
    pending_approvals: List[Dict[str, Any]]
    online_agents: int
    agents: List[AgentSummary]
    system_status: str


@router.get('/briefing')
@limiter.limit(get_user_persona_limit)
async def get_briefing(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Aggregate data for the Morning Briefing widget."""
    try:
        from datetime import datetime

        hour = datetime.now().hour
        if hour < 12:
            greeting = 'Good Morning'
        elif hour < 18:
            greeting = 'Good Afternoon'
        else:
            greeting = 'Good Evening'

        approvals = await get_pending_approvals(request, user_id)
        org_data = await get_org_chart(request)
        agent_nodes = [n for n in org_data.nodes if n.type == 'agent']
        online_agents = len(agent_nodes)
        agents = [AgentSummary(label=n.label, role=n.role, status=n.status) for n in agent_nodes]

        return BriefingData(
            greeting=greeting,
            pending_approvals=approvals,
            online_agents=online_agents,
            agents=agents,
            system_status='All Systems Operational',
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/briefing/today')
@limiter.limit(get_user_persona_limit)
async def get_briefing_today(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Return email triage sections for today."""
    try:
        from datetime import datetime, timezone

        db = get_service_client()
        today = datetime.now(timezone.utc).date().isoformat()
        response = (
            db.table('email_triage')
            .select('id, section, subject, sender, priority, status, action_type, created_at')
            .eq('user_id', user_id)
            .gte('created_at', today)
            .execute()
        )
        items = response.data or []

        sections: Dict[str, List[Dict[str, Any]]] = {
            'urgent': [],
            'needs_reply': [],
            'auto_handled': [],
            'fyi': [],
        }

        for item in items:
            section = item.get('section') or item.get('action_type') or 'fyi'
            if item.get('priority') == 'urgent' or section == 'urgent':
                sections['urgent'].append(item)
            elif section == 'needs_reply':
                sections['needs_reply'].append(item)
            elif section in ('auto_handle', 'auto_handled') or item.get('status') in (
                'auto_handled',
                'sent',
            ):
                sections['auto_handled'].append(item)
            else:
                sections['fyi'].append(item)

        return {
            'date': today,
            'total': len(items),
            'sections': sections,
            'counts': {k: len(v) for k, v in sections.items()},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/briefing/refresh')
@limiter.limit(get_user_persona_limit)
async def refresh_briefing(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Trigger on-demand email triage for the current user."""
    try:
        from app.services.email_triage_worker import EmailTriageWorker

        db = get_service_client()
        prefs_resp = (
            db.table('user_briefing_preferences')
            .select('preferences')
            .eq('user_id', user_id)
            .maybe_single()
            .execute()
        )
        prefs = {}
        if prefs_resp.data:
            prefs = prefs_resp.data.get('preferences') or {}

        worker = EmailTriageWorker(supabase_client=db)
        result = await worker.process_user(user_id, prefs)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ApproveDraftBody(BaseModel):
    """Request body for approving a draft reply."""

    draft_text: Optional[str] = None


@router.patch('/briefing/items/{item_id}/approve')
@limiter.limit(get_user_persona_limit)
async def approve_briefing_item(
    item_id: str,
    request: Request,
    body: ApproveDraftBody = ApproveDraftBody(),
    user_id: str = Depends(get_current_user_id),
):
    """Approve a draft reply and mark the triage item as sent."""
    try:
        from datetime import datetime, timezone
        from app.integrations.google.client import get_google_credentials
        from app.integrations.google.gmail import GmailService

        db = get_service_client()
        resp = (
            db.table('email_triage')
            .select('*')
            .eq('id', item_id)
            .eq('user_id', user_id)
            .single()
            .execute()
        )
        item = resp.data
        if not item:
            raise HTTPException(status_code=404, detail='Triage item not found.')

        draft_reply = body.draft_text or item.get('draft_reply')
        if not draft_reply:
            raise HTTPException(status_code=422, detail='No draft reply available.')

        # Fetch provider token from user session
        token_resp = (
            db.table('user_google_tokens')
            .select('provider_token, refresh_token')
            .eq('user_id', user_id)
            .maybe_single()
            .execute()
        )
        token_data = token_resp.data or {}
        provider_token = token_data.get('provider_token')
        if not provider_token:
            raise HTTPException(status_code=401, detail='Google authentication required.')

        credentials = get_google_credentials(provider_token, token_data.get('refresh_token'))
        gmail_service = GmailService(credentials)
        send_result = gmail_service.send_email(
            to=[item.get('sender', '')],
            subject=f"Re: {item.get('subject', '')}",
            body=draft_reply,
        )

        db.table('email_triage').update(
            {'status': 'sent', 'acted_at': datetime.now(timezone.utc).isoformat()}
        ).eq('id', item_id).execute()

        return {'status': 'ok', 'message': 'Draft approved and sent.', 'send_result': send_result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch('/briefing/items/{item_id}/dismiss')
@limiter.limit(get_user_persona_limit)
async def dismiss_briefing_item(
    item_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Dismiss a triage item."""
    try:
        from datetime import datetime, timezone

        db = get_service_client()
        db.table('email_triage').update(
            {'status': 'dismissed', 'acted_at': datetime.now(timezone.utc).isoformat()}
        ).eq('id', item_id).eq('user_id', user_id).execute()
        return {'status': 'ok', 'message': f'Item {item_id} dismissed.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch('/briefing/items/{item_id}/undo')
@limiter.limit(get_user_persona_limit)
async def undo_briefing_item(
    item_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Undo an auto-action on a triage item, reverting to pending."""
    try:
        db = get_service_client()
        db.table('email_triage').update(
            {'status': 'pending', 'acted_at': None}
        ).eq('id', item_id).eq('user_id', user_id).execute()
        return {'status': 'ok', 'message': f'Auto-action undone for item {item_id}.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BriefingPreferences(BaseModel):
    """User briefing preferences."""

    email_triage_enabled: Optional[bool] = None
    auto_act_enabled: Optional[bool] = None
    vip_senders: Optional[List[str]] = None
    ignored_senders: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None


_DEFAULT_PREFERENCES: Dict[str, Any] = {
    'email_triage_enabled': False,
    'auto_act_enabled': False,
    'vip_senders': [],
    'ignored_senders': [],
    'preferences': {},
}


@router.get('/briefing/preferences')
@limiter.limit(get_user_persona_limit)
async def get_briefing_preferences(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Get user briefing preferences (returns defaults if none set)."""
    try:
        db = get_service_client()
        resp = (
            db.table('user_briefing_preferences')
            .select('*')
            .eq('user_id', user_id)
            .maybe_single()
            .execute()
        )
        if resp.data:
            return resp.data
        return {**_DEFAULT_PREFERENCES, 'user_id': user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put('/briefing/preferences')
@limiter.limit(get_user_persona_limit)
async def upsert_briefing_preferences(
    prefs: BriefingPreferences,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Upsert user briefing preferences."""
    try:
        db = get_service_client()
        data: Dict[str, Any] = {'user_id': user_id}
        if prefs.email_triage_enabled is not None:
            data['email_triage_enabled'] = prefs.email_triage_enabled
        if prefs.auto_act_enabled is not None:
            data['auto_act_enabled'] = prefs.auto_act_enabled
        if prefs.vip_senders is not None:
            data['vip_senders'] = prefs.vip_senders
        if prefs.ignored_senders is not None:
            data['ignored_senders'] = prefs.ignored_senders
        if prefs.preferences is not None:
            data['preferences'] = prefs.preferences

        resp = (
            db.table('user_briefing_preferences')
            .upsert(data, on_conflict='user_id')
            .execute()
        )
        return resp.data[0] if resp.data else data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/briefing/dashboard-summary')
@limiter.limit(get_user_persona_limit)
async def get_dashboard_summary(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Return persona-aware home data for the dashboard shell."""
    try:
        service = get_dashboard_summary_service()
        return await service.get_home_summary(
            user_id=user_id,
            persona=resolve_request_persona(request),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
