from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.personas.runtime import resolve_request_persona
from app.routers.approvals import get_pending_approvals
from app.routers.onboarding import get_current_user_id
from app.routers.org import get_org_chart
from app.services.dashboard_summary_service import get_dashboard_summary_service
from app.services.supabase import get_service_client

router = APIRouter()


class AgentSummary(BaseModel):
    label: str
    role: str | None = None
    status: str = "active"


class BriefingData(BaseModel):
    greeting: str
    pending_approvals: list[dict[str, Any]]
    online_agents: int
    agents: list[AgentSummary]
    system_status: str


@router.get("/briefing")
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
            greeting = "Good Morning"
        elif hour < 18:
            greeting = "Good Afternoon"
        else:
            greeting = "Good Evening"

        approvals = await get_pending_approvals(request, user_id)
        org_data = await get_org_chart(request)
        agent_nodes = [n for n in org_data.nodes if n.type == "agent"]
        online_agents = len(agent_nodes)
        agents = [
            AgentSummary(label=n.label, role=n.role, status=n.status)
            for n in agent_nodes
        ]

        return BriefingData(
            greeting=greeting,
            pending_approvals=approvals,
            online_agents=online_agents,
            agents=agents,
            system_status="All Systems Operational",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/briefing/today")
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
            db.table("email_triage")
            .select(
                "id, section, subject, sender, priority, status, action_type, created_at"
            )
            .eq("user_id", user_id)
            .gte("created_at", today)
            .execute()
        )
        items = response.data or []

        sections: dict[str, list[dict[str, Any]]] = {
            "urgent": [],
            "needs_reply": [],
            "auto_handled": [],
            "fyi": [],
        }

        for item in items:
            section = item.get("section") or item.get("action_type") or "fyi"
            if item.get("priority") == "urgent" or section == "urgent":
                sections["urgent"].append(item)
            elif section == "needs_reply":
                sections["needs_reply"].append(item)
            elif section in ("auto_handle", "auto_handled") or item.get("status") in (
                "auto_handled",
                "sent",
            ):
                sections["auto_handled"].append(item)
            else:
                sections["fyi"].append(item)

        return {
            "date": today,
            "total": len(items),
            "sections": sections,
            "counts": {k: len(v) for k, v in sections.items()},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/briefing/refresh")
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
            db.table("user_briefing_preferences")
            .select("preferences")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        prefs = {}
        if prefs_resp.data:
            prefs = prefs_resp.data.get("preferences") or {}

        worker = EmailTriageWorker(supabase_client=db)
        result = await worker.process_user(user_id, prefs)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ApproveDraftBody(BaseModel):
    """Request body for approving a draft reply."""

    draft_text: str | None = None


@router.patch("/briefing/items/{item_id}/approve")
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
            db.table("email_triage")
            .select("*")
            .eq("id", item_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        item = resp.data
        if not item:
            raise HTTPException(status_code=404, detail="Triage item not found.")

        import html

        draft_reply = body.draft_text or item.get("draft_reply")
        if not draft_reply:
            raise HTTPException(status_code=422, detail="No draft reply available.")
        # Note: html.escape removed — draft_reply is sent as plain text by GmailService.
        # Escaping would cause recipients to see &lt; instead of < in the email body.

        # Fetch provider token from user session
        token_resp = (
            db.table("user_google_tokens")
            .select("provider_token, refresh_token")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        token_data = token_resp.data or {}
        provider_token = token_data.get("provider_token")
        if not provider_token:
            raise HTTPException(
                status_code=401, detail="Google authentication required."
            )

        credentials = get_google_credentials(
            provider_token, token_data.get("refresh_token")
        )
        gmail_service = GmailService(credentials)
        send_result = gmail_service.send_email(
            to=[item.get("sender", "")],
            subject=f"Re: {item.get('subject', '')}",
            body=draft_reply,
        )

        db.table("email_triage").update(
            {"status": "sent", "acted_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", item_id).execute()

        return {
            "status": "ok",
            "message": "Draft approved and sent.",
            "send_result": send_result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/briefing/items/{item_id}/dismiss")
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
        db.table("email_triage").update(
            {"status": "dismissed", "acted_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", item_id).eq("user_id", user_id).execute()
        return {"status": "ok", "message": f"Item {item_id} dismissed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/briefing/items/{item_id}/undo")
@limiter.limit(get_user_persona_limit)
async def undo_briefing_item(
    item_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Undo an auto-action on a triage item, reverting to pending."""
    try:
        db = get_service_client()
        db.table("email_triage").update({"status": "pending", "acted_at": None}).eq(
            "id", item_id
        ).eq("user_id", user_id).execute()
        return {"status": "ok", "message": f"Auto-action undone for item {item_id}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BriefingPreferences(BaseModel):
    """User briefing preferences."""

    email_triage_enabled: bool | None = None
    auto_act_enabled: bool | None = None
    auto_act_daily_cap: int | None = None
    auto_act_categories: list[str] | None = None
    vip_senders: list[str] | None = None
    ignored_senders: list[str] | None = None
    briefing_time: str | None = None
    timezone: str | None = None
    email_digest_enabled: bool | None = None
    email_digest_frequency: str | None = None
    preferences: dict[str, Any] | None = None


_DEFAULT_PREFERENCES: dict[str, Any] = {
    "email_triage_enabled": False,
    "auto_act_enabled": False,
    "auto_act_daily_cap": 10,
    "auto_act_categories": [],
    "vip_senders": [],
    "ignored_senders": [],
    "briefing_time": "07:00",
    "timezone": "UTC",
    "email_digest_enabled": False,
    "email_digest_frequency": "daily",
    "preferences": {},
}


@router.get("/briefing/preferences")
@limiter.limit(get_user_persona_limit)
async def get_briefing_preferences(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Get user briefing preferences (returns defaults if none set)."""
    try:
        db = get_service_client()
        resp = (
            db.table("user_briefing_preferences")
            .select("*")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if resp.data:
            return resp.data
        return {**_DEFAULT_PREFERENCES, "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/briefing/preferences")
@limiter.limit(get_user_persona_limit)
async def upsert_briefing_preferences(
    prefs: BriefingPreferences,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Upsert user briefing preferences using field-level merge to avoid race conditions."""
    try:
        from datetime import datetime, timezone

        db = get_service_client()

        # Build update dict from only non-None fields to avoid overwriting
        # fields that were set by a concurrent request.
        _field_map: list[str] = [
            "email_triage_enabled",
            "auto_act_enabled",
            "auto_act_daily_cap",
            "auto_act_categories",
            "vip_senders",
            "ignored_senders",
            "briefing_time",
            "timezone",
            "email_digest_enabled",
            "email_digest_frequency",
        ]
        update_data: dict[str, Any] = {}
        for field in _field_map:
            value = getattr(prefs, field, None)
            if value is not None:
                update_data[field] = value
        if prefs.preferences is not None:
            update_data["preferences"] = prefs.preferences
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        resp = (
            db.table("user_briefing_preferences")
            .update(update_data)
            .eq("user_id", user_id)
            .execute()
        )
        if resp.data:
            return resp.data[0]

        # No existing row — insert with defaults merged with the supplied fields
        insert_data: dict[str, Any] = {
            **_DEFAULT_PREFERENCES,
            **update_data,
            "user_id": user_id,
        }
        resp = db.table("user_briefing_preferences").insert(insert_data).execute()
        return resp.data[0] if resp.data else insert_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/briefing/digest-status")
@limiter.limit(get_user_persona_limit)
async def get_digest_status(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Check digest delivery status and next scheduled send.

    Returns the user's digest configuration, when preferences were
    last updated (proxy for last digest send), and whether the next
    digest will fire based on the current day and frequency setting.
    """
    try:
        from datetime import datetime, timezone

        db = get_service_client()
        prefs_resp = (
            db.table("user_briefing_preferences")
            .select(
                "email_digest_enabled, email_digest_frequency, briefing_time, timezone, updated_at"
            )
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        prefs = prefs_resp.data

        if not prefs:
            return {
                "digest_enabled": False,
                "frequency": "off",
                "last_updated": None,
                "next_digest": None,
            }

        digest_enabled = prefs.get("email_digest_enabled", False)
        frequency = prefs.get("email_digest_frequency", "off")
        briefing_time = prefs.get("briefing_time", "07:00")
        user_tz = prefs.get("timezone", "UTC")
        last_updated = prefs.get("updated_at")

        # Determine if next digest will fire
        now_utc = datetime.now(timezone.utc)
        today_weekday = now_utc.weekday()  # 0=Mon .. 6=Sun
        will_send_today = False
        if digest_enabled and frequency != "off":
            if frequency == "daily":
                will_send_today = True
            elif frequency == "weekdays" and today_weekday < 5:
                will_send_today = True

        return {
            "digest_enabled": digest_enabled,
            "frequency": frequency,
            "briefing_time": briefing_time,
            "timezone": user_tz,
            "last_updated": last_updated,
            "will_send_today": will_send_today,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/briefing/dashboard-summary")
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
