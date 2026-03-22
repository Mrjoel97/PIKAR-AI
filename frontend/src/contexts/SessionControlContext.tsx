'use client'

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
} from 'react'
import type { SessionConfig } from '@/types/session'
import { DEFAULT_SESSION_CONFIG } from '@/types/session'
import { useSessionMap, type ChatSession } from './SessionMapContext'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const STORAGE_KEY = 'pikar_current_session_id'

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

  // Stubs — will be implemented in Task 7
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
// Provider
// ---------------------------------------------------------------------------
interface SessionControlProviderProps {
  children: React.ReactNode
}

export function SessionControlProvider({
  children,
}: SessionControlProviderProps) {
  const { addActiveSession } = useSessionMap()

  // ---- Core state ----
  const [visibleSessionId, setVisibleSessionIdRaw] = useState<string | null>(
    null,
  )
  const [sessionRestored, setSessionRestored] = useState(false)
  const [config, setConfig] = useState<SessionConfig>(DEFAULT_SESSION_CONFIG)

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
  // Config fetch — non-blocking, falls back to defaults on failure
  // ------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false

    async function fetchConfig() {
      try {
        const res = await fetch('/configuration/session-config')
        if (!res.ok) return
        const data = await res.json()
        if (!cancelled) {
          setConfig((prev) => ({ ...prev, ...data }))
        }
      } catch {
        // Silently use defaults
      }
    }

    fetchConfig()
    return () => {
      cancelled = true
    }
  }, [])

  // ------------------------------------------------------------------
  // createNewChat
  // ------------------------------------------------------------------
  const createNewChat = useCallback((): string => {
    const newId = generateSessionId()
    addActiveSession(newId)
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
  // Stubs — TODO: migrate from ChatSessionContext.tsx in Task 7
  // ------------------------------------------------------------------
  const deleteChat = useCallback(
    async (_sessionId: string): Promise<void> => {
      // TODO: migrate from ChatSessionContext.tsx in Task 7
    },
    [],
  )

  const clearAllChats = useCallback(async (): Promise<void> => {
    // TODO: migrate from ChatSessionContext.tsx in Task 7
  }, [])

  const refreshSessions = useCallback(async (): Promise<void> => {
    // TODO: migrate from ChatSessionContext.tsx in Task 7
  }, [])

  const updateSessionTitle = useCallback(
    async (_sessionId: string, _title: string): Promise<void> => {
      // TODO: migrate from ChatSessionContext.tsx in Task 7
    },
    [],
  )

  const updateSessionPreview = useCallback(
    async (_sessionId: string, _preview: string): Promise<void> => {
      // TODO: migrate from ChatSessionContext.tsx in Task 7
    },
    [],
  )

  const addSessionOptimistic = useCallback((_session: ChatSession): void => {
    // TODO: migrate from ChatSessionContext.tsx in Task 7
  }, [])

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
