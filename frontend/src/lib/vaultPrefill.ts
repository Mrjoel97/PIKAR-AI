// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Hand-off layer between the Vault page and the workspace chat composer.
 *
 * When the user picks vault assets and clicks an action chip, we mint a
 * fresh session id, write the templated prompt under a session-scoped
 * sessionStorage key, and navigate to the workspace. The chat composer
 * reads (and clears) the key on mount so the message appears in the
 * input ready to edit and send.
 */

import { markFreshClientSession } from '@/lib/freshClientSessions';

export const PREFILL_STORAGE_PREFIX = 'pikar_vault_prefill_';

/**
 * Mints a session id in the same shape used by SessionControlContext.
 * Marks it fresh so the history-restore effect skips it.
 */
export function mintPrefillSessionId(): string {
  const id = `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  markFreshClientSession(id);
  return id;
}

export function storeVaultPrefill(sessionId: string, prompt: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(`${PREFILL_STORAGE_PREFIX}${sessionId}`, prompt);
  } catch {
    // sessionStorage unavailable — nothing else we can do.
  }
}

/**
 * Reads and CLEARS the prefill in one call. Returns null if not present.
 * Single-use is intentional — re-entering the workspace must not refill.
 */
export function consumeVaultPrefill(sessionId: string): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const key = `${PREFILL_STORAGE_PREFIX}${sessionId}`;
    const value = window.sessionStorage.getItem(key);
    if (value !== null) {
      window.sessionStorage.removeItem(key);
    }
    return value;
  } catch {
    return null;
  }
}
