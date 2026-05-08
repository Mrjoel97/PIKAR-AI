/**
 * @vitest-environment node
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

const getUserMock = vi.fn()
const getSessionMock = vi.fn()

const makeJwt = (sub: string) => {
    const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url')
    const payload = Buffer.from(JSON.stringify({ sub, exp: 4070908800 })).toString('base64url')
    return `${header}.${payload}.signature`
}

vi.mock('@/lib/supabase/server', () => ({
    createClient: vi.fn(async () => ({
        auth: { getUser: getUserMock, getSession: getSessionMock },
    })),
}))

describe('GET /api/sessions/list', () => {
    beforeEach(() => {
        vi.resetModules()
        vi.clearAllMocks()
        process.env.BACKEND_URL = 'http://backend.test'
    })

    afterEach(() => {
        vi.unstubAllGlobals()
        delete process.env.BACKEND_URL
    })

    it('forwards the cookie JWT to the backend and returns the response', async () => {
        getUserMock.mockResolvedValue({ data: { user: { id: 'u' } } })
        getSessionMock.mockResolvedValue({
            data: { session: { access_token: makeJwt('u') } },
            error: null,
        })
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            json: async () => ({ sessions: [{ id: 's1', title: 'Hi', created_at: 'x', updated_at: 'y' }], count: 1 }),
        })
        vi.stubGlobal('fetch', fetchMock)

        const { GET } = await import('@/app/api/sessions/list/route')
        const req = new Request('http://localhost/api/sessions/list?limit=25')
        const res = await GET(req as never)
        const body = await res.json()

        expect(res.status).toBe(200)
        expect(body.count).toBe(1)
        const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
        expect(url).toBe('http://backend.test/sessions?limit=25')
        const headers = new Headers(init.headers)
        expect(headers.get('Authorization')).toBe(`Bearer ${makeJwt('u')}`)
    })

    it('returns 401 when no authenticated user', async () => {
        getUserMock.mockResolvedValue({ data: { user: null } })
        getSessionMock.mockResolvedValue({ data: { session: null }, error: null })
        const fetchMock = vi.fn()
        vi.stubGlobal('fetch', fetchMock)

        const { GET } = await import('@/app/api/sessions/list/route')
        const req = new Request('http://localhost/api/sessions/list')
        const res = await GET(req as never)
        expect(res.status).toBe(401)
        expect(fetchMock).not.toHaveBeenCalled()
    })

    it('passes through backend 5xx as 502 so the client can retry', async () => {
        getUserMock.mockResolvedValue({ data: { user: { id: 'u' } } })
        getSessionMock.mockResolvedValue({
            data: { session: { access_token: makeJwt('u') } },
            error: null,
        })
        const fetchMock = vi.fn().mockResolvedValue({
            ok: false,
            status: 503,
            json: async () => ({}),
            text: async () => 'unavailable',
        })
        vi.stubGlobal('fetch', fetchMock)

        const { GET } = await import('@/app/api/sessions/list/route')
        const res = await GET(new Request('http://localhost/api/sessions/list') as never)
        expect(res.status).toBe(502)
    })
})
