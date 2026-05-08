/**
 * @vitest-environment jsdom
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { VaultActionBar } from '@/components/vault/VaultActionBar'

describe('<VaultActionBar />', () => {
    it('renders the count and four chips when at least one item is selected', () => {
        render(
            <VaultActionBar
                selectedCount={3}
                onAction={vi.fn()}
                onClear={vi.fn()}
            />,
        )
        expect(screen.getByText(/3 selected/i)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /post to social/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /use in campaign/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /draft an email/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /custom prompt/i })).toBeInTheDocument()
    })

    it('returns null when selectedCount is 0', () => {
        const { container } = render(
            <VaultActionBar selectedCount={0} onAction={vi.fn()} onClear={vi.fn()} />,
        )
        expect(container.firstChild).toBeNull()
    })

    it('calls onAction with the action id when a chip is clicked', () => {
        const onAction = vi.fn()
        render(
            <VaultActionBar selectedCount={2} onAction={onAction} onClear={vi.fn()} />,
        )
        fireEvent.click(screen.getByRole('button', { name: /post to social/i }))
        expect(onAction).toHaveBeenCalledWith('post_social')
    })

    it('calls onClear when Clear is clicked', () => {
        const onClear = vi.fn()
        render(
            <VaultActionBar selectedCount={1} onAction={vi.fn()} onClear={onClear} />,
        )
        fireEvent.click(screen.getByRole('button', { name: /clear/i }))
        expect(onClear).toHaveBeenCalled()
    })
})
