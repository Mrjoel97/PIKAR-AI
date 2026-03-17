# Brain Dump Voice Session Enhancements — Implementation Plan

**Spec:** `docs/superpowers/specs/2026-03-17-braindump-voice-session-enhancements-design.md`
**Date:** 2026-03-17

## Phases

Work is ordered by dependency: database first, then backend, then frontend. Each phase is independently testable.

---

## Phase 1: Database Migration — `braindump_sessions` table

**Files:**
- `supabase/migrations/20260317000000_braindump_sessions.sql` (new)

**Steps:**
1. Create the migration file with the schema from the spec:
   - `braindump_sessions` table with `id`, `user_id`, `session_type`, `status`, `started_at`, `ended_at`, `duration_seconds`, `turn_count`, `transcript_doc_id`, `analysis_doc_id`, `metadata`, `created_at`, `updated_at`
   - Indexes on `user_id` and `status`
   - RLS policy: `auth.uid() = user_id`
   - `updated_at` trigger function

**Verification:** Run `supabase db push --local` or check SQL syntax validity.

---

## Phase 2: Backend — Server-Side Timer + Session Tracking + Comprehensive Output

**Files:**
- `app/routers/voice_session.py` (modify)
- `app/agents/tools/brain_dump.py` (modify)

### 2a: Timer constants and `session_timer()` task

**Steps:**
1. Add constants at module level: `SESSION_MAX_SECONDS`, `SESSION_WRAPUP_SECONDS`, `SESSION_FINAL_WARNING_SECONDS` (env-configurable)
2. Create `async def session_timer(websocket, live_session, stop_event)`:
   - Sleep until `SESSION_WRAPUP_SECONDS`. If `stop_event` is set, return.
   - Send `{ "type": "time_warning", "remaining_seconds": SESSION_MAX_SECONDS - SESSION_WRAPUP_SECONDS }` to client
   - Inject wrap-up system prompt into `live_session`: `"We have about 3 minutes remaining. Start naturally wrapping up by summarizing the key points discussed."`
   - Sleep until `SESSION_FINAL_WARNING_SECONDS`. If `stop_event` is set, return.
   - Send `{ "type": "time_warning", "remaining_seconds": SESSION_MAX_SECONDS - SESSION_FINAL_WARNING_SECONDS }` to client
   - Sleep until `SESSION_MAX_SECONDS`. If `stop_event` is set, return.
   - Send `{ "type": "session_timeout" }` to client
   - Set `stop_event`
3. In `voice_session()`, add `session_timer` as third task in `asyncio.gather`:
   ```python
   await asyncio.gather(
       forward_audio_to_gemini(),
       forward_audio_from_gemini(),
       session_timer(websocket, live_session, stop_event),
       return_exceptions=True,
   )
   ```

### 2b: Session tracking in WebSocket handler

**Steps:**
1. After auth succeeds, insert a `braindump_sessions` row:
   ```python
   from app.services.supabase_client import get_service_client
   db = get_service_client()
   session_row = db.table("braindump_sessions").insert({
       "user_id": user_id,
       "session_type": "voice",
       "status": "active",
       "metadata": {"session_id": session_id},
   }).execute()
   db_session_id = session_row.data[0]["id"]
   ```
2. In the `finally` block of `voice_session()`, if no finalization happened (track via a flag), update status to `abandoned`:
   ```python
   db.table("braindump_sessions").update({
       "status": "abandoned",
       "ended_at": datetime.now(timezone.utc).isoformat(),
   }).eq("id", db_session_id).execute()
   ```
3. Track whether session timed out via the timer task setting a `timed_out` flag.

### 2c: Enhanced finalize endpoint

**Steps:**
1. Add `BrainstormSummary` model to `voice_session.py`:
   ```python
   class BrainstormSummary(BaseModel):
       title: str
       key_themes: list[str] = Field(default_factory=list)
       action_item_count: int = 0
       executive_summary: str = ""
   ```
2. Add `summary`, `analysis_doc_id`, `analysis_markdown` fields to `BrainstormFinalizeResponse`. Mark `validation_plan` as deprecated (always None).
3. In `finalize_brainstorm_session()`:
   - Replace the call to `process_brainstorm_conversation()` with a call to the new `process_comprehensive_brainstorm()` (see 2d)
   - Set `summary` from the processor result
   - Set `analysis_doc_id` from the saved vault document ID
   - Set `analysis_markdown` from the generated content
   - Replace `saved_categories.extend(["Brain Dump", "Validation Plan"])` with `saved_categories.append("Brain Dump Analysis")`
   - Set `validation_plan = None` explicitly
   - Update the `braindump_sessions` row with artifact doc IDs, duration, turn count, and status (`completed` or `timed_out`)

### 2d: Comprehensive single-document processor

**Steps:**
1. In `app/agents/tools/brain_dump.py`, add `async def process_comprehensive_brainstorm()`:
   - Takes `chat_history`, `context`, `transcript_markdown` (optional, to embed in `<details>`)
   - Single Gemini call with enhanced prompt that produces the comprehensive markdown format from the spec (Executive Summary, Key Ideas, Decision Points, Action Items, Resource Requirements, Risk Factors, Suggested Next Steps)
   - Also instructs the model to return a JSON block at the end with `title`, `key_themes`, `action_item_count`, `executive_summary` for the summary card
   - Parse the JSON block, strip it from the markdown, save the markdown to vault as "Brain Dump Analysis" category
   - Return `{ "success": True, "analysis_markdown": ..., "summary": {...}, "analysis_doc_id": ... }`
2. Keep `process_brainstorm_conversation()` for backward compat (existing tool calls from agents may use it), but it is no longer called from the finalize endpoint.
3. Modify `_save_to_vault()` to return the `vault_documents.id` (not just the file path). Currently it returns `file_path` — change the return to include both:
   ```python
   return {"file_path": file_path, "doc_id": inserted_row_id}
   ```
   Update callers of `_save_to_vault()` accordingly.

---

## Phase 3: Frontend — Voice Session Hook Timer Handling

**Files:**
- `frontend/src/hooks/useVoiceSession.ts` (modify)

**Steps:**
1. Add new state fields to `VoiceSessionState`:
   ```typescript
   remainingSeconds: number | null;
   isWrappingUp: boolean;
   ```
2. Initialize both in the default state: `remainingSeconds: null`, `isWrappingUp: false`
3. Add a `onSessionTimeout` callback ref that the consumer (ChatInterface) can set
4. In the `ws.onmessage` switch, add cases:
   ```typescript
   case 'time_warning':
       setState(prev => ({
           ...prev,
           remainingSeconds: msg.remaining_seconds,
           isWrappingUp: true,
       }));
       break;
   case 'session_timeout':
       setState(prev => ({
           ...prev,
           remainingSeconds: 0,
       }));
       // Trigger auto-finalization callback
       if (onSessionTimeoutRef.current) {
           onSessionTimeoutRef.current();
       }
       break;
   ```
5. Expose `remainingSeconds`, `isWrappingUp`, and `setOnSessionTimeout` in the return value
6. Reset `remainingSeconds` and `isWrappingUp` on `connect()` and `disconnect()`

---

## Phase 4: Frontend — Widget Type + BraindumpAnalysisWidget

**Files:**
- `frontend/src/types/widgets.ts` (modify)
- `frontend/src/components/widgets/BraindumpAnalysisWidget.tsx` (new)
- `frontend/src/components/widgets/WidgetRegistry.tsx` (modify)
- `frontend/src/components/dashboard/ActiveWorkspace.tsx` (modify)

### 4a: Widget type definitions

**Steps:**
1. In `widgets.ts`:
   - Add `'braindump_analysis'` to `WidgetType` union
   - Add `BraindumpAnalysisData` interface
   - Add to `WidgetData` union
   - Add `isBraindumpAnalysisData()` type guard
   - Add `'braindump_analysis'` to `isValidWidgetType()` valid types array
   - Add case to `validateWidgetDefinition()` switch

### 4b: Widget component

**Steps:**
1. Create `BraindumpAnalysisWidget.tsx`:
   - Import `ReactMarkdown`, `remarkGfm`, `WidgetProps`
   - Extract `data` from `definition.data` as `BraindumpAnalysisData`
   - Render header: title, category badge ("Brain Dump Analysis" in indigo), action item count
   - Render markdown body with `prose` styling matching `BrainDumpInterface`
   - "Create Initiative" button — calls `createInitiativeFromBraindump(data.documentId)`
   - "Download" button — creates a Blob from `data.markdown` and triggers download
   - Export as default

### 4c: Registry + workspace hydration

**Steps:**
1. In `WidgetRegistry.tsx`:
   - Add dynamic import for `BraindumpAnalysisWidget`
   - Add `braindump_analysis: BraindumpAnalysisWidget` to `WIDGET_MAP`
2. In `ActiveWorkspace.tsx`:
   - Add `braindump_analysis` case to `workspaceRowToWidget()` (per spec code snippet)

---

## Phase 5: Frontend — Chat Summary Card + Post-Session Flow

**Files:**
- `frontend/src/components/chat/ChatInterface.tsx` (modify)
- `frontend/src/components/chat/MessageItem.tsx` (modify)

### 5a: Deduplication guard + finalization flow

**Steps:**
1. In `ChatInterface.tsx`, add `isFinalizingRef = useRef(false)` alongside existing state
2. In `handleConcludeBrainstorming()`:
   - At the top: `if (isFinalizingRef.current) return; isFinalizingRef.current = true;`
   - In `finally`: `isFinalizingRef.current = false;`
3. Wire up `voiceSession.setOnSessionTimeout` to call `handleConcludeBrainstorming` (for auto-finalize on server timeout)
4. After successful finalize:
   - Build a `WidgetDefinition` of type `braindump_analysis`:
     ```typescript
     const widgetDef: WidgetDefinition = {
         type: 'braindump_analysis',
         title: result.summary?.title || 'Brain Dump Analysis',
         data: {
             markdown: result.analysis_markdown || '',
             documentId: result.analysis_doc_id || '',
             sessionId,
             title: result.summary?.title || 'Brain Dump Analysis',
             keyThemes: result.summary?.key_themes || [],
             actionItemCount: result.summary?.action_item_count || 0,
         },
         workspace: { mode: 'focus' },
     };
     ```
   - Import and call `buildWorkspaceRenderableItem` + dispatch `WORKSPACE_ITEMS_EVENT` with `action: 'add'`
   - Dispatch second `WORKSPACE_ITEMS_EVENT` with `action: 'set_active'` + `layoutMode: 'focus'`
   - Replace the existing `addMessage` calls with a single message carrying `braindumpSummary` metadata:
     ```typescript
     addMessage({
         role: 'agent',
         text: result.summary?.executive_summary || 'Your brainstorming session has been analyzed.',
         agentName: agentName || 'Pikar AI',
         metadata: {
             braindumpSummary: {
                 title: result.summary?.title || 'Brain Dump Analysis',
                 keyThemes: result.summary?.key_themes || [],
                 actionItemCount: result.summary?.action_item_count || 0,
                 executiveSummary: result.summary?.executive_summary || '',
                 analysisDocId: result.analysis_doc_id || '',
                 workspaceItemId: itemId, // from the workspace item created above
             },
         },
     });
     ```

### 5b: Summary card rendering in MessageItem

**Steps:**
1. In `MessageItem.tsx`, check for `message.metadata?.braindumpSummary`
2. If present, render the compact card instead of plain text:
   - Teal-accented border, rounded-xl card
   - Brain icon + title
   - Executive summary (2-3 lines, truncated)
   - Key themes as dot-separated inline list
   - Action item count badge
   - "View Full Analysis" button — dispatches `WORKSPACE_ITEMS_EVENT` with `action: 'set_active'`
   - "Create Initiative" button — calls `createInitiativeFromBraindump(summary.analysisDocId)`
3. Import necessary event dispatchers from `@/services/widgetDisplay`

---

## Phase 6: Frontend — Client-Side Timer UI

**Files:**
- `frontend/src/components/chat/ChatInterface.tsx` (modify — brainstorm bar section)

**Steps:**
1. In the brainstorm bar component (lines 1256-1308), consume `voiceSession.remainingSeconds` and `voiceSession.isWrappingUp`
2. Add timer color logic based on `brainstormDuration`:
   - `< 720` (12 min): teal (existing)
   - `720-839`: amber + "Agent wrapping up..." label
   - `>= 840`: red + pulse animation + countdown display using `voiceSession.remainingSeconds`
3. When `remainingSeconds` is available and `< 60`, show countdown instead of elapsed time
4. No functional changes — purely visual. The auto-finalize is handled by the `onSessionTimeout` callback from Phase 5a.

---

## Phase Summary

| Phase | Files | Depends On |
|---|---|---|
| 1. DB Migration | 1 new | None |
| 2. Backend (timer, tracking, output) | 2 modified | Phase 1 |
| 3. Frontend (hook timer handling) | 1 modified | Phase 2 |
| 4. Frontend (widget type + component) | 4 modified/new | None (parallel with 2-3) |
| 5. Frontend (summary card + flow) | 2 modified | Phases 2, 3, 4 |
| 6. Frontend (timer UI) | 1 modified | Phase 3 |

**Phases 1-2** and **Phase 4** can run in parallel since they have no dependencies on each other.

**Total files:** 1 new migration + 1 new component + 8 modified = 10 files
