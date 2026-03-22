// @vitest-environment jsdom
import { describe, it, expect } from 'vitest'
import { getEvictionCandidate } from '@/hooks/useStreamCap'
import type { ActiveSessionState } from '@/types/session'
import { createEmptyActiveSession } from '@/types/session'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeSession(
  sessionId: string,
  status: ActiveSessionState['status'],
  lastUpdatedAt: number,
): ActiveSessionState {
  return {
    ...createEmptyActiveSession(sessionId),
    status,
    lastUpdatedAt,
  }
}

function makeMap(
  sessions: ActiveSessionState[],
): Map<string, ActiveSessionState> {
  const m = new Map<string, ActiveSessionState>()
  for (const s of sessions) {
    m.set(s.sessionId, s)
  }
  return m
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('getEvictionCandidate', () => {
  it('returns null when streaming count is under cap', () => {
    // 2 streaming sessions, cap=4 — no eviction needed
    const sessions = makeMap([
      makeSession('s1', 'streaming', 1000),
      makeSession('s2', 'streaming', 2000),
      makeSession('s3', 'idle', 3000),
      makeSession('s4', 'idle', 4000),
    ])

    const result = getEvictionCandidate(sessions, 's1', 4)
    expect(result).toBeNull()
  })

  it('returns the streaming session with the oldest lastUpdatedAt when at cap', () => {
    // 4 streaming sessions, cap=4 — s1 is oldest (1000), not visible
    const sessions = makeMap([
      makeSession('s1', 'streaming', 1000),
      makeSession('s2', 'streaming', 2000),
      makeSession('s3', 'streaming', 3000),
      makeSession('s4', 'streaming', 4000),
    ])

    // visible is s4 (newest), so s1 (oldest non-visible) should be evicted
    const result = getEvictionCandidate(sessions, 's4', 4)
    expect(result).toBe('s1')
  })

  it('never evicts the visible session even if it has the oldest lastUpdatedAt', () => {
    // s1 is both oldest AND visible — must not be evicted
    const sessions = makeMap([
      makeSession('s1', 'streaming', 1000), // oldest
      makeSession('s2', 'streaming', 2000),
      makeSession('s3', 'streaming', 3000),
      makeSession('s4', 'streaming', 4000),
    ])

    // s1 is visible — s2 is next oldest non-visible candidate
    const result = getEvictionCandidate(sessions, 's1', 4)
    expect(result).toBe('s2')
  })

  it('returns null if only the visible session is streaming at cap', () => {
    // Only one streaming session and it is the visible one
    // cap=1, count=1 — at cap, but no non-visible candidates to evict
    const sessions = makeMap([
      makeSession('s1', 'streaming', 1000),
      makeSession('s2', 'idle', 2000),
      makeSession('s3', 'idle', 3000),
    ])

    const result = getEvictionCandidate(sessions, 's1', 1)
    expect(result).toBeNull()
  })

  it('handles an empty map by returning null', () => {
    const sessions = makeMap([])
    const result = getEvictionCandidate(sessions, null, 4)
    expect(result).toBeNull()
  })
})
