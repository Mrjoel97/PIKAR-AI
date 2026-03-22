// @vitest-environment jsdom
import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import React from 'react'
import { SessionMapProvider, useSessionMap } from '@/contexts/SessionMapContext'
import type { ActiveSessionState } from '@/types/session'

// Wrapper for renderHook
function wrapper({ children }: { children: React.ReactNode }) {
  return <SessionMapProvider>{children}</SessionMapProvider>
}

describe('SessionMapContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initialization', () => {
    it('initializes with empty activeSessions map', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      expect(result.current.activeSessions).toBeInstanceOf(Map)
      expect(result.current.activeSessions.size).toBe(0)
    })

    it('initializes with empty sessions array', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      expect(result.current.sessions).toEqual([])
      expect(result.current.isLoadingSessions).toBe(false)
    })
  })

  describe('useSessionMap outside provider', () => {
    it('throws if used outside SessionMapProvider', () => {
      // Suppress console.error for expected error
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
      expect(() => {
        renderHook(() => useSessionMap())
      }).toThrow('useSessionMap must be used within a SessionMapProvider')
      spy.mockRestore()
    })
  })

  describe('addActiveSession', () => {
    it('adds entry with default empty state', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      act(() => {
        result.current.addActiveSession('session-1')
      })

      expect(result.current.activeSessions.size).toBe(1)
      const session = result.current.activeSessions.get('session-1')
      expect(session).toBeDefined()
      expect(session!.sessionId).toBe('session-1')
      expect(session!.messages).toEqual([])
      expect(session!.status).toBe('idle')
      expect(session!.hasUnread).toBe(false)
      expect(session!.abortController).toBeNull()
      expect(session!.rawWidgets).toEqual([])
      expect(session!.pendingActions).toEqual([])
    })

    it('adds entry with custom initial state', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      act(() => {
        result.current.addActiveSession('session-2', {
          status: 'streaming',
          hasUnread: true,
        })
      })

      const session = result.current.activeSessions.get('session-2')
      expect(session).toBeDefined()
      expect(session!.sessionId).toBe('session-2')
      expect(session!.status).toBe('streaming')
      expect(session!.hasUnread).toBe(true)
      // Defaults still applied for unspecified fields
      expect(session!.messages).toEqual([])
    })

    it('does not overwrite existing session', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      act(() => {
        result.current.addActiveSession('session-1')
      })

      act(() => {
        result.current.updateSessionState('session-1', {
          messages: [{ role: 'user', text: 'hello' }],
        })
      })

      // Try adding again - should not overwrite
      act(() => {
        result.current.addActiveSession('session-1')
      })

      const session = result.current.activeSessions.get('session-1')
      expect(session!.messages).toHaveLength(1)
    })

    it('can add multiple sessions', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      act(() => {
        result.current.addActiveSession('session-a')
        result.current.addActiveSession('session-b')
        result.current.addActiveSession('session-c')
      })

      expect(result.current.activeSessions.size).toBe(3)
    })
  })

  describe('updateSessionState', () => {
    it('merges partial updates into existing session', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      act(() => {
        result.current.addActiveSession('session-1')
      })

      act(() => {
        result.current.updateSessionState('session-1', {
          status: 'streaming',
          messages: [{ role: 'user', text: 'hello' }],
        })
      })

      const session = result.current.activeSessions.get('session-1')
      expect(session!.status).toBe('streaming')
      expect(session!.messages).toHaveLength(1)
      // Other fields remain at defaults
      expect(session!.hasUnread).toBe(false)
    })

    it('does not affect other sessions', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      act(() => {
        result.current.addActiveSession('session-1')
        result.current.addActiveSession('session-2')
      })

      act(() => {
        result.current.updateSessionState('session-1', { status: 'error' })
      })

      expect(result.current.activeSessions.get('session-1')!.status).toBe('error')
      expect(result.current.activeSessions.get('session-2')!.status).toBe('idle')
    })

    it('is a no-op for non-existent session', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      act(() => {
        result.current.updateSessionState('does-not-exist', { status: 'error' })
      })

      expect(result.current.activeSessions.size).toBe(0)
    })
  })

  describe('removeActiveSession', () => {
    it('removes an existing session', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      act(() => {
        result.current.addActiveSession('session-1')
        result.current.addActiveSession('session-2')
      })

      expect(result.current.activeSessions.size).toBe(2)

      act(() => {
        result.current.removeActiveSession('session-1')
      })

      expect(result.current.activeSessions.size).toBe(1)
      expect(result.current.activeSessions.has('session-1')).toBe(false)
      expect(result.current.activeSessions.has('session-2')).toBe(true)
    })

    it('is a no-op for non-existent session', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      act(() => {
        result.current.addActiveSession('session-1')
      })

      act(() => {
        result.current.removeActiveSession('does-not-exist')
      })

      expect(result.current.activeSessions.size).toBe(1)
    })
  })

  describe('hasUnread toggling', () => {
    it('can toggle hasUnread via updateSessionState', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      act(() => {
        result.current.addActiveSession('session-1')
      })

      expect(result.current.activeSessions.get('session-1')!.hasUnread).toBe(false)

      act(() => {
        result.current.updateSessionState('session-1', { hasUnread: true })
      })

      expect(result.current.activeSessions.get('session-1')!.hasUnread).toBe(true)

      act(() => {
        result.current.updateSessionState('session-1', { hasUnread: false })
      })

      expect(result.current.activeSessions.get('session-1')!.hasUnread).toBe(false)
    })
  })

  describe('getActiveSessionRef', () => {
    it('returns a ref object with current session state', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      act(() => {
        result.current.addActiveSession('session-1')
      })

      const ref = result.current.getActiveSessionRef('session-1')
      expect(ref).toBeDefined()
      expect(ref!.current).toBeDefined()
      expect(ref!.current!.sessionId).toBe('session-1')
    })

    it('returns null for non-existent session', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      const ref = result.current.getActiveSessionRef('does-not-exist')
      expect(ref).toBeNull()
    })

    it('ref stays in sync after updateSessionState', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      act(() => {
        result.current.addActiveSession('session-1')
      })

      const ref = result.current.getActiveSessionRef('session-1')

      act(() => {
        result.current.updateSessionState('session-1', { status: 'streaming' })
      })

      // The ref should reflect the updated state
      expect(ref!.current!.status).toBe('streaming')
    })
  })

  describe('sessions metadata', () => {
    it('allows setting sessions list', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      act(() => {
        result.current.setSessions([
          {
            id: 's1',
            title: 'First Chat',
            createdAt: '2025-01-01T00:00:00Z',
            updatedAt: '2025-01-01T01:00:00Z',
          },
        ])
      })

      expect(result.current.sessions).toHaveLength(1)
      expect(result.current.sessions[0].title).toBe('First Chat')
    })

    it('allows toggling isLoadingSessions', () => {
      const { result } = renderHook(() => useSessionMap(), { wrapper })

      expect(result.current.isLoadingSessions).toBe(false)

      act(() => {
        result.current.setIsLoadingSessions(true)
      })

      expect(result.current.isLoadingSessions).toBe(true)
    })
  })
})
