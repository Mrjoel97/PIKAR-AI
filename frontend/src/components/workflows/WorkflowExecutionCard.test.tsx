// @vitest-environment jsdom
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach, vi } from 'vitest'
import WorkflowExecutionCard from './WorkflowExecutionCard'

describe('WorkflowExecutionCard', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders safely when execution context is null and falls back to template name', () => {
    const onClick = vi.fn()
    const execution = {
      id: 'exec-1',
      user_id: 'user-1',
      template_id: 'template-1',
      name: 'Test workflow',
      status: 'pending',
      current_phase_index: 0,
      current_step_index: 0,
      context: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      template_name: 'Quarterly Review',
    } as any

    render(<WorkflowExecutionCard execution={execution} onClick={onClick} />)

    const title = screen.getByText('Quarterly Review', { selector: 'h4' })
    expect(title).toBeTruthy()
    fireEvent.click(title)
    expect(onClick).toHaveBeenCalledWith('exec-1')
  })
})
