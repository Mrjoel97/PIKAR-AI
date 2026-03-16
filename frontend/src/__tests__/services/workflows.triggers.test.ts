import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  createWorkflowTrigger,
  deleteWorkflowTrigger,
  listWorkflowTriggers,
  updateWorkflowTrigger,
} from '@/services/workflows'
import { fetchWithAuth } from '@/services/api'

vi.mock('@/services/api', () => ({
  fetchWithAuth: vi.fn(),
  getClientPersonaHeader: vi.fn(() => null),
}))

vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(),
}))

describe('workflow trigger service helpers', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('builds trigger list query params for template, enabled state, and department', async () => {
    vi.mocked(fetchWithAuth).mockResolvedValue({
      json: async () => ({ triggers: [] }),
    } as Response)

    await listWorkflowTriggers({ templateId: 'tpl-1', enabled: true, department: 'sales' })

    expect(fetchWithAuth).toHaveBeenCalledWith('/workflow-triggers?template_id=tpl-1&enabled=true&department=sales')
  })

  it('creates, updates, and deletes workflow triggers through the expected endpoints', async () => {
    vi.mocked(fetchWithAuth).mockResolvedValue({
      json: async () => ({ status: 'success', trigger: { id: 'trigger-1' } }),
    } as Response)

    await createWorkflowTrigger({
      template_id: 'tpl-1',
      trigger_name: 'Daily ops',
      trigger_type: 'schedule',
      schedule_frequency: 'daily',
    })
    await updateWorkflowTrigger('trigger-1', { trigger_name: 'Updated ops' })
    await deleteWorkflowTrigger('trigger-1')

    expect(fetchWithAuth).toHaveBeenNthCalledWith(1, '/workflow-triggers', expect.objectContaining({
      method: 'POST',
    }))
    expect(fetchWithAuth).toHaveBeenNthCalledWith(2, '/workflow-triggers/trigger-1', expect.objectContaining({
      method: 'PATCH',
    }))
    expect(fetchWithAuth).toHaveBeenNthCalledWith(3, '/workflow-triggers/trigger-1', expect.objectContaining({
      method: 'DELETE',
    }))
  })
})
