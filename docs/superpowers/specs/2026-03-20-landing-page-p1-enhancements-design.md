# Landing Page P1 Enhancements — Design Spec

**Date:** 2026-03-20
**Status:** Approved
**Author:** Claude + User collaborative brainstorm
**Depends on:** P0 fixes committed in `00d992b` (lead form wiring, schema alignment, public rendering)

## Problem Statement

The landing page feature has a functional backend (generation, storage, publishing) but lacks user-facing management, SEO basics, and a smooth Stitch onboarding flow. Users can only interact with landing pages through the chat agent — no dashboard visibility, no edit capability, no import flow.

## Solution Overview

Four enhancements that make the landing page feature production-ready:

1. **Page Management API** — CRUD endpoints with submission counts and page duplication
2. **SEO Metadata** — Template-based meta tags injected at generation time
3. **Stitch Integration** — API key onboarding via chat + HTML import flow
4. **Dashboard Widget** — Compact card showing pages, stats, and quick actions

## Deferred to Phase 2

- Full landing pages management page (dedicated route, not just widget)
- AI-powered SEO metadata generation (Gemini-based)
- Stitch visual editor embedding
- A/B testing with traffic splitting

---

## Section 1: Page Management API

Extend existing `app/routers/pages.py` with authenticated CRUD endpoints. All user-scoped via `Depends(get_current_user_id)`.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/pages` | List user's pages with submission counts |
| `GET` | `/pages/{page_id}` | Get single page (update: add user_id scoping for auth) |
| `PATCH` | `/pages/{page_id}` | Update title, html_content, metadata, slug |
| `DELETE` | `/pages/{page_id}` | Delete page (explicit cleanup — see cascade note below) |
| `POST` | `/pages/{page_id}/publish` | Set published=true, published_at=now |
| `POST` | `/pages/{page_id}/unpublish` | Set published=false |
| `POST` | `/pages/{page_id}/duplicate` | Clone page with "-copy" slug suffix, unpublished |
| `POST` | `/pages/import` | Create page from pasted HTML (Stitch import flow) |

### Submission Count Enrichment

The `GET /pages` endpoint returns a `submission_count` per page. Implementation options:

**Approach:** Use a Supabase RPC function that joins `landing_pages` with a count subquery on `form_submissions`:

```sql
CREATE OR REPLACE FUNCTION get_user_pages_with_counts(p_user_id UUID)
RETURNS TABLE(
    id UUID, title TEXT, slug TEXT, published BOOLEAN,
    published_at TIMESTAMPTZ, created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ, submission_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        lp.id, lp.title, lp.slug, lp.published,
        lp.published_at, lp.created_at, lp.updated_at,
        COALESCE(COUNT(fs.id), 0) AS submission_count
    FROM landing_pages lp
    LEFT JOIN form_submissions fs ON fs.page_id = lp.id
    WHERE lp.user_id = p_user_id
    GROUP BY lp.id
    ORDER BY lp.updated_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

This goes in a new migration file.

### Pre-existing Bug: Fallback Insert in `pages.py`

The P0 fix added a fallback insert path in `submit_lead()` that writes to `form_submissions` without `form_id` or `user_id` — both are `NOT NULL` in the schema. This migration must fix this by making `form_id` nullable:

```sql
ALTER TABLE form_submissions ALTER COLUMN form_id DROP NOT NULL;
```

This allows direct page-level submissions (no form configured) to persist correctly. The RPC count query already handles this via `LEFT JOIN` on `page_id`.

### Delete Cascade Path

Cascade chain: `landing_pages` → `landing_forms` (CASCADE) → `form_submissions` (CASCADE via `form_id`). However, submissions without a `form_id` (from the fallback path) only get `page_id` SET NULL — they become orphaned.

**Fix:** The `DELETE /pages/{page_id}` endpoint must explicitly delete orphaned submissions before deleting the page:

```python
# Delete submissions directly linked to page (no form)
supabase.table("form_submissions").delete().eq("page_id", page_id).is_("form_id", "null").execute()
# Then delete the page (FK cascades handle the rest)
supabase.table("landing_pages").delete().eq("id", page_id).eq("user_id", user_id).execute()
```

### Duplicate Endpoint

Clones the page row with:
- New UUID
- Slug suffixed with `-copy` (or `-copy-2` if exists)
- `published = false`
- `published_at = null`
- New `created_at` and `updated_at`
- Same `html_content` and `metadata`

### Import Endpoint

`POST /pages/import` accepts:
```json
{
    "title": "My Stitch Page",
    "html_content": "<html>...</html>",
    "source": "stitch_import"
}
```

Creates a new page with auto-generated slug, SEO meta tags injected into the HTML `<head>`, and `metadata.source` set for tracking origin. Returns the created page with its URL.

### Slug Conflict Handling

When updating a slug via `PATCH`, if the new slug collides with an existing slug for the same user, return HTTP 409 Conflict: `{"detail": "A page with this slug already exists"}`. Catch the unique constraint violation from Supabase.

### Duplicate Slug Algorithm

Query for existing slugs matching `{base_slug}-copy%`. Parse highest numeric suffix. If no copies exist, use `-copy`. Otherwise use `-copy-N` where N is highest + 1.

### Auth Pattern

All new endpoints use `user_id: str = Depends(get_current_user_id)` and `request: Request` (for rate limiter). Follows existing pattern in `app/routers/briefing.py`.

---

## Section 2: SEO Metadata

Template-based meta tags added at generation time. No AI call needed — uses existing headline/subheadline data.

### Tags Injected

Added after `<title>` in every generated `<head>`:

```html
<meta name="description" content="{subheadline}">
<meta property="og:title" content="{headline}">
<meta property="og:description" content="{subheadline}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{headline}">
<meta name="twitter:description" content="{subheadline}">
```

### Files Modified

- `app/mcp/tools/landing_page.py:generate_html()` — insert meta block after `<title>` tag
- `app/mcp/tools/stitch.py:generate_html_fallback()` — same pattern
- Import endpoint (`POST /pages/import`) — inject SEO tags into imported HTML if `<meta name="description">` is not already present

### User Override

Users can later customize SEO fields via `PATCH /pages/{page_id}` by updating `metadata.seo` fields. The rendering endpoint (`GET /landing/{slug}`) will use overrides from `metadata.seo` if present, falling back to inline tags in the HTML.

---

## Section 3: Stitch Integration

### 3a: API Key Onboarding

**Trigger:** User asks to create a landing page AND `STITCH_API_KEY` is not configured.

**Agent flow:**
1. Check `mcp_config.is_stitch_configured()` before calling Stitch API
2. If not configured, proactively tell the user (don't silently fall back)
3. Offer to accept the key via chat: "Paste your Stitch API key here and I'll configure it"
4. If user pastes key: validate with lightweight Stitch health check, write to config
5. If user declines: offer local template fallback with clear quality tradeoff

**New tool:** `configure_stitch_api_key(api_key: str)` in `app/mcp/tools/stitch.py`
- Writes key to `.env` file (appends `STITCH_API_KEY=...`)
- Sets `os.environ["STITCH_API_KEY"] = api_key` for immediate effect
- Clears config cache via `get_mcp_config.cache_clear()` so `is_stitch_configured()` returns True
- Validates key with Stitch API health endpoint
- Returns success/failure status
- Never echoes the key back in response

**Updated wrapper:** `mcp_stitch_landing_page` in `agent_tools.py` returns structured `{"status": "not_configured", "message": "..."}` instead of silently falling back to local generation.

**Marketing Agent instructions:** Add Stitch onboarding guidance to `app/agents/marketing/` instructions.

### 3b: HTML Import Flow

Two paths for importing Stitch-designed pages:

**Via API:** `POST /pages/import` (defined in Section 1)

**Via Chat:** User says "import this landing page" and pastes HTML. The Marketing Agent:
1. Receives the HTML in the message
2. Calls `create_landing_page(user_id, title, html_content)` tool
3. Confirms: "Landing page saved as draft. View it at /landing/{slug}"

**SEO injection on import:** If the imported HTML lacks `<meta name="description">`, inject template-based tags using the title as headline/subheadline.

---

## Section 4: Landing Pages Dashboard Widget

### Component: `LandingPagesWidget.tsx`

Compact card on the main persona dashboard, following the CalendarWidget pattern.

**Props:** `{ definition: WidgetDefinition; onAction?: (action: string, data: any) => void }`

#### Layout

**Header Row:**
- Title: "Landing Pages"
- Quick stats: `N published` · `N drafts` · `N leads`
- "Create New" button

**Page List (max 5 recent):**
- Each row: title, status pill (Published=green / Draft=gray), submission count, relative time
- Click row → expands inline:
  - Preview link (opens `/landing/{slug}` in new tab)
  - Publish/Unpublish toggle
  - Duplicate button
  - Delete button (with confirmation)
  - "Import HTML" button

**Import Modal:**
- Triggered by "Import HTML" button
- Textarea for pasting HTML + title input
- Calls `POST /pages/import`
- New page appears in list

**Empty State:**
- "No landing pages yet"
- CTA: "Create Landing Page" (triggers chat) and "Import from Stitch" (opens import modal)

#### Data

- Fetch: `GET /pages` on mount
- Realtime: Supabase subscription on `landing_pages` table
- Optimistic updates on publish/unpublish/delete

#### Registration

Register in `WidgetRegistry.tsx` as `'landing_pages'` with dynamic import.

---

## Section 5: Implementation & Build Order

### Task 1: Database Migration (submission count RPC)
- Create: `supabase/migrations/XXXXXXXX_landing_page_counts_rpc.sql`

### Task 2: Page Management API
- Modify: `app/routers/pages.py` — add 6 new endpoints
- Uses existing `get_service_client()` and auth patterns

### Task 3: SEO Meta Tags
- Modify: `app/mcp/tools/landing_page.py` — inject meta in `generate_html()`
- Modify: `app/mcp/tools/stitch.py` — inject meta in `generate_html_fallback()`

### Task 4: Stitch Onboarding + Import
- Modify: `app/mcp/tools/stitch.py` — add `configure_stitch_api_key()` tool
- Modify: `app/mcp/agent_tools.py` — return `not_configured` status
- Modify: Marketing Agent instructions

### Task 5: Frontend Widget
- Create: `frontend/src/services/landing-pages.ts` — API client
- Create: `frontend/src/components/widgets/LandingPagesWidget.tsx`
- Modify: `frontend/src/components/widgets/WidgetRegistry.tsx`

### Task 6: Lint & Verify
- Run backend tests and linting
- Run frontend build

### Dependency Chain

```
Task 1 (Migration) → Task 2 (API) → Task 5 (Widget)
Task 3 (SEO) — independent
Task 4 (Stitch) — independent
Task 6 (Verify) — after all
```

Tasks 1+3+4 can run in parallel. Task 2 needs Task 1. Task 5 needs Task 2.

## Files to Create

| File | Type |
|------|------|
| `supabase/migrations/XXXXXXXX_landing_page_counts_rpc.sql` | New migration |
| `frontend/src/services/landing-pages.ts` | New API client |
| `frontend/src/components/widgets/LandingPagesWidget.tsx` | New widget |

## Files to Modify

| File | Change |
|------|--------|
| `app/routers/pages.py` | Add CRUD + import + duplicate endpoints |
| `app/mcp/tools/landing_page.py` | Inject SEO meta tags in generate_html() |
| `app/mcp/tools/stitch.py` | SEO tags + configure_stitch_api_key() tool |
| `app/mcp/agent_tools.py` | Return not_configured status for Stitch |
| `frontend/src/components/widgets/WidgetRegistry.tsx` | Register landing_pages widget |
| `frontend/src/types/widgets.ts` | Add `'landing_pages'` to WidgetType union, create LandingPagesData interface, update isValidWidgetType and validateWidgetDefinition |
| Marketing Agent instructions | Add Stitch onboarding guidance |
