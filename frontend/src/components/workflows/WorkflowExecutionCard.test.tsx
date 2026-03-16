// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

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

  it('shows automation, approval, verification, and evidence badges for durable runs', () => {
    const execution = {
      id: 'exec-2',
      user_id: 'user-1',
      template_id: 'template-2',
      name: 'Durable workflow',
      status: 'waiting_approval',
      current_phase_index: 1,
      current_step_index: 0,
      context: {
        topic: 'Pipeline cleanup',
        department: 'sales',
        trigger: {
          type: 'event',
          event_name: 'workflow.started',
          reason: 'event',
        },
      },
      approval_state: 'pending',
      verification_status: 'verified',
      evidence_refs: [{ href: '/proof/1' }, { href: '/proof/2' }],
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      template_name: 'Revenue Ops',
    } as any

    render(<WorkflowExecutionCard execution={execution} onClick={() => undefined} />)

    expect(screen.getByText('Event Hook')).toBeTruthy()
    expect(screen.getByText('sales')).toBeTruthy()
    expect(screen.getByText('Approval: Pending')).toBeTruthy()
    expect(screen.getByText('Verification: Verified')).toBeTruthy()
    expect(screen.getByText('2 evidence items')).toBeTruthy()
    expect(screen.getByText('Event: workflow.started')).toBeTruthy()
  })
})
