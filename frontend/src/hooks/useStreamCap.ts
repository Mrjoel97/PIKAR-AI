'use client'

import { useCallback } from 'react'
import type { ActiveSessionState } from '@/types/session'
import { useSessionMap } from '@/contexts/SessionMapContext'
import { useSessionControl } from '@/contexts/SessionControlContext'
import { useBackgroundStream } from '@/hooks/useBackgroundStream'

// ---------------------------------------------------------------------------
// Pure helper — exported for unit testing
// ---------------------------------------------------------------------------

/**
 * Find the LRU streaming session that can be evicted to satisfy the cap.
 *
 * Returns the session ID of the streaming session with the oldest
 * `lastUpdatedAt` that is NOT the currently visible session, or `null` when
 * no eviction is required (count < cap) or all streaming sessions are the
 * visible session.
 */
export function getEvictionCandidate(
  activeSessions: Map<string, ActiveSessionState>,
  visibleSessionId: string | null,
  maxConcurrentStreams: number,
): string | null {
  // Collect all sessions that are currently streaming
  const streaming: ActiveSessionState[] = []
  for (const session of activeSessions.values()) {
    if (session.status === 'streaming') {
      streaming.push(session)
    }
  }

  // Under cap — nothing to evict
  if (streaming.length < maxConcurrentStreams) {
    return null
  }

  // Find the oldest streaming session that is not the visible one
  let candidate: ActiveSessionState | null = null
  for (const session of streaming) {
    if (session.sessionId === visibleSessionId) continue
    if (candidate === null || session.lastUpdatedAt < candidate.lastUpdatedAt) {
      candidate = session
    }
  }

  return candidate?.sessionId ?? null
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface UseStreamCapReturn {
  /**
   * Check the concurrent-stream cap and evict the LRU background stream if
   * the cap would be exceeded.  Returns the evicted session ID, or `null` if
   * no eviction was necessary.
   */
  enforceCapBeforeStream: () => string | null
}

export function useStreamCap(): UseStreamCapReturn {
  const { activeSessions, updateSessionState } = useSessionMap()
  const { visibleSessionId, config } = useSessionControl()
  const { stopStream } = useBackgroundStream()

  const enforceCapBeforeStream = useCallback((): string | null => {
    const evictId = getEvictionCandidate(
      activeSessions,
      visibleSessionId,
      config.max_concurrent_streams,
    )

    if (evictId === null) return null

    // Abort the stream via the background stream manager
    stopStream(evictId)

    // Override the status to 'interrupted' so consumers know it was
    // evicted rather than stopped cleanly
    updateSessionState(evictId, { status: 'interrupted' })

    return evictId
  }, [activeSessions, visibleSessionId, config.max_concurrent_streams, stopStream, updateSessionState])

  return { enforceCapBeforeStream }
}
