'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
} from 'react'
import type { SessionConfig } from '@/types/session'
import { DEFAULT_SESSION_CONFIG } from '@/types/session'
import { useSessionMap, type ChatSession } from './SessionMapContext'
import { createClient } from '@/lib/supabase/client'
import { listUserSessions } from '@/services/sessions'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const STORAGE_KEY = 'pikar_current_session_id'
const OPEN_TABS_STORAGE_KEY = 'pikar_open_tab_ids'
// Multi-session tab caps. Exported so `ChatSessionContext.useChatSession()`
// can read tier and push the right value into provider state via setTabCap.
export const TAB_CAP_FREE = 5
export const TAB_CAP_PAID = 8
const AGENTS_APP_NAME = 'agents'

// ---------------------------------------------------------------------------
// TabCapReachedError — thrown by openTab when openTabIds.length >= tabCap.
// Callers (e.g. selectChat, the future TabStrip) should catch this and
// surface a user-facing message ("Close a tab before opening a new one").
// ---------------------------------------------------------------------------
export class TabCapReachedError extends Error {
  constructor(public cap: number) {
    super(`Tab cap reached (${cap}). Close a tab before opening a new one.`)
    this.name = 'TabCapReachedError'
  }
}

// ---------------------------------------------------------------------------
// Context shape
// ---------------------------------------------------------------------------
interface SessionControlContextValue {
  visibleSessionId: string | null
  setVisibleSessionId: (id: string | null) => void
  sessionRestored: boolean
  config: SessionConfig

  createNewChat: () => string
  selectChat: (sessionId: string) => void

  deleteChat: (sessionId: string) => Promise<void>
  clearAllChats: () => Promise<void>
  refreshSessions: () => Promise<void>
  updateSessionTitle: (sessionId: string, title: string) => Promise<void>
  updateSessionPreview: (sessionId: string, preview: string) => Promise<void>
  addSessionOptimistic: (session: ChatSession) => void

  // ----- Multi-session tabs (FEATURE-MULTI-SESSION-TABS) -----
  /** Ordered list of session ids the user has open as tabs. Persisted to
   *  localStorage under `pikar_open_tab_ids` and restored on mount. */
  openTabIds: string[]
  /** Maximum concurrent tabs. Default = TAB_CAP_FREE (5). The dashboard tree
   *  pushes a tier-derived value via `setTabCap` (free=5, paid=8) — see
   *  ChatSessionContext.useChatSession. */
  tabCap: number
  /** Setter so `useChatSession()` (which is the dashboard-only consumer) can
   *  push the tier-derived cap into provider state without forcing the
   *  provider itself to call `useSubscription()` (provider-tree mismatch:
   *  SessionControlProvider lives at the root, SubscriptionProvider lives at
   *  the dashboard layout — calling useSubscription() here would throw). */
  setTabCap: (cap: number) => void
  /** Open `sessionId` as a tab (idempotent on duplicate add) and make it
   *  visible. Throws `TabCapReachedError` when at cap. */
  openTab: (sessionId: string) => void
  /** Close a tab. Removes from `openTabIds` AND from the in-memory
   *  `activeSessions` map. If the closed tab was visible, the most-recently
   *  opened remaining tab is promoted; if it was the LAST tab, a fresh chat
   *  is created so the chat panel never empties. Does NOT delete the session
   *  from Supabase. */
  closeTab: (sessionId: string) => void
}

const SessionControlContext = createContext<SessionControlContextValue | null>(
  null,
)

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useSessionControl(): SessionControlContextValue {
  const ctx = useContext(SessionControlContext)
  if (!ctx) {
    throw new Error(
      'useSessionControl must be used within a SessionControlProvider',
    )
  }
  return ctx
}

// ---------------------------------------------------------------------------
// Session ID generation
// ---------------------------------------------------------------------------
function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

// ---------------------------------------------------------------------------
// Helper: extract a readable title from a session ID timestamp
// ---------------------------------------------------------------------------
function extractTitleFromSessionId(sessionId: string): string {
  const match = sessionId.match(/session-(\d+)/)
  if (match) {
    const timestamp = parseInt(match[1], 10)
    const date = new Date(timestamp)
    if (!isNaN(date.getTime())) {
      return `Chat from ${date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year:
          date.getFullYear() !== new Date().getFullYear()
            ? 'numeric'
            : undefined,
      })}`
    }
  }
  return 'Untitled Chat'
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
interface SessionControlProviderProps {
  children: React.ReactNode
}

export function SessionControlProvider({
  children,
}: SessionControlProviderProps) {
  const {
    addActiveSession,
    removeActiveSession,
    sessions,
    setSessions,
    setIsLoadingSessions,
  } = useSessionMap()

  const supabase = useMemo(() => createClient(), [])

  // ---- Core state ----
  const [visibleSessionId, setVisibleSessionIdRaw] = useState<string | null>(
    null,
  )
  const [sessionRestored, setSessionRestored] = useState(false)
  const [config, setConfig] = useState<SessionConfig>(DEFAULT_SESSION_CONFIG)
  const [userId, setUserId] = useState<string | null>(null)

  // ---- Multi-session tab state (FEATURE-MULTI-SESSION-TABS) ----
  // openTabIds is a string[] of session ids open as tabs. Persisted to
  // localStorage under `pikar_open_tab_ids` and restored on mount.
  // tabCap defaults to TAB_CAP_FREE so the provider is mountable at the
  // root layout where `SubscriptionProvider` is NOT available. The
  // tier-derived override is pushed in via `setTabCap` from `useChatSession()`
  // (which only runs inside the dashboard tree).
  const [openTabIds, setOpenTabIds] = useState<string[]>([])
  const [tabCap, setTabCap] = useState<number>(TAB_CAP_FREE)

  // Track whether we've done initial load
  const initializedRef = useRef(false)

  // ------------------------------------------------------------------
  // localStorage restore — useLayoutEffect runs synchronously before paint
  // ------------------------------------------------------------------
  useLayoutEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        setVisibleSessionIdRaw(stored)
      }
    } catch {
      // localStorage may be unavailable (SSR, privacy mode, etc.)
    }
    setSessionRestored(true)
  }, [])

  // ------------------------------------------------------------------
  // Restore openTabIds from localStorage on mount
  // (FEATURE-MULTI-SESSION-TABS — pikar_open_tab_ids)
  // ------------------------------------------------------------------
  useLayoutEffect(() => {
    try {
      const stored = localStorage.getItem(OPEN_TABS_STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        if (
          Array.isArray(parsed) &&
          parsed.every((x) => typeof x === 'string')
        ) {
          setOpenTabIds(parsed)
        }
      }
    } catch {
      // localStorage unavailable or JSON malformed — start with empty list
    }
  }, [])

  // ------------------------------------------------------------------
  // Persist openTabIds to localStorage on every change
  // ------------------------------------------------------------------
  useEffect(() => {
    try {
      if (openTabIds.length === 0) {
        localStorage.removeItem(OPEN_TABS_STORAGE_KEY)
      } else {
        localStorage.setItem(OPEN_TABS_STORAGE_KEY, JSON.stringify(openTabIds))
      }
    } catch {
      // localStorage unavailable
    }
  }, [openTabIds])

  // ------------------------------------------------------------------
  // Cross-browser-tab sync — HOTFIX-06 success criterion 4
  //
  // The `storage` event fires on `window` in OTHER same-origin tabs ONLY
  // when localStorage is mutated. Last-write-wins is acceptable per the
  // ROADMAP — we just need to keep this tab's React state in sync with
  // localStorage so the workspace and chat panel re-query for the new
  // session_id rather than displaying stale data keyed on the old one.
  //
  // Do NOT call `setVisibleSessionId` (the persisting setter) from this
  // handler — it would write to localStorage and risk a feedback loop.
  // Use the raw setter so we update React state without touching storage.
  // ------------------------------------------------------------------
  useEffect(() => {
    const handleStorage = (e: StorageEvent) => {
      if (e.key !== STORAGE_KEY) return
      if (e.storageArea !== window.localStorage) return
      // e.newValue is null when the key is removed (e.g. logout in other tab)
      setVisibleSessionIdRaw(e.newValue)
    }
    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }, [])

  // ------------------------------------------------------------------
  // localStorage persist — write whenever visibleSessionId changes
  // ------------------------------------------------------------------
  const setVisibleSessionId = useCallback((id: string | null) => {
    setVisibleSessionIdRaw(id)
    try {
      if (id === null) {
        localStorage.removeItem(STORAGE_KEY)
      } else {
        localStorage.setItem(STORAGE_KEY, id)
      }
    } catch {
      // localStorage may be unavailable
    }
  }, [])

  // ------------------------------------------------------------------
  // Get current user from Supabase auth
  // ------------------------------------------------------------------
  useEffect(() => {
    const getUser = async () => {
      const { data } = await supabase.auth.getUser()
      if (data.user) {
        setUserId(data.user.id)
      }
    }
    getUser()
  }, [supabase])

  // Config: uses DEFAULT_SESSION_CONFIG from @/types/session.
  // Remote config fetch will be enabled once the backend endpoint is deployed.

  // ------------------------------------------------------------------
  // createNewChat
  //
  // Generates a fresh session id, warms the in-memory map, makes it visible,
  // and pushes the new id into `openTabIds` so the multi-session tab strip
  // (Plan 03) reflects the new chat. No cap check here — `createNewChat` is
  // also the LAST-RESORT fallback when `closeTab` empties the list, so we
  // MUST be able to seed a fresh tab even if stale ids in localStorage
  // exceeded the cap. The next user-initiated `openTab` will hit the cap
  // normally.
  // ------------------------------------------------------------------
  const createNewChat = useCallback((): string => {
    const newId = generateSessionId()
    addActiveSession(newId, { skipHistoryRestore: true })
    setOpenTabIds((prev) => {
      if (prev.includes(newId)) return prev
      return [...prev, newId]
    })
    setVisibleSessionId(newId)
    return newId
  }, [addActiveSession, setVisibleSessionId])

  // ------------------------------------------------------------------
  // openTab — open a session as a tab and make it visible.
  //
  // Idempotent on duplicate add (already-open id just becomes visible).
  // Throws TabCapReachedError when openTabIds is at cap; the caller (e.g.
  // selectChat or the future TabStrip) is responsible for surfacing a
  // user-facing toast. We read `openTabIds` from the render's closure for
  // the cap check (and the duplicate check) rather than throwing inside a
  // setState updater — React may re-run updaters during reconciliation, so
  // a throw inside the updater can fire from an unexpected stack frame.
  // ------------------------------------------------------------------
  const openTab = useCallback(
    (sessionId: string) => {
      // Already open — just make it visible (idempotent, no list mutation).
      if (openTabIds.includes(sessionId)) {
        addActiveSession(sessionId)
        setVisibleSessionId(sessionId)
        return
      }

      // At cap — throw synchronously BEFORE any state mutation. The thrown
      // error propagates to the caller (Plan 03 TabStrip will catch it and
      // surface a toast).
      if (openTabIds.length >= tabCap) {
        throw new TabCapReachedError(tabCap)
      }

      // Append to the list, warm the active session map, make visible.
      setOpenTabIds((prev) =>
        prev.includes(sessionId) ? prev : [...prev, sessionId],
      )
      addActiveSession(sessionId)
      setVisibleSessionId(sessionId)
    },
    [openTabIds, tabCap, addActiveSession, setVisibleSessionId],
  )

  // ------------------------------------------------------------------
  // closeTab — close a tab.
  //
  // Removes from openTabIds and from the in-memory activeSessions map.
  // Does NOT delete the session from Supabase — sessions remain in the
  // /sessions list so the user can reopen via the chat history dropdown.
  //
  // If the closed tab was the visible one, the most-recently-opened
  // remaining tab is promoted to visible. If the closed tab was the LAST
  // remaining tab, createNewChat() is called so the chat panel never
  // empties (locked decision per CONTEXT.md).
  //
  // Transient-write note: the closeTab → createNewChat sequence transiently
  // writes [] to pikar_open_tab_ids between the two setOpenTabIds updaters,
  // then [newId]. This is acceptable today because pikar_open_tab_ids does
  // NOT have a cross-tab `storage` event listener (only pikar_current_session_id
  // does — Plan 88-01 scope). If a future phase adds cross-tab sync for
  // open tabs, the writes need to be unified (e.g., flushSync, a single
  // combined reducer, or a debounced effect).
  // ------------------------------------------------------------------
  const closeTab = useCallback(
    (sessionId: string) => {
      // Compute the next array from the closure-captured current state so
      // the rest of the logic (promotion / fallback) sees a deterministic
      // value before React commits the setState.
      if (!openTabIds.includes(sessionId)) {
        return
      }
      const nextOpenTabIds = openTabIds.filter((id) => id !== sessionId)
      setOpenTabIds(nextOpenTabIds)

      // Remove from the in-memory map. Safe even if the entry is absent.
      removeActiveSession(sessionId)

      // Was the closed tab the visible one? Promote the next remaining
      // tab if so; if none remain, seed a fresh chat.
      if (visibleSessionId === sessionId) {
        if (nextOpenTabIds.length === 0) {
          // Last tab closed — auto-open a fresh chat (locked decision).
          createNewChat()
        } else {
          // Promote the most-recently-opened remaining tab.
          const promoted = nextOpenTabIds[nextOpenTabIds.length - 1]
          setVisibleSessionId(promoted)
        }
      }
    },
    [
      openTabIds,
      visibleSessionId,
      removeActiveSession,
      setVisibleSessionId,
      createNewChat,
    ],
  )

  // ------------------------------------------------------------------
  // selectChat — opening from the history dropdown produces a tab pill.
  //
  // Delegates to openTab so the tab strip stays in sync with what the user
  // is viewing. If the cap is reached, log to console (Plan 03 TabStrip +
  // Plan 04 toast will render a user-facing message); other errors are
  // re-thrown so we don't swallow real bugs.
  // ------------------------------------------------------------------
  const selectChat = useCallback(
    (sessionId: string) => {
      try {
        openTab(sessionId)
      } catch (err) {
        if (err instanceof TabCapReachedError) {
          console.warn('[SessionControl] selectChat hit tab cap:', err.message)
          return
        }
        throw err
      }
    },
    [openTab],
  )

  // ------------------------------------------------------------------
  // refreshSessions — fetch via backend GET /sessions
  //
  // The backend computes title and preview server-side in a single optimized
  // call; previously the frontend did N+1 Supabase queries per refresh which
  // both slowed sidebar load and (more importantly) was the data source for
  // the in-memory `sessions` array that the chat-history-loading effect
  // raced against on reload.
  // ------------------------------------------------------------------
  const refreshSessions = useCallback(async (): Promise<void> => {
    if (!userId) return

    try {
      setIsLoadingSessions(true)
      const { sessions: serverSessions } = await listUserSessions()
      const chatSessions: ChatSession[] = serverSessions.map((s) => ({
        id: s.id,
        title:
          s.title && s.title.trim()
            ? s.title
            : extractTitleFromSessionId(s.id),
        preview: s.preview ?? undefined,
        createdAt: s.created_at,
        updatedAt: s.updated_at,
      }))

      setSessions(chatSessions)

      if (!initializedRef.current && chatSessions.length > 0) {
        initializedRef.current = true
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err)
    } finally {
      setIsLoadingSessions(false)
    }
  }, [userId, setSessions, setIsLoadingSessions])

  // ------------------------------------------------------------------
  // Load sessions when user is available
  // ------------------------------------------------------------------
  useEffect(() => {
    if (userId) {
      refreshSessions()
    }
  }, [userId, refreshSessions])

  // ------------------------------------------------------------------
  // deleteChat — delete session events, workspace items, and session
  // ------------------------------------------------------------------
  const deleteChat = useCallback(
    async (sessionId: string): Promise<void> => {
      if (!userId) return

      try {
        // Delete session events first (scoped to user + app)
        await supabase
          .from('session_events')
          .delete()
          .eq('session_id', sessionId)
          .eq('user_id', userId)
          .eq('app_name', AGENTS_APP_NAME)

        await supabase
          .from('workspace_items')
          .delete()
          .eq('session_id', sessionId)
          .eq('user_id', userId)

        // Delete the session
        const { error } = await supabase
          .from('sessions')
          .delete()
          .eq('session_id', sessionId)
          .eq('user_id', userId)

        if (error) {
          console.error('Error deleting session:', error)
          throw error
        }

        // Update local state
        setSessions((prev) => prev.filter((s) => s.id !== sessionId))

        // Remove from active sessions map if present
        removeActiveSession(sessionId)

        // If deleted current session, clear it
        if (visibleSessionId === sessionId) {
          setVisibleSessionId(null)
        }
      } catch (err) {
        console.error('Failed to delete session:', err)
        throw err
      }
    },
    [
      userId,
      supabase,
      visibleSessionId,
      setSessions,
      removeActiveSession,
      setVisibleSessionId,
    ],
  )

  // ------------------------------------------------------------------
  // clearAllChats — delete all sessions for the user
  // ------------------------------------------------------------------
  const clearAllChats = useCallback(async (): Promise<void> => {
    if (!userId) return

    try {
      // Delete all session events for user (scoped to agents app only)
      await supabase
        .from('session_events')
        .delete()
        .eq('user_id', userId)
        .eq('app_name', AGENTS_APP_NAME)

      await supabase
        .from('workspace_items')
        .delete()
        .eq('user_id', userId)

      // Delete all sessions for user
      const { error } = await supabase
        .from('sessions')
        .delete()
        .eq('user_id', userId)

      if (error) {
        console.error('Error clearing sessions:', error)
        throw error
      }

      // Clear local state
      setSessions([])
      setVisibleSessionId(null)
    } catch (err) {
      console.error('Failed to clear all sessions:', err)
      throw err
    }
  }, [userId, supabase, setSessions, setVisibleSessionId])

  // ------------------------------------------------------------------
  // updateSessionTitle — update title in DB and local state
  // ------------------------------------------------------------------
  const updateSessionTitle = useCallback(
    async (sessionId: string, title: string): Promise<void> => {
      if (!userId) return

      try {
        // First get current state
        const { data: session } = await supabase
          .from('sessions')
          .select('state')
          .eq('session_id', sessionId)
          .eq('user_id', userId)
          .eq('app_name', AGENTS_APP_NAME)
          .single()

        const currentState = (session?.state as Record<string, unknown>) || {}

        // Update with new title
        const { error } = await supabase
          .from('sessions')
          .update({
            state: { ...currentState, title },
            updated_at: new Date().toISOString(),
          })
          .eq('session_id', sessionId)
          .eq('user_id', userId)
          .eq('app_name', AGENTS_APP_NAME)

        if (error) {
          console.error('Error updating session title:', error)
          throw error
        }

        // Update local state
        setSessions((prev) =>
          prev.map((s) => (s.id === sessionId ? { ...s, title } : s)),
        )
      } catch (err) {
        console.error('Failed to update session title:', err)
        throw err
      }
    },
    [userId, supabase, setSessions],
  )

  // ------------------------------------------------------------------
  // updateSessionPreview — update last message preview in DB and local state
  // ------------------------------------------------------------------
  const updateSessionPreview = useCallback(
    async (sessionId: string, preview: string): Promise<void> => {
      if (!userId || !preview) return

      try {
        const safePreview =
          typeof preview === 'string' ? preview : JSON.stringify(preview)
        const truncatedPreview =
          safePreview.length > 100
            ? safePreview.substring(0, 100) + '...'
            : safePreview

        // Get current state
        const { data: session } = await supabase
          .from('sessions')
          .select('state')
          .eq('session_id', sessionId)
          .eq('user_id', userId)
          .eq('app_name', AGENTS_APP_NAME)
          .single()

        const currentState = (session?.state as Record<string, unknown>) || {}

        // Update with new preview
        const { error } = await supabase
          .from('sessions')
          .update({
            state: { ...currentState, lastMessage: truncatedPreview },
            updated_at: new Date().toISOString(),
          })
          .eq('session_id', sessionId)
          .eq('user_id', userId)
          .eq('app_name', AGENTS_APP_NAME)

        if (error) {
          console.error('Error updating session preview:', error.message || error)
          return
        }

        // Update local state
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId ? { ...s, preview: truncatedPreview } : s,
          ),
        )
      } catch (err: any) {
        console.error(
          'Failed to update session preview:',
          err.message || err,
        )
      }
    },
    [userId, supabase, setSessions],
  )

  // ------------------------------------------------------------------
  // addSessionOptimistic — add session to list immediately
  // ------------------------------------------------------------------
  const addSessionOptimistic = useCallback(
    (session: ChatSession): void => {
      setSessions((prev) => {
        const exists = prev.some((s) => s.id === session.id)
        if (exists)
          return prev.map((s) =>
            s.id === session.id
              ? {
                  ...session,
                  updatedAt:
                    s.updatedAt > session.updatedAt
                      ? s.updatedAt
                      : session.updatedAt,
                }
              : s,
          )
        return [session, ...prev]
      })
    },
    [setSessions],
  )

  // ------------------------------------------------------------------
  // Memoized context value
  // ------------------------------------------------------------------
  const value = useMemo<SessionControlContextValue>(
    () => ({
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
      // FEATURE-MULTI-SESSION-TABS
      openTabIds,
      tabCap,
      setTabCap,
      openTab,
      closeTab,
    }),
    [
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
      // FEATURE-MULTI-SESSION-TABS
      openTabIds,
      tabCap,
      setTabCap,
      openTab,
      closeTab,
    ],
  )

  return (
    <SessionControlContext.Provider value={value}>
      {children}
    </SessionControlContext.Provider>
  )
}
