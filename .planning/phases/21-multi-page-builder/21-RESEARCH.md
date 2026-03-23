# Phase 21: Multi-Page Builder - Research

**Researched:** 2026-03-23
**Domain:** Stitch MCP sequential page generation, HTML navigation injection, shared design components, sitemap mutation, multi-page preview, SSE streaming
**Confidence:** HIGH (architecture patterns verified from codebase inspection of Phases 16-20; Stitch MCP tool schema verified from live stitch_mcp.py; all DB schema confirmed from migration SQL)

---

## Summary

Phase 21 extends the single-screen building loop (Phase 19/20) into a full multi-page generation engine. The core concept is the **stitch-loop baton pattern**: given an approved SITE.md sitemap, the system iterates through each page entry in order, calling `generate_screen_from_text` once per page with (a) the locked design system prepended and (b) a growing nav-context baton appended. Between each page generation, the baton is updated with the newly generated page's slug and title, so every subsequent page "knows" what pages already exist and can generate consistent navigation.

The critical discovery is that Stitch generates **standalone HTML documents** — there is no shared runtime or router. Inter-page navigation must be injected as post-processing into the persisted HTML: after `persist_screen_assets` stores the HTML, a lightweight Python post-processor rewrites all in-page `<a href="...">` anchors to point at the correct sibling page HTML URLs (Supabase Storage public URLs). This avoids any dependency on Stitch understanding multi-page concepts.

Shared header/footer components are handled via prompt engineering: the generation prompt for every page after page 1 includes the header HTML extracted from page 1, instructing Stitch to use the same header. This is simpler and more reliable than post-processing DOM injection. An alternative (post-processing DOM injection with BeautifulSoup) is documented as fallback.

The verification stage (FLOW-06) is a new `verifying` GSD stage rendered in a tab-switcher frontend page — each page is shown in a sandboxed iframe, navigable by clicking page tabs. No new backend infra is needed; verification consumes the already-persisted HTML URLs from the DB.

**Primary recommendation:** Implement the baton loop as a new `multi_page_service.py` async generator that yields per-page SSE events (`page_started`, `page_complete`, `build_complete`). Navigation injection runs as a synchronous post-processing step after all pages are generated. The verification stage is a new Next.js page at `/app-builder/[projectId]/verifying` that fetches all approved screens and renders a tab-based multi-page preview.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PAGE-01 | Stitch-loop baton pattern autonomously generates multi-page sites: SITE.md sitemap → generate screen → update nav → next | `generate_screen_from_text` verified in Phases 19/20; baton = growing nav context string appended to each prompt; sequential `await` required (asyncio.Lock) |
| PAGE-02 | System auto-generates navigation linking all pages together | Stitch generates standalone HTML; nav linking requires post-processing to rewrite `<a>` hrefs to Supabase Storage URLs; Python `html.parser` in stdlib handles this without new deps |
| PAGE-03 | Shared components (header, footer, nav) derived from DESIGN.md are reused across all pages | Prompt engineering approach: inject DESIGN.md raw_markdown as header context into every page prompt; first-page header HTML optionally extracted and re-injected |
| PAGE-04 | User can reorder, add, or remove pages from the sitemap at any point during the build | Sitemap is stored in `app_projects.sitemap` JSONB; a PATCH endpoint updates it; already-generated `app_screens` rows for removed pages are soft-deleted or marked; no re-generation triggered automatically |
| FLOW-06 | After all screens are built, a verification stage shows the complete app for final review | New `/app-builder/[projectId]/verifying` page; tab switcher shows each approved screen's `html_url` in a sandboxed iframe; stage advancement to `verifying` via existing `/stage` endpoint |
</phase_requirements>

---

## Standard Stack

### Core (all already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `app/services/stitch_mcp.py` | project | `generate_screen_from_text` via asyncio.Lock-serialized MCP calls | Established Phase 16; all page calls use same `call_tool()` interface |
| `app/services/stitch_assets.py` | project | `persist_screen_assets()` — download HTML/screenshots to Supabase Storage | Mandatory before yielding events; same pattern as Phases 19/20 |
| `app/services/screen_generation_service.py` | project | Reference implementation for sequential Stitch calls + SSE event pattern | Multi-page service mirrors this structure at page granularity instead of variant granularity |
| `app/services/iteration_service.py` | project | `_get_locked_design_markdown()` — fetch locked design system raw_markdown | Re-used in multi-page service to build per-page prompts |
| `app/routers/app_builder.py` | project | SSE StreamingResponse pattern; auth; Supabase client calls | All new endpoints extend this router |
| Python stdlib `html.parser` | 3.10 | Parse and rewrite `<a href>` anchors in generated HTML for nav injection | Zero new deps; `HTMLParser` subclass pattern works for this scope |
| FastAPI `StreamingResponse` | existing | SSE streaming of per-page progress to frontend | Same pattern: `yield f"data: {json.dumps(event)}\n\n"` |
| Next.js App Router | existing | New `verifying` page for multi-page preview tab switcher | Same routing as `building` page |
| Tailwind CSS 4 | existing | All new frontend components | Project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `lucide-react` | existing | Icons for page tabs, status indicators | Same icon pattern as GsdProgressBar |
| pytest + `unittest.mock` | existing | Backend service unit tests | `AsyncMock` for `call_tool`, `MagicMock` for Supabase chain |
| vitest + `@testing-library/react` | existing | Frontend component tests for tab switcher | Project frontend test standard |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Prompt-engineering for shared nav | BeautifulSoup DOM injection | BeautifulSoup adds a new dep; prompt engineering requires no new packages and keeps Stitch responsible for rendering consistency. BeautifulSoup is documented as fallback if prompt approach produces inconsistent results. |
| Python stdlib `html.parser` for nav rewrite | `lxml` or `beautifulsoup4` | stdlib is always available; for simple `<a href>` rewriting it is sufficient. lxml is faster but overkill for small HTML files (~50KB). |
| Tab-based multi-page preview | Dropdown + single iframe | Tabs give all pages visible at a glance, consistent with the Phase 19 VariantComparisonGrid pattern. Dropdown risks hiding pages and adds interaction friction. |
| Generating pages fully in parallel | Sequential baton generation | Parallel would deadlock the `asyncio.Lock` inside `StitchMCPService`. The Lock serializes all MCP calls — this is a hard constraint from Phase 16. |

**Installation:**
```bash
# No new packages required for backend — all stdlib
# No new packages required for frontend — existing Tailwind + lucide-react
```

---

## Architecture Patterns

### Recommended Project Structure
```
app/services/
  multi_page_service.py          # New: baton-loop generator, nav injection
app/routers/
  app_builder.py                 # Extended: 3 new endpoints
tests/unit/app_builder/
  test_multi_page_service.py     # New: unit tests for baton loop + nav injection
frontend/src/app/app-builder/[projectId]/
  verifying/
    page.tsx                     # New: tab-based multi-page verification
frontend/src/components/app-builder/
  MultiPageProgress.tsx          # New: per-page progress indicator
  MultiPageVerificationView.tsx  # New: tab switcher + iframe for verification
frontend/src/services/
  app-builder.ts                 # Extended: buildAllPages(), updateSitemap(),
                                 #           listProjectScreens()
frontend/src/types/
  app-builder.ts                 # Extended: MultiPageEvent, new event step types
```

### Pattern 1: Stitch-Loop Baton Pattern

**What:** Sequential `generate_screen_from_text` calls where each call's prompt includes a growing "pages built so far" context (the baton) so Stitch generates consistent navigation structure.

**When to use:** Any time a sitemap has 2+ pages to generate autonomously.

**Example:**
```python
# app/services/multi_page_service.py
async def build_all_pages(
    project_id: str,
    user_id: str,
    sitemap: list[dict],
    design_markdown: str,
    stitch_project_id: str,
) -> AsyncIterator[dict[str, Any]]:
    """Generate all pages sequentially using the baton pattern.

    Yields SSE-compatible events:
      {"step": "page_started", "page_index": i, "page_slug": ..., "total_pages": n}
      {"step": "page_complete", "page_index": i, "page_slug": ...,
       "screen_id": ..., "html_url": ..., "screenshot_url": ...}
      {"step": "build_complete", "total_pages": n, "screens": [...]}
    """
    service = get_stitch_service()
    supabase = get_service_client()
    total = len(sitemap)
    screens_built: list[dict] = []

    for i, page in enumerate(sitemap):
        page_slug = page.get("page", f"page-{i+1}")
        page_title = page.get("title", page_slug.title())

        yield {
            "step": "page_started",
            "page_index": i,
            "page_slug": page_slug,
            "total_pages": total,
        }

        # Build baton: nav context from already-generated pages
        nav_context = _build_nav_baton(screens_built)

        # Build prompt: design system + page-specific + nav context
        prompt = _build_page_prompt(
            design_markdown=design_markdown,
            page_title=page_title,
            page_slug=page_slug,
            sections=page.get("sections", []),
            nav_context=nav_context,
        )

        # Sequential Stitch call — CRITICAL: never asyncio.gather, Lock deadlocks
        stitch_response = await service.call_tool(
            "generate_screen_from_text",
            {"prompt": prompt, "projectId": stitch_project_id, "deviceType": "DESKTOP"},
        )

        screen_id = str(uuid4())
        # Insert app_screens row
        supabase.table("app_screens").insert({
            "id": screen_id,
            "project_id": project_id,
            "user_id": user_id,
            "name": page_title,
            "page_slug": page_slug,
            "device_type": "DESKTOP",
            "order_index": i,
            "approved": False,
            "stitch_project_id": stitch_project_id,
        }).execute()

        # Persist assets before yielding
        persisted = await persist_screen_assets(
            stitch_response=stitch_response,
            user_id=user_id,
            project_id=project_id,
            screen_id=screen_id,
            variant_index=0,
        )

        # Insert screen_variants row (single variant for baton generation)
        stitch_screen_id = stitch_response.get("screenId", "")
        variant_id = str(uuid4())
        supabase.table("screen_variants").insert({
            "id": variant_id,
            "screen_id": screen_id,
            "user_id": user_id,
            "variant_index": 0,
            "stitch_screen_id": stitch_screen_id,
            "html_url": persisted["html_url"],
            "screenshot_url": persisted["screenshot_url"],
            "prompt_used": prompt,
            "is_selected": True,
            "iteration": 1,
        }).execute()

        screen_entry = {
            "page_index": i,
            "page_slug": page_slug,
            "page_title": page_title,
            "screen_id": screen_id,
            "variant_id": variant_id,
            "html_url": persisted["html_url"],
            "screenshot_url": persisted["screenshot_url"],
        }
        screens_built.append(screen_entry)

        yield {"step": "page_complete", **screen_entry}

    yield {
        "step": "build_complete",
        "total_pages": total,
        "screens": screens_built,
    }
```

### Pattern 2: Nav Baton Builder

**What:** Accumulates a growing navigation context string as pages are built, passed to each subsequent page's prompt.

**When to use:** Inside the baton loop, called before each `generate_screen_from_text` call.

**Example:**
```python
def _build_nav_baton(screens_built: list[dict]) -> str:
    """Build a navigation context string from already-generated pages.

    Returns empty string for first page (no nav context yet).
    Returns a human-readable nav map for subsequent pages.
    """
    if not screens_built:
        return ""
    nav_lines = ["Navigation structure — link to these pages:"]
    for s in screens_built:
        nav_lines.append(f"  - {s['page_title']} → /{s['page_slug']}")
    return "\n".join(nav_lines)

def _build_page_prompt(
    design_markdown: str,
    page_title: str,
    page_slug: str,
    sections: list[str],
    nav_context: str,
) -> str:
    parts = []
    if design_markdown:
        parts.append(f"DESIGN SYSTEM:\n{design_markdown}")
    parts.append(f"Generate the '{page_title}' page (slug: {page_slug})")
    if sections:
        parts.append(f"Sections: {', '.join(sections)}")
    if nav_context:
        parts.append(nav_context)
    return "\n\n".join(parts)
```

### Pattern 3: Navigation Link Injection (Post-Processing)

**What:** After all pages are generated, rewrite `<a href="/page-slug">` style links in every persisted HTML to point to the sibling page's Supabase Storage `html_url`. Uses Python stdlib `html.parser`.

**When to use:** Called once after `build_complete` event, passing the full `screens_built` map. Re-uploads modified HTML to Supabase Storage.

**Example:**
```python
from html.parser import HTMLParser
import re

class NavLinkRewriter(HTMLParser):
    """Rewrite <a href="/slug"> to absolute Supabase Storage URLs."""

    def __init__(self, slug_to_url: dict[str, str]) -> None:
        super().__init__()
        self.slug_to_url = slug_to_url
        self.output: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "a":
            new_attrs = []
            for name, val in attrs:
                if name == "href" and val:
                    # Match /page-slug or page-slug (relative)
                    slug = val.lstrip("/")
                    if slug in self.slug_to_url:
                        val = self.slug_to_url[slug]
                new_attrs.append((name, val))
            attrs = new_attrs
        attr_str = "".join(
            f' {k}="{v}"' if v is not None else f" {k}"
            for k, v in attrs
        )
        self.output.append(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag: str) -> None:
        self.output.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.output.append(data)

async def inject_navigation_links(
    screens: list[dict],  # from screens_built in baton loop
    user_id: str,
    project_id: str,
) -> None:
    """Re-download, rewrite nav hrefs, re-upload each page's HTML."""
    slug_to_url = {s["page_slug"]: s["html_url"] for s in screens}
    supabase = get_service_client()

    async with httpx.AsyncClient() as client:
        for screen in screens:
            try:
                resp = await client.get(screen["html_url"], follow_redirects=True)
                html_content = resp.text

                rewriter = NavLinkRewriter(slug_to_url)
                rewriter.feed(html_content)
                new_html = "".join(rewriter.output)

                # Re-upload — same path, upsert=true
                storage_path = f"{user_id}/{project_id}/{screen['screen_id']}/v0/screen.html"
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: supabase.storage.from_("stitch-assets").upload(
                        path=storage_path,
                        file=new_html.encode("utf-8"),
                        file_options={"content-type": "text/html", "upsert": "true"},
                    ),
                )
            except Exception as e:
                logger.warning("Nav injection failed for %s: %s", screen["page_slug"], e)
                # Non-fatal — page still works, just without nav links
```

### Pattern 4: Verification Stage Tab Switcher

**What:** A new `/app-builder/[projectId]/verifying` page that fetches all approved `app_screens` for the project, renders tabs for each page, and shows the selected page's `html_url` in a sandboxed iframe. Stage advancement to `verifying` uses the existing PATCH `/stage` endpoint.

**When to use:** After `build_complete` event, user clicks "Review All Pages" which calls `advanceStage(projectId, 'verifying')` then navigates to `/verifying`.

**Example:**
```tsx
// frontend/src/app/app-builder/[projectId]/verifying/page.tsx
'use client';
import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { listProjectScreens, advanceStage } from '@/services/app-builder';
import type { AppScreen } from '@/types/app-builder';

export default function VerifyingPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [screens, setScreens] = useState<AppScreen[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    listProjectScreens(projectId).then(setScreens).catch(console.error);
  }, [projectId]);

  const activeScreen = screens[activeIndex];

  return (
    <div>
      {/* Page tab switcher */}
      <div className="flex gap-2 mb-4 border-b border-slate-200">
        {screens.map((s, i) => (
          <button
            key={s.id}
            onClick={() => setActiveIndex(i)}
            className={i === activeIndex ? 'border-b-2 border-indigo-600 ...' : '...'}
          >
            {s.name}
          </button>
        ))}
      </div>
      {/* Live iframe preview */}
      {activeScreen && (
        <iframe
          key={activeScreen.id}  // force remount on tab change (Phase 19 pattern)
          src={activeScreen.selected_html_url}
          sandbox="allow-scripts allow-same-origin"
          className="w-full h-[80vh] rounded-lg border"
        />
      )}
      <button onClick={() => advanceStage(projectId, 'shipping')}>
        Approve and Ship
      </button>
    </div>
  );
}
```

### Pattern 5: Sitemap Mutation (PAGE-04)

**What:** PATCH `/app-builder/projects/{id}/sitemap` updates `app_projects.sitemap` JSONB. Already-generated `app_screens` rows for pages removed from the sitemap are marked `approved=false` to exclude them from verification. No automatic re-generation is triggered.

**When to use:** User reorders, adds, or removes pages via the existing SitemapCard component (already has `onChange` prop).

**Example:**
```python
@router.patch("/app-builder/projects/{project_id}/sitemap")
async def update_sitemap(
    project_id: str,
    body: UpdateSitemapRequest,  # {"sitemap": [...]}
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    supabase = get_service_client()
    supabase.table("app_projects").update(
        {"sitemap": body.sitemap, "build_plan": []}  # clear stale build plan
    ).eq("id", project_id).eq("user_id", user_id).execute()
    return {"success": True, "sitemap": body.sitemap}
```

### Anti-Patterns to Avoid

- **asyncio.gather for Stitch calls:** Deadlocks the `asyncio.Lock` in `StitchMCPService`. Every page generation is a sequential `await service.call_tool(...)` — this is a hard constraint from Phase 16.
- **Generating nav HTML by post-processing with regex:** Regex on HTML is fragile. Use `html.parser` `HTMLParser` subclass or accept prompt-engineered nav without rewriting. Never `re.sub` on raw HTML.
- **Advancing to `verifying` stage before `build_complete` fires:** The stage machine must stay on `building` until the full baton loop finishes. Only advance on `build_complete` (or explicit user action).
- **Re-fetching html_url from Stitch after persist_screen_assets:** `persist_screen_assets` already returns permanent Supabase Storage URLs. Do not use the short-lived Stitch URL after persistence — it expires in minutes.
- **Storing nav context in DB:** The baton is ephemeral — it only exists during the generation run. It does not need to be persisted to DB.
- **Requiring page_slug column migration on app_screens:** The `page_slug` concept is already supported — `screen_generation_service.py` already accepts `page_slug` and stores it. Confirm the column exists in migration; if absent, add it via new migration.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML link rewriting | Custom regex substitution | stdlib `html.parser.HTMLParser` subclass | Regex on HTML breaks on attribute quoting styles, nested elements, and `<script>` tag content |
| Multi-page router in preview | Custom client-side JS router injected into HTML | Tab-switcher UI in the React host page switching `src` on a single iframe | Injecting a router into Stitch HTML is brittle; React tab switching is reliable and already used in VariantComparisonGrid |
| Sitemap state management | Separate sitemap DB table | `app_projects.sitemap` JSONB (already exists) | sitemap is already in the schema and the SitemapCard component already reads/writes it |
| Per-page SSE state in frontend | Redux/Zustand store | Local accumulator array pattern (same as Phase 19 `BuildingPage`) | Phase 19 established the local accumulator pattern to avoid stale-state closures; use the same pattern |
| Design system injection | Re-fetch design_systems table on every page | Call `_get_locked_design_markdown()` once before the loop, pass as parameter | Avoids N DB calls during the loop; design system does not change mid-generation |

**Key insight:** The entire multi-page generation loop is a higher-level orchestration of the exact same Stitch `generate_screen_from_text` call already proven in Phase 19. The new complexity is sequencing and context accumulation, not new Stitch API surface.

---

## Common Pitfalls

### Pitfall 1: Missing page_slug Column on app_screens
**What goes wrong:** `screen_generation_service.py` accepts `page_slug` as a parameter and uses it in prompts, but the `app_screens` schema migration (`20260321400000_app_builder_schema.sql`) does NOT include a `page_slug` column — the `page_type TEXT NOT NULL DEFAULT 'page'` exists but no `page_slug`. The existing code inserts `page_slug` into the dict but Supabase silently ignores unknown columns.
**Why it happens:** The migration predates the decision to use `page_slug` as a routing concept, which was added in Phase 19 service code without a schema update.
**How to avoid:** Add a `page_slug TEXT` column migration at the start of Phase 21 (Wave 0). Without it, the verification tab switcher cannot distinguish pages by slug.
**Warning signs:** `SELECT page_slug FROM app_screens` throws `column "page_slug" does not exist`.

### Pitfall 2: asyncio.Lock Deadlock from Parallel Generation Attempt
**What goes wrong:** Any attempt to use `asyncio.gather` across multiple `service.call_tool()` calls causes an immediate deadlock — the Lock inside `StitchMCPService` is held by the first coroutine and the second waits forever.
**Why it happens:** `StitchMCPService._lock` is a single `asyncio.Lock()` shared across all calls. This is documented in both `screen_generation_service.py` and `iteration_service.py` headers.
**How to avoid:** The baton loop MUST be a sequential `for` loop with `await service.call_tool(...)` inside. Never gather, never `asyncio.create_task` across tool calls.
**Warning signs:** Service appears to hang; no SSE events arrive after the first page.

### Pitfall 3: Stitch Signed URL Expiry During Navigation Injection
**What goes wrong:** If nav injection runs after a delay and tries to re-download HTML from the Stitch signed URL (not the Supabase URL), the URL may have expired.
**Why it happens:** Stitch signed URLs expire in minutes. `persist_screen_assets` stores the permanent URL in the DB, but the short-lived URL is also in the raw Stitch response.
**How to avoid:** Always re-download from the Supabase Storage `html_url` (the persisted permanent URL), never from the raw Stitch response. Use `screen_entry["html_url"]` from `screens_built`, which contains the Supabase URL.
**Warning signs:** `httpx.HTTPStatusError: 403` or `404` when downloading HTML for nav injection.

### Pitfall 4: SitemapCard Missing Remove-Page Capability
**What goes wrong:** The existing `SitemapCard` component has `addPage()` but no `removePage()` function (PAGE-04 requires remove). Users cannot remove pages from the sitemap.
**Why it happens:** Phase 18 SitemapCard was built for the research/brief phase where removing pages was not a priority.
**How to avoid:** Extend `SitemapCard` with a delete button per row (using a `removePage(index: number)` handler). This is a small UI change but critical for PAGE-04.
**Warning signs:** PAGE-04 MUST requirement fails — user cannot remove pages.

### Pitfall 5: Verification iframe CORS / CSP on Supabase Storage HTML
**What goes wrong:** Supabase Storage serves HTML with `Content-Security-Policy` headers that may block inline scripts in the generated Stitch HTML, causing a blank iframe in the verification stage.
**Why it happens:** Stitch-generated HTML includes inline `<script>` and `<style>` tags. The `stitch-assets` bucket is `public=true` but the Supabase CDN may set restrictive CSP on served files.
**How to avoid:** Use `sandbox="allow-scripts allow-same-origin"` on the iframe (already established in `DevicePreviewFrame`). If Supabase CDN adds CSP headers, serve HTML through a FastAPI proxy endpoint that strips CSP headers. Confirm the existing `DevicePreviewFrame` pattern works before building the verification view — it already handles this in Phase 19.
**Warning signs:** Blank iframe in DevicePreviewFrame for any page's `html_url`.

### Pitfall 6: Frontend Accumulator Stale-State Closure During SSE Stream
**What goes wrong:** Using `setScreens(prev => [...prev, newPage])` inside an SSE event handler closure captures stale state if the closure is created once and reused.
**Why it happens:** React state updates are async; event handler closures created at mount time do not see subsequent state updates.
**How to avoid:** Use the local accumulator array pattern established in Phase 19 `BuildingPage`: maintain a `const accumulated: ScreenEntry[] = []` array mutated in the closure, then call `setScreens([...accumulated])` to sync to React state. This is the exact same pattern used for `variant_generated` events.
**Warning signs:** Only one screen appears in UI after multi-page generation completes even though multiple `page_complete` events were received.

---

## Code Examples

Verified patterns from existing codebase:

### SSE Streaming Pattern (from app_builder.py)
```python
# Source: app/routers/app_builder.py — generate_screen endpoint
async def event_generator():
    async for event in multi_page_service.build_all_pages(...):
        yield f"data: {json.dumps(event)}\n\n"

return StreamingResponse(
    event_generator(),
    media_type="text/event-stream",
    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
)
```

### SSE Consumer Pattern (from frontend/src/services/app-builder.ts)
```typescript
// Source: frontend/src/services/app-builder.ts — generateScreen()
// New buildAllPages() follows identical fetch ReadableStream pattern
export async function buildAllPages(
  projectId: string,
  onEvent: (event: MultiPageEvent) => void,
): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/app-builder/projects/${projectId}/build-all`, {
    method: 'POST',
    headers,
  });
  if (!res.ok || !res.body) throw new Error('Build failed to start');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try { onEvent(JSON.parse(line.slice(6))); } catch { /* skip malformed */ }
      }
    }
  }
}
```

### Design System Fetch (from iteration_service.py)
```python
# Source: app/services/iteration_service.py — _get_locked_design_markdown()
# Fetch ONCE before the baton loop, not once per page
design_markdown = await _get_locked_design_markdown(project_id, user_id)
# Pass to build_all_pages — avoids N DB calls during loop
```

### iframe Key-Remount Pattern (from Phase 19)
```typescript
// Source: frontend/src/app/app-builder/[projectId]/building/page.tsx
// Force iframe remount when page changes — avoids stale content
<iframe
  key={activeScreen.id}        // changed key = React unmounts and remounts iframe
  src={activeScreen.html_url}
  sandbox="allow-scripts allow-same-origin"
  className="w-full h-[80vh] border rounded-lg"
/>
```

### Supabase Storage Re-upload for Nav Injection
```python
# Re-upload pattern from stitch_assets.py — used for nav injection
loop = asyncio.get_event_loop()
await loop.run_in_executor(
    None,
    lambda: supabase.storage.from_("stitch-assets").upload(
        path=storage_path,
        file=modified_html_bytes,
        file_options={"content-type": "text/html", "upsert": "true"},
    ),
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-request MCP subprocess | Persistent singleton with asyncio.Lock | Phase 16 | All Stitch calls are sequential; gather = deadlock |
| Stitch-generated HTML with short-lived URLs | Download + Supabase Storage persistence | Phase 16 | Nav injection re-downloads from permanent URL, never from Stitch directly |
| Single-screen generation | Sequential baton loop | Phase 21 | Nav context accumulates across pages |
| Manual stage advancement | Decoupled approve + advance actions | Phase 20 | `approve_screen` does NOT advance stage; explicit PATCH `/stage` required |

**Deprecated/outdated:**
- Direct Stitch URL usage after generation: always use persisted Supabase Storage URL. Stitch URLs expire in minutes.

---

## Open Questions

1. **Does `app_screens` have a `page_slug` column in the DB?**
   - What we know: `screen_generation_service.py` accepts `page_slug` parameter and uses it in Stitch prompts. The migration SQL `20260321400000_app_builder_schema.sql` does NOT have this column — only `page_type TEXT DEFAULT 'page'`.
   - What's unclear: Whether a subsequent migration added it (only 4 migration files exist, none appear to add `page_slug`).
   - Recommendation: Wave 0 plan should add a migration `ALTER TABLE app_screens ADD COLUMN IF NOT EXISTS page_slug TEXT;` to guarantee the column exists for verification tab routing.

2. **Does Stitch consistently generate `<a>` href anchors with page slugs?**
   - What we know: Stitch generates standalone HTML. We cannot verify from codebase alone what HTML structure Stitch produces for navigation elements.
   - What's unclear: Whether Stitch uses `/page-slug`, `page-slug.html`, `#page-slug`, or other href formats.
   - Recommendation: Nav injection post-processing should be tolerant — strip both leading `/` and trailing `.html` from href values before matching against the slug map. If nav injection produces no rewrites (zero hrefs matched), log a warning but continue — nav is an enhancement, not a blocker.

3. **Does the `listProjectScreens` endpoint exist?**
   - What we know: The verification page needs to fetch all `app_screens` for a project ordered by `order_index`. The existing `app_builder.py` router has no such `GET /screens` endpoint — only per-screen variant endpoints.
   - What's unclear: Whether a general list-screens endpoint should be added now or this data comes from the `app_projects` build_plan.
   - Recommendation: Add `GET /app-builder/projects/{project_id}/screens` endpoint in this phase — returns all `app_screens` with their selected variant's `html_url` joined via a second query. Keep it simple: no joins (Supabase REST doesn't support complex joins easily), two sequential queries.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest (frontend) |
| Config file | `pytest.ini` / `vitest.config.ts` (existing) |
| Quick run command | `uv run pytest tests/unit/app_builder/test_multi_page_service.py -x` |
| Full suite command | `uv run pytest tests/unit/app_builder/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PAGE-01 | Baton loop generates N pages sequentially, yields page_started + page_complete per page, build_complete at end | unit | `uv run pytest tests/unit/app_builder/test_multi_page_service.py::test_baton_loop_yields_correct_events -x` | Wave 0 |
| PAGE-01 | Design system markdown prepended to every page prompt | unit | `uv run pytest tests/unit/app_builder/test_multi_page_service.py::test_design_system_injected_in_prompt -x` | Wave 0 |
| PAGE-01 | Nav baton grows with each page (page 2 prompt contains page 1 slug) | unit | `uv run pytest tests/unit/app_builder/test_multi_page_service.py::test_nav_baton_accumulates -x` | Wave 0 |
| PAGE-02 | NavLinkRewriter rewrites /slug hrefs to absolute URLs | unit | `uv run pytest tests/unit/app_builder/test_multi_page_service.py::test_nav_link_rewriter -x` | Wave 0 |
| PAGE-02 | inject_navigation_links re-uploads modified HTML to Supabase Storage | unit | `uv run pytest tests/unit/app_builder/test_multi_page_service.py::test_nav_injection_uploads -x` | Wave 0 |
| PAGE-03 | DESIGN.md raw_markdown appears in every page prompt | unit | `uv run pytest tests/unit/app_builder/test_multi_page_service.py::test_design_system_injected_in_prompt -x` | Wave 0 |
| PAGE-04 | PATCH /sitemap updates app_projects.sitemap and clears build_plan | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_update_sitemap -x` | Wave 0 |
| FLOW-06 | GET /screens returns all app_screens with selected html_url | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_list_project_screens -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/app_builder/ -x`
- **Per wave merge:** `uv run pytest tests/unit/app_builder/ -x && cd frontend && npx vitest run src/components/app-builder`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/app_builder/test_multi_page_service.py` — covers PAGE-01, PAGE-02, PAGE-03
- [ ] `supabase/migrations/YYYYMMDD_add_page_slug.sql` — `ALTER TABLE app_screens ADD COLUMN IF NOT EXISTS page_slug TEXT;`
- [ ] `.planning/phases/21-multi-page-builder/` directory — already created

*(Existing test infrastructure covers the router patterns; only new service file needs new test file)*

---

## Sources

### Primary (HIGH confidence)
- Codebase: `app/services/stitch_mcp.py` — asyncio.Lock serialization constraint verified directly
- Codebase: `app/services/screen_generation_service.py` — `generate_screen_from_text` call schema, `persist_screen_assets` pattern, SSE event structure
- Codebase: `app/services/iteration_service.py` — `_get_locked_design_markdown()` pattern, design system injection
- Codebase: `app/routers/app_builder.py` — full router pattern, StreamingResponse SSE, auth pattern
- Codebase: `frontend/src/app/app-builder/[projectId]/building/page.tsx` — accumulator pattern, SSE consumer, local accumulator to avoid stale-state
- Codebase: `frontend/src/services/app-builder.ts` — fetch ReadableStream SSE consumer pattern
- Codebase: `frontend/src/types/app-builder.ts` — GSD_STAGES, AppProject, ScreenVariant types
- Codebase: `frontend/src/components/app-builder/SitemapCard.tsx` — addPage exists, removePage absent (PAGE-04 gap confirmed)
- Codebase: `supabase/migrations/20260321400000_app_builder_schema.sql` — schema confirmed, page_slug column absent
- Python docs: `html.parser.HTMLParser` — stdlib, always available in Python 3.10+

### Secondary (MEDIUM confidence)
- Phase 20 RESEARCH.md — confirms Stitch `edit_screens` schema and design system injection pattern; navigation injection approach extrapolated from same principles

### Tertiary (LOW confidence)
- Assumption: Stitch generates `<a>` tags with slug-style hrefs when nav context is provided in prompt. This is inferred from Stitch being an HTML generator; actual href format is unverified until first generation run.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already in project; no new deps required
- Architecture (baton loop): HIGH — direct extension of Phase 19 `generate_screen_variants` pattern; no new Stitch API surface
- Navigation injection: MEDIUM — html.parser approach is correct but Stitch's actual href format is unverified (see Open Questions)
- Pitfalls: HIGH — page_slug gap, Lock deadlock, URL expiry all verified from codebase
- Verification stage: HIGH — tab-switcher is a known React pattern; iframe key remount proven in Phase 19

**Research date:** 2026-03-23
**Valid until:** 2026-04-22 (stable domain — Stitch MCP API, Python stdlib, existing project patterns do not change frequently)
