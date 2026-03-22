# Phase 19: Screen Generation & Preview - Research

**Researched:** 2026-03-22
**Domain:** Stitch MCP parallel variant generation, device-specific preview, iframe live preview, SSE orchestration, React side-by-side comparison UI
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCRN-01 | System generates 2-3 design variants per screen via Stitch MCP for user comparison | `generate_screen_from_text` called in parallel via `asyncio.gather` with same prompt/project but producing distinct `screenId`s; each persisted as a separate `screen_variants` row with `variant_index` 0/1/2 |
| SCRN-02 | Variants displayed side-by-side in the UI with visual comparison tools | VariantComparisonGrid component — CSS Grid with 2-3 columns; screenshot `<img>` thumbnails; selected state ring; keyboard nav |
| SCRN-03 | User can preview any screen in desktop, mobile, and tablet viewports | DevicePreviewFrame component — iframe src set to Supabase Storage HTML URL; viewport controlled by CSS `width` + `transform: scale` (not re-generation) for the chrome switcher; SCRN-04 drives actual Stitch re-generation per device |
| SCRN-04 | System generates device-specific layouts (Stitch `deviceType: DESKTOP/MOBILE/TABLET`) not just responsive CSS | `generate_screen_from_text` called once per device type for the selected variant's prompt; stored as device-specific rows on `app_screens` (one row per `device_type`) |
| FOUN-05 | Generated apps can be previewed live in browser via embedded iframe/preview pane | `<iframe src={html_url} sandbox="allow-scripts allow-same-origin">` renders permanent Supabase Storage HTML; `stitch-assets` bucket is public — no auth needed |
| BLDR-02 | Live browser preview pane showing generated app in embedded iframe | Implemented as part of the building page — iframe is shown in a resizable split-pane or full-width panel; variant switching updates `src`; device switching re-requests Stitch or scales frame |
</phase_requirements>

---

## Summary

Phase 19 is primarily an **orchestration + UI phase** — the underlying Stitch MCP integration, asset persistence, and DB schema are all live from Phase 16, and the build plan consumed here was produced by Phase 18. The work is: (1) a backend generation service that calls `generate_screen_from_text` in parallel 2-3 times per screen (for variants) and once per device type (for device-specific layouts), streams progress over SSE, and persists rows to `app_screens` + `screen_variants`; (2) a `/app-builder/[projectId]/building` Next.js page with a side-by-side variant grid and a live iframe preview pane.

The most important design decision is the **parallel-vs-sequential Stitch call strategy**. The `StitchMCPService` singleton serializes all Stitch calls through a single `asyncio.Lock` (by design — see STATE.md Phase 16 concern). Generating 2-3 variants × 3 device types = 6-9 Stitch calls per screen. These must be queued, not truly parallel. The SSE stream communicates progress per call so users see incremental progress rather than a long wait. Variants come first (DESKTOP only); device-specific generation for MOBILE/TABLET is triggered on-demand when the user switches device tabs (lazy, not eagerly upfront).

The **iframe preview** is straightforward: `stitch-assets` bucket is `public=true` (Phase 16 decision), so the permanent Supabase Storage URL is safe to load directly in a sandboxed `<iframe>`. No auth headers, no proxy needed.

**Primary recommendation:** Build a `screen_generation_service.py` async generator that reads the build plan from `app_projects`, generates variants for the selected/current build phase screen, streams `variant_generated` / `device_generated` / `ready` events over SSE. Frontend building page reads the plan, triggers generation per screen, shows VariantComparisonGrid (screenshots) + DevicePreviewFrame (live iframe). Device switching for TABLET/MOBILE calls a separate SSE endpoint to generate device variants lazily.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `StitchMCPService.call_tool` | project singleton | Generate screens via `generate_screen_from_text` | Already live from Phase 16; only interface to Stitch |
| `persist_screen_assets` | project internal | Download Stitch signed URLs → permanent Supabase Storage URLs | Phase 16 pattern; handles HTML + screenshot persistence |
| FastAPI + Pydantic v2 | project-pinned | Generation endpoint, SSE streaming, generate-device endpoint | Matches all existing routers |
| Supabase Python client | 2.27.2 | Insert `app_screens` + `screen_variants` rows | `get_service_client()` pattern — same as all prior phases |
| Next.js App Router | 16.1.4 | `/app-builder/[projectId]/building` page | Project-standard; existing `[projectId]/layout.tsx` already provides GsdProgressBar |
| React 19 | 19.2.3 | Variant grid, device switcher, iframe pane | Project-standard |
| Tailwind CSS 4 | project-pinned | All UI | All existing UI uses Tailwind only |
| framer-motion | 12.29.0 | Generation progress animation, variant reveal | Already installed; Phase 17/18 patterns established |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio.gather` | stdlib | Sequential queuing through the Lock (gather has no benefit here — Lock serializes anyway) | Use sequential `await` calls with SSE progress events between each; do NOT use `asyncio.gather` for Stitch calls |
| `google.genai` async client | project-pinned | Optional: re-enhance prompt per device type using design system tokens | Only if prompt injection differs per device — use `enhance_prompt` from Phase 16 |
| `app/services/supabase.get_service_client()` | internal | All DB writes | Service-role bypass for cross-table writes |
| `app/routers/onboarding.get_current_user_id` | internal | Auth dependency | Same `Depends()` pattern as all prior phases |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sequential Stitch calls with SSE progress | `asyncio.gather` on Stitch calls | `asyncio.gather` would deadlock on the internal `asyncio.Lock` — the Lock is per-service singleton, can only be held by one caller at a time. Must be sequential. |
| Lazy device generation (MOBILE/TABLET on-demand) | Eager generation of all 3 devices upfront | Eager = 6-9 Stitch calls before user sees anything. Lazy = 2-3 calls for DESKTOP variants first, fast first render, MOBILE/TABLET generated when user clicks device tab. |
| iframe with Supabase Storage URL | Proxy endpoint to serve HTML | stitch-assets bucket is public=true (Phase 16 decision). No proxy needed — iframe src is the permanent Supabase URL directly. |
| Screenshot-based comparison thumbnails | Live iframes in comparison grid | Live iframes in a 3-column grid would triple iframe load + layout thrash. Screenshots as thumbnails for selection; one live iframe for the selected variant is the correct pattern. |

**Installation:** No new packages required. All dependencies are already present.

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── services/
│   └── screen_generation_service.py   # NEW: variant + device generation orchestration
├── routers/
│   └── app_builder.py                 # EXTEND: POST /generate-screen, POST /generate-device-variant

frontend/src/
├── app/app-builder/
│   └── [projectId]/
│       └── building/
│           └── page.tsx               # NEW: main building page — plan nav, variant grid, preview pane
├── components/app-builder/
│   ├── VariantComparisonGrid.tsx      # NEW: 2-3 screenshot thumbnails side-by-side, selection state
│   ├── DevicePreviewFrame.tsx         # NEW: iframe wrapper + DESKTOP/MOBILE/TABLET switcher tabs
│   └── GenerationProgress.tsx        # NEW: SSE progress indicator (reuses ResearchPage pattern)
├── services/
│   └── app-builder.ts                # EXTEND: generateScreen(), generateDeviceVariant(), getScreenVariants()
└── types/
    └── app-builder.ts                # EXTEND: ScreenVariant, GenerationEvent, DeviceType interfaces
```

### Pattern 1: Variant Generation Service (Sequential Stitch calls + SSE)

**What:** `screen_generation_service.py` is an async generator that calls Stitch 2-3 times sequentially (not concurrently — Lock constraint), persisting each variant and yielding a `variant_generated` event after each one.

**When to use:** For the initial screen generation step when the user triggers "Generate" on a build plan screen.

**Key constraint:** The `asyncio.Lock` in `StitchMCPService` means only one `call_tool` can run at a time across the entire FastAPI process. Sequential awaits are safe and correct; `asyncio.gather` across multiple `call_tool` calls would deadlock waiting for the Lock.

```python
# Source: app/services/stitch_mcp.py (existing Lock pattern)
# app/services/screen_generation_service.py — NEW
from collections.abc import AsyncGenerator
from app.services.stitch_mcp import get_stitch_service
from app.services.stitch_assets import persist_screen_assets
from app.services.supabase import get_service_client
import uuid, logging

logger = logging.getLogger(__name__)

async def generate_screen_variants(
    project_id: str,
    user_id: str,
    screen_name: str,
    page_slug: str,
    prompt: str,
    stitch_project_id: str,
    num_variants: int = 3,
) -> AsyncGenerator[dict, None]:
    """Generate 2-3 DESKTOP variants for a screen, yielding SSE events per variant."""
    service = get_stitch_service()
    supabase = get_service_client()

    # Create app_screens row for DESKTOP
    screen_id = str(uuid.uuid4())
    supabase.table("app_screens").insert({
        "id": screen_id,
        "project_id": project_id,
        "user_id": user_id,
        "name": screen_name,
        "device_type": "DESKTOP",
        "order_index": 0,
    }).execute()

    yield {"step": "generating", "message": f"Generating {screen_name}…", "screen_id": screen_id}

    variants = []
    for i in range(num_variants):
        # Sequential — Lock only allows one call at a time
        stitch_result = await service.call_tool(
            "generate_screen_from_text",
            {"prompt": prompt, "projectId": stitch_project_id, "deviceType": "DESKTOP"},
        )
        persisted = await persist_screen_assets(
            stitch_result, user_id=user_id, project_id=project_id,
            screen_id=screen_id, variant_index=i,
        )
        variant_id = str(uuid.uuid4())
        supabase.table("screen_variants").insert({
            "id": variant_id,
            "screen_id": screen_id,
            "user_id": user_id,
            "variant_index": i,
            "stitch_screen_id": stitch_result.get("screenId"),
            "html_url": persisted["html_url"],
            "screenshot_url": persisted["screenshot_url"],
            "prompt_used": prompt,
            "is_selected": i == 0,  # first variant selected by default
        }).execute()
        variants.append({"variant_id": variant_id, "variant_index": i,
                         "screenshot_url": persisted["screenshot_url"],
                         "html_url": persisted["html_url"]})
        yield {"step": "variant_generated", "variant_index": i, "variant_id": variant_id,
               "screenshot_url": persisted["screenshot_url"], "screen_id": screen_id}

    yield {"step": "ready", "screen_id": screen_id, "variants": variants}
```

### Pattern 2: Device-Specific Generation (Lazy, On-Demand)

**What:** A separate endpoint `POST /generate-device-variant` that generates a MOBILE or TABLET version of an already-selected variant. Called only when the user clicks a device tab in DevicePreviewFrame.

**When to use:** User has selected a variant and clicks "Mobile" or "Tablet" tab.

```python
# POST /app-builder/projects/{project_id}/screens/{screen_id}/generate-device-variant
# Body: { "device_type": "MOBILE" | "TABLET", "prompt_used": str }
# Returns SSE stream: generating → variant_generated → ready
# Implementation: same pattern as generate_screen_variants but num_variants=1 and device_type != DESKTOP
```

### Pattern 3: Live iframe Preview

**What:** A sandboxed `<iframe>` whose `src` is set to the permanent Supabase Storage HTML URL for the selected variant.

**When to use:** Any time a variant is selected OR device type changes.

```tsx
// Source: Phase 16 decision — stitch-assets bucket public=true, no auth needed
// frontend/src/components/app-builder/DevicePreviewFrame.tsx — NEW
const DEVICE_DIMS: Record<DeviceType, { width: number; label: string }> = {
  DESKTOP: { width: 1280, label: 'Desktop' },
  TABLET:  { width:  768, label: 'Tablet' },
  MOBILE:  { width:  390, label: 'Mobile' },
};

export function DevicePreviewFrame({ htmlUrl, device, onDeviceChange }: Props) {
  return (
    <div className="flex flex-col gap-2">
      {/* Device tab switcher */}
      <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
        {(Object.keys(DEVICE_DIMS) as DeviceType[]).map(d => (
          <button key={d} onClick={() => onDeviceChange(d)}
            className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors
              ${device === d ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500'}`}>
            {DEVICE_DIMS[d].label}
          </button>
        ))}
      </div>
      {/* Live iframe — public URL, no auth header needed */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <iframe
          key={htmlUrl}  // key forces remount when URL changes
          src={htmlUrl}
          sandbox="allow-scripts allow-same-origin"
          style={{ width: DEVICE_DIMS[device].width, border: 'none', height: '600px' }}
          className="w-full"
          title="Screen preview"
        />
      </div>
    </div>
  );
}
```

### Pattern 4: Variant Comparison Grid

**What:** CSS Grid with 2-3 columns showing screenshot thumbnails. Clicking a thumbnail sets it as the selected variant and updates the iframe src.

```tsx
// frontend/src/components/app-builder/VariantComparisonGrid.tsx — NEW
export function VariantComparisonGrid({ variants, selectedId, onSelect }: Props) {
  return (
    <div className={`grid gap-4 ${variants.length === 2 ? 'grid-cols-2' : 'grid-cols-3'}`}>
      {variants.map(v => (
        <button key={v.id} onClick={() => onSelect(v.id)}
          className={`rounded-xl overflow-hidden border-2 transition-all
            ${selectedId === v.id ? 'border-indigo-500 ring-2 ring-indigo-200' : 'border-slate-200 hover:border-slate-300'}`}>
          <img src={v.screenshot_url} alt={`Variant ${v.variant_index + 1}`}
               className="w-full aspect-video object-cover object-top" />
          <div className="p-2 text-center text-xs font-medium text-slate-600">
            Variant {v.variant_index + 1}
          </div>
        </button>
      ))}
    </div>
  );
}
```

### Pattern 5: SSE in Building Page (Reusing Phase 18 Pattern)

**What:** Same `fetch ReadableStream` + `TextDecoder` + buffer-split pattern used in `startResearch()`. New `generateScreen()` service function follows the identical contract.

```typescript
// frontend/src/services/app-builder.ts — EXTEND
export async function generateScreen(
  projectId: string,
  screenName: string,
  pageSlug: string,
  onEvent: (event: GenerationEvent) => void,
): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/app-builder/projects/${projectId}/generate-screen`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ screen_name: screenName, page_slug: pageSlug }),
  });
  if (!res.ok || !res.body) throw new Error('Generation failed to start');
  // Same ReadableStream reader pattern as startResearch()
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

### Recommended Building Page Structure

The building page (`/app-builder/[projectId]/building`) reads the `build_plan` from the project, lets the user navigate between build phases, triggers generation per screen, and shows the comparison grid + preview pane.

```
BuildingPage
├── BuildPlanSidebar (phases list — from build_plan)
├── ScreenGenerationPanel (active screen)
│   ├── GenerationProgress (SSE progress indicator — shown during generation)
│   ├── VariantComparisonGrid (thumbnail grid — shown after variants ready)
│   └── DevicePreviewFrame (live iframe — shown when variant selected)
└── PhaseApproveButton (not Phase 19 scope — Phase 20 adds approval)
```

### Anti-Patterns to Avoid

- **`asyncio.gather` on multiple Stitch calls:** The `asyncio.Lock` in `StitchMCPService` serializes all calls. `gather` will queue them behind the lock anyway but adds scheduling overhead. Use sequential `await` calls with intermediate SSE yields between each.
- **Eager MOBILE/TABLET generation upfront:** Generates 6-9 Stitch calls before user sees any preview. Lazy device generation (on tab click) keeps the first-paint fast.
- **Live iframes in the comparison grid:** Three simultaneous iframes loading full HTML files causes layout thrash and makes selection feel heavy. Use `<img src={screenshot_url}>` in the grid; single iframe in the preview pane only.
- **Re-fetching Stitch for the iframe:** The permanent Supabase Storage URL is the source of truth for the iframe `src`. Never call Stitch again just to refresh a preview — the `html_url` in `screen_variants` is permanent.
- **Serving HTML through a FastAPI proxy:** `stitch-assets` bucket is `public=true`. The iframe `src` can point directly to Supabase Storage. No proxy endpoint needed, no auth headers on the iframe.
- **Storing variant index as the primary key:** Always use a proper UUID `id` for `screen_variants`. The `variant_index` is display-order only; lookups use `id`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Screen HTML generation | Custom HTML templates | `StitchMCPService.call_tool("generate_screen_from_text", ...)` | Stitch generates pixel-quality HTML; custom templates cannot match quality |
| Asset persistence | Custom download + upload code | `persist_screen_assets()` from `app/services/stitch_assets.py` | Phase 16 already handles signed URL expiry, error fallback, path isolation |
| Prompt enrichment | Inline prompt construction | `enhance_prompt()` from `app/services/prompt_enhancer.py` | Phase 16 Gemini enricher adds design vocabulary; reuse identical function |
| DB upsert on re-generation | Custom conflict detection | `upsert` with `on_conflict` on Supabase | Handles idempotency when screen is regenerated |
| iframe scaling for device preview | CSS viewport meta manipulation | CSS `transform: scale()` on outer container | Simpler, no DOM mutation; works with any HTML content in the iframe |

**Key insight:** All the hard infrastructure exists — generation, asset persistence, DB schema, auth, SSE pattern. Phase 19 assembles these pieces into a user-facing generation workflow.

---

## Common Pitfalls

### Pitfall 1: Lock Deadlock via asyncio.gather on Stitch Calls
**What goes wrong:** `asyncio.gather(service.call_tool(...), service.call_tool(...), service.call_tool(...))` — the second and third calls block forever waiting for the Lock held by the first.
**Why it happens:** `StitchMCPService._lock = asyncio.Lock()` is a singleton; only one `call_tool` can run at a time in the entire process.
**How to avoid:** Sequential `await service.call_tool(...)` calls with `yield` SSE events between each.
**Warning signs:** Generation hangs indefinitely after the first variant appears.

### Pitfall 2: Stitch Project ID vs App Project UUID
**What goes wrong:** Confusing `stitch_project_id` (the Stitch internal project ID used in `generate_screen_from_text` calls) with the `app_projects.id` UUID (the Supabase row identifier).
**Why it happens:** Both are called "project ID" in different contexts. The existing `generate_app_screen` tool in `app_builder.py` takes both: `project_id` (Stitch) and `project_uuid` (app row).
**How to avoid:** The `app_screens` table has a `stitch_project_id TEXT` column — store the Stitch project ID there. Read it when constructing generation calls.
**Warning signs:** "project not found" errors from Stitch, or wrong project's assets appearing.

### Pitfall 3: Iframe Sandbox Blocking Scripts
**What goes wrong:** Generated HTML may use JavaScript for interactivity. `sandbox=""` (no flags) blocks all scripts, making the preview non-interactive.
**Why it happens:** Default iframe sandbox is maximally restrictive.
**How to avoid:** Use `sandbox="allow-scripts allow-same-origin"`. Do NOT add `allow-top-navigation` or `allow-forms` — these create XSS vectors.
**Warning signs:** Blank iframe, or HTML loads but interactive elements don't respond.

### Pitfall 4: Screenshot URL Race Condition
**What goes wrong:** Variant comparison grid renders before `persist_screen_assets` completes — shows null or Stitch temp URLs (already expired) in `<img>` tags.
**Why it happens:** Generation service yielded `variant_generated` event before persistence finished.
**How to avoid:** Only yield `variant_generated` after `persist_screen_assets` returns the permanent URLs. Never yield the temp Stitch URL to the frontend.
**Warning signs:** Broken image thumbnails in the comparison grid.

### Pitfall 5: Migration Timestamp Conflict
**What goes wrong:** New migration file uses a timestamp already taken by a prior migration.
**Why it happens:** Two migrations created on the same date. Phase 18 used `20260322000000` — next available must be `20260322000001` or higher.
**How to avoid:** Check `supabase/migrations/` for the latest timestamp before creating the new migration file.
**Warning signs:** Supabase migration apply fails with "duplicate migration version" error.

### Pitfall 6: `screen_variants.user_id` FK Constraint
**What goes wrong:** Insert into `screen_variants` fails because `user_id` has a FOREIGN KEY to `auth.users(id)` — if the test user UUID doesn't exist in `auth.users`, inserts fail in integration tests.
**Why it happens:** Phase 16 schema decision: `screen_variants.user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE` — stricter than `app_projects.user_id` which is plain UUID with no FK.
**How to avoid:** In unit tests, mock `get_service_client()` entirely (same pattern as Phase 18 tests). In integration tests, use a real Supabase auth user UUID.
**Warning signs:** `ForeignKeyViolationError` on `screen_variants` insert during tests.

---

## Code Examples

### POST Endpoint: Generate Screen Variants (SSE)

```python
# Source: existing pattern from app/routers/app_builder.py (research_project endpoint)
@router.post("/app-builder/projects/{project_id}/generate-screen")
async def generate_screen(
    project_id: str,
    body: GenerateScreenRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> StreamingResponse:
    """Stream screen variant generation progress as Server-Sent Events."""
    supabase = get_service_client()
    result = (
        supabase.table("app_projects")
        .select("build_plan, design_system, status")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    project = result.data
    stitch_project_id = _get_or_create_stitch_project_id(project_id)

    async def event_generator():
        async for event in generate_screen_variants(
            project_id=project_id,
            user_id=user_id,
            screen_name=body.screen_name,
            page_slug=body.page_slug,
            prompt=_build_prompt(body, project.get("design_system", {})),
            stitch_project_id=stitch_project_id,
            num_variants=body.num_variants or 3,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

### GET Endpoint: Fetch Screen Variants

```python
# New: GET /app-builder/projects/{project_id}/screens/{screen_id}/variants
@router.get("/app-builder/projects/{project_id}/screens/{screen_id}/variants")
async def list_screen_variants(
    project_id: str,
    screen_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> list[dict]:
    """Return all variants for a screen, ordered by variant_index."""
    supabase = get_service_client()
    result = (
        supabase.table("screen_variants")
        .select("id, variant_index, screenshot_url, html_url, is_selected, device_type")
        .eq("screen_id", screen_id)
        .eq("user_id", user_id)
        .order("variant_index")
        .execute()
    )
    return result.data or []
```

### PATCH Endpoint: Select Variant

```python
# PATCH /app-builder/projects/{project_id}/screens/{screen_id}/variants/{variant_id}/select
@router.patch("/app-builder/projects/{project_id}/screens/{screen_id}/variants/{variant_id}/select")
async def select_variant(
    project_id: str,
    screen_id: str,
    variant_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Mark one variant as selected, deselect all others for this screen."""
    supabase = get_service_client()
    # Deselect all variants for this screen
    supabase.table("screen_variants").update({"is_selected": False}).eq("screen_id", screen_id).execute()
    # Select the chosen variant
    supabase.table("screen_variants").update({"is_selected": True}).eq("id", variant_id).eq("user_id", user_id).execute()
    return {"success": True, "selected_variant_id": variant_id}
```

### TypeScript: New Types for Phase 19

```typescript
// frontend/src/types/app-builder.ts — EXTEND
export type DeviceType = 'DESKTOP' | 'MOBILE' | 'TABLET';

export interface ScreenVariant {
  id: string;
  screen_id: string;
  variant_index: number;
  screenshot_url: string | null;
  html_url: string | null;
  is_selected: boolean;
  prompt_used: string | null;
  device_type?: DeviceType;
  created_at: string;
}

export interface GenerationEvent {
  step: 'generating' | 'variant_generated' | 'device_generated' | 'ready' | 'error';
  message?: string;
  screen_id?: string;
  variant_index?: number;
  variant_id?: string;
  screenshot_url?: string;
  html_url?: string;
  variants?: ScreenVariant[];
}

export interface AppScreen {
  id: string;
  project_id: string;
  name: string;
  device_type: DeviceType;
  page_type: string;
  order_index: number;
  approved: boolean;
  stitch_project_id: string | null;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ADK MCPToolset per request | StitchMCPService singleton with asyncio.Lock | Phase 16 (2026-03-21) | No per-request subprocess spawn; Lock serializes calls safely |
| Stitch signed URLs served directly | Permanent Supabase Storage URLs via `persist_screen_assets` | Phase 16 (2026-03-21) | URLs survive indefinitely; iframe src is stable |
| `asyncio.get_event_loop()` for sync→async bridge | `asyncio.run` in ThreadPoolExecutor | Phase 16 `app_builder.py` `_run_async()` | Handles running event loop correctly |

**Deprecated/outdated:**
- Direct ADK MCPToolset usage: Phase 16 replaced this with StitchMCPService due to bug #2927. Do not reintroduce `ADK MCPToolset` for Stitch calls.

---

## Open Questions

1. **Stitch Project ID for new screens**
   - What we know: `app_screens.stitch_project_id TEXT` column exists but nothing writes to it yet (Phase 16 schema, not populated in Phases 17-18)
   - What's unclear: Does each `app_projects` row have one reusable Stitch project ID, or is a new Stitch project created per screen? The `generate_screen_from_text` tool requires a `projectId` argument.
   - Recommendation: The generation service should create or reuse a Stitch project ID per `app_projects` row. Store it in `app_projects` as a new JSONB field (e.g., `stitch_metadata: {"project_id": "stitch-proj-xxx"}`), or add a `stitch_project_id TEXT` column to `app_projects`. The service creates it once on first generation for the project. **This likely requires a DB migration** — check if `app_projects` needs a `stitch_project_id` column. The current schema only has it on `app_screens`.

2. **Number of variants: 2 vs 3**
   - What we know: SCRN-01 says "2-3 variants". The requirement is a range.
   - What's unclear: Should it always be 3, or user-selectable?
   - Recommendation: Default to 3; make `num_variants` a configurable parameter in the request body (default: 3, max: 3). This keeps Stitch call count predictable.

3. **`screen_variants.device_type` column**
   - What we know: `screen_variants` table does not have a `device_type` column — only `app_screens` has `device_type`. Device-specific variants are stored as separate `app_screens` rows (one per device).
   - What's unclear: Should device variants be separate `app_screens` rows (current schema) or should `screen_variants` get a `device_type` column?
   - Recommendation: Follow the existing schema — separate `app_screens` row per device type. A DESKTOP screen and its MOBILE equivalent are separate `app_screens` rows with the same `page_slug`. The `screen_variants` table then holds variants per device-screen combination. No migration needed for this.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python backend) + vitest (frontend) |
| Backend config | `pytest.ini` / `pyproject.toml` in project root |
| Frontend config | `frontend/vitest.config.mts` |
| Backend quick run | `uv run pytest tests/unit/app_builder/test_screen_generation_service.py -x` |
| Frontend quick run | `cd frontend && npx vitest run src/__tests__/components/VariantComparisonGrid.test.tsx` |
| Full suite | `uv run pytest tests/unit/app_builder/ -x && cd frontend && npx vitest run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCRN-01 | Service generates 3 `screen_variants` rows via 3 sequential Stitch calls | unit (mocked Stitch) | `uv run pytest tests/unit/app_builder/test_screen_generation_service.py -x` | Wave 0 |
| SCRN-01 | SSE endpoint streams `variant_generated` event after each variant | unit (mocked service) | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_generate_screen_sse -x` | Wave 0 |
| SCRN-02 | `VariantComparisonGrid` renders N thumbnails, clicking selects | unit (vitest) | `cd frontend && npx vitest run src/__tests__/components/VariantComparisonGrid.test.tsx` | Wave 0 |
| SCRN-02 | Selected variant ring class applied to clicked thumbnail | unit (vitest) | same file | Wave 0 |
| SCRN-03 | `DevicePreviewFrame` renders iframe with correct `src` | unit (vitest) | `cd frontend && npx vitest run src/__tests__/components/DevicePreviewFrame.test.tsx` | Wave 0 |
| SCRN-03 | Device tab switcher changes active tab indicator | unit (vitest) | same file | Wave 0 |
| SCRN-04 | `POST /generate-device-variant` calls Stitch with correct `deviceType` | unit (mocked Stitch) | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_generate_device_variant -x` | Wave 0 |
| FOUN-05 | iframe `src` is a Supabase Storage URL (not Stitch temp URL) | unit (service mock) | `uv run pytest tests/unit/app_builder/test_screen_generation_service.py::test_persists_before_yield -x` | Wave 0 |
| BLDR-02 | Building page renders `VariantComparisonGrid` after generation | unit (vitest + mocked service) | `cd frontend && npx vitest run src/__tests__/components/BuildingPage.test.tsx` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/app_builder/ -x && cd frontend && npx vitest run --reporter=dot`
- **Per wave merge:** Full suite above
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/app_builder/test_screen_generation_service.py` — covers SCRN-01, FOUN-05
- [ ] `tests/unit/app_builder/test_app_builder_router.py` — extend with generate-screen SSE tests (SCRN-01, SCRN-04)
- [ ] `frontend/src/__tests__/components/VariantComparisonGrid.test.tsx` — covers SCRN-02
- [ ] `frontend/src/__tests__/components/DevicePreviewFrame.test.tsx` — covers SCRN-03
- [ ] `frontend/src/__tests__/components/BuildingPage.test.tsx` — covers BLDR-02

---

## Sources

### Primary (HIGH confidence)
- `app/services/stitch_mcp.py` — StitchMCPService singleton with asyncio.Lock constraint (definitive)
- `app/services/stitch_assets.py` — `persist_screen_assets()` signature and storage path pattern
- `app/agents/tools/app_builder.py` — `generate_screen_from_text` tool call arguments (prompt, projectId, deviceType)
- `supabase/migrations/20260321400000_app_builder_schema.sql` — app_screens, screen_variants schema (definitive)
- `app/routers/app_builder.py` — SSE endpoint pattern, auth pattern, Supabase client pattern
- `frontend/src/services/app-builder.ts` — ReadableStream SSE client pattern
- `frontend/src/types/app-builder.ts` — existing type interfaces to extend
- `frontend/src/__tests__/components/ResearchPage.test.tsx` — vitest mock pattern for service functions
- `.planning/STATE.md` — Phase 16 decisions: Lock constraint, public bucket, signed URL expiry

### Secondary (MEDIUM confidence)
- Phase 18 SUMMARY files — SSE streaming patterns, async generator service pattern, TDD workflow
- `frontend/src/app/app-builder/[projectId]/layout.tsx` — server component layout pattern that building page inherits

### Tertiary (LOW confidence)
- None — all findings are directly verifiable from existing project code

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use in the project; no new packages needed
- Architecture: HIGH — directly derived from existing Phase 16-18 patterns; no new integration territory
- Pitfalls: HIGH — Lock constraint, FK constraint, and iframe sandbox are concrete facts from existing code
- Open questions: MEDIUM — Stitch project ID lifecycle is an unresolved schema question; answered by checking if `app_projects` needs a new column

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable domain — all infrastructure is internal project code, not an external moving API)
