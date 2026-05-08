/**
 * @vitest-environment node
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

describe('listUserSessions retry behaviour', () => {
    beforeEach(() => {
        vi.resetModules()
    })

    afterEach(() => {
        vi.unstubAllGlobals()
        vi.useRealTimers()
    })

    it('hits /api/sessions/list and returns the parsed body', async () => {
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            json: async () => ({ sessions: [{ id: 's1' }], count: 1 }),
        })
        vi.stubGlobal('fetch', fetchMock)

        const { listUserSessions } = await import('@/services/sessions')
        const result = await listUserSessions(25)

        expect(result.count).toBe(1)
        expect(fetchMock).toHaveBeenCalledTimes(1)
        const [url] = fetchMock.mock.calls[0] as [string]
        expect(url).toBe('/api/sessions/list?limit=25')
    })

    it('retries once on a 5xx response and succeeds on the second try', async () => {
        const fetchMock = vi.fn()
            .mockResolvedValueOnce({ ok: false, status: 502, json: async () => ({}) })
            .mockResolvedValueOnce({
                ok: true,
                status: 200,
                json: async () => ({ sessions: [], count: 0 }),
            })
        vi.stubGlobal('fetch', fetchMock)

        const { listUserSessions } = await import('@/services/sessions')
        const result = await listUserSessions()

        expect(result.count).toBe(0)
        expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('does NOT retry on 4xx', async () => {
        const fetchMock = vi.fn().mockResolvedValue({
            ok: false,
            status: 401,
            json: async () => ({ error: 'unauthenticated' }),
        })
        vi.stubGlobal('fetch', fetchMock)

        const { listUserSessions } = await import('@/services/sessions')
        await expect(listUserSessions()).rejects.toThrow(/401/)
        expect(fetchMock).toHaveBeenCalledTimes(1)
    })
})
