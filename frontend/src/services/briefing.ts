// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { getAccessToken } from '@/lib/supabase/client';

export interface TriageItem {
  id: string;
  gmail_message_id: string;
  sender: string;
  sender_name: string | null;
  subject: string | null;
  snippet: string | null;
  received_at: string | null;
  priority: 'urgent' | 'important' | 'normal' | 'low';
  action_type: 'needs_reply' | 'needs_review' | 'fyi' | 'auto_handle' | 'spam';
  category: string | null;
  confidence: number;
  classification_reasoning: string | null;
  draft_reply: string | null;
  draft_confidence: number | null;
  status: 'pending' | 'approved' | 'sent' | 'dismissed' | 'auto_handled';
  auto_action_taken: string | null;
  briefing_date: string;
}

export interface BriefingSections {
  urgent: TriageItem[];
  needs_reply: TriageItem[];
  auto_handled: TriageItem[];
  fyi: TriageItem[];
}

export interface BriefingResponse {
  sections: BriefingSections;
  counts: Record<string, number>;
  total: number;
}

export interface BriefingPreferences {
  briefing_time: string;
  timezone: string;
  email_digest_enabled: boolean;
  email_digest_frequency: 'daily' | 'weekdays' | 'off';
  auto_act_enabled: boolean;
  auto_act_daily_cap: number;
  auto_act_categories: string[];
  vip_senders: string[];
  ignored_senders: string[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getAuthHeaders(): Promise<Record<string, string>> {
  const accessToken = await getAccessToken();
  if (!accessToken) throw new Error('Not authenticated');
  return { Authorization: `Bearer ${accessToken}` };
}

export async function getBriefingToday(): Promise<BriefingResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/today`, { headers });
  if (!res.ok) throw new Error(`Failed to fetch briefing: ${res.statusText}`);
  return res.json();
}

export async function refreshBriefing(): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/refresh`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to refresh: ${res.statusText}`);
}

export async function approveTriageItem(itemId: string, draftText?: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/items/${itemId}/approve`, {
    method: 'PATCH',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ draft_text: draftText }),
  });
  if (!res.ok) throw new Error(`Failed to approve: ${res.statusText}`);
}

export async function dismissTriageItem(itemId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/items/${itemId}/dismiss`, {
    method: 'PATCH',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to dismiss: ${res.statusText}`);
}

export async function undoTriageAction(itemId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/items/${itemId}/undo`, {
    method: 'PATCH',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to undo: ${res.statusText}`);
}

export async function getBriefingPreferences(): Promise<BriefingPreferences> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/preferences`, { headers });
  if (!res.ok) throw new Error(`Failed to fetch preferences: ${res.statusText}`);
  return res.json();
}

export async function updateBriefingPreferences(prefs: Partial<BriefingPreferences>): Promise<BriefingPreferences> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/preferences`, {
    method: 'PUT',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify(prefs),
  });
  if (!res.ok) throw new Error(`Failed to update preferences: ${res.statusText}`);
  return res.json();
}

export interface DigestStatus {
  digest_enabled: boolean;
  frequency: string;
  briefing_time: string;
  timezone: string;
  last_updated: string | null;
  will_send_today: boolean;
}

export async function getDigestStatus(): Promise<DigestStatus> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/briefing/digest-status`, { headers });
  if (!res.ok) throw new Error(`Failed to fetch digest status: ${res.statusText}`);
  return res.json();
}
