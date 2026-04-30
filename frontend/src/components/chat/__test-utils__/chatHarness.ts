// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.
//
// chatHarness — reusable component-level test harness for ChatInterface.
//
// Why this exists
// ---------------
// `frontend/src/components/chat/ChatInterface.tsx` calls 11 hooks at module
// scope on every render: useAgentChat, useFileUpload, useTextToSpeech,
// usePresence, useRealtimeSession, useSessionControl, useSessionMap,
// useSpeechRecognition, useVoiceSession, usePersona, plus
// `createClient` from `@/lib/supabase/client`. Any one of those throwing
// (e.g. context-not-mounted or "Cannot read properties of undefined") will
// crash the render before the test can fire its first event.
//
// This module installs `vi.mock(...)` calls at module scope (vitest hoists
// these to the top of the test file at compile time) so every hook returns
// a stable, benign default. Behavior tests in Plan 02+ then call
// `renderChatInterface(opts)` to render the component AND override the
// two values they actually care about: `uploadFile` (file extraction) and
// global `fetch` (so they can assert on outgoing HTTP calls — e.g. that
// `/api/upload/smart` was NOT called).
//
// Scope
// -----
// This file is test-only. It must NOT import from production paths in a
// way that affects bundling. It is consumed exclusively by `*.test.tsx`
// files under `frontend/src/components/chat/`.

import React from 'react'
import { render, type RenderResult } from '@testing-library/react'
import { vi } from 'vitest'

import { ChatInterface } from '../ChatInterface'
import type { SessionConfig } from '@/types/session'
import { DEFAULT_SESSION_CONFIG } from '@/types/session'

// ---------------------------------------------------------------------------
// Module-scope mocks. vitest hoists every `vi.mock` to the top of the
// importing test file, so each test that imports this harness picks up the
// full set of stubs before any production code is evaluated.
// ---------------------------------------------------------------------------

vi.mock('@/hooks/useAgentChat', () => ({
  useAgentChat: vi.fn(),
}))

vi.mock('@/hooks/useFileUpload', () => ({
  useFileUpload: vi.fn(),
}))

vi.mock('@/hooks/useTextToSpeech', () => ({
  useTextToSpeech: vi.fn(),
}))

vi.mock('@/hooks/usePresence', () => ({
  usePresence: vi.fn(),
}))

vi.mock('@/hooks/useRealtimeSession', () => ({
  useRealtimeSession: vi.fn(),
}))

vi.mock('@/hooks/useSpeechRecognition', () => ({
  useSpeechRecognition: vi.fn(),
}))

vi.mock('@/hooks/useVoiceSession', () => ({
  useVoiceSession: vi.fn(),
}))

vi.mock('@/contexts/SessionControlContext', () => ({
  useSessionControl: vi.fn(),
}))

vi.mock('@/contexts/SessionMapContext', () => ({
  useSessionMap: vi.fn(),
}))

vi.mock('@/contexts/PersonaContext', () => ({
  usePersona: vi.fn(),
}))

// Supabase client stub — chainable so any incidental `.from(...).select(...)`
// path inside the component (or the hooks it triggers post-mock) does not
// throw. We DO NOT replicate the full supabase-js surface; behavior tests
// that need rich behavior should override on a per-test basis.
vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(() => ({
    from: () => ({
      select: () => ({
        eq: () => ({ data: [], error: null }),
        maybeSingle: () => Promise.resolve({ data: null, error: null }),
        single: () => Promise.resolve({ data: null, error: null }),
      }),
      insert: () => Promise.resolve({ data: null, error: null }),
      update: () => Promise.resolve({ data: null, error: null }),
      delete: () => Promise.resolve({ data: null, error: null }),
    }),
    auth: {
      getUser: vi.fn().mockResolvedValue({ data: { user: null }, error: null }),
      getSession: vi
        .fn()
        .mockResolvedValue({ data: { session: null }, error: null }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
    },
    channel: () => ({
      on: () => ({ subscribe: vi.fn() }),
      subscribe: vi.fn(),
      track: vi.fn(),
      untrack: vi.fn(),
      unsubscribe: vi.fn(),
      presenceState: () => ({}),
    }),
    removeChannel: vi.fn(),
  })),
  getAccessToken: vi.fn().mockResolvedValue(null),
  getAuthenticatedUser: vi.fn().mockResolvedValue(null),
  getStoredAccessToken: vi.fn().mockReturnValue(null),
  getUserFromAccessToken: vi.fn().mockReturnValue(null),
  getSupabaseAuthStorageKey: vi.fn().mockReturnValue(null),
  getSupabaseStorageKeyPrefix: vi.fn().mockReturnValue(null),
  clearSupabaseBrowserState: vi.fn(),
}))

// Re-import the mocked symbols AFTER the vi.mock calls. vitest hoists the
// mocks above all imports inside the test file at compile time, so by the
// time these `import`s execute the mock factories are already registered.
import { useAgentChat } from '@/hooks/useAgentChat'
import { useFileUpload } from '@/hooks/useFileUpload'
import { useTextToSpeech } from '@/hooks/useTextToSpeech'
import { usePresence } from '@/hooks/usePresence'
import { useRealtimeSession } from '@/hooks/useRealtimeSession'
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition'
import { useVoiceSession } from '@/hooks/useVoiceSession'
import { useSessionControl } from '@/contexts/SessionControlContext'
import { useSessionMap } from '@/contexts/SessionMapContext'
import { usePersona } from '@/contexts/PersonaContext'

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/**
 * Override surface for the SessionControlContext mock. Plan 88-01 (HOTFIX-06)
 * uses this to seed `visibleSessionId` so persistence-related behavior tests
 * can drive the harness declaratively without re-touching the mock per test.
 */
export interface SessionControlOverrides {
  visibleSessionId?: string | null
  setVisibleSessionId?: (id: string | null) => void
  sessionRestored?: boolean
  config?: SessionConfig
  createNewChat?: () => string
  selectChat?: (id: string) => void
  deleteChat?: (id: string) => Promise<void>
  clearAllChats?: () => Promise<void>
  refreshSessions?: () => Promise<void>
  updateSessionTitle?: (id: string, t: string) => Promise<void>
  updateSessionPreview?: (id: string, p: string) => Promise<void>
  addSessionOptimistic?: (s: unknown) => void
}

/** Per-test override surface for `renderChatInterface`. */
export interface RenderChatOptions {
  /** Override the function returned by `useFileUpload().uploadFile`. */
  uploadFile?: ReturnType<typeof vi.fn>
  /** Override the messages array returned by useAgentChat (default: empty). */
  messages?: unknown[]
  /** Override useAgentChat().isStreaming (default: false). */
  isStreaming?: boolean
  /** Override useAgentChat().addMessage (default: a fresh vi.fn()). */
  addMessage?: ReturnType<typeof vi.fn>
  /** Override useAgentChat().sendMessage (default: a fresh vi.fn()). */
  sendMessage?: ReturnType<typeof vi.fn>
  /**
   * Forwarded to <ChatInterface initialSessionId={...} />. Used by HOTFIX-06
   * persistence tests to assert that a restored session_id is forwarded into
   * useAgentChat as the first argument.
   */
  initialSessionId?: string
  /**
   * Per-test overrides for the SessionControlContext mock. Merges over the
   * harness default so callers only need to supply the fields they care about
   * (e.g. `{ visibleSessionId: 'session-restore-555' }`).
   */
  sessionControl?: SessionControlOverrides
}

/** Return shape of `renderChatInterface`. */
export interface RenderChatResult extends RenderResult {
  /** The same vi.fn() instance returned by useAgentChat().addMessage. */
  addMessage: ReturnType<typeof vi.fn>
  /** The same vi.fn() instance returned by useAgentChat().sendMessage. */
  sendMessage: ReturnType<typeof vi.fn>
  /** The same vi.fn() instance returned by useFileUpload().uploadFile. */
  uploadFile: ReturnType<typeof vi.fn>
}

// ---------------------------------------------------------------------------
// Module-level fetch spy. Behavior tests need to assert that no smart-upload
// fetch is issued; storing the spy here lets `getFetchSpy()` return the
// exact instance currently installed. We re-install on every render so each
// test starts with a clean call history.
// ---------------------------------------------------------------------------

let fetchSpy: ReturnType<typeof vi.spyOn> | null = null

/**
 * Returns the active `vi.spyOn(global, 'fetch')` instance. Test files use
 * this to assert call counts or arguments after triggering UI events.
 */
export function getFetchSpy(): ReturnType<typeof vi.spyOn> {
  if (!fetchSpy) {
    throw new Error(
      'getFetchSpy() called before renderChatInterface() — call render first.',
    )
  }
  return fetchSpy
}

// ---------------------------------------------------------------------------
// Hook return-shape factories. Match the shapes ChatInterface.tsx
// destructures from each hook so an unconfigured hook never produces a
// "Cannot read properties of undefined" crash on first render.
// ---------------------------------------------------------------------------

function defaultAgentChat(opts: RenderChatOptions): {
  messages: unknown[]
  sendMessage: ReturnType<typeof vi.fn>
  isStreaming: boolean
  addMessage: ReturnType<typeof vi.fn>
  toggleWidgetMinimized: ReturnType<typeof vi.fn>
  isLoadingHistory: boolean
  pinWidget: ReturnType<typeof vi.fn>
  sessionId: string
  getSessionId: ReturnType<typeof vi.fn>
  stopGeneration: ReturnType<typeof vi.fn>
} {
  return {
    messages: opts.messages ?? [],
    sendMessage: opts.sendMessage ?? vi.fn(),
    isStreaming: opts.isStreaming ?? false,
    addMessage: opts.addMessage ?? vi.fn(),
    toggleWidgetMinimized: vi.fn(),
    isLoadingHistory: false,
    pinWidget: vi.fn(),
    sessionId: 'test-session-id',
    getSessionId: vi.fn(() => 'test-session-id'),
    stopGeneration: vi.fn(),
  }
}

function defaultFileUpload(uploadFile: ReturnType<typeof vi.fn>) {
  return {
    uploadFile,
    uploadFileToVault: vi.fn().mockResolvedValue({
      result: null,
      error: null,
    }),
    isUploading: false,
    uploadError: null,
  }
}

function defaultTextToSpeech() {
  // Matches the destructure in ChatInterface.tsx:
  //   const { speak, stop: stopSpeaking, isSpeaking } = useTextToSpeech(...)
  return {
    speak: vi.fn(),
    stop: vi.fn(),
    isSpeaking: false,
    isSupported: false,
  }
}

function defaultPresence() {
  // ChatInterface.tsx destructures `{ onlineUsers }`.
  return {
    presenceState: {},
    onlineUsers: [],
  }
}

function defaultRealtimeSession() {
  // The hook is invoked side-effectfully (no destructure). Return undefined
  // to match the production signature. We still need vi.mocked(...) to
  // resolve, so we return undefined explicitly.
  return undefined
}

function defaultSpeechRecognition() {
  // Full destructure used at ChatInterface.tsx:244-254.
  return {
    isRecording: false,
    isTranscribing: false,
    toggleRecording: vi.fn(),
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    transcript: '',
    transcriptVersion: 0,
    interimTranscript: '',
    error: null,
    isSupported: false,
    clearTranscript: vi.fn(),
  }
}

function defaultVoiceSession() {
  // ChatInterface uses the hook as a single object: voiceSession.isConnected,
  // voiceSession.transcriptTurns, voiceSession.connect(...), etc. Return all
  // the fields ChatInterface reads.
  return {
    isConnected: false,
    isAgentSpeaking: false,
    agentTranscript: '',
    userTranscript: '',
    transcriptTurns: [] as unknown[],
    error: null,
    remainingSeconds: null,
    isWrappingUp: false,
    isTimedOut: false,
    connect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn(),
  }
}

function defaultSessionControl(overrides: SessionControlOverrides = {}) {
  // ChatInterface destructures `{ visibleSessionId }`. Provide the rest of
  // the context contract too so any future destructure does not crash.
  // `overrides` lets HOTFIX-06 persistence tests seed visibleSessionId or
  // any other field declaratively via renderChatInterface({ sessionControl }).
  const base = {
    visibleSessionId: null as string | null,
    setVisibleSessionId: vi.fn(),
    sessionRestored: true,
    config: DEFAULT_SESSION_CONFIG,
    createNewChat: vi.fn(() => 'new-session-id'),
    selectChat: vi.fn(),
    deleteChat: vi.fn().mockResolvedValue(undefined),
    clearAllChats: vi.fn().mockResolvedValue(undefined),
    refreshSessions: vi.fn().mockResolvedValue(undefined),
    updateSessionTitle: vi.fn().mockResolvedValue(undefined),
    updateSessionPreview: vi.fn().mockResolvedValue(undefined),
    addSessionOptimistic: vi.fn(),
  }
  return { ...base, ...overrides }
}

function defaultSessionMap() {
  // ChatInterface destructures `{ activeSessions, updateSessionState }`.
  return {
    activeSessions: new Map(),
    addActiveSession: vi.fn(),
    removeActiveSession: vi.fn(),
    updateSessionState: vi.fn(),
    getActiveSessionRef: vi.fn(() => null),
    sessions: [],
    setSessions: vi.fn(),
    isLoadingSessions: false,
    setIsLoadingSessions: vi.fn(),
  }
}

function defaultPersona() {
  // ChatInterface destructures `{ persona }`.
  return {
    persona: null,
    setPersona: vi.fn(),
    isLoading: false,
    userId: null,
    userEmail: null,
    agentName: null,
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Render <ChatInterface /> with all module-scope hooks pre-mocked.
 *
 * @param opts - Per-test overrides. The two override slots that matter for
 *   Plan 02 behavior tests are `uploadFile` (the function returned by
 *   useFileUpload().uploadFile) and the global fetch spy (auto-installed).
 *
 * @returns The standard `@testing-library/react` RenderResult, plus
 *   references to the mock callbacks behavior tests assert on.
 */
export function renderChatInterface(
  opts: RenderChatOptions = {},
): RenderChatResult {
  // jsdom does not implement scrollIntoView; ChatInterface calls it on
  // every render via the auto-scroll effect.
  Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
    value: vi.fn(),
    writable: true,
    configurable: true,
  })

  // jsdom does not implement window.matchMedia. ChatInterface uses it to
  // detect mobile viewport at line ~196. Stub a benign no-op so the
  // useEffect does not crash on first render.
  if (typeof window.matchMedia !== 'function') {
    Object.defineProperty(window, 'matchMedia', {
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(), // legacy
        removeListener: vi.fn(), // legacy
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
      writable: true,
      configurable: true,
    })
  }

  // Resolve the mocks installed by the module-scope vi.mock calls above.
  const agentChat = defaultAgentChat(opts)
  const uploadFile =
    opts.uploadFile ??
    vi.fn().mockResolvedValue({
      result: { filename: 'mock.txt', content: 'mock content', summary_prompt: '' },
      error: null,
    })
  const fileUpload = defaultFileUpload(uploadFile)

  vi.mocked(useAgentChat).mockReturnValue(agentChat as never)
  vi.mocked(useFileUpload).mockReturnValue(fileUpload as never)
  vi.mocked(useTextToSpeech).mockReturnValue(defaultTextToSpeech() as never)
  vi.mocked(usePresence).mockReturnValue(defaultPresence() as never)
  vi.mocked(useRealtimeSession).mockReturnValue(
    defaultRealtimeSession() as never,
  )
  vi.mocked(useSpeechRecognition).mockReturnValue(
    defaultSpeechRecognition() as never,
  )
  vi.mocked(useVoiceSession).mockReturnValue(defaultVoiceSession() as never)
  vi.mocked(useSessionControl).mockReturnValue(
    defaultSessionControl(opts.sessionControl) as never,
  )
  vi.mocked(useSessionMap).mockReturnValue(defaultSessionMap() as never)
  vi.mocked(usePersona).mockReturnValue(defaultPersona() as never)

  // Install (or refresh) the global fetch spy. Default implementation
  // returns a 200 Response so any incidental fetch never crashes the
  // render. Tests can swap the implementation per-call via
  // `getFetchSpy().mockImplementationOnce(...)`.
  if (fetchSpy) {
    fetchSpy.mockRestore()
  }
  fetchSpy = vi.spyOn(global, 'fetch').mockImplementation(async () => {
    return new Response(null, { status: 200 })
  })

  const result = render(
    React.createElement(
      ChatInterface,
      opts.initialSessionId ? { initialSessionId: opts.initialSessionId } : {},
    ),
  )

  return {
    ...result,
    addMessage: agentChat.addMessage,
    sendMessage: agentChat.sendMessage,
    uploadFile,
  }
}
