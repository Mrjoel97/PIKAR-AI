// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.
//
// Smoke + behavior tests for the chatHarness module.
// These tests prove the harness pre-mocks every module-scope hook in
// ChatInterface.tsx with stable defaults, exposes overrides for the two
// values component-level tests need to control (uploadFile + global fetch),
// and re-exports the mocked agent-chat callbacks so behavior tests don't
// have to redo the useAgentChat mock by hand.

import { describe, it, expect, afterEach, vi } from 'vitest'
import { cleanup, screen } from '@testing-library/react'

import { renderChatInterface, getFetchSpy } from './chatHarness'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('chatHarness', () => {
  it('renders <ChatInterface /> in jsdom without throwing (smoke)', () => {
    const result = renderChatInterface()
    // Sanity: the chat input must be in the tree.
    expect(screen.getByPlaceholderText(/Type your message/i)).toBeTruthy()
    // The harness exposes the standard render result.
    expect(result.container).toBeTruthy()
  })

  it('uses the uploadFile override returned by useFileUpload()', async () => {
    const uploadFile = vi.fn().mockResolvedValue({
      result: { filename: 'a.pdf', content: 'X', summary_prompt: '' },
      error: null,
    })
    const { uploadFile: exposedUploadFile } = renderChatInterface({ uploadFile })

    // The harness MUST return the exact same vi.fn() instance that
    // useFileUpload() returns inside the component, so behavior tests
    // can assert call counts/args without spelunking through React tree.
    expect(exposedUploadFile).toBe(uploadFile)

    // The override must actually return the override value when called.
    const outcome = await exposedUploadFile(new File(['x'], 'a.pdf'))
    expect(outcome.result?.filename).toBe('a.pdf')
    expect(uploadFile).toHaveBeenCalledTimes(1)
  })

  it('exposes addMessage and sendMessage from the useAgentChat mock', () => {
    const { addMessage, sendMessage } = renderChatInterface()

    // Both must be vi.fn() instances callable by behavior tests.
    expect(typeof addMessage).toBe('function')
    expect(typeof sendMessage).toBe('function')
    expect(vi.isMockFunction(addMessage)).toBe(true)
    expect(vi.isMockFunction(sendMessage)).toBe(true)

    // Calling them does not throw.
    addMessage({ role: 'system', text: 'hi' })
    sendMessage('hello')
    expect(addMessage).toHaveBeenCalledTimes(1)
    expect(sendMessage).toHaveBeenCalledWith('hello')
  })

  it('provides a fetch spy via getFetchSpy() with a benign default', async () => {
    renderChatInterface()
    const spy = getFetchSpy()
    expect(spy).toBeTruthy()
    expect(vi.isMockFunction(spy)).toBe(true)

    // Default implementation returns a 200 Response for any incidental
    // fetch (Supabase RPC, presence channel, etc.) so the render never
    // crashes on a real network call.
    const res = await fetch('http://example.test/anything')
    expect(res.status).toBe(200)
    expect(spy).toHaveBeenCalled()
  })
})
