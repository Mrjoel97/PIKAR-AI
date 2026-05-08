/**
 * @vitest-environment node
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect } from 'vitest'
import { buildVaultActionPrompt, VaultActionItem } from '@/lib/vaultActions'

const items: VaultActionItem[] = [
    { id: 'a1', filename: 'hero.png', file_type: 'image/png', signed_url: 'https://x/a' },
    { id: 'a2', filename: 'demo.mp4', file_type: 'video/mp4', signed_url: 'https://x/b' },
]

describe('buildVaultActionPrompt', () => {
    it('builds a post-to-social prompt that lists every asset with filename and URL', () => {
        const prompt = buildVaultActionPrompt('post_social', items)
        expect(prompt).toContain('post these assets to social')
        expect(prompt.toLowerCase()).toContain('hero.png')
        expect(prompt).toContain('https://x/a')
        expect(prompt).toContain('demo.mp4')
        expect(prompt).toContain('https://x/b')
    })

    it('builds a campaign prompt', () => {
        const prompt = buildVaultActionPrompt('use_campaign', items)
        expect(prompt.toLowerCase()).toContain('marketing campaign')
        expect(prompt).toContain('hero.png')
    })

    it('builds an email prompt', () => {
        const prompt = buildVaultActionPrompt('draft_email', items)
        expect(prompt.toLowerCase()).toContain('email')
        expect(prompt).toContain('demo.mp4')
    })

    it('builds a custom-prompt scaffold with just the assets list', () => {
        const prompt = buildVaultActionPrompt('custom', items)
        expect(prompt).toContain('hero.png')
        expect(prompt).toContain('https://x/a')
        expect(prompt.toLowerCase()).not.toContain('post these assets')
        expect(prompt.toLowerCase()).not.toContain('marketing campaign')
    })

    it('throws on unknown action', () => {
        expect(() => buildVaultActionPrompt('explode' as never, items)).toThrow()
    })
})
