/**
 * @vitest-environment node
 */

import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'

const exchangeCodeForSessionMock = vi.fn()
const getUserMock = vi.fn()
const getSessionMock = vi.fn()
const createClientMock = vi.fn(async () => ({
  auth: {
    exchangeCodeForSession: exchangeCodeForSessionMock,
    getUser: getUserMock,
    getSession: getSessionMock,
  },
}))
const rateLimitCheckMock = vi.fn(() => ({ success: true }))

vi.mock('@/lib/supabase/server', () => ({
  createClient: createClientMock,
}))

vi.mock('@/lib/rate-limit', () => ({
  rateLimiters: {
    authenticated: {
      check: rateLimitCheckMock,
    },
  },
  getClientIp: vi.fn(() => '127.0.0.1'),
}))

describe('Google Workspace auth/status server contract', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
    vi.unstubAllGlobals()
    process.env.BACKEND_URL = 'http://backend.test'
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    delete process.env.BACKEND_URL
  })

  it('redirects successful OAuth callbacks to the dashboard command center', async () => {
    exchangeCodeForSessionMock.mockResolvedValue({
      data: {
        session: {
          access_token: 'supabase-jwt',
          provider_token: 'google-access-token',
          provider_refresh_token: 'google-refresh-token',
          user: {
            email: 'founder@example.com',
            app_metadata: {
              provider: 'google',
            },
          },
        },
      },
      error: null,
    })

    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    const { GET } = await import('@/app/auth/callback/route')
    const response = await GET(new Request('http://localhost/auth/callback?code=oauth-code'))

    expect(fetchMock).not.toHaveBeenCalled()
    expect(response.headers.get('location')).toBe('http://localhost/dashboard/command-center')
  })

  it('keeps the successful auth redirect focused on the dashboard even for Google OAuth sessions', async () => {
    exchangeCodeForSessionMock.mockResolvedValue({
      data: {
        session: {
          access_token: 'supabase-jwt',
          provider_token: 'google-access-token',
          provider_refresh_token: 'google-refresh-token',
          user: {
            email: 'founder@example.com',
            app_metadata: {
              provider: 'google',
            },
          },
        },
      },
      error: null,
    })

    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    const { GET } = await import('@/app/auth/callback/route')
    const response = await GET(
      new Request('http://localhost/auth/callback?code=oauth-code'),
    )

    expect(fetchMock).not.toHaveBeenCalled()
    expect(response.headers.get('location')).toBe('http://localhost/dashboard/command-center')
  })

  it('skips Google Workspace sync when the callback session is not Google OAuth', async () => {
    exchangeCodeForSessionMock.mockResolvedValue({
      data: {
        session: {
          access_token: 'supabase-jwt',
          user: {
            email: 'founder@example.com',
            app_metadata: {
              provider: 'email',
            },
          },
        },
      },
      error: null,
    })

    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    const { GET } = await import('@/app/auth/callback/route')
    await GET(new Request('http://localhost/auth/callback?code=email-code'))

    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('forwards the truthful backend Google Workspace status through the authenticated route', async () => {
    getUserMock.mockResolvedValue({
      data: {
        user: {
          id: 'user-123',
        },
      },
    })
    getSessionMock.mockResolvedValue({
      data: {
        session: {
          access_token: 'supabase-jwt',
        },
      },
    })

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        connected: false,
        needs_reconnect: true,
        message: 'Reconnect Google Workspace to finish storing a reusable server-side token.',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { GET } = await import('@/app/api/configuration/google-workspace-status/route')
    const response = await GET(
      new NextRequest('http://localhost/api/configuration/google-workspace-status'),
    )

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://backend.test/configuration/google-workspace-status?user_id=user-123')

    const headers = new Headers(init.headers)
    expect(headers.get('Authorization')).toBe('Bearer supabase-jwt')

    await expect(response.json()).resolves.toMatchObject({
      connected: false,
      needs_reconnect: true,
    })
  })
})
