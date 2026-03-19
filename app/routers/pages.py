import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from app.middleware.rate_limiter import limiter, get_user_persona_limit
from typing import Any
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/pages/{page_id}")
@limiter.limit(get_user_persona_limit)
async def get_page_content(request: Request, page_id: str):
    """Retrieve landing page data as JSON."""
    try:
        supabase = get_service_client()
        res = supabase.table("landing_pages").select("*").eq("id", page_id).single().execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="Page not found")

        return res.data
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Page not found")


@router.get("/landing/{slug}", response_class=HTMLResponse)
@limiter.limit(get_user_persona_limit)
async def render_landing_page(request: Request, slug: str):
    """Serve a published landing page as rendered HTML.

    This is the public-facing URL visitors see (e.g. /landing/my-product).
    Only serves published pages.
    """
    try:
        supabase = get_service_client()
        res = (
            supabase.table("landing_pages")
            .select("html_content, title, published")
            .eq("slug", slug)
            .eq("published", True)
            .single()
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="Page not found")

        return HTMLResponse(content=res.data["html_content"], status_code=200)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Page not found")


@router.post("/pages/{page_id}/submit")
@limiter.limit(get_user_persona_limit)
async def submit_lead(request: Request, page_id: str, payload: dict[str, Any]):
    """Capture a lead from a landing page form.

    Persists submission to form_submissions table, triggers webhooks
    and email notifications if configured.
    """
    from app.mcp.tools.supabase_landing import get_landing_tool

    tool = get_landing_tool()

    # Find the form associated with this page
    try:
        supabase = get_service_client()
        form_res = (
            supabase.table("landing_forms")
            .select("id")
            .eq("page_id", page_id)
            .limit(1)
            .execute()
        )

        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        if form_res.data:
            # Route through the full form handler (persists + webhook + email)
            result = await tool.handle_form_submission(
                form_id=form_res.data[0]["id"],
                submission_data=payload,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])
            return result

        # Fallback: no form configured, store directly in form_submissions
        import uuid
        from datetime import datetime, timezone

        supabase.table("form_submissions").insert({
            "id": str(uuid.uuid4()),
            "page_id": page_id,
            "data": payload,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        logger.info("Lead captured for page %s (no form configured)", page_id)
        return {"success": True, "message": "Lead captured"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Lead submission failed for page %s: %s", page_id, e)
        raise HTTPException(status_code=500, detail="Submission failed")
