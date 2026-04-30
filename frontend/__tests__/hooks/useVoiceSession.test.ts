// @vitest-environment jsdom
import { renderHook, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/supabase/client', () => ({
  getAccessToken: vi.fn().mockResolvedValue('mock-access-token'),
}))

vi.mock('@/services/api', () => ({
  buildAgentWebSocketUrl: vi.fn((path: string) => `wss://test.example${path}`),
}))

import { drainPlaybackQueue, useVoiceSession } from '@/hooks/useVoiceSession'

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

class MockAudioBuffer {
  copyToChannel = vi.fn()
}

class MockAudioBufferSourceNode extends MockAudioNode {
  static autoFinish = true

  buffer: AudioBuffer | null = null
  onended: (() => void) | null = null
  start = vi.fn(() => {
    if (MockAudioBufferSourceNode.autoFinish) {
      queueMicrotask(() => this.onended?.())
    }
  })
  stop = vi.fn()
}

class MockAudioContext {
  static instances: MockAudioContext[] = []

  state: AudioContextState = 'running'
  readonly sampleRate: number
  readonly destination = {}
  lastScriptProcessor: MockScriptProcessorNode | null = null

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
    const node = new MockScriptProcessorNode()
    this.lastScriptProcessor = node
    return node as unknown as ScriptProcessorNode
  })

  createGain = vi.fn(() => new MockGainNode() as unknown as GainNode)
  createBuffer = vi.fn(() => new MockAudioBuffer() as unknown as AudioBuffer)
  createBufferSource = vi.fn(
    () => new MockAudioBufferSourceNode() as unknown as AudioBufferSourceNode,
  )
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
    MockAudioBufferSourceNode.autoFinish = true
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
    vi.useRealTimers()
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
    expect(result.current.error).toBeNull()
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

  it('keeps the user turn open for server-side VAD instead of sending audio_stream_end mid-session', async () => {
    const { result } = renderHook(() => useVoiceSession())

    const pending = result.current.connect('session-quiet-turn')
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0))
      await new Promise((resolve) => setTimeout(resolve, 0))
    })

    const socket = MockWebSocket.instances[0]
    expect(socket).toBeDefined()

    await act(async () => {
      socket.emitMessage({ type: 'ready' })
      await pending
    })

    const captureContext = MockAudioContext.instances[0]
    const scriptNode = captureContext?.lastScriptProcessor
    expect(scriptNode?.onaudioprocess).toBeTypeOf('function')

    const quietChunk = new Float32Array(4096).fill(0.0045)
    const sentTypes = () =>
      socket.send.mock.calls.map(([payload]) => JSON.parse(payload as string).type)

    act(() => {
      scriptNode?.onaudioprocess?.({
        inputBuffer: {
          getChannelData: () => quietChunk,
        },
      } as AudioProcessingEvent)
    })

    expect(sentTypes()).toContain('audio')
    expect(sentTypes()).not.toContain('audio_stream_end')

    act(() => {
      result.current.disconnect()
    })
  })

  it('merges queued playback chunks into a smoother buffer', () => {
    const queue = [
      new Float32Array([0.1, 0.2]),
      new Float32Array([0.3, 0.4]),
      new Float32Array([0.5, 0.6]),
    ]

    const merged = drainPlaybackQueue(queue, 4)

    expect(Array.from(merged ?? [])).toHaveLength(4)
    expect(Array.from(merged ?? []).map((value) => Number(value.toFixed(3)))).toEqual([
      0.1,
      0.2,
      0.3,
      0.4,
    ])
    expect(queue).toHaveLength(1)
    expect(Array.from(queue[0]).map((value) => Number(value.toFixed(3)))).toEqual([
      0.5,
      0.6,
    ])
  })

  it('unlocks mic capture as soon as the server sends waiting_for_input', async () => {
    MockAudioBufferSourceNode.autoFinish = false

    const { result } = renderHook(() => useVoiceSession())

    const pending = result.current.connect('session-turn-handoff')
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0))
      await new Promise((resolve) => setTimeout(resolve, 0))
    })

    const socket = MockWebSocket.instances[0]
    expect(socket).toBeDefined()

    await act(async () => {
      socket.emitMessage({ type: 'ready' })
      await pending
    })

    const captureContext = MockAudioContext.instances[0]
    const scriptNode = captureContext?.lastScriptProcessor
    expect(scriptNode?.onaudioprocess).toBeTypeOf('function')

    await act(async () => {
      socket.emitMessage({
        type: 'audio',
        data: 'AAAAAA==',
        mime_type: 'audio/pcm;rate=24000',
      })
      await new Promise((resolve) => setTimeout(resolve, 300))
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(result.current.isAgentSpeaking).toBe(true)
    const callsBeforeMic = socket.send.mock.calls.length

    await act(async () => {
      socket.emitMessage({ type: 'waiting_for_input' })
      await Promise.resolve()
      await Promise.resolve()
    })

    const userChunk = new Float32Array(4096).fill(0.01)
    act(() => {
      scriptNode?.onaudioprocess?.({
        inputBuffer: {
          getChannelData: () => userChunk,
        },
      } as AudioProcessingEvent)
    })

    const laterTypes = socket.send.mock.calls
      .slice(callsBeforeMic)
      .map(([payload]) => JSON.parse(payload as string).type)
    expect(laterTypes).toContain('audio')

    act(() => {
      result.current.disconnect()
    })
  })

  describe('noise-floor cutoff (HOTFIX-02)', () => {
    /**
     * Fill a Float32Array with sign-alternating samples so its mean is zero
     * and its RMS equals |value|. Length 128 matches the AudioWorklet block
     * size noted in 84-RESEARCH.md § Risks #4; ScriptProcessor uses 4096 in
     * production but the cutoff is computed per-call on whatever block the
     * harness pushes — 128 is a representative worklet-sized chunk.
     */
    const makeFloat32ChunkAtRMS = (rms: number, length = 128): Float32Array => {
      const chunk = new Float32Array(length)
      for (let i = 0; i < length; i++) {
        chunk[i] = i % 2 === 0 ? rms : -rms
      }
      return chunk
    }

    /**
     * Drive the hook to the post-intro state where the mic gate is open:
     *  1. Connect, await ready
     *  2. Emit one agent audio chunk (autoFinish on MockAudioBufferSourceNode
     *     causes onended to fire on the next microtask after start())
     *  3. Emit turn_complete so remoteTurnCompleteRef flips true after the
     *     decode chain settles
     *
     * Returns { socket, scriptNode } for pushing user-speech chunks.
     */
    const driveToPostIntro = async (
      sessionId: string,
      hookResult: { current: ReturnType<typeof useVoiceSession> },
    ) => {
      const pending = hookResult.current.connect(sessionId)
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0))
        await new Promise((resolve) => setTimeout(resolve, 0))
      })
      const socket = MockWebSocket.instances[MockWebSocket.instances.length - 1]
      expect(socket).toBeDefined()

      await act(async () => {
        socket.emitMessage({ type: 'ready' })
        await pending
      })

      const captureContext =
        MockAudioContext.instances[MockAudioContext.instances.length - 2]
      const scriptNode = captureContext?.lastScriptProcessor
      expect(scriptNode?.onaudioprocess).toBeTypeOf('function')

      // Drive one agent audio chunk → autoFinish fires onended → playback
      // queue drains → isPlayingRef returns to false. Then turn_complete
      // chains onto the decode promise to flip remoteTurnCompleteRef true.
      await act(async () => {
        socket.emitMessage({
          type: 'audio',
          data: 'AAAAAA==',
          mime_type: 'audio/pcm;rate=24000',
        })
        // Wait past AGENT_RESPONSE_DELAY_MS (250ms) for pendingTurnDelay to fire
        await new Promise((resolve) => setTimeout(resolve, 300))
        await Promise.resolve()
        await Promise.resolve()
      })

      await act(async () => {
        socket.emitMessage({ type: 'turn_complete' })
        await Promise.resolve()
        await Promise.resolve()
      })

      return { socket, scriptNode: scriptNode! }
    }

    const pushChunk = (
      scriptNode: MockScriptProcessorNode,
      chunk: Float32Array,
    ) => {
      act(() => {
        scriptNode.onaudioprocess?.({
          inputBuffer: {
            getChannelData: () => chunk,
          },
        } as unknown as AudioProcessingEvent)
      })
    }

    const audioSendCount = (socket: MockWebSocket): number =>
      socket.send.mock.calls.filter(
        ([payload]) =>
          (JSON.parse(payload as string) as { type?: string }).type === 'audio',
      ).length

    it('forwards user speech (RMS > floor) after intro onended fires', async () => {
      const { result } = renderHook(() => useVoiceSession())
      const { socket, scriptNode } = await driveToPostIntro(
        'session-rms-above-floor',
        result,
      )

      const before = audioSendCount(socket)
      pushChunk(scriptNode, makeFloat32ChunkAtRMS(0.05))
      const after = audioSendCount(socket)

      expect(after).toBe(before + 1)

      act(() => {
        result.current.disconnect()
      })
    })

    it('drops sub-noise-floor chunks so server VAD can close the turn', async () => {
      const { result } = renderHook(() => useVoiceSession())
      const { socket, scriptNode } = await driveToPostIntro(
        'session-rms-below-floor',
        result,
      )

      // Sub-floor ambient: 0.001 RMS — below 0.003 default threshold.
      const baseline = audioSendCount(socket)
      pushChunk(scriptNode, makeFloat32ChunkAtRMS(0.001))
      expect(audioSendCount(socket)).toBe(baseline)

      // Real speech: 0.05 RMS — must pass.
      pushChunk(scriptNode, makeFloat32ChunkAtRMS(0.05))
      expect(audioSendCount(socket)).toBe(baseline + 1)

      // Another sub-floor chunk: must NOT pass.
      pushChunk(scriptNode, makeFloat32ChunkAtRMS(0.001))
      expect(audioSendCount(socket)).toBe(baseline + 1)

      act(() => {
        result.current.disconnect()
      })
    })

    it('completes a 4-turn conversation cycle without permanent gating', async () => {
      const { result } = renderHook(() => useVoiceSession())
      const { socket, scriptNode } = await driveToPostIntro(
        'session-four-turns',
        result,
      )

      // Loop: each iteration represents one full cycle (user-speech →
      // agent-audio + onended → turn_complete → next user turn open).
      // Iteration 0 already had the intro driven by driveToPostIntro;
      // we run 4 more user→agent cycles to total ≥4 turns.
      for (let cycle = 0; cycle < 4; cycle++) {
        // User speaks — chunk MUST pass the gate.
        const before = audioSendCount(socket)
        pushChunk(scriptNode, makeFloat32ChunkAtRMS(0.05))
        expect(audioSendCount(socket)).toBe(before + 1)

        // Agent responds (one chunk + autoFinish onended).
        await act(async () => {
          socket.emitMessage({
            type: 'audio',
            data: 'AAAAAA==',
            mime_type: 'audio/pcm;rate=24000',
          })
          await new Promise((resolve) => setTimeout(resolve, 300))
          await Promise.resolve()
          await Promise.resolve()
        })

        // Server signals turn complete — gate must reopen.
        await act(async () => {
          socket.emitMessage({ type: 'turn_complete' })
          await Promise.resolve()
          await Promise.resolve()
        })
      }

      // After 4 cycles, gate must still open for fresh user speech.
      const finalBefore = audioSendCount(socket)
      pushChunk(scriptNode, makeFloat32ChunkAtRMS(0.05))
      expect(audioSendCount(socket)).toBe(finalBefore + 1)

      act(() => {
        result.current.disconnect()
      })
    })

    it('stale remote activity does not suppress mic during user speech', async () => {
      const { result } = renderHook(() => useVoiceSession())
      const { socket, scriptNode } = await driveToPostIntro(
        'session-stale-activity',
        result,
      )

      // User starts speaking — chunk passes.
      const before = audioSendCount(socket)
      pushChunk(scriptNode, makeFloat32ChunkAtRMS(0.05))
      expect(audioSendCount(socket)).toBe(before + 1)

      // Stray late-arriving 'transcript' event (a server echo for the
      // closed agent turn). In the OLD wider gate this bumped
      // lastRemoteActivityAtRef and re-latched the mic mid-utterance.
      // The narrow gate must ignore it.
      await act(async () => {
        socket.emitMessage({ type: 'transcript', text: 'stray echo' })
        await Promise.resolve()
        await Promise.resolve()
      })

      // User keeps speaking — must still pass (no re-latch).
      pushChunk(scriptNode, makeFloat32ChunkAtRMS(0.05))
      expect(audioSendCount(socket)).toBe(before + 2)

      act(() => {
        result.current.disconnect()
      })
    })

    it('keeps the half-duplex gate narrow (does not check queue/pending/tail)', async () => {
      // Guard-rail: arrange a state where playbackQueueRef.length > 0 AND
      // pendingTurnDelayRef !== null AND lastRemoteActivityAtRef is recent,
      // BUT isPlayingRef === false. The narrow gate must allow user speech
      // through. If a future PR widens the gate per SC4 verbatim, the chunk
      // would be suppressed and this test fails — surfacing the
      // architectural disagreement explicitly.
      //
      // We achieve this state by disabling autoFinish so the buffer source
      // never finishes (isPlayingRef stays false BEFORE pendingTurnDelay
      // fires) and pushing a user chunk during the AGENT_RESPONSE_DELAY_MS
      // window. At that moment: pendingTurnDelay is set, queue has chunks,
      // lastRemoteActivityAtRef is now-ish — but isPlayingRef is still false.
      MockAudioBufferSourceNode.autoFinish = false

      const { result } = renderHook(() => useVoiceSession())

      const pending = result.current.connect('session-narrow-gate-guard')
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 0))
        await new Promise((resolve) => setTimeout(resolve, 0))
      })
      const socket = MockWebSocket.instances[MockWebSocket.instances.length - 1]
      expect(socket).toBeDefined()

      await act(async () => {
        socket.emitMessage({ type: 'ready' })
        await pending
      })

      const captureContext =
        MockAudioContext.instances[MockAudioContext.instances.length - 2]
      const scriptNode = captureContext?.lastScriptProcessor
      expect(scriptNode?.onaudioprocess).toBeTypeOf('function')

      // Emit an agent audio chunk WITHOUT advancing past pendingTurnDelay.
      // Decode chain pushes onto the queue; pendingTurnDelay is set.
      // isPlayingRef remains false (playNextChunk hasn't been called yet
      // because the 250ms timer is still pending).
      await act(async () => {
        socket.emitMessage({
          type: 'audio',
          data: 'AAAAAA==',
          mime_type: 'audio/pcm;rate=24000',
        })
        // Allow the decode promise to settle but stay BELOW the 250ms
        // pendingTurnDelay so isPlayingRef remains false.
        await Promise.resolve()
        await Promise.resolve()
        await new Promise((resolve) => setTimeout(resolve, 50))
      })

      // At this point: isPlayingRef === false (timer pending),
      // playbackQueueRef.length > 0, pendingTurnDelayRef !== null,
      // lastRemoteActivityAtRef is recent. SC4 verbatim would close the
      // gate here. The narrow gate must let the chunk through.
      const before = audioSendCount(socket!)
      pushChunk(scriptNode!, makeFloat32ChunkAtRMS(0.05))
      expect(audioSendCount(socket!)).toBe(before + 1)

      act(() => {
        result.current.disconnect()
      })
    })
  })
})
