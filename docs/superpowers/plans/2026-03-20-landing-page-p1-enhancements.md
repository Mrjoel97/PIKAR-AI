# Landing Page P1 Enhancements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add page management API (CRUD + duplicate + import), SEO meta tags, Stitch onboarding, and a dashboard widget for landing pages.

**Architecture:** Extend existing `pages.py` router with authenticated endpoints. Inject SEO meta tags at generation time in both `landing_page.py` and `stitch.py`. Add Stitch API key configuration tool. Create a new frontend widget and API client following the CalendarWidget pattern.

**Tech Stack:** Python 3.10+ (FastAPI), Supabase (PostgreSQL + RPC), Next.js/React (frontend widget), Tailwind CSS.

**Spec:** `docs/superpowers/specs/2026-03-20-landing-page-p1-enhancements-design.md`

---

## File Map

### New Files

| File | Responsibility |
|------|----------------|
| `supabase/migrations/20260320200000_landing_page_enhancements.sql` | RPC for page counts, make form_id nullable |
| `frontend/src/services/landing-pages.ts` | API client for landing page endpoints |
| `frontend/src/components/widgets/LandingPagesWidget.tsx` | Dashboard widget for page management |

### Modified Files

| File | Change |
|------|--------|
| `app/routers/pages.py` | Add 7 new endpoints (list, update, delete, publish, unpublish, duplicate, import) + auth on existing get |
| `app/mcp/tools/landing_page.py` | Inject SEO meta tags in `generate_html()` |
| `app/mcp/tools/stitch.py` | SEO tags in fallback + `configure_stitch_api_key()` tool |
| `app/mcp/agent_tools.py` | Return `not_configured` status for Stitch wrapper |
| `frontend/src/components/widgets/WidgetRegistry.tsx` | Register `landing_pages` widget |
| `frontend/src/types/widgets.ts` | Add `landing_pages` to WidgetType union, LandingPagesData interface |
| `app/agents/marketing/agent.py` | Add Stitch tools + onboarding guidance to instructions |

---

## Task 1: Database Migration

**Files:**
- Create: `supabase/migrations/20260320200000_landing_page_enhancements.sql`

- [ ] **Step 1: Create migration file**

```sql
-- Landing page P1 enhancements:
-- 1. Make form_id nullable on form_submissions (allows direct page submissions)
-- 2. RPC for listing pages with submission counts

-- Fix: allow form submissions without a form or user (direct page submissions from anonymous visitors)
ALTER TABLE form_submissions ALTER COLUMN form_id DROP NOT NULL;
ALTER TABLE form_submissions ALTER COLUMN user_id DROP NOT NULL;

-- RPC: get user's landing pages with submission counts
CREATE OR REPLACE FUNCTION get_user_pages_with_counts(p_user_id UUID)
RETURNS TABLE(
    id UUID,
    title TEXT,
    slug TEXT,
    published BOOLEAN,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    metadata JSONB,
    submission_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        lp.id, lp.title, lp.slug, lp.published,
        lp.published_at, lp.created_at, lp.updated_at,
        lp.metadata,
        COALESCE(COUNT(fs.id), 0) AS submission_count
    FROM landing_pages lp
    LEFT JOIN form_submissions fs ON fs.page_id = lp.id
    WHERE lp.user_id = p_user_id
    GROUP BY lp.id
    ORDER BY lp.updated_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

- [ ] **Step 2: Commit**

```bash
git add supabase/migrations/20260320200000_landing_page_enhancements.sql
git commit -m "feat: add landing page counts RPC and make form_id nullable"
```

---

## Task 2: Page Management API

**Files:**
- Modify: `app/routers/pages.py`

- [ ] **Step 1: Add imports and auth dependency**

Add to the top of `app/routers/pages.py`, after existing imports:

```python
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends
from pydantic import BaseModel
from app.routers.onboarding import get_current_user_id
```

Add Pydantic models after the `router = APIRouter()` line:

```python
class PageUpdateRequest(BaseModel):
    """Request body for updating a landing page."""
    title: Optional[str] = None
    html_content: Optional[str] = None
    slug: Optional[str] = None
    metadata: Optional[dict] = None


class PageImportRequest(BaseModel):
    """Request body for importing a landing page from HTML."""
    title: str
    html_content: str
    source: Optional[str] = "import"
```

- [ ] **Step 2: Add auth to existing GET /pages/{page_id}**

Replace the existing `get_page_content` function to add user_id scoping. This is intentional — the public rendering path uses `GET /landing/{slug}`, not `GET /pages/{page_id}`. The pages endpoint is for authenticated management only:

```python
@router.get("/pages/{page_id}")
@limiter.limit(get_user_persona_limit)
async def get_page_content(
    request: Request,
    page_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Retrieve landing page data as JSON (auth-scoped)."""
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
```

- [ ] **Step 3: Add POST /pages/import (BEFORE any {page_id} routes)**

**IMPORTANT:** This must be defined BEFORE all `{page_id}` parameterized routes, otherwise FastAPI will match `POST /pages/import` as `page_id="import"`. Place it right after `GET /pages`.

```python
@router.post("/pages/import")
@limiter.limit(get_user_persona_limit)
async def import_page(
    request: Request,
    body: PageImportRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Import a landing page from raw HTML (e.g., from Stitch)."""
    try:
        supabase = get_service_client()

        slug = body.title.lower().replace(" ", "-")[:50]
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        page_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Inject SEO meta tags if missing
        html = body.html_content
        if '<meta name="description"' not in html and "</head>" in html:
            seo_tags = f'''    <meta name="description" content="{body.title}">
    <meta property="og:title" content="{body.title}">
    <meta property="og:description" content="{body.title}">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{body.title}">
    <meta name="twitter:description" content="{body.title}">
'''
            html = html.replace("</head>", seo_tags + "</head>")

        supabase.table("landing_pages").insert({
            "id": page_id,
            "user_id": user_id,
            "title": body.title,
            "slug": slug,
            "html_content": html,
            "metadata": {"source": body.source},
            "published": False,
            "created_at": now,
            "updated_at": now,
        }).execute()

        return {
            "status": "imported",
            "page_id": page_id,
            "slug": slug,
            "url": f"/landing/{slug}",
        }
    except Exception as e:
        error_msg = str(e)
        if "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise HTTPException(status_code=409, detail="A page with this slug already exists")
        raise HTTPException(status_code=500, detail=error_msg)
```

- [ ] **Step 4: Add GET /pages (list with counts)**

```python
@router.get("/pages")
@limiter.limit(get_user_persona_limit)
async def list_pages(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """List user's landing pages with submission counts."""
    try:
        supabase = get_service_client()
        result = supabase.rpc(
            "get_user_pages_with_counts",
            {"p_user_id": user_id},
        ).execute()

        return {"pages": result.data or [], "count": len(result.data or [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: Add PATCH /pages/{page_id} (update)**

```python
@router.patch("/pages/{page_id}")
@limiter.limit(get_user_persona_limit)
async def update_page(
    request: Request,
    page_id: str,
    body: PageUpdateRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Update a landing page's title, content, slug, or metadata."""
    try:
        supabase = get_service_client()
        updates = {k: v for k, v in body.model_dump().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        supabase.table("landing_pages").update(updates).eq(
            "id", page_id
        ).eq("user_id", user_id).execute()

        return {"status": "updated", "page_id": page_id, "fields": list(updates.keys())}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise HTTPException(status_code=409, detail="A page with this slug already exists")
        raise HTTPException(status_code=500, detail=error_msg)
```

- [ ] **Step 5: Add DELETE, publish, unpublish endpoints**

```python
@router.delete("/pages/{page_id}")
@limiter.limit(get_user_persona_limit)
async def delete_page(
    request: Request,
    page_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Delete a landing page and its orphaned submissions."""
    try:
        supabase = get_service_client()
        # Delete orphaned submissions (no form_id, linked only by page_id)
        supabase.table("form_submissions").delete().eq(
            "page_id", page_id
        ).is_("form_id", "null").execute()
        # Delete the page (FK cascades handle forms -> their submissions)
        supabase.table("landing_pages").delete().eq(
            "id", page_id
        ).eq("user_id", user_id).execute()

        return {"status": "deleted", "page_id": page_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pages/{page_id}/publish")
@limiter.limit(get_user_persona_limit)
async def publish_page(
    request: Request,
    page_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Publish a landing page."""
    try:
        supabase = get_service_client()
        res = supabase.table("landing_pages").update({
            "published": True,
            "published_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", page_id).eq("user_id", user_id).execute()

        if not res.data:
            raise HTTPException(status_code=404, detail="Page not found")

        slug = res.data[0].get("slug", "")
        return {"status": "published", "page_id": page_id, "url": f"/landing/{slug}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pages/{page_id}/unpublish")
@limiter.limit(get_user_persona_limit)
async def unpublish_page(
    request: Request,
    page_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Unpublish a landing page."""
    try:
        supabase = get_service_client()
        supabase.table("landing_pages").update({
            "published": False,
        }).eq("id", page_id).eq("user_id", user_id).execute()

        return {"status": "unpublished", "page_id": page_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 6: Add duplicate endpoint**

Note: The import endpoint was already added in Step 3 (before {page_id} routes to avoid route conflicts).

```python
@router.post("/pages/{page_id}/duplicate")
@limiter.limit(get_user_persona_limit)
async def duplicate_page(
    request: Request,
    page_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Duplicate a landing page as a new draft."""
    try:
        supabase = get_service_client()

        # Fetch original
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
        base_slug = page["slug"]

        # Find next available copy slug
        existing = (
            supabase.table("landing_pages")
            .select("slug")
            .eq("user_id", user_id)
            .like("slug", f"{base_slug}-copy%")
            .execute()
        )
        existing_slugs = {r["slug"] for r in (existing.data or [])}

        if f"{base_slug}-copy" not in existing_slugs:
            new_slug = f"{base_slug}-copy"
        else:
            n = 2
            while f"{base_slug}-copy-{n}" in existing_slugs:
                n += 1
            new_slug = f"{base_slug}-copy-{n}"

        new_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        supabase.table("landing_pages").insert({
            "id": new_id,
            "user_id": user_id,
            "title": f"{page['title']} (Copy)",
            "slug": new_slug,
            "html_content": page["html_content"],
            "metadata": page.get("metadata", {}),
            "published": False,
            "created_at": now,
            "updated_at": now,
        }).execute()

        return {
            "status": "duplicated",
            "page_id": new_id,
            "slug": new_slug,
            "url": f"/landing/{new_slug}",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


- [ ] **Step 7: Lint and verify**

Run: `C:/Users/expert/.local/bin/uv.cmd run ruff check app/routers/pages.py --fix && C:/Users/expert/.local/bin/uv.cmd run ruff format app/routers/pages.py`

- [ ] **Step 8: Commit**

```bash
git add app/routers/pages.py
git commit -m "feat: add landing page CRUD, duplicate, import, and publish endpoints"
```

---

## Task 3: SEO Meta Tags in Generation

**Files:**
- Modify: `app/mcp/tools/landing_page.py`
- Modify: `app/mcp/tools/stitch.py`

- [ ] **Step 1: Add SEO meta tags to landing_page.py generate_html()**

In `app/mcp/tools/landing_page.py`, in the `generate_html()` method, replace the `<title>{title}</title>` line with:

```python
    <title>{title}</title>
    <meta name="description" content="{subheadline}">
    <meta property="og:title" content="{headline}">
    <meta property="og:description" content="{subheadline}">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{headline}">
    <meta name="twitter:description" content="{subheadline}">
```

This is inside the f-string that builds the HTML. The variables `title`, `headline`, and `subheadline` are already in scope.

- [ ] **Step 2: Add SEO meta tags to stitch.py generate_html_fallback()**

In `app/mcp/tools/stitch.py`, in the `generate_html_fallback()` method, replace the `<title>{config.title}</title>` line with:

```python
    <title>{config.title}</title>
    <meta name="description" content="{config.subheadline or config.description}">
    <meta property="og:title" content="{config.headline or config.title}">
    <meta property="og:description" content="{config.subheadline or config.description}">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{config.headline or config.title}">
    <meta name="twitter:description" content="{config.subheadline or config.description}">
```

- [ ] **Step 3: Lint both files**

Run: `C:/Users/expert/.local/bin/uv.cmd run ruff check app/mcp/tools/landing_page.py app/mcp/tools/stitch.py --fix`

- [ ] **Step 4: Commit**

```bash
git add app/mcp/tools/landing_page.py app/mcp/tools/stitch.py
git commit -m "feat: add SEO meta tags to landing page generation"
```

---

## Task 4: Stitch Onboarding + Not-Configured Status

**Files:**
- Modify: `app/mcp/tools/stitch.py`
- Modify: `app/mcp/agent_tools.py`

- [ ] **Step 1: Add configure_stitch_api_key tool to stitch.py**

Add this function after the existing `stitch_export_to_workspace` function, before `STITCH_TOOLS`:

```python
async def configure_stitch_api_key(
    api_key: str,
) -> Dict[str, Any]:
    """Configure the Stitch API key for landing page generation.

    Validates the key and writes it to the environment. The key takes
    effect immediately without requiring a server restart.

    Args:
        api_key: Stitch API key from stitch.withgoogle.com.

    Returns:
        Configuration result.
    """
    if not api_key or len(api_key) < 10:
        return {"success": False, "error": "Invalid API key format"}

    try:
        # Set in environment immediately
        os.environ["STITCH_API_KEY"] = api_key

        # Clear cached config so is_stitch_configured() sees the new key
        get_mcp_config.cache_clear()

        # Validate by checking config
        config = get_mcp_config()
        if not config.is_stitch_configured():
            return {"success": False, "error": "Key was set but config check failed"}

        # Persist to .env file (dev only — in production, set via Cloud Run env vars)
        env_path = os.path.join(os.getcwd(), ".env")
        try:
            # Check for existing key to avoid duplicates
            existing = ""
            if os.path.exists(env_path):
                with open(env_path) as f:
                    existing = f.read()
            if "STITCH_API_KEY=" not in existing:
                with open(env_path, "a") as f:
                    f.write(f"\nSTITCH_API_KEY={api_key}\n")
        except OSError:
            logger.warning("Could not persist Stitch key to .env (production mode)")

        logger.info("Stitch API key configured successfully")

        return {
            "success": True,
            "message": "Stitch API key configured. You can now generate professional landing pages.",
        }
    except Exception as e:
        logger.error(f"Failed to configure Stitch API key: {e}")
        return {"success": False, "error": str(e)}
```

Update the `STITCH_TOOLS` export to include the new tool:

```python
STITCH_TOOLS = [
    stitch_generate_landing_page,
    stitch_export_to_workspace,
    configure_stitch_api_key,
]
```

- [ ] **Step 2: Update agent_tools.py wrapper to return not_configured status**

In `app/mcp/agent_tools.py`, in the `mcp_stitch_landing_page` function, add a config check at the beginning of the function body (before the try/except):

```python
    # Check if Stitch is configured
    from app.mcp.config import get_mcp_config
    config = get_mcp_config()
    if not config.is_stitch_configured():
        return {
            "status": "not_configured",
            "success": False,
            "message": (
                "Stitch API is not configured. To generate professional landing pages, "
                "you need a Stitch API key from stitch.withgoogle.com. "
                "You can paste your key here and I'll configure it for you, "
                "or I can create a simpler landing page using built-in templates."
            ),
        }
```

- [ ] **Step 3: Update Marketing Agent instructions and tools**

In `app/agents/marketing/agent.py`:

1. Add `mcp_stitch_landing_page` to the Marketing Agent's tool imports and tools list (alongside existing `mcp_generate_landing_page`)
2. Add `configure_stitch_api_key` to the tools list
3. Update `MARKETING_AGENT_INSTRUCTION` to include Stitch onboarding guidance:
   - When generating landing pages, check if Stitch is configured (look for `not_configured` status)
   - If not configured, offer to accept the user's API key via `configure_stitch_api_key`
   - Explain the quality difference between Stitch and local templates
   - Mention the HTML import flow for users who design in Stitch's visual editor

- [ ] **Step 4: Lint all modified files**

Run: `C:/Users/expert/.local/bin/uv.cmd run ruff check app/mcp/tools/stitch.py app/mcp/agent_tools.py app/agents/marketing/agent.py --fix`

- [ ] **Step 5: Commit**

```bash
git add app/mcp/tools/stitch.py app/mcp/agent_tools.py app/agents/marketing/agent.py
git commit -m "feat: add Stitch API key onboarding and not-configured status"
```

---

## Task 5: Frontend API Client

**Files:**
- Create: `frontend/src/services/landing-pages.ts`

- [ ] **Step 1: Create the API client**

```typescript
// frontend/src/services/landing-pages.ts
import { createClient } from '@/lib/supabase/client';

export interface LandingPage {
  id: string;
  title: string;
  slug: string;
  published: boolean;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
  submission_count: number;
}

export interface LandingPageDetail extends LandingPage {
  html_content: string;
}

export interface PageListResponse {
  pages: LandingPage[];
  count: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getAuthHeaders(): Promise<Record<string, string>> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error('Not authenticated');
  return { Authorization: `Bearer ${session.access_token}` };
}

export async function listPages(): Promise<PageListResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages`, { headers });
  if (!res.ok) throw new Error(`Failed to list pages: ${res.statusText}`);
  return res.json();
}

export async function getPage(pageId: string): Promise<LandingPageDetail> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/${pageId}`, { headers });
  if (!res.ok) throw new Error(`Failed to get page: ${res.statusText}`);
  return res.json();
}

export async function updatePage(pageId: string, updates: Partial<Pick<LandingPage, 'title' | 'slug' | 'metadata'>> & { html_content?: string }): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/${pageId}`, {
    method: 'PATCH',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update page: ${res.statusText}`);
}

export async function deletePage(pageId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/${pageId}`, {
    method: 'DELETE',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to delete page: ${res.statusText}`);
}

export async function publishPage(pageId: string): Promise<{ url: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/${pageId}/publish`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to publish: ${res.statusText}`);
  return res.json();
}

export async function unpublishPage(pageId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/${pageId}/unpublish`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to unpublish: ${res.statusText}`);
}

export async function duplicatePage(pageId: string): Promise<{ page_id: string; slug: string; url: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/${pageId}/duplicate`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to duplicate: ${res.statusText}`);
  return res.json();
}

export async function importPage(title: string, htmlContent: string, source?: string): Promise<{ page_id: string; slug: string; url: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/import`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, html_content: htmlContent, source: source || 'stitch_import' }),
  });
  if (!res.ok) throw new Error(`Failed to import: ${res.statusText}`);
  return res.json();
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/landing-pages.ts
git commit -m "feat: add landing pages API client"
```

---

## Task 6: Landing Pages Dashboard Widget

**Files:**
- Create: `frontend/src/components/widgets/LandingPagesWidget.tsx`
- Modify: `frontend/src/components/widgets/WidgetRegistry.tsx`

- [ ] **Step 1: Create LandingPagesWidget.tsx**

Build the widget with:

1. **Header:** "Landing Pages" title, quick stats (`N published` / `N drafts` / `N leads`), "Create New" button
2. **Page list (max 5):** Each row shows title, status pill (green Published / gray Draft), submission count, relative time. Click expands to reveal: preview link, Publish/Unpublish toggle, Duplicate, Delete (with confirm dialog).
3. **Import modal:** Button triggers a textarea modal for pasting HTML + title input. Calls `importPage()`.
4. **Empty state:** "No landing pages yet" with CTA buttons.

Follow the `CalendarWidget.tsx` pattern:
- Props: `{ definition: WidgetDefinition; onAction?: (action: string, data: any) => void }`
- `'use client'` directive
- Tailwind dark mode: `bg-slate-900 text-white border-slate-700`
- Icons from `lucide-react`: `FileText`, `Globe`, `Copy`, `Trash2`, `Upload`, `ExternalLink`, `Plus`
- `useState` for pages data, loading, expanded row, import modal
- `useEffect` on mount calls `listPages()`
- Optimistic updates on actions

Register in `WidgetRegistry.tsx`:
```typescript
const LandingPagesWidget = dynamic(() => import('./LandingPagesWidget'), {
  loading: () => <WidgetSkeleton />,
  ssr: false,
});
```
Add to registry: `'landing_pages': LandingPagesWidget,`

- [ ] **Step 2: Update widget types in `frontend/src/types/widgets.ts`**

Add `'landing_pages'` to the `WidgetType` union type. Create a `LandingPagesData` interface with `pages` array and stats fields. Add `'landing_pages'` to the `isValidWidgetType` check array. Add a `case 'landing_pages':` branch to `validateWidgetDefinition`. Add `LandingPagesData` to the `WidgetData` discriminated union.

- [ ] **Step 3: Verify frontend build**

Run: `cd C:/Users/expert/documents/pka/pikar-ai/frontend && npm run build`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/widgets/LandingPagesWidget.tsx frontend/src/components/widgets/WidgetRegistry.tsx frontend/src/types/widgets.ts
git commit -m "feat: add LandingPagesWidget with import, publish, and duplicate"
```

---

## Task 7: Lint & Verify

- [ ] **Step 1: Run backend linting**

Run: `C:/Users/expert/.local/bin/uv.cmd run ruff check app/routers/pages.py app/mcp/tools/landing_page.py app/mcp/tools/stitch.py app/mcp/agent_tools.py --fix`
Run: `C:/Users/expert/.local/bin/uv.cmd run ruff format app/routers/pages.py app/mcp/tools/landing_page.py app/mcp/tools/stitch.py app/mcp/agent_tools.py`

- [ ] **Step 2: Run frontend build**

Run: `cd C:/Users/expert/documents/pka/pikar-ai/frontend && npm run build`

- [ ] **Step 3: Commit any fixes**

```bash
git add -u
git commit -m "chore: fix lint issues from landing page P1 enhancements"
```

---

## Dependency Graph

```
Task 1 (Migration) → Task 2 (API) → Task 6 (Widget)
Task 3 (SEO) — independent
Task 4 (Stitch) — independent
Task 5 (API Client) → Task 6 (Widget)
Task 7 (Verify) — after all
```

Tasks 1, 3, 4, 5 can run in parallel. Task 2 needs Task 1. Task 6 needs Tasks 2 + 5. Task 7 is last.
