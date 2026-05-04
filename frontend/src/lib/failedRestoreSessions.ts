// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// localStorage-backed marker for sessions whose history-restore has timed
// out or otherwise failed. Stored as a `{ [sessionId]: epochMillis }` map
// so each entry has its own age and we can lazily evict expired markers
// without an explicit cleanup pass.
//
// Why localStorage and not in-memory?
//   The in-memory variant only protects within a single page load. The
//   most common user-visible symptom of a stuck session is reload-loop:
//   user reloads the dashboard, every load attempts the same Supabase
//   query, every load times out 25s. Persisting the marker lets the
//   second-and-later loads short-circuit immediately.
//
// Why a TTL and not permanent?
//   A 25-second timeout can be caused by transient Supabase slowness,
//   slow network, or genuine schema problems. We don't know which it is
//   from the failure alone, so a permanent block would lock users out of
//   sessions whose backend has fully recovered. 5 minutes is long enough
//   that a thrashing Supabase isn't repeatedly hammered, short enough
//   that users aren't stranded if they intentionally come back.

const STORAGE_KEY = 'pikar_failed_restore_sessions';
const TTL_MS = 5 * 60 * 1000;

type Marker = { [sessionId: string]: number };

function read(): Marker {
    if (typeof window === 'undefined') return {};
    try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (!raw) return {};
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
            return parsed as Marker;
        }
        return {};
    } catch {
        return {};
    }
}

function write(value: Marker): void {
    if (typeof window === 'undefined') return;
    try {
        if (Object.keys(value).length === 0) {
            window.localStorage.removeItem(STORAGE_KEY);
            return;
        }
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    } catch {
        // localStorage may be unavailable (private mode, quota exceeded).
        // Best-effort persistence — fall back to no-op.
    }
}

// Drop entries older than the TTL. Returns the cleaned-up map and writes
// it back to storage. Used internally by every read/check.
function purgeExpired(now: number = Date.now()): Marker {
    const map = read();
    const cleaned: Marker = {};
    let mutated = false;
    for (const [id, ts] of Object.entries(map)) {
        if (typeof ts === 'number' && now - ts < TTL_MS) {
            cleaned[id] = ts;
        } else {
            mutated = true;
        }
    }
    if (mutated) write(cleaned);
    return cleaned;
}

export function markFailedRestore(sessionId: string): void {
    if (!sessionId) return;
    const map = purgeExpired();
    map[sessionId] = Date.now();
    write(map);
}

export function isRecentlyFailedRestore(
    sessionId: string | null | undefined,
): boolean {
    if (!sessionId) return false;
    const map = purgeExpired();
    return Boolean(map[sessionId]);
}

export function clearFailedRestore(sessionId: string): void {
    if (!sessionId) return;
    const map = purgeExpired();
    if (sessionId in map) {
        delete map[sessionId];
        write(map);
    }
}

// Test-only — wipes the persistent + in-process state.
export function __resetFailedRestoreForTests(): void {
    if (typeof window !== 'undefined') {
        try {
            window.localStorage.removeItem(STORAGE_KEY);
        } catch {
            // ignore
        }
    }
}

export const __FAILED_RESTORE_STORAGE_KEY = STORAGE_KEY;
export const __FAILED_RESTORE_TTL_MS = TTL_MS;
