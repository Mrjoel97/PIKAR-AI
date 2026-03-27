'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useEffect, useRef } from 'react'
import { useSessionMap } from '@/contexts/SessionMapContext'
import { useSessionControl } from '@/contexts/SessionControlContext'

export function useSessionMemoryManager() {
  const { activeSessions, removeActiveSession } = useSessionMap()
  const { visibleSessionId, config } = useSessionControl()

  // Use refs to avoid recreating the interval on every state change
  const activeSessionsRef = useRef(activeSessions)
  activeSessionsRef.current = activeSessions
  const visibleRef = useRef(visibleSessionId)
  visibleRef.current = visibleSessionId
  const configRef = useRef(config)
  configRef.current = config

  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now()
      const sessions = activeSessionsRef.current
      const visible = visibleRef.current
      const cfg = configRef.current
      const evictionThreshold = cfg.memory_eviction_minutes * 60 * 1000

      // Evict idle sessions past threshold
      for (const [id, session] of sessions) {
        if (
          id !== visible &&
          session.status === 'idle' &&
          !session.hasUnread &&
          (now - session.lastUpdatedAt) > evictionThreshold
        ) {
          removeActiveSession(id)
        }
      }

      // Hard cap enforcement
      if (activeSessionsRef.current.size > cfg.max_active_sessions_in_memory) {
        const sortedIdle = Array.from(activeSessionsRef.current.entries())
          .filter(([id, s]) => id !== visible && s.status === 'idle')
          .sort((a, b) => a[1].lastUpdatedAt - b[1].lastUpdatedAt)

        const excess = activeSessionsRef.current.size - cfg.max_active_sessions_in_memory
        for (let i = 0; i < Math.min(excess, sortedIdle.length); i++) {
          removeActiveSession(sortedIdle[i][0])
        }
      }
    }, 5 * 60 * 1000) // Every 5 minutes

    return () => clearInterval(interval)
  }, [removeActiveSession]) // Only depends on stable callback

  // No return value — this is a side-effect-only hook
}
