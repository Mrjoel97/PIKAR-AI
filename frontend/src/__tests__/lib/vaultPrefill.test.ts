/**
 * @vitest-environment jsdom
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
    mintPrefillSessionId,
    storeVaultPrefill,
    consumeVaultPrefill,
    PREFILL_STORAGE_PREFIX,
} from '@/lib/vaultPrefill'

vi.mock('@/lib/freshClientSessions', () => ({
    markFreshClientSession: vi.fn(),
}))

describe('vaultPrefill', () => {
    beforeEach(() => {
        sessionStorage.clear()
    })

    afterEach(() => {
        sessionStorage.clear()
    })

    it('mints a session id starting with `session-`', () => {
        const id = mintPrefillSessionId()
        expect(id).toMatch(/^session-\d+-[a-z0-9]+$/)
    })

    it('stores and consumes the prefill exactly once', () => {
        const id = 'session-1-abc'
        storeVaultPrefill(id, 'hello world')
        expect(sessionStorage.getItem(`${PREFILL_STORAGE_PREFIX}${id}`)).toBe('hello world')

        const first = consumeVaultPrefill(id)
        expect(first).toBe('hello world')

        const second = consumeVaultPrefill(id)
        expect(second).toBeNull()
    })

    it('returns null when nothing is stored', () => {
        expect(consumeVaultPrefill('missing')).toBeNull()
    })
})
