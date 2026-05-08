'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useEffect } from 'react'
import { useSessionMap, type ChatSession } from './SessionMapContext'
import {
  useSessionControl,
  TAB_CAP_FREE,
  TAB_CAP_PAID,
} from './SessionControlContext'
import { useSubscription } from './SubscriptionContext'

export type { ChatSession }

/** Subset of SessionControlContextValue exposed to dashboard chat consumers. */
export interface ChatSessionContextValue {
  currentSessionId: string | null;
  setCurrentSessionId: (id: string | null) => void;
  sessionRestored: boolean;
  sessions: ChatSession[];
  isLoadingSessions: boolean;
  createNewChat: () => string;
  selectChat: (sessionId: string) => void;
  deleteChat: (sessionId: string) => Promise<void>;
  clearAllChats: () => Promise<void>;
  refreshSessions: () => Promise<void>;
  refreshError: Error | null;
  updateSessionTitle: (sessionId: string, title: string) => Promise<void>;
  updateSessionPreview: (sessionId: string, preview: string) => Promise<void>;
  addSessionOptimistic: (session: ChatSession) => void;
  goToHistoryPage: () => void;
  openTabIds: string[];
  tabCap: number;
  openTab: (sessionId: string) => void;
  closeTab: (sessionId: string) => void;
}

// Re-export the old context shape for backward compatibility.
// Consumers should use useChatSession() instead of accessing the context directly.
export const ChatSessionContext = null

/**
 * No-op wrapper — the real providers (SessionMapProvider + SessionControlProvider)
 * are mounted in layout.tsx. This component exists so that any file still importing
 * `ChatSessionProvider` from this module will continue to compile and render.
 */
export function ChatSessionProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}

/**
 * Backward-compatible hook that combines the new SessionMapContext and
 * SessionControlContext into the shape that existing consumers expect.
 *
 * Tier-derived tab cap (FEATURE-MULTI-SESSION-TABS):
 * `SessionControlProvider` lives at the ROOT layout (`app/layout.tsx`),
 * above `SubscriptionProvider` (mounted at `app/dashboard/layout.tsx`).
 * The provider therefore CANNOT call `useSubscription()` itself — that
 * would throw "must be used within a <SubscriptionProvider>". This hook,
 * however, is invoked only inside the dashboard tree where
 * `SubscriptionProvider` IS mounted, so we read the tier here and push
 * the tier-derived cap (5 free / 8 paid) into the provider via
 * `ctrl.setTabCap` from a `useEffect`. The provider's default of
 * `TAB_CAP_FREE = 5` is the safe floor for any non-dashboard consumer.
 */
export function useChatSession() {
  const map = useSessionMap()
  const ctrl = useSessionControl()
  const { tier } = useSubscription()
  const desiredCap = tier === 'free' ? TAB_CAP_FREE : TAB_CAP_PAID

  // Push the tier-derived cap into provider state so openTab's cap-check
  // (which reads `tabCap` from `SessionControlProvider`) sees the right
  // value for paid-tier users. Runs only in the dashboard tree.
  useEffect(() => {
    ctrl.setTabCap(desiredCap)
  }, [desiredCap, ctrl])

  return {
    currentSessionId: ctrl.visibleSessionId,
    setCurrentSessionId: ctrl.setVisibleSessionId,
    sessionRestored: ctrl.sessionRestored,
    sessions: map.sessions,
    isLoadingSessions: map.isLoadingSessions,
    createNewChat: ctrl.createNewChat,
    selectChat: ctrl.selectChat,
    deleteChat: ctrl.deleteChat,
    clearAllChats: ctrl.clearAllChats,
    refreshSessions: ctrl.refreshSessions,
    refreshError: ctrl.refreshError,
    updateSessionTitle: ctrl.updateSessionTitle,
    updateSessionPreview: ctrl.updateSessionPreview,
    addSessionOptimistic: ctrl.addSessionOptimistic,
    goToHistoryPage: () => {
      window.location.href = '/dashboard/history'
    },
    // FEATURE-MULTI-SESSION-TABS
    openTabIds: ctrl.openTabIds,
    tabCap: desiredCap,
    openTab: ctrl.openTab,
    closeTab: ctrl.closeTab,
  }
}
