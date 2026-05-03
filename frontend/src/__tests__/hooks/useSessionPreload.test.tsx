// @vitest-environment jsdom
import { renderHook, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ActiveSessionState } from '@/types/session'
import { createEmptyActiveSession } from '@/types/session'
import type { ChatSession } from '@/contexts/SessionMapContext'

const mockLoadSessionHistory = vi.fn()

vi.mock('@/lib/sessionHistory', () => ({
  loadSessionHistory: (...args: unknown[]) => mockLoadSessionHistory(...args),
}))

let mockSessions: ChatSession[] = []
let mockVisibleSessionId: string | null = null
let mockActiveSessions = new Map<string, ActiveSessionState>()

const mockAddActiveSession = vi.fn(
  (sessionId: string, overrides?: Partial<ActiveSessionState>) => {
    if (!mockActiveSessions.has(sessionId)) {
      mockActiveSessions.set(sessionId, {
        ...createEmptyActiveSession(sessionId),
        ...overrides,
        sessionId,
      })
    }
  },
)

vi.mock('@/contexts/SessionMapContext', () => ({
  useSessionMap: () => ({
    sessions: mockSessions,
    addActiveSession: mockAddActiveSession,
    activeSessions: mockActiveSessions,
  }),
}))

vi.mock('@/contexts/SessionControlContext', () => ({
  useSessionControl: () => ({
    visibleSessionId: mockVisibleSessionId,
  }),
}))

import { useSessionPreload } from '@/hooks/useSessionPreload'

describe('useSessionPreload', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()

    mockVisibleSessionId = 'session-visible'
    mockActiveSessions = new Map()
    mockSessions = [
      {
        id: 'session-visible',
        title: 'Visible session',
        createdAt: '2026-04-30T00:00:00.000Z',
        updatedAt: '2026-04-30T00:00:00.000Z',
      },
      {
        id: 'session-two',
        title: 'Second session',
        createdAt: '2026-04-29T00:00:00.000Z',
        updatedAt: '2026-04-29T00:00:00.000Z',
      },
      {
        id: 'session-three',
        title: 'Third session',
        createdAt: '2026-04-28T00:00:00.000Z',
        updatedAt: '2026-04-28T00:00:00.000Z',
      },
    ]
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('waits before preloading and skips the visible session while loading others sequentially', async () => {
    let resolveSecondSession: ((messages: never[]) => void) | null = null
    let resolveThirdSession: ((messages: never[]) => void) | null = null

    mockLoadSessionHistory.mockImplementation((sessionId: string) => {
      if (sessionId === 'session-two') {
        return new Promise((resolve) => {
          resolveSecondSession = resolve
        })
      }

      if (sessionId === 'session-three') {
        return new Promise((resolve) => {
          resolveThirdSession = resolve
        })
      }

      return Promise.resolve([])
    })

    renderHook(() => useSessionPreload('user-123', 3))

    expect(mockLoadSessionHistory).not.toHaveBeenCalled()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2999)
    })

    expect(mockLoadSessionHistory).not.toHaveBeenCalled()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1)
      await Promise.resolve()
    })

    expect(mockLoadSessionHistory).toHaveBeenCalledTimes(1)
    expect(mockLoadSessionHistory).toHaveBeenCalledWith('session-two', 'user-123')

    resolveSecondSession?.([])

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(mockLoadSessionHistory).toHaveBeenCalledTimes(2)
    expect(mockLoadSessionHistory).toHaveBeenNthCalledWith(2, 'session-three', 'user-123')
    expect(mockLoadSessionHistory).not.toHaveBeenCalledWith('session-visible', 'user-123')

    resolveThirdSession?.([])

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(mockAddActiveSession).toHaveBeenCalledWith(
      'session-two',
      expect.objectContaining({ messages: [] }),
    )
    expect(mockAddActiveSession).toHaveBeenCalledWith(
      'session-three',
      expect.objectContaining({ messages: [] }),
    )
  })
})
