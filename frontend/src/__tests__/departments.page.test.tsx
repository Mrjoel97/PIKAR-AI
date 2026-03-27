// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import DepartmentsPage from '@/app/departments/page'
import { listDepartments, toggleDepartment, triggerDepartmentHeartbeat } from '@/services/departments'
import {
  createWorkflowTrigger,
  deleteWorkflowTrigger,
  listWorkflowExecutions,
  listWorkflowTemplates,
  listWorkflowTriggers,
  updateWorkflowTrigger,
} from '@/services/workflows'

vi.mock('@/components/layout/PremiumShell', () => ({
  default: ({ children }: { children: any }) => <div>{children}</div>,
}))

vi.mock('@/components/workflows/WorkflowTriggerCard', () => ({
  default: () => <div>Trigger Card</div>,
}))

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

vi.mock('@/services/departments', () => ({
  listDepartments: vi.fn(),
  toggleDepartment: vi.fn(),
  triggerDepartmentHeartbeat: vi.fn(),
}))

vi.mock('@/services/workflows', () => ({
  createWorkflowTrigger: vi.fn(),
  deleteWorkflowTrigger: vi.fn(),
  listWorkflowExecutions: vi.fn(),
  listWorkflowTemplates: vi.fn(),
  listWorkflowTriggers: vi.fn(),
  updateWorkflowTrigger: vi.fn(),
}))

async function flushMicrotasks() {
  await Promise.resolve()
  await Promise.resolve()
}

describe('DepartmentsPage polling', () => {
  let hidden = false

  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()

    hidden = false
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      get: () => hidden,
    })

    vi.mocked(listDepartments).mockResolvedValue([
      {
        id: 'dept-1',
        name: 'Content Studio',
        type: 'CONTENT',
        status: 'RUNNING',
        state: {},
        last_heartbeat: null,
      },
    ] as any)
    vi.mocked(listWorkflowTemplates).mockResolvedValue([
      { id: 'tpl-1', name: 'Published Workflow', description: 'Ready', category: 'ops' },
    ] as any)
    vi.mocked(listWorkflowTriggers).mockResolvedValue([] as any)
    vi.mocked(listWorkflowExecutions).mockResolvedValue([] as any)
    vi.mocked(createWorkflowTrigger).mockResolvedValue({ trigger: { id: 'trigger-1' } } as any)
    vi.mocked(updateWorkflowTrigger).mockResolvedValue({ trigger: { id: 'trigger-1' } } as any)
    vi.mocked(deleteWorkflowTrigger).mockResolvedValue({} as any)
    vi.mocked(toggleDepartment).mockResolvedValue({} as any)
    vi.mocked(triggerDepartmentHeartbeat).mockResolvedValue({} as any)
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('polls with a single batched execution request, skips template reloads, and pauses when hidden', async () => {
    render(<DepartmentsPage />)

    await act(async () => {
      await flushMicrotasks()
    })

    expect(screen.getByText('Autonomous Departments')).toBeTruthy()
    expect(listDepartments).toHaveBeenCalledTimes(1)
    expect(listWorkflowTemplates).toHaveBeenCalledTimes(1)
    expect(listWorkflowTriggers).toHaveBeenCalledTimes(1)
    expect(listWorkflowExecutions).toHaveBeenCalledTimes(1)
    expect(listWorkflowExecutions).toHaveBeenLastCalledWith(['running', 'waiting_approval', 'pending'], 60)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(20_000)
      await flushMicrotasks()
    })

    expect(listDepartments).toHaveBeenCalledTimes(2)
    expect(listWorkflowTemplates).toHaveBeenCalledTimes(1)
    expect(listWorkflowTriggers).toHaveBeenCalledTimes(2)
    expect(listWorkflowExecutions).toHaveBeenCalledTimes(2)
    expect(listWorkflowExecutions).toHaveBeenLastCalledWith(['running', 'waiting_approval', 'pending'], 60)

    hidden = true
    await act(async () => {
      await vi.advanceTimersByTimeAsync(20_000)
      await flushMicrotasks()
    })

    expect(listDepartments).toHaveBeenCalledTimes(2)
    expect(listWorkflowExecutions).toHaveBeenCalledTimes(2)

    hidden = false
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'))
      await flushMicrotasks()
    })

    expect(listDepartments).toHaveBeenCalledTimes(3)
    expect(listWorkflowExecutions).toHaveBeenCalledTimes(3)
  })
})
