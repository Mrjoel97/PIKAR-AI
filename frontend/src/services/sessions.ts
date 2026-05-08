// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

export interface SessionSummary {
  id: string;
  title: string;
  preview?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionListResponse {
  sessions: SessionSummary[];
  count: number;
}

const RETRY_DELAY_MS = 500;

async function fetchSessions(limit: number): Promise<Response> {
  return fetch(`/api/sessions/list?limit=${encodeURIComponent(limit)}`, {
    cache: 'no-store',
  });
}

/**
 * Fetch the authenticated user's chat sessions, most recent first.
 *
 * Calls the Next.js server route /api/sessions/list which proxies the
 * backend with the cookie-resolved JWT. We retry once on transient
 * failures (network error, 5xx) but never on 4xx — those are real auth
 * or contract problems the caller should see.
 */
export async function listUserSessions(limit = 50): Promise<SessionListResponse> {
  let lastError: unknown = null;

  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const res = await fetchSessions(limit);
      if (res.ok) {
        return (await res.json()) as SessionListResponse;
      }
      // 5xx is transient — retry once. 4xx is not.
      if (res.status >= 500 && attempt === 0) {
        lastError = new Error(`Failed to load sessions: ${res.status} ${res.statusText}`);
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
        continue;
      }
      throw new Error(`Failed to load sessions: ${res.status} ${res.statusText}`);
    } catch (err) {
      lastError = err;
      if (attempt === 0 && err instanceof TypeError) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
        continue;
      }
      throw err;
    }
  }

  throw lastError instanceof Error ? lastError : new Error('listUserSessions failed');
}
