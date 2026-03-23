'use client'

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  useRef,
  type MutableRefObject,
} from 'react'
import type { ActiveSessionState } from '@/types/session'
import { createEmptyActiveSession } from '@/types/session'

// ---------------------------------------------------------------------------
// ChatSession — sidebar metadata (distinct from ActiveSessionState which is
// the in-memory runtime state used by streams).
// ---------------------------------------------------------------------------
export interface ChatSession {
  id: string
  title: string
  preview?: string
  createdAt: string
  updatedAt: string
}

// ---------------------------------------------------------------------------
// Context shape
// ---------------------------------------------------------------------------
interface SessionMapContextType {
  /** In-memory active session state map — keyed by session id. */
  activeSessions: Map<string, ActiveSessionState>

  /** Create a new entry in the active sessions map. No-op if already exists. */
  addActiveSession: (
    sessionId: string,
    initialOverrides?: Partial<ActiveSessionState>,
  ) => void

  /** Remove an entry from the active sessions map. */
  removeActiveSession: (sessionId: string) => void

  /** Merge partial updates into an existing session's state. No-op if session not found. */
  updateSessionState: (
    sessionId: string,
    updates: Partial<ActiveSessionState>,
  ) => void

  /**
   * Returns a stable MutableRefObject whose `.current` mirrors the latest
   * state for the given session. Background SSE streams should write through
   * this ref so that high-frequency updates avoid triggering React re-renders.
   * Returns `null` when the session is not in the map.
   */
  getActiveSessionRef: (
    sessionId: string,
  ) => MutableRefObject<ActiveSessionState | null> | null

  // --- Sidebar metadata (from Supabase) ---
  sessions: ChatSession[]
  setSessions: React.Dispatch<React.SetStateAction<ChatSession[]>>
  isLoadingSessions: boolean
  setIsLoadingSessions: React.Dispatch<React.SetStateAction<boolean>>
}

const SessionMapContext = createContext<SessionMapContextType | null>(null)

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export function useSessionMap(): SessionMapContextType {
  const ctx = useContext(SessionMapContext)
  if (!ctx) {
    throw new Error('useSessionMap must be used within a SessionMapProvider')
  }
  return ctx
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
interface SessionMapProviderProps {
  children: React.ReactNode
}

export function SessionMapProvider({ children }: SessionMapProviderProps) {
  // ---- Active sessions (in-memory, high-frequency) ----
  const [activeSessions, setActiveSessions] = useState<
    Map<string, ActiveSessionState>
  >(() => new Map())

  // Parallel ref map so background streams can read/write without triggering
  // React re-renders. Each entry is a MutableRefObject whose `.current`
  // mirrors the corresponding state entry.
  const sessionRefsMap = useRef<
    Map<string, MutableRefObject<ActiveSessionState | null>>
  >(new Map())

  // ---- Sidebar metadata ----
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [isLoadingSessions, setIsLoadingSessions] = useState(false)

  // ------------------------------------------------------------------
  // addActiveSession
  // ------------------------------------------------------------------
  const addActiveSession = useCallback(
    (sessionId: string, initialOverrides?: Partial<ActiveSessionState>) => {
      setActiveSessions((prev) => {
        // Do not overwrite an existing entry
        if (prev.has(sessionId)) return prev

        const newSession: ActiveSessionState = {
          ...createEmptyActiveSession(sessionId),
          ...initialOverrides,
          sessionId, // ensure sessionId is always correct
        }

        // Update ref map
        const refEntry = { current: newSession }
        sessionRefsMap.current.set(sessionId, refEntry)

        const next = new Map(prev)
        next.set(sessionId, newSession)
        return next
      })
    },
    [],
  )

  // ------------------------------------------------------------------
  // updateSessionState
  // ------------------------------------------------------------------
  const updateSessionState = useCallback(
    (sessionId: string, updates: Partial<ActiveSessionState>) => {
      setActiveSessions((prev) => {
        const existing = prev.get(sessionId)
        if (!existing) return prev

        const updated: ActiveSessionState = { ...existing, ...updates }

        // Keep the ref in sync
        const ref = sessionRefsMap.current.get(sessionId)
        if (ref) {
          ref.current = updated
        }

        const next = new Map(prev)
        next.set(sessionId, updated)
        return next
      })
    },
    [],
  )

  // ------------------------------------------------------------------
  // removeActiveSession
  // ------------------------------------------------------------------
  const removeActiveSession = useCallback((sessionId: string) => {
    setActiveSessions((prev) => {
      if (!prev.has(sessionId)) return prev

      // Clean up ref map
      sessionRefsMap.current.delete(sessionId)

      const next = new Map(prev)
      next.delete(sessionId)
      return next
    })
  }, [])

  // ------------------------------------------------------------------
  // getActiveSessionRef
  // ------------------------------------------------------------------
  const getActiveSessionRef = useCallback(
    (
      sessionId: string,
    ): MutableRefObject<ActiveSessionState | null> | null => {
      return sessionRefsMap.current.get(sessionId) ?? null
    },
    [],
  )

  // ------------------------------------------------------------------
  // Memoized context value
  // ------------------------------------------------------------------
  const value = useMemo<SessionMapContextType>(
    () => ({
      activeSessions,
      addActiveSession,
      removeActiveSession,
      updateSessionState,
      getActiveSessionRef,
      sessions,
      setSessions,
      isLoadingSessions,
      setIsLoadingSessions,
    }),
    [
      activeSessions,
      addActiveSession,
      removeActiveSession,
      updateSessionState,
      getActiveSessionRef,
      sessions,
      isLoadingSessions,
    ],
  )

  return (
    <SessionMapContext.Provider value={value}>
      {children}
    </SessionMapContext.Provider>
  )
}
