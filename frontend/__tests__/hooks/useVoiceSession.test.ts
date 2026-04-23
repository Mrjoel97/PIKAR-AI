// @vitest-environment jsdom
import { renderHook, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/supabase/client', () => ({
  getAccessToken: vi.fn().mockResolvedValue('mock-access-token'),
}))

vi.mock('@/services/api', () => ({
  buildAgentWebSocketUrl: vi.fn((path: string) => `wss://test.example${path}`),
}))

import { useVoiceSession } from '@/hooks/useVoiceSession'

class MockMediaStreamTrack {
  readyState: 'live' | 'ended' = 'live'

  stop = vi.fn(() => {
    this.readyState = 'ended'
  })
}

class MockMediaStream {
  active = true
  private readonly tracks = [new MockMediaStreamTrack()]

  getTracks() {
    return this.tracks
  }
}

class MockAudioNode {
  connect = vi.fn()
  disconnect = vi.fn()
}

class MockGainNode extends MockAudioNode {
  gain = { value: 1 }
}

class MockScriptProcessorNode extends MockAudioNode {
  onaudioprocess: ((event: AudioProcessingEvent) => void) | null = null
}

class MockAudioContext {
  static instances: MockAudioContext[] = []

  state: AudioContextState = 'running'
  readonly sampleRate: number
  readonly destination = {}

  constructor(options?: AudioContextOptions) {
    this.sampleRate = options?.sampleRate ?? 16000
    MockAudioContext.instances.push(this)
  }

  resume = vi.fn(async () => {
    if (this.state !== 'closed') {
      this.state = 'running'
    }
  })

  close = vi.fn(async () => {
    this.state = 'closed'
  })

  createMediaStreamSource = vi.fn((_stream: MediaStream) => {
    if (this.state === 'closed') {
      throw new Error('audio context is closed')
    }
    return new MockAudioNode() as unknown as MediaStreamAudioSourceNode
  })

  createScriptProcessor = vi.fn(() => {
    if (this.state === 'closed') {
      throw new Error('audio context is closed')
    }
    return new MockScriptProcessorNode() as unknown as ScriptProcessorNode
  })

  createGain = vi.fn(() => new MockGainNode() as unknown as GainNode)
}

class MockWebSocket {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSING = 2
  static readonly CLOSED = 3
  static instances: MockWebSocket[] = []

  readonly url: string
  readyState = MockWebSocket.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  send = vi.fn()

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
    queueMicrotask(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen?.(new Event('open'))
    })
  }

  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED
  })

  emitMessage(payload: unknown) {
    this.onmessage?.({
      data: JSON.stringify(payload),
    } as MessageEvent)
  }

  emitClose(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.({
      code,
      reason,
      wasClean: code === 1000,
    } as CloseEvent)
  }
}

describe('useVoiceSession', () => {
  const originalAudioContext = globalThis.AudioContext
  const originalWebSocket = globalThis.WebSocket
  const originalNavigator = globalThis.navigator
  const getUserMedia = vi.fn(async () => new MockMediaStream())
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    MockAudioContext.instances = []
    MockWebSocket.instances = []
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    Object.defineProperty(globalThis, 'AudioContext', {
      configurable: true,
      value: MockAudioContext,
    })
    Object.defineProperty(globalThis, 'WebSocket', {
      configurable: true,
      value: MockWebSocket,
    })
    Object.defineProperty(globalThis, 'navigator', {
      configurable: true,
      value: {
        ...originalNavigator,
        mediaDevices: {
          getUserMedia,
        },
      },
    })
  })

  afterEach(() => {
    Object.defineProperty(globalThis, 'AudioContext', {
      configurable: true,
      value: originalAudioContext,
    })
    Object.defineProperty(globalThis, 'WebSocket', {
      configurable: true,
      value: originalWebSocket,
    })
    Object.defineProperty(globalThis, 'navigator', {
      configurable: true,
      value: originalNavigator,
    })
    consoleErrorSpy.mockRestore()
    vi.clearAllMocks()
  })

  it('ignores stale socket closes from an older connection attempt', async () => {
    const { result } = renderHook(() => useVoiceSession())

    let firstConnectError: Error | null = null
    await act(async () => {
      result.current.connect('session-1').catch((error: Error) => {
        firstConnectError = error
      })
      await Promise.resolve()
    })

    expect(MockWebSocket.instances).toHaveLength(1)

    await act(async () => {
      result.current.connect('session-1').catch(() => undefined)
      await Promise.resolve()
    })

    expect(MockWebSocket.instances).toHaveLength(2)
    expect(MockAudioContext.instances).toHaveLength(4)

    const firstSocket = MockWebSocket.instances[0]
    const secondSocket = MockWebSocket.instances[1]

    await act(async () => {
      firstSocket.emitClose(1005, '')
      await Promise.resolve()
    })

    expect(firstConnectError?.message).toBe('Voice connection superseded')
    expect(MockAudioContext.instances[2]?.state).toBe('running')
    expect(MockAudioContext.instances[3]?.state).toBe('running')

    await act(async () => {
      secondSocket.emitMessage({ type: 'ready' })
      await Promise.resolve()
    })

    expect(result.current.isConnected).toBe(true)
    expect(result.current.error).toBeNull()

    act(() => {
      result.current.disconnect()
    })
  })
})
