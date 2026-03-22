# Multi-Session Parallel Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable users to run multiple chat sessions in parallel with background streaming, configurable concurrent stream cap, and instant session switching.

**Architecture:** Split the single `ChatSessionContext` into two focused contexts (`SessionMapContext` for active session state, `SessionControlContext` for navigation/config). Extract SSE streaming into a ref-based `useBackgroundStream` hook that writes to map entries regardless of which session is visible. `ChatInterface` becomes a thin renderer that subscribes to the visible session.

**Tech Stack:** React 19, TypeScript, Supabase (PostgreSQL), sonner (toasts), fetchEventSource (SSE), FastAPI (backend config endpoint)

**Spec:** `docs/superpowers/specs/2026-03-23-multi-session-parallel-chat-design.md`

---

## Wave 1: Foundation — Types, Contexts, and Provider Wiring

### Task 1: Session Types and Interfaces

**Files:**
- Create: `frontend/src/types/session.ts`

- [ ] **Step 1: Create shared type definitions**

```typescript
// frontend/src/types/session.ts

export type SessionStatus = 'idle' | 'streaming' | 'error' | 'interrupted'

export interface ActiveSessionState {
  sessionId: string
  messages: Message[]
  status: SessionStatus
  abortController: AbortController | null
  hasUnread: boolean
  lastUpdatedAt: number
  scrollTop: number
  rawWidgets: RawWidgetData[]
  pendingActions: PendingSessionAction[]
}

export interface RawWidgetData {
  widget: unknown  // raw widget from SSE, pre-validation
  messageIndex: number
}

export interface PendingSessionAction {
  type: 'focus_widget' | 'workspace_activity'
  payload: unknown
}

export interface SessionConfig {
  max_concurrent_streams: number
  memory_eviction_minutes: number
  max_active_sessions_in_memory: number
}

export const DEFAULT_SESSION_CONFIG: SessionConfig = {
  max_concurrent_streams: 4,
  memory_eviction_minutes: 30,
  max_active_sessions_in_memory: 20,
}

export function createEmptyActiveSession(sessionId: string): ActiveSessionState {
  return {
    sessionId,
    messages: [],
    status: 'idle',
    abortController: null,
    hasUnread: false,
    lastUpdatedAt: Date.now(),
    scrollTop: -1,  // -1 = scroll to bottom (default)
    rawWidgets: [],
    pendingActions: [],
  }
}
```

Import the `Message` type from the existing `useAgentChat.ts` (lines 11-24). That type will later be moved here when `useAgentChat` is rewritten in Task 6, but for now import from the existing location.

- [ ] **Step 2: Verify types compile**

Run: `cd frontend && npx tsc --noEmit src/types/session.ts`
Expected: No errors (or only errors from the Message import which is fine at this stage)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/session.ts
git commit -m "feat(sessions): add shared types for multi-session state"
```

---

### Task 2: SessionMapContext — Active Sessions State

This context holds the `activeSessions` map and the session metadata list. It's the high-frequency context (updated by streams).

**Files:**
- Create: `frontend/src/contexts/SessionMapContext.tsx`
- Test: `frontend/__tests__/contexts/SessionMapContext.test.tsx`

- [ ] **Step 1: Write failing test for SessionMapProvider**

```typescript
// frontend/__tests__/contexts/SessionMapContext.test.tsx
import { renderHook, act } from '@testing-library/react'
import { SessionMapProvider, useSessionMap } from '@/contexts/SessionMapContext'
import { createEmptyActiveSession } from '@/types/session'

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <SessionMapProvider>{children}</SessionMapProvider>
)

describe('SessionMapContext', () => {
  it('initializes with empty active sessions map', () => {
    const { result } = renderHook(() => useSessionMap(), { wrapper })
    expect(result.current.activeSessions.size).toBe(0)
    expect(result.current.sessions).toEqual([])
  })

  it('adds an active session', () => {
    const { result } = renderHook(() => useSessionMap(), { wrapper })
    act(() => {
      result.current.addActiveSession('session-123')
    })
    expect(result.current.activeSessions.has('session-123')).toBe(true)
    expect(result.current.activeSessions.get('session-123')?.status).toBe('idle')
  })

  it('updates session status', () => {
    const { result } = renderHook(() => useSessionMap(), { wrapper })
    act(() => {
      result.current.addActiveSession('session-123')
    })
    act(() => {
      result.current.updateSessionState('session-123', { status: 'streaming' })
    })
    expect(result.current.activeSessions.get('session-123')?.status).toBe('streaming')
  })

  it('removes an active session', () => {
    const { result } = renderHook(() => useSessionMap(), { wrapper })
    act(() => {
      result.current.addActiveSession('session-123')
    })
    act(() => {
      result.current.removeActiveSession('session-123')
    })
    expect(result.current.activeSessions.has('session-123')).toBe(false)
  })

  it('marks session as unread', () => {
    const { result } = renderHook(() => useSessionMap(), { wrapper })
    act(() => {
      result.current.addActiveSession('session-123')
    })
    act(() => {
      result.current.updateSessionState('session-123', { hasUnread: true })
    })
    expect(result.current.activeSessions.get('session-123')?.hasUnread).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest __tests__/contexts/SessionMapContext.test.tsx --no-cache`
Expected: FAIL — module not found

- [ ] **Step 3: Implement SessionMapContext**

```typescript
// frontend/src/contexts/SessionMapContext.tsx
'use client'

import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'
import type { ActiveSessionState, RawWidgetData, PendingSessionAction } from '@/types/session'
import { createEmptyActiveSession } from '@/types/session'

// Re-export ChatSession type from existing context for backward compat during migration
export interface ChatSession {
  id: string
  title: string
  preview?: string
  createdAt: string
  updatedAt: string
}

interface SessionMapContextValue {
  // Active session state (in-memory, for open sessions)
  activeSessions: Map<string, ActiveSessionState>
  addActiveSession: (sessionId: string, initialState?: Partial<ActiveSessionState>) => void
  removeActiveSession: (sessionId: string) => void
  updateSessionState: (sessionId: string, updates: Partial<ActiveSessionState>) => void
  getActiveSessionRef: (sessionId: string) => React.MutableRefObject<ActiveSessionState | null>

  // Session metadata (from Supabase, for sidebar list)
  sessions: ChatSession[]
  setSessions: React.Dispatch<React.SetStateAction<ChatSession[]>>
  isLoadingSessions: boolean
  setIsLoadingSessions: React.Dispatch<React.SetStateAction<boolean>>
}

const SessionMapContext = createContext<SessionMapContextValue | null>(null)

export function SessionMapProvider({ children }: { children: React.ReactNode }) {
  const [activeSessions, setActiveSessions] = useState<Map<string, ActiveSessionState>>(new Map())
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [isLoadingSessions, setIsLoadingSessions] = useState(true)

  // Ref map for background stream writing (no re-renders)
  const sessionRefsMap = useRef<Map<string, React.MutableRefObject<ActiveSessionState | null>>>(new Map())

  const addActiveSession = useCallback((sessionId: string, initialState?: Partial<ActiveSessionState>) => {
    const session = { ...createEmptyActiveSession(sessionId), ...initialState }
    setActiveSessions(prev => {
      const next = new Map(prev)
      next.set(sessionId, session)
      return next
    })
    // Also create/update the ref
    if (!sessionRefsMap.current.has(sessionId)) {
      sessionRefsMap.current.set(sessionId, { current: session })
    } else {
      sessionRefsMap.current.get(sessionId)!.current = session
    }
  }, [])

  const removeActiveSession = useCallback((sessionId: string) => {
    setActiveSessions(prev => {
      const next = new Map(prev)
      next.delete(sessionId)
      return next
    })
    sessionRefsMap.current.delete(sessionId)
  }, [])

  const updateSessionState = useCallback((sessionId: string, updates: Partial<ActiveSessionState>) => {
    setActiveSessions(prev => {
      const existing = prev.get(sessionId)
      if (!existing) return prev
      const next = new Map(prev)
      const updated = { ...existing, ...updates }
      next.set(sessionId, updated)
      // Sync to ref
      const ref = sessionRefsMap.current.get(sessionId)
      if (ref) ref.current = updated
      return next
    })
  }, [])

  const getActiveSessionRef = useCallback((sessionId: string) => {
    if (!sessionRefsMap.current.has(sessionId)) {
      sessionRefsMap.current.set(sessionId, { current: null })
    }
    return sessionRefsMap.current.get(sessionId)!
  }, [])

  const value = useMemo(() => ({
    activeSessions,
    addActiveSession,
    removeActiveSession,
    updateSessionState,
    getActiveSessionRef,
    sessions,
    setSessions,
    isLoadingSessions,
    setIsLoadingSessions,
  }), [activeSessions, addActiveSession, removeActiveSession, updateSessionState, getActiveSessionRef, sessions, isLoadingSessions])

  return (
    <SessionMapContext.Provider value={value}>
      {children}
    </SessionMapContext.Provider>
  )
}

export function useSessionMap() {
  const ctx = useContext(SessionMapContext)
  if (!ctx) throw new Error('useSessionMap must be used within SessionMapProvider')
  return ctx
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest __tests__/contexts/SessionMapContext.test.tsx --no-cache`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/contexts/SessionMapContext.tsx frontend/__tests__/contexts/SessionMapContext.test.tsx
git commit -m "feat(sessions): add SessionMapContext for multi-session state"
```

---

### Task 3: SessionControlContext — Navigation and Config

This context holds `visibleSessionId` and session lifecycle actions. Low-frequency updates.

**Files:**
- Create: `frontend/src/contexts/SessionControlContext.tsx`
- Test: `frontend/__tests__/contexts/SessionControlContext.test.tsx`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/__tests__/contexts/SessionControlContext.test.tsx
import { renderHook, act } from '@testing-library/react'
import { SessionControlProvider, useSessionControl } from '@/contexts/SessionControlContext'
import { SessionMapProvider } from '@/contexts/SessionMapContext'

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <SessionMapProvider>
    <SessionControlProvider>{children}</SessionControlProvider>
  </SessionMapProvider>
)

describe('SessionControlContext', () => {
  it('initializes with null visibleSessionId', () => {
    const { result } = renderHook(() => useSessionControl(), { wrapper })
    expect(result.current.visibleSessionId).toBeNull()
  })

  it('creates a new session and sets it visible', () => {
    const { result } = renderHook(() => useSessionControl(), { wrapper })
    act(() => {
      result.current.createNewChat()
    })
    expect(result.current.visibleSessionId).toMatch(/^session-\d+-[a-z0-9]+$/)
  })

  it('switches visible session', () => {
    const { result } = renderHook(() => useSessionControl(), { wrapper })
    act(() => {
      result.current.setVisibleSessionId('session-abc')
    })
    expect(result.current.visibleSessionId).toBe('session-abc')
  })

  it('persists visibleSessionId to localStorage', () => {
    const { result } = renderHook(() => useSessionControl(), { wrapper })
    act(() => {
      result.current.setVisibleSessionId('session-persist')
    })
    expect(localStorage.getItem('pikar_current_session_id')).toBe('session-persist')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest __tests__/contexts/SessionControlContext.test.tsx --no-cache`
Expected: FAIL — module not found

- [ ] **Step 3: Implement SessionControlContext**

```typescript
// frontend/src/contexts/SessionControlContext.tsx
'use client'

import { createContext, useCallback, useContext, useLayoutEffect, useMemo, useState } from 'react'
import { useSessionMap } from './SessionMapContext'
import type { SessionConfig } from '@/types/session'
import { DEFAULT_SESSION_CONFIG } from '@/types/session'

const SESSION_STORAGE_KEY = 'pikar_current_session_id'

function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

interface SessionControlContextValue {
  visibleSessionId: string | null
  setVisibleSessionId: (id: string | null) => void
  sessionRestored: boolean
  config: SessionConfig

  // Lifecycle actions
  createNewChat: () => string
  selectChat: (sessionId: string) => void
  deleteChat: (sessionId: string) => Promise<void>
  clearAllChats: () => Promise<void>
  refreshSessions: () => Promise<void>
  updateSessionTitle: (sessionId: string, title: string) => Promise<void>
  updateSessionPreview: (sessionId: string, preview: string) => Promise<void>
  addSessionOptimistic: (session: { id: string; title: string; preview: string; createdAt: string; updatedAt: string }) => void
}

const SessionControlContext = createContext<SessionControlContextValue | null>(null)

export function SessionControlProvider({ children }: { children: React.ReactNode }) {
  const [visibleSessionId, setVisibleSessionIdRaw] = useState<string | null>(null)
  const [sessionRestored, setSessionRestored] = useState(false)
  const [config, setConfig] = useState<SessionConfig>(DEFAULT_SESSION_CONFIG)
  const { addActiveSession, removeActiveSession, activeSessions, sessions, setSessions, setIsLoadingSessions } = useSessionMap()

  // Restore last session from localStorage before paint
  useLayoutEffect(() => {
    try {
      const stored = localStorage.getItem(SESSION_STORAGE_KEY)
      if (stored) {
        setVisibleSessionIdRaw(stored)
      }
    } catch {
      // localStorage unavailable
    }
    setSessionRestored(true)
  }, [])

  // Fetch session config from backend on mount
  useLayoutEffect(() => {
    fetch('/configuration/session-config')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data) setConfig({ ...DEFAULT_SESSION_CONFIG, ...data })
      })
      .catch(() => {
        // Use defaults on failure
      })
  }, [])

  const setVisibleSessionId = useCallback((id: string | null) => {
    setVisibleSessionIdRaw(id)
    try {
      if (id) {
        localStorage.setItem(SESSION_STORAGE_KEY, id)
      } else {
        localStorage.removeItem(SESSION_STORAGE_KEY)
      }
    } catch {
      // localStorage unavailable
    }
  }, [])

  const createNewChat = useCallback(() => {
    const newId = generateSessionId()
    addActiveSession(newId)
    setVisibleSessionId(newId)
    return newId
  }, [addActiveSession, setVisibleSessionId])

  const selectChat = useCallback((sessionId: string) => {
    // Save scroll position of current visible session
    // (ChatInterface handles this via useEffect cleanup)

    // Mark current visible session's unread as read
    setVisibleSessionId(sessionId)

    // Update lastUpdatedAt for the newly visible session
    if (activeSessions.has(sessionId)) {
      // Will be handled by ChatInterface on mount
    }
  }, [setVisibleSessionId, activeSessions])

  // Note: deleteChat, clearAllChats, refreshSessions, updateSessionTitle, updateSessionPreview,
  // and addSessionOptimistic will be migrated from the existing ChatSessionContext.tsx
  // during Task 7 (provider wiring). For now, stub them.
  const deleteChat = useCallback(async (_sessionId: string) => {
    // TODO: migrate from ChatSessionContext.tsx lines 290-331
  }, [])

  const clearAllChats = useCallback(async () => {
    // TODO: migrate from ChatSessionContext.tsx lines 334-368
  }, [])

  const refreshSessions = useCallback(async () => {
    // TODO: migrate from ChatSessionContext.tsx lines 111-266
  }, [])

  const updateSessionTitle = useCallback(async (_sessionId: string, _title: string) => {
    // TODO: migrate from ChatSessionContext.tsx lines 373-412
  }, [])

  const updateSessionPreview = useCallback(async (_sessionId: string, _preview: string) => {
    // TODO: migrate from ChatSessionContext.tsx lines 415-456
  }, [])

  const addSessionOptimistic = useCallback((_session: { id: string; title: string; preview: string; createdAt: string; updatedAt: string }) => {
    // TODO: migrate from ChatSessionContext.tsx lines 459-465
  }, [])

  const value = useMemo(() => ({
    visibleSessionId,
    setVisibleSessionId,
    sessionRestored,
    config,
    createNewChat,
    selectChat,
    deleteChat,
    clearAllChats,
    refreshSessions,
    updateSessionTitle,
    updateSessionPreview,
    addSessionOptimistic,
  }), [visibleSessionId, setVisibleSessionId, sessionRestored, config, createNewChat, selectChat, deleteChat, clearAllChats, refreshSessions, updateSessionTitle, updateSessionPreview, addSessionOptimistic])

  return (
    <SessionControlContext.Provider value={value}>
      {children}
    </SessionControlContext.Provider>
  )
}

export function useSessionControl() {
  const ctx = useContext(SessionControlContext)
  if (!ctx) throw new Error('useSessionControl must be used within SessionControlProvider')
  return ctx
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx jest __tests__/contexts/SessionControlContext.test.tsx --no-cache`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/contexts/SessionControlContext.tsx frontend/__tests__/contexts/SessionControlContext.test.tsx
git commit -m "feat(sessions): add SessionControlContext for session navigation and config"
```

---

## Wave 2: Core Streaming Engine

### Task 3.5: Extract loadSessionHistory Utility

The `loadHistory` function in `useAgentChat.ts` (lines 136-303) is needed by both the background stream hook and the session preload. Extract it as a standalone async function.

**Files:**
- Create: `frontend/src/lib/sessionHistory.ts`
- Test: `frontend/__tests__/lib/sessionHistory.test.ts`

- [ ] **Step 1: Create the utility**

Extract `useAgentChat.ts` lines 136-303 into a pure async function:

```typescript
// frontend/src/lib/sessionHistory.ts
import { createClient } from '@/lib/supabase/client'
import type { Message } from '@/types/session'

/**
 * Load conversation history for a session from Supabase.
 * Extracted from useAgentChat.ts loadHistory function.
 *
 * Queries session_events, reconstructs Message[] with widgets and traces.
 * Filters out superseded events (rollback support).
 */
export async function loadSessionHistory(
  sessionId: string,
  userId: string,
  appName = 'agents',
): Promise<Message[]> {
  const supabase = createClient()

  const { data: events, error } = await supabase
    .from('session_events')
    .select('event_data, event_index')
    .eq('session_id', sessionId)
    .eq('user_id', userId)
    .eq('app_name', appName)
    .is('superseded_by', null)
    .order('event_index', { ascending: true })

  if (error || !events) return []

  // Reconstruct messages from ADK events
  // (faithful copy of useAgentChat.ts lines 150-295)
  // Key steps:
  // 1. Group events by role (user/model)
  // 2. Extract text from content.parts[].text
  // 3. Extract widgets from content.parts[].functionResponse
  // 4. Extract widgets from top-level widget field
  // 5. Validate widgets via validateWidgetDefinition
  // 6. Extract traces from custom_event fields
  // 7. Build Message objects with all metadata

  const messages: Message[] = []
  // ... (implementation extracted from useAgentChat.ts)

  return messages
}
```

The implementer MUST read `useAgentChat.ts` lines 136-303 and faithfully extract the logic.

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit src/lib/sessionHistory.ts`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/sessionHistory.ts
git commit -m "refactor(sessions): extract loadSessionHistory as standalone utility"
```

---

### Task 4: useBackgroundStream — Ref-Based SSE Manager

This is the core of background streaming. It manages SSE connections that write to `ActiveSessionState` entries via refs, gating side effects based on visibility.

**Files:**
- Create: `frontend/src/hooks/useBackgroundStream.ts`
- Test: `frontend/__tests__/hooks/useBackgroundStream.test.ts`
- Reference: `frontend/src/hooks/useAgentChat.ts` (lines 362-732 — the existing `executeSend` logic to extract from)

- [ ] **Step 1: Extract SSE parsing into standalone module**

Before building the hook, extract the SSE event parsing logic from `useAgentChat.ts` into a pure, testable module. This is the largest and most critical extraction — ~200 lines of dense logic covering widget extraction, trace handling, message accumulation, and metadata parsing.

Create `frontend/src/lib/sseParser.ts`:

```typescript
// frontend/src/lib/sseParser.ts
// Pure functions for parsing SSE events from /a2a/app/run_sse

import type { Message, TraceStep } from '@/types/session'

export interface SSEAccumulator {
  agentText: string
  currentTraces: TraceStep[]
  currentWidget: unknown | null
  agentName: string
  isThinking: boolean
  metadata: Record<string, unknown>
}

export function createAccumulator(): SSEAccumulator {
  return {
    agentText: '',
    currentTraces: [],
    currentWidget: null,
    agentName: '',
    isThinking: false,
    metadata: {},
  }
}

/**
 * Parse a single SSE event and update the accumulator.
 * Returns side-effect descriptors (widget found, focus needed, etc.)
 * without executing them — the caller decides based on visibility.
 *
 * This function is a direct extraction of the logic in
 * useAgentChat.ts lines 437-613 (the onmessage handler body).
 * The implementer MUST copy that logic here faithfully, replacing:
 *   - `setMessages(...)` calls → return updated message in result
 *   - `widgetServiceRef.current.saveWidget(...)` → return { type: 'save_widget', ... }
 *   - `dispatchFocusWidget(...)` → return { type: 'focus_widget', ... }
 *   - `dispatchWorkspaceActivity(...)` → return { type: 'workspace_activity', ... }
 */
export interface ParseResult {
  updatedMessage: Partial<Message> | null
  sideEffects: Array<{
    type: 'save_widget' | 'focus_widget' | 'workspace_activity'
    payload: unknown
  }>
  isComplete: boolean
}

export function parseSSEEvent(
  eventData: string,
  accumulator: SSEAccumulator,
): ParseResult {
  // IMPLEMENTATION: Copy useAgentChat.ts onmessage handler (lines 437-613).
  //
  // Key sections to extract:
  // 1. JSON.parse(event.data) — parse the SSE event payload
  // 2. Extract agent text from content.parts[].text (lines 449-470)
  // 3. Handle widget parts from content.parts[].functionResponse (lines 471-510)
  // 4. Handle top-level widget field (lines 511-530)
  // 5. Widget validation via validateWidgetDefinition (lines 532-546)
  // 6. Trace extraction: tool_call, tool_result, status events (lines 548-569)
  // 7. Director progress tracking (lines 437-445)
  // 8. Metadata extraction (lines 571-590)
  // 9. Agent name from event.author or content.role (lines 591-600)
  //
  // Return the accumulated state changes and side effects,
  // NOT the React state updates. The hook decides when to flush.

  const parsed = JSON.parse(eventData)
  // ... (faithful extraction of the above sections)

  return {
    updatedMessage: null, // populated by extraction
    sideEffects: [],       // populated by extraction
    isComplete: false,     // true when final event received
  }
}
```

The implementer must read `useAgentChat.ts` lines 437-613 in full and copy the parsing logic into this pure function. The key architectural change: instead of calling `setMessages()`, `dispatchFocusWidget()`, or `widgetServiceRef.current.saveWidget()` directly, return descriptors that the hook layer will act on based on visibility.

- [ ] **Step 2: Write test for SSE parser**

```typescript
// frontend/__tests__/lib/sseParser.test.ts
import { createAccumulator, parseSSEEvent } from '@/lib/sseParser'

describe('sseParser', () => {
  it('parses a text event and accumulates agent text', () => {
    const acc = createAccumulator()
    const eventData = JSON.stringify({
      content: { parts: [{ text: 'Hello from agent' }] },
    })
    const result = parseSSEEvent(eventData, acc)
    expect(acc.agentText).toContain('Hello from agent')
    expect(result.sideEffects).toEqual([])
  })

  it('extracts widget from function response part', () => {
    const acc = createAccumulator()
    const eventData = JSON.stringify({
      content: {
        parts: [{
          functionResponse: {
            response: { widget_type: 'chart', data: {} },
          },
        }],
      },
    })
    const result = parseSSEEvent(eventData, acc)
    expect(result.sideEffects.some(e => e.type === 'save_widget')).toBe(true)
  })

  it('tracks trace steps for tool calls', () => {
    const acc = createAccumulator()
    const eventData = JSON.stringify({
      custom_event: { type: 'tool_call', name: 'search', input: {} },
    })
    const result = parseSSEEvent(eventData, acc)
    expect(acc.currentTraces.length).toBeGreaterThan(0)
  })
})
```

- [ ] **Step 3: Run parser tests**

Run: `cd frontend && npx jest __tests__/lib/sseParser.test.ts --no-cache`
Expected: PASS (once implementation is complete)

- [ ] **Step 4: Write test for useBackgroundStream**

```typescript
// frontend/__tests__/hooks/useBackgroundStream.test.ts
import { renderHook, act, waitFor } from '@testing-library/react'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import { SessionMapProvider, useSessionMap } from '@/contexts/SessionMapContext'
import { SessionControlProvider } from '@/contexts/SessionControlContext'
import { useBackgroundStream } from '@/hooks/useBackgroundStream'

jest.mock('@microsoft/fetch-event-source', () => ({
  fetchEventSource: jest.fn(),
}))

const mockFetchEventSource = fetchEventSource as jest.MockedFunction<typeof fetchEventSource>

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <SessionMapProvider>
    <SessionControlProvider>{children}</SessionControlProvider>
  </SessionMapProvider>
)

describe('useBackgroundStream', () => {
  beforeEach(() => {
    mockFetchEventSource.mockReset()
  })

  it('sets session status to streaming when stream starts', async () => {
    // Simulate fetchEventSource resolving immediately
    mockFetchEventSource.mockImplementation(async () => {})

    const { result } = renderHook(() => {
      const stream = useBackgroundStream()
      const map = useSessionMap()
      return { stream, map }
    }, { wrapper })

    // Add a session first
    act(() => {
      result.current.map.addActiveSession('test-session')
    })

    // Start stream
    await act(async () => {
      await result.current.stream.startStream({
        sessionId: 'test-session',
        messageText: 'hello',
        agentMode: 'auto',
        token: null,
        userId: 'user-1',
      })
    })

    // fetchEventSource should have been called
    expect(mockFetchEventSource).toHaveBeenCalledTimes(1)
    expect(mockFetchEventSource).toHaveBeenCalledWith(
      '/a2a/app/run_sse',
      expect.objectContaining({
        method: 'POST',
        openWhenHidden: true,
      })
    )
  })

  it('stopStream aborts the controller and sets status to idle', () => {
    const { result } = renderHook(() => {
      const stream = useBackgroundStream()
      const map = useSessionMap()
      return { stream, map }
    }, { wrapper })

    const mockAbort = jest.fn()

    act(() => {
      result.current.map.addActiveSession('test-session')
      result.current.map.updateSessionState('test-session', {
        status: 'streaming',
        abortController: { abort: mockAbort, signal: new AbortController().signal } as any,
      })
    })

    act(() => {
      result.current.stream.stopStream('test-session')
    })

    expect(mockAbort).toHaveBeenCalled()
  })
})
```

- [ ] **Step 5: Implement useBackgroundStream**

```typescript
// frontend/src/hooks/useBackgroundStream.ts
'use client'

import { useCallback, useRef } from 'react'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import { useSessionMap } from '@/contexts/SessionMapContext'
import { useSessionControl } from '@/contexts/SessionControlContext'
import { createAccumulator, parseSSEEvent } from '@/lib/sseParser'
import type { ActiveSessionState } from '@/types/session'

interface StartStreamOptions {
  sessionId: string
  messageText: string
  agentMode: string
  token: string | null
  userId: string
  onStreamComplete?: (sessionId: string, title: string) => void
}

export function useBackgroundStream() {
  const { getActiveSessionRef, updateSessionState } = useSessionMap()
  const { visibleSessionId } = useSessionControl()
  const visibleSessionIdRef = useRef(visibleSessionId)
  visibleSessionIdRef.current = visibleSessionId

  const startStream = useCallback(async (options: StartStreamOptions) => {
    const { sessionId, messageText, agentMode, token, userId, onStreamComplete } = options
    const sessionRef = getActiveSessionRef(sessionId)
    const abortController = new AbortController()

    updateSessionState(sessionId, {
      status: 'streaming',
      abortController,
      lastUpdatedAt: Date.now(),
    })

    const accumulator = createAccumulator()
    let rafId: number | null = null

    // Flush accumulated state to React (only for visible session)
    const flushToState = () => {
      if (sessionId === visibleSessionIdRef.current) {
        const ref = sessionRef.current
        if (ref) {
          updateSessionState(sessionId, { messages: [...ref.messages] })
        }
      }
      rafId = null
    }

    const scheduleFlush = () => {
      if (rafId === null) {
        rafId = requestAnimationFrame(flushToState)
      }
    }

    try {
      await fetchEventSource('/a2a/app/run_sse', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          session_id: sessionId,
          user_id: userId,
          new_message: { parts: [{ text: messageText }] },
          agent_mode: agentMode,
        }),
        signal: abortController.signal,
        openWhenHidden: true,
        onmessage(event) {
          const result = parseSSEEvent(event.data, accumulator)
          const isVisible = sessionId === visibleSessionIdRef.current

          // Update messages in the ref (always, regardless of visibility)
          if (result.updatedMessage && sessionRef.current) {
            // Apply message update to ref's messages array
            // (merge with last message or append new)
          }

          // Gate side effects based on visibility
          for (const effect of result.sideEffects) {
            if (isVisible) {
              // Execute immediately: dispatchFocusWidget, saveWidget, etc.
              // (import and call the actual functions)
            } else {
              // Queue for later: store in ref's pendingActions/rawWidgets
              if (sessionRef.current) {
                if (effect.type === 'save_widget') {
                  sessionRef.current.rawWidgets.push({
                    widget: effect.payload,
                    messageIndex: sessionRef.current.messages.length - 1,
                  })
                } else {
                  sessionRef.current.pendingActions.push({
                    type: effect.type,
                    payload: effect.payload,
                  })
                }
              }
            }
          }

          // Schedule React state flush for visible session
          if (isVisible) scheduleFlush()
        },
        onclose() {
          if (rafId !== null) cancelAnimationFrame(rafId)
          flushToState()  // Final flush

          const isBackground = sessionId !== visibleSessionIdRef.current
          updateSessionState(sessionId, {
            status: 'idle',
            abortController: null,
            hasUnread: isBackground,
          })
          if (isBackground && onStreamComplete) {
            const title = sessionRef.current?.messages?.[0]?.text?.slice(0, 50) || 'Chat'
            onStreamComplete(sessionId, title)
          }
        },
        onerror(err) {
          if (rafId !== null) cancelAnimationFrame(rafId)
          updateSessionState(sessionId, { status: 'error', abortController: null })
          throw err
        },
      })
    } catch (err) {
      if ((err as Error)?.name === 'AbortError') return
      updateSessionState(sessionId, { status: 'error', abortController: null })
    }
  }, [getActiveSessionRef, updateSessionState])

  const stopStream = useCallback((sessionId: string) => {
    const sessionRef = getActiveSessionRef(sessionId)
    if (sessionRef.current?.abortController) {
      sessionRef.current.abortController.abort()
    }
    updateSessionState(sessionId, { status: 'idle', abortController: null })
  }, [getActiveSessionRef, updateSessionState])

  return { startStream, stopStream }
}
```

- [ ] **Step 3: Run tests**

Run: `cd frontend && npx jest __tests__/hooks/useBackgroundStream.test.ts --no-cache`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useBackgroundStream.ts frontend/__tests__/hooks/useBackgroundStream.test.ts
git commit -m "feat(sessions): add useBackgroundStream for ref-based SSE streaming"
```

---

### Task 5: useStreamCap — Concurrent Stream Limit and LRU Eviction

**Files:**
- Create: `frontend/src/hooks/useStreamCap.ts`
- Test: `frontend/__tests__/hooks/useStreamCap.test.ts`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/__tests__/hooks/useStreamCap.test.ts
import { getEvictionCandidate } from '@/hooks/useStreamCap'
import type { ActiveSessionState } from '@/types/session'
import { createEmptyActiveSession } from '@/types/session'

describe('getEvictionCandidate', () => {
  it('returns null when under cap', () => {
    const sessions = new Map<string, ActiveSessionState>()
    sessions.set('s1', { ...createEmptyActiveSession('s1'), status: 'streaming', lastUpdatedAt: 100 })
    sessions.set('s2', { ...createEmptyActiveSession('s2'), status: 'streaming', lastUpdatedAt: 200 })

    const result = getEvictionCandidate(sessions, 'current-visible', 4)
    expect(result).toBeNull()
  })

  it('returns least recently visible streaming session', () => {
    const sessions = new Map<string, ActiveSessionState>()
    sessions.set('s1', { ...createEmptyActiveSession('s1'), status: 'streaming', lastUpdatedAt: 100 })
    sessions.set('s2', { ...createEmptyActiveSession('s2'), status: 'streaming', lastUpdatedAt: 300 })
    sessions.set('s3', { ...createEmptyActiveSession('s3'), status: 'streaming', lastUpdatedAt: 200 })
    sessions.set('s4', { ...createEmptyActiveSession('s4'), status: 'streaming', lastUpdatedAt: 400 })

    const result = getEvictionCandidate(sessions, 's4', 4)
    expect(result).toBe('s1')  // oldest lastUpdatedAt
  })

  it('never evicts the visible session', () => {
    const sessions = new Map<string, ActiveSessionState>()
    sessions.set('visible', { ...createEmptyActiveSession('visible'), status: 'streaming', lastUpdatedAt: 1 })
    sessions.set('s2', { ...createEmptyActiveSession('s2'), status: 'streaming', lastUpdatedAt: 100 })
    sessions.set('s3', { ...createEmptyActiveSession('s3'), status: 'streaming', lastUpdatedAt: 200 })
    sessions.set('s4', { ...createEmptyActiveSession('s4'), status: 'streaming', lastUpdatedAt: 300 })

    const result = getEvictionCandidate(sessions, 'visible', 4)
    expect(result).toBe('s2')  // visible is protected even though oldest
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx jest __tests__/hooks/useStreamCap.test.ts --no-cache`
Expected: FAIL

- [ ] **Step 3: Implement useStreamCap**

```typescript
// frontend/src/hooks/useStreamCap.ts
import { useCallback } from 'react'
import { useSessionMap } from '@/contexts/SessionMapContext'
import { useSessionControl } from '@/contexts/SessionControlContext'
import { useBackgroundStream } from './useBackgroundStream'
import type { ActiveSessionState } from '@/types/session'

/**
 * Pure function: find the streaming session to evict.
 * Exported for testing.
 */
export function getEvictionCandidate(
  activeSessions: Map<string, ActiveSessionState>,
  visibleSessionId: string | null,
  maxConcurrentStreams: number,
): string | null {
  const streamingSessions = Array.from(activeSessions.entries())
    .filter(([_, s]) => s.status === 'streaming')

  if (streamingSessions.length < maxConcurrentStreams) return null

  // Find LRU streaming session that is NOT the visible one
  const candidates = streamingSessions
    .filter(([id]) => id !== visibleSessionId)
    .sort((a, b) => a[1].lastUpdatedAt - b[1].lastUpdatedAt)

  return candidates.length > 0 ? candidates[0][0] : null
}

/**
 * Hook that enforces the concurrent stream cap.
 * Call `enforceCapBeforeStream()` before starting a new stream.
 * Returns the evicted sessionId or null.
 */
export function useStreamCap() {
  const { activeSessions, updateSessionState } = useSessionMap()
  const { visibleSessionId, config } = useSessionControl()
  const { stopStream } = useBackgroundStream()

  const enforceCapBeforeStream = useCallback((): string | null => {
    const evictId = getEvictionCandidate(
      activeSessions,
      visibleSessionId,
      config.max_concurrent_streams,
    )

    if (evictId) {
      stopStream(evictId)
      updateSessionState(evictId, { status: 'interrupted' })
    }

    return evictId
  }, [activeSessions, visibleSessionId, config.max_concurrent_streams, stopStream, updateSessionState])

  return { enforceCapBeforeStream }
}
```

- [ ] **Step 4: Run tests**

Run: `cd frontend && npx jest __tests__/hooks/useStreamCap.test.ts --no-cache`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useStreamCap.ts frontend/__tests__/hooks/useStreamCap.test.ts
git commit -m "feat(sessions): add useStreamCap with LRU eviction for concurrent stream limit"
```

---

## Wave 3: Integration — Rewire Existing Components

### Task 6: Rewrite useAgentChat as Thin Wrapper

The existing `useAgentChat.ts` (797 lines) is rewritten to delegate to the new contexts and `useBackgroundStream`. It becomes a thin hook that:
1. Gets messages for the visible session from `SessionMapContext`
2. Delegates `sendMessage` to `useBackgroundStream.startStream()`
3. Delegates `stopGeneration` to `useBackgroundStream.stopStream()`
4. Enforces stream cap via `useStreamCap.enforceCapBeforeStream()`

**Files:**
- Modify: `frontend/src/hooks/useAgentChat.ts`
- Reference: `frontend/__tests__/hooks/useAgentChat.test.ts` (existing tests to keep passing)

- [ ] **Step 1: Run existing tests to establish baseline**

Run: `cd frontend && npx jest __tests__/hooks/useAgentChat.test.ts --no-cache`
Note which tests pass/fail. These are the contract to preserve.

- [ ] **Step 2: Rewrite useAgentChat**

Key changes:
- Remove internal `messages` state → read from `useSessionMap().activeSessions.get(visibleSessionId)`
- Remove internal `sessionIdRef` → use `visibleSessionId` from `useSessionControl()`
- Remove internal `abortControllerRef` → managed by `useBackgroundStream`
- Remove internal `isStreaming` state → derive from `activeSessions.get(id)?.status === 'streaming'`
- Remove `executeSend` function body → call `startStream()` from `useBackgroundStream`
- Remove `loadHistory` → move to `useSessionPreload` (Task 13) and on-demand loading in `selectChat`
- Keep `toggleWidgetMinimized`, `pinWidget` → these operate on the visible session's messages
- Keep the return type signature identical for backward compatibility

The hook return shape stays the same:
```typescript
{
  messages, sendMessage, addMessage, isStreaming,
  toggleWidgetMinimized, isLoadingHistory, pinWidget,
  sessionId, getSessionId, stopGeneration
}
```

- [ ] **Step 3: Run existing tests**

Run: `cd frontend && npx jest __tests__/hooks/useAgentChat.test.ts --no-cache`
Expected: All previously-passing tests still pass

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useAgentChat.ts
git commit -m "refactor(sessions): rewrite useAgentChat as thin wrapper over multi-session contexts"
```

---

### Task 7: Migrate Session Logic and Wire Providers

Move the Supabase-facing session logic (fetch, delete, title/preview updates) from `ChatSessionContext.tsx` into the new contexts. Wire the new providers into `layout.tsx`.

**Files:**
- Modify: `frontend/src/contexts/SessionControlContext.tsx` (fill in TODO stubs)
- Modify: `frontend/src/contexts/SessionMapContext.tsx` (add fetchSessions)
- Modify: `frontend/src/app/layout.tsx` (swap providers)
- Modify: `frontend/src/contexts/ChatSessionContext.tsx` (create backward-compat shim)

- [ ] **Step 1: Migrate fetchSessions logic**

Copy the session fetching logic from `ChatSessionContext.tsx` lines 111-266 into a `useFetchSessions` function within `SessionMapContext.tsx` or a separate `useSessionFetcher.ts` utility hook. This logic queries the `sessions` table, extracts titles from first user messages, extracts previews from last agent messages.

- [ ] **Step 2: Migrate delete/clear/update logic**

Fill in the TODO stubs in `SessionControlContext.tsx`:
- `deleteChat`: from `ChatSessionContext.tsx` lines 290-331 (deletes from session_events, workspace_items, sessions)
- `clearAllChats`: from lines 334-368
- `updateSessionTitle`: from lines 373-412
- `updateSessionPreview`: from lines 415-456
- `addSessionOptimistic`: from lines 459-465

- [ ] **Step 3: Create backward-compat shim in ChatSessionContext.tsx**

Replace `ChatSessionContext.tsx` with a thin re-export layer:

```typescript
// frontend/src/contexts/ChatSessionContext.tsx
// BACKWARD COMPAT SHIM — delegates to new split contexts
// Consumers should migrate to useSessionMap() / useSessionControl() directly
'use client'

import { useSessionMap, type ChatSession } from './SessionMapContext'
import { useSessionControl } from './SessionControlContext'

export type { ChatSession }

export function useChatSession() {
  const map = useSessionMap()
  const ctrl = useSessionControl()
  return {
    currentSessionId: ctrl.visibleSessionId,
    setCurrentSessionId: ctrl.setVisibleSessionId,
    sessionRestored: ctrl.sessionRestored,
    sessions: map.sessions,
    isLoadingSessions: map.isLoadingSessions,
    createNewChat: ctrl.createNewChat,
    selectChat: ctrl.selectChat,
    deleteChat: ctrl.deleteChat,
    clearAllChats: ctrl.clearAllChats,
    refreshSessions: ctrl.refreshSessions,
    updateSessionTitle: ctrl.updateSessionTitle,
    updateSessionPreview: ctrl.updateSessionPreview,
    addSessionOptimistic: ctrl.addSessionOptimistic,
    goToHistoryPage: () => { window.location.href = '/dashboard/history' },
  }
}
```

- [ ] **Step 4: Update layout.tsx providers**

Replace `ChatSessionProvider` with `SessionMapProvider` + `SessionControlProvider`:

```tsx
// frontend/src/app/layout.tsx — provider section
<PersonaProvider>
  <SessionMapProvider>
    <SessionControlProvider>
      {children}
      <Toaster position="top-right" richColors closeButton duration={5000} />
    </SessionControlProvider>
  </SessionMapProvider>
</PersonaProvider>
```

- [ ] **Step 5: Verify app compiles and existing behavior works**

Run: `cd frontend && npm run build`
Expected: Build succeeds (backward-compat shim keeps all consumers working)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/contexts/ frontend/src/app/layout.tsx
git commit -m "feat(sessions): wire new providers, migrate session logic, add backward-compat shim"
```

---

### Task 8: Update PersonaDashboardLayout — Remove Key Prop

**Files:**
- Modify: `frontend/src/components/dashboard/PersonaDashboardLayout.tsx`

- [ ] **Step 1: Remove the key prop from ChatInterface**

At line 268, change:
```tsx
// BEFORE
<ChatInterface
    key={effectiveSessionId ?? 'new'}
    initialSessionId={effectiveSessionId}
```

To:
```tsx
// AFTER
<ChatInterface
    initialSessionId={effectiveSessionId}
```

- [ ] **Step 2: Update context imports**

Replace `useChatSession()` with the appropriate new hooks:
- For `currentSessionId` → `useSessionControl().visibleSessionId`
- For `sessions`, callback management → `useSessionControl()` methods
- For `addSessionOptimistic` → `useSessionControl().addSessionOptimistic`

Keep the `handleSessionStarted` and `handleAgentResponse` callbacks — these update session metadata in `SessionMapContext` and should fire for all sessions (visible or background).

- [ ] **Step 3: Verify page loads and chat works**

Run: `cd frontend && npm run dev`
Navigate to a persona page. Send a message. Verify streaming works.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dashboard/PersonaDashboardLayout.tsx
git commit -m "feat(sessions): remove ChatInterface key prop, enable persistent rendering"
```

---

### Task 9: Update ChatInterface — Thin Renderer with Scroll Preservation

**Files:**
- Modify: `frontend/src/components/chat/ChatInterface.tsx`

- [ ] **Step 1: Add scroll position save/restore**

Add a `useEffect` that:
- On `visibleSessionId` change (cleanup phase): captures current `scrollTop` from the messages container and saves to `updateSessionState(prevSessionId, { scrollTop })`
- On `visibleSessionId` change (effect phase): restores `scrollTop` from `activeSessions.get(newSessionId)?.scrollTop` via `requestAnimationFrame`

```typescript
const messagesContainerRef = useRef<HTMLDivElement>(null)
const prevVisibleRef = useRef(visibleSessionId)

useEffect(() => {
  const prev = prevVisibleRef.current
  prevVisibleRef.current = visibleSessionId

  // Restore scroll for newly visible session
  if (visibleSessionId && messagesContainerRef.current) {
    const session = activeSessions.get(visibleSessionId)
    if (session && session.scrollTop >= 0) {
      requestAnimationFrame(() => {
        if (messagesContainerRef.current) {
          messagesContainerRef.current.scrollTop = session.scrollTop
        }
      })
    } else {
      // Default: scroll to bottom
      messagesEndRef.current?.scrollIntoView({ behavior: 'instant' })
    }
  }

  // Save scroll for previous session (cleanup runs before effect)
  return () => {
    if (prev && messagesContainerRef.current) {
      updateSessionState(prev, { scrollTop: messagesContainerRef.current.scrollTop })
    }
  }
}, [visibleSessionId])
```

- [ ] **Step 2: Update useRealtimeSession to switch channels dynamically**

Currently `useRealtimeSession` subscribes to a fixed session channel. Update it to unsubscribe from the old channel and subscribe to the new one when `visibleSessionId` changes. The hook likely already does this if its `sessionId` prop changes — verify and adjust.

- [ ] **Step 3: Update usePresence to switch channels dynamically**

Same as above for `usePresence` — it needs to leave the old `chat:${oldSessionId}` channel and join `chat:${newSessionId}` on switch.

- [ ] **Step 4: Mark hasUnread as false when session becomes visible**

```typescript
useEffect(() => {
  if (visibleSessionId) {
    const session = activeSessions.get(visibleSessionId)
    if (session?.hasUnread) {
      updateSessionState(visibleSessionId, { hasUnread: false, lastUpdatedAt: Date.now() })
    }
  }
}, [visibleSessionId])
```

- [ ] **Step 5: Process pending actions on session switch**

When a session with `rawWidgets` or `pendingActions` becomes visible, flush them:

```typescript
useEffect(() => {
  if (!visibleSessionId) return
  const session = activeSessions.get(visibleSessionId)
  if (!session) return

  // Process deferred widgets
  if (session.rawWidgets.length > 0) {
    setTimeout(() => {
      // Validate and save each widget
      for (const raw of session.rawWidgets) {
        // validateWidgetDefinition + widgetService.saveWidget
      }
      updateSessionState(visibleSessionId, { rawWidgets: [] })
    }, 0)
  }

  // Flush pending actions (focus last widget, fire workspace activity)
  if (session.pendingActions.length > 0) {
    const lastFocus = [...session.pendingActions].reverse().find(a => a.type === 'focus_widget')
    if (lastFocus) {
      dispatchFocusWidget(lastFocus.payload)
    }
    updateSessionState(visibleSessionId, { pendingActions: [] })
  }
}, [visibleSessionId])
```

- [ ] **Step 6: Verify chat works with session switching**

Run: `cd frontend && npm run dev`
1. Start a conversation
2. The existing behavior should work as before
3. (Multi-session UI comes in Wave 4)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/chat/ChatInterface.tsx
git commit -m "feat(sessions): update ChatInterface as thin renderer with scroll preservation"
```

---

## Wave 4: Consumer Migration

### Task 10: Update SessionList and Remove useSessionHistory

**Files:**
- Modify: `frontend/src/components/chat/SessionList.tsx`
- Delete: `frontend/src/hooks/useSessionHistory.ts`

- [ ] **Step 1: Update SessionList to consume SessionMapContext**

Replace:
```typescript
const { sessions, isLoading, deleteSession } = useSessionHistory(userId)
```
With:
```typescript
const { sessions, isLoadingSessions } = useSessionMap()
const { deleteChat, visibleSessionId } = useSessionControl()
```

Update the delete handler to use `deleteChat()` instead of `deleteSession()`.

- [ ] **Step 2: Add active session grouping**

Split sessions into two groups:
```typescript
const { activeSessions } = useSessionMap()

const activeSessionIds = new Set(
  Array.from(activeSessions.entries())
    .filter(([_, s]) => s.status === 'streaming' || s.hasUnread)
    .map(([id]) => id)
)

const activeSorted = sessions.filter(s => activeSessionIds.has(s.id))
const restSorted = sessions.filter(s => !activeSessionIds.has(s.id))
```

Render with an "Active" divider when `activeSorted.length > 0`.

- [ ] **Step 3: Delete useSessionHistory.ts**

```bash
git rm frontend/src/hooks/useSessionHistory.ts
```

- [ ] **Step 4: Verify SessionList renders correctly**

Run: `cd frontend && npm run dev`
Check sidebar shows sessions, can select/delete.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/chat/SessionList.tsx
git rm frontend/src/hooks/useSessionHistory.ts
git commit -m "feat(sessions): update SessionList to use SessionMapContext, remove useSessionHistory"
```

---

### Task 11: Update ActiveWorkspace — Deep Consumer Migration

**Files:**
- Modify: `frontend/src/components/dashboard/ActiveWorkspace.tsx`

- [ ] **Step 1: Replace all currentSessionId references**

There are 10+ references to `currentSessionId` from `useChatSession()`. Replace with `visibleSessionId` from `useSessionControl()`.

Key areas:
- Widget filtering by session
- `workspace_items` queries
- `WORKSPACE_ACTIVITY_EVENT` handler — filter events for visible session only
- `WIDGET_FOCUS_EVENT` handler — only focus if from visible session

- [ ] **Step 2: Verify workspace displays correctly**

Run: `cd frontend && npm run dev`
Send a message that produces a widget. Verify it appears in the workspace panel.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dashboard/ActiveWorkspace.tsx
git commit -m "feat(sessions): update ActiveWorkspace to use visibleSessionId from new context"
```

---

### Task 12: Update Remaining Consumers

**Files:**
- Modify: `frontend/src/components/vault/VaultInterface.tsx`
- Modify: `frontend/src/app/dashboard/history/page.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Update VaultInterface**

Replace `useContext(ChatSessionContext)` with appropriate new hooks. The VaultInterface likely just needs `visibleSessionId` to scope its queries.

- [ ] **Step 2: Update history page**

Replace `useChatSession()` with `useSessionControl()` / `useSessionMap()` as needed.

- [ ] **Step 3: Update Sidebar**

Sidebar currently reads `sessionId` from URL search params. Evaluate:
- If URL-based routing is still needed (for deep links), keep it and sync with `visibleSessionId` via a `useEffect`
- If redundant, consume `useSessionControl().visibleSessionId` directly

- [ ] **Step 4: Verify all pages compile and work**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/vault/VaultInterface.tsx frontend/src/app/dashboard/history/page.tsx frontend/src/components/layout/Sidebar.tsx
git commit -m "feat(sessions): migrate remaining consumers to new session contexts"
```

---

## Wave 5: UI Features

### Task 13: SessionStatusBadge Component

**Files:**
- Create: `frontend/src/components/chat/SessionStatusBadge.tsx`

- [ ] **Step 1: Implement status badge**

```tsx
// frontend/src/components/chat/SessionStatusBadge.tsx
'use client'

import type { SessionStatus } from '@/types/session'

interface SessionStatusBadgeProps {
  status: SessionStatus
  hasUnread: boolean
}

export function SessionStatusBadge({ status, hasUnread }: SessionStatusBadgeProps) {
  if (status === 'streaming') {
    return (
      <span className="relative flex h-2.5 w-2.5">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500" />
      </span>
    )
  }

  if (hasUnread) {
    return <span className="inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
  }

  if (status === 'interrupted') {
    return <span className="inline-flex rounded-full h-2 w-2 bg-zinc-400" />
  }

  return null
}
```

- [ ] **Step 2: Integrate into SessionList**

In `SessionList.tsx`, add `<SessionStatusBadge>` next to each session item, reading status from `activeSessions.get(session.id)`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/chat/SessionStatusBadge.tsx frontend/src/components/chat/SessionList.tsx
git commit -m "feat(sessions): add SessionStatusBadge with streaming/unread/interrupted indicators"
```

---

### Task 14: NewChatButton Component

**Files:**
- Create: `frontend/src/components/chat/NewChatButton.tsx`

- [ ] **Step 1: Implement NewChatButton**

```tsx
// frontend/src/components/chat/NewChatButton.tsx
'use client'

import { useEffect } from 'react'
import { useSessionControl } from '@/contexts/SessionControlContext'
import { Plus } from 'lucide-react'

export function NewChatButton() {
  const { createNewChat } = useSessionControl()

  // Alt+N / Option+N keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.altKey && e.key.toLowerCase() === 'n') {
        e.preventDefault()
        createNewChat()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [createNewChat])

  return (
    <button
      onClick={() => createNewChat()}
      className="flex items-center gap-2 w-full px-3 py-2 text-sm font-medium text-zinc-100 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
      title="New Chat (Alt+N)"
    >
      <Plus className="h-4 w-4" />
      New Chat
    </button>
  )
}
```

- [ ] **Step 2: Add to SessionList header**

Place `<NewChatButton />` at the top of the sidebar session list.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/chat/NewChatButton.tsx frontend/src/components/chat/SessionList.tsx
git commit -m "feat(sessions): add NewChatButton with Alt+N keyboard shortcut"
```

---

### Task 15: SessionToast — Background Completion Notification

**Files:**
- Create: `frontend/src/components/chat/SessionToast.tsx`
- Modify: `frontend/src/hooks/useBackgroundStream.ts`

- [ ] **Step 1: Create toast trigger utility**

```typescript
// frontend/src/components/chat/SessionToast.tsx
'use client'

import { toast } from 'sonner'

let activeToastCount = 0

export function showSessionReadyToast(
  sessionId: string,
  sessionTitle: string,
  onNavigate: (sessionId: string) => void,
) {
  // Don't show if tab is hidden
  if (document.visibilityState === 'hidden') return

  // Cap at 2 individual toasts, then show summary
  activeToastCount++

  if (activeToastCount > 2) {
    // Dismiss existing toasts and show summary
    toast.dismiss()
    toast(`${activeToastCount} sessions ready`, {
      duration: 5000,
      onDismiss: () => { activeToastCount = 0 },
    })
    return
  }

  toast(
    `${sessionTitle} — Response ready`,
    {
      duration: 5000,
      action: {
        label: 'View',
        onClick: () => onNavigate(sessionId),
      },
      onDismiss: () => {
        activeToastCount = Math.max(0, activeToastCount - 1)
      },
    },
  )
}
```

- [ ] **Step 2: Wire into useBackgroundStream onStreamComplete**

In `useBackgroundStream.ts`, call `showSessionReadyToast()` when a background stream completes and the session is not visible.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/chat/SessionToast.tsx frontend/src/hooks/useBackgroundStream.ts
git commit -m "feat(sessions): add toast notification for background stream completion"
```

---

### Task 16: useSessionPreload — Startup Preload

**Files:**
- Create: `frontend/src/hooks/useSessionPreload.ts`

- [ ] **Step 1: Implement preload hook**

```typescript
// frontend/src/hooks/useSessionPreload.ts
'use client'

import { useEffect, useRef } from 'react'
import { useSessionMap } from '@/contexts/SessionMapContext'

/**
 * On mount, preloads message history for the N most recent sessions
 * into activeSessions so the first switches are instant.
 */
export function useSessionPreload(maxPreload = 3) {
  const { sessions, addActiveSession, activeSessions } = useSessionMap()
  const hasPreloaded = useRef(false)

  useEffect(() => {
    if (hasPreloaded.current) return
    if (sessions.length === 0) return

    hasPreloaded.current = true

    const toPreload = sessions
      .slice(0, maxPreload)
      .filter(s => !activeSessions.has(s.id))

    if (toPreload.length === 0) return

    // Load history for each in parallel
    Promise.all(
      toPreload.map(async (session) => {
        try {
          // Fetch session events from Supabase
          // (extract loadHistory logic from useAgentChat.ts lines 136-303)
          const messages = await loadSessionHistory(session.id)
          addActiveSession(session.id, { messages })
        } catch {
          // Silently fail — session will load on demand
        }
      })
    )
  }, [sessions, addActiveSession, activeSessions, maxPreload])
}
```

Note: `loadSessionHistory` needs to be extracted from `useAgentChat.ts` lines 136-303 into a standalone async function (e.g., in `frontend/src/lib/sessionHistory.ts`) that both the preloader and the on-demand loader can use.

- [ ] **Step 2: Add to layout or PersonaDashboardLayout**

Call `useSessionPreload()` in `PersonaDashboardLayout` after the providers are set up.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useSessionPreload.ts
git commit -m "feat(sessions): add startup preload for 3 most recent sessions"
```

---

## Wave 6: Backend Config

### Task 17: Session Config Admin Endpoint

**Files:**
- Modify: `app/routers/configuration.py`
- Test: `tests/unit/test_session_config.py`

- [ ] **Step 1: Write failing test**

Note: The `user_configurations` table has `user_id UUID NOT NULL REFERENCES auth.users(id)`, so we cannot use a string like `'system'`. Instead, the endpoint reads config from the **authenticated user's own** `user_configurations` row, or falls back to hardcoded defaults. Admins set org-wide defaults by storing config under their own user_id, which the frontend fetches. If no row exists (most users), defaults are returned.

```python
# tests/unit/test_session_config.py
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.fast_api_app import app
from app.routers.onboarding import get_current_user_id

# Override auth dependency for testing
app.dependency_overrides[get_current_user_id] = lambda: "test-user-id"

client = TestClient(app)


def test_session_config_returns_defaults():
    """GET /configuration/session-config returns defaults when no DB row exists."""
    response = client.get("/configuration/session-config")
    assert response.status_code == 200
    data = response.json()
    assert data["max_concurrent_streams"] == 4
    assert data["memory_eviction_minutes"] == 30
    assert data["max_active_sessions_in_memory"] == 20


def teardown_module():
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_session_config.py -v`
Expected: FAIL — 404 (endpoint doesn't exist)

- [ ] **Step 3: Add endpoint to configuration router**

The endpoint does NOT require a sentinel `user_id = 'system'` row. It queries the authenticated user's config first, then falls back to hardcoded defaults. This avoids the FK constraint issue entirely.

Add to `app/routers/configuration.py`:

```python
class SessionConfigResponse(BaseModel):
    """Session configuration for frontend."""
    max_concurrent_streams: int = 4
    memory_eviction_minutes: int = 30
    max_active_sessions_in_memory: int = 20


@router.get("/session-config", response_model=SessionConfigResponse)
@limiter.limit(get_user_persona_limit)
async def get_session_config(
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
):
    """Get session configuration (user-configurable, falls back to defaults).

    Reads from user_configurations where config_key='sessions'.
    Returns hardcoded defaults if no row exists for this user.
    """
    defaults = SessionConfigResponse()
    try:
        client = get_service_client()
        result = (
            client.table("user_configurations")
            .select("config_value")
            .eq("user_id", current_user_id)
            .eq("config_key", "sessions")
            .limit(1)
            .execute()
        )
        if result.data:
            import json
            config_data = json.loads(result.data[0]["config_value"])
            return SessionConfigResponse(**{**defaults.model_dump(), **config_data})
    except Exception:
        pass
    return defaults
```

Also add `"sessions"` to the `_ALLOWED_CONFIG_KEYS` set (line 460) so admins can save it via the existing `save-user-config` endpoint.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_session_config.py -v`
Expected: PASS

- [ ] **Step 5: Update frontend config fetch URL**

In `SessionControlContext.tsx`, update the fetch URL from `/api/admin/config/sessions` to `/configuration/session-config` (matching the existing router prefix pattern).

- [ ] **Step 6: Commit**

```bash
git add app/routers/configuration.py tests/unit/test_session_config.py frontend/src/contexts/SessionControlContext.tsx
git commit -m "feat(sessions): add session config endpoint with admin-configurable defaults"
```

---

## Wave 7: Memory Management

### Task 18: Idle Session Eviction and Memory Cleanup

**Files:**
- Create: `frontend/src/hooks/useSessionMemoryManager.ts`

- [ ] **Step 1: Implement memory manager**

```typescript
// frontend/src/hooks/useSessionMemoryManager.ts
'use client'

import { useEffect } from 'react'
import { useSessionMap } from '@/contexts/SessionMapContext'
import { useSessionControl } from '@/contexts/SessionControlContext'

/**
 * Periodically evicts idle sessions from memory to prevent unbounded growth.
 * Runs every 5 minutes.
 */
export function useSessionMemoryManager() {
  const { activeSessions, removeActiveSession } = useSessionMap()
  const { visibleSessionId, config } = useSessionControl()

  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now()
      const evictionThreshold = config.memory_eviction_minutes * 60 * 1000

      // Find idle sessions past eviction threshold
      const candidates = Array.from(activeSessions.entries())
        .filter(([id, s]) =>
          id !== visibleSessionId &&
          s.status === 'idle' &&
          !s.hasUnread &&
          (now - s.lastUpdatedAt) > evictionThreshold
        )

      for (const [id] of candidates) {
        removeActiveSession(id)
      }

      // Hard cap enforcement
      if (activeSessions.size > config.max_active_sessions_in_memory) {
        const sortedIdle = Array.from(activeSessions.entries())
          .filter(([id, s]) => id !== visibleSessionId && s.status === 'idle')
          .sort((a, b) => a[1].lastUpdatedAt - b[1].lastUpdatedAt)

        const excess = activeSessions.size - config.max_active_sessions_in_memory
        for (let i = 0; i < Math.min(excess, sortedIdle.length); i++) {
          removeActiveSession(sortedIdle[i][0])
        }
      }
    }, 5 * 60 * 1000)  // Run every 5 minutes

    return () => clearInterval(interval)
  }, [activeSessions, visibleSessionId, config, removeActiveSession])
}
```

- [ ] **Step 2: Add to layout**

Call `useSessionMemoryManager()` in the same location as `useSessionPreload()`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useSessionMemoryManager.ts
git commit -m "feat(sessions): add idle session eviction and memory cap enforcement"
```

---

## Wave 8: Final Integration and Cleanup

### Task 19: Remove Backward Compat Shim and Final Cleanup

Once all consumers are migrated, the backward-compat shim in `ChatSessionContext.tsx` can be simplified or removed.

**Files:**
- Modify: `frontend/src/contexts/ChatSessionContext.tsx`

- [ ] **Step 1: Audit all imports of useChatSession**

Run: `grep -r "useChatSession\|ChatSessionContext\|ChatSessionProvider" frontend/src/ --include="*.tsx" --include="*.ts" -l`

Verify all consumers use the new hooks directly. If any still use the shim, migrate them.

- [ ] **Step 2: Simplify or remove the shim**

If all consumers are migrated, delete the file and update any remaining imports. If some still depend on it, keep it as a thin re-export.

- [ ] **Step 3: Run full test suite**

Run: `cd frontend && npm run build && npx jest --no-cache`
Expected: Build succeeds, all tests pass

- [ ] **Step 4: Manual smoke test**

1. Open the app
2. Start a conversation — verify streaming works
3. Click "New Chat" — verify new empty session appears
4. Send a message in the new session — verify streaming starts
5. Switch back to the first session while second is streaming — verify first session's messages are intact
6. Wait for second session to finish — verify toast appears, sidebar badge shows
7. Switch to second session — verify response is there, toast/badge clear
8. Open 5+ streams to test cap eviction — verify oldest background stream gets interrupted

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat(sessions): finalize multi-session parallel chat — cleanup and integration"
```
