'use client'

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useSessionMap, type ChatSession } from './SessionMapContext'
import { useSessionControl } from './SessionControlContext'

export type { ChatSession }

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
 */
export function useChatSession() {
  const map = useSessionMap()
  const ctrl = useSessionControl()
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
    updateSessionTitle: ctrl.updateSessionTitle,
    updateSessionPreview: ctrl.updateSessionPreview,
    addSessionOptimistic: ctrl.addSessionOptimistic,
    goToHistoryPage: () => {
      window.location.href = '/dashboard/history'
    },
  }
}
