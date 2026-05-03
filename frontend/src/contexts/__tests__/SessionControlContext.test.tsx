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

// Module-scope spies for SessionMapContext.useSessionMap — Tests 11+ assert
// on these. We use Option B from the plan (mock the entire useSessionMap
// hook while preserving the real SessionMapProvider for existing tests that
// render through it). The provider becomes a passthrough since the consumer
// reads via the mocked hook, not via context.
const removeActiveSessionMock = vi.fn()
const addActiveSessionMock = vi.fn()

vi.mock('@/contexts/SessionMapContext', async () => {
  const actual = await vi.importActual<typeof import('@/contexts/SessionMapContext')>(
    '@/contexts/SessionMapContext',
  )
  return {
    ...actual,
    useSessionMap: () => ({
      activeSessions: new Map(),
      addActiveSession: addActiveSessionMock,
      removeActiveSession: removeActiveSessionMock,
      updateSessionState: vi.fn(),
      getActiveSessionRef: vi.fn(() => null),
      sessions: [],
      setSessions: vi.fn(),
      isLoadingSessions: false,
      setIsLoadingSessions: vi.fn(),
    }),
  }
})

// Imports must come AFTER vi.mock — vitest hoists mocks to the top so by the
// time these imports execute the factories are already registered.
import {
  SessionControlProvider,
  TabCapReachedError,
  useSessionControl,
} from '../SessionControlContext'
import { PENDING_CHAT_SESSION_IDS_STORAGE_KEY } from '@/lib/pendingChatSessions'
import { SessionMapProvider } from '../SessionMapContext'

const STORAGE_KEY = 'pikar_current_session_id'
const OPEN_TABS_STORAGE_KEY = 'pikar_open_tab_ids'

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
    expect(
      JSON.parse(localStorage.getItem(PENDING_CHAT_SESSION_IDS_STORAGE_KEY) || '[]'),
    ).toContain(stored)
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

// ---------------------------------------------------------------------------
// Multi-session tabs (FEATURE-MULTI-SESSION-TABS) — Tests 6-14
// ---------------------------------------------------------------------------

function TabConsumer({ onError }: { onError?: (e: unknown) => void }) {
  const ctx = useSessionControl()
  return (
    <div>
      <span data-testid="vsid">{ctx.visibleSessionId ?? 'null'}</span>
      <span data-testid="tabs">{JSON.stringify(ctx.openTabIds)}</span>
      <span data-testid="cap">{ctx.tabCap}</span>
      <button
        data-testid="open"
        onClick={(e) => {
          const id = (e.currentTarget as HTMLButtonElement).dataset.id!
          try {
            ctx.openTab(id)
          } catch (err) {
            onError?.(err)
          }
        }}
      />
      <button
        data-testid="close"
        onClick={(e) => {
          const id = (e.currentTarget as HTMLButtonElement).dataset.id!
          ctx.closeTab(id)
        }}
      />
    </div>
  )
}

function renderWithTabConsumer(onError?: (e: unknown) => void) {
  return render(
    <SessionMapProvider>
      <SessionControlProvider>
        <TabConsumer onError={onError} />
      </SessionControlProvider>
    </SessionMapProvider>,
  )
}

function clickOpen(id: string) {
  const btn = screen.getByTestId('open') as HTMLButtonElement
  btn.dataset.id = id
  fireEvent.click(btn)
}

function clickClose(id: string) {
  const btn = screen.getByTestId('close') as HTMLButtonElement
  btn.dataset.id = id
  fireEvent.click(btn)
}

function readOpenTabIds(): string[] {
  return JSON.parse(screen.getByTestId('tabs').textContent || '[]')
}

describe('SessionControlContext — multi-session tabs (FEATURE-MULTI-SESSION-TABS)', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('Test 6: openTab adds id to openTabIds', async () => {
    renderWithTabConsumer()

    await waitFor(() => {
      expect(screen.getByTestId('vsid')).toBeTruthy()
    })

    await act(async () => {
      clickOpen('session-A')
    })

    expect(readOpenTabIds()).toEqual(['session-A'])
  })

  it('Test 7: openTab is idempotent on duplicate', async () => {
    renderWithTabConsumer()

    await waitFor(() => {
      expect(screen.getByTestId('vsid')).toBeTruthy()
    })

    await act(async () => {
      clickOpen('session-A')
    })
    await act(async () => {
      clickOpen('session-A')
    })

    expect(readOpenTabIds()).toEqual(['session-A'])
  })

  it('Test 8: openTab makes the session visible (and persists session_id)', async () => {
    renderWithTabConsumer()

    await waitFor(() => {
      expect(screen.getByTestId('vsid')).toBeTruthy()
    })

    await act(async () => {
      clickOpen('session-X')
    })

    expect(screen.getByTestId('vsid').textContent).toBe('session-X')
    expect(localStorage.getItem(STORAGE_KEY)).toBe('session-X')
  })

  it('Test 9: openTab persists openTabIds to localStorage', async () => {
    renderWithTabConsumer()

    await waitFor(() => {
      expect(screen.getByTestId('vsid')).toBeTruthy()
    })

    await act(async () => {
      clickOpen('session-A')
    })
    await act(async () => {
      clickOpen('session-B')
    })

    expect(JSON.parse(localStorage.getItem(OPEN_TABS_STORAGE_KEY) || '[]')).toEqual([
      'session-A',
      'session-B',
    ])
  })

  it('Test 10: openTab at cap throws TabCapReachedError', async () => {
    let capturedError: unknown = null
    renderWithTabConsumer((err) => {
      capturedError = err
    })

    await waitFor(() => {
      expect(screen.getByTestId('cap').textContent).toBe('5')
    })

    // Open 5 tabs — at the free-tier cap.
    for (const id of ['session-1', 'session-2', 'session-3', 'session-4', 'session-5']) {
      await act(async () => {
        clickOpen(id)
      })
    }

    expect(readOpenTabIds()).toEqual([
      'session-1',
      'session-2',
      'session-3',
      'session-4',
      'session-5',
    ])

    // 6th attempt — must throw TabCapReachedError(5)
    await act(async () => {
      clickOpen('session-6')
    })

    expect(capturedError).toBeInstanceOf(TabCapReachedError)
    expect((capturedError as TabCapReachedError).cap).toBe(5)
    // No state mutation on cap rejection
    expect(readOpenTabIds()).toEqual([
      'session-1',
      'session-2',
      'session-3',
      'session-4',
      'session-5',
    ])
  })

  it('Test 11: closeTab removes id from openTabIds and calls removeActiveSession', async () => {
    renderWithTabConsumer()

    await waitFor(() => {
      expect(screen.getByTestId('vsid')).toBeTruthy()
    })

    await act(async () => {
      clickOpen('session-A')
    })
    await act(async () => {
      clickOpen('session-B')
    })

    await act(async () => {
      clickClose('session-A')
    })

    expect(readOpenTabIds()).toEqual(['session-B'])
    expect(removeActiveSessionMock).toHaveBeenCalledWith('session-A')
  })

  it('Test 12: closeTab on visible tab promotes the most-recently-opened remaining tab', async () => {
    renderWithTabConsumer()

    await waitFor(() => {
      expect(screen.getByTestId('vsid')).toBeTruthy()
    })

    await act(async () => {
      clickOpen('session-A')
    })
    await act(async () => {
      clickOpen('session-B')
    })
    await act(async () => {
      clickOpen('session-C')
    })

    // Visible should now be session-C (last-opened)
    expect(screen.getByTestId('vsid').textContent).toBe('session-C')

    await act(async () => {
      clickClose('session-C')
    })

    // Most-recently opened remaining tab is session-B (last in the array
    // after the splice-out of session-C).
    expect(screen.getByTestId('vsid').textContent).toBe('session-B')
    expect(readOpenTabIds()).toEqual(['session-A', 'session-B'])
  })

  it('Test 13: closeTab on the last remaining tab triggers createNewChat', async () => {
    renderWithTabConsumer()

    await waitFor(() => {
      expect(screen.getByTestId('vsid')).toBeTruthy()
    })

    await act(async () => {
      clickOpen('session-only')
    })

    expect(readOpenTabIds()).toEqual(['session-only'])

    await act(async () => {
      clickClose('session-only')
    })

    const tabs = readOpenTabIds()
    // openTabIds.length === 1 because createNewChat replaced the closed tab
    expect(tabs).toHaveLength(1)
    expect(tabs[0]).not.toBe('session-only')
    // generateSessionId() shape
    expect(tabs[0]).toMatch(/^session-\d+-[a-z0-9]+$/)

    // Final localStorage state: only the new id, never an empty array.
    const newId = tabs[0]
    expect(JSON.parse(localStorage.getItem(OPEN_TABS_STORAGE_KEY) || '[]')).toEqual([newId])
  })

  it('Test 14: openTabIds restored from localStorage on mount', async () => {
    localStorage.setItem(
      OPEN_TABS_STORAGE_KEY,
      JSON.stringify(['session-restore-1', 'session-restore-2']),
    )

    renderWithTabConsumer()

    await waitFor(() => {
      expect(readOpenTabIds()).toEqual(['session-restore-1', 'session-restore-2'])
    })
  })
})
