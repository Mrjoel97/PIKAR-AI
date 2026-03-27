// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createClient } from '@/lib/supabase/client'
import { fetchWithAuth, getClientPersonaHeader } from '@/services/api'

vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(),
}))

describe('api service trust contract', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.unstubAllGlobals()
    window.sessionStorage.clear()
    window.history.replaceState({}, '', '/')

    vi.mocked(createClient).mockReturnValue({
      auth: {
        getSession: vi.fn().mockResolvedValue({
          data: {
            session: {
              access_token: 'token-123',
            },
          },
        }),
      },
    } as never)
  })

  afterEach(() => {
    window.sessionStorage.clear()
    window.history.replaceState({}, '', '/')
    vi.unstubAllGlobals()
  })

  it('adds authorization, persona, and JSON headers to authenticated requests', async () => {
    window.sessionStorage.setItem('pikar:persona', 'startup')

    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true }),
    })
    vi.stubGlobal('fetch', fetchSpy)

    await fetchWithAuth('/workflows/templates', {
      method: 'POST',
      body: JSON.stringify({ name: 'Launch workflow' }),
    })

    expect(fetchSpy).toHaveBeenCalledTimes(1)

    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
    const headers = new Headers(init.headers)

    expect(url).toBe('http://localhost:8000/workflows/templates')
    expect(headers.get('Authorization')).toBe('Bearer token-123')
    expect(headers.get('x-pikar-persona')).toBe('startup')
    expect(headers.get('Content-Type')).toBe('application/json')
  })

  it('falls back to the current route when no persona is stored', () => {
    window.history.replaceState({}, '', '/enterprise/dashboard')

    expect(getClientPersonaHeader()).toBe('enterprise')
  })
})
