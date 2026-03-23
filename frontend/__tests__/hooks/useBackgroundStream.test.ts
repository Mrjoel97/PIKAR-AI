// @vitest-environment jsdom
import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import type { ActiveSessionState } from '@/types/session'
import { createEmptyActiveSession } from '@/types/session'

// ---------------------------------------------------------------------------
// Mocks — vi.mock factories run once; we use mutableState + per-test setup
// to control behaviour without relying on clearAllMocks wiping implementations.
// ---------------------------------------------------------------------------

vi.mock('@microsoft/fetch-event-source', () => ({
  fetchEventSource: vi.fn(),
}))

vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    auth: {
      getSession: () =>
        Promise.resolve({
          data: {
            session: {
              access_token: 'mock-token',
              user: { id: 'user-123' },
            },
          },
        }),
    },
  }),
}))

vi.mock('@/services/widgetDisplay', () => {
  class MockWidgetDisplayService {
    saveWidget() { return { id: 'widget-1' } }
    getSessionWidgets() { return [] }
    clearSessionWidgets() { /* noop */ }
  }
  return {
    WidgetDisplayService: MockWidgetDisplayService,
    dispatchFocusWidget: vi.fn(),
    dispatchWorkspaceActivity: vi.fn(),
  }
})

// ---------------------------------------------------------------------------
// Mutable state that the mocked context hooks read from
// ---------------------------------------------------------------------------

const mockSessionRefs = new Map<string, { current: ActiveSessionState | null }>()
const mockUpdateSessionState = vi.fn()

let mockVisibleSessionId: string | null = null

vi.mock('@/contexts/SessionMapContext', () => ({
  useSessionMap: () => ({
    getActiveSessionRef: (sessionId: string) =>
      mockSessionRefs.get(sessionId) ?? null,
    updateSessionState: (...args: unknown[]) =>
      mockUpdateSessionState(...args),
    activeSessions: new Map(),
    addActiveSession: () => {},
    removeActiveSession: () => {},
    sessions: [],
    setSessions: () => {},
    isLoadingSessions: false,
    setIsLoadingSessions: () => {},
  }),
}))

vi.mock('@/contexts/SessionControlContext', () => ({
  useSessionControl: () => ({
    visibleSessionId: mockVisibleSessionId,
    setVisibleSessionId: () => {},
    sessionRestored: true,
    config: {
      max_concurrent_streams: 4,
      memory_eviction_minutes: 30,
      max_active_sessions_in_memory: 20,
    },
    createNewChat: () => '',
    selectChat: () => {},
    deleteChat: async () => {},
    clearAllChats: async () => {},
    refreshSessions: async () => {},
    updateSessionTitle: async () => {},
    updateSessionPreview: async () => {},
    addSessionOptimistic: () => {},
  }),
}))

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function setupMockSession(
  sessionId: string,
  overrides?: Partial<ActiveSessionState>,
) {
  const session: ActiveSessionState = {
    ...createEmptyActiveSession(sessionId),
    ...overrides,
  }
  mockSessionRefs.set(sessionId, { current: session })
  return mockSessionRefs.get(sessionId)!
}

// ---------------------------------------------------------------------------
// Import after mocks
// ---------------------------------------------------------------------------

import { useBackgroundStream } from '@/hooks/useBackgroundStream'

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useBackgroundStream', () => {
  beforeEach(() => {
    mockSessionRefs.clear()
    mockUpdateSessionState.mockReset()
    vi.mocked(fetchEventSource).mockReset()
    mockVisibleSessionId = null
    process.env.NEXT_PUBLIC_API_URL = 'http://test-api.com'
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
  })

  afterEach(() => {
    vi.useRealTimers()
    delete process.env.NEXT_PUBLIC_API_URL
  })

  // -----------------------------------------------------------------------
  // stopStream
  // -----------------------------------------------------------------------
  describe('stopStream', () => {
    it('aborts the controller and sets status to idle', () => {
      const abortController = new AbortController()
      const abortSpy = vi.spyOn(abortController, 'abort')
      const ref = setupMockSession('session-1', {
        status: 'streaming',
        abortController,
      })

      const { result } = renderHook(() => useBackgroundStream())

      act(() => {
        result.current.stopStream('session-1')
      })

      expect(abortSpy).toHaveBeenCalled()
      expect(ref.current!.status).toBe('idle')
      expect(ref.current!.abortController).toBeNull()
      expect(mockUpdateSessionState).toHaveBeenCalledWith(
        'session-1',
        expect.objectContaining({ status: 'idle', abortController: null }),
      )
    })

    it('is a no-op for non-existent session', () => {
      const { result } = renderHook(() => useBackgroundStream())

      act(() => {
        result.current.stopStream('does-not-exist')
      })

      expect(mockUpdateSessionState).not.toHaveBeenCalled()
    })

    it('is a no-op when session has no abort controller', () => {
      setupMockSession('session-1', { status: 'idle', abortController: null })

      const { result } = renderHook(() => useBackgroundStream())

      act(() => {
        result.current.stopStream('session-1')
      })

      // It still writes idle — that's fine and idempotent
      expect(mockUpdateSessionState).toHaveBeenCalledWith(
        'session-1',
        expect.objectContaining({ status: 'idle' }),
      )
    })
  })

  // -----------------------------------------------------------------------
  // startStream
  // -----------------------------------------------------------------------
  describe('startStream', () => {
    it('calls fetchEventSource with correct params', async () => {
      setupMockSession('session-1')
      mockVisibleSessionId = 'session-1'

      const { result } = renderHook(() => useBackgroundStream())

      await act(async () => {
        await result.current.startStream({
          sessionId: 'session-1',
          message: 'Hello',
          agentMode: 'auto',
        })
      })

      expect(fetchEventSource).toHaveBeenCalledWith(
        'http://test-api.com/a2a/app/run_sse',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            Authorization: 'Bearer mock-token',
            'Content-Type': 'application/json',
          }),
          openWhenHidden: true,
        }),
      )

      // Verify body contents
      const callArgs = vi.mocked(fetchEventSource).mock.calls[0]
      const body = JSON.parse(callArgs[1]!.body as string)
      expect(body.session_id).toBe('session-1')
      expect(body.new_message.parts[0].text).toBe('Hello')
      expect(body.agent_mode).toBe('auto')
      expect(body.user_id).toBe('user-123')
    })

    it('adds agent placeholder message to session messages', async () => {
      const ref = setupMockSession('session-1', {
        messages: [{ role: 'user', text: 'Hello' }],
      })
      mockVisibleSessionId = 'session-1'

      vi.mocked(fetchEventSource).mockResolvedValue(undefined)

      const { result } = renderHook(() => useBackgroundStream())

      await act(async () => {
        await result.current.startStream({
          sessionId: 'session-1',
          message: 'Hello',
          agentMode: 'auto',
        })
      })

      // Should have user msg + agent placeholder
      expect(ref.current!.messages.length).toBeGreaterThanOrEqual(2)
      const agentMsg = ref.current!.messages.find(
        (m) => m.role === 'agent' && m.id?.startsWith('agent-'),
      )
      expect(agentMsg).toBeDefined()
    })

    it('processes onmessage events through sseParser', async () => {
      const ref = setupMockSession('session-1')
      mockVisibleSessionId = 'session-1'

      vi.mocked(fetchEventSource).mockImplementation(async (_url, opts) => {
        if (opts?.onmessage) {
          opts.onmessage({
            event: 'message',
            data: JSON.stringify({
              author: 'ExecutiveAgent',
              content: { parts: [{ text: 'Hi there!' }] },
            }),
          } as any)
        }
      })

      const { result } = renderHook(() => useBackgroundStream())

      await act(async () => {
        await result.current.startStream({
          sessionId: 'session-1',
          message: 'Hello',
          agentMode: 'auto',
        })
      })

      // The agent message should have text
      const agentMsg = ref.current!.messages.find(
        (m) => m.role === 'agent' && m.text === 'Hi there!',
      )
      expect(agentMsg).toBeDefined()
    })

    it('sets hasUnread=true for background sessions on close', async () => {
      const ref = setupMockSession('session-1')
      mockVisibleSessionId = 'other-session' // NOT the one streaming

      vi.mocked(fetchEventSource).mockImplementation(async (_url, opts) => {
        if (opts?.onmessage) {
          opts.onmessage({
            event: 'message',
            data: JSON.stringify({
              content: { parts: [{ text: 'Done' }] },
            }),
          } as any)
        }
      })

      const { result } = renderHook(() => useBackgroundStream())

      await act(async () => {
        await result.current.startStream({
          sessionId: 'session-1',
          message: 'Hello',
          agentMode: 'auto',
        })
      })

      expect(ref.current!.hasUnread).toBe(true)
      expect(mockUpdateSessionState).toHaveBeenCalledWith(
        'session-1',
        expect.objectContaining({ hasUnread: true }),
      )
    })

    it('queues side effects for background sessions', async () => {
      const ref = setupMockSession('session-1')
      mockVisibleSessionId = 'other-session' // Background

      vi.mocked(fetchEventSource).mockImplementation(async (_url, opts) => {
        if (opts?.onmessage) {
          opts.onmessage({
            event: 'message',
            data: JSON.stringify({
              content: { parts: [{ text: 'Working...' }] },
            }),
          } as any)
        }
      })

      const { result } = renderHook(() => useBackgroundStream())

      await act(async () => {
        await result.current.startStream({
          sessionId: 'session-1',
          message: 'Hello',
          agentMode: 'auto',
        })
      })

      // Background sessions should have queued workspace_activity
      expect(ref.current!.pendingActions.length).toBeGreaterThan(0)
    })

    it('calls onStreamComplete callback when stream finishes', async () => {
      setupMockSession('session-1')
      mockVisibleSessionId = 'session-1'

      vi.mocked(fetchEventSource).mockImplementation(async (_url, opts) => {
        if (opts?.onmessage) {
          opts.onmessage({
            event: 'message',
            data: JSON.stringify({
              content: { parts: [{ text: 'Final answer' }] },
            }),
          } as any)
        }
      })

      const onComplete = vi.fn()
      const { result } = renderHook(() => useBackgroundStream())

      await act(async () => {
        await result.current.startStream({
          sessionId: 'session-1',
          message: 'Hello',
          agentMode: 'auto',
          onStreamComplete: onComplete,
        })
      })

      expect(onComplete).toHaveBeenCalledWith('session-1', 'Final answer')
    })

    it('handles fetch errors gracefully', async () => {
      const ref = setupMockSession('session-1')
      mockVisibleSessionId = 'session-1'

      vi.mocked(fetchEventSource).mockRejectedValue(new Error('Network Error'))

      const onError = vi.fn()
      const { result } = renderHook(() => useBackgroundStream())

      // Run the stream and advance all timers to clear retry backoff delays
      await act(async () => {
        const streamPromise = result.current.startStream({
          sessionId: 'session-1',
          message: 'Hello',
          agentMode: 'auto',
          onStreamError: onError,
        })
        await vi.runAllTimersAsync()
        await streamPromise
      })

      expect(ref.current!.status).toBe('error')
      expect(onError).toHaveBeenCalledWith(
        'session-1',
        expect.stringContaining('Error:'),
      )
      // Should have a system error message
      const systemMsg = ref.current!.messages.find((m) => m.role === 'system')
      expect(systemMsg).toBeDefined()
    })

    it('skips ping events', async () => {
      const ref = setupMockSession('session-1')
      mockVisibleSessionId = 'session-1'

      vi.mocked(fetchEventSource).mockImplementation(async (_url, opts) => {
        if (opts?.onmessage) {
          opts.onmessage({ event: 'ping', data: '' } as any)
          opts.onmessage({
            event: 'message',
            data: JSON.stringify({
              content: { parts: [{ text: 'Real data' }] },
            }),
          } as any)
        }
      })

      const { result } = renderHook(() => useBackgroundStream())

      await act(async () => {
        await result.current.startStream({
          sessionId: 'session-1',
          message: 'Hello',
          agentMode: 'auto',
        })
      })

      // Only the real message should have been processed
      const agentMsg = ref.current!.messages.find(
        (m) => m.role === 'agent' && m.text,
      )
      expect(agentMsg?.text).toBe('Real data')
    })

    it('sets status to idle after successful completion', async () => {
      const ref = setupMockSession('session-1')
      mockVisibleSessionId = 'session-1'

      vi.mocked(fetchEventSource).mockResolvedValue(undefined)

      const { result } = renderHook(() => useBackgroundStream())

      await act(async () => {
        await result.current.startStream({
          sessionId: 'session-1',
          message: 'Hello',
          agentMode: 'auto',
        })
      })

      expect(ref.current!.status).toBe('idle')
      expect(ref.current!.abortController).toBeNull()
    })

    // -----------------------------------------------------------------------
    // SSE auto-reconnection
    // -----------------------------------------------------------------------
    describe('SSE auto-reconnection', () => {
      it('retries on transient error and succeeds on second attempt', async () => {
        setupMockSession('session-1', {
          messages: [{ role: 'user', text: 'Hello' }],
        })
        mockVisibleSessionId = 'session-1'

        let callCount = 0
        vi.mocked(fetchEventSource).mockImplementation(async (_url, opts) => {
          callCount++
          if (callCount === 1) {
            // First call: onerror fires, which triggers the throw
            if (opts?.onerror) {
              opts.onerror(new Error('Network Error'))
            }
            throw new Error('Network Error')
          }
          // Second call: succeeds with a message
          if (opts?.onmessage) {
            opts.onmessage({
              event: 'message',
              data: JSON.stringify({
                content: { parts: [{ text: 'Recovered!' }] },
              }),
            } as any)
          }
        })

        const onComplete = vi.fn()
        const { result } = renderHook(() => useBackgroundStream())

        await act(async () => {
          const streamPromise = result.current.startStream({
            sessionId: 'session-1',
            message: 'Hello',
            agentMode: 'auto',
            onStreamComplete: onComplete,
          })
          await vi.runAllTimersAsync()
          await streamPromise
        })

        // fetchEventSource should have been called twice (initial + 1 retry)
        expect(callCount).toBe(2)
        // Stream should end successfully
        expect(onComplete).toHaveBeenCalledWith('session-1', 'Recovered!')
      })

      it('exhausts all retries and reports error after MAX_RETRIES failures', async () => {
        const ref = setupMockSession('session-1')
        mockVisibleSessionId = 'session-1'

        // Always fail — will be called 1 (initial) + 3 (retries) = 4 times
        vi.mocked(fetchEventSource).mockRejectedValue(new Error('Network Error'))

        const onError = vi.fn()
        const { result } = renderHook(() => useBackgroundStream())

        await act(async () => {
          const streamPromise = result.current.startStream({
            sessionId: 'session-1',
            message: 'Hello',
            agentMode: 'auto',
            onStreamError: onError,
          })
          await vi.runAllTimersAsync()
          await streamPromise
        })

        // Should have retried exactly 3 times after the initial attempt = 4 total calls
        expect(vi.mocked(fetchEventSource).mock.calls.length).toBe(4)
        // Final status should be error
        expect(ref.current!.status).toBe('error')
        expect(onError).toHaveBeenCalledWith(
          'session-1',
          expect.stringContaining('Error:'),
        )
      })

      it('does not retry when abort signal is triggered', async () => {
        setupMockSession('session-1')
        mockVisibleSessionId = 'session-1'

        // Replace AbortController with a version that is pre-aborted,
        // so signal.aborted is true when the inner catch checks it.
        const OriginalAbortController = globalThis.AbortController
        class PreAbortedController extends OriginalAbortController {
          constructor() {
            super()
            this.abort()
          }
        }
        globalThis.AbortController = PreAbortedController as unknown as typeof AbortController

        vi.mocked(fetchEventSource).mockRejectedValue(
          new DOMException('Aborted', 'AbortError'),
        )

        const onError = vi.fn()
        const { result } = renderHook(() => useBackgroundStream())

        try {
          await act(async () => {
            await result.current.startStream({
              sessionId: 'session-1',
              message: 'Hello',
              agentMode: 'auto',
              onStreamError: onError,
            })
          })
        } finally {
          // Always restore, even if the test throws
          globalThis.AbortController = OriginalAbortController
        }

        // Abort should not retry — fetchEventSource called only once
        expect(vi.mocked(fetchEventSource).mock.calls.length).toBe(1)
        // No error message shown for user-initiated aborts
        expect(onError).not.toHaveBeenCalled()
      })

      it('sets reconnecting metadata on agent message during retry', async () => {
        const ref = setupMockSession('session-1', {
          messages: [{ role: 'user', text: 'Hello' }],
        })
        mockVisibleSessionId = 'session-1'

        let callCount = 0
        vi.mocked(fetchEventSource).mockImplementation(async (_url, opts) => {
          callCount++
          if (callCount === 1) {
            if (opts?.onerror) {
              opts.onerror(new Error('Network blip'))
            }
            throw new Error('Network blip')
          }
          // Second attempt: no-op (clean close, no messages)
        })

        const { result } = renderHook(() => useBackgroundStream())

        // Track calls to updateSessionState to detect the reconnecting update
        const reconnectingCalls: unknown[] = []
        mockUpdateSessionState.mockImplementation((_id: string, update: Record<string, unknown>) => {
          const msgs = update.messages as Array<{ role: string; metadata?: Record<string, unknown> }> | undefined
          if (msgs) {
            const hasReconnecting = msgs.some(
              (m) => m.role === 'agent' && m.metadata?.reconnecting === true,
            )
            if (hasReconnecting) reconnectingCalls.push(update)
          }
        })

        await act(async () => {
          const streamPromise = result.current.startStream({
            sessionId: 'session-1',
            message: 'Hello',
            agentMode: 'auto',
          })
          await vi.runAllTimersAsync()
          await streamPromise
        })

        // The reconnecting indicator should have been set during the retry wait
        expect(reconnectingCalls.length).toBeGreaterThan(0)
      })

      it('clears reconnecting metadata when stream recovers', async () => {
        const ref = setupMockSession('session-1', {
          messages: [{ role: 'user', text: 'Hello' }],
        })
        mockVisibleSessionId = 'session-1'

        let callCount = 0
        vi.mocked(fetchEventSource).mockImplementation(async (_url, opts) => {
          callCount++
          if (callCount === 1) {
            if (opts?.onerror) opts.onerror(new Error('blip'))
            throw new Error('blip')
          }
          // Second attempt: deliver a message (triggers reconnecting=false clear)
          if (opts?.onmessage) {
            opts.onmessage({
              event: 'message',
              data: JSON.stringify({
                content: { parts: [{ text: 'Back online' }] },
              }),
            } as any)
          }
        })

        const { result } = renderHook(() => useBackgroundStream())

        await act(async () => {
          const streamPromise = result.current.startStream({
            sessionId: 'session-1',
            message: 'Hello',
            agentMode: 'auto',
          })
          await vi.runAllTimersAsync()
          await streamPromise
        })

        // After recovery, the agent message should NOT have reconnecting=true
        const agentMsg = ref.current!.messages.find((m) => m.role === 'agent')
        expect(agentMsg?.metadata?.reconnecting).not.toBe(true)
      })
    })
  })
})
