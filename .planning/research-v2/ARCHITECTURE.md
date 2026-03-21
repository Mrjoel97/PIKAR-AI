# Architecture Research

**Domain:** AI-powered app builder integration (Stitch MCP) into existing FastAPI/ADK/Supabase/Next.js system
**Researched:** 2026-03-21
**Confidence:** HIGH for integration patterns and DB schema; MEDIUM for Stitch MCP tool surface (documentation is thin); HIGH for Windows/Linux subprocess compatibility

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         BROWSER (Next.js frontend)                    │
│  ┌──────────────────┐  ┌─────────────────┐  ┌──────────────────────┐ │
│  │  AppBuilderUI    │  │ ScreenPreview   │  │  LandingPagesWidget  │ │
│  │  (new)           │  │ (new)           │  │  (existing, extend)  │ │
│  └────────┬─────────┘  └────────┬────────┘  └──────────┬───────────┘ │
│           │ SSE chat            │ REST              │ REST             │
└───────────┼─────────────────────┼───────────────────┼─────────────────┘
            │                     │                   │
┌───────────┼─────────────────────┼───────────────────┼─────────────────┐
│           │        FastAPI Backend (app/)            │                 │
│  ┌────────▼──────────┐  ┌───────▼───────────────────▼──────────────┐  │
│  │  /a2a/app/run_sse │  │  app/routers/pages.py (existing + new)   │  │
│  │  (SSE streaming)  │  │  app/routers/app_builder.py (NEW)        │  │
│  └────────┬──────────┘  └────────────────────────────────────────┘  │
│           │                                                           │
│  ┌────────▼──────────────────────────────────────────────────────┐   │
│  │  ExecutiveAgent → ContentAgent (routed via ADK)               │   │
│  │  tools registered: stitch_build_page, stitch_list_projects,   │   │
│  │  stitch_generate_screen, stitch_edit_screens, prompt_enhance, │   │
│  │  react_convert, persist_html, persist_screenshot              │   │
│  └────────┬──────────────────────────────────────────────────────┘   │
│           │ StitchMCPService (singleton, async lifecycle)             │
│  ┌────────▼──────────────────────────────────────────────────────┐   │
│  │  app/services/stitch_mcp.py (NEW)                             │   │
│  │  Wraps MCPToolset / StdioConnectionParams                     │   │
│  │  Manages subprocess lifecycle (platform-aware)                │   │
│  └────────┬──────────────────────────────────────────────────────┘   │
│           │ stdio (npx @_davideast/stitch-mcp proxy)                  │
└───────────┼───────────────────────────────────────────────────────────┘
            │
┌───────────▼────────────────────────────────┐
│  Stitch MCP Server (Node.js child process)  │
│  Tools: list_projects, get_project,         │
│  list_screens, get_screen, generate_screen_ │
│  from_text, edit_screens, generate_variants,│
│  build_site, get_screen_code, get_screen_   │
│  image                                      │
└────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│  Supabase (PostgreSQL + Storage)             │
│  landing_pages (extended)                   │
│  app_projects (NEW)                         │
│  app_screens (NEW)                          │
│  design_systems (NEW)                       │
│  screen_variants (NEW)                      │
│  Supabase Storage bucket: stitch-assets     │
└──────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Status |
|-----------|---------------|--------|
| `app/services/stitch_mcp.py` | Owns the MCPToolset subprocess lifecycle; exposes async methods for all Stitch tools; handles URL-to-bytes download for temporary signed URLs | **NEW** |
| `app/agents/tools/app_builder.py` | ADK-compatible tool functions that call StitchMCPService; handles prompt enhancement, multi-device generation, design system persistence | **NEW** |
| `app/services/prompt_enhancer.py` | Calls Gemini (not Stitch) to expand vague user prompts into structured UI specifications; reuses existing model fallback pattern | **NEW** |
| `app/services/react_converter.py` | Converts Stitch-generated HTML to React components with Tailwind extraction; AST validation via py_mini_racer or subprocess Node | **NEW** |
| `app/routers/app_builder.py` | REST endpoints for project/screen CRUD, trigger generation, serve preview blobs; extends beyond ADK chat flows | **NEW** |
| `app/routers/pages.py` | Existing CRUD + publish; minor additions for multi-page project linking | **MODIFIED** |
| `app/mcp/tools/stitch.py` | Current REST-based stub — replace entirely with delegation to StitchMCPService; remove old REST auth code | **REPLACE** |
| `app/mcp/agent_tools.py` | Remove `mcp_stitch_landing_page` sync wrapper (incompatible with persistent MCP session); ADK agents use app_builder tools directly | **MODIFIED** |
| `frontend/src/app/(personas)/[persona]/app-builder/` | New App Router section: project list, screen gallery, live preview, iteration panel | **NEW** |
| `frontend/src/services/app-builder.ts` | API client for all app builder REST endpoints | **NEW** |
| `frontend/src/components/widgets/AppBuilderWidget.tsx` | Agent-triggered widget showing current project state inside chat | **NEW** |
| `supabase/migrations/YYYYMMDD_app_builder_schema.sql` | New tables: app_projects, app_screens, design_systems, screen_variants | **NEW** |

---

## New vs Modified: Full Inventory

### New Files (Python backend)

```
app/services/stitch_mcp.py          # StitchMCPService singleton
app/services/prompt_enhancer.py     # Gemini-powered prompt expansion
app/services/react_converter.py     # HTML→React+Tailwind pipeline
app/agents/tools/app_builder.py     # ADK tool functions
app/routers/app_builder.py          # REST router for app builder
```

### Modified Files (Python backend)

```
app/mcp/tools/stitch.py             # Strip REST auth, delegate to StitchMCPService
app/mcp/agent_tools.py              # Remove mcp_stitch_landing_page wrapper
app/fast_api_app.py                 # Register lifespan for StitchMCPService startup/shutdown
                                    # Include app/routers/app_builder router
app/agent.py                        # Add app_builder tools to ExecutiveAgent tool list
```

### New Files (Frontend)

```
frontend/src/app/(personas)/[persona]/app-builder/
  page.tsx                          # Project list / entry point
  [projectId]/
    page.tsx                        # Screen gallery + project dashboard
    preview/[screenId]/page.tsx     # Full-screen preview with iteration panel
frontend/src/services/app-builder.ts
frontend/src/components/widgets/AppBuilderWidget.tsx
frontend/src/components/app-builder/
  ScreenGallery.tsx
  ScreenPreviewPane.tsx
  IterationPanel.tsx
  DesignSystemBadge.tsx
  DeviceSelector.tsx
  ReactExportModal.tsx
```

### New Migration

```
supabase/migrations/YYYYMMDD_app_builder_schema.sql
```

---

## Data Flow: Screen Generation to Deployment

### 1. User Initiates via Chat (agent-driven path)

```
User types "Build me a landing page for my bakery"
    |
    v
ExecutiveAgent (SSE stream)
    |
    +--> prompt_enhance_tool(raw_description)
    |        calls Gemini directly (not Stitch)
    |        returns: structured_spec {target_audience, visual_style,
    |                  sections, tone, color_hints}
    |
    +--> stitch_generate_screen_tool(prompt=structured_spec, deviceType="desktop")
    |        calls StitchMCPService.generate_screen_from_text()
    |        MCP returns: {screenId, projectId, downloadUrl (TEMPORARY)}
    |
    +--> persist_screen_tool(screenId, projectId, downloadUrl)
    |        StitchMCPService.get_screen_code() → downloads HTML bytes NOW
    |        StitchMCPService.get_screen_image() → downloads screenshot bytes NOW
    |        uploads both to Supabase Storage (stitch-assets bucket)
    |        inserts row into app_screens table with permanent storage URLs
    |
    v
Agent streams AppBuilderWidget to frontend
    |
    v
Frontend renders screen gallery with permanent screenshot URLs
```

### 2. User Previews and Iterates (REST path)

```
User clicks "I like this, but make the header darker"
    |
    v
POST /app-builder/screens/{screenId}/iterate
    { prompt: "darker header", device_types: ["desktop", "mobile"] }
    |
    v
app/routers/app_builder.py
    |
    +--> StitchMCPService.edit_screens(screenIds, prompt)
    |        returns: new screen variants with temporary URLs
    |
    +--> persist each variant (download + upload to Storage)
    |
    v
Response: { variants: [{ variantId, screenshotUrl, device }] }
    |
    v
Frontend IterationPanel shows new variants side-by-side
```

### 3. Multi-Page Site Builder (stitch-loop pattern)

```
User: "Build a full 5-page website for my SaaS"
    |
    v
ExecutiveAgent → stitch_loop_tool(description, page_count)
    |
    +--> generate SITE.md: list of pages with routes and purposes
    |
    loop for each page:
    +--> generate_screen_from_text(page_purpose + design_system_context)
    +--> persist screen
    |
    +--> generate_variants(for hero screen only, 3 variants)
    |
    v
Agent streams progress via SSE
Final: AppBuilderWidget shows site map with all pages
```

### 4. React Conversion

```
User: "Convert to React components"
    |
    v
POST /app-builder/projects/{projectId}/export/react
    |
    v
react_converter.py
    +--> fetch html_content from app_screens (Supabase Storage)
    +--> parse DOM: identify sections, extract inline CSS
    +--> generate Tailwind theme tokens from inline CSS values
    +--> output JSX components: one per section + index.tsx barrel
    +--> validate: check JSX is parseable (subprocess: node --check)
    |
    v
Response: { react_zip_url, tailwind_config, component_list }
    |
    v
Frontend: ReactExportModal shows component tree, download link
```

### 5. Capacitor Hybrid Output

```
POST /app-builder/projects/{projectId}/export/capacitor
    |
    v
Backend generates capacitor.config.ts + package.json scaffold
    zips: React components + capacitor config + README
    uploads to Supabase Storage
    |
    v
Response: { zip_url, instructions }
    (user downloads and runs: npm install && npx cap add ios && npx cap add android)
```

---

## DB Schema Changes

### Modified: `landing_pages`

Add column to link single-page results to an app project:

```sql
ALTER TABLE public.landing_pages
  ADD COLUMN IF NOT EXISTS app_project_id UUID REFERENCES public.app_projects(id) ON DELETE SET NULL;
```

### New Table: `app_projects`

```sql
CREATE TABLE public.app_projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT,
    stitch_project_id TEXT,             -- Stitch platform project ID
    site_md         TEXT,               -- SITE.md content for multi-page baton
    status          TEXT NOT NULL DEFAULT 'draft',
                                        -- draft | generating | ready | exported
    output_type     TEXT NOT NULL DEFAULT 'landing_page',
                                        -- landing_page | multi_page | pwa | hybrid
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.app_projects ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their app projects"
  ON public.app_projects FOR ALL USING (auth.uid() = user_id);
```

### New Table: `design_systems`

```sql
CREATE TABLE public.design_systems (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES public.app_projects(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    design_md       TEXT NOT NULL,      -- DESIGN.md content
    color_tokens    JSONB DEFAULT '{}', -- extracted palette
    typography      JSONB DEFAULT '{}', -- font families, weights, sizes
    spacing         JSONB DEFAULT '{}', -- spacing scale
    version         INT NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.design_systems ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their design systems"
  ON public.design_systems FOR ALL USING (auth.uid() = user_id);
```

### New Table: `app_screens`

```sql
CREATE TABLE public.app_screens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES public.app_projects(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    stitch_screen_id TEXT,              -- Stitch platform screen ID
    route           TEXT,               -- e.g. "/" or "/about" (for multi-page)
    device_type     TEXT NOT NULL DEFAULT 'desktop',
                                        -- desktop | mobile | tablet
    title           TEXT NOT NULL,
    html_storage_path TEXT,             -- Supabase Storage path (permanent)
    screenshot_storage_path TEXT,       -- Supabase Storage path (permanent)
    html_url        TEXT,               -- public URL from Storage
    screenshot_url  TEXT,               -- public URL from Storage
    prompt_used     TEXT,               -- enhanced prompt that created this screen
    status          TEXT NOT NULL DEFAULT 'active',
                                        -- active | archived | selected
    is_selected     BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order      INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.app_screens ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their app screens"
  ON public.app_screens FOR ALL USING (auth.uid() = user_id);

CREATE INDEX idx_app_screens_project ON public.app_screens(project_id, sort_order);
```

### New Table: `screen_variants`

```sql
CREATE TABLE public.screen_variants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    screen_id       UUID NOT NULL REFERENCES public.app_screens(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    iteration_prompt TEXT,              -- what the user asked to change
    device_type     TEXT NOT NULL DEFAULT 'desktop',
    html_storage_path TEXT,
    screenshot_storage_path TEXT,
    screenshot_url  TEXT,
    is_applied      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.screen_variants ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their screen variants"
  ON public.screen_variants FOR ALL USING (auth.uid() = user_id);
```

---

## Stitch MCP Client Integration Pattern

### The Core Problem with Existing Pattern

The current `mcp_stitch_landing_page` sync wrapper in `agent_tools.py` uses `ThreadPoolExecutor + asyncio.run()`. Each call creates a new subprocess, connects, calls one tool, then terminates. This works for stateless tools (web search, scrape) but is wrong for Stitch MCP because:

1. Subprocess startup is expensive (Node.js cold start ~1-2s per call)
2. ADK agents make multiple sequential Stitch calls per user request
3. The session persistence bug in ADK 1.12.0 means reconnecting per call loses Stitch auth context

### Correct Pattern: Singleton Service with Lifespan

**MEDIUM confidence** — ADK's MCPToolset on FastAPI lifespan support is partially documented and the session bug (issue #2927) may affect this pattern. Test required.

```python
# app/services/stitch_mcp.py

import asyncio
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class StitchMCPService:
    """Singleton that owns the Stitch MCP subprocess lifecycle.

    One subprocess per FastAPI process. Initialized at lifespan startup,
    closed at lifespan shutdown. Individual tool calls reuse the session.
    Does NOT use ADK MCPToolset — uses mcp SDK directly to avoid the
    ADK session-per-call bug (issue #2927).
    """

    def __init__(self) -> None:
        self._session: ClientSession | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the Stitch MCP subprocess and establish session."""
        params = StdioServerParameters(
            command="npx",
            args=["@_davideast/stitch-mcp", "proxy"],
            env={"STITCH_API_KEY": os.environ["STITCH_API_KEY"]},
        )
        # stdio_client is an async context manager — hold it open for lifetime
        self._stdio_cm = stdio_client(params)
        read, write = await self._stdio_cm.__aenter__()
        self._session = ClientSession(read, write)
        await self._session.__aenter__()
        await self._session.initialize()

    async def stop(self) -> None:
        if self._session:
            await self._session.__aexit__(None, None, None)
        if hasattr(self, "_stdio_cm"):
            await self._stdio_cm.__aexit__(None, None, None)

    async def call_tool(self, name: str, arguments: dict) -> dict:
        async with self._lock:  # serialize calls; MCP sessions are not thread-safe
            result = await self._session.call_tool(name, arguments)
            return result.content


_stitch_service: StitchMCPService | None = None


def get_stitch_service() -> StitchMCPService:
    if _stitch_service is None:
        raise RuntimeError("StitchMCPService not initialized")
    return _stitch_service
```

**Lifespan registration in `fast_api_app.py`:**

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _stitch_service
    from app.services.stitch_mcp import StitchMCPService
    _stitch_service = StitchMCPService()
    await _stitch_service.start()
    yield
    await _stitch_service.stop()
```

**Agent tool functions in `app/agents/tools/app_builder.py` call the service directly (they are already async):**

```python
async def stitch_generate_screen(
    prompt: str,
    project_id: str,
    device_type: str = "desktop",
) -> dict:
    """Generate a UI screen via Stitch MCP and persist to Supabase Storage."""
    service = get_stitch_service()
    result = await service.call_tool("generate_screen_from_text", {
        "prompt": prompt,
        "projectId": project_id,
        "deviceType": device_type,
    })
    # Download immediately — temporary URLs expire
    screen_id = result["screenId"]
    html_result = await service.call_tool("get_screen_code", {
        "projectId": project_id, "screenId": screen_id
    })
    img_result = await service.call_tool("get_screen_image", {
        "projectId": project_id, "screenId": screen_id
    })
    # Persist to Supabase Storage + insert app_screens row
    return await _persist_screen(project_id, screen_id, html_result, img_result)
```

These async functions are registered directly in the ADK agent's tools list — no sync wrapper needed.

---

## Windows Dev vs Linux Prod (MCP Subprocess)

### The Problem

`asyncio.create_subprocess_exec()` (used internally by `mcp`'s `stdio_client`) raises `NotImplementedError` on Windows when Uvicorn uses `SelectorEventLoop`. Uvicorn on Windows defaults to `SelectorEventLoop` when `--reload` is used; without `--reload` it uses `ProactorEventLoop`, which supports subprocesses.

### Solution: Platform-Aware Event Loop Policy

Set the event loop policy at the entry point, before Uvicorn starts:

```python
# In the Makefile `local-backend` target or a run.py wrapper:
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

Or in `app/fast_api_app.py` at module level (executes before Uvicorn sets its own policy):

```python
import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

**Important:** This must be set before `asyncio.get_event_loop()` is called. Adding it to `fast_api_app.py` at the top is safest.

**Dev command change:** Use `uvicorn app.fast_api_app:app --no-reload` on Windows for MCP subprocess work. The `--reload` flag forks child processes using `SelectorEventLoop` regardless of policy.

### Linux/Cloud Run

No change needed. Linux uses `DefaultEventLoopPolicy` which is `SelectorEventLoop` but Linux `SelectorEventLoop` does support subprocesses (unlike Windows). `ProactorEventLoop` is Windows-only; the policy set above only activates on `win32`.

### Summary

| Environment | Event Loop | subprocess support | Action needed |
|-------------|-----------|-------------------|---------------|
| Windows + `--no-reload` | ProactorEventLoop | YES | Set policy at startup |
| Windows + `--reload` | SelectorEventLoop | NO | Must use `--no-reload` in dev |
| Linux (Cloud Run) | SelectorEventLoop | YES | No change |
| Docker on Windows | Linux kernel | YES | No change |

**Recommendation:** Add `run_stitch_dev.py` script to the project root that sets the policy then starts Uvicorn programmatically, avoiding the `--reload` issue entirely for the app builder milestone.

---

## Architectural Patterns

### Pattern 1: Immediate Download on Generation

**What:** Download HTML and screenshots from Stitch within the same tool call that generates them. Store in Supabase Storage. Return permanent Storage URLs, never the temporary Stitch signed URLs.

**When to use:** Every Stitch tool call that returns a URL — `get_screen`, `get_screen_code`, `get_screen_image`, `build_site`, `generate_variants`.

**Why:** Stitch download URLs are temporary signed URLs (GCS-backed). Their expiry is not documented but observed to be short (minutes). The frontend needs stable URLs for preview rendering, iteration comparison, and React export.

**Implementation:** `_persist_screen()` helper in `app/agents/tools/app_builder.py` handles download + upload atomically. If upload fails, the generation is retried rather than returning a broken URL.

### Pattern 2: Project-Scoped Design System

**What:** First-screen generation for a project generates a `DESIGN.md` that captures color palette, typography, and spacing extracted from the Stitch output. Subsequent screen generations for the same project include the design system context in the prompt.

**When to use:** All multi-screen projects (multi-page sites, variant generation).

**Implementation:** `design_systems` table stores the design MD. `stitch_generate_screen` tool fetches the project's latest design system and appends it to the Stitch prompt before calling MCP.

### Pattern 3: Prompt Enhancement Before MCP Call

**What:** All user-facing generation requests pass through `prompt_enhancer.py` first. Vague descriptions ("make a bakery page") become structured Stitch-optimized specifications ("Professional bakery landing page with warm color palette (#F5E6D3, #8B4513), Playfair Display headings, hero with artisan bread photography placeholder, three-column product feature grid, embedded Google Maps section...").

**When to use:** All initial screen generation calls. Skipped for iteration prompts (user knows what they want to change).

**Implementation:** Single `enhance_prompt(description, context)` async function calling Gemini Flash (cheap, fast). 300ms typical latency. Adds ~200 tokens to the Stitch prompt but dramatically improves output quality.

### Pattern 4: SSE for Long-Running Generation, REST for CRUD

**What:** Screen generation (which can take 10-30 seconds per screen) streams progress via the existing SSE chat. Simple CRUD operations (list, delete, publish, rename) use REST endpoints in `app/routers/app_builder.py`.

**When to use:** Generation and multi-page stitch-loop use SSE chat. Everything else uses REST.

**Why:** Stitch generation is LLM-backed and slow. Users need feedback that something is happening. The existing SSE infrastructure handles this perfectly. REST is faster for instantaneous operations.

---

## Anti-Patterns

### Anti-Pattern 1: Using the Old Sync Wrapper Pattern for Stitch

**What people do:** Add a sync wrapper to `agent_tools.py` that calls `asyncio.run(stitch_generate_landing_page(...))` inside a `ThreadPoolExecutor`, following the existing pattern for web search.

**Why it's wrong:** Each call starts and terminates a new `npx` Node.js process (~2s overhead), loses Stitch session auth context, and accumulates orphaned processes under load. The pattern is fine for stateless HTTP tools (web search) but breaks for long-lived subprocess-based MCP servers.

**Do this instead:** Use the `StitchMCPService` singleton with the lifespan pattern. Register async tool functions directly in the ADK agent tools list — ADK supports both sync and async functions.

### Anti-Pattern 2: Returning Stitch Signed URLs to the Frontend

**What people do:** Return the `downloadUrl` from a Stitch tool response directly to the frontend for preview rendering.

**Why it's wrong:** Signed URLs expire in minutes. The user sees a broken image in the screen gallery within the session. The React export pipeline also needs stable URLs.

**Do this instead:** Download immediately in the tool call, upload to Supabase Storage, return the permanent Storage public URL.

### Anti-Pattern 3: Storing React Components in JSONB `metadata`

**What people do:** Save generated React components as a string inside the `metadata` JSONB column of `landing_pages`, following the current pattern where `react_content` lives there.

**Why it's wrong:** Multi-component exports (multiple JSX files, tailwind config, capacitor config) can't be represented as a flat string. JSONB metadata is already overloaded.

**Do this instead:** Store multi-component output as a ZIP file in Supabase Storage. Store the storage path in `app_screens`. The `react_content` single-string pattern is acceptable only for single-file legacy output.

### Anti-Pattern 4: Running MCPToolset with `--reload` on Windows

**What people do:** Run `make local-backend` (which includes `--reload`) unchanged when testing Stitch MCP integration on Windows.

**Why it's wrong:** Uvicorn's `--reload` uses `SelectorEventLoop` on Windows, which does not support `asyncio.create_subprocess_exec`. The `StitchMCPService.start()` call at lifespan will raise `NotImplementedError`.

**Do this instead:** Add a separate Makefile target `make local-backend-stitch` that runs Uvicorn without `--reload` with `WindowsProactorEventLoopPolicy` set.

---

## Integration Points

### Stitch MCP Client ↔ Existing Agent Tools

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `StitchMCPService` ↔ Stitch MCP Server | stdio (mcp SDK `ClientSession`) | One persistent subprocess per FastAPI process |
| ADK agent tools ↔ `StitchMCPService` | Direct Python async call (`await get_stitch_service().call_tool(...)`) | No sync wrapper; tool functions are async |
| Agent tool return ↔ Supabase Storage | `supabase.storage.from_("stitch-assets").upload(...)` | Uses existing service client pattern |
| ADK agent tools ↔ Gemini (prompt enhance) | ADK `InvocationContext` model call or direct `genai` SDK | Reuses existing model fallback (Pro → Flash) |
| `app/routers/app_builder.py` ↔ `StitchMCPService` | Dependency injection via `Depends(get_stitch_service)` | REST path for non-chat operations |

### Frontend ↔ Backend

| Surface | Pattern | Notes |
|---------|---------|-------|
| Screen generation trigger | SSE chat (`/a2a/app/run_sse`) | User describes what they want in chat |
| Project/screen CRUD | REST (`/app-builder/*`) | Separate from chat flow |
| Preview rendering | `<img src={screenshot_url}>` + `<iframe srcdoc={html_content}>` | Both served from Supabase Storage |
| Iteration panel | REST POST `/app-builder/screens/{id}/iterate` | Non-streaming; returns variants array |
| React export download | REST GET `/app-builder/projects/{id}/export/react` → redirect to Storage zip URL | ZIP in Storage |

---

## Build Order (Phase Dependencies)

```
Phase 1: StitchMCPService + Windows event loop fix
         [app/services/stitch_mcp.py + fast_api_app.py lifespan]
         Prerequisite for all subsequent phases

Phase 2: DB Schema
         [supabase migration: app_projects, design_systems, app_screens, screen_variants]
         Prerequisite for persistence in all phases

Phase 3: Prompt Enhancer
         [app/services/prompt_enhancer.py]
         Standalone Gemini integration, no MCP dependency

Phase 4: Core ADK Tool Set
         [app/agents/tools/app_builder.py]
         Depends on: Phase 1 (MCP service), Phase 2 (DB), Phase 3 (enhancer)
         Tools: stitch_generate_screen, stitch_list_projects, persist_screen

Phase 5: REST Router
         [app/routers/app_builder.py]
         Depends on: Phase 1, Phase 2
         CRUD endpoints; can be built in parallel with Phase 4

Phase 6: Frontend App Builder UI
         [frontend/src/app/(personas)/[persona]/app-builder/]
         Depends on: Phase 5 (REST endpoints available)

Phase 7: Screen Preview + Iteration
         [IterationPanel + /screens/{id}/iterate endpoint]
         Depends on: Phase 4 (edit_screens tool), Phase 6 (UI exists)

Phase 8: Design System Persistence
         [design_systems table + DESIGN.md extraction]
         Depends on: Phase 4 (screens exist to extract from)

Phase 9: Multi-Page Stitch-Loop
         [stitch_loop_tool + SITE.md generation]
         Depends on: Phase 4, Phase 8 (design system context)

Phase 10: React Conversion
          [app/services/react_converter.py + export endpoint]
          Depends on: Phase 2 (app_screens with html), Phase 5 (endpoint)

Phase 11: Capacitor Hybrid Output
          [scaffold generation + zip export]
          Depends on: Phase 10 (React components exist)

Phase 12: Remotion Video Generation
          [reuses existing Remotion infra + stitch screenshots]
          Depends on: Phase 2 (screenshot_url in app_screens)
```

---

## Scaling Considerations

| Scale | Architecture Adjustment |
|-------|------------------------|
| 0-100 active users | Single StitchMCPService subprocess per Cloud Run instance; MCP calls serialized per instance via asyncio.Lock |
| 100-1000 users | MCP subprocess becomes bottleneck; move generation to background tasks (Cloud Tasks or ADK workflow); return job_id immediately, poll for completion |
| 1000+ users | Pool of MCP subprocesses (separate Cloud Run service per user session); dedicated Stitch MCP worker tier |

**First bottleneck:** The asyncio.Lock in StitchMCPService serializes all Stitch calls within one instance. Under concurrent load a second user waits for the first user's 15-second generation. At 100 users this becomes noticeable. Fix: Cloud Run min-instances > 1 and Stitch calls moved to async job queue before 100 active builders.

**Second bottleneck:** Supabase Storage upload latency during screen persistence (typically 200-500ms per asset). Fix: Parallel upload of HTML + screenshot using `asyncio.gather()`.

---

## Sources

- [ADK MCP Tools documentation](https://google.github.io/adk-docs/tools-custom/mcp-tools/) — MCPToolset stdio pattern (HIGH confidence)
- [ADK issue #2927: MCPToolset session not persisted across tool calls](https://github.com/google/adk-python/issues/2927) — Session bug, ADK 1.12.0 (HIGH confidence, confirmed by multiple reporters)
- [ADK issue #2979: MCPToolset Session Management](https://github.com/google/adk-python/issues/2979) — Additional context (HIGH confidence)
- [stitch-mcp GitHub repository](https://github.com/davideast/stitch-mcp) — Tool list and proxy command (MEDIUM confidence — official but sparse docs)
- [stitch-mcp tool catalog](https://davideast.github.io/stitch-mcp/tool-catalog) — Full tool schema list (MEDIUM confidence)
- [stitch-skills repository](https://github.com/google-labs-code/stitch-skills) — DESIGN.md, SITE.md, react-components patterns (MEDIUM confidence — these are SKILL.md instruction files, not importable modules)
- [FastAPI asyncio subprocess Windows discussion](https://github.com/fastapi/fastapi/discussions/6485) — SelectorEventLoop / ProactorEventLoop Windows workaround (HIGH confidence)
- [Uvicorn Windows subprocess issue](https://github.com/Kludex/uvicorn/discussions/2346) — `--reload` disables ProactorEventLoop (HIGH confidence)
- [Capacitor React integration](https://capacitorjs.com/solution/react) — React to iOS/Android pipeline (HIGH confidence)

---

*Architecture research for: Stitch MCP app builder integration into pikar-ai*
*Researched: 2026-03-21*
