// @vitest-environment jsdom
import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { ActiveSessionState } from '@/types/session'
import { createEmptyActiveSession } from '@/types/session'

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Mock Supabase
vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { id: 'user-123' } },
      }),
      getSession: vi.fn().mockResolvedValue({
        data: {
          session: {
            access_token: 'mock-token',
            user: { id: 'user-123' },
          },
        },
      }),
    },
  })),
  getAuthenticatedUser: vi.fn().mockResolvedValue({ id: 'user-123' }),
}))

// Mock loadSessionHistory
vi.mock('@/lib/sessionHistory', () => ({
  loadSessionHistory: vi.fn().mockResolvedValue([]),
}))

// Mock widgetDisplay
vi.mock('@/services/widgetDisplay', () => {
  class MockWidgetDisplayService {
    saveWidget() { return { id: 'widget-1' } }
    getSessionWidgets() { return [] }
    clearSessionWidgets() { /* noop */ }
    updateWidgetState() { /* noop */ }
    pinWidget() { /* noop */ }
  }
  return {
    WidgetDisplayService: MockWidgetDisplayService,
    dispatchFocusWidget: vi.fn(),
    dispatchWorkspaceActivity: vi.fn(),
    isWorkspaceCanvasWidget: vi.fn((widget) => widget?.type !== 'morning_briefing'),
  }
})

// ---------------------------------------------------------------------------
// Mutable state for mocked context hooks
// ---------------------------------------------------------------------------

let mockActiveSessions = new Map<string, ActiveSessionState>()
const mockUpdateSessionState = vi.fn((sessionId: string, updates: Partial<ActiveSessionState>) => {
  const existing = mockActiveSessions.get(sessionId)
  if (existing) {
    const updated = { ...existing, ...updates }
    mockActiveSessions.set(sessionId, updated)
  }
})
const mockAddActiveSession = vi.fn((sessionId: string, overrides?: Partial<ActiveSessionState>) => {
  if (!mockActiveSessions.has(sessionId)) {
    const session = { ...createEmptyActiveSession(sessionId), ...overrides, sessionId }
    mockActiveSessions.set(sessionId, session)
  }
})

let mockVisibleSessionId: string | null = null
const mockStartStream = vi.fn()
const mockStopStream = vi.fn()
const mockEnforceCapBeforeStream = vi.fn().mockReturnValue(null)

vi.mock('@/contexts/SessionMapContext', () => ({
  useSessionMap: () => ({
    activeSessions: mockActiveSessions,
    updateSessionState: mockUpdateSessionState,
    addActiveSession: mockAddActiveSession,
    removeActiveSession: vi.fn(),
    getActiveSessionRef: vi.fn(),
    sessions: [],
    setSessions: vi.fn(),
    isLoadingSessions: false,
    setIsLoadingSessions: vi.fn(),
  }),
}))

vi.mock('@/contexts/SessionControlContext', () => ({
  useSessionControl: () => ({
    visibleSessionId: mockVisibleSessionId,
    setVisibleSessionId: vi.fn(),
    sessionRestored: true,
    config: {
      max_concurrent_streams: 4,
      memory_eviction_minutes: 30,
      max_active_sessions_in_memory: 20,
    },
    createNewChat: vi.fn().mockReturnValue('new-session-id'),
    selectChat: vi.fn(),
    deleteChat: vi.fn().mockResolvedValue(undefined),
    clearAllChats: vi.fn().mockResolvedValue(undefined),
    refreshSessions: vi.fn().mockResolvedValue(undefined),
    updateSessionTitle: vi.fn().mockResolvedValue(undefined),
    updateSessionPreview: vi.fn().mockResolvedValue(undefined),
    addSessionOptimistic: vi.fn(),
  }),
}))

vi.mock('@/hooks/useBackgroundStream', () => ({
  useBackgroundStream: () => ({
    startStream: mockStartStream,
    stopStream: mockStopStream,
  }),
}))

vi.mock('@/hooks/useStreamCap', () => ({
  useStreamCap: () => ({
    enforceCapBeforeStream: mockEnforceCapBeforeStream,
  }),
}))

// ---------------------------------------------------------------------------
// Import after mocks
// ---------------------------------------------------------------------------

import { useAgentChat } from '@/hooks/useAgentChat'

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useAgentChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockActiveSessions = new Map()
    mockVisibleSessionId = null
    mockStartStream.mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // -----------------------------------------------------------------------
  // Initialization
  // -----------------------------------------------------------------------
  it('initializes with a welcome message', () => {
    const { result } = renderHook(() => useAgentChat())

    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0].role).toBe('agent')
    expect(result.current.messages[0].text).toContain('Pikar AI')
    expect(result.current.isStreaming).toBe(false)
  })

  it('returns custom agent name in welcome message', () => {
    const { result } = renderHook(() =>
      useAgentChat({ customAgentName: 'Test Agent' })
    )

    expect(result.current.messages[0].text).toContain('Test Agent')
  })

  it('adds session to activeSession map on mount', () => {
    renderHook(() => useAgentChat())

    expect(mockAddActiveSession).toHaveBeenCalled()
  })

  it('returns isStreaming=false when session is idle', () => {
    const sessionId = 'test-session'
    mockActiveSessions.set(sessionId, {
      ...createEmptyActiveSession(sessionId),
      status: 'idle',
      messages: [{ role: 'agent', text: 'Hello' }],
    })
    mockVisibleSessionId = sessionId

    const { result } = renderHook(() =>
      useAgentChat({ initialSessionId: sessionId })
    )

    expect(result.current.isStreaming).toBe(false)
  })

  it('returns isStreaming=true when session is streaming', () => {
    const sessionId = 'test-session'
    mockActiveSessions.set(sessionId, {
      ...createEmptyActiveSession(sessionId),
      status: 'streaming',
      messages: [{ role: 'agent', text: 'Hello' }],
    })
    mockVisibleSessionId = sessionId

    const { result } = renderHook(() =>
      useAgentChat({ initialSessionId: sessionId })
    )

    expect(result.current.isStreaming).toBe(true)
  })

  // -----------------------------------------------------------------------
  // Return type shape
  // -----------------------------------------------------------------------
  it('returns all expected properties', () => {
    const { result } = renderHook(() => useAgentChat())

    expect(result.current).toHaveProperty('messages')
    expect(result.current).toHaveProperty('sendMessage')
    expect(result.current).toHaveProperty('addMessage')
    expect(result.current).toHaveProperty('isStreaming')
    expect(result.current).toHaveProperty('toggleWidgetMinimized')
    expect(result.current).toHaveProperty('isLoadingHistory')
    expect(result.current).toHaveProperty('pinWidget')
    expect(result.current).toHaveProperty('sessionId')
    expect(result.current).toHaveProperty('getSessionId')
    expect(result.current).toHaveProperty('stopGeneration')

    expect(typeof result.current.sendMessage).toBe('function')
    expect(typeof result.current.addMessage).toBe('function')
    expect(typeof result.current.toggleWidgetMinimized).toBe('function')
    expect(typeof result.current.pinWidget).toBe('function')
    expect(typeof result.current.getSessionId).toBe('function')
    expect(typeof result.current.stopGeneration).toBe('function')
    expect(typeof result.current.sessionId).toBe('string')
    expect(typeof result.current.isStreaming).toBe('boolean')
    expect(typeof result.current.isLoadingHistory).toBe('boolean')
    expect(Array.isArray(result.current.messages)).toBe(true)
  })

  // -----------------------------------------------------------------------
  // Backward compatibility
  // -----------------------------------------------------------------------
  it('accepts string argument for backward compatibility', () => {
    const { result } = renderHook(() => useAgentChat('my-session'))

    expect(result.current.sessionId).toBeTruthy()
  })

  it('accepts options object', () => {
    const { result } = renderHook(() =>
      useAgentChat({
        initialSessionId: 'my-session',
        customAgentName: 'Custom Agent',
      })
    )

    expect(result.current.sessionId).toBeTruthy()
  })

  // -----------------------------------------------------------------------
  // sendMessage
  // -----------------------------------------------------------------------
  it('delegates to startStream when sendMessage is called', async () => {
    const sessionId = 'test-session'
    mockActiveSessions.set(sessionId, {
      ...createEmptyActiveSession(sessionId),
      messages: [{ id: 'welcome-message', role: 'agent', text: 'Hello' }],
    })
    mockVisibleSessionId = sessionId

    const { result } = renderHook(() =>
      useAgentChat({ initialSessionId: sessionId })
    )

    await act(async () => {
      result.current.sendMessage('Hello Agent', 'auto')
    })

    // The user message should have been added to the session
    expect(mockUpdateSessionState).toHaveBeenCalledWith(
      sessionId,
      expect.objectContaining({
        messages: expect.arrayContaining([
          expect.objectContaining({ role: 'user', text: 'Hello Agent' }),
        ]),
      })
    )

    // startStream should have been called
    expect(mockStartStream).toHaveBeenCalledWith(
      expect.objectContaining({
        sessionId,
        message: 'Hello Agent',
        agentMode: 'auto',
      })
    )
  })

  it('enforces stream cap before starting', async () => {
    const sessionId = 'test-session'
    mockActiveSessions.set(sessionId, {
      ...createEmptyActiveSession(sessionId),
      messages: [{ id: 'welcome-message', role: 'agent', text: 'Hello' }],
    })
    mockVisibleSessionId = sessionId

    const { result } = renderHook(() =>
      useAgentChat({ initialSessionId: sessionId })
    )

    await act(async () => {
      result.current.sendMessage('Hello', 'auto')
    })

    expect(mockEnforceCapBeforeStream).toHaveBeenCalled()
  })

  it('ignores empty messages', async () => {
    const { result } = renderHook(() => useAgentChat())

    await act(async () => {
      result.current.sendMessage('  ', 'auto')
    })

    expect(mockStartStream).not.toHaveBeenCalled()
  })

  // -----------------------------------------------------------------------
  // addMessage
  // -----------------------------------------------------------------------
  it('addMessage appends to session messages', () => {
    const sessionId = 'test-session'
    mockActiveSessions.set(sessionId, {
      ...createEmptyActiveSession(sessionId),
      messages: [{ id: 'welcome-message', role: 'agent', text: 'Hello' }],
    })
    mockVisibleSessionId = sessionId

    const { result } = renderHook(() =>
      useAgentChat({ initialSessionId: sessionId })
    )

    act(() => {
      result.current.addMessage({ role: 'system', text: 'System message' })
    })

    expect(mockUpdateSessionState).toHaveBeenCalledWith(
      sessionId,
      expect.objectContaining({
        messages: expect.arrayContaining([
          expect.objectContaining({ role: 'system', text: 'System message' }),
        ]),
      })
    )
  })

  // -----------------------------------------------------------------------
  // stopGeneration
  // -----------------------------------------------------------------------
  it('stopGeneration calls stopStream and adds cancellation message', () => {
    const sessionId = 'test-session'
    mockActiveSessions.set(sessionId, {
      ...createEmptyActiveSession(sessionId),
      status: 'streaming',
      messages: [
        { role: 'user', text: 'Hello' },
        { id: 'agent-1', role: 'agent', text: 'Working...', isThinking: true },
      ],
    })
    mockVisibleSessionId = sessionId

    const { result } = renderHook(() =>
      useAgentChat({ initialSessionId: sessionId })
    )

    act(() => {
      result.current.stopGeneration()
    })

    expect(mockStopStream).toHaveBeenCalledWith(sessionId)
    expect(mockUpdateSessionState).toHaveBeenCalledWith(
      sessionId,
      expect.objectContaining({
        status: 'idle',
        messages: expect.arrayContaining([
          expect.objectContaining({
            role: 'system',
            text: 'Task cancelled by user. Queued messages were aborted.',
          }),
        ]),
      })
    )
  })

  // -----------------------------------------------------------------------
  // getSessionId
  // -----------------------------------------------------------------------
  it('getSessionId returns the current session id', () => {
    const sessionId = 'test-session'
    mockVisibleSessionId = sessionId

    const { result } = renderHook(() =>
      useAgentChat({ initialSessionId: sessionId })
    )

    expect(result.current.getSessionId()).toBe(sessionId)
    expect(result.current.sessionId).toBe(sessionId)
  })

  // -----------------------------------------------------------------------
  // Session ID resolution
  // -----------------------------------------------------------------------
  it('prefers visibleSessionId over initialSessionId', () => {
    mockVisibleSessionId = 'visible-session'

    const { result } = renderHook(() =>
      useAgentChat({ initialSessionId: 'initial-session' })
    )

    expect(result.current.sessionId).toBe('visible-session')
  })

  it('falls back to initialSessionId when visibleSessionId is null', () => {
    mockVisibleSessionId = null

    const { result } = renderHook(() =>
      useAgentChat({ initialSessionId: 'initial-session' })
    )

    expect(result.current.sessionId).toBe('initial-session')
  })

  it('generates a fallback session id when no ids provided', () => {
    mockVisibleSessionId = null

    const { result } = renderHook(() => useAgentChat())

    expect(result.current.sessionId).toMatch(/^session-/)
  })

  // -----------------------------------------------------------------------
  // onSessionStarted callback
  // -----------------------------------------------------------------------
  it('fires onSessionStarted on first message for new sessions', async () => {
    const onSessionStarted = vi.fn()
    const sessionId = 'new-session'
    mockActiveSessions.set(sessionId, {
      ...createEmptyActiveSession(sessionId),
      messages: [{ id: 'welcome-message', role: 'agent', text: 'Hello' }],
    })
    mockVisibleSessionId = sessionId

    const { result } = renderHook(() =>
      useAgentChat({
        customAgentName: 'Test',
        onSessionStarted,
      })
    )

    await act(async () => {
      result.current.sendMessage('First message', 'auto')
    })

    expect(onSessionStarted).toHaveBeenCalledWith(
      sessionId,
      'First message'
    )
  })
})
