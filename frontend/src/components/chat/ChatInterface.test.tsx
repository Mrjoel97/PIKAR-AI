// @vitest-environment jsdom
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, afterEach } from 'vitest'
import { ChatInterface } from './ChatInterface'

describe('ChatInterface', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders initial greeting', () => {
    render(<ChatInterface />)
    expect(screen.getByText('Hello! How can I help you today?')).toBeTruthy()
  })

  it('allows sending a message', async () => {
    render(<ChatInterface />)
    
    const input = screen.getByLabelText('Message input')
    const sendButton = screen.getByLabelText('Send message')

    fireEvent.change(input, { target: { value: 'Test message' } })
    fireEvent.click(sendButton)

    // User message should appear
    expect(screen.getByText('Test message')).toBeTruthy()
    // Input should be cleared
    expect((input as HTMLInputElement).value).toBe('')

    // Agent response should appear (after timeout)
    await waitFor(() => {
        expect(screen.getByText('I am a placeholder agent.')).toBeTruthy()
    })
  })
})
