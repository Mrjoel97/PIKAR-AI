// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { renderHook, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useSpeechRecognition } from '@/hooks/useSpeechRecognition'

/**
 * Phase 87 Plan 01 — useSpeechRecognition unit suite.
 *
 * The hook is a thin wrapper around `window.SpeechRecognition`. jsdom does NOT
 * implement that API, so we install a fake constructor on `window` for each
 * test and fire the spec events (`onresult`, `onerror`, `onend`) by hand.
 *
 * Public 11-field return shape MUST stay byte-identical to the prior backend
 * wrapper — `chatHarness.defaultSpeechRecognition()` and ChatInterface.tsx's
 * destructure both depend on it.
 */

type FakeRec = {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((event: any) => void) | null
  onerror: ((event: any) => void) | null
  onend: (() => void) | null
  start: ReturnType<typeof vi.fn>
  stop: ReturnType<typeof vi.fn>
  abort: ReturnType<typeof vi.fn>
}

let latest: FakeRec | null = null

function FakeCtor(this: FakeRec) {
  this.continuous = false
  this.interimResults = false
  this.lang = ''
  this.onresult = null
  this.onerror = null
  this.onend = null
  this.start = vi.fn()
  this.stop = vi.fn()
  this.abort = vi.fn()
  latest = this
}

function installFakeSpeechRecognition() {
  ;(window as unknown as { SpeechRecognition: unknown }).SpeechRecognition = FakeCtor
}

function uninstallSpeechRecognition() {
  delete (window as unknown as { SpeechRecognition?: unknown }).SpeechRecognition
  delete (window as unknown as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition
}

/** Fire an onresult event with a single result entry. */
function fireResult(transcript: string, isFinal: boolean) {
  if (!latest?.onresult) throw new Error('No fake recognition instance / onresult registered')
  latest.onresult({
    resultIndex: 0,
    results: [
      Object.assign(
        [{ transcript, confidence: 1 }],
        { isFinal, length: 1 },
      ),
    ],
  })
}

/** Fire an onerror event. */
function fireError(code: string) {
  if (!latest?.onerror) throw new Error('No fake recognition instance / onerror registered')
  latest.onerror({ error: code })
}

/** Fire an onend event. */
function fireEnd() {
  if (!latest?.onend) throw new Error('No fake recognition instance / onend registered')
  latest.onend()
}

describe('useSpeechRecognition (Web Speech API path)', () => {
  beforeEach(() => {
    installFakeSpeechRecognition()
    latest = null
  })

  afterEach(() => {
    uninstallSpeechRecognition()
    latest = null
    vi.restoreAllMocks()
  })

  it('Test 1: isSupported reflects window.SpeechRecognition presence', () => {
    // Supported case
    const { result, rerender, unmount } = renderHook(() => useSpeechRecognition())
    expect(result.current.isSupported).toBe(true)
    unmount()

    // Unsupported case — both prefixes absent
    uninstallSpeechRecognition()
    const { result: unsupportedResult } = renderHook(() => useSpeechRecognition())
    expect(unsupportedResult.current.isSupported).toBe(false)

    // Re-install for afterEach idempotency
    installFakeSpeechRecognition()
    rerender()
  })

  it('Test 2: startRecording instantiates SpeechRecognition with continuous + interimResults', () => {
    const { result } = renderHook(() => useSpeechRecognition())

    act(() => {
      result.current.startRecording()
    })

    expect(latest).not.toBeNull()
    expect(latest!.continuous).toBe(true)
    expect(latest!.interimResults).toBe(true)
    expect(latest!.start).toHaveBeenCalledTimes(1)
    expect(result.current.isRecording).toBe(true)
  })

  it('Test 3: interim onresult updates interimTranscript without bumping transcriptVersion', () => {
    const { result } = renderHook(() => useSpeechRecognition())

    act(() => {
      result.current.startRecording()
    })

    act(() => {
      fireResult('hello', false)
    })

    expect(result.current.interimTranscript).toBe('hello')
    expect(result.current.transcriptVersion).toBe(0)
    expect(result.current.transcript).toBe('')
  })

  it('Test 4: final onresult accumulates into transcript and is preserved across subsequent interim chunks', () => {
    const { result } = renderHook(() => useSpeechRecognition())

    act(() => {
      result.current.startRecording()
    })

    act(() => {
      fireResult('hello world', true)
    })
    expect(result.current.transcript).toBe('hello world')

    act(() => {
      fireResult('and goodb', false)
    })
    expect(result.current.transcript).toBe('hello world')
    expect(result.current.interimTranscript).toBe('and goodb')
  })

  it('Test 5: onend bumps transcriptVersion when finalRef has content; does not bump when empty', () => {
    const { result } = renderHook(() => useSpeechRecognition())

    // Bumps when there is final content
    act(() => {
      result.current.startRecording()
    })
    act(() => {
      fireResult('hello world', true)
    })
    act(() => {
      fireEnd()
    })

    expect(result.current.transcriptVersion).toBe(1)
    expect(result.current.isRecording).toBe(false)
    expect(result.current.interimTranscript).toBe('')

    // Subsequent session without final content — no bump.
    act(() => {
      result.current.startRecording()
    })
    act(() => {
      fireEnd()
    })

    // Version stays at 1 (no second bump because finalRef was empty for the second session).
    expect(result.current.transcriptVersion).toBe(1)
    expect(result.current.isRecording).toBe(false)
  })

  it('Test 6: onerror with not-allowed surfaces a friendly permission-denied message', () => {
    const { result } = renderHook(() => useSpeechRecognition())

    act(() => {
      result.current.startRecording()
    })

    act(() => {
      fireError('not-allowed')
    })

    expect(result.current.error).toMatch(/microphone permission|allow access/i)
    expect(result.current.isRecording).toBe(false)
  })

  it('Test 7: stopRecording calls recognition.stop() (NOT abort)', () => {
    const { result } = renderHook(() => useSpeechRecognition())

    act(() => {
      result.current.startRecording()
    })

    act(() => {
      result.current.stopRecording()
    })

    expect(latest!.stop).toHaveBeenCalledTimes(1)
    expect(latest!.abort).not.toHaveBeenCalled()
  })

  it('Test 8: unsupported environment — startRecording sets fallback error and does not throw', () => {
    uninstallSpeechRecognition()

    const { result } = renderHook(() => useSpeechRecognition())
    expect(result.current.isSupported).toBe(false)

    expect(() => {
      act(() => {
        result.current.startRecording()
      })
    }).not.toThrow()

    expect(result.current.error).toMatch(/not supported|please type/i)
    expect(result.current.isRecording).toBe(false)
  })
})
