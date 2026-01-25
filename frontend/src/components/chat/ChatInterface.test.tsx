// @vitest-environment jsdom
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest'
import { ChatInterface } from './ChatInterface'

// Mock the useAgentChat hook
vi.mock('@/hooks/useAgentChat', () => ({
  useAgentChat: vi.fn()
}))

import { useAgentChat } from '@/hooks/useAgentChat'

describe('ChatInterface', () => {
  const mockSendMessage = vi.fn();
  const mockMessages = [
    { role: 'agent', text: 'Hello! I am Pikar AI. How can I help you optimize your business today?', agentName: 'ExecutiveAgent' }
  ];

  beforeEach(() => {
    // Mock scrollIntoView as it's not implemented in jsdom
    window.HTMLElement.prototype.scrollIntoView = vi.fn();

    vi.mocked(useAgentChat).mockReturnValue({
      messages: mockMessages,
      sendMessage: mockSendMessage,
      isStreaming: false
    })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders initial greeting', () => {
    render(<ChatInterface />)
    expect(screen.getByText(/Hello! I am Pikar AI/i)).toBeTruthy()
  })

  it('allows typing a message', async () => {
    render(<ChatInterface />)
    
    const input = screen.getByPlaceholderText(/Type your message/i)
    fireEvent.change(input, { target: { value: 'Test message' } })
    
    expect((input as HTMLInputElement).value).toBe('Test message')
  })

  it('calls sendMessage when clicking send', async () => {
    render(<ChatInterface />)
    
    const input = screen.getByPlaceholderText(/Type your message/i)
    const sendButton = screen.getByRole('button')

    fireEvent.change(input, { target: { value: 'Test message' } })
    fireEvent.click(sendButton)

    expect(mockSendMessage).toHaveBeenCalledWith('Test message')
    expect((input as HTMLInputElement).value).toBe('')
  })

  it('disables input when streaming', () => {
    vi.mocked(useAgentChat).mockReturnValue({
      messages: mockMessages,
      sendMessage: mockSendMessage,
      isStreaming: true
    })

    render(<ChatInterface />)
    const input = screen.getByPlaceholderText(/Type your message/i)
    expect((input as HTMLInputElement).disabled).toBe(true)
  })
})