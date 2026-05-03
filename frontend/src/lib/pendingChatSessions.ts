// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

export const PENDING_CHAT_SESSION_IDS_STORAGE_KEY = 'pikar_pending_chat_session_ids';

function readPendingChatSessionIds(): string[] {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(PENDING_CHAT_SESSION_IDS_STORAGE_KEY);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter((value): value is string => typeof value === 'string' && value.length > 0);
  } catch {
    return [];
  }
}

function writePendingChatSessionIds(sessionIds: string[]): void {
  if (typeof window === 'undefined') {
    return;
  }

  const deduped = Array.from(new Set(sessionIds.filter((value) => value.length > 0)));

  try {
    if (deduped.length === 0) {
      window.localStorage.removeItem(PENDING_CHAT_SESSION_IDS_STORAGE_KEY);
      return;
    }

    window.localStorage.setItem(PENDING_CHAT_SESSION_IDS_STORAGE_KEY, JSON.stringify(deduped));
  } catch {
    // Best-effort persistence only.
  }
}

export function isPendingChatSession(sessionId: string): boolean {
  if (!sessionId) {
    return false;
  }

  return readPendingChatSessionIds().includes(sessionId);
}

export function markPendingChatSession(sessionId: string): void {
  if (!sessionId) {
    return;
  }

  const next = readPendingChatSessionIds();
  if (next.includes(sessionId)) {
    return;
  }

  next.push(sessionId);
  writePendingChatSessionIds(next);
}

export function clearPendingChatSession(sessionId: string): void {
  if (!sessionId) {
    return;
  }

  writePendingChatSessionIds(
    readPendingChatSessionIds().filter((value) => value !== sessionId),
  );
}

export function clearAllPendingChatSessions(): void {
  writePendingChatSessionIds([]);
}
