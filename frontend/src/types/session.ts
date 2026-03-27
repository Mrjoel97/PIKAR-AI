// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// Import Message type from existing hook
import type { Message } from '@/hooks/useAgentChat'

export type SessionStatus = 'idle' | 'streaming' | 'error' | 'interrupted'

export interface ActiveSessionState {
  sessionId: string
  messages: Message[]
  status: SessionStatus
  abortController: AbortController | null
  hasUnread: boolean
  lastUpdatedAt: number
  scrollTop: number
  rawWidgets: RawWidgetData[]
  pendingActions: PendingSessionAction[]
}

export interface RawWidgetData {
  widget: unknown
  messageIndex: number
}

export interface PendingSessionAction {
  type: 'focus_widget' | 'workspace_activity'
  payload: unknown
}

export interface SessionConfig {
  max_concurrent_streams: number
  memory_eviction_minutes: number
  max_active_sessions_in_memory: number
}

export const DEFAULT_SESSION_CONFIG: SessionConfig = {
  max_concurrent_streams: 4,
  memory_eviction_minutes: 30,
  max_active_sessions_in_memory: 20,
}

export function createEmptyActiveSession(sessionId: string): ActiveSessionState {
  return {
    sessionId,
    messages: [],
    status: 'idle',
    abortController: null,
    hasUnread: false,
    lastUpdatedAt: Date.now(),
    scrollTop: -1,
    rawWidgets: [],
    pendingActions: [],
  }
}
