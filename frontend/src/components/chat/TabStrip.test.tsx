// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.
//
// TabStrip behavior tests — FEATURE-MULTI-SESSION-TABS, Plan 88-03.
//
// TabStrip is a stateless presentation component (no context, no hooks beyond
// JSX). Tests render the component directly with plain @testing-library/react;
// no harness or provider wrapping is needed. The 6 tests assert the props
// contract documented in TabStrip.tsx:
//
//   1. renders one pill per tab
//   2. active pill has distinct styling (teal background, aria-selected)
//   3. clicking a pill calls onSwitch with the id
//   4. clicking the × calls onClose with the id (and not onSwitch)
//   5. trailing + button calls onNew when below cap
//   6. trailing + is disabled at cap and does not fire onNew

import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'

import { TabStrip, type TabStripTab } from './TabStrip'

afterEach(() => {
  cleanup()
})

const baseTabs: TabStripTab[] = [
  { id: 'a', label: 'Alpha', isActive: false },
  { id: 'b', label: 'Beta', isActive: true },
]

describe('TabStrip — multi-session tabs (FEATURE-MULTI-SESSION-TABS)', () => {
  it('renders one pill per tab', () => {
    render(
      <TabStrip
        tabs={baseTabs}
        activeId="b"
        cap={5}
        onSwitch={vi.fn()}
        onClose={vi.fn()}
        onNew={vi.fn()}
      />,
    )
    expect(screen.getByText('Alpha')).toBeTruthy()
    expect(screen.getByText('Beta')).toBeTruthy()
  })

  it('active pill has distinct styling', () => {
    render(
      <TabStrip
        tabs={baseTabs}
        activeId="b"
        cap={5}
        onSwitch={vi.fn()}
        onClose={vi.fn()}
        onNew={vi.fn()}
      />,
    )
    // Use the data-testid pill button → walk up to the [role="tab"] container
    // (the styled wrapper) which holds the active styling and aria-selected.
    const activePill = screen.getByTestId('tab-pill-b')
    const activeContainer = activePill.closest('[role="tab"]') as HTMLElement
    expect(activeContainer).toBeTruthy()
    expect(activeContainer.className).toMatch(/bg-teal/)
    expect(activeContainer.getAttribute('aria-selected')).toBe('true')

    const inactivePill = screen.getByTestId('tab-pill-a')
    const inactiveContainer = inactivePill.closest(
      '[role="tab"]',
    ) as HTMLElement
    expect(inactiveContainer).toBeTruthy()
    expect(inactiveContainer.getAttribute('aria-selected')).toBe('false')
    // Inactive should NOT carry the active background class.
    expect(inactiveContainer.className).not.toMatch(/bg-teal-50/)
  })

  it('clicking a pill calls onSwitch with the id', () => {
    const onSwitch = vi.fn()
    render(
      <TabStrip
        tabs={baseTabs}
        activeId="b"
        cap={5}
        onSwitch={onSwitch}
        onClose={vi.fn()}
        onNew={vi.fn()}
      />,
    )
    fireEvent.click(screen.getByTestId('tab-pill-a'))
    expect(onSwitch).toHaveBeenCalledTimes(1)
    expect(onSwitch).toHaveBeenCalledWith('a')
  })

  it('clicking the × calls onClose with the id (and not onSwitch)', () => {
    const onSwitch = vi.fn()
    const onClose = vi.fn()
    render(
      <TabStrip
        tabs={baseTabs}
        activeId="b"
        cap={5}
        onSwitch={onSwitch}
        onClose={onClose}
        onNew={vi.fn()}
      />,
    )
    fireEvent.click(screen.getByTestId('tab-close-a'))
    expect(onClose).toHaveBeenCalledTimes(1)
    expect(onClose).toHaveBeenCalledWith('a')
    // The close button calls e.stopPropagation, so onSwitch must not fire.
    expect(onSwitch).not.toHaveBeenCalled()
  })

  it('trailing + button calls onNew when below cap', () => {
    const onNew = vi.fn()
    render(
      <TabStrip
        tabs={baseTabs}
        activeId="b"
        cap={5}
        onSwitch={vi.fn()}
        onClose={vi.fn()}
        onNew={onNew}
      />,
    )
    const newButton = screen.getByTestId('tab-new') as HTMLButtonElement
    expect(newButton.disabled).toBe(false)
    fireEvent.click(newButton)
    expect(onNew).toHaveBeenCalledTimes(1)
  })

  it('trailing + is disabled at cap and does not fire onNew', () => {
    const onNew = vi.fn()
    render(
      <TabStrip
        tabs={baseTabs}
        activeId="b"
        cap={2}
        onSwitch={vi.fn()}
        onClose={vi.fn()}
        onNew={onNew}
      />,
    )
    const newButton = screen.getByTestId('tab-new') as HTMLButtonElement
    expect(newButton.disabled).toBe(true)
    fireEvent.click(newButton)
    expect(onNew).not.toHaveBeenCalled()
  })
})

// ---------------------------------------------------------------------------
// Plan 88-04 — indicators prop (streaming dot / unread badge)
// FEATURE-MULTI-SESSION-TABS criterion 9
// ---------------------------------------------------------------------------

describe('TabStrip — indicators (FEATURE-MULTI-SESSION-TABS criterion 9)', () => {
  it('renders streaming dot on non-active streaming tab', () => {
    render(
      <TabStrip
        tabs={baseTabs}
        activeId="b"
        cap={5}
        onSwitch={vi.fn()}
        onClose={vi.fn()}
        onNew={vi.fn()}
        indicators={{ a: 'streaming' }}
      />,
    )
    const dot = screen.getByTestId('tab-indicator-a')
    expect(dot).toBeTruthy()
    // Streaming uses the pulsing animation.
    expect(dot.className).toMatch(/animate-pulse/)
    // Active tab b never shows an indicator regardless of map content.
    expect(screen.queryByTestId('tab-indicator-b')).toBeNull()
  })

  it('renders solid badge on non-active unread tab (no pulse)', () => {
    render(
      <TabStrip
        tabs={baseTabs}
        activeId="b"
        cap={5}
        onSwitch={vi.fn()}
        onClose={vi.fn()}
        onNew={vi.fn()}
        indicators={{ a: 'unread' }}
      />,
    )
    const dot = screen.getByTestId('tab-indicator-a')
    expect(dot).toBeTruthy()
    // Unread is a solid dot — distinct visual from streaming so the
    // user can tell "still working" from "finished but unviewed."
    expect(dot.className).not.toMatch(/animate-pulse/)
  })

  it('renders no indicator when state is none or absent', () => {
    const { rerender } = render(
      <TabStrip
        tabs={baseTabs}
        activeId="b"
        cap={5}
        onSwitch={vi.fn()}
        onClose={vi.fn()}
        onNew={vi.fn()}
        indicators={{ a: 'none' }}
      />,
    )
    expect(screen.queryByTestId('tab-indicator-a')).toBeNull()

    // Re-render without the indicators prop entirely — same outcome.
    rerender(
      <TabStrip
        tabs={baseTabs}
        activeId="b"
        cap={5}
        onSwitch={vi.fn()}
        onClose={vi.fn()}
        onNew={vi.fn()}
      />,
    )
    expect(screen.queryByTestId('tab-indicator-a')).toBeNull()
  })
})
