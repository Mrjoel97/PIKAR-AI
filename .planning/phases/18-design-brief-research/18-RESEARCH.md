# Phase 18: Design Brief & Research - Research

**Researched:** 2026-03-21
**Domain:** Gemini-powered design research, design system document generation, approval state machine, FastAPI SSE, Next.js interactive editor
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FLOW-02 | System performs design research — analyzes competitors/inspiration, suggests palettes, layouts, and typography patterns | Answered by: Gemini 2.5 Flash for research synthesis, Tavily search via existing TavilySearchTool, creative_brief JSONB as input, app_projects.design_system JSONB as output |
| FLOW-03 | System generates a design brief with sitemap, DESIGN.md (colors, fonts, spacing), features per page, and device targets — user approves before building | Answered by: design_systems table already in schema (raw_markdown column for DESIGN.md text), app_projects.sitemap JSONB, approval state machine via PATCH stage endpoint, explicit user approval action |
| FLOW-04 | System creates a build plan breaking the app into phases per page/screen group with dependencies | Answered by: app_projects.build_plan JSONB (already in schema), Gemini to generate ordered phase array with dependency field, stored after approval |
</phase_requirements>

---

## Summary

Phase 18 bridges the Phase 17 creative questioning output (a `creative_brief` JSONB on `app_projects`) to Phase 19's screen generation (which needs a locked `design_system` and `build_plan`). The system must do three things in sequence: (1) run design research using the creative brief as input and surface references/palette/type suggestions; (2) draft a DESIGN.md document and a SITE.md sitemap for user review and edit; (3) after explicit user approval, persist the locked design system and generate a build plan.

The good news for planning: every data structure Phase 18 needs already exists in the DB schema from Phase 16. The `design_systems` table has `colors`, `typography`, `spacing`, `components`, `locked`, and `raw_markdown` columns. The `app_projects` table has `design_system`, `sitemap`, and `build_plan` JSONB columns. No new migration is needed.

Phase 18 is primarily a Gemini + SSE orchestration phase. There is no Stitch MCP call here — Stitch generates screens, but Phase 18 is pre-generation. The research step uses the existing `TavilySearchTool` (Tavily API via `app/mcp/tools/web_search.py`) to find competitor/inspiration references. The design synthesis uses Gemini 2.5 Flash to turn brief + research results into DESIGN.md markdown and SITE.md sitemap JSON. The frontend shows two editable preview cards (design system + sitemap) with an explicit "Approve" button.

**Primary recommendation:** Build a dedicated FastAPI research-and-brief service that accepts a `project_id`, runs Tavily search + Gemini synthesis in sequence, streams progress via SSE, saves draft documents to `design_systems` and `app_projects`, then waits for user approval before advancing the stage to `brief` (and then `building` after the build plan is generated). Use Gemini 2.5 Flash for all synthesis steps (not Pro — this is structured output, not deep reasoning).

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Gemini 2.5 Flash | `gemini-2.5-flash` | Design research synthesis, DESIGN.md generation, build plan generation | Project standard — FAST_AGENT_CONFIG at temperature=0.3; Pro overkill for structured output |
| `TavilySearchTool` | project-pinned | Competitor/inspiration web search | Already in `app/mcp/tools/web_search.py`; TAVILY_API_KEY already in env |
| FastAPI + Pydantic v2 | project-pinned | Research-and-brief endpoint, SSE streaming | Matches all existing routers |
| Supabase Python client | 2.27.2 | Write design_systems row, update app_projects JSONB columns | `get_service_client()` pattern — same as Phase 17 |
| Next.js App Router | 16.1.4 | `/app-builder/[projectId]/research` page, approval UI | Project-standard; matches existing /app-builder layout |
| React 19 | 19.2.3 | Editable design brief cards, SSE hook | Project-standard |
| Tailwind CSS 4 | project-pinned | Brief review UI, editable text areas | All existing UI uses Tailwind only |
| framer-motion | 12.29.0 | Research progress animation, brief reveal | Already installed; Phase 17 patterns established |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `google.genai` async client | project-pinned | Gemini calls for synthesis | `client.aio.models.generate_content()` — same pattern as `prompt_enhancer.py` |
| `asyncio.gather` | stdlib | Parallel Tavily searches (e.g., "competitors" + "design inspiration" tracks) | Two search tracks are independent; run concurrently |
| `app/services/supabase.get_service_client()` | internal | All DB writes | Service-role bypass for research writes (RLS would block cross-table updates) |
| `app/routers/onboarding.get_current_user_id` | internal | Auth dependency | Same Depends() pattern as Phase 17 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Gemini Flash for synthesis | Gemini Pro | Pro is 10x more expensive; Flash structured output (JSON mode) is sufficient for palette/type/sitemap generation |
| Tavily for competitor research | Firecrawl only | Tavily gives ranked results + summaries quickly; Firecrawl is for full-page scraping. Tavily for discovery, Firecrawl if deep content is needed (optional) |
| SSE for research progress | WebSocket | SSE is one-way (server to client), which is all Phase 18 needs — no client messages during generation. Consistent with existing SSE pattern in `fast_api_app.py` |
| Inline editing in the brief card | Separate edit page | Inline editing (contenteditable or textarea) on the review card reduces friction. No separate route needed. |

**Installation:** No new packages required. All dependencies are already present.

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── routers/
│   └── app_builder.py          # EXTEND: add POST /app-builder/projects/{id}/research
│                               #          and POST /app-builder/projects/{id}/approve-brief
├── services/
│   └── design_brief_service.py # NEW: research + synthesis orchestration
│
frontend/src/
├── app/app-builder/
│   └── [projectId]/
│       ├── page.tsx             # REPLACE stub: redirect to /research if stage='research'
│       └── research/
│           └── page.tsx         # NEW: design brief review + approval page
├── components/app-builder/
│   ├── DesignBriefCard.tsx      # NEW: editable design system preview card
│   ├── SitemapCard.tsx          # NEW: editable sitemap preview card
│   └── ResearchProgressBar.tsx  # NEW: step-by-step research progress indicator
├── services/
│   └── app-builder.ts           # EXTEND: startResearch(), approveBrief(), updateDesignBrief()
└── types/
    └── app-builder.ts           # EXTEND: DesignBrief, SitemapPage, BuildPlan interfaces
```

### Pattern 1: Design Research + Synthesis Service

**What:** `design_brief_service.py` is a pure async service (no FastAPI, no ADK) that takes a `creative_brief` dict and returns research findings + generated DESIGN.md + SITE.md + build plan. Broken into discrete async steps that can be SSE-streamed.

**When to use:** Called from the FastAPI router's SSE endpoint. Each step yields a progress event before moving to the next.

**Example:**
```python
# app/services/design_brief_service.py
from app.mcp.tools.web_search import TavilySearchTool
from google import genai
from google.genai import types as genai_types

DESIGN_SYSTEM_PROMPT = """You are a UI design director generating a design brief.
Given a creative brief and competitor research, produce:

DESIGN_SYSTEM_MARKDOWN: (full DESIGN.md content in markdown)
SITEMAP_JSON: (JSON array of page objects)
PALETTE: (3-5 hex colors with names)
TYPOGRAPHY: (heading font + body font + scale)
SPACING: (base unit and scale description)

creative_brief: {brief}
competitor_research: {research}
"""

async def run_design_research(
    creative_brief: dict,
    project_id: str,
    user_id: str,
) -> AsyncGenerator[dict, None]:
    """Stream design research progress events."""
    search_tool = TavilySearchTool()

    # Step 1: Parallel competitor + inspiration searches
    yield {"step": "searching", "message": "Researching design space..."}
    what = creative_brief.get("what", "web app")
    vibe = creative_brief.get("vibe", "clean minimal")
    search_queries = [
        f"{what} website design {vibe} examples",
        f"{what} color palette typography inspiration",
    ]
    results = await asyncio.gather(*[
        search_tool.search(q, max_results=5, search_depth="basic")
        for q in search_queries
    ])

    # Step 2: Synthesize with Gemini Flash
    yield {"step": "synthesizing", "message": "Generating design brief..."}
    research_summary = _flatten_search_results(results)
    client = genai.Client()
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=DESIGN_SYSTEM_PROMPT.format(
            brief=json.dumps(creative_brief),
            research=research_summary,
        ),
        config=genai_types.GenerateContentConfig(
            temperature=0.4,
            max_output_tokens=2000,
        ),
    )

    # Step 3: Parse and persist
    yield {"step": "saving", "message": "Saving design brief..."}
    design_doc = _parse_design_response(response.text)
    await _persist_design_draft(design_doc, project_id, user_id)

    yield {"step": "ready", "data": design_doc}
```

### Pattern 2: FastAPI SSE Endpoint for Research Progress

**What:** POST triggers research; response is a text/event-stream. Each research step emits a JSON event. Frontend reads via EventSource or custom SSE hook.

**When to use:** Long-running operations (research + Gemini synthesis can take 10-30 seconds). SSE gives the user progress feedback.

**Example:**
```python
# app/routers/app_builder.py — new endpoint
from fastapi.responses import StreamingResponse

@router.post("/app-builder/projects/{project_id}/research")
async def start_research(
    project_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> StreamingResponse:
    """Kick off design research and stream progress events."""
    # Verify project ownership
    supabase = get_service_client()
    result = (
        supabase.table("app_projects")
        .select("creative_brief, stage")
        .eq("id", project_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    project = result.data

    async def event_generator():
        async for event in run_design_research(
            creative_brief=project["creative_brief"],
            project_id=project_id,
            user_id=user_id,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

### Pattern 3: Explicit Approval Endpoint

**What:** A separate POST endpoint that (1) locks the `design_systems` row (`locked=true`), (2) saves the (possibly user-edited) design system and sitemap back to `app_projects`, (3) generates the build plan via Gemini, (4) advances stage from `research`/`brief` to `building`.

**When to use:** Only after user clicks "Approve & Generate Build Plan". Never called automatically.

**Example:**
```python
class ApproveBriefRequest(BaseModel):
    """Payload for approving the design brief."""
    design_system: dict   # user-edited design tokens (colors, typography, spacing)
    sitemap: list[dict]   # user-edited list of pages
    raw_markdown: str     # user-edited DESIGN.md text

@router.post("/app-builder/projects/{project_id}/approve-brief")
async def approve_brief(
    project_id: str,
    body: ApproveBriefRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> dict:
    """Lock design system, generate build plan, advance to 'building' stage."""
    supabase = get_service_client()

    # 1. Lock design system
    supabase.table("design_systems").update({"locked": True}).eq(
        "project_id", project_id
    ).execute()

    # 2. Generate build plan via Gemini
    build_plan = await _generate_build_plan(body.sitemap, body.design_system)

    # 3. Persist approved data + build plan to app_projects
    supabase.table("app_projects").update({
        "design_system": body.design_system,
        "sitemap": body.sitemap,
        "build_plan": build_plan,
        "stage": "building",
        "status": "generating",
    }).eq("id", project_id).eq("user_id", user_id).execute()

    # 4. Advance build_sessions stage
    supabase.table("build_sessions").update({"stage": "building"}).eq(
        "project_id", project_id
    ).execute()

    return {"success": True, "build_plan": build_plan, "stage": "building"}
```

### Pattern 4: Build Plan Generation

**What:** Gemini Flash takes the approved sitemap (list of pages) and design system, and returns a structured JSON array of build phases — each phase contains one or more screens with their page type, device targets, and dependency list.

**Expected output shape (stored in `app_projects.build_plan`):**
```json
[
  {
    "phase": 1,
    "label": "Homepage",
    "screens": [
      {"name": "Homepage — Desktop", "page": "home", "device": "DESKTOP"},
      {"name": "Homepage — Mobile", "page": "home", "device": "MOBILE"}
    ],
    "dependencies": []
  },
  {
    "phase": 2,
    "label": "About",
    "screens": [
      {"name": "About — Desktop", "page": "about", "device": "DESKTOP"}
    ],
    "dependencies": [1]
  }
]
```

**Why this shape:** Matches `app_screens.device_type` CHECK constraint (`DESKTOP/MOBILE/TABLET`). The `dependencies` array (list of phase numbers) enables the UI to show a dependency graph in Phase 19+.

### Pattern 5: GsdProgressBar Dynamic Stage (Deferred from Phase 17)

**What:** Phase 17 hardcoded `currentStage="questioning"` in `/app-builder/layout.tsx`. Phase 18 must make this dynamic — the layout needs to read the project's actual stage when on a project page.

**The problem:** `layout.tsx` is a Server Component; the project ID is in the URL (`/app-builder/[projectId]/...`). The layout receives `params` in Next.js App Router via the segment hierarchy.

**Solution:** The `[projectId]` segment creates a nested layout that can read `params.projectId`, fetch the project, and pass `currentStage` to `GsdProgressBar`. The root `/app-builder/layout.tsx` keeps the bar for the `/new` page; the `[projectId]/layout.tsx` owns the dynamic bar.

**Example:**
```typescript
// frontend/src/app/app-builder/[projectId]/layout.tsx  (NEW — Server Component)
import { getProject } from '@/services/app-builder';
import { GsdProgressBar } from '@/components/app-builder/GsdProgressBar';

export default async function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const project = await getProject(projectId).catch(() => null);
  const stage = project?.stage ?? 'research';

  return (
    <div className="min-h-screen bg-slate-50">
      <GsdProgressBar currentStage={stage} />
      <main className="max-w-4xl mx-auto px-4 py-8">{children}</main>
    </div>
  );
}
```

Note: `params` is a Promise in Next.js 15+ App Router — must be awaited. This matches the project's Next.js 16.1.4 version.

### Pattern 6: DESIGN.md and SITE.md Document Shapes

These are the canonical document formats persisted in the DB:

**DESIGN.md (stored as `design_systems.raw_markdown`):**
```markdown
# Design System — [Project Title]

## Colors
- Primary: #6366F1 (Indigo 500)
- Background: #FFFFFF
- Surface: #F8FAFC (Slate 50)
- Text: #0F172A (Slate 900)
- Accent: #F59E0B (Amber 400)

## Typography
- Heading: Inter, 700, scale: 48/36/28/22/18
- Body: Inter, 400, 16px/24px line-height
- Caption: Inter, 500, 12px

## Spacing
- Base unit: 4px
- Section padding: 80px top/bottom
- Card padding: 24px

## Components
- Buttons: Rounded-lg, indigo fill, white text
- Cards: White bg, slate-200 border, 12px radius
```

**SITE.md (stored as `app_projects.sitemap` JSONB array):**
```json
[
  {"page": "home",    "title": "Homepage",    "sections": ["hero", "features", "cta"], "device_targets": ["DESKTOP", "MOBILE"]},
  {"page": "about",   "title": "About",       "sections": ["story", "team"],           "device_targets": ["DESKTOP"]},
  {"page": "pricing", "title": "Pricing",     "sections": ["tiers", "faq"],            "device_targets": ["DESKTOP", "MOBILE"]}
]
```

### Anti-Patterns to Avoid

- **Auto-advancing to `building` stage after research:** FLOW-03 is explicit — user must approve. Never call `/approve-brief` automatically.
- **Calling Stitch in Phase 18:** Stitch generates HTML screens. Phase 18 is pre-generation. No Stitch calls belong here.
- **Storing DESIGN.md only as raw markdown:** The `design_systems` table has structured `colors`, `typography`, `spacing` JSONB columns. Parse the Gemini response into structured fields AND store raw_markdown. The structured fields enable programmatic injection into future Stitch prompts.
- **Blocking the event loop with Tavily sync calls:** `TavilySearchTool.search()` is async. Always `await` it. Do not use `_run_async()` wrapper — that is for ADK sync contexts only.
- **Using ADK Runner for the research service:** This phase does not need an ADK agent. Direct Gemini API calls + service functions are simpler, testable, and avoid ADK session lifecycle complexity.
- **`params` not awaited in Next.js 16 layouts:** `params` is a Promise in App Router for Next.js 15+. Use `const { projectId } = await params` — not `params.projectId` directly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Web search for competitor research | Custom httpx scraper | `TavilySearchTool` from `app/mcp/tools/web_search.py` | Already handles rate limiting, PII sanitization, API key mgmt, error handling |
| Design token parsing from Gemini response | Custom regex parser | Structured prompt with explicit JSON output section + `json.loads()` | Gemini with explicit JSON format instructions is reliable; regex breaks on slight format variation |
| Color palette generation | Custom color algorithm | Gemini Flash with design vocabulary prompt | Gemini incorporates design principles (contrast ratios, harmony) better than HSL math |
| SSE streaming | WebSocket or polling | `StreamingResponse` with `text/event-stream` | Existing pattern in `fast_api_app.py`; one-way, no client send needed |
| Auth in new endpoints | Custom JWT decode | `get_current_user_id` from `app/routers/onboarding.py` | Established Depends() pattern used in all 25+ routers |
| Supabase client in service | Per-request instantiation | `get_service_client()` from `app/services/supabase` | Pooling, RLS bypass for service-role writes |

**Key insight:** Phase 18 reuses everything from Phase 16 and 17. The hard work is orchestration: chaining Tavily → Gemini → Supabase → SSE events in the right order.

---

## Common Pitfalls

### Pitfall 1: Gemini Response Not Parseable as Structured Data

**What goes wrong:** Gemini returns a freeform markdown response when you need parseable JSON for `colors`, `typography`, etc.

**Why it happens:** LLMs drift from format instructions unless explicitly constrained.

**How to avoid:** Use `response_mime_type="application/json"` in `GenerateContentConfig` for the SITE.md sitemap (pure JSON output). For DESIGN.md, use two separate Gemini calls: one for the markdown document (human-readable), one for the structured tokens (JSON). This matches the `prompt_enhancer.py` pattern.

**Warning signs:** `json.loads()` raising `JSONDecodeError` on the Gemini response. Add a fallback that returns empty structured data and logs the raw response.

### Pitfall 2: Stage Does Not Advance After Research Completes

**What goes wrong:** Research SSE completes and `step: ready` fires, but the project's stage is still `questioning` — the progress bar does not update.

**Why it happens:** Research completion and stage advance are separate operations. The service saves the draft design system but does not advance the stage (that's the approval action's job). The frontend must advance stage to `research` when research starts (so the progress bar shows the right step), and then to `brief` when research completes.

**How to avoid:** Two-phase stage model:
- When the user navigates to `/app-builder/[projectId]/research`, PATCH stage to `research` if it's still `questioning`.
- When SSE `step: ready` arrives, PATCH stage to `brief` (brief is ready for review).
- When user clicks Approve, approve-brief endpoint advances to `building`.

**Warning signs:** Progress bar shows `Questioning` while the research page is visible.

### Pitfall 3: Design System Row Already Exists on Retry

**What goes wrong:** User refreshes the research page, triggering a second `POST /research` call that tries to INSERT a new `design_systems` row, failing with a unique constraint violation.

**Why it happens:** The research endpoint creates a `design_systems` row per call. On retry, the row already exists.

**How to avoid:** Use UPSERT: `supabase.table("design_systems").upsert({...}, on_conflict="project_id").execute()`. The `design_systems` table does not have a unique constraint on `project_id` in the Phase 16 migration — add `UNIQUE(project_id)` in a Phase 18 migration, or use `SELECT` first and `UPDATE` if exists, `INSERT` if not.

**Warning signs:** `23505 unique_violation` from Supabase on the second POST /research call.

### Pitfall 4: Frontend SSE Hook Memory Leak

**What goes wrong:** The SSE `EventSource` connection is not closed when the component unmounts. Leaves a dangling connection, causes state updates on unmounted components.

**Why it happens:** `EventSource` must be explicitly closed on cleanup.

**How to avoid:** In the SSE hook's `useEffect`, always return a cleanup function: `return () => { eventSource.close(); }`. Use `useRef` to track the EventSource instance.

**Example:**
```typescript
useEffect(() => {
  const es = new EventSource(`${API_BASE}/app-builder/projects/${projectId}/research`, {
    // Note: EventSource doesn't support custom headers for auth.
    // Use a short-lived token in query param, or POST to start then GET for events.
  });
  es.onmessage = (e) => { /* handle */ };
  return () => es.close();  // cleanup on unmount
}, [projectId]);
```

**Critical note:** Native `EventSource` does NOT support custom headers (no `Authorization` header). Solution: POST `/research` endpoint returns `202 Accepted` with a `stream_token` (short-lived UUID stored in Redis or Supabase), then GET `/research/stream?token=...` streams events using the token for auth. Alternatively, use `fetch()` with a ReadableStream instead of native EventSource (same auth header pattern).

**Warning signs:** Network tab shows the SSE connection persisting after route navigation.

### Pitfall 5: Tailored Design Brief Stored Only In-Memory

**What goes wrong:** User edits the DESIGN.md text in the browser. They click Approve. The approval request sends the edited text, but if they reload before approving, their edits are lost.

**Why it happens:** Edits live in React state only until approval is POSTed.

**How to avoid:** Auto-save edits to the draft (PATCH `/app-builder/projects/{id}/design-draft`) with debounce (500ms). The approval endpoint reads from the `design_systems` row, not from the POST body — this removes a class of "stale data in POST" bugs. The POST body is still accepted as override for the common case.

---

## Code Examples

Verified patterns from the existing codebase:

### Gemini Flash Async Call (from prompt_enhancer.py)
```python
# Source: app/services/prompt_enhancer.py
from google import genai
from google.genai import types as genai_types

client = genai.Client()
response = await client.aio.models.generate_content(
    model="gemini-2.5-flash",
    contents=f"{description}{vocab_context}",
    config=genai_types.GenerateContentConfig(
        system_instruction=ENHANCEMENT_SYSTEM_PROMPT,
        temperature=0.4,
        max_output_tokens=2000,
    ),
)
result_text = response.text
```

### Tavily Search (from app/mcp/tools/web_search.py)
```python
# Source: app/mcp/tools/web_search.py
search_tool = TavilySearchTool()
result = await search_tool.search(
    query="SaaS landing page design minimal 2025",
    max_results=5,
    search_depth="basic",
    include_answer=True,
)
# result["results"] is a list of {url, title, content, score}
# result["answer"] is the AI-generated summary
```

### Parallel Async Gather (from track_runner.py)
```python
# Source: app/agents/research/tools/track_runner.py
results = await asyncio.gather(
    search_tool.search(query_a, max_results=5),
    search_tool.search(query_b, max_results=5),
)
```

### FastAPI StreamingResponse SSE (from fast_api_app.py pattern)
```python
# Source: app/fast_api_app.py SSE pattern (A2A streaming)
from fastapi.responses import StreamingResponse

async def event_generator():
    for event in events:
        yield f"data: {json.dumps(event)}\n\n"

return StreamingResponse(
    event_generator(),
    media_type="text/event-stream",
    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
)
```

### Supabase UPSERT Pattern
```python
# Source: supabase-py 2.27.2 docs — on_conflict for upsert
supabase.table("design_systems").upsert(
    {
        "project_id": project_id,
        "user_id": user_id,
        "colors": colors_json,
        "typography": typography_json,
        "raw_markdown": design_md_text,
        "locked": False,
    },
    on_conflict="project_id",
).execute()
# Requires UNIQUE constraint on design_systems(project_id) — add in Phase 18 migration
```

### Next.js App Router Server Component with Awaited Params (Next.js 16)
```typescript
// Source: Next.js 15+ App Router — params is Promise
export default async function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  // fetch project here
}
```

### Auth-Capable SSE via Fetch ReadableStream (avoids EventSource auth limitation)
```typescript
// Source: project pattern from existing SSE streaming in chat components
async function startResearch(projectId: string, onEvent: (e: object) => void) {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/app-builder/projects/${projectId}/research`, {
    method: 'POST',
    headers,
  });
  if (!res.ok || !res.body) throw new Error('Research failed to start');

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
        onEvent(JSON.parse(line.slice(6)));
      }
    }
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Upfront full-form "describe everything" | Staged discovery → research → brief review | Industry shift 2023-2025 (v0, Bolt, Lovable) | User sees AI working before committing; higher engagement |
| Static design system in config file | AI-generated, user-editable, locked JSONB | 2024 AI design tooling (Galileo AI, Uizard) | Personalized to user's creative brief, not a generic template |
| Blocking HTTP for long AI operations | SSE / streaming for progress feedback | Next.js 13+ / React 18 | Users see incremental progress; no 30-second blank wait |
| Design token as raw CSS variables | Structured JSONB + raw markdown dual storage | Best practice since design tokens spec 2022 | Programmatic injection into LLM prompts AND human-readable review |
| Native `EventSource` for auth-gated streams | `fetch()` ReadableStream with Bearer header | Always been the case; often overlooked | Avoids CORS/auth issues; consistent with rest of project's fetch pattern |

**Deprecated/outdated:**
- `getServerSideProps`: Project uses App Router exclusively. Never use.
- ADK `Runner` for research: Not needed here. Direct Gemini async calls are simpler and testable without ADK session lifecycle overhead.

---

## Open Questions

1. **Does `design_systems` need a UNIQUE constraint on `project_id` for the upsert pattern?**
   - What we know: The Phase 16 migration creates `design_systems` with `project_id UUID NOT NULL REFERENCES app_projects(id)` but no UNIQUE constraint.
   - What's unclear: Supabase upsert `on_conflict` requires a unique index. Without it, the upsert will INSERT a second row.
   - Recommendation: Add a Phase 18 migration: `ALTER TABLE design_systems ADD CONSTRAINT design_systems_project_id_unique UNIQUE(project_id);` This is a single-line additive migration, safe on an empty table.

2. **Should the research step also use Firecrawl to scrape competitor pages for deeper content?**
   - What we know: `FirecrawlScrapeTool` exists and is configured. Firecrawl scrapes full HTML → markdown, which gives richer design context than Tavily summaries.
   - What's unclear: Scraping 3-5 competitor pages adds 15-30 seconds to research time. Is that acceptable?
   - Recommendation: Make it optional — do Tavily-only search first (fast, ~3s), yield `step: ready` with that. Include a "Go deeper" option that triggers Firecrawl scraping. For Phase 18, Tavily-only is sufficient. Firecrawl can be added in a future iteration.

3. **How does the `[projectId]` layout get the project data without blocking hydration?**
   - What we know: Next.js App Router Server Components fetch at render time. `getProject()` makes an authenticated fetch to FastAPI, which queries Supabase. This is ~50-200ms per render.
   - What's unclear: If the project fetch fails (project not found, network error), the layout throws and breaks the entire page tree.
   - Recommendation: Use `.catch(() => null)` on the `getProject()` call in the layout. Default stage to `'research'` if fetch fails. Add a `notFound()` call only in the page component (not the layout) where a 404 is meaningful.

4. **Stage sequencing: `research` vs `brief` — are two separate stages needed?**
   - What we know: The DB CHECK constraint has 7 stages: `questioning, research, brief, building, verifying, shipping, done`. The GSD_STAGES const in TypeScript matches. Phase 18 spans both `research` and `brief` stages.
   - What's unclear: Does the planner want `research` to be "system is running research" and `brief` to be "brief is ready for user review"?
   - Recommendation: Yes — use both stages as designed. `research` = in-progress (spinner shown). `brief` = review mode (edit cards shown). `building` = approved (Phase 19 takes over). This matches the DB constraint and GSD_STAGES UI labels.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), vitest 4.0.18 (frontend) |
| Config file | `pytest.ini` (backend), `frontend/scripts/run-vitest.mjs` |
| Quick run command | `uv run pytest tests/unit/app_builder/ -x` |
| Full suite command | `uv run pytest tests/unit/ -x && cd frontend && node scripts/run-vitest.mjs` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FLOW-02 | `run_design_research()` calls TavilySearchTool and returns research results | unit | `uv run pytest tests/unit/app_builder/test_design_brief_service.py::test_research_calls_tavily -x` | Wave 0 |
| FLOW-02 | Research results feed Gemini synthesis call | unit | `uv run pytest tests/unit/app_builder/test_design_brief_service.py::test_synthesis_uses_research -x` | Wave 0 |
| FLOW-02 | POST /app-builder/projects/{id}/research returns SSE stream with expected steps | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_research_sse_steps -x` | Wave 0 (extend existing file) |
| FLOW-03 | `_parse_design_response()` extracts colors, typography, spacing from Gemini text | unit | `uv run pytest tests/unit/app_builder/test_design_brief_service.py::test_parse_design_response -x` | Wave 0 |
| FLOW-03 | POST /approve-brief locks design_systems row and advances stage to 'building' | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_approve_brief_locks_and_advances -x` | Wave 0 (extend existing file) |
| FLOW-03 | DesignBriefCard renders editable fields from design system data (frontend) | unit | `cd frontend && node scripts/run-vitest.mjs src/__tests__/components/DesignBriefCard.test.tsx` | Wave 0 |
| FLOW-03 | Approve button calls approveBrief() and redirects to /building (frontend) | unit | `cd frontend && node scripts/run-vitest.mjs src/__tests__/components/ResearchPage.test.tsx` | Wave 0 |
| FLOW-04 | `_generate_build_plan()` returns array with phase/screens/dependencies structure | unit | `uv run pytest tests/unit/app_builder/test_design_brief_service.py::test_build_plan_structure -x` | Wave 0 |
| FLOW-04 | Build plan stored in app_projects.build_plan after approval | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_approve_brief_saves_build_plan -x` | Wave 0 (extend existing file) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/app_builder/ -x`
- **Per wave merge:** `uv run pytest tests/unit/ -x && cd frontend && node scripts/run-vitest.mjs`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/app_builder/test_design_brief_service.py` — covers FLOW-02, FLOW-03, FLOW-04 (new file; mock TavilySearchTool and genai.Client)
- [ ] `frontend/src/__tests__/components/DesignBriefCard.test.tsx` — covers FLOW-03 (editable card rendering)
- [ ] `frontend/src/__tests__/components/ResearchPage.test.tsx` — covers FLOW-03 (SSE progress + approval flow)
- [ ] Phase 18 migration: `supabase/migrations/20260321700000_design_brief_unique.sql` — adds UNIQUE(project_id) on design_systems

*(Existing `tests/unit/app_builder/test_app_builder_router.py` is extended with new endpoint tests — not a new file.)*

---

## Sources

### Primary (HIGH confidence)
- `supabase/migrations/20260321400000_app_builder_schema.sql` — definitive column names, JSONB columns (`design_system`, `sitemap`, `build_plan` on app_projects; `colors`, `typography`, `spacing`, `raw_markdown`, `locked` on design_systems)
- `app/routers/app_builder.py` — Phase 17 router patterns: auth dependency, service client, PATCH stage, Pydantic models
- `app/services/prompt_enhancer.py` — Gemini Flash async call pattern (`client.aio.models.generate_content`, `GenerateContentConfig`, temperature, max_output_tokens)
- `app/mcp/tools/web_search.py` — `TavilySearchTool.search()` async signature, return shape
- `app/agents/research/tools/track_runner.py` — `asyncio.gather` parallel search pattern
- `frontend/src/types/app-builder.ts` — `GSD_STAGES` const, `GsdStage` type, `AppProject` interface (confirmed columns present)
- `frontend/src/services/app-builder.ts` — `getAuthHeaders()` pattern, fetch wrapper shape
- `frontend/src/app/app-builder/layout.tsx` — hardcoded `currentStage="questioning"` — confirmed Phase 18 must make this dynamic
- `.planning/phases/17-creative-questioning/17-02-SUMMARY.md` — confirmed `params` is Promise in Next.js 16, `toBeDisabled()` not available in vitest
- `.planning/config.json` — `nyquist_validation: true` — validation architecture section required

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS-v2.md` + `.planning/ROADMAP-v2.md` — phase scope and success criteria (project-authored)
- `.planning/STATE.md` — locked decisions from prior phases (v2.0 design system persistence, Stitch patterns)
- `app/agents/tools/creative_brief.py` — established pattern for "generate then persist to knowledge store" — adapted for design brief

### Tertiary (LOW confidence)
- General knowledge: `EventSource` does not support custom headers — verified by well-known browser limitation; specific fetch/ReadableStream alternative is industry-standard pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified from existing code; no new installs needed
- Architecture patterns: HIGH — derived directly from Phase 16/17 code, DB schema, and service patterns
- DB schema: HIGH — verified from migration SQL; all needed columns exist
- Pitfalls: HIGH — derived from known browser limitations (EventSource auth) and Supabase upsert behavior
- Test map: HIGH — existing pytest + vitest setup verified; test file locations match Phase 16/17 patterns

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable stack; DB schema locked by Phase 16 migration)
