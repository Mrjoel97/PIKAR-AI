# Voice Brainstorm Overlay — Design Spec

## Problem

The current brainstorm feature feels robotic and turn-based: agent speaks, a recording session starts, user speaks, recording stops, text is transcribed, agent replies. Users want a natural, uninterrupted voice conversation — like a phone call — with the structured `.md` analysis generated only after the session ends.

## Solution

A full-screen modal overlay (`VoiceBrainstormOverlay`) that provides an immersive call-like experience. The overlay is purely a presentation layer on top of the existing `useVoiceSession` hook and Gemini Live API WebSocket infrastructure. Zero backend changes.

## Architecture

### Entry Point

The existing `BrainDumpMenu` brain icon in ChatInterface triggers `handleStartBrainstorming()`, which calls `voiceSession.connect(sessionId)`. Once `isBrainstorming` is true, ChatInterface renders `<VoiceBrainstormOverlay>` as a React portal to `document.body`.

### Component: VoiceBrainstormOverlay

**Location:** `frontend/src/components/braindump/VoiceBrainstormOverlay.tsx`

**Props:**

```typescript
/** Result from POST /ws/voice/finalize — matches BrainstormFinalizeResponse on backend. */
interface BrainstormFinalizeResult {
  success: boolean;
  transcript_markdown: string | null;
  transcript_file_path: string | null;
  saved_categories: string[];
  error: string | null;
  summary: {
    title: string;
    key_themes: string[];
    action_item_count: number;
    executive_summary: string;
  } | null;
  analysis_doc_id: string | null;
  analysis_markdown: string | null;
}

interface VoiceBrainstormOverlayProps {
  isConnected: boolean;
  isAgentSpeaking: boolean;
  transcriptTurns: VoiceTranscriptTurn[];
  remainingSeconds: number | null;
  isWrappingUp: boolean;
  isTimedOut: boolean;
  error: string | null;
  isFinalizingBrainstorm: boolean;
  finalizeResult: BrainstormFinalizeResult | null;
  onEndSession: () => void;       // maps to handleConcludeBrainstorming (finalize + analyze)
  onRetry: () => void;            // maps to handleStartBrainstorming (reconnect)
  onViewAnalysis: () => void;     // dispatches workspace event + closes overlay
  onDismiss: () => void;          // clears finalizeResult, closes overlay
}
```

All props are derived from existing state in ChatInterface and the `useVoiceSession` hook. No new hooks or data fetching.

- `onEndSession` always means **finalize** — disconnect, save transcript, generate analysis. It does NOT cancel/discard.
- `onRetry` re-triggers the full connect flow (used only in the Connection Error phase).

### Phase Derivation (from props, not internal state)

Evaluated top-to-bottom; first match wins:

| # | Condition | Phase | Notes |
|---|-----------|-------|-------|
| 1 | `finalizeResult` | Summary Card | Terminal — always wins if set |
| 2 | `isFinalizingBrainstorm && !finalizeResult` | Processing | Spinner while API runs |
| 3 | `isConnected && !isFinalizingBrainstorm` | Active Conversation | Main state; error banner shown inline if `error` is set |
| 4 | `error && !isConnected && transcriptTurns.length > 0` | Active Conversation (disconnected) | Mid-session drop: amber banner + End Session still works |
| 5 | `error && !isConnected && transcriptTurns.length === 0` | Connection Error | Pre-conversation failure: retry/cancel buttons |
| 6 | `!isConnected && !error` | Connecting | Initial WebSocket handshake |

**Mid-session disconnect (row 4):** The overlay stays in Active Conversation phase showing an amber "Connection lost" banner above the transcript. The End Session button still works — clicking it calls `onEndSession` which finalizes with whatever transcript was captured. This matches the existing `useVoiceSession` behavior where `error` is set but the transcript persists.

**Empty transcript edge case:** If `handleConcludeBrainstorming` detects an empty transcript, it short-circuits before setting `isFinalizingBrainstorm`. ChatInterface sets `isBrainstorming = false`, which would abruptly close the overlay. To handle this gracefully, ChatInterface should set `finalizeResult` to an error result (`{ success: false, error: 'No conversation captured', ... }`) so the overlay transitions to the Summary Card phase with the error message and a Close button, rather than vanishing.

### Changes to ChatInterface.tsx

1. **New state:** `finalizeResult: BrainstormFinalizeResult | null` — holds the finalize response. Set inside `handleConcludeBrainstorming` alongside existing chat message posting.
2. **New type:** `BrainstormFinalizeResult` — extracted from the inline response shape already used in `handleConcludeBrainstorming`.
3. **Render overlay:** When `isBrainstorming || isFinalizingBrainstorm || finalizeResult`, render `<VoiceBrainstormOverlay>` via `createPortal(el, document.body)`.
4. **`onViewAnalysis` callback:** Extracts the existing `WORKSPACE_ITEMS_EVENT` dispatch block from `handleConcludeBrainstorming` into a reusable function.
5. **`onRetry` callback:** Wraps `handleStartBrainstorming` — clears error state and re-initiates the voice session connect.
6. **`onDismiss` callback:** Sets `finalizeResult = null`, ensures `isBrainstorming = false`.
7. **Empty transcript guard:** When `handleConcludeBrainstorming` detects empty transcript, set `finalizeResult` to `{ success: false, error: 'No conversation was captured' }` instead of short-circuiting — so the overlay shows the error in the summary card phase.

The existing chat message posting (system messages, summary card in chat) is preserved — the overlay is additive.

### BrainDumpMenu

Unchanged. Continues to show the brain icon for start, and a compact "In Session" pill with timer during active sessions. The overlay renders at `z-50` via portal to `document.body`, fully blocking interaction with the underlying UI including BrainDumpMenu. The BrainDumpMenu's Finalize/Stop buttons are not clickable while the overlay is visible.

## Visual Design

### Phase 1: Connecting

- Full-screen dark backdrop: `bg-black/60 backdrop-blur-sm`
- Centered: pulsing brain icon with gradient ring animation
- Text: "Connecting..."
- Duration: 1-3 seconds typically

### Phase 2: Active Conversation

- Dark backdrop persists
- Centered card (`rounded-[28px]`, app shadow style, `max-w-lg`)
- **Agent avatar:** Circular brain icon with animated gradient ring. Pulses when agent speaks, calm idle otherwise.
- **Status line:** Green dot + "Connected" + elapsed timer (counts up: `3:42`). Timer phases: teal (normal) → amber at 12:00 (wrap-up) → red pulse at 14:00 (final warning). In the final-warning phase (last 60s), the timer switches to a countdown. Reuses the same phase logic as BrainDumpMenu.
- **Wrap-up banner:** Appears at 12:00 — "Wrapping up — summarize your key points". At 14:00 — "1 minute remaining".
- **Live transcript panel:** Below avatar, `max-h-[40vh]` with `overflow-y-auto`, auto-scroll to bottom. Read-only display of `transcriptTurns`. Speaker labels: "You" (right-aligned, teal bubble) / "Pikar" (left-aligned, slate bubble).
- **End Session button:** Rose/red, prominent, bottom center. Triggers `onEndSession`.
- **No close X / dismiss gesture during active conversation.** The overlay closes only via End Session, session timeout, or error-state Cancel. The dark backdrop has `pointer-events: none` pass-through disabled — the underlying BrainDumpMenu is not interactive while the overlay is visible.

### Phase 3a: Processing

- Same card, content transitions (framer-motion `AnimatePresence`)
- Spinner + "Generating your analysis..."
- Transcript still visible but faded

### Phase 3b: Summary Card

- Brief confirmation card (auto-dismisses after 3 seconds, or on click):
  - Checkmark icon + "Session Complete"
  - Title from `finalizeResult.summary.title`
  - "Your analysis is ready in chat" subtitle
- After auto-dismiss (or click), overlay closes. The rich summary is displayed in two places:
  1. **Chat:** `handleConcludeBrainstorming` posts the existing summary card message (title, executive summary, key themes, action item count) as an agent message in chat. This already works — no change needed.
  2. **Workspace:** `handleConcludeBrainstorming` dispatches the existing `WORKSPACE_ITEMS_EVENT` to push a `braindump_analysis` widget. This already works — no change needed. The widget has a "Focus" button that opens it full-screen in the workspace.
- The overlay's job is just to provide the brief visual confirmation before getting out of the way. The real summary lives in chat (scrollable, persistent) and workspace (expandable, focusable).
- **Error result:** If `finalizeResult.success` is false, show error icon + `finalizeResult.error` message + "Close" button (calls `onDismiss`). If `transcript_markdown` exists despite the error, also show "View Transcript" link. No auto-dismiss on errors.

### Connection Error State

- Same card layout
- Error icon + message from `error` prop
- "Try Again" button (calls `onRetry` → re-triggers `handleStartBrainstorming`) + "Cancel" button (calls `onDismiss`)

## Error Handling

| Scenario | Behavior |
|----------|----------|
| WebSocket connection fails | Error state with retry/cancel |
| Mid-session disconnect | Amber banner, End Session still works |
| Session timeout (15:00) | Auto-transitions to processing → summary |
| Empty transcript | `handleConcludeBrainstorming` sets error `finalizeResult` → overlay shows "No conversation captured" + Close |
| Finalize API failure | Summary card shows error + "View Transcript" if transcript was saved |
| Browser tab backgrounded | Existing `ctx.resume()` in useVoiceSession handles it |
| Browser navigation during session | `onBeforeUnload` warning via `useEffect` in overlay — "Leave session? Your conversation will be lost." |

## Session Limits

- Max duration: 15 minutes (existing `SESSION_MAX_SECONDS=900`)
- Wrap-up warning: 12:00 (existing `SESSION_WRAPUP_SECONDS=720`)
- Final warning: 14:00 (existing `SESSION_FINAL_WARNING_SECONDS=840`)
- No changes to these values.

## Styling

- `rounded-[28px]` cards matching app design language
- Teal accent for primary actions, rose for end session
- Framer-motion transitions between phases (`AnimatePresence mode="wait"`)
- Mobile responsive: card goes full-width with padding on small screens
- Dark mode compatible (dark backdrop works either way)

## Scope Boundaries

### In Scope
- VoiceBrainstormOverlay component (new)
- ChatInterface integration (minimal additions)

### Out of Scope
- Backend changes (none needed)
- useVoiceSession hook changes (none needed)
- Voice quality tuning (system prompt / voice name — separate concern)
- BrainDumpMenu redesign (stays as-is)
- New npm dependencies (none needed)

## Files

### Create
| File | Purpose |
|------|---------|
| `frontend/src/components/braindump/VoiceBrainstormOverlay.tsx` | Overlay with 3 phases |

### Modify
| File | Change |
|------|--------|
| `frontend/src/components/chat/ChatInterface.tsx` | Add `finalizeResult` state, render portal, extract callbacks |
