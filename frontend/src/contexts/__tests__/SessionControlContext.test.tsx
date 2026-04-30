// @vitest-environment jsdom
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.
//
// SessionControlContext behavior tests — HOTFIX-06 persistence reconciliation.
//
// Covers the four ROADMAP success criteria for chat-history-on-reload that
// shipped in commit c8da1d99 (2026-04-27) without test coverage:
//   1. localStorage restore on mount
//   2. localStorage persist on change
//   3. createNewChat replaces stored id
//   4. cross-browser-tab safety via the `storage` event (RED until Task 2)
//
// SessionControlProvider requires SessionMapProvider as a parent (calls
// useSessionMap() at line 105-111) and uses the supabase client + the
// listUserSessions service on mount, so we mock those at module scope.

import React from 'react'
import { render, screen, fireEvent, waitFor, cleanup, act } from '@testing-library/react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// ---------------------------------------------------------------------------
// Module-scope mocks — must be declared before importing the providers.
// ---------------------------------------------------------------------------

vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'test-user' } }, error: null }),
    },
    from: vi.fn(() => ({
      select: vi.fn(() => ({
        eq: vi.fn(() => ({
          eq: vi.fn(() => ({
            eq: vi.fn(() => ({
              single: vi.fn().mockResolvedValue({ data: { state: {} }, error: null }),
            })),
          })),
          single: vi.fn().mockResolvedValue({ data: { state: {} }, error: null }),
        })),
      })),
      delete: vi.fn(() => ({
        eq: vi.fn(() => ({
          eq: vi.fn(() => ({
            eq: vi.fn().mockResolvedValue({ data: null, error: null }),
          })),
        })),
      })),
      update: vi.fn(() => ({
        eq: vi.fn(() => ({
          eq: vi.fn(() => ({
            eq: vi.fn().mockResolvedValue({ data: null, error: null }),
          })),
        })),
      })),
    })),
  })),
}))

vi.mock('@/services/sessions', () => ({
  listUserSessions: vi.fn().mockResolvedValue({ sessions: [], count: 0 }),
}))

// Imports must come AFTER vi.mock — vitest hoists mocks to the top so by the
// time these imports execute the factories are already registered.
import { SessionControlProvider, useSessionControl } from '../SessionControlContext'
import { SessionMapProvider } from '../SessionMapContext'

const STORAGE_KEY = 'pikar_current_session_id'

// ---------------------------------------------------------------------------
// Consumer component — exposes the context state via DOM elements so tests
// can drive interactions without renderHook gymnastics.
// ---------------------------------------------------------------------------

function Consumer() {
  const ctx = useSessionControl()
  return (
    <div>
      <span data-testid="vsid">{ctx.visibleSessionId ?? 'null'}</span>
      <span data-testid="restored">{String(ctx.sessionRestored)}</span>
      <button
        data-testid="set"
        onClick={() => ctx.setVisibleSessionId('session-new-456')}
      >
        set
      </button>
      <button data-testid="new" onClick={() => ctx.createNewChat()}>
        new
      </button>
    </div>
  )
}

function renderWithProviders() {
  return render(
    <SessionMapProvider>
      <SessionControlProvider>
        <Consumer />
      </SessionControlProvider>
    </SessionMapProvider>,
  )
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  localStorage.clear()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SessionControlContext — persistence (HOTFIX-06)', () => {
  it('Test 1: restores session_id from localStorage on mount', async () => {
    localStorage.setItem(STORAGE_KEY, 'session-test-restore-123')

    renderWithProviders()

    await waitFor(() => {
      expect(screen.getByTestId('vsid').textContent).toBe('session-test-restore-123')
    })
    expect(screen.getByTestId('restored').textContent).toBe('true')
  })

  it('Test 2: persists session_id to localStorage on change', async () => {
    renderWithProviders()

    // sessionRestored becomes true after the layout effect; wait for it so
    // the consumer renders the buttons we can click.
    await waitFor(() => {
      expect(screen.getByTestId('restored').textContent).toBe('true')
    })

    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()

    await act(async () => {
      fireEvent.click(screen.getByTestId('set'))
    })

    expect(localStorage.getItem(STORAGE_KEY)).toBe('session-new-456')
    await waitFor(() => {
      expect(screen.getByTestId('vsid').textContent).toBe('session-new-456')
    })
  })

  it('Test 3: createNewChat replaces stored session_id', async () => {
    localStorage.setItem(STORAGE_KEY, 'session-old-789')

    renderWithProviders()

    await waitFor(() => {
      expect(screen.getByTestId('vsid').textContent).toBe('session-old-789')
    })

    await act(async () => {
      fireEvent.click(screen.getByTestId('new'))
    })

    const stored = localStorage.getItem(STORAGE_KEY)
    expect(stored).not.toBe('session-old-789')
    expect(stored).not.toBeNull()
    // generateSessionId() shape: `session-${Date.now()}-${random}`
    expect(stored).toMatch(/^session-\d+-[a-z0-9]+$/)
  })

  it('Test 4: cross-tab storage event updates visibleSessionId', async () => {
    localStorage.setItem(STORAGE_KEY, 'session-tab-A')

    renderWithProviders()

    await waitFor(() => {
      expect(screen.getByTestId('vsid').textContent).toBe('session-tab-A')
    })

    // jsdom does not fire `storage` from local localStorage.setItem in the
    // same window — the spec says it only fires in OTHER same-origin tabs.
    // We dispatch a synthetic StorageEvent to simulate another tab's write.
    await act(async () => {
      const event = new StorageEvent('storage', {
        key: STORAGE_KEY,
        newValue: 'session-tab-B',
        oldValue: 'session-tab-A',
        storageArea: window.localStorage,
      })
      window.dispatchEvent(event)
    })

    await waitFor(() => {
      expect(screen.getByTestId('vsid').textContent).toBe('session-tab-B')
    })
  })
})
