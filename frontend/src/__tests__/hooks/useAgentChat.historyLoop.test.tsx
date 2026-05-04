// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
/**
 * Regression test: unrelated session-map updates must NOT restart history loading.
 *
 * Root cause: useAgentChat listed the full `activeSessions` Map in the
 * history-loading effect's dependency list. Because `activeSessions` is a new
 * Map instance on every session-map state update (how React's useState works
 * with Maps), ANY update to ANY session — even one completely unrelated to the
 * selected session — cancelled and restarted the history fetch, producing a
 * visible loading loop.
 *
 * Fix: the history effect now reads through `activeSessionsRef.current` (a
 * stable ref kept in sync via a separate effect) rather than depending on the
 * live `activeSessions` map value. This test verifies that `loadSessionHistory`
 * is only called ONCE per session selection even when unrelated sessions receive
 * updates after the initial mount.
 */

import React, { useLayoutEffect, useState } from 'react';
import { render, act, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks — declared before any import that transitively loads the mocked modules
// ---------------------------------------------------------------------------

// Stable Supabase client mock — same object reference every call
const mockGetUser = vi.fn().mockResolvedValue({
  data: { user: { id: 'user-abc' } },
});
const mockGetAuthenticatedUser = vi.fn().mockResolvedValue({ id: 'user-abc' });
vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(() => ({
    auth: { getUser: mockGetUser },
  })),
  getAuthenticatedUser: (...args: unknown[]) => mockGetAuthenticatedUser(...args),
}));

// Session history loader — records invocation count
const mockLoadSessionHistory = vi.fn().mockResolvedValue([]);
vi.mock('@/lib/sessionHistory', () => ({
  loadSessionHistory: (...args: unknown[]) => mockLoadSessionHistory(...args),
}));

// WidgetDisplayService — no-op stubs
vi.mock('@/services/widgetDisplay', () => ({
  WidgetDisplayService: vi.fn(function WidgetDisplayServiceMock() {
    return {
    getSessionWidgets: vi.fn(() => []),
    clearSessionWidgets: vi.fn(),
    saveWidget: vi.fn(),
    updateWidgetState: vi.fn(),
    };
  }),
  dispatchFocusWidget: vi.fn(),
  dispatchWorkspaceActivity: vi.fn(),
  isWorkspaceCanvasWidget: vi.fn((widget) => widget?.type !== 'morning_briefing'),
}));

vi.mock('@/components/chat/SessionToast', () => ({
  showSessionReadyToast: vi.fn(),
}));

// useBackgroundStream — no-op
vi.mock('@/hooks/useBackgroundStream', () => ({
  useBackgroundStream: () => ({
    startStream: vi.fn(),
    stopStream: vi.fn(),
  }),
}));

// useStreamCap — no-op
vi.mock('@/hooks/useStreamCap', () => ({
  useStreamCap: () => ({
    enforceCapBeforeStream: vi.fn(),
  }),
}));

// useSessionControl — stub that returns a minimal stable value.
// We mock this hook rather than the real provider so we don't need to stand up
// the full SessionControlProvider (which itself calls createClient and Supabase).
const mockSelectChat = vi.fn();
const mockSetVisibleSessionId = vi.fn();
const sessionControlState = {
  visibleSessionId: null as string | null,
  sessionRestored: true,
  sessionsLoaded: false,
  selectChat: mockSelectChat,
  setVisibleSessionId: mockSetVisibleSessionId,
};
vi.mock('@/contexts/SessionControlContext', () => ({
  useSessionControl: vi.fn(() => ({
    visibleSessionId: sessionControlState.visibleSessionId,
    sessionRestored: sessionControlState.sessionRestored,
    sessionsLoaded: sessionControlState.sessionsLoaded,
    selectChat: sessionControlState.selectChat,
    setVisibleSessionId: sessionControlState.setVisibleSessionId,
  })),
}));

// ---------------------------------------------------------------------------
// Imports that use the mocked modules
// ---------------------------------------------------------------------------
import { SessionMapProvider, useSessionMap } from '@/contexts/SessionMapContext';
import { useAgentChat } from '@/hooks/useAgentChat';
import { PENDING_CHAT_SESSION_IDS_STORAGE_KEY } from '@/lib/pendingChatSessions';
import {
  markFreshClientSession,
  __resetFreshClientSessionsForTests,
} from '@/lib/freshClientSessions';
import {
  __resetFailedRestoreForTests,
  __FAILED_RESTORE_STORAGE_KEY,
  __FAILED_RESTORE_TTL_MS,
  markFailedRestore,
  isRecentlyFailedRestore,
} from '@/lib/failedRestoreSessions';

// ---------------------------------------------------------------------------
// Test harness
// ---------------------------------------------------------------------------

// Shared mutable handle so tests can poke the hook from outside React
interface HookHandle {
  isLoadingHistory: boolean;
  triggerUnrelatedSessionUpdate: () => void;
}

let handle: HookHandle | null = null;

function TestConsumer({ sessionId }: { sessionId: string }) {
  const { addActiveSession, updateSessionState } = useSessionMap();

  const { isLoadingHistory } = useAgentChat({ initialSessionId: sessionId });

  handle = {
    isLoadingHistory,
    triggerUnrelatedSessionUpdate: () => {
      const otherId = 'unrelated-session-xyz';
      addActiveSession(otherId, { messages: [] });
      updateSessionState(otherId, {
        messages: [{ id: 'msg-1', role: 'agent', text: 'hello from other session' }],
      });
    },
  };

  return <div data-testid="status">{isLoadingHistory ? 'loading' : 'ready'}</div>;
}

function VisibleSessionConsumer() {
  const { addActiveSession, updateSessionState } = useSessionMap();

  const { isLoadingHistory } = useAgentChat();

  handle = {
    isLoadingHistory,
    triggerUnrelatedSessionUpdate: () => {
      const otherId = 'unrelated-session-xyz';
      addActiveSession(otherId, { messages: [] });
      updateSessionState(otherId, {
        messages: [{ id: 'msg-1', role: 'agent', text: 'hello from other session' }],
      });
    },
  };

  return <div data-testid="status">{isLoadingHistory ? 'loading' : 'ready'}</div>;
}

function FreshSessionHarness({ sessionId }: { sessionId: string }) {
  const { addActiveSession } = useSessionMap();
  const [seeded, setSeeded] = useState(false);

  useLayoutEffect(() => {
    addActiveSession(sessionId, { skipHistoryRestore: true, messages: [] });
    setSeeded(true);
  }, [addActiveSession, sessionId]);

  if (!seeded) {
    return <div data-testid="status">ready</div>;
  }

  return <TestConsumer sessionId={sessionId} />;
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return <SessionMapProvider>{children}</SessionMapProvider>;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useAgentChat history-loading loop regression', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    handle = null;
    sessionControlState.visibleSessionId = null;
    sessionControlState.sessionRestored = true;
    // Default to sessionsLoaded=false so existing tests' behavior is
    // unchanged (they predate the stale-session skip and were written
    // assuming no list-based gating).
    sessionControlState.sessionsLoaded = false;
    mockGetUser.mockResolvedValue({ data: { user: { id: 'user-abc' } } });
    mockGetAuthenticatedUser.mockResolvedValue({ id: 'user-abc' });
    mockLoadSessionHistory.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.useRealTimers();
    handle = null;
    localStorage.clear();
    __resetFreshClientSessionsForTests();
    __resetFailedRestoreForTests();
  });

  it('calls loadSessionHistory exactly once even when an unrelated session is updated', async () => {
    render(
      <Wrapper>
        <TestConsumer sessionId="session-target-001" />
      </Wrapper>,
    );

    // Wait for the initial history load to complete
    await waitFor(() => {
      expect(mockLoadSessionHistory).toHaveBeenCalledTimes(1);
    });

    // Simulate an unrelated session receiving messages.
    // Before the fix this caused activeSessions to be a new Map instance,
    // which re-triggered the history effect and restarted the fetch.
    await act(async () => {
      handle?.triggerUnrelatedSessionUpdate();
      // Give React time to flush the state update and any downstream effects
      await new Promise((r) => setTimeout(r, 60));
    });

    // The history loader must still have been called exactly once
    expect(mockLoadSessionHistory).toHaveBeenCalledTimes(1);
  });

  it('does not re-enter isLoadingHistory=true after settling on an empty session', async () => {
    mockLoadSessionHistory.mockResolvedValue([]);

    const { getByTestId } = render(
      <Wrapper>
        <TestConsumer sessionId="session-empty-001" />
      </Wrapper>,
    );

    // Wait for the loading indicator to clear
    await waitFor(() => {
      expect(getByTestId('status').textContent).toBe('ready');
    });

    // Trigger an unrelated session update
    await act(async () => {
      handle?.triggerUnrelatedSessionUpdate();
      await new Promise((r) => setTimeout(r, 60));
    });

    // Must stay "ready" — not flipped back to "loading"
    expect(getByTestId('status').textContent).toBe('ready');
    expect(mockLoadSessionHistory).toHaveBeenCalledTimes(1);
  });

  it('re-loads history when the session ID prop changes', async () => {
    const { rerender } = render(
      <Wrapper>
        <TestConsumer sessionId="session-a" />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(mockLoadSessionHistory).toHaveBeenCalledTimes(1);
    });

    // Switch to a different session
    rerender(
      <Wrapper>
        <TestConsumer sessionId="session-b" />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(mockLoadSessionHistory).toHaveBeenCalledTimes(2);
    });

    expect(mockLoadSessionHistory).toHaveBeenNthCalledWith(1, 'session-a', 'user-abc');
    expect(mockLoadSessionHistory).toHaveBeenNthCalledWith(2, 'session-b', 'user-abc');
  });

  it('falls back to a fresh chat when history restore never settles', async () => {
    vi.useFakeTimers();
    mockLoadSessionHistory.mockImplementation(() => new Promise(() => {}));

    const { getByTestId } = render(
      <Wrapper>
        <TestConsumer sessionId="session-stuck-001" />
      </Wrapper>,
    );

    expect(getByTestId('status').textContent).toBe('loading');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(25500);
      await Promise.resolve();
    });

    expect(getByTestId('status').textContent).toBe('ready');
    expect(mockLoadSessionHistory).toHaveBeenCalledTimes(1);
  });

  it('restores history on reload for a persisted session even when the in-memory sessions array is empty (race-condition regression)', async () => {
    // Reproduces the user-visible "chat history disappears on reload" bug:
    // - localStorage restored a real session id starting with "session-"
    // - The async refreshSessions() that populates the in-memory `sessions`
    //   array hadn't completed when the history-loading effect first ran
    // - The previous code mistook this for a "fresh client session" and
    //   permanently skipped the fetch
    // After the fix, loadSessionHistory is always asked authoritatively
    // and a non-empty result is restored.
    const persistedMessages = [
      { id: 'evt-1', role: 'user' as const, text: 'remember this' },
      { id: 'evt-2', role: 'agent' as const, text: 'noted, I will' },
    ];
    mockLoadSessionHistory.mockResolvedValueOnce(persistedMessages);

    const { getByTestId } = render(
      <Wrapper>
        <TestConsumer sessionId="session-persisted-001" />
      </Wrapper>,
    );

    // Wait for the history fetch to settle and the welcome state to clear
    await waitFor(() => {
      expect(getByTestId('status').textContent).toBe('ready');
    });

    expect(mockLoadSessionHistory).toHaveBeenCalledTimes(1);
    expect(mockLoadSessionHistory).toHaveBeenCalledWith(
      'session-persisted-001',
      'user-abc',
    );
  });

  it('skips history restore for freshly created client-side sessions', async () => {
    const { getByTestId } = render(
      <Wrapper>
        <FreshSessionHarness sessionId="session-fresh-001" />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(getByTestId('status').textContent).toBe('ready');
    });

    expect(mockLoadSessionHistory).not.toHaveBeenCalled();
  });

  it('skips history restore for stale-but-unknown sessions once sessionsLoaded flips to true', async () => {
    // Models the scenario where the user restored a session id from
    // localStorage (previous tab abandoned without sending) — that id is
    // NOT in the user's persisted-sessions list, NOT in pendingChatSessions
    // markers (cleared / never written / cross-browser-data wiped), and
    // NOT in the in-memory fresh-set (different page load minted it).
    // Without the new gate this would hit the 25-second Supabase timeout
    // and silently break the chat. With sessionsLoaded=true and the id
    // missing from the list, we authoritatively short-circuit.
    sessionControlState.sessionsLoaded = true;

    const { getByTestId } = render(
      <Wrapper>
        <TestConsumer sessionId="session-stale-from-prev-tab" />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(getByTestId('status').textContent).toBe('ready');
    });

    expect(mockLoadSessionHistory).not.toHaveBeenCalled();
  });

  it('forgets the persisted session id when restore times out, so the next reload starts fresh', async () => {
    // Models the user's exact reload-loop: stuck session id is the visible
    // (persisted) session, restore times out, and without this fix the
    // user is permanently re-attached to the broken session every reload.
    // After the fix, restoreWelcomeState calls setVisibleSessionId(null)
    // which clears pikar_current_session_id, freeing the user.
    vi.useFakeTimers();
    sessionControlState.visibleSessionId = 'session-stuck-and-current';
    mockLoadSessionHistory.mockImplementation(() => new Promise(() => {}));

    render(
      <Wrapper>
        <VisibleSessionConsumer />
      </Wrapper>,
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(25500);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(mockSetVisibleSessionId).toHaveBeenCalledWith(null);
  });

  it('clears pikar_current_session_id directly even when historySessionId came in via initialSessionId prop', async () => {
    // Edge case: a second useAgentChat instance has the stuck id only via
    // its `initialSessionId` prop while the visible-session React state
    // hasn't yet matched it. The setVisibleSessionId(null) check
    // (`historySessionId === visibleSessionId`) misses, but the direct
    // localStorage write still fires — guarantees the persisted pointer
    // is cleared regardless of React state alignment.
    vi.useFakeTimers();
    localStorage.setItem('pikar_current_session_id', 'session-stuck-via-prop');
    sessionControlState.visibleSessionId = null; // mismatch on purpose
    mockLoadSessionHistory.mockImplementation(() => new Promise(() => {}));

    render(
      <Wrapper>
        <TestConsumer sessionId="session-stuck-via-prop" />
      </Wrapper>,
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(25500);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(localStorage.getItem('pikar_current_session_id')).toBeNull();
  });

  it('skips history restore when the session was recently marked as failed', async () => {
    // Models the user's reload-loop: they land on a stuck session id
    // from `pikar_current_session_id`, restore times out, falls back to
    // welcome — and then on the NEXT page load, the same id should be
    // skipped immediately instead of paying the 25-second timeout again.
    markFailedRestore('session-stuck-from-prev-load');
    expect(isRecentlyFailedRestore('session-stuck-from-prev-load')).toBe(true);

    const { getByTestId } = render(
      <Wrapper>
        <TestConsumer sessionId="session-stuck-from-prev-load" />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(getByTestId('status').textContent).toBe('ready');
    });

    expect(mockLoadSessionHistory).not.toHaveBeenCalled();
  });

  it('expires the failed-restore marker after the TTL window', () => {
    // Confirms the helper doesn't permanently lock a session out — once
    // the TTL elapses, the next attempt is allowed through (Supabase may
    // have recovered).
    markFailedRestore('session-recently-failed');
    expect(isRecentlyFailedRestore('session-recently-failed')).toBe(true);

    // Manually age the marker by rewriting localStorage with a stale ts
    const map = JSON.parse(localStorage.getItem(__FAILED_RESTORE_STORAGE_KEY) || '{}');
    map['session-recently-failed'] = Date.now() - __FAILED_RESTORE_TTL_MS - 1000;
    localStorage.setItem(__FAILED_RESTORE_STORAGE_KEY, JSON.stringify(map));

    expect(isRecentlyFailedRestore('session-recently-failed')).toBe(false);
  });

  it('skips history restore for IDs marked via markFreshClientSession', async () => {
    // Models the scenario reported by the user: workspace mints a session id
    // client-side (matching `session-<epoch>-<rand>`), the restore effect
    // races with `addActiveSession`, and there's no localStorage "pending"
    // marker yet — historically that caused a 25s Supabase timeout.
    // The new in-memory marker, written synchronously at ID-mint time,
    // short-circuits the restore call before it starts.
    markFreshClientSession('session-1777909775656-w63lw3i');

    const { getByTestId } = render(
      <Wrapper>
        <TestConsumer sessionId="session-1777909775656-w63lw3i" />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(getByTestId('status').textContent).toBe('ready');
    });

    expect(mockLoadSessionHistory).not.toHaveBeenCalled();
  });

  it('skips history restore on reload for a pending unsent chat session id', async () => {
    localStorage.setItem(
      PENDING_CHAT_SESSION_IDS_STORAGE_KEY,
      JSON.stringify(['session-pending-reload-001']),
    );

    const { getByTestId } = render(
      <Wrapper>
        <TestConsumer sessionId="session-pending-reload-001" />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(getByTestId('status').textContent).toBe('ready');
    });

    expect(mockLoadSessionHistory).not.toHaveBeenCalled();
  });

  it('restores history for the visible session even when no initialSessionId prop is provided', async () => {
    sessionControlState.visibleSessionId = 'session-visible-restore-001';

    render(
      <Wrapper>
        <VisibleSessionConsumer />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(mockLoadSessionHistory).toHaveBeenCalledTimes(1);
    });

    expect(mockLoadSessionHistory).toHaveBeenCalledWith(
      'session-visible-restore-001',
      'user-abc',
    );
  });
});
