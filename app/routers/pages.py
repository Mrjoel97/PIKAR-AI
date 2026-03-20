import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.middleware.rate_limiter import get_user_persona_limit, limiter
from app.routers.onboarding import get_current_user_id
from app.services.supabase import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter()


class PageUpdateRequest(BaseModel):
    """Request model for updating a landing page."""

    title: Optional[str] = None
    html_content: Optional[str] = None
    slug: Optional[str] = None
    metadata: Optional[dict] = None


class PageImportRequest(BaseModel):
    """Request model for importing a landing page from raw HTML."""

    title: str
    html_content: str
    source: Optional[str] = "import"


@router.post("/pages/import")
@limiter.limit(get_user_persona_limit)
async def import_page(
    request: Request,
    body: PageImportRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Create a landing page from raw HTML, auto-generating a slug and injecting SEO tags."""
    try:
        supabase = get_service_client()

        # Generate base slug from title
        base_slug = body.title.lower().replace(" ", "-")
        base_slug = re.sub(r"[^a-z0-9-]", "", base_slug)
        base_slug = re.sub(r"-+", "-", base_slug).strip("-") or "page"

        # Find an available slug
        slug = base_slug
        counter = 1
        while True:
            existing = (
                supabase.table("landing_pages")
                .select("id")
                .eq("slug", slug)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if not existing.data:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Inject SEO meta tags if missing
        html_content = body.html_content
        if '<meta name="description"' not in html_content and "<head" in html_content:
            seo_tags = (
                f'<meta name="description" content="{body.title}">\n'
                f'<meta property="og:title" content="{body.title}">\n'
                '<meta property="og:type" content="website">\n'
            )
            html_content = html_content.replace("<head>", f"<head>\n{seo_tags}", 1)

        now = datetime.now(timezone.utc).isoformat()
        page_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": body.title,
            "html_content": html_content,
            "slug": slug,
            "published": False,
            "metadata": {"source": body.source},
            "created_at": now,
            "updated_at": now,
        }

        res = supabase.table("landing_pages").insert(page_data).execute()

        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create page")

        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Page import failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Import failed")


@router.get("/pages")
@limiter.limit(get_user_persona_limit)
async def list_pages(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """List all landing pages for the current user with submission counts."""
    try:
        supabase = get_service_client()
        res = supabase.rpc("get_user_pages_with_counts", {"p_user_id": user_id}).execute()
        pages = res.data or []
        return {"pages": pages, "count": len(pages)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list pages for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Failed to list pages")


@router.get("/pages/{page_id}")
@limiter.limit(get_user_persona_limit)
async def get_page_content(
    request: Request,
    page_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Retrieve landing page data as JSON."""
    try:
        supabase = get_service_client()
        res = (
            supabase.table("landing_pages")
            .select("*")
            .eq("id", page_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="Page not found")

        return res.data
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Page not found")


@router.patch("/pages/{page_id}")
@limiter.limit(get_user_persona_limit)
async def update_page(
    request: Request,
    page_id: str,
    body: PageUpdateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Update a landing page's fields."""
    try:
        supabase = get_service_client()

        update_data: dict[str, Any] = {}
        if body.title is not None:
            update_data["title"] = body.title
        if body.html_content is not None:
            update_data["html_content"] = body.html_content
        if body.slug is not None:
            update_data["slug"] = body.slug
        if body.metadata is not None:
            update_data["metadata"] = body.metadata

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        res = (
            supabase.table("landing_pages")
            .update(update_data)
            .eq("id", page_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="Page not found")

        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        err_str = str(e)
        if "unique" in err_str.lower() or "duplicate" in err_str.lower():
            raise HTTPException(status_code=409, detail="Slug already in use")
        logger.error("Failed to update page %s: %s", page_id, e)
        raise HTTPException(status_code=500, detail="Update failed")


@router.delete("/pages/{page_id}")
@limiter.limit(get_user_persona_limit)
async def delete_page(
    request: Request,
    page_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Delete a landing page and its orphaned form submissions."""
    try:
        supabase = get_service_client()

        # Verify ownership first
        existing = (
            supabase.table("landing_pages")
            .select("id")
            .eq("id", page_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Page not found")

        # Delete orphaned submissions (no associated form)
        supabase.table("form_submissions").delete().eq("page_id", page_id).is_(
            "form_id", "null"
        ).execute()

        # Delete the page
        supabase.table("landing_pages").delete().eq("id", page_id).eq(
            "user_id", user_id
        ).execute()

        return {"success": True, "message": "Page deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete page %s: %s", page_id, e)
        raise HTTPException(status_code=500, detail="Delete failed")


@router.post("/pages/{page_id}/publish")
@limiter.limit(get_user_persona_limit)
async def publish_page(
    request: Request,
    page_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Publish a landing page, making it publicly accessible."""
    try:
        supabase = get_service_client()
        now = datetime.now(timezone.utc).isoformat()
        res = (
            supabase.table("landing_pages")
            .update({"published": True, "published_at": now, "updated_at": now})
            .eq("id", page_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="Page not found")

        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to publish page %s: %s", page_id, e)
        raise HTTPException(status_code=500, detail="Publish failed")


@router.post("/pages/{page_id}/unpublish")
@limiter.limit(get_user_persona_limit)
async def unpublish_page(
    request: Request,
    page_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Unpublish a landing page, making it inaccessible to the public."""
    try:
        supabase = get_service_client()
        now = datetime.now(timezone.utc).isoformat()
        res = (
            supabase.table("landing_pages")
            .update({"published": False, "updated_at": now})
            .eq("id", page_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="Page not found")

        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to unpublish page %s: %s", page_id, e)
        raise HTTPException(status_code=500, detail="Unpublish failed")


@router.post("/pages/{page_id}/duplicate")
@limiter.limit(get_user_persona_limit)
async def duplicate_page(
    request: Request,
    page_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Duplicate a landing page, generating a new slug and setting published=False."""
    try:
        supabase = get_service_client()

        # Fetch the original page
        original = (
            supabase.table("landing_pages")
            .select("*")
            .eq("id", page_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        if not original.data:
            raise HTTPException(status_code=404, detail="Page not found")

        page = original.data
        base_slug = page.get("slug", "page")

        # Generate a unique copy slug: -copy, -copy-2, -copy-3, ...
        candidate = f"{base_slug}-copy"
        counter = 2
        while True:
            existing = (
                supabase.table("landing_pages")
                .select("id")
                .eq("slug", candidate)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if not existing.data:
                break
            candidate = f"{base_slug}-copy-{counter}"
            counter += 1

        now = datetime.now(timezone.utc).isoformat()
        new_page = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": f"{page.get('title', 'Untitled')} (Copy)",
            "html_content": page.get("html_content", ""),
            "slug": candidate,
            "published": False,
            "metadata": page.get("metadata") or {},
            "created_at": now,
            "updated_at": now,
        }

        res = supabase.table("landing_pages").insert(new_page).execute()

        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to duplicate page")

        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to duplicate page %s: %s", page_id, e)
        raise HTTPException(status_code=500, detail="Duplicate failed")


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
