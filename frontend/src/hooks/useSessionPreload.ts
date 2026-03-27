'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useEffect, useRef } from 'react'
import { useSessionMap } from '@/contexts/SessionMapContext'
import { loadSessionHistory } from '@/lib/sessionHistory'

export function useSessionPreload(userId: string | null, maxPreload = 3) {
  const { sessions, addActiveSession, activeSessions } = useSessionMap()
  const hasPreloaded = useRef(false)

  useEffect(() => {
    if (hasPreloaded.current || !userId || sessions.length === 0) return
    hasPreloaded.current = true

    const toPreload = sessions
      .slice(0, maxPreload)
      .filter(s => !activeSessions.has(s.id))

    if (toPreload.length === 0) return

    Promise.all(
      toPreload.map(async (session) => {
        try {
          const messages = await loadSessionHistory(session.id, userId)
          addActiveSession(session.id, { messages })
        } catch {
          // Silently fail
        }
      })
    )
  }, [sessions, userId, addActiveSession, activeSessions, maxPreload])
}
