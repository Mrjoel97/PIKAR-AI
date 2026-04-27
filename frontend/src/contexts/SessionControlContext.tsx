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
const AGENTS_APP_NAME = 'agents'

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
  // ------------------------------------------------------------------
  const createNewChat = useCallback((): string => {
    const newId = generateSessionId()
    addActiveSession(newId, { skipHistoryRestore: true })
    setVisibleSessionId(newId)
    return newId
  }, [addActiveSession, setVisibleSessionId])

  // ------------------------------------------------------------------
  // selectChat
  // ------------------------------------------------------------------
  const selectChat = useCallback(
    (sessionId: string) => {
      setVisibleSessionId(sessionId)
    },
    [setVisibleSessionId],
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
    ],
  )

  return (
    <SessionControlContext.Provider value={value}>
      {children}
    </SessionControlContext.Provider>
  )
}
