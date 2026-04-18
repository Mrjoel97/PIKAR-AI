import { afterEach, describe, expect, it, vi } from 'vitest'

import { fetchPublicApi } from '@/services/api'

describe('invite flow trust contract', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('fetches public invite metadata without auth headers', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: 'invite-1' }),
    })
    vi.stubGlobal('fetch', fetchSpy)

    await fetchPublicApi('/teams/invites/details?token=test-token', { cache: 'no-store' }, false)

    expect(fetchSpy).toHaveBeenCalledTimes(1)

    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
    const headers = new Headers(init.headers)

    expect(url).toBe('http://localhost:8000/teams/invites/details?token=test-token')
    expect(headers.get('Authorization')).toBeNull()
    expect(init.cache).toBe('no-store')
  })

  it('normalizes public invite detail requests onto the backend origin', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: 'invite-1' }),
    })
    vi.stubGlobal('fetch', fetchSpy)

    await fetchPublicApi('teams/invites/details?token=second-token', {}, false)

    expect(fetchSpy).toHaveBeenCalledTimes(1)

    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
    const headers = new Headers(init.headers)

    expect(url).toBe('http://localhost:8000/teams/invites/details?token=second-token')
    expect(headers.get('Authorization')).toBeNull()
  })
})
