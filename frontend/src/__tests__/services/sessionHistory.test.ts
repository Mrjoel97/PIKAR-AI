// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const queryBuilder = {
  select: vi.fn(),
  eq: vi.fn(),
  is: vi.fn(),
  order: vi.fn(),
  limit: vi.fn(),
}

queryBuilder.select.mockImplementation(() => queryBuilder)
queryBuilder.eq.mockImplementation(() => queryBuilder)
queryBuilder.is.mockImplementation(() => queryBuilder)
queryBuilder.order.mockImplementation(() => queryBuilder)

const mockFrom = vi.fn(() => queryBuilder)

vi.mock('@/lib/supabase/client', () => ({
  createClient: () => ({
    from: mockFrom,
  }),
}))

import { loadSessionHistory } from '@/lib/sessionHistory'

describe('sessionHistory loader', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    queryBuilder.select.mockImplementation(() => queryBuilder)
    queryBuilder.eq.mockImplementation(() => queryBuilder)
    queryBuilder.is.mockImplementation(() => queryBuilder)
    queryBuilder.order.mockImplementation(() => queryBuilder)
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('reconstructs messages and restores widgets from wrapped function responses', async () => {
    queryBuilder.limit.mockResolvedValue({
      data: [
        {
          id: 'evt-2',
          app_name: 'agents',
          user_id: 'user-123',
          session_id: 'session-123',
          event_index: 1,
          created_at: '2026-05-03T00:00:05Z',
          event_data: {
            source: 'model',
            content: {
              parts: [
                { text: 'Here is your export.' },
                {
                  functionResponse: {
                    response: {
                      status: 'success',
                      widget: {
                        type: 'document',
                        title: 'Retention Metrics',
                        data: {
                          documentUrl: 'https://example.com/retention.xlsx',
                          title: 'Retention Metrics',
                          fileType: 'xlsx',
                          sizeBytes: 4096,
                        },
                      },
                    },
                  },
                },
              ],
            },
          },
        },
        {
          id: 'evt-1',
          app_name: 'agents',
          user_id: 'user-123',
          session_id: 'session-123',
          event_index: 0,
          created_at: '2026-05-03T00:00:00Z',
          event_data: {
            source: 'user',
            content: { parts: [{ text: 'Build me a retention workbook.' }] },
          },
        },
      ],
      error: null,
    })

    const messages = await loadSessionHistory('session-123', 'user-123')

    expect(mockFrom).toHaveBeenCalledWith('session_events')
    expect(messages).toHaveLength(2)
    expect(messages[0]).toEqual({
      id: 'evt-1',
      role: 'user',
      text: 'Build me a retention workbook.',
    })
    expect(messages[1]).toMatchObject({
      id: 'evt-2',
      role: 'agent',
      text: 'Here is your export.',
      widget: {
        type: 'document',
        data: {
          documentUrl: 'https://example.com/retention.xlsx',
          fileType: 'xlsx',
        },
      },
    })
  })

  it('returns an empty array when the session_events query fails', async () => {
    queryBuilder.limit.mockResolvedValue({
      data: null,
      error: { message: 'database unavailable' },
    })

    await expect(loadSessionHistory('session-123', 'user-123')).resolves.toEqual([])
  })
})
