# Phase 20: Iteration Loop - Research

**Researched:** 2026-03-23
**Domain:** Stitch MCP edit_screens, design system enforcement, version history/rollback, GSD approval checkpoint UX
**Confidence:** HIGH (Stitch tool schemas verified via live CLI execution; architecture patterns from codebase inspection)

---

## Summary

Phase 20 adds four capabilities on top of Phase 19's generation infrastructure: (1) natural-language screen editing via Stitch `edit_screens`, (2) automatic design-system enforcement once the DESIGN.md is locked, (3) per-screen version history with rollback using the existing `screen_variants` table, and (4) GSD-style approval checkpoint cards that block workflow advancement until explicit user confirmation.

The critical discovery is the exact `edit_screens` tool schema — it requires `projectId`, `prompt`, and `selectedScreenIds` (an array of bare stitch screen IDs, without the `screens/` prefix). The `stitch_screen_id` column on `screen_variants` already captures these IDs from Phase 19, so edit operations can look up the Stitch screen ID from the selected variant row and pass it directly to `edit_screens`. No DB migration is needed for the core editing capability.

Design system enforcement is already partially implemented in `_build_generation_prompt()` in `app_builder.py`. For Phase 20, the same pattern is extended: when `design_systems.locked = true` for a project, the full `raw_markdown` from the design system is prepended to every edit prompt, making the locked DESIGN.md the authoritative context for Stitch generation.

**Primary recommendation:** Use `edit_screens` (not `generate_screen_from_text`) for iteration — it maintains continuity with the existing Stitch screen rather than creating an orphaned new screen. The `iteration` column on `screen_variants` (already in the schema, defaults to 1) tracks which edit pass produced each variant row. Version history display and rollback are pure frontend+DB operations with no new Stitch calls required.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ITER-01 | User can describe changes to a screen ("make the hero bigger") and Stitch edit_screens re-generates | edit_screens tool schema verified — accepts projectId, prompt, selectedScreenIds array |
| ITER-02 | Once DESIGN.md is approved, all subsequent screens automatically follow the locked design system | design_systems.locked column exists; inject raw_markdown into every prompt when locked=true |
| ITER-03 | System tracks all iterations per screen with version history and rollback to any previous version | screen_variants table has iteration column; rollback = select-variant PATCH, already implemented |
| ITER-04 | GSD-style approval checkpoint cards at each stage — user must approve before the workflow advances | GsdProgressBar + stage state machine already built; approval card is a new component that calls advance_stage |
| FLOW-05 | Each build phase follows a generate → preview → iterate → approve loop with GSD-style checkpoint cards | Building page already has generate→preview; iteration panel + ApprovalCheckpoint card close the loop |
</phase_requirements>

---

## Standard Stack

### Core (all already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@_davideast/stitch-mcp` | latest (npx) | `edit_screens` tool call via MCP session | Already singleton; same call_tool() interface |
| `app/services/stitch_mcp.py` | project | StitchMCPService singleton with asyncio.Lock | Established in Phase 16; edit calls slot in identically |
| `app/services/stitch_assets.py` | project | persist_screen_assets() for permanent URLs | Same pattern as generation — edit output must be persisted |
| Supabase `screen_variants` table | existing | Version history via `iteration` column | Already in schema; no new table needed |
| FastAPI SSE (StreamingResponse) | existing | Stream edit progress to frontend | Same SSE pattern as generate-screen endpoint |
| React + framer-motion | existing | Frontend iteration panel and approval card | GenerationProgress already uses framer-motion |
| Tailwind CSS 4 | existing | All new UI components | Project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `lucide-react` | existing | Icons for approval card (CheckCircle, X, RotateCcw) | Matches GsdProgressBar icon pattern |
| pytest + `unittest.mock` | existing | Backend service tests | Project test standard |
| vitest + `@testing-library/react` | existing | Frontend component tests | Project frontend test standard |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `edit_screens` | `generate_screen_from_text` | generate_screen_from_text creates an orphaned screen with no continuity with the original; edit_screens operates on the existing stitch_screen_id maintaining design coherence |
| Inline textarea in building page | Separate iteration modal | Modal adds navigation friction; inline textarea directly below the preview is faster for iteration loops |
| New `screen_iterations` table | Existing `screen_variants` table + `iteration` column | The `iteration` INTEGER column already exists on screen_variants; adding rows with incrementing iteration values gives full version history without schema changes |

**Installation:** No new packages required. All dependencies are in place.

---

## Architecture Patterns

### Recommended Project Structure (additions to existing)

```
app/
  services/
    iteration_service.py      # edit_screen_variant() async generator
  routers/
    app_builder.py            # add: POST /{projectId}/screens/{screenId}/iterate
                              #      POST /{projectId}/screens/{screenId}/approve
                              #      GET  /{projectId}/screens/{screenId}/history
                              #      POST /{projectId}/screens/{screenId}/rollback/{variantId}

frontend/src/
  components/app-builder/
    IterationPanel.tsx         # Textarea + submit triggers edit SSE stream
    ApprovalCheckpointCard.tsx # "Approve this screen" card; blocks stage advance
    VersionHistoryPanel.tsx    # Scrollable list of past variant thumbnails with rollback button
  app/app-builder/[projectId]/
    building/page.tsx          # Extended: adds IterationPanel + ApprovalCheckpointCard + VersionHistoryPanel

tests/unit/app_builder/
  test_iteration_service.py   # Tests for edit_screen_variant async generator

frontend/src/__tests__/components/
  IterationPanel.test.tsx
  ApprovalCheckpointCard.test.tsx
  VersionHistoryPanel.test.tsx
```

### Pattern 1: edit_screens via StitchMCPService

**What:** Call `edit_screens` with the stitch_screen_id from the selected variant, the user's change description (optionally prefixed with the locked DESIGN.md), and the stitch_project_id. Persist returned assets before yielding SSE events.

**When to use:** ITER-01 — user submits an iteration request from the UI.

**Exact tool schema (verified via `npx @_davideast/stitch-mcp tool edit_screens -s`):**
```json
{
  "name": "edit_screens",
  "description": "Edits existing screens within a project using a text prompt.",
  "arguments": {
    "projectId": "string (required) - The project ID, without the `projects/` prefix",
    "prompt": "string (required) - The input text describing the desired changes",
    "selectedScreenIds": "array (required) - The screen IDs of screens to edit, without the `screens/` prefix",
    "deviceType": "string (optional)",
    "modelId": "string (optional)"
  }
}
```

**Example implementation pattern:**
```python
# Source: live stitch-mcp CLI tool schema + existing screen_generation_service.py pattern
async def edit_screen_variant(
    project_id: str,
    screen_id: str,
    user_id: str,
    stitch_project_id: str,
    stitch_screen_id: str,   # from screen_variants.stitch_screen_id
    change_description: str,
    design_system_markdown: str | None,  # injected if design_systems.locked = true
    iteration_number: int,
) -> AsyncIterator[dict[str, Any]]:
    """Edit an existing Stitch screen and persist the result as a new screen_variants row."""
    service = get_stitch_service()

    # Inject locked DESIGN.md as context prefix
    prompt = change_description
    if design_system_markdown:
        prompt = f"{design_system_markdown}\n\nEdits: {change_description}"

    yield {"step": "editing", "message": f"Applying edit: {change_description[:60]}..."}

    # CRITICAL: Sequential await — same Lock constraint as generate calls
    stitch_response = await service.call_tool(
        "edit_screens",
        {
            "projectId": stitch_project_id,
            "prompt": prompt,
            "selectedScreenIds": [stitch_screen_id],  # array, bare ID without "screens/" prefix
        },
    )

    # Persist BEFORE yielding — callers get permanent URLs
    persisted = await persist_screen_assets(
        stitch_response=stitch_response,
        user_id=user_id,
        project_id=project_id,
        screen_id=screen_id,
        variant_index=iteration_number,
    )

    variant_id = str(uuid4())
    new_stitch_screen_id = stitch_response.get("screenId") or stitch_response.get("screen_id", "")

    supabase.table("screen_variants").insert({
        "id": variant_id,
        "screen_id": screen_id,
        "user_id": user_id,
        "variant_index": 0,           # iteration panel has one result at a time
        "stitch_screen_id": new_stitch_screen_id,  # IMPORTANT: update for future edits
        "html_url": persisted["html_url"],
        "screenshot_url": persisted["screenshot_url"],
        "prompt_used": change_description,
        "is_selected": True,
        "iteration": iteration_number,
    }).execute()

    # Deselect all previous variants for this screen
    supabase.table("screen_variants").update({"is_selected": False}).eq(
        "screen_id", screen_id
    ).neq("id", variant_id).execute()

    yield {
        "step": "edit_complete",
        "variant_id": variant_id,
        "screenshot_url": persisted["screenshot_url"],
        "html_url": persisted["html_url"],
        "iteration": iteration_number,
        "screen_id": screen_id,
    }
    yield {"step": "ready", "screen_id": screen_id, "iteration": iteration_number}
```

### Pattern 2: Design System Enforcement (ITER-02)

**What:** When a project has `design_systems.locked = true`, read `raw_markdown` from the design_systems table and prepend it to every edit prompt. This is the DESIGN.md content that was approved in Phase 18.

**When to use:** All screen generation and edit operations after the brief is approved.

**Example:**
```python
# Source: existing app_builder.py _build_generation_prompt() + design_systems table schema
async def _get_locked_design_markdown(project_id: str, user_id: str) -> str | None:
    """Return raw_markdown from design_systems if locked=True, else None."""
    supabase = get_service_client()
    result = (
        supabase.table("design_systems")
        .select("raw_markdown, locked")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    return row["raw_markdown"] if row.get("locked") else None
```

**Critical detail:** The DESIGN.md from Phase 18 is stored as `design_systems.raw_markdown` (TEXT column). The `design_systems` table already has a `locked` boolean. This is the exact mechanism Phase 18 uses — Phase 20 just reads and injects it.

### Pattern 3: Version History and Rollback (ITER-03)

**What:** The `screen_variants` table already stores all variants including iterated ones (via the `iteration` column). Version history is a sorted query; rollback is a selection operation.

**Version history endpoint:**
```python
# GET /app-builder/projects/{project_id}/screens/{screen_id}/history
# Returns all variants for a screen ordered by iteration DESC, then created_at DESC
result = supabase.table("screen_variants").select("*").eq("screen_id", screen_id).order("iteration", desc=True).order("created_at", desc=True).execute()
```

**Rollback endpoint:**
```python
# POST /app-builder/projects/{project_id}/screens/{screen_id}/rollback/{variant_id}
# Equivalent to select-variant: deselect all, select the target
supabase.table("screen_variants").update({"is_selected": False}).eq("screen_id", screen_id).execute()
supabase.table("screen_variants").update({"is_selected": True}).eq("id", variant_id).eq("user_id", user_id).execute()
```

**No new DB migration needed.** The `iteration` column (INTEGER, default 1) is already in the schema. The edit service writes new rows with `iteration = max_iteration + 1` — increment computed from:
```python
max_iter_result = supabase.table("screen_variants").select("iteration").eq("screen_id", screen_id).order("iteration", desc=True).limit(1).execute()
next_iteration = (max_iter_result.data[0]["iteration"] if max_iter_result.data else 0) + 1
```

### Pattern 4: GSD Approval Checkpoint Card (ITER-04, FLOW-05)

**What:** After a user selects a variant and optionally iterates, an `ApprovalCheckpointCard` blocks workflow advancement. "Approve" calls the existing `PATCH /app-builder/projects/{id}/stage` (advance_stage endpoint already built in Phase 17). The card is not a modal — it's an inline card below the preview, matching the ConfirmationCard UX established for admin operations in Phase 7.

**Card states:**
- `idle`: Shows "Approve this screen and continue" button
- `approving`: Button disabled, spinner shown (prevents double-clicks — same pattern as Phase 7 ConfirmationCard)
- `approved`: Green checkmark banner, card collapses

**Frontend component pattern:**
```tsx
// Source: Phase 7 ConfirmationCard pattern + Phase 18 ResearchPage approve button
function ApprovalCheckpointCard({
  screenName,
  onApprove,
  isApproved,
}: {
  screenName: string;
  onApprove: () => Promise<void>;
  isApproved: boolean;
}) {
  const [clicked, setClicked] = useState(false);  // Phase 7 double-click protection

  const handleApprove = async () => {
    if (clicked) return;
    setClicked(true);
    try {
      await onApprove();
    } finally {
      setClicked(false);
    }
  };

  if (isApproved) {
    return (
      <div className="rounded-xl border border-green-200 bg-green-50 p-4 text-green-700">
        Screen approved. Continue to the next screen.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-6">
      <h3 className="font-semibold text-indigo-900">{screenName}</h3>
      <p className="mt-1 text-sm text-indigo-600">Happy with this design? Approve to continue.</p>
      <button
        type="button"
        onClick={handleApprove}
        disabled={clicked}
        className="mt-4 rounded-md bg-indigo-600 px-6 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {clicked ? 'Approving...' : 'Approve screen'}
      </button>
    </div>
  );
}
```

**Approval action:** Sets `app_screens.approved = true` for the selected screen. The stage only advances when all screens in the current build phase are approved — or the user explicitly clicks "Advance to next stage" after approval. Approval of individual screens is tracked on `app_screens.approved` (column already exists, default false).

### Pattern 5: SSE Streaming for Edit Operations

**What:** Identical SSE pattern to generate-screen endpoint from Phase 18/19. No different streaming protocol needed.

**Endpoint pattern:**
```python
# POST /app-builder/projects/{project_id}/screens/{screen_id}/iterate
@router.post("/app-builder/projects/{project_id}/screens/{screen_id}/iterate")
async def iterate_screen(
    project_id: str,
    screen_id: str,
    body: IterateScreenRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> StreamingResponse:
    """Stream screen edit progress as Server-Sent Events."""
    # Fetch: stitch_project_id from app_projects, stitch_screen_id from selected variant
    # Fetch: locked design system markdown
    async def event_generator():
        async for event in edit_screen_variant(...):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

### Anti-Patterns to Avoid

- **Using `generate_screen_from_text` for iteration instead of `edit_screens`:** Creates orphan screens in the Stitch project with no continuity with the original; the new screen has no relationship to the prior design.
- **asyncio.gather on Stitch calls:** The StitchMCPService uses asyncio.Lock; gathering would deadlock. All Stitch calls must be sequential awaits.
- **Yielding SSE events before `persist_screen_assets` returns:** Caller would receive a short-lived Stitch signed URL that expires in minutes. Always persist first.
- **Losing stitch_screen_id after editing:** The response from `edit_screens` contains a new screenId. This must be stored in the new `screen_variants` row as `stitch_screen_id` — future edits on the iterated screen need the updated ID, not the original.
- **Advancing GSD stage from within the iteration service:** Stage transitions must only happen in response to explicit user approval actions (the approve endpoint). The iteration loop itself never advances stage.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Screen editing | Custom diff/patch or CSS injection | `edit_screens` Stitch MCP tool | Stitch has the model context and screen state; diffing HTML is fragile |
| Version storage | New `screen_iterations` table | Existing `screen_variants` table with `iteration` column | Column already in schema, Phase 19 already writes to it |
| Design token injection | Custom design language parser | Prepend `design_systems.raw_markdown` verbatim to prompt | DESIGN.md is already structured for LLM consumption by Phase 18 |
| Rollback | Time-travel DB snapshots | `PATCH /variants/{id}/select` (already implemented in Phase 19) | Rollback = selection; the old variant rows are never deleted |
| Approval gating | Custom workflow engine | `app_screens.approved` column + `advance_stage` endpoint | Schema and endpoint already exist |
| SSE streaming | WebSockets or polling | Same `StreamingResponse` SSE pattern from Phase 18/19 | Already established and tested in project |

**Key insight:** The schema designed in Phase 16 (`screen_variants.iteration`, `screen_variants.stitch_screen_id`, `app_screens.approved`, `design_systems.locked`) is pre-built for Phase 20's requirements. Phase 20 is primarily about wiring these together with new service methods and frontend UI.

---

## Common Pitfalls

### Pitfall 1: Wrong stitch_screen_id Passed to edit_screens

**What goes wrong:** `edit_screens` is passed the wrong screen ID — either the `app_screens.id` (our UUID) instead of `screen_variants.stitch_screen_id` (Stitch's bare hex ID), or the original generation's ID when the screen has been edited (the previous edit returns a new Stitch screen ID).

**Why it happens:** The `screen_variants` table has both `id` (our UUID) and `stitch_screen_id` (Stitch hex ID, e.g. `98b50e2ddc9943efb387052637738f61`). `edit_screens` requires the bare Stitch ID, not our UUID.

**How to avoid:** Always query `screen_variants` for the currently selected variant and use its `stitch_screen_id` field. After each edit, store the new `screenId` from the Stitch response into the newly created `screen_variants` row. The next edit chain: reads the newest `is_selected=true` row's `stitch_screen_id`.

**Warning signs:** Stitch returns an error or edits the wrong screen. The response `screenId` field differs from the requested one.

### Pitfall 2: Design System Injection Doubles Content

**What goes wrong:** The edit prompt contains the DESIGN.md content twice — once in the original prompt and again in the prefix.

**Why it happens:** `_build_generation_prompt()` already injects color palette and typography from `design_system` JSONB. Adding the full `raw_markdown` as a prefix duplicates this.

**How to avoid:** In the iteration service, when `design_system_markdown` is present, use it as the sole design context instead of also calling `_build_generation_prompt`. The `raw_markdown` from Phase 18 already contains everything.

### Pitfall 3: Approval State Lost on Page Refresh

**What goes wrong:** User approves a screen, navigates away, and the approval state is lost.

**Why it happens:** `app_screens.approved` is stored in DB but the frontend reads it only once at page load.

**How to avoid:** The approve endpoint writes `app_screens.approved = true` to the DB. The building page fetches variant list and screen state on mount (useEffect + getProject call already exists). Approved state should be derived from the screen's DB record, not just React local state.

### Pitfall 4: edit_screens Returns a New Screen with No HTML URL

**What goes wrong:** `edit_screens` response may not include `html_url` / `htmlUrl` directly (unlike `generate_screen_from_text`). The response shape may only contain `screenId`.

**Why it happens:** Stitch's edit_screens may return only the new screenId, requiring a subsequent `get_screen` call to retrieve the download URLs. This is similar to how `generate_screen_from_text` behaves when the generation is async.

**How to avoid:** After calling `edit_screens`, check the response for html_url / htmlUrl. If absent, call `get_screen` with the returned screenId to retrieve the download URLs before calling `persist_screen_assets`. Mirror the error-handling pattern already in `stitch_assets.py` (falls back to temp URL on error).

**Code pattern:**
```python
stitch_response = await service.call_tool("edit_screens", {...})
# If edit_screens doesn't return html_url, fetch it
if not (stitch_response.get("html_url") or stitch_response.get("htmlUrl")):
    screen_id_from_stitch = stitch_response.get("screenId") or stitch_response.get("id")
    if screen_id_from_stitch:
        stitch_response = await service.call_tool(
            "get_screen",
            {
                "projectId": stitch_project_id,
                "screenId": screen_id_from_stitch,
                "name": f"projects/{stitch_project_id}/screens/{screen_id_from_stitch}",
            },
        )
```

### Pitfall 5: Iteration Count Computed Client-Side

**What goes wrong:** Frontend increments iteration number in state. On refresh the count resets, creating duplicate `iteration=2` rows.

**Why it happens:** Iteration number should be computed server-side from the DB.

**How to avoid:** The iteration service queries `MAX(iteration)` from `screen_variants` for the given `screen_id` before inserting the new row. This is authoritative regardless of frontend state.

### Pitfall 6: Approve Endpoint Advances Stage for All Screens When Only One Is Approved

**What goes wrong:** User approves one screen and the stage advances to "verifying" prematurely.

**Why it happens:** Stage advance is triggered per-screen approval rather than when all screens in the phase are approved.

**How to avoid:** The approve-screen endpoint only sets `app_screens.approved = true`. Stage advancement is a separate user-initiated action via the existing `PATCH /{project_id}/stage` endpoint. The `ApprovalCheckpointCard` has two distinct actions: "Approve this screen" (per-screen) and "Continue to next phase" (stage advance, only shown when all current phase screens are approved).

---

## Code Examples

### Verified Tool Schemas (from live `npx @_davideast/stitch-mcp tool <name> -s`)

**edit_screens:**
```json
{
  "name": "edit_screens",
  "description": "Edits existing screens within a project using a text prompt.",
  "virtual": false,
  "arguments": {
    "deviceType": "string (optional)",
    "modelId": "string (optional)",
    "projectId": "string (required) - without 'projects/' prefix",
    "prompt": "string (required)",
    "selectedScreenIds": "array (required) - without 'screens/' prefix"
  }
}
```

**generate_variants** (alternative for comparison variants, if needed):
```json
{
  "name": "generate_variants",
  "description": "Generates variants of existing screens within a project using a text prompt.",
  "arguments": {
    "projectId": "string (required)",
    "prompt": "string (required)",
    "selectedScreenIds": "array (required)",
    "variantOptions": "undefined (required) - includes count, creative range, aspects",
    "deviceType": "string (optional)",
    "modelId": "string (optional)"
  }
}
```

**get_screen** (for fetching download URLs after edit):
```json
{
  "name": "get_screen",
  "arguments": {
    "name": "string (required) - Format: projects/{project}/screens/{screen}",
    "projectId": "string (required)",
    "screenId": "string (required)"
  }
}
```

### SSE Frontend Consumer Pattern (established in Phase 18/19)
```typescript
// Source: frontend/src/services/app-builder.ts generateScreen() — identical pattern for iterate
export async function iterateScreen(
  projectId: string,
  screenId: string,
  changeDescription: string,
  onEvent: (event: IterationEvent) => void,
): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/app-builder/projects/${projectId}/screens/${screenId}/iterate`,
    {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ change_description: changeDescription }),
    },
  );
  if (!res.ok || !res.body) throw new Error('Iteration failed to start');
  // ReadableStream SSE parsing — identical to generateScreen()
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
        try { onEvent(JSON.parse(line.slice(6))); } catch { /* skip */ }
      }
    }
  }
}
```

### Building Page Extension Pattern

```tsx
// Source: frontend/src/app/app-builder/[projectId]/building/page.tsx pattern
// New state additions to existing BuildingPage
const [isIterating, setIsIterating] = useState(false);
const [versionHistory, setVersionHistory] = useState<ScreenVariant[]>([]);
const [isApproved, setIsApproved] = useState(false);

const handleIterate = useCallback(async (changeDescription: string) => {
  if (!activeScreenId || isIterating) return;
  setIsIterating(true);
  const onEvent = (event: IterationEvent) => {
    if (event.step === 'edit_complete') {
      const newVariant: ScreenVariant = {
        id: event.variant_id ?? `iter-${Date.now()}`,
        screen_id: activeScreenId,
        variant_index: 0,
        screenshot_url: event.screenshot_url ?? null,
        html_url: event.html_url ?? null,
        is_selected: true,
        prompt_used: null,
        created_at: new Date().toISOString(),
        iteration: event.iteration,
      };
      setVariants(prev => [newVariant, ...prev]);
      setSelectedVariantId(newVariant.id);
    } else if (event.step === 'ready') {
      setIsIterating(false);
    }
  };
  try {
    await iterateScreen(projectId, activeScreenId, changeDescription, onEvent);
  } catch {
    setIsIterating(false);
  }
}, [projectId, activeScreenId, isIterating]);
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate screen creation per edit | `edit_screens` MCP tool preserving design continuity | Stitch MCP March 2026 | Edits maintain visual coherence with original |
| Manual version history table | `screen_variants.iteration` column | Phase 16 schema design | No new table needed; rollback = row selection |
| Polling for edit completion | SSE streaming (same as generation) | Phase 18 established | Consistent pattern; no polling timeout risk |
| DESIGN.md as separate file | `design_systems.raw_markdown` + `locked` boolean | Phase 18 | Persistence and locking built in |

**Deprecated/outdated:**
- Using `generate_screen_from_text` for edits (creates orphan screens — no continuity with original Stitch screen context)
- EventSource for SSE (cannot send Authorization header — established in Phase 18 that fetch ReadableStream is the correct pattern)

---

## Open Questions

1. **edit_screens response shape — does it include html_url directly?**
   - What we know: `generate_screen_from_text` returns `screenId`, `html_url`, `screenshot_url` (or camelCase equivalents) based on `stitch_assets.py` extraction patterns (`stitch_response.get("html_url") or stitch_response.get("htmlUrl")`)
   - What's unclear: Whether `edit_screens` returns the same shape or only `screenId` (requiring a follow-up `get_screen` call)
   - Recommendation: Implement the fallback pattern described in Pitfall 4 — check for html_url in edit response, call `get_screen` if absent. This handles both cases safely.

2. **Multiple selectedScreenIds — should we ever edit multiple screens at once?**
   - What we know: `edit_screens` accepts an array of screenIds; ITER-01 describes single-screen editing
   - What's unclear: Whether batch editing improves consistency for multi-page design coherence (Phase 21 use case)
   - Recommendation: For Phase 20, always pass a single-element array. Document the multi-screen capability for Phase 21.

3. **Approval granularity — per screen or per build phase?**
   - What we know: `app_screens.approved` exists per-screen; ITER-04 says "at each stage"; FLOW-05 says "each build phase"
   - What's unclear: Whether "approve" means approving a single screen or all screens in a build phase
   - Recommendation: Implement per-screen approval (sets `app_screens.approved = true`). "Continue to next phase" is a separate action shown only after all screens in the current phase are approved. This matches the Phase 7 confirmation card pattern.

---

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — this section is required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework (backend) | pytest 8.4.2 |
| Framework (frontend) | vitest |
| Backend config | `pyproject.toml` / `pytest.ini` |
| Frontend config | `vitest.config.*` |
| Backend quick run | `uv run pytest tests/unit/app_builder/test_iteration_service.py -x -v` |
| Backend full suite | `uv run pytest tests/unit/app_builder/ -x -v` |
| Frontend quick run | `cd frontend && npx vitest run src/__tests__/components/IterationPanel.test.tsx` |
| Frontend full suite | `cd frontend && npx vitest run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ITER-01 | edit_screen_variant yields editing + edit_complete + ready events with correct stitch_screen_id passed | unit | `uv run pytest tests/unit/app_builder/test_iteration_service.py::test_edit_yields_correct_events -x` | ❌ Wave 0 |
| ITER-01 | edit_screens called with selectedScreenIds array (not bare string) | unit | `uv run pytest tests/unit/app_builder/test_iteration_service.py::test_edit_screens_called_with_array -x` | ❌ Wave 0 |
| ITER-01 | POST /iterate endpoint streams SSE | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_iterate_screen_sse -x` | ❌ Wave 0 |
| ITER-02 | Locked design system markdown prepended to edit prompt | unit | `uv run pytest tests/unit/app_builder/test_iteration_service.py::test_design_system_injected_when_locked -x` | ❌ Wave 0 |
| ITER-02 | Unlocked design system not injected | unit | `uv run pytest tests/unit/app_builder/test_iteration_service.py::test_no_injection_when_unlocked -x` | ❌ Wave 0 |
| ITER-03 | edit inserts new screen_variants row with incremented iteration number | unit | `uv run pytest tests/unit/app_builder/test_iteration_service.py::test_iteration_number_incremented -x` | ❌ Wave 0 |
| ITER-03 | GET /history returns variants ordered by iteration DESC | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_screen_history_ordered -x` | ❌ Wave 0 |
| ITER-03 | POST /rollback selects old variant (deselects others) | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_rollback_selects_variant -x` | ❌ Wave 0 |
| ITER-04 | ApprovalCheckpointCard renders approve button; disabled during submission | unit | `cd frontend && npx vitest run src/__tests__/components/ApprovalCheckpointCard.test.tsx` | ❌ Wave 0 |
| ITER-04 | POST /approve sets app_screens.approved = true | unit | `uv run pytest tests/unit/app_builder/test_app_builder_router.py::test_approve_screen -x` | ❌ Wave 0 |
| FLOW-05 | IterationPanel renders textarea + submit; shows iteration progress | unit | `cd frontend && npx vitest run src/__tests__/components/IterationPanel.test.tsx` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/app_builder/test_iteration_service.py -x -v`
- **Per wave merge:** `uv run pytest tests/unit/app_builder/ -x -v && cd frontend && npx vitest run src/__tests__/components/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/app_builder/test_iteration_service.py` — covers ITER-01, ITER-02, ITER-03
- [ ] `tests/unit/app_builder/test_app_builder_router.py` — extend with iterate, approve, history, rollback tests
- [ ] `frontend/src/__tests__/components/IterationPanel.test.tsx` — covers FLOW-05
- [ ] `frontend/src/__tests__/components/ApprovalCheckpointCard.test.tsx` — covers ITER-04
- [ ] `frontend/src/__tests__/components/VersionHistoryPanel.test.tsx` — covers ITER-03 UI
- [ ] New service file `app/services/iteration_service.py` (no framework install needed)

---

## Sources

### Primary (HIGH confidence)
- Live CLI execution: `npx @_davideast/stitch-mcp tool edit_screens -s` — exact tool schema with all parameters
- Live CLI execution: `npx @_davideast/stitch-mcp tool generate_screen_from_text -s` — confirmed parameter parity
- Live CLI execution: `npx @_davideast/stitch-mcp tool get_screen -s` — confirmed fallback query pattern
- `app/services/screen_generation_service.py` — Phase 19 sequential Stitch call pattern (Lock constraint confirmed)
- `supabase/migrations/20260321400000_app_builder_schema.sql` — screen_variants.iteration column exists; app_screens.approved exists; design_systems.locked exists
- `app/routers/app_builder.py` — existing SSE pattern, _build_generation_prompt, approve_brief endpoint
- `frontend/src/services/app-builder.ts` — ReadableStream SSE consumer pattern

### Secondary (MEDIUM confidence)
- `davideast.github.io/stitch-mcp/tool-catalog/` — Tool catalog listing confirmed edit_screens and generate_variants existence
- `github.com/google-labs-code/stitch-sdk` README — screen.edit() SDK method confirms natural language prompt is the primary parameter
- `skills.sh/google-labs-code/stitch-skills/design-md` — DESIGN.md as natural language design system spec for prompt injection

### Tertiary (LOW confidence)
- WebSearch results on edit_screens parameter shape — corroborated by live CLI execution (HIGH confidence overrides)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project; Stitch tool schemas verified via live CLI
- Architecture: HIGH — patterns lifted directly from Phase 18/19 production code; schema columns pre-exist
- edit_screens response shape: MEDIUM — parameters verified, response shape inferred from generate_screen_from_text analogy + fallback pattern documented
- Pitfalls: HIGH — stitch_screen_id vs UUID confusion and iteration count server-side are direct architectural risks visible in current code

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (Stitch MCP API is actively developed; re-verify tool schemas if more than 30 days pass)
