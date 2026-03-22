// @vitest-environment jsdom
import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import React from 'react'
import { SessionMapProvider } from '@/contexts/SessionMapContext'
import {
  SessionControlProvider,
  useSessionControl,
} from '@/contexts/SessionControlContext'
import { DEFAULT_SESSION_CONFIG } from '@/types/session'

// ---------------------------------------------------------------------------
// localStorage mock
// ---------------------------------------------------------------------------
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
    get _store() {
      return store
    },
  }
})()

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })

// ---------------------------------------------------------------------------
// fetch mock
// ---------------------------------------------------------------------------
const fetchMock = vi.fn()
Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })

// ---------------------------------------------------------------------------
// Wrapper that includes both providers
// ---------------------------------------------------------------------------
function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <SessionMapProvider>
      <SessionControlProvider>{children}</SessionControlProvider>
    </SessionMapProvider>
  )
}

describe('SessionControlContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
    // Default: config fetch returns 404 so we fall back to defaults
    fetchMock.mockResolvedValue({
      ok: false,
      status: 404,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // -----------------------------------------------------------------------
  // Initialization
  // -----------------------------------------------------------------------
  describe('initialization', () => {
    it('initializes with null visibleSessionId', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      expect(result.current.visibleSessionId).toBeNull()
    })

    it('config defaults to DEFAULT_SESSION_CONFIG', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      expect(result.current.config).toEqual(DEFAULT_SESSION_CONFIG)
    })

    it('sessionRestored becomes true after mount', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await waitFor(() => {
        expect(result.current.sessionRestored).toBe(true)
      })
    })
  })

  // -----------------------------------------------------------------------
  // useSessionControl outside provider
  // -----------------------------------------------------------------------
  describe('useSessionControl outside provider', () => {
    it('throws if used outside SessionControlProvider', () => {
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
      expect(() => {
        renderHook(() => useSessionControl())
      }).toThrow('useSessionControl must be used within a SessionControlProvider')
      spy.mockRestore()
    })
  })

  // -----------------------------------------------------------------------
  // createNewChat
  // -----------------------------------------------------------------------
  describe('createNewChat', () => {
    it('generates ID matching expected pattern', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      let newId: string = ''
      act(() => {
        newId = result.current.createNewChat()
      })

      expect(newId).toMatch(/^session-\d+-[a-z0-9]{2,9}$/)
    })

    it('sets the new session as visibleSessionId', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      let newId: string = ''
      act(() => {
        newId = result.current.createNewChat()
      })

      expect(result.current.visibleSessionId).toBe(newId)
    })

    it('generates unique IDs on subsequent calls', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      let id1: string = ''
      let id2: string = ''
      act(() => {
        id1 = result.current.createNewChat()
      })
      act(() => {
        id2 = result.current.createNewChat()
      })

      expect(id1).not.toBe(id2)
      expect(result.current.visibleSessionId).toBe(id2)
    })
  })

  // -----------------------------------------------------------------------
  // setVisibleSessionId
  // -----------------------------------------------------------------------
  describe('setVisibleSessionId', () => {
    it('updates visibleSessionId', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      act(() => {
        result.current.setVisibleSessionId('some-session-id')
      })

      expect(result.current.visibleSessionId).toBe('some-session-id')
    })

    it('can be set back to null', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      act(() => {
        result.current.setVisibleSessionId('some-session-id')
      })
      act(() => {
        result.current.setVisibleSessionId(null)
      })

      expect(result.current.visibleSessionId).toBeNull()
    })
  })

  // -----------------------------------------------------------------------
  // selectChat
  // -----------------------------------------------------------------------
  describe('selectChat', () => {
    it('sets visibleSessionId to the given session', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      act(() => {
        result.current.selectChat('target-session')
      })

      expect(result.current.visibleSessionId).toBe('target-session')
    })
  })

  // -----------------------------------------------------------------------
  // localStorage persistence
  // -----------------------------------------------------------------------
  describe('localStorage persistence', () => {
    it('persists visibleSessionId to localStorage on change', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      act(() => {
        result.current.setVisibleSessionId('persisted-session')
      })

      await waitFor(() => {
        expect(localStorageMock.setItem).toHaveBeenCalledWith(
          'pikar_current_session_id',
          'persisted-session',
        )
      })
    })

    it('restores visibleSessionId from localStorage on mount', async () => {
      localStorageMock.setItem('pikar_current_session_id', 'restored-session')
      // Clear mock call counts after manual setItem
      localStorageMock.setItem.mockClear()

      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await waitFor(() => {
        expect(result.current.sessionRestored).toBe(true)
      })
      expect(result.current.visibleSessionId).toBe('restored-session')
    })

    it('removes localStorage key when visibleSessionId is set to null', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      act(() => {
        result.current.setVisibleSessionId('some-id')
      })
      act(() => {
        result.current.setVisibleSessionId(null)
      })

      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith(
          'pikar_current_session_id',
        )
      })
    })
  })

  // -----------------------------------------------------------------------
  // Config fetch
  // -----------------------------------------------------------------------
  describe('config fetch', () => {
    it('fetches config from /configuration/session-config on mount', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            max_concurrent_streams: 8,
            memory_eviction_minutes: 60,
            max_active_sessions_in_memory: 50,
          }),
      })

      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await waitFor(() => {
        expect(result.current.config.max_concurrent_streams).toBe(8)
      })
      expect(result.current.config.memory_eviction_minutes).toBe(60)
      expect(result.current.config.max_active_sessions_in_memory).toBe(50)
    })

    it('uses defaults on fetch failure', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await waitFor(() => {
        expect(result.current.sessionRestored).toBe(true)
      })
      expect(result.current.config).toEqual(DEFAULT_SESSION_CONFIG)
    })

    it('merges partial config response with defaults', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            max_concurrent_streams: 10,
            // other fields omitted
          }),
      })

      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await waitFor(() => {
        expect(result.current.config.max_concurrent_streams).toBe(10)
      })
      // Defaults for omitted fields
      expect(result.current.config.memory_eviction_minutes).toBe(
        DEFAULT_SESSION_CONFIG.memory_eviction_minutes,
      )
      expect(result.current.config.max_active_sessions_in_memory).toBe(
        DEFAULT_SESSION_CONFIG.max_active_sessions_in_memory,
      )
    })
  })

  // -----------------------------------------------------------------------
  // Stubs (Task 7 placeholders)
  // -----------------------------------------------------------------------
  describe('stub methods', () => {
    it('deleteChat resolves without error', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await expect(result.current.deleteChat('any-id')).resolves.toBeUndefined()
    })

    it('clearAllChats resolves without error', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await expect(result.current.clearAllChats()).resolves.toBeUndefined()
    })

    it('refreshSessions resolves without error', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await expect(result.current.refreshSessions()).resolves.toBeUndefined()
    })

    it('updateSessionTitle resolves without error', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await expect(
        result.current.updateSessionTitle('id', 'title'),
      ).resolves.toBeUndefined()
    })

    it('updateSessionPreview resolves without error', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await expect(
        result.current.updateSessionPreview('id', 'preview'),
      ).resolves.toBeUndefined()
    })

    it('addSessionOptimistic does not throw', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      expect(() => {
        result.current.addSessionOptimistic({
          id: 'opt-1',
          title: 'Optimistic',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        })
      }).not.toThrow()
    })
  })
})
