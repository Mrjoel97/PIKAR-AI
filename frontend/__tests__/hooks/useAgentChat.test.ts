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
    expect(result.current.messages[1]).toEqual(expect.objectContaining({ role: 'user', text: 'Hello Agent' }))
    expect(result.current.messages[2]).toEqual(expect.objectContaining({ 
        role: 'agent'
    }))
    expect(typeof result.current.isStreaming).toBe('boolean')

    // Verify fetchEventSource called correctly
    expect(fetchEventSource).toHaveBeenCalledWith(
      'http://test-api.com/a2a/app/run_sse',
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

  it('renders live director progress as trace timeline entries', async () => {
    const { result } = renderHook(() => useAgentChat())

    vi.mocked(fetchEventSource).mockImplementation(async (_url, options) => {
      if (options?.onmessage) {
        options.onmessage({
          event: 'message',
          data: JSON.stringify({
            event_type: 'director_progress',
            stage: 'planning_started',
            payload: { scene_count: 4 }
          })
        } as any)
        options.onmessage({
          event: 'message',
          data: JSON.stringify({
            event_type: 'director_progress',
            stage: 'rendering_started',
            payload: { duration_frames: 240 }
          })
        } as any)
      }
      if (options?.onclose) {
        options.onclose()
      }
    })

    await act(async () => {
      await result.current.sendMessage('Create a pro video')
    })

    const lastMsg = result.current.messages[result.current.messages.length - 1]
    expect(lastMsg.role).toBe('agent')
    expect(lastMsg.traces?.length).toBeGreaterThanOrEqual(2)
    expect(lastMsg.traces?.some((t) => t.toolName === 'AI Director')).toBe(true)
    expect(lastMsg.traces?.some((t) => t.content.includes('Planning storyboard'))).toBe(true)
    expect(lastMsg.traces?.some((t) => t.content.includes('Rendering final video'))).toBe(true)
  })
})
