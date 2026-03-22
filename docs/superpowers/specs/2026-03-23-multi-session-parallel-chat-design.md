# Multi-Session Parallel Chat

**Date:** 2026-03-23
**Status:** Approved
**Approach:** Lightweight State Lift (Approach 1)

## Overview

Add the ability for users to run multiple chat sessions in parallel — like Claude.ai — where they can start a new chat while an existing one is still streaming, switch freely between sessions, and see background responses complete without interruption.

The backend already fully supports multi-session (stateless `/a2a/app/run_sse`, `SupabaseSessionService` with per-user session management). This feature is **frontend-only** with minor admin config additions.

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| UI pattern | Sidebar-based, one chat visible at a time | Matches existing `SessionList.tsx` layout, proven pattern (Claude.ai) |
| Background stream behavior | Continue streaming when user switches away | Best UX — response is ready when they return |
| Concurrent stream cap | 4 (configurable via admin config) | Balances resource usage with power-user needs |
| Cap enforcement | Client-side | SSE connections originate from browser; backend is already stateless |
| Eviction strategy | LRU by least recently visible | Matches user attention/intent signal |
| Notifications | Sidebar badge + toast | Covers passive (badge) and active (toast) discovery |

## Critical Architecture Change: Remove Component Remounting

The current `PersonaDashboardLayout.tsx` renders `ChatInterface` with a `key` prop:

```tsx
<ChatInterface key={effectiveSessionId ?? 'new'} initialSessionId={effectiveSessionId} ... />
```

This forces React to **unmount and remount** the entire component tree on every session switch, destroying all in-memory state (messages, SSE connections, AbortControllers). This is fundamentally incompatible with background streaming.

**Required change:** Remove the `key` prop from `ChatInterface`. Instead, `ChatInterface` becomes a thin renderer that subscribes to whichever session `visibleSessionId` points to. All session state and stream management lives in the contexts above it, surviving session switches.

## Consolidating Session Management

The codebase currently has **two independent session management systems**:

1. `ChatSessionContext.tsx` — used by `PersonaDashboardLayout`, layout, vault, workspace
2. `useSessionHistory.ts` — used by `SessionList.tsx` (independent Supabase client, independent state)

Both fetch from the same `sessions` table but maintain separate state. **This must be consolidated.** The new `SessionMapContext` becomes the single source of truth for session metadata and active state. `useSessionHistory.ts` is removed; `SessionList.tsx` consumes `SessionMapContext` directly.

## Core State Architecture

### Current State

```
currentSessionId: string | null
sessions: SessionMetadata[]
```

### New State

```
visibleSessionId: string | null
activeSessions: Map<string, ActiveSessionState>
sessions: SessionMetadata[]
```

Where `ActiveSessionState`:

```typescript
interface ActiveSessionState {
  sessionId: string
  messages: Message[]
  status: 'idle' | 'streaming' | 'error' | 'interrupted'
  abortController: AbortController | null
  hasUnread: boolean
  lastUpdatedAt: number       // timestamp of last user view
  scrollTop: number           // preserved scroll position
  rawWidgets: WidgetData[]    // deferred widget processing for background sessions
}
```

The `'interrupted'` status is distinct from `'error'`:
- `'interrupted'` — stream was stopped by cap eviction. Inline message: "Response was interrupted — send again to continue"
- `'error'` — stream failed due to network/server error. Inline message shows error details (existing behavior)
- User clicking "Stop" sets status to `'idle'` with the partial message preserved (not `'interrupted'`)

### Key Behaviors

- **"New Chat"** — Generates session ID using existing format: `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`. Adds empty `ActiveSessionState` to map, sets as `visibleSessionId`.
- **"Select session" (warm)** — Session already in `activeSessions` map. Flip `visibleSessionId` pointer. Zero network calls, instant render.
- **"Select session" (cold)** — Session not in map. Load history from Supabase into new `ActiveSessionState` entry, then flip. Minimal skeleton shown during load.
- **"Send message"** — Operates on `ActiveSessionState` for current `visibleSessionId`. SSE stream writes to map entry regardless of which session is visible.

## Background Stream Management

### Stream Lifecycle

```
User sends message in Session A
  -> Create AbortController, store in activeSessions['A']
  -> Start fetch to /a2a/app/run_sse
  -> On each SSE event: update activeSessions['A'].messages via ref
  -> User switches to Session B
  -> Stream keeps writing to activeSessions['A'] (map ref is stable)
  -> Stream completes -> set status='idle', hasUnread=true, fire toast
  -> User switches back to Session A -> messages already there, instant
```

### Ref-Based Stream Writing

The SSE event handler writes to a `useRef` pointing at the map entry, NOT to React state directly. This is critical for performance:

- Background sessions accumulate messages in the ref without triggering any re-renders
- Batched state updates flush on `requestAnimationFrame` only for the **visible session**
- When the user switches to a background session, the ref data is flushed to state in one batch

### Deferred Widget Processing

For background sessions, skip `validateWidgetDefinition()` during streaming. Store raw widget data in `rawWidgets`. Process on switch using `setTimeout(fn, 0)` (preferred over `requestIdleCallback` since Safari lacks support and the codebase doesn't use it elsewhere).

### Background Session Side-Effect Suppression

Several operations in the current `useAgentChat` fire side effects during streaming that are only meaningful for the visible session:

- `WidgetDisplayService.saveWidget()` — saves widgets to workspace
- `dispatchFocusWidget()` — fires `CustomEvent` to focus a widget panel
- `dispatchWorkspaceActivity()` — fires `CustomEvent` on every SSE chunk

**For background sessions, these must be suppressed:**
- `dispatchFocusWidget()` and `dispatchWorkspaceActivity()` — skip entirely when `sessionId !== visibleSessionId`. Queue them as pending actions in `ActiveSessionState`.
- `WidgetDisplayService.saveWidget()` — defer until the session becomes visible. Store raw widget data in `rawWidgets`.
- When the user switches to a session with pending actions, flush: process `rawWidgets`, fire a single `dispatchWorkspaceActivity`, and focus the last widget (not every intermediate one).

### Session Lifecycle Callbacks

`ChatInterface` currently receives `onSessionStarted` and `onAgentResponse` callbacks from `PersonaDashboardLayout` to update session titles and previews.

**In the new architecture:**
- `onSessionStarted` — fires for all sessions (updates title in sidebar metadata). This is lightweight and should always run.
- `onAgentResponse` — fires for all sessions (updates preview text in sidebar). Also lightweight.
- These callbacks update `SessionMapContext` metadata, not component state, so they don't trigger re-renders of the chat area.

## Concurrent Stream Cap & Eviction

### Cap: 4 concurrent SSE streams (admin-configurable)

When a 5th stream is triggered:

1. Check `activeSessions` where `status === 'streaming'` — count exceeds cap
2. Find the streaming session with the oldest `lastUpdatedAt` that is NOT `visibleSessionId`
3. Abort that stream's `AbortController`
4. Set its status to `'interrupted'`
5. Preserve its partial messages (no data loss)
6. Start the new session's stream

### Eviction Rules

- The currently visible session is **never evicted**
- Eviction only stops the stream, does not delete the session or messages
- Interrupted sessions show inline indicator: "Response was interrupted — send again to continue"

### Admin Config

Session settings are stored in the `user_configurations` table (migration `0034`) under a `sessions` config key:

```sql
-- Uses existing user_configurations table, no new migration needed
-- Admin sets org-wide defaults; individual users inherit unless overridden
INSERT INTO user_configurations (user_id, config_key, config_value)
VALUES ('system', 'sessions', '{
  "max_concurrent_streams": 4,
  "memory_eviction_minutes": 30,
  "max_active_sessions_in_memory": 20
}');
```

**Backend endpoint:** Add a `GET /api/admin/config/sessions` route in `app/routers/admin/` that reads from `user_configurations` where `config_key = 'sessions'`. This follows the existing admin config pattern.

**Frontend consumption:** Fetched once on app load, cached in `SessionControlContext`. Re-fetched when admin updates config. If the endpoint is unavailable, fall back to hardcoded defaults: `{ max_concurrent_streams: 4, memory_eviction_minutes: 30, max_active_sessions_in_memory: 20 }`.

## UI Changes

### Sidebar (`SessionList.tsx`)

- **"New Chat" button** — Pinned at top. Always visible. Keyboard shortcut: `Alt+N` / `Option+N` (avoids browser conflicts — `Ctrl+N` opens new window, `Ctrl+Shift+N` / `Cmd+Shift+N` opens incognito/private window)
- **Status indicators per session item:**
  - Streaming: animated pulse dot (accent color)
  - Unread: solid dot (clears when session becomes visible)
  - Interrupted: muted icon
- **Active grouping** — Sessions with active streams or unread responses float to top under "Active" divider. Remaining sessions in chronological order below.

### Chat Area (`ChatInterface.tsx`)

- **Instant switching** — Sessions in `activeSessions` swap with a single state pointer change. No loading skeleton.
- **Cold session loading** — Minimal skeleton for sessions loaded from Supabase.
- **Scroll position preservation** — The chat message container (the scrollable `div` wrapping the message list inside `ChatInterface`) stores its `scrollTop` into `ActiveSessionState` on every `visibleSessionId` change (captured in a `useEffect` cleanup). On switch-in, `scrollTop` is restored after messages render via `requestAnimationFrame`. Auto-scroll-to-bottom (existing `messagesEndRef` behavior) only applies when the user was already at the bottom when they left, or when new messages arrive in the visible session.
- **Startup preload** — Load up to 3 most recent sessions' message history in parallel on mount via `Promise.all`. Gated: only preloads sessions that actually exist (no wasted requests for new users with <3 sessions). Each preload respects the existing `SESSION_MAX_EVENTS` (80) limit. This supplements (not replaces) the existing session metadata fetch. The metadata fetch loads titles/previews for the sidebar; the preload additionally loads full message history so the first switches are instant.

### Toast Notifications

- Appears bottom-right on background stream completion: **"[Session title] — Response ready"**
- Clickable — switches to that session
- Auto-dismiss after 5 seconds
- Max 2 stacked. 3+ simultaneous completions show summary toast: "N sessions ready"
- No toast when `document.visibilityState === 'hidden'` (rely on sidebar badge when user returns)

## Performance Safeguards

### Render Isolation

**Context splitting** — Split `ChatSessionContext` into two:

- `SessionMapContext` — holds `activeSessions` map. Updated frequently by streams. Consumed by chat renderer (visible session only) and sidebar badges.
- `SessionControlContext` — holds `visibleSessionId`, `createSession`, `selectSession`. Rarely changes. Consumed by sidebar and layout.

**Per-session memoization** — Chat message list wrapped in `React.memo` keyed by `visibleSessionId`. Background updates never trigger visible chat re-renders.

### Network Efficiency

| Concern | Mitigation |
|---|---|
| Multiple SSE connections | Browser handles 6+ concurrent per origin. 4 is well within budget. |
| Session list re-fetching | Stale-while-revalidate cache. Refetch only on create/delete. |
| History loading (cold switch) | Fetch last 80 events (existing `SESSION_MAX_EVENTS`). Paginate on scroll-up. |
| Startup preload | 3 most recent sessions loaded in parallel on mount. |
| Widget processing | Deferred for background sessions. `setTimeout(fn, 0)` on switch. |

### Memory Management

- **Idle eviction (30min configurable)** — Sessions with `status: 'idle'` and `hasUnread: false` not viewed in 30 min get messages cleared. Metadata stays in sidebar. Re-loaded from Supabase on visit.
- **Hard cap (20 in memory)** — Map exceeds 20 entries -> LRU evict idle sessions regardless of time.
- **Message compaction** — Sessions with 100+ messages keep last 50 rendered. Older messages lazy-load on scroll-up.

### What We're NOT Doing (YAGNI)

- No Web Workers — SSE is lightweight at 4 streams on main thread
- No service worker session caching — Supabase is fast enough for cold loads
- No cross-tab session sync — Each tab manages independently
- No optimistic pre-streaming — Don't start streams before user sends a message

## File Changes

### Rewritten Files

These files are effectively rewritten rather than patched. The existing code is single-session throughout and the multi-session architecture changes their core responsibility.

| File | Change |
|---|---|
| `frontend/src/hooks/useAgentChat.ts` | **Rewrite.** Extract SSE streaming logic into `useBackgroundStream`. What remains is a thin hook that calls into `SessionMapContext` to get/set messages for the visible session and delegates streaming to `useBackgroundStream`. Existing widget service calls, workspace activity dispatches, and message queue logic move into the background stream manager with visibility-gating. |
| `frontend/src/contexts/ChatSessionContext.tsx` | **Replace.** Split into `SessionMapContext` + `SessionControlContext`. The original file is deleted; a re-export shim (`useChatSession` -> new hooks) is provided temporarily if needed but ideally all consumers migrate directly. |

### Modified Files

| File | Change |
|---|---|
| `frontend/src/components/chat/SessionList.tsx` | Consume `SessionMapContext` instead of `useSessionHistory`. Add "New Chat" button, status indicators, active session grouping. |
| `frontend/src/components/chat/ChatInterface.tsx` | Remove reliance on `key` prop for remounting. Become thin renderer: subscribe to `visibleSessionId` from context, render messages from `activeSessions` map. Add scroll position save/restore. Update `useRealtimeSession` to dynamically switch channels when `visibleSessionId` changes (unsubscribe old, subscribe new). Update `usePresence` to switch presence channel (`chat:${sessionId}`) on session change. |
| `frontend/src/app/(personas)/[persona]/PersonaDashboardLayout.tsx` | Remove `key={effectiveSessionId}` from `ChatInterface`. Update to consume new split contexts. |
| `frontend/src/app/layout.tsx` | Replace `ChatSessionProvider` with new `SessionMapProvider` + `SessionControlProvider`. |
| `frontend/src/components/vault/VaultInterface.tsx` | Replace raw `useContext(ChatSessionContext)` calls with new split-context hooks. |
| `frontend/src/components/dashboard/ActiveWorkspace.tsx` | Deep migration: replace 10+ `currentSessionId` references with `visibleSessionId` from new context. Update widget filtering, `workspace_items` queries, and event handlers (`WORKSPACE_ACTIVITY_EVENT`, `WIDGET_FOCUS_EVENT`) to use `visibleSessionId`. Coordinate with deferred widget processing — when a session becomes visible, `ActiveWorkspace` must process any pending `rawWidgets` flushed from background. |
| `frontend/src/app/dashboard/history/page.tsx` | Update `useChatSession()` import to new context hook. |
| `frontend/src/components/layout/Sidebar.tsx` | Currently reads `sessionId` from URL search params, not from context. Verify if URL-based approach is still needed alongside context-based `visibleSessionId`. If redundant, remove URL dependency and consume context directly. |

### Removed Files

| File | Reason |
|---|---|
| `frontend/src/hooks/useSessionHistory.ts` | Redundant — `SessionMapContext` becomes the single source of truth for session metadata. `SessionList.tsx` consumes context directly. |

### New Files

| File | Purpose |
|---|---|
| `frontend/src/contexts/SessionMapContext.tsx` | Active sessions map, stream status, unread state, session metadata |
| `frontend/src/contexts/SessionControlContext.tsx` | Visible session pointer, create/switch/delete actions, admin config cache |
| `frontend/src/hooks/useBackgroundStream.ts` | Ref-based SSE stream manager. Handles `fetchEventSource` calls, writes to map entries, gates side effects (widget save, focus dispatch, workspace activity) based on visibility. Core of the background streaming feature. |
| `frontend/src/hooks/useStreamCap.ts` | Concurrent stream limit enforcement, LRU eviction logic |
| `frontend/src/hooks/useSessionPreload.ts` | Parallel preload of 3 most recent sessions' message history on mount |
| `frontend/src/components/chat/SessionStatusBadge.tsx` | Streaming dot, unread badge, interrupted indicator |
| `frontend/src/components/chat/SessionToast.tsx` | Background completion toast notification |
| `frontend/src/components/chat/NewChatButton.tsx` | "New Chat" button with `Alt+N` / `Option+N` keyboard shortcut |

### Backend Changes

| File | Change |
|---|---|
| `app/routers/admin/config.py` (or equivalent) | Add `GET /api/admin/config/sessions` endpoint returning session config from `system_config` table with defaults fallback |
| `user_configurations` table seed | Add `sessions` config entry (user_id='system') with defaults: `{ max_concurrent_streams: 4, memory_eviction_minutes: 30, max_active_sessions_in_memory: 20 }` |

### No Changes Needed

- `SupabaseSessionService` — already multi-session
- `/a2a/app/run_sse` — already stateless per request
- Database schema — no new migrations (uses existing `system_config`)
- Agent code — no changes
- `useAdminChat.ts` — admin panel remains single-session (future consideration)

### Estimated Scope

- 2 files rewritten (`useAgentChat`, `ChatSessionContext`)
- 8 files modified (consumers of old context + layout changes)
- 1 file removed (`useSessionHistory`)
- 8 new files (contexts, hooks, components)
- 1-2 backend files (admin config endpoint + seed)
- 0 database migrations
