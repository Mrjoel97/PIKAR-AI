// @vitest-environment jsdom
import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useAgentChat } from '@/hooks/useAgentChat'
import { fetchEventSource } from '@microsoft/fetch-event-source'

// Mock Supabase
vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'mock-token' } }
      })
    }
  }))
}))

// Mock fetchEventSource
vi.mock('@microsoft/fetch-event-source', () => ({
  fetchEventSource: vi.fn()
}))

describe('useAgentChat', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.NEXT_PUBLIC_API_URL = 'http://test-api.com'
  })

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_API_URL
  })

  it('initializes with default state', () => {
    const { result } = renderHook(() => useAgentChat())
    
    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0].role).toBe('agent')
    expect(result.current.isStreaming).toBe(false)
  })

  it('updates messages and starts streaming when sendMessage is called', async () => {
    const { result } = renderHook(() => useAgentChat())

    await act(async () => {
      await result.current.sendMessage('Hello Agent')
    })

    // Should have added user message and placeholder agent message
    expect(result.current.messages).toHaveLength(3)
    expect(result.current.messages[1]).toEqual({ role: 'user', text: 'Hello Agent' })
    expect(result.current.messages[2]).toEqual(expect.objectContaining({ 
        role: 'agent', 
        isThinking: true 
    }))
    expect(result.current.isStreaming).toBe(true)

    // Verify fetchEventSource called correctly
    expect(fetchEventSource).toHaveBeenCalledWith(
      'http://test-api.com/a2a/pikar_ai/run_sse',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Authorization': 'Bearer mock-token'
        }),
        body: expect.stringContaining('Hello Agent')
      })
    )
  })

  it('handles streaming messages correctly', async () => {
    const { result } = renderHook(() => useAgentChat())
    
    // Mock fetchEventSource implementation to trigger onmessage
    vi.mocked(fetchEventSource).mockImplementation(async (url, options) => {
       if (options?.onmessage) {
           const mockEvent = {
               event: 'message',
               data: JSON.stringify({
                   author: 'ExecutiveAgent',
                   content: { parts: [{ text: 'Response' }] }
               })
           } as any
           options.onmessage(mockEvent)
       }
       if (options?.onclose) {
           options.onclose()
       }
    })

    await act(async () => {
      await result.current.sendMessage('Hi')
    })

    expect(result.current.messages[2].text).toBe('Response')
    expect(result.current.isStreaming).toBe(false)
  })

  it('handles errors gracefully', async () => {
     const { result } = renderHook(() => useAgentChat())

     vi.mocked(fetchEventSource).mockRejectedValue(new Error('Network Error'))

     await act(async () => {
       await result.current.sendMessage('Fail me')
     })

     expect(result.current.messages.length).toBeGreaterThan(0)
     const lastMsg = result.current.messages[result.current.messages.length - 1]
     expect(lastMsg.role).toBe('system')
     expect(result.current.isStreaming).toBe(false)
  })
})
