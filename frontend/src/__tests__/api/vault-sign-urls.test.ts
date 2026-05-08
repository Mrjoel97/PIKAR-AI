/**
 * @vitest-environment node
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

const getUserMock = vi.fn()
const createSignedUrlsMock = vi.fn()
const fromMock = vi.fn(() => ({ createSignedUrls: createSignedUrlsMock }))

vi.mock('@/lib/supabase/server', () => ({
    createClient: vi.fn(async () => ({
        auth: { getUser: getUserMock },
        storage: { from: fromMock },
    })),
}))

describe('POST /api/vault/sign-urls', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    afterEach(() => {
        vi.resetModules()
    })

    it('returns signed URLs for the given paths in the requested bucket', async () => {
        getUserMock.mockResolvedValue({ data: { user: { id: 'user-1' } } })
        createSignedUrlsMock.mockResolvedValue({
            data: [
                { path: 'user-1/a.png', signedUrl: 'https://x/signed/a', error: null },
                { path: 'user-1/b.jpg', signedUrl: 'https://x/signed/b', error: null },
            ],
            error: null,
        })

        const { POST } = await import('@/app/api/vault/sign-urls/route')
        const req = new Request('http://localhost/api/vault/sign-urls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bucket: 'media-assets', paths: ['user-1/a.png', 'user-1/b.jpg'] }),
        })
        const res = await POST(req as never)
        const body = await res.json()

        expect(res.status).toBe(200)
        expect(fromMock).toHaveBeenCalledWith('media-assets')
        expect(createSignedUrlsMock).toHaveBeenCalledWith(['user-1/a.png', 'user-1/b.jpg'], 3600)
        expect(body.items).toEqual([
            { path: 'user-1/a.png', signedUrl: 'https://x/signed/a' },
            { path: 'user-1/b.jpg', signedUrl: 'https://x/signed/b' },
        ])
    })

    it('rejects unauthenticated requests with 401', async () => {
        getUserMock.mockResolvedValue({ data: { user: null } })

        const { POST } = await import('@/app/api/vault/sign-urls/route')
        const req = new Request('http://localhost/api/vault/sign-urls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bucket: 'media-assets', paths: ['x'] }),
        })
        const res = await POST(req as never)
        expect(res.status).toBe(401)
        expect(createSignedUrlsMock).not.toHaveBeenCalled()
    })

    it('rejects malformed bodies with 400', async () => {
        getUserMock.mockResolvedValue({ data: { user: { id: 'u' } } })

        const { POST } = await import('@/app/api/vault/sign-urls/route')
        const req = new Request('http://localhost/api/vault/sign-urls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bucket: 'media-assets' }), // no paths
        })
        const res = await POST(req as never)
        expect(res.status).toBe(400)
        expect(createSignedUrlsMock).not.toHaveBeenCalled()
    })

    it('caps paths at 200 to avoid runaway requests', async () => {
        getUserMock.mockResolvedValue({ data: { user: { id: 'u' } } })

        const { POST } = await import('@/app/api/vault/sign-urls/route')
        const paths = Array.from({ length: 250 }, (_, i) => `p/${i}`)
        const req = new Request('http://localhost/api/vault/sign-urls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bucket: 'media-assets', paths }),
        })
        const res = await POST(req as never)
        expect(res.status).toBe(400)
    })
})
