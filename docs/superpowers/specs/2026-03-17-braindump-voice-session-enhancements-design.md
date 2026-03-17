# Brain Dump Voice Session Enhancements — Design Spec

**Date:** 2026-03-17
**Status:** Approved
**Approach:** B — Full Integration (Timer + Workspace Widget + Session Tracking)

## Overview

Enhance the brain dump voice session feature so users can have a structured 15-minute voice conversation with their executive assistant agent, receive a comprehensive markdown analysis in the workspace, and continue collaborating with suggested next steps.

### Goals

1. Enforce a 15-minute maximum session duration with server-side authority
2. Produce a single comprehensive markdown document combining analysis + validation plan
3. Show a compact summary card in chat with a "View Full Analysis" button
4. Render the full analysis in the agent workspace (right panel) in focus mode
5. Track session lifecycle in a new `braindump_sessions` table

### Non-Goals

- Session resume after WebSocket disconnect (future enhancement)
- Periodic transcript checkpointing (future enhancement)
- Interactive next-steps checklist with assign/schedule (future enhancement)
- Multi-language voice selection in the UI (future enhancement)

---

## 1. Server-Side Timer Enforcement

### File: `app/routers/voice_session.py`

### Constants

```python
SESSION_MAX_SECONDS = int(os.getenv("BRAINDUMP_SESSION_MAX_SECONDS", "900"))       # 15 min
SESSION_WRAPUP_SECONDS = int(os.getenv("BRAINDUMP_SESSION_WRAPUP_SECONDS", "720")) # 12 min
SESSION_FINAL_WARNING_SECONDS = int(os.getenv("BRAINDUMP_SESSION_FINAL_WARNING_SECONDS", "840"))  # 14 min
```

### New concurrent task: `session_timer()`

Added as a third task in the `asyncio.gather` alongside `forward_audio_to_gemini()` and `forward_audio_from_gemini()`.

Behavior:

- **At `SESSION_WRAPUP_SECONDS` (12:00):** Injects a system prompt into the Gemini Live session telling the agent to start wrapping up naturally. Sends `{ "type": "time_warning", "remaining_seconds": 180 }` to the client.
- **At `SESSION_FINAL_WARNING_SECONDS` (14:00):** Sends `{ "type": "time_warning", "remaining_seconds": 60 }` to the client for the countdown banner.
- **At `SESSION_MAX_SECONDS` (15:00):** Sends `{ "type": "session_timeout" }` to the client. Sets `stop_event` which causes both streaming tasks to exit cleanly.

The timer task is pure `asyncio.sleep` + event checks. No performance impact. The server is the authoritative time source — if the client crashes, the server still closes the session.

### New WebSocket message types (server → client)

```json
{ "type": "time_warning", "remaining_seconds": 180 }
{ "type": "time_warning", "remaining_seconds": 60 }
{ "type": "session_timeout" }
```

---

## 2. Database — `braindump_sessions` Table

### New migration file: `supabase/migrations/XXXX_braindump_sessions.sql`

```sql
CREATE TABLE braindump_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    session_type TEXT DEFAULT 'voice' CHECK (session_type IN ('voice')),  -- future: 'recording', 'text'
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'timed_out', 'abandoned')),
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    turn_count INTEGER DEFAULT 0,
    transcript_doc_id UUID REFERENCES vault_documents(id) ON DELETE SET NULL,
    analysis_doc_id UUID REFERENCES vault_documents(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_braindump_sessions_user_id ON braindump_sessions(user_id);
CREATE INDEX idx_braindump_sessions_status ON braindump_sessions(status);

ALTER TABLE braindump_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY braindump_sessions_user_policy ON braindump_sessions
    FOR ALL USING (auth.uid() = user_id);

-- Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION update_braindump_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER braindump_sessions_updated_at
    BEFORE UPDATE ON braindump_sessions
    FOR EACH ROW EXECUTE FUNCTION update_braindump_sessions_updated_at();
```

### Lifecycle

| Event | Status | Action |
|---|---|---|
| WebSocket auth succeeds | `active` | INSERT row with `user_id`, `session_type='voice'` |
| Finalization completes | `completed` | UPDATE with artifact doc IDs, `duration_seconds`, `turn_count`, `ended_at` |
| Timeout triggers finalization | `timed_out` | Same as completed but status = `timed_out` |
| WebSocket disconnects without finalize | `abandoned` | UPDATE with `ended_at`, status = `abandoned` |

### Integration points

- `voice_session()` WebSocket handler: create/update session row
- `finalize_brainstorm_session()` endpoint: update session with artifact IDs
- Future: dashboard analytics, session history page

---

## 3. Comprehensive Single-Document Output

### File: `app/routers/voice_session.py` + `app/agents/tools/brain_dump.py`

### Changes to `process_brainstorm_conversation()`

The Gemini prompt is enhanced to produce a single comprehensive document instead of separate Brain Dump + Validation Plan artifacts. The output format:

```markdown
# Brain Dump Analysis: [Extracted Title]

| Detail | Value |
| --- | --- |
| **Session** | `{session_id}` |
| **Date** | [timestamp] |
| **Duration** | [Xm Ys] |
| **Topics** | [N] themes identified |

---

## Executive Summary
[2-3 paragraph synthesis]

## Key Ideas Discussed
### 1. [Idea Title]
[Description with context]
...

## Decision Points
| Decision | Pro | Con | Recommendation |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

## Action Items
- [ ] [Item] — *Priority: High*
- [ ] [Item] — *Priority: Medium*
...

## Resource Requirements
[If discussed]

## Risk Factors
[If discussed]

## Suggested Next Steps
1. [Step with rationale]
2. [Step with rationale]
...

## Raw Transcript
<details>
<summary>View full conversation transcript (X turns)</summary>
[Full transcript]
</details>
```

### Changes to response models

```python
class BrainstormSummary(BaseModel):
    title: str
    key_themes: list[str] = Field(default_factory=list)
    action_item_count: int = 0
    executive_summary: str = ""

class BrainstormFinalizeResponse(BaseModel):
    success: bool
    validation_plan: str | None = None          # DEPRECATED — always None, kept for existing callers
    transcript_markdown: str | None = None
    transcript_file_path: str | None = None
    saved_categories: list[str] = Field(default_factory=list)
    error: str | None = None
    summary: BrainstormSummary | None = None     # NEW — powers chat summary card
    analysis_doc_id: str | None = None           # NEW — vault_documents ID
    analysis_markdown: str | None = None         # NEW — full markdown for workspace widget
```

### Backward compatibility

- `validation_plan` field is **always `None`** going forward. The "Suggested Next Steps" section of the comprehensive analysis document replaces it. Any frontend code reading `validation_plan` must be updated to use `analysis_markdown` instead.
- The existing `saved_categories.extend(["Brain Dump", "Validation Plan"])` line is replaced with `saved_categories.append("Brain Dump Analysis")`.

### Initiative creation integration

The `analysisDocId` returned by finalization is a `vault_documents.id` with `category='Brain Dump Analysis'`. The existing `createInitiativeFromBraindump()` function sends `{ braindump_id }` to `POST /initiatives/from-braindump`, which looks up the vault document by ID. Since the new analysis document is saved to `vault_documents` with category `'Brain Dump Analysis'`, it is a valid `braindump_id` — no backend changes needed to the initiatives endpoint.

### Artifact output

Finalization now produces **2 artifacts** (down from 3):

1. **Brain Dump Transcript** — Raw conversation (unchanged)
2. **Brain Dump Analysis** — Comprehensive merged document (replaces separate Brain Dump + Validation Plan)

The `saved_categories` field reflects the actual categories saved.

---

## 4. New `braindump_analysis` Widget

### Frontend types — `frontend/src/types/widgets.ts`

Add to `WidgetType` union:

```typescript
export type WidgetType =
    | /* ...existing... */
    | 'braindump_analysis';
```

Add data interface:

```typescript
export interface BraindumpAnalysisData {
    markdown: string;
    documentId: string;
    sessionId?: string;
    title: string;
    keyThemes: string[];
    actionItemCount: number;
}
```

Add to `WidgetData` union:

```typescript
| { type: 'braindump_analysis'; data: BraindumpAnalysisData }
```

Add type guard:

```typescript
export function isBraindumpAnalysisData(data: unknown): data is BraindumpAnalysisData {
    if (!data || typeof data !== 'object') return false;
    const d = data as Record<string, unknown>;
    return typeof d.markdown === 'string' && typeof d.documentId === 'string';
}
```

Update `isValidWidgetType` and `validateWidgetDefinition` to include the new type.

### Widget component — `frontend/src/components/widgets/BraindumpAnalysisWidget.tsx`

New component that:

- Renders full markdown using `ReactMarkdown` + `remarkGfm` (same renderer as `BrainDumpInterface`)
- Has a header with title, session metadata, category badge
- Includes "Create Initiative" button (reuses `createInitiativeFromBraindump()`)
- Includes "Download" button
- Supports `fullFocus` mode for workspace rendering
- Styled consistently with existing workspace panels (rounded-[28px], slate borders, teal accents)

### Widget registry — `frontend/src/components/widgets/WidgetRegistry.tsx`

```typescript
const BraindumpAnalysisWidget = dynamic(() => import('./BraindumpAnalysisWidget'), {
    loading: WidgetSkeleton,
    ssr: false
});

// In WIDGET_MAP:
braindump_analysis: BraindumpAnalysisWidget,
```

### Workspace hydration — `frontend/src/components/dashboard/ActiveWorkspace.tsx`

Add `braindump_analysis` case to `workspaceRowToWidget()`:

```typescript
if (row.widget_type === 'braindump_analysis') {
    return {
        type: 'braindump_analysis',
        title: row.title || 'Brain Dump Analysis',
        data: {
            markdown: stringValue(payload.markdown) || '',
            documentId: stringValue(payload.document_id) || '',
            sessionId: row.session_id || stringValue(payload.session_id),
            title: row.title || 'Brain Dump Analysis',
            keyThemes: Array.isArray(payload.key_themes) ? payload.key_themes : [],
            actionItemCount: typeof payload.action_item_count === 'number' ? payload.action_item_count : 0,
        },
        workspace,
    };
}
```

---

## 5. Chat Summary Card

### File: `frontend/src/components/chat/ChatInterface.tsx`

### Changes to `handleConcludeBrainstorming()`

After the finalize API returns successfully:

1. Create a `WidgetDefinition` of type `braindump_analysis` with the full markdown + metadata
2. Dispatch `WORKSPACE_ITEMS_EVENT` with `action: 'add'` to push the widget to the workspace
3. Immediately dispatch a second `WORKSPACE_ITEMS_EVENT` with `action: 'set_active'` + the new item's ID + `layoutMode: 'focus'` to auto-focus the analysis in the workspace. (The `add` handler does not auto-activate items, so this second dispatch is required.)
4. Post a chat message with `braindumpSummary` metadata (instead of the raw validation plan text)

**Deduplication guard:** Add an `isFinalizingRef = useRef(false)` in `ChatInterface`. `handleConcludeBrainstorming()` checks this ref and returns early if already finalizing. This prevents double-invocation when the client-side 900s fallback timer and the server's `session_timeout` message fire near-simultaneously.

### File: `frontend/src/components/chat/MessageItem.tsx`

When a message has `braindumpSummary` metadata, render a compact card:

```
┌─────────────────────────────────────────────┐
│ 🧠 Brain Dump Analysis: [Title]            │
│                                             │
│ [2-3 line executive summary...]             │
│                                             │
│ Key themes: Theme 1 · Theme 2 · Theme 3    │
│ 4 action items identified                   │
│                                             │
│ [View Full Analysis]  [Create Initiative]   │
└─────────────────────────────────────────────┘
```

- **"View Full Analysis"** dispatches `WORKSPACE_ITEMS_EVENT` with `action: 'set_active'` + the widget's item ID
- **"Create Initiative"** calls `createInitiativeFromBraindump(analysisDocId)`

Styling: teal accent border, rounded-xl, consistent with existing chat widget cards.

---

## 6. Client-Side Timer UI

### File: `frontend/src/hooks/useVoiceSession.ts`

New state exposed:

```typescript
remainingSeconds: number | null   // null until first time_warning
isWrappingUp: boolean             // true after 12:00 mark
```

Handle new message types from server:

- `time_warning` → update `remainingSeconds`, set `isWrappingUp = true`
- `session_timeout` → trigger auto-finalization (same code path as user clicking Finalize)

### File: `frontend/src/components/chat/ChatInterface.tsx` — brainstorm bar

The existing bar at lines 1256-1308 gets visual state changes:

| Elapsed | Timer Color | Additional UI |
|---|---|---|
| 0:00 – 11:59 | Teal (default) | Normal — waveform, elapsed time |
| 12:00 – 13:59 | Amber | Label: "Agent wrapping up..." |
| 14:00 – 14:59 | Red + pulse | Countdown: "1:00 remaining" (ticks down) |
| 15:00 | — | Auto-finalize triggered |

The server is authoritative. The client timer is cosmetic. Both converge to the same `handleConcludeBrainstorming()` flow. The existing client-side 900s fallback timer (line 359) serves as a safety net if server messages don't arrive.

---

## Files Changed (Summary)

| File | Change Type |
|---|---|
| `app/routers/voice_session.py` | Modified — timer task, session tracking, enhanced response |
| `app/agents/tools/brain_dump.py` | Modified — comprehensive single-document prompt |
| `supabase/migrations/XXXX_braindump_sessions.sql` | New — session tracking table |
| `frontend/src/types/widgets.ts` | Modified — add `braindump_analysis` type |
| `frontend/src/components/widgets/BraindumpAnalysisWidget.tsx` | New — workspace widget |
| `frontend/src/components/widgets/WidgetRegistry.tsx` | Modified — register new widget |
| `frontend/src/components/dashboard/ActiveWorkspace.tsx` | Modified — hydrate new widget type |
| `frontend/src/components/chat/ChatInterface.tsx` | Modified — summary card, timer UI, auto-finalize |
| `frontend/src/components/chat/MessageItem.tsx` | Modified — render summary card |
| `frontend/src/hooks/useVoiceSession.ts` | Modified — handle timer messages |

---

## Testing Strategy

1. **Server timer:** Unit test that `session_timer()` sends correct messages at correct intervals (mock asyncio.sleep)
2. **Finalization:** Integration test that the enhanced finalize endpoint returns `summary`, `analysis_doc_id`, and `analysis_markdown`
3. **Widget rendering:** Component test that `BraindumpAnalysisWidget` renders markdown correctly
4. **Summary card:** Component test that `MessageItem` renders the compact card when `braindumpSummary` metadata is present
5. **E2E:** Manual test — start voice session, let it run past 12 min mark, verify agent wrap-up prompt, verify auto-finalize at 15 min, verify summary card + workspace widget appear
