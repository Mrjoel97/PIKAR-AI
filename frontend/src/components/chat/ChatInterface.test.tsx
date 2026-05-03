// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.
//
// ChatInterface tests.
//
// Existing tests (initial greeting, typing, send-on-click, disabled-on-streaming)
// were originally written before ChatInterface.tsx grew its 11 module-scope
// hooks; they relied on a single `vi.mock('@/hooks/useAgentChat', ...)` and
// rendered the component directly, which crashed at render time once
// useSessionControl/useFileUpload/etc were added. We now adopt the shared
// `renderChatInterface` harness from `__test-utils__/chatHarness.ts` (Plan 01,
// Phase 83) so every hook is pre-stubbed and the component can mount cleanly.
//
// HOTFIX-01 behavior tests (Plan 02, Phase 83) follow the existing tests in
// their own describe block. They cover all four ROADMAP success criteria:
//   1. Single-file drop attaches as a pill within one render tick.
//   2. The "Detecting content type..." indicator never renders on attach.
//   3. On send, /api/upload extracts file content and inlines it via sendMessage.
//   4. On upload failure, addMessage emits a single system message; no spinner.
//   5. The /api/upload/smart proxy is never fetched from handleFileAttach.
import { screen, cleanup, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest'

// Plan 88-04 — mock sonner BEFORE importing any module that pulls it in.
// vi.mock is hoisted to the top of the file at compile time so this fires
// before the chatHarness import below (which transitively imports
// ChatInterface, which imports sonner).
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
    message: vi.fn(),
  },
}))

import { renderChatInterface, getFetchSpy } from './__test-utils__/chatHarness'
import { useAgentChat } from '@/hooks/useAgentChat'
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition'
import { useVoiceSession } from '@/hooks/useVoiceSession'
import { toast } from 'sonner'
import { TabCapReachedError } from '@/contexts/SessionControlContext'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ChatInterface', () => {
  it('renders initial greeting from agent-chat hook', () => {
    renderChatInterface({
      messages: [
        {
          role: 'agent' as const,
          text: 'Hello! I am Pikar AI. How can I help you optimize your business today?',
          agentName: 'ExecutiveAgent',
        },
      ],
    })
    expect(screen.getByText(/Hello! I am Pikar AI/i)).toBeTruthy()
  })

  it('allows typing a message', () => {
    renderChatInterface()
    const input = screen.getByPlaceholderText(/Type your message/i)
    fireEvent.change(input, { target: { value: 'Test message' } })
    expect((input as HTMLTextAreaElement).value).toBe('Test message')
  })

  it('calls sendMessage when clicking send', () => {
    const { sendMessage } = renderChatInterface()
    const input = screen.getByPlaceholderText(/Type your message/i)
    const sendButton = screen.getByTestId('chat-send-button')

    fireEvent.change(input, { target: { value: 'Test message' } })
    fireEvent.click(sendButton)

    expect(sendMessage).toHaveBeenCalledWith('Test message', expect.anything())
    expect((input as HTMLTextAreaElement).value).toBe('')
  })

  it('replaces send button with stop button when streaming', () => {
    // ChatInterface gates streaming by swapping the send button for a Stop
    // button (lines 1812-1831 of ChatInterface.tsx). The textarea itself is
    // disabled by isUploading / isSpeechTranscribing only — not isStreaming.
    // This assertion matches the actual production behavior: while a response
    // is streaming, the Stop button is rendered instead of the Send button so
    // the user can cancel; the input remains editable for the next message.
    renderChatInterface({ isStreaming: true })
    expect(screen.queryByTestId('chat-send-button')).toBeNull()
    expect(screen.getByTitle(/Stop Generation/i)).toBeTruthy()
  })
})

// ---------------------------------------------------------------------------
// HOTFIX-01 — Phase 83 Plan 02
// Direct attach without /api/upload/smart auto-call.
// ---------------------------------------------------------------------------

/**
 * Locate the FileDropZone wrapper in the rendered tree. FileDropZone renders
 * a <div className="relative h-full w-full flex flex-col"> as the drop
 * target, so we query by className to avoid coupling to a test-id.
 */
function findDropZone(container: HTMLElement): Element {
  const zone = container.querySelector(
    'div.relative.h-full.w-full.flex.flex-col',
  )
  if (!zone) {
    throw new Error(
      'FileDropZone wrapper not found — verify FileDropZone.tsx className still matches the selector.',
    )
  }
  return zone
}

/**
 * Build a synthetic DragEvent payload that mimics the browser's
 * dataTransfer when a file is dropped on a zone.
 */
function buildDropEvent(file: File): { dataTransfer: DataTransfer } {
  return {
    dataTransfer: {
      files: [file] as unknown as FileList,
      items: [
        {
          kind: 'file',
          type: file.type,
          getAsFile: () => file,
        },
      ] as unknown as DataTransferItemList,
      types: ['Files'],
    } as unknown as DataTransfer,
  }
}

describe('ChatInterface — file attach hotfix (HOTFIX-01)', () => {
  it('drop attaches without smart', async () => {
    const { container } = renderChatInterface()
    const fetchSpy = getFetchSpy()
    fetchSpy.mockClear()

    const file = new File(['dummy content'], 'doc.pdf', {
      type: 'application/pdf',
    })
    fireEvent.drop(findDropZone(container), buildDropEvent(file))

    await waitFor(() => {
      expect(screen.getByText(/doc\.pdf/)).toBeTruthy()
    })

    // Assertion (b): no /api/upload/smart fetch issued from the drop handler.
    const smartCalls = fetchSpy.mock.calls.filter((call) => {
      const url = String(call[0] ?? '')
      return url.includes('/api/upload/smart')
    })
    expect(smartCalls).toHaveLength(0)
  })

  it('no detecting content type indicator', async () => {
    const { container } = renderChatInterface()
    const file = new File(['dummy content'], 'doc.pdf', {
      type: 'application/pdf',
    })

    // Pre-drop sanity check.
    expect(screen.queryByText(/Detecting content type/i)).toBeNull()

    fireEvent.drop(findDropZone(container), buildDropEvent(file))
    expect(screen.queryByText(/Detecting content type/i)).toBeNull()

    await waitFor(() => {
      expect(screen.getByText(/doc\.pdf/)).toBeTruthy()
    })
    expect(screen.queryByText(/Detecting content type/i)).toBeNull()
  })

  it('send delivers extracted content inline', async () => {
    const uploadFile = vi.fn().mockResolvedValue({
      result: {
        filename: 'doc.pdf',
        content: 'extracted text',
        summary_prompt: '',
      },
      error: null,
    })
    const { container, sendMessage } = renderChatInterface({ uploadFile })

    const file = new File(['dummy content'], 'doc.pdf', {
      type: 'application/pdf',
    })
    fireEvent.drop(findDropZone(container), buildDropEvent(file))

    await waitFor(() => {
      expect(screen.getByText(/doc\.pdf/)).toBeTruthy()
    })

    // Once a file is attached the textarea placeholder switches from
    // "Type your message..." to "Add a message or just send the files..."
    // (ChatInterface.tsx:1700). Query by id instead of placeholder so the
    // assertion is stable across both states.
    const input = document.getElementById('chat-input-text') as HTMLTextAreaElement
    expect(input).toBeTruthy()
    fireEvent.change(input, { target: { value: 'Summarize this' } })

    const sendButton = screen.getByTestId('chat-send-button')
    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(uploadFile).toHaveBeenCalledTimes(1)
    })
    expect(uploadFile).toHaveBeenCalledWith(file)

    await waitFor(() => {
      expect(sendMessage).toHaveBeenCalledTimes(1)
    })
    const sentMessage = sendMessage.mock.calls[0][0] as string
    expect(sentMessage).toContain('**Attached File: doc.pdf**')
    expect(sentMessage).toContain('extracted text')
  })

  it('upload failure renders single system message', async () => {
    const uploadFile = vi.fn().mockResolvedValue({
      result: null,
      error: 'Backend rejected',
    })
    const addMessage = vi.fn()
    const { container } = renderChatInterface({ uploadFile, addMessage })

    const file = new File(['dummy content'], 'doc.pdf', {
      type: 'application/pdf',
    })
    fireEvent.drop(findDropZone(container), buildDropEvent(file))

    await waitFor(() => {
      expect(screen.getByText(/doc\.pdf/)).toBeTruthy()
    })

    const sendButton = screen.getByTestId('chat-send-button')
    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(uploadFile).toHaveBeenCalledTimes(1)
    })
    await waitFor(() => {
      expect(addMessage).toHaveBeenCalledTimes(1)
    })
    const call = addMessage.mock.calls[0][0] as {
      role: string
      text: string
    }
    expect(call.role).toBe('system')
    expect(call.text).toMatch(/doc\.pdf/)
    expect(call.text).toMatch(/Backend rejected/)
    expect(screen.queryByText(/Detecting content type/i)).toBeNull()
  })

  it('drop does not fetch smart endpoint', async () => {
    const { container } = renderChatInterface()
    const fetchSpy = getFetchSpy()
    fetchSpy.mockClear()

    const file = new File(['dummy content'], 'spreadsheet.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    fireEvent.drop(findDropZone(container), buildDropEvent(file))

    // Flush any microtasks queued by the drop handler.
    await Promise.resolve()
    await Promise.resolve()

    const smartCalls = fetchSpy.mock.calls.filter((call) => {
      const url = String(call[0] ?? '')
      return /\/api\/upload\/smart/.test(url)
    })
    expect(smartCalls).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------
// HOTFIX-06 — Phase 88 Plan 01
// Reload-restore: ChatInterface receives restored sessionId via initialSessionId
// and forwards it into useAgentChat as the first argument.
// ---------------------------------------------------------------------------

describe('ChatInterface — persistence (HOTFIX-06)', () => {
  it('forwards initialSessionId from props to useAgentChat', () => {
    renderChatInterface({
      initialSessionId: 'session-restore-555',
      sessionControl: { visibleSessionId: 'session-restore-555' },
    })

    expect(useAgentChat).toHaveBeenCalled()
    const firstCallArgs = (useAgentChat as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(firstCallArgs.length).toBeGreaterThan(0)

    // useAgentChat accepts either (sessionId: string) or (options: UseAgentChatOptions);
    // ChatInterface.tsx:101-105 uses the options object form.
    const arg = firstCallArgs[0]
    if (typeof arg === 'string') {
      expect(arg).toBe('session-restore-555')
    } else {
      expect(arg.initialSessionId).toBe('session-restore-555')
    }
  })

  // -------------------------------------------------------------------------
  // Plan 88-03 — TabStrip wired into ChatInterface header
  // -------------------------------------------------------------------------

  it('renders TabStrip pills from openTabIds × sessions and removes legacy +', () => {
    renderChatInterface({
      sessionControl: {
        openTabIds: ['s1', 's2'],
        visibleSessionId: 's2',
        tabCap: 5,
      },
      sessionMap: {
        sessions: [
          {
            id: 's1',
            title: 'First chat',
            createdAt: '',
            updatedAt: '',
          },
          {
            id: 's2',
            title: 'Second chat',
            createdAt: '',
            updatedAt: '',
          },
        ],
      },
    })

    // Both tab labels render — derived from session.title via the
    // ChatInterface useMemo over openTabIds × sessions.
    expect(screen.getByText('First chat')).toBeTruthy()
    expect(screen.getByText('Second chat')).toBeTruthy()

    // The legacy `+` icon button (title="New Chat") that previously lived in
    // the action-icon row at line ~1167 has been removed in Plan 88-03.
    expect(screen.queryByTitle('New Chat')).toBeNull()

    // The TabStrip's trailing `+` is still present as the canonical
    // new-chat affordance.
    expect(screen.getByTestId('tab-new')).toBeTruthy()
  })

  it('clicking a TabStrip pill calls openTab with the id', () => {
    const openTab = vi.fn()
    renderChatInterface({
      sessionControl: {
        openTabIds: ['s1', 's2'],
        visibleSessionId: 's2',
        openTab,
        tabCap: 5,
      },
      sessionMap: {
        sessions: [
          {
            id: 's1',
            title: 'First chat',
            createdAt: '',
            updatedAt: '',
          },
          {
            id: 's2',
            title: 'Second chat',
            createdAt: '',
            updatedAt: '',
          },
        ],
      },
    })

    fireEvent.click(screen.getByTestId('tab-pill-s1'))
    expect(openTab).toHaveBeenCalledTimes(1)
    expect(openTab).toHaveBeenCalledWith('s1')
  })
})

// ---------------------------------------------------------------------------
// Plan 88-04 — multi-session tab POLISH (FEATURE-MULTI-SESSION-TABS)
// Streaming/unread indicators (criterion 9) + sonner cap toast (cap UX).
// ---------------------------------------------------------------------------

describe('ChatInterface — multi-session tabs polish (FEATURE-MULTI-SESSION-TABS)', () => {
  beforeEach(() => {
    vi.mocked(toast.error).mockClear()
  })

  it('renders streaming indicator on non-active streaming tab', () => {
    // Seed an ActiveSessionState entry for s1 with status='streaming' and
    // the visible tab as s2. ChatInterface's indicators useMemo should
    // emit { s1: 'streaming', s2: 'none' }, which TabStrip renders as a
    // pulsing dot on s1's pill and nothing on s2's pill.
    const streamingSession = {
      sessionId: 's1',
      messages: [],
      status: 'streaming' as const,
      abortController: null,
      hasUnread: false,
      lastUpdatedAt: Date.now(),
      scrollTop: -1,
      rawWidgets: [],
      pendingActions: [],
    }
    renderChatInterface({
      sessionControl: {
        openTabIds: ['s1', 's2'],
        visibleSessionId: 's2',
        tabCap: 5,
      },
      sessionMap: {
        sessions: [
          { id: 's1', title: 'Streaming chat', createdAt: '', updatedAt: '' },
          { id: 's2', title: 'Visible chat', createdAt: '', updatedAt: '' },
        ],
        activeSessions: new Map([['s1', streamingSession]]),
      },
    })

    const dot = screen.getByTestId('tab-indicator-s1')
    expect(dot).toBeTruthy()
    expect(dot.className).toMatch(/animate-pulse/)
    // Active tab (s2) never renders an indicator regardless of its
    // session state.
    expect(screen.queryByTestId('tab-indicator-s2')).toBeNull()
  })

  it('shows sonner toast when openTab throws TabCapReachedError', () => {
    // The harness's openTab is the only path that ChatInterface calls when
    // a tab pill is clicked. Override it to throw TabCapReachedError so we
    // can verify the cap-toast wrapper at the call site.
    const openTab = vi.fn(() => {
      throw new TabCapReachedError(2)
    })
    renderChatInterface({
      sessionControl: {
        openTabIds: ['s1', 's2'],
        visibleSessionId: 's2',
        tabCap: 2,
        openTab,
      },
      sessionMap: {
        sessions: [
          { id: 's1', title: 'A', createdAt: '', updatedAt: '' },
          { id: 's2', title: 'B', createdAt: '', updatedAt: '' },
        ],
      },
    })

    // Click the non-active pill — ChatInterface.handleTabSwitch wraps openTab
    // in a try/catch that surfaces TabCapReachedError as a sonner toast.
    fireEvent.click(screen.getByTestId('tab-pill-s1'))
    expect(openTab).toHaveBeenCalledTimes(1)
    expect(toast.error).toHaveBeenCalledTimes(1)
    const toastArg = vi.mocked(toast.error).mock.calls[0][0] as string
    expect(toastArg).toMatch(/Tab limit reached \(2\)/)
  })
})

// ---------------------------------------------------------------------------
// HOTFIX-05 — Phase 87 Plan 02
// Chat-input mic dictation integration + boundary guard-rail.
// ---------------------------------------------------------------------------

describe('ChatInterface — HOTFIX-05 mic dictation', () => {
  function baseSpeechRecognitionMock() {
    return {
      isRecording: false,
      isTranscribing: false,
      isSupported: true,
      toggleRecording: vi.fn(),
      startRecording: vi.fn(),
      stopRecording: vi.fn(),
      transcript: '',
      transcriptVersion: 0,
      interimTranscript: '',
      error: null,
      clearTranscript: vi.fn(),
    }
  }

  it('mic button toggles recognition', () => {
    const toggleSpy = vi.fn()
    vi.mocked(useSpeechRecognition).mockReturnValueOnce({
      ...baseSpeechRecognitionMock(),
      toggleRecording: toggleSpy,
    } as never)

    renderChatInterface()
    fireEvent.click(screen.getByTitle(/Start voice input/i))
    expect(toggleSpy).toHaveBeenCalledTimes(1)

    cleanup()

    vi.mocked(useSpeechRecognition).mockReturnValueOnce({
      ...baseSpeechRecognitionMock(),
      isRecording: true,
      toggleRecording: toggleSpy,
    } as never)

    renderChatInterface()
    fireEvent.click(screen.getByTitle(/Stop recording/i))
    expect(toggleSpy).toHaveBeenCalledTimes(2)
  })

  it('interim transcript appears in input', () => {
    vi.mocked(useSpeechRecognition).mockReturnValueOnce({
      ...baseSpeechRecognitionMock(),
      isRecording: true,
      interimTranscript: 'hello world',
    } as never)

    renderChatInterface()

    const textarea = document.getElementById(
      'chat-input-text',
    ) as HTMLTextAreaElement
    expect(textarea).toBeTruthy()
    expect(textarea.value).toContain('hello world')
  })

  it('user can edit dictated text', () => {
    vi.mocked(useSpeechRecognition).mockReturnValueOnce({
      ...baseSpeechRecognitionMock(),
      isRecording: true,
      interimTranscript: 'hello',
    } as never)

    renderChatInterface()

    const textarea = document.getElementById(
      'chat-input-text',
    ) as HTMLTextAreaElement
    expect(textarea).toBeTruthy()
    expect(textarea.readOnly).toBe(false)

    fireEvent.change(textarea, { target: { value: 'edited text' } })
    expect(textarea.value).toContain('edited text')
  })

  it('send during dictation stops recognition and sends combined text', async () => {
    const stopRecording = vi.fn()
    vi.mocked(useSpeechRecognition).mockReturnValueOnce({
      ...baseSpeechRecognitionMock(),
      isRecording: true,
      transcript: 'hello',
      interimTranscript: 'world',
      stopRecording,
    } as never)

    const { sendMessage } = renderChatInterface()

    const sendButton = screen.getByTestId('chat-send-button')
    expect(sendButton).not.toHaveProperty('disabled', true)

    fireEvent.click(sendButton)

    expect(stopRecording).toHaveBeenCalledTimes(1)
    await waitFor(() => {
      expect(sendMessage).toHaveBeenCalledTimes(1)
    })

    const sentMessage = sendMessage.mock.calls[0][0] as string
    expect(sentMessage).toContain('hello')
    expect(sentMessage).toContain('world')
  })

  it('unsupported browser shows fallback', () => {
    vi.mocked(useSpeechRecognition).mockReturnValueOnce({
      ...baseSpeechRecognitionMock(),
      isSupported: false,
    } as never)

    renderChatInterface()

    const micButton = screen.getByTitle(
      /Voice input not supported in this browser/i,
    ) as HTMLButtonElement
    expect(micButton.disabled).toBe(true)
    expect(screen.queryByText(/permission denied|voice input failed/i)).toBeNull()
  })

  it('chat mic does not call useVoiceSession', () => {
    // SC5 boundary guard-rail: this test fails CI if anyone ever wires the
    // chat-input mic flow into useVoiceSession.connect/disconnect. The two
    // paths must remain structurally independent. DO NOT DELETE.
    const connectSpy = vi.fn().mockResolvedValue(undefined)
    const disconnectSpy = vi.fn()

    vi.mocked(useSpeechRecognition).mockReturnValueOnce({
      ...baseSpeechRecognitionMock(),
      isSupported: true,
      toggleRecording: vi.fn(),
    } as never)
    vi.mocked(useVoiceSession).mockReturnValueOnce({
      isConnected: false,
      isAgentSpeaking: false,
      agentTranscript: '',
      userTranscript: '',
      transcriptTurns: [],
      error: null,
      remainingSeconds: null,
      isWrappingUp: false,
      isTimedOut: false,
      connect: connectSpy,
      disconnect: disconnectSpy,
    } as never)

    renderChatInterface()
    fireEvent.click(screen.getByTitle(/Start voice input/i))

    expect(connectSpy).not.toHaveBeenCalled()
    expect(disconnectSpy).not.toHaveBeenCalled()
  })

  it('renders the brainstorm start menu in a portal and closes after selection', async () => {
    renderChatInterface()

    fireEvent.click(
      screen.getByTitle(/Discuss with Agent — start a voice conversation/i),
    )

    const menu = await screen.findByTestId('brainstorm-start-menu')
    expect(menu.parentElement).toBe(document.body)
    expect(screen.getByText(/Continue from context/i)).toBeTruthy()
    expect(screen.getByText(/Start fresh/i)).toBeTruthy()

    fireEvent.click(screen.getByText(/Start fresh/i))

    await waitFor(() => {
      expect(screen.queryByTestId('brainstorm-start-menu')).toBeNull()
    })
  })
})
