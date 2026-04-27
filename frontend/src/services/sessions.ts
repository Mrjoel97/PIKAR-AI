// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { getAccessToken } from '@/lib/supabase/client';

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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getAuthHeaders(): Promise<Record<string, string>> {
  const accessToken = await getAccessToken();
  if (!accessToken) throw new Error('Not authenticated');
  return { Authorization: `Bearer ${accessToken}` };
}

/**
 * Fetch the authenticated user's chat sessions, most recent first.
 *
 * Returns sessions across every device — useful for restoring chats whose
 * ids are not in this device's localStorage (incognito, cleared cache,
 * sign-in from a new device, etc.).
 */
export async function listUserSessions(limit = 50): Promise<SessionListResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/sessions?limit=${encodeURIComponent(limit)}`, {
    headers,
    cache: 'no-store',
  });
  if (!res.ok) {
    throw new Error(`Failed to load sessions: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
