/**
 * @vitest-environment node
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Regression coverage for vault proxy auth forwarding.
 *
 * Verifies:
 * - Authenticated search requests forward the server-resolved session token to the backend
 * - Authenticated process requests forward the server-resolved session token to the backend
 * - Unauthenticated requests fail cleanly with 401
 * - Body user_id does NOT replace the token-based auth contract
 */

import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

const getUserMock = vi.fn()
const getSessionMock = vi.fn()
const rateLimitCheckMock = vi.fn(() => ({ success: true }))

const makeJwt = (sub: string) => {
    const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url')
    const payload = Buffer.from(JSON.stringify({ sub, exp: 4070908800 })).toString('base64url')
    return `${header}.${payload}.signature`
}

vi.mock('@/lib/supabase/server', () => ({
    createClient: vi.fn(async () => ({
        auth: {
            getUser: getUserMock,
            getSession: getSessionMock,
        },
    })),
}))

vi.mock('@/lib/rate-limit', () => ({
    rateLimiters: {
        authenticated: {
            check: rateLimitCheckMock,
        },
    },
    getClientIp: vi.fn(() => '127.0.0.1'),
}))

describe('vault proxy auth forwarding contract', () => {
    beforeEach(() => {
        vi.resetModules()
        vi.clearAllMocks()
        vi.unstubAllGlobals()
        process.env.BACKEND_URL = 'http://backend.test'
        getSessionMock.mockResolvedValue({
            data: { session: { access_token: makeJwt('user-123') } },
            error: null,
        })
    })

    afterEach(() => {
        vi.unstubAllGlobals()
        delete process.env.BACKEND_URL
    })

    // -----------------------------------------------------------------------
    // Search proxy
    // -----------------------------------------------------------------------

    describe('POST /api/vault/search', () => {
        it('forwards the authenticated session token to the backend for search', async () => {
            getUserMock.mockResolvedValue({
                data: { user: { id: 'user-123', email: 'test@example.com' } },
                error: null,
            })
            const matchingJwt = makeJwt('user-123')

            const backendResponse = {
                results: [{ id: 'r1', content: 'match', similarity: 0.9 }],
                query: 'budget report',
                error: null,
            }
            const fetchMock = vi.fn().mockResolvedValue({
                ok: true,
                status: 200,
                json: async () => backendResponse,
            })
            vi.stubGlobal('fetch', fetchMock)

            const { POST } = await import('@/app/api/vault/search/route')
            const request = new Request('http://localhost/api/vault/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${matchingJwt}` },
                body: JSON.stringify({ query: 'budget report', top_k: 5 }),
            })

            const response = await POST(request as never)
            expect(response.status).toBe(200)

            expect(fetchMock).toHaveBeenCalledTimes(1)
            const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
            expect(url).toBe('http://backend.test/vault/search')

            const headers = new Headers(init.headers)
            expect(headers.get('Authorization')).toBe(`Bearer ${matchingJwt}`)
        })

        it('rejects unauthenticated search requests with 401', async () => {
            getUserMock.mockResolvedValue({
                data: { user: null },
                error: { message: 'Not authenticated' },
            })

            const fetchMock = vi.fn()
            vi.stubGlobal('fetch', fetchMock)

            const { POST } = await import('@/app/api/vault/search/route')
            const request = new Request('http://localhost/api/vault/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: 'test' }),
            })

            const response = await POST(request as never)
            expect(response.status).toBe(401)
            // Backend should never be called for unauthenticated requests
            expect(fetchMock).not.toHaveBeenCalled()
        })

        it('does not include user_id as a trust-escalation path in search forwarding', async () => {
            getUserMock.mockResolvedValue({
                data: { user: { id: 'user-123' } },
                error: null,
            })

            const fetchMock = vi.fn().mockResolvedValue({
                ok: true,
                status: 200,
                json: async () => ({ results: [], query: 'test', error: null }),
            })
            vi.stubGlobal('fetch', fetchMock)

            const { POST } = await import('@/app/api/vault/search/route')
            // Attacker supplies a different user_id in the body
            const request = new Request('http://localhost/api/vault/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${makeJwt('other-user')}` },
                body: JSON.stringify({ query: 'test', user_id: 'attacker-user-id' }),
            })

            await POST(request as never)

            // The authenticated session token is authoritative; caller-supplied
            // headers must not override the current cookie-backed user.
            const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
            const headers = new Headers(init.headers)
            expect(headers.get('Authorization')).toBe(`Bearer ${makeJwt('user-123')}`)
        })
    })

    // -----------------------------------------------------------------------
    // Process proxy
    // -----------------------------------------------------------------------

    describe('POST /api/vault/process', () => {
        it('forwards the authenticated session token to the backend for process', async () => {
            getUserMock.mockResolvedValue({
                data: { user: { id: 'user-123' } },
                error: null,
            })
            const matchingJwt = makeJwt('user-123')

            const fetchMock = vi.fn().mockResolvedValue({
                ok: true,
                status: 200,
                json: async () => ({ success: true, message: 'Processed 4 chunks', embedding_count: 4 }),
            })
            vi.stubGlobal('fetch', fetchMock)

            const { POST } = await import('@/app/api/vault/process/route')
            const request = new Request('http://localhost/api/vault/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${matchingJwt}` },
                body: JSON.stringify({ file_path: 'user-123/report.pdf' }),
            })

            const response = await POST(request as never)
            expect(response.status).toBe(200)

            expect(fetchMock).toHaveBeenCalledTimes(1)
            const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
            expect(url).toBe('http://backend.test/vault/process')

            const headers = new Headers(init.headers)
            expect(headers.get('Authorization')).toBe(`Bearer ${matchingJwt}`)
        })

        it('rejects unauthenticated process requests with 401', async () => {
            getUserMock.mockResolvedValue({
                data: { user: null },
                error: { message: 'Not authenticated' },
            })

            const fetchMock = vi.fn()
            vi.stubGlobal('fetch', fetchMock)

            const { POST } = await import('@/app/api/vault/process/route')
            const request = new Request('http://localhost/api/vault/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: 'some/file.txt' }),
            })

            const response = await POST(request as never)
            expect(response.status).toBe(401)
            expect(fetchMock).not.toHaveBeenCalled()
        })

        it('body user_id does not replace the token-based auth contract', async () => {
            getUserMock.mockResolvedValue({
                data: { user: { id: 'user-123' } },
                error: null,
            })

            const fetchMock = vi.fn().mockResolvedValue({
                ok: true,
                status: 200,
                json: async () => ({ success: true, message: 'done', embedding_count: 1 }),
            })
            vi.stubGlobal('fetch', fetchMock)

            const { POST } = await import('@/app/api/vault/process/route')
            // Attacker supplies a different user_id
            const request = new Request('http://localhost/api/vault/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${makeJwt('other-user')}` },
                body: JSON.stringify({ file_path: 'user-123/doc.txt', user_id: 'attacker-id' }),
            })

            const response = await POST(request as never)
            // Backend receives the authenticated session token — it will reject attacker-id itself
            const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
            const headers = new Headers(init.headers)
            expect(headers.get('Authorization')).toBe(`Bearer ${makeJwt('user-123')}`)
            // Response is proxied through correctly
            expect(response.status).toBe(200)
        })

        it('rejects authenticated requests when no session token is available to forward', async () => {
            getUserMock.mockResolvedValue({
                data: { user: { id: 'user-123' } },
                error: null,
            })
            getSessionMock.mockResolvedValue({
                data: { session: null },
                error: null,
            })

            const fetchMock = vi.fn()
            vi.stubGlobal('fetch', fetchMock)

            const { POST } = await import('@/app/api/vault/process/route')
            const request = new Request('http://localhost/api/vault/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${makeJwt('other-user')}` },
                body: JSON.stringify({ file_path: 'user-123/doc.txt' }),
            })

            const response = await POST(request as never)
            expect(response.status).toBe(401)
            expect(fetchMock).not.toHaveBeenCalled()
        })

        it('returns 400 when file_path is missing', async () => {
            getUserMock.mockResolvedValue({
                data: { user: { id: 'user-123' } },
                error: null,
            })

            const fetchMock = vi.fn()
            vi.stubGlobal('fetch', fetchMock)

            const { POST } = await import('@/app/api/vault/process/route')
            const request = new Request('http://localhost/api/vault/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer supabase-jwt' },
                body: JSON.stringify({}),
            })

            const response = await POST(request as never)
            expect(response.status).toBe(400)
            expect(fetchMock).not.toHaveBeenCalled()
        })

        it('preserves backend error detail for retryable process failures', async () => {
            getUserMock.mockResolvedValue({
                data: { user: { id: 'user-123' } },
                error: null,
            })

            const fetchMock = vi.fn().mockResolvedValue({
                ok: false,
                status: 403,
                json: async () => ({ detail: 'File access not allowed' }),
            })
            vi.stubGlobal('fetch', fetchMock)

            const { POST } = await import('@/app/api/vault/process/route')
            const request = new Request('http://localhost/api/vault/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${makeJwt('user-123')}` },
                body: JSON.stringify({ file_path: 'user-123/doc.txt' }),
            })

            const response = await POST(request as never)
            expect(response.status).toBe(403)
            await expect(response.json()).resolves.toEqual({
                success: false,
                detail: 'File access not allowed',
                error: 'File access not allowed',
                message: 'File access not allowed',
            })
        })
    })
})
