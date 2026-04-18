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

import React from 'react';
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
vi.mock('@/contexts/SessionControlContext', () => ({
  useSessionControl: vi.fn(() => ({
    visibleSessionId: null,
    selectChat: vi.fn(),
  })),
}));

// ---------------------------------------------------------------------------
// Imports that use the mocked modules
// ---------------------------------------------------------------------------
import { SessionMapProvider, useSessionMap } from '@/contexts/SessionMapContext';
import { useAgentChat } from '@/hooks/useAgentChat';

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
  const { isLoadingHistory } = useAgentChat({ initialSessionId: sessionId });
  const { addActiveSession, updateSessionState } = useSessionMap();

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
    mockGetUser.mockResolvedValue({ data: { user: { id: 'user-abc' } } });
    mockGetAuthenticatedUser.mockResolvedValue({ id: 'user-abc' });
    mockLoadSessionHistory.mockResolvedValue([]);
  });

  afterEach(() => {
    vi.useRealTimers();
    handle = null;
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
      await vi.advanceTimersByTimeAsync(12500);
      await Promise.resolve();
    });

    expect(getByTestId('status').textContent).toBe('ready');
    expect(mockLoadSessionHistory).toHaveBeenCalledTimes(1);
  });
});
