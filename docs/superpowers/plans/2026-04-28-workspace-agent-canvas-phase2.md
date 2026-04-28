# Workspace Agent Canvas — Phase 2: Agent ↔ Workspace Contract

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Phase 2a is independent of 2b–2e and can be merged first; do not skip the open decisions in §3 before execution.
>
> **Predecessor:** `docs/superpowers/plans/2026-04-28-workspace-agent-canvas.md` (Phase 1 — shipped 2026-04-28). Read §5 of that doc for the original sketch this plan promotes.
>
> **Status:** DRAFT FOR REVIEW (2026-04-28).

---

## 1. Goal

Replace today's *implicit* agent↔workspace contract — where the SSE parser heuristically detects widgets and dispatches CustomEvents — with an *explicit*, typed contract:

1. Agents emit **`workspace_command`** SSE events with a typed action payload (`set_layout`, `focus`, `highlight`, `request_approval`, `replace_active`, `pin`, `unpin`, `clear_canvas`).
2. The workspace UI emits **`workspace_event`** back-channel POSTs (item closed, edited, approved, rearranged) so agents observe what users did with their output.
3. Agents read both via a session-memory field **`active_workspace_items`** populated by the same pipeline, so resumed sessions know what's already on canvas.
4. A single ADK tool **`workspace.update(commands=[...])`** is the agent's surface for emitting commands. Initial rollout: ContentCreationAgent, MarketingAgent, ExecutiveAgent.

**Architecture shift:** keep today's `WidgetDisplayService` browser CustomEvent bus and Supabase `workspace_items` table — they work. Layer the new SSE event type and back-channel POST on top so legacy widget-emission paths keep working as a fallback during rollout.

**Why now:** Phase 1 unified the canvas surface but agents still can't request layouts (`compare`, `grid`), highlight specific items, request inline approval, or know what users did with prior outputs. The user's original ask included "improve agent manipulation/molding of the workspace area" — this is that.

**Tech stack:** Python 3.10+ (FastAPI, Google ADK, Pydantic), TypeScript/React 19 (Next.js), Supabase (PostgreSQL with JSONB + RLS), pytest with pytest-asyncio, Vitest with jsdom, uv (package manager), ruff (lint), ty (type checking).

---

## 2. Architecture Summary

### 2.1 SSE event flow (forward channel)

```
ADK tool: workspace.update(commands=[...])
  ↓ returns {"_workspace_command": True, "commands": [...]}
ADK Runner emits FunctionResponse part
  ↓
fast_api_app.py:1880 SSE post-processor pipeline:
  - _extract_widget_from_event (existing)
  - _extract_traces_from_event (existing)
  - _extract_workspace_command_from_event (NEW)  ← injects top-level `workspace_command` field
  ↓
SSE event: {"author": "...", "content": {...}, "workspace_command": {"action": "set_layout", "payload": {...}}}
  ↓
frontend/src/lib/sseParser.ts: ParsedSideEffect.type adds 'workspace_command'
  ↓
frontend/src/hooks/useBackgroundStream.ts: dispatchWorkspaceCommand(detail) (NEW)
  ↓
frontend/src/services/widgetDisplay.ts: WORKSPACE_COMMAND_EVENT (NEW)
  ↓
ActiveWorkspace listens, applies command via setLayoutMode / setActiveItemId / etc.
```

### 2.2 Back-channel flow (reverse channel)

```
User closes/edits/approves workspace item in ActiveWorkspace
  ↓
frontend/src/services/workspaceEvents.ts: postWorkspaceEvent({sessionId, event, payload}) (NEW)
  ↓
POST /a2a/sessions/{session_id}/workspace_events
  ↓
app/routers/a2a_workspace.py:create_workspace_event (NEW)
  ↓
INSERT INTO workspace_events (NEW table)
  +
session_service.update_state() — append to active_workspace_items[i].history
  ↓
Next agent turn: context_memory_before_model_callback reads active_workspace_items
  +
Optional: agent calls read_workspace_events(since_ts) tool to query new events
```

### 2.3 Session memory

New session-state key: `active_workspace_items` (parallel to `user_context`, `user_agent_personalization`). Populated by:

- `_extract_workspace_command_from_event` — when `replace_active` or `focus` references a known item, ensures it's in the list
- `workspace_items` table — initial load on session resume reads recent rows (last 20)
- Back-channel POST handler — appends to `history` field on the relevant entry

Pre-turn callback `context_memory_before_model_callback` is extended to inject a compact `active_workspace_items` summary (id, type, title, last user action) into the model context.

### 2.4 Sub-phases

| Sub-phase | Scope | Risk | Can ship alone |
|-----------|-------|------|----------------|
| 2a | SSE forward channel: event type, parser, dispatch, ActiveWorkspace handlers | Low | ✓ |
| 2b | Back-channel POST + `workspace_events` table + RLS | Med (new endpoint, auth) | ✓ (after 2a) |
| 2c | ADK `workspace.update` tool + ContentCreationAgent rollout | Med (touches agent prompt) | After 2a |
| 2d | Session memory `active_workspace_items` + pre-turn injection | Med (model context size) | After 2b |
| 2e | Rollout: MarketingAgent, ExecutiveAgent | Low (mechanical) | After 2c |

---

## 3. Open Decisions (please answer before we execute)

1. **Command dialect — do we need `clear_canvas`?** A pure agent-driven `clear_canvas` could surprise users (deletes their work-in-progress view). Frontend `Clear workspace` already exists as a user-driven action.
   *Recommendation:* Drop `clear_canvas` from agent surface for v1. Agents can still `replace_active` to swap.

2. **Approval-request UX placement** — `request_approval` could render either as (a) a banner above the active widget, (b) a modal, or (c) inline footer. Aligns with the existing `approvals` router pattern in `app/routers/approvals.py`.
   *Recommendation:* Inline footer card under the active widget, with `Approve` / `Reject` / `Request changes` buttons. Reuse existing approvals API for persistence so this is just a *render hint*, not a new persistence path.

3. **`active_workspace_items` size cap** — long sessions could push >50 items. Pre-turn injection budget matters because every turn pays the token cost.
   *Recommendation:* Cap at 20 most-recent items; surface a `more_items_in_history: true` flag and an optional `read_workspace_events(since_ts)` tool the agent can call when it needs older context.

4. **Legacy widget paths during rollout** — keep `dispatchWorkspaceWidget` heuristic parsing alongside `workspace_command` events?
   *Recommendation:* Yes, for one milestone. Mark deprecated. After all four high-traffic agents (Content, Marketing, Executive, Director) emit explicit commands, remove the heuristic from `useBackgroundStream.ts`.

5. **Back-channel events the agent reads — pull or push?**
   - Pull: agent calls `read_workspace_events(session_id, since_ts?)` tool when it wants to know.
   - Push: pre-turn callback injects new events into context every turn.
   *Recommendation:* **Push** for the first turn after a new event arrives (so the agent sees "user just closed the chart") — but cap history; **Pull** for older context if the agent explicitly asks.

6. **Phase 2 sequencing** — ship 2a alone first, then 2b+2c together, or all five at once?
   *Recommendation:* Ship 2a alone first (no agent changes, frontend-only). Validate the event channel works in production. Then 2b+2c+2d together (back-channel + first agent). 2e last.

---

## 4. File Plan

### Phase 2a — SSE forward channel

**Create:**
- `frontend/src/services/workspaceCommands.ts` — `WorkspaceCommand` type + `dispatchWorkspaceCommand()`
- `app/sse_workspace_commands.py` — `_extract_workspace_command_from_event()` post-processor

**Modify:**
- `app/sse_utils.py` — export the new extractor next to the existing widget/traces extractors
- `app/fast_api_app.py:1880` — add the new post-processor to the pipeline
- `frontend/src/lib/sseParser.ts` — add `'workspace_command'` to `ParsedSideEffect.type` union; emit on detection
- `frontend/src/hooks/useBackgroundStream.ts` — handle `workspace_command` side effect, call `dispatchWorkspaceCommand()`
- `frontend/src/components/dashboard/ActiveWorkspace.tsx` — listen for `WORKSPACE_COMMAND_EVENT`; apply `set_layout`, `focus`, `replace_active`, `pin`, `unpin`, `highlight`, `request_approval`

**Test:**
- `app/tests/unit/test_sse_workspace_commands.py` — extractor unit tests
- `frontend/src/services/__tests__/workspaceCommands.test.ts` — dispatch + event shape tests
- `frontend/src/components/dashboard/ActiveWorkspace.test.tsx` — extend with command handling cases

### Phase 2b — Back-channel POST + table

**Create:**
- `supabase/migrations/20260501120000_workspace_events.sql` — `workspace_events` table + RLS + indexes
- `app/routers/a2a_workspace.py` — `POST /a2a/sessions/{session_id}/workspace_events` endpoint
- `app/services/workspace_event_service.py` — append/query helpers (mirrors `content_bundle_service.py`)
- `frontend/src/services/workspaceEvents.ts` — typed POST helper

**Modify:**
- `app/fast_api_app.py` — register the new router under the existing A2A mount
- `frontend/src/components/dashboard/ActiveWorkspace.tsx` — call `postWorkspaceEvent()` on item close/edit/approve

**Test:**
- `app/tests/unit/test_workspace_event_service.py`
- `app/tests/integration/test_workspace_events_api.py`
- `frontend/src/services/__tests__/workspaceEvents.test.ts`

### Phase 2c — ADK tool + first agent

**Create:**
- `app/agents/tools/workspace.py` — `workspace_update` tool registered via `@agent_tool` decorator
- `app/agents/tools/workspace.py` — `read_workspace_events` tool (pull-side companion)

**Modify:**
- `app/agents/content/agent.py` — import and register the new tools; update the agent's instruction with a short snippet on when to call `workspace_update`
- `app/agents/shared_instructions.py` — add a reusable `WORKSPACE_UPDATE_INSTRUCTION` block

**Test:**
- `app/tests/unit/test_workspace_tool.py` — tool returns the marker dict; SSE extractor picks it up
- `app/tests/integration/test_content_agent_workspace_command.py` — end-to-end: ContentCreationAgent emits `set_layout` for a multi-asset response; SSE event reaches frontend

### Phase 2d — Session memory

**Modify:**
- `app/agents/context_extractor.py` — add `ACTIVE_WORKSPACE_ITEMS_STATE_KEY = "active_workspace_items"`; extend `context_memory_before_model_callback` to inject summary
- `app/persistence/supabase_session_service.py` — confirm `update_state` supports nested key paths or document workaround
- `app/services/workspace_event_service.py` — write to session state on event create

**Test:**
- `app/tests/unit/test_active_workspace_items_state.py` — load, append, cap-at-20 logic
- `app/tests/integration/test_pre_turn_injection.py` — agent context contains `active_workspace_items`

### Phase 2e — Agent rollout

**Modify:**
- `app/agents/marketing/agent.py` — add tools, update instruction
- `app/agents/admin/agent.py` (ExecutiveAgent equivalent) — add tools, update instruction
- `app/agents/content/director.py` — if it produces multi-asset outputs, add tools

**Test:**
- `app/tests/integration/test_marketing_agent_workspace_command.py`
- `app/tests/integration/test_executive_agent_workspace_command.py`

---

## 5. Detailed Tasks (execute-ready)

### Task 2a-1 — Define `WorkspaceCommand` types (frontend)

**Files:**
- Create: `frontend/src/services/workspaceCommands.ts`
- Test: `frontend/src/services/__tests__/workspaceCommands.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/services/__tests__/workspaceCommands.test.ts
// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest';
import { dispatchWorkspaceCommand, WORKSPACE_COMMAND_EVENT } from '../workspaceCommands';

describe('dispatchWorkspaceCommand', () => {
  it('emits a WORKSPACE_COMMAND_EVENT with the typed payload', () => {
    const handler = vi.fn();
    window.addEventListener(WORKSPACE_COMMAND_EVENT, handler);
    dispatchWorkspaceCommand({
      userId: 'user-1',
      sessionId: 'session-1',
      command: { action: 'set_layout', payload: { mode: 'compare' } },
    });
    expect(handler).toHaveBeenCalledTimes(1);
    const detail = handler.mock.calls[0][0].detail;
    expect(detail.command.action).toBe('set_layout');
    window.removeEventListener(WORKSPACE_COMMAND_EVENT, handler);
  });
});
```

- [ ] **Step 2: Implement the module**

```ts
// frontend/src/services/workspaceCommands.ts
import { WidgetDefinition, WidgetWorkspaceMode } from '@/types/widgets';

export const WORKSPACE_COMMAND_EVENT = 'workspace-command';

export type WorkspaceCommand =
  | { action: 'set_layout'; payload: { mode: WidgetWorkspaceMode; itemIds?: string[] } }
  | { action: 'focus'; payload: { itemId: string } }
  | { action: 'highlight'; payload: { itemId: string; region?: string | { x: number; y: number; w: number; h: number } } }
  | { action: 'request_approval'; payload: { deliverableId: string; prompt: string } }
  | { action: 'replace_active'; payload: { widget: WidgetDefinition } }
  | { action: 'pin'; payload: { itemId: string } }
  | { action: 'unpin'; payload: { itemId: string } };

export interface WorkspaceCommandEventDetail {
  userId: string;
  sessionId?: string;
  command: WorkspaceCommand;
}

export function dispatchWorkspaceCommand(detail: WorkspaceCommandEventDetail): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(WORKSPACE_COMMAND_EVENT, { detail }));
}
```

- [ ] **Step 3: Run the test, confirm green.**
- [ ] **Step 4: Run lint + typecheck on this file. Commit.**

### Task 2a-2 — Add `workspace_command` to SSE parser

**Files:**
- Modify: `frontend/src/lib/sseParser.ts`
- Test: `frontend/src/lib/sseParser.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
it('parses a workspace_command field as a side effect', () => {
  const result = parseSseEvent({
    author: 'content_creator',
    workspace_command: { action: 'set_layout', payload: { mode: 'compare' } },
  });
  expect(result.sideEffects).toContainEqual({
    type: 'workspace_command',
    payload: { action: 'set_layout', payload: { mode: 'compare' } },
  });
});
```

- [ ] **Step 2: Implement**

In `sseParser.ts`, extend the `ParsedSideEffect.type` union with `'workspace_command'`. After the existing extraction logic, scan the event for a top-level `workspace_command` field and push it into `sideEffects`.

- [ ] **Step 3: Confirm green. Commit.**

### Task 2a-3 — Wire dispatch in `useBackgroundStream`

**Files:**
- Modify: `frontend/src/hooks/useBackgroundStream.ts`

- [ ] In the visible-session side-effect handling block (around line 432), add a branch for `effect.type === 'workspace_command'`. Call `dispatchWorkspaceCommand({ userId, sessionId, command: effect.payload })`.
- [ ] In the background-session block (around line 489), enqueue the command in `pendingActions` (extend the `PendingSessionAction` type union with `'workspace_command'`).
- [ ] Add a flush step: when a backgrounded session becomes visible, replay queued `workspace_command` actions in order.
- [ ] Run dev server and verify no runtime errors.

### Task 2a-4 — Apply commands in `ActiveWorkspace`

**Files:**
- Modify: `frontend/src/components/dashboard/ActiveWorkspace.tsx`
- Test: `frontend/src/components/dashboard/ActiveWorkspace.test.tsx`

- [ ] **Step 1: Write tests** for each command type — `set_layout`, `focus`, `replace_active`, `pin`, `unpin`. `highlight` and `request_approval` get tests once the visual treatment is decided (Q2).
- [ ] **Step 2: Add a `WORKSPACE_COMMAND_EVENT` listener** that dispatches into the existing state setters (`setLayoutMode`, `setActiveItemId`, `setWorkspaceItems`).
- [ ] **Step 3: For `replace_active`** — append the new widget to `workspaceItems` and set it active.
- [ ] **Step 4: For `highlight`** — set a transient `highlightedItemId` state (auto-clears after 4 s).
- [ ] **Step 5: For `request_approval`** — render the `<ApprovalCheckpointCard />` (already exists in `frontend/src/__tests__/components/ApprovalCheckpointCard.test.tsx`) below the active widget.
- [ ] **Step 6: Run dashboard test suite. All pass.**

### Task 2a-5 — SSE post-processor (backend)

**Files:**
- Create: `app/sse_workspace_commands.py`
- Modify: `app/sse_utils.py`, `app/fast_api_app.py`
- Test: `app/tests/unit/test_sse_workspace_commands.py`

- [ ] **Step 1: Write the failing test**

```python
# app/tests/unit/test_sse_workspace_commands.py
from app.sse_workspace_commands import extract_workspace_command_from_event

def test_extracts_workspace_command_from_function_response():
    event = {
        "content": {
            "parts": [
                {
                    "function_response": {
                        "response": {
                            "_workspace_command": True,
                            "commands": [
                                {"action": "set_layout", "payload": {"mode": "compare"}},
                            ],
                        }
                    }
                }
            ]
        }
    }
    enriched = extract_workspace_command_from_event(event)
    assert enriched["workspace_command"] == {
        "action": "set_layout",
        "payload": {"mode": "compare"},
    }

def test_no_op_when_no_marker():
    event = {"content": {"parts": [{"text": "Hello"}]}}
    assert extract_workspace_command_from_event(event) == event
```

- [ ] **Step 2: Implement** following the same pattern as `_extract_widget_from_event` in `app/sse_utils.py`. Look for `function_response.response._workspace_command == True`, lift the first command (or list) into a top-level `workspace_command` field on the event dict.
- [ ] **Step 3: Wire into pipeline** — in `fast_api_app.py:1880`, add `data = extract_workspace_command_from_event(data)` after the existing extractors.
- [ ] **Step 4: Run unit tests + integration test that hits `/a2a/app/run_sse`** with a stubbed agent that emits the marker.

### Task 2b-1 — Migration: `workspace_events` table

**Files:**
- Create: `supabase/migrations/20260501120000_workspace_events.sql`
- Test: manual verification via `supabase db reset --local` + assertion query

- [ ] **Step 1: Write the migration**

```sql
-- supabase/migrations/20260501120000_workspace_events.sql
CREATE TABLE IF NOT EXISTS workspace_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    workspace_item_id UUID REFERENCES workspace_items(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'item_closed', 'item_edited', 'item_approved', 'item_rejected',
        'item_pinned', 'item_unpinned', 'layout_changed'
    )),
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workspace_events_session ON workspace_events (user_id, session_id, created_at DESC);
CREATE INDEX idx_workspace_events_item ON workspace_events (workspace_item_id) WHERE workspace_item_id IS NOT NULL;

ALTER TABLE workspace_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see their own workspace events"
    ON workspace_events FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users insert their own workspace events"
    ON workspace_events FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role full access on workspace_events"
    ON workspace_events FOR ALL
    USING (auth.role() = 'service_role');
```

- [ ] **Step 2: Apply locally**: `supabase db reset --local`
- [ ] **Step 3: Verify** via `psql` that the table exists with correct columns/indexes/RLS.
- [ ] **Step 4: Add seed coverage** if `supabase/seed.sql` references it (probably not).

### Task 2b-2 — Service layer

**Files:**
- Create: `app/services/workspace_event_service.py`
- Test: `app/tests/unit/test_workspace_event_service.py`

- [ ] **Step 1: Test-first**

```python
# Test: appending an event writes a row and updates session state
async def test_append_event_writes_row_and_updates_session(supabase, session_service):
    service = WorkspaceEventService(supabase, session_service)
    event_id = await service.append(
        user_id="user-1",
        session_id="sess-1",
        workspace_item_id="item-1",
        event_type="item_closed",
        payload={},
    )
    rows = await supabase.from_("workspace_events").select("*").eq("id", event_id).execute()
    assert len(rows.data) == 1
    state = await session_service.get_session("sess-1")
    assert any(item["id"] == "item-1" and item["history"][-1]["event_type"] == "item_closed"
               for item in state.state.get("active_workspace_items", []))
```

- [ ] **Step 2: Implement** following the `content_bundle_service.py` shape. Two methods: `append(...)` and `query(user_id, session_id, since_ts=None, limit=50)`.
- [ ] **Step 3: Confirm green. Lint + type check.**

### Task 2b-3 — POST endpoint

**Files:**
- Create: `app/routers/a2a_workspace.py`
- Modify: `app/fast_api_app.py` (register router)
- Test: `app/tests/integration/test_workspace_events_api.py`

- [ ] **Step 1: Test-first** — TestClient POST with auth, assert 201 + row exists + session state updated.
- [ ] **Step 2: Implement endpoint**

```python
# app/routers/a2a_workspace.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

router = APIRouter(prefix="/a2a/sessions", tags=["a2a-workspace"])

class WorkspaceEventRequest(BaseModel):
    workspace_item_id: str | None = None
    event_type: Literal[
        "item_closed", "item_edited", "item_approved", "item_rejected",
        "item_pinned", "item_unpinned", "layout_changed"
    ]
    payload: dict = Field(default_factory=dict)

class WorkspaceEventResponse(BaseModel):
    id: str
    created_at: str

@router.post("/{session_id}/workspace_events", response_model=WorkspaceEventResponse, status_code=201)
async def create_workspace_event(
    session_id: str,
    body: WorkspaceEventRequest,
    user_id: str = Depends(verify_token),
    service: WorkspaceEventService = Depends(get_workspace_event_service),
):
    return await service.append(
        user_id=user_id,
        session_id=session_id,
        workspace_item_id=body.workspace_item_id,
        event_type=body.event_type,
        payload=body.payload,
    )
```

- [ ] **Step 3: Register** in `fast_api_app.py` near the other routers.
- [ ] **Step 4: Frontend client** — `frontend/src/services/workspaceEvents.ts` with `postWorkspaceEvent()` typed wrapper using existing `fetchWithAuth`.
- [ ] **Step 5: Wire ActiveWorkspace** — the existing `handleClearWorkspace` and `handleSelectItem` already modify state; add `postWorkspaceEvent({event_type: 'item_closed', ...})` on close, etc.

### Task 2c-1 — `workspace.update` tool

**Files:**
- Create: `app/agents/tools/workspace.py`
- Test: `app/tests/unit/test_workspace_tool.py`

- [ ] **Step 1: Test-first** — assert tool returns `{"_workspace_command": True, "commands": [...]}`.
- [ ] **Step 2: Implement**

```python
# app/agents/tools/workspace.py
from typing import Any, Literal
from app.agents.tools.base import agent_tool

CommandAction = Literal[
    "set_layout", "focus", "highlight", "request_approval",
    "replace_active", "pin", "unpin",
]

@agent_tool
def workspace_update(commands: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply one or more workspace commands to the user's active canvas.

    Each command is a dict with keys: action (one of set_layout, focus, highlight,
    request_approval, replace_active, pin, unpin) and payload (action-specific).
    Use this when you want to control how prior outputs are presented — for
    example, set_layout=compare when you want the user to see two artifacts
    side-by-side, or request_approval before publishing a deliverable.
    """
    # Light validation; SSE extractor handles the rest.
    for cmd in commands:
        if "action" not in cmd:
            raise ValueError("Each command must have an 'action' field")
    return {"_workspace_command": True, "commands": commands}

@agent_tool
def read_workspace_events(
    session_id: str,
    since_ts: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Read recent user actions on workspace items (closed, edited, approved).

    Use when the user references something they did with a prior artifact and
    you don't have it in your immediate context. Returns the most recent events
    after `since_ts` (ISO timestamp), capped at `limit`.
    """
    # Implementation calls workspace_event_service.query()
    ...

WORKSPACE_TOOLS = [workspace_update, read_workspace_events]
```

- [ ] **Step 3: Register** in `app/agents/tools/__init__.py` exports.

### Task 2c-2 — ContentCreationAgent rollout

**Files:**
- Modify: `app/agents/content/agent.py`
- Modify: `app/agents/shared_instructions.py`
- Test: `app/tests/integration/test_content_agent_workspace_command.py`

- [ ] **Step 1: Add to `shared_instructions.py`**

```python
WORKSPACE_UPDATE_INSTRUCTION = """
## Shaping the Workspace Canvas

When you produce multiple artifacts that benefit from comparison (two campaign
variants, before/after analyses, draft+revision), call `workspace_update` with
`set_layout: compare` so the user sees them side-by-side.

When you want the user to act on a specific deliverable (approve a video,
review a draft), call `workspace_update` with `request_approval` and reference
the deliverable_id.

Never call `clear_canvas`. The user controls when to clear their workspace.
""".strip()
```

- [ ] **Step 2: Inject into ContentCreationAgent** — append `WORKSPACE_UPDATE_INSTRUCTION` to its instruction string. Add `WORKSPACE_TOOLS` to its tools list.
- [ ] **Step 3: Integration test** — fire a request that produces two image variants, assert the SSE stream contains a `workspace_command` event with `set_layout: compare`.
- [ ] **Step 4: Run agent eval** if one exists — `make test` or specific eval script.

### Task 2d-1 — `active_workspace_items` session state

**Files:**
- Modify: `app/agents/context_extractor.py`
- Modify: `app/services/workspace_event_service.py`
- Test: `app/tests/unit/test_active_workspace_items_state.py`

- [ ] **Step 1: Define key + read/write helpers** in `context_extractor.py`:

```python
ACTIVE_WORKSPACE_ITEMS_STATE_KEY = "active_workspace_items"
MAX_ACTIVE_WORKSPACE_ITEMS = 20

def append_workspace_item(state: dict, item: dict) -> None:
    items = state.setdefault(ACTIVE_WORKSPACE_ITEMS_STATE_KEY, [])
    items.append(item)
    if len(items) > MAX_ACTIVE_WORKSPACE_ITEMS:
        del items[: len(items) - MAX_ACTIVE_WORKSPACE_ITEMS]

def append_workspace_event(state: dict, item_id: str, event: dict) -> None:
    items = state.get(ACTIVE_WORKSPACE_ITEMS_STATE_KEY, [])
    for entry in items:
        if entry["id"] == item_id:
            entry.setdefault("history", []).append(event)
            return
```

- [ ] **Step 2: Extend `context_memory_before_model_callback`** — inject a compact summary string of `active_workspace_items` into the model context (id, type, title, last 3 events).
- [ ] **Step 3: Update `WorkspaceEventService.append`** — also call `append_workspace_event` on the session state.
- [ ] **Step 4: Tests** — load state, simulate events, assert cap-at-20, assert history append, assert pre-turn injection contains the summary.

### Task 2e — Rollout (mechanical)

- [ ] **MarketingAgent** — same as 2c-2 but for `app/agents/marketing/agent.py`. Integration test for a multi-channel campaign rollup → `set_layout: grid`.
- [ ] **ExecutiveAgent / Admin** — for delegation handoffs, prefer `replace_active` so the user sees the sub-agent's output appear in place rather than as a new card.
- [ ] **Director / Video** — for storyboard reviews, `request_approval` per scene.

---

## 6. Risks & Tradeoffs

- **Token cost on session memory injection.** Pre-turn injection of `active_workspace_items` adds ~50–200 tokens per turn for active sessions. Mitigation: cap at 20 items, summarize to id+title+last_event only (drop full payloads).
- **Backwards compatibility during rollout.** Legacy heuristic widget extraction stays for one milestone. After 2e completes, gate removal behind a feature flag (e.g., `WORKSPACE_LEGACY_PARSER_ENABLED=false` in production for one week before deletion).
- **`replace_active` bug surface.** If the agent emits `replace_active` with a widget that has the same id as an existing item, naive append-and-set-active would duplicate. Mitigation: `mergeWorkspaceItems` already de-dupes by id (Phase 1 code).
- **Approval card double-persistence.** `request_approval` is a render hint; the actual approval still goes through the existing `app/routers/approvals.py` path. Two channels means two consistency points. Mitigation: render the card from the canonical approvals API state, not from the SSE event payload — the SSE event just tells the UI "show the card now."
- **`read_workspace_events` tool unbounded reads.** A misbehaving agent could call it in a tight loop. Mitigation: rate-limit per session id (5 calls per 60s window).
- **A2A protocol drift.** Adding `POST /a2a/sessions/{id}/workspace_events` extends the A2A surface. If the project later adopts a strict upstream A2A spec, this endpoint might need to move under a `/pikar/v1/...` prefix. Mitigation: name the route consistently with existing local A2A endpoints and document in `docs/superpowers/`.
- **Pre-existing lint debt** — none touched by Phase 2. The `react-hooks/set-state-in-effect` errors fixed in the Phase 1 cleanup PR are unrelated.

---

## 7. Verification

### Phase 2a only (frontend + SSE plumbing, no agent changes)

- [ ] Backend unit tests pass: `make test` (or `uv run pytest app/tests/unit/test_sse_workspace_commands.py`).
- [ ] Frontend tests pass: `cd frontend && npm test`.
- [ ] Manual: in dev, `console.log` inside `dispatchWorkspaceCommand` and have an agent emit a marker via a temporary tool — verify the event reaches `ActiveWorkspace`.

### Full Phase 2 (all five sub-phases)

- [ ] All unit + integration tests pass.
- [ ] In dev, prompt ContentCreationAgent: "Generate two campaign variants for our product launch and show them side by side." Verify the workspace flips to `compare` layout automatically.
- [ ] Close the active workspace item. Verify a row appears in `workspace_events`. Verify the next agent turn's context contains a reference to the closed item.
- [ ] Resume an old session with prior artifacts. Verify `active_workspace_items` is hydrated from `workspace_items` table and the agent acknowledges them in its response.
- [ ] No regressions in Phase 1 dashboard test suite (12 + 1 = 13 tests still pass).
- [ ] `make lint` clean. `cd frontend && npm run lint` clean (no new errors beyond the pre-existing warnings on `_user`/`title`/`description` props).

---

## 8. Out of Scope (this plan)

- Changes to the agent decision-making for *when* to call `workspace_update` — this plan only adds the surface; agent behaviour tuning is a follow-up.
- Per-user preferences for default layout mode (e.g., "always show compare for me").
- Mobile-specific workspace command rendering (highlight regions, approval cards) — desktop-first; mobile follows once UX is decided.
- Revenue/usage analytics on command emission rates.
- Migrating other browser CustomEvents (`WIDGET_CHANGE_EVENT`, `WIDGET_FOCUS_EVENT`) to the new contract — they keep working as the in-process bus.
- A formal A2A spec compliance audit. The new endpoint is a project-local extension; conformance with upstream A2A is deferred.

---

## 9. Open follow-ups (post Phase 2)

- **Workspace command analytics** — emit telemetry events on each `workspace_command` so we can see which agents/commands actually get used. Feeds into the Executive Enhancement telemetry work tracked in `project_executive_enhancement.md`.
- **Heuristic parser deprecation** — once 2e is a milestone old, delete the `dispatchWorkspaceWidget` heuristic in `useBackgroundStream.ts` and the related branches in `sseParser.ts`.
- **Tool: `workspace_state(session_id)`** — give agents a read-only view of the current canvas (for debugging mid-conversation).
- **Tool: `workspace_diff(session_id, since_ts)`** — agents that resume long-paused sessions can request a diff rather than the full state.
