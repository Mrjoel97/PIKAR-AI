// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// In-memory tracker for session IDs minted client-side during the CURRENT
// page load. The set lives only for the lifetime of the JS module (cleared
// on hard refresh / new tab), which is exactly the right scope: a session
// that was generated in this tab cannot have history in Supabase yet, so the
// 25-second `loadSessionHistory` round-trip is pure waste — it can only ever
// return zero events (best case) or time out (worst case, what the user
// reports as "history restore failed").
//
// Why not localStorage / sessionStorage?
//   The persisted markers (see `pendingChatSessions.ts`) carry the
//   "this user typed nothing yet, treat as fresh" intent ACROSS reloads,
//   which is a different invariant. We want a strictly in-memory marker so
//   that legitimate persisted sessions (re-opened from the sidebar after
//   a real send) can still load their history on the next visit.
//
// Why not the existing `skipHistoryRestore` flag on session state?
//   That flag is set inside `addActiveSession` calls, and there's a race
//   between (a) the restore effect reading `activeSessionsRef.current` and
//   (b) the add-session effect writing the flag. This module-level Set is
//   written synchronously at ID-mint time, before any React lifecycle has
//   a chance to start, so the restore effect's check is race-free.

const freshSessionIds = new Set<string>();

export function markFreshClientSession(sessionId: string): void {
    if (!sessionId) return;
    freshSessionIds.add(sessionId);
}

export function isFreshClientSession(sessionId: string | null | undefined): boolean {
    if (!sessionId) return false;
    return freshSessionIds.has(sessionId);
}

export function clearFreshClientSession(sessionId: string): void {
    if (!sessionId) return;
    freshSessionIds.delete(sessionId);
}

// Test-only — resets the in-memory set between test cases.
export function __resetFreshClientSessionsForTests(): void {
    freshSessionIds.clear();
}
