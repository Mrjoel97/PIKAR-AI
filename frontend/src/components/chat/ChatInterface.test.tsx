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
import { describe, it, expect, afterEach, vi } from 'vitest'

import { renderChatInterface, getFetchSpy } from './__test-utils__/chatHarness'
import { useAgentChat } from '@/hooks/useAgentChat'

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
})
