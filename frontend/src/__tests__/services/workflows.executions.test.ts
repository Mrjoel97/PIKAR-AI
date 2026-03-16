import { beforeEach, describe, expect, it, vi } from 'vitest'

import { listWorkflowExecutions } from '@/services/workflows'
import { fetchWithAuth } from '@/services/api'

vi.mock('@/services/api', () => ({
  fetchWithAuth: vi.fn(),
  getClientPersonaHeader: vi.fn(() => null),
}))

vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(),
}))

describe('workflow execution service helpers', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('builds a batched statuses query for active execution polling', async () => {
    vi.mocked(fetchWithAuth).mockResolvedValue({
      json: async () => ([]),
    } as Response)

    await listWorkflowExecutions(['running', 'waiting_approval', 'pending'], 60)

    expect(fetchWithAuth).toHaveBeenCalledWith('/workflows/executions?statuses=running%2Cwaiting_approval%2Cpending&limit=60')
  })

  it('preserves the single-status execution query shape', async () => {
    vi.mocked(fetchWithAuth).mockResolvedValue({
      json: async () => ([]),
    } as Response)

    await listWorkflowExecutions('completed', 25, 50)

    expect(fetchWithAuth).toHaveBeenCalledWith('/workflows/executions?status=completed&limit=25&offset=50')
  })
})
