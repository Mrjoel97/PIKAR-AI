'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Phase 87 — Web Speech API wrapper.
 *
 * Thin client-side hook around `window.SpeechRecognition` (or the webkit
 * prefix). Replaces the previous MediaRecorder + backend `/ws/voice/transcribe`
 * round-trip wrapper. Streams interim results in real time so the chat input
 * fills as the user speaks.
 *
 * Public 11-field return shape MUST stay byte-identical to the prior hook —
 * `chatHarness.defaultSpeechRecognition()` and `ChatInterface.tsx`'s destructure
 * both depend on it. `isTranscribing` is retained but always returns `false`
 * (no async backend transcription step in the Web Speech API path).
 *
 * Phase 87 boundary: this hook is independent of `useVoiceSession.ts`
 * (brain-dump full-duplex Gemini Live session). The two never cross-import.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

interface UseSpeechRecognitionReturn {
  isRecording: boolean
  isSupported: boolean
  isTranscribing: boolean
  transcript: string
  transcriptVersion: number
  interimTranscript: string
  error: string | null
  startRecording: () => void
  stopRecording: () => void
  toggleRecording: () => void
  clearTranscript: () => void
}

/**
 * Look up the SpeechRecognition constructor on the current window object.
 *
 * Reads from `window` (NOT a captured module-load value) so tests can install /
 * remove the fake constructor between renders without `vi.resetModules`.
 *
 * `@types/dom-speech-recognition` declares both `SpeechRecognition` and
 * `webkitSpeechRecognition` as `declare var` globals, but does NOT augment
 * the `Window` interface. The runtime exposes them on `window`, so we read
 * via an `unknown` cast to a narrow lookup shape.
 */
function getSpeechRecognitionCtor(): typeof SpeechRecognition | undefined {
  if (typeof window === 'undefined') {
    return undefined
  }
  const win = window as unknown as {
    SpeechRecognition?: typeof SpeechRecognition
    webkitSpeechRecognition?: typeof SpeechRecognition
  }
  return win.SpeechRecognition || win.webkitSpeechRecognition
}

const ERROR_MESSAGES: Record<string, string> = {
  'not-allowed': 'Microphone permission denied. Please allow access in your browser settings.',
  'no-speech': 'No speech detected. Please try again.',
  'audio-capture': 'No microphone found. Please connect a microphone and try again.',
  network: 'Network error during recognition. Please retry.',
}

export function useSpeechRecognition(): UseSpeechRecognitionReturn {
  const [isRecording, setIsRecording] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [interimTranscript, setInterimTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [transcriptVersion, setTranscriptVersion] = useState(0)
  const [isSupported] = useState<boolean>(() => !!getSpeechRecognitionCtor())

  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const finalRef = useRef('')
  const versionRef = useRef(0)

  const startRecording = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor()
    if (!Ctor) {
      setError('Voice input is not supported in this browser. Please type your message.')
      return
    }
    if (recognitionRef.current) {
      // Already running — idempotent no-op.
      return
    }

    finalRef.current = ''
    setTranscript('')
    setInterimTranscript('')
    setError(null)

    const rec = new Ctor()
    rec.continuous = true
    rec.interimResults = true
    rec.lang = (typeof navigator !== 'undefined' && navigator.language) || 'en-US'

    rec.onresult = (event: SpeechRecognitionEvent) => {
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          const chunk = result[0].transcript.trim()
          if (chunk) {
            finalRef.current += (finalRef.current ? ' ' : '') + chunk
          }
        } else {
          interim += result[0].transcript
        }
      }
      setTranscript(finalRef.current)
      setInterimTranscript(interim)
    }

    rec.onerror = (event: SpeechRecognitionErrorEvent) => {
      const code = event.error
      setError(ERROR_MESSAGES[code] ?? `Voice input failed: ${code}`)
      setIsRecording(false)
    }

    rec.onend = () => {
      // Browser-side silence auto-stop OR explicit stopRecording(): bump version
      // ONLY when finalRef has content so the consumer effect appends to input.
      // Interim is dropped here (already streamed live to interimTranscript).
      if (finalRef.current.trim()) {
        versionRef.current += 1
        setTranscriptVersion(versionRef.current)
      }
      setInterimTranscript('')
      setIsRecording(false)
      recognitionRef.current = null
    }

    try {
      rec.start()
      recognitionRef.current = rec
      setIsRecording(true)
    } catch {
      setError('Could not start voice input. Please try again.')
    }
  }, [])

  const stopRecording = useCallback(() => {
    // stop() flushes the in-progress interim into a final result via onend,
    // supporting "click Send mid-dictation includes the in-progress phrase".
    // NOT abort() — abort() discards interim silently.
    recognitionRef.current?.stop()
  }, [])

  const toggleRecording = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
    } else {
      startRecording()
    }
  }, [startRecording])

  const clearTranscript = useCallback(() => {
    finalRef.current = ''
    setTranscript('')
    setInterimTranscript('')
    setError(null)
  }, [])

  // Cleanup: abort() (silent — does NOT fire onend) so unmount never produces a
  // phantom transcriptVersion bump on the next mount.
  useEffect(() => {
    return () => {
      recognitionRef.current?.abort()
      recognitionRef.current = null
    }
  }, [])

  return {
    isRecording,
    isSupported,
    isTranscribing: false, // Legacy field — always false in Web Speech API path.
    transcript,
    transcriptVersion,
    interimTranscript,
    error,
    startRecording,
    stopRecording,
    toggleRecording,
    clearTranscript,
  }
}
