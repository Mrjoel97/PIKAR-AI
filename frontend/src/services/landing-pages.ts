// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { createClient } from '@/lib/supabase/client';

export interface LandingPage {
  id: string;
  title: string;
  slug: string;
  published: boolean;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
  submission_count: number;
}

export interface LandingPageDetail extends LandingPage {
  html_content: string;
}

export interface PageListResponse {
  pages: LandingPage[];
  count: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getAuthHeaders(): Promise<Record<string, string>> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error('Not authenticated');
  return { Authorization: `Bearer ${session.access_token}` };
}

export async function listPages(): Promise<PageListResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages`, { headers });
  if (!res.ok) throw new Error(`Failed to list pages: ${res.statusText}`);
  return res.json();
}

export async function getPage(pageId: string): Promise<LandingPageDetail> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/${pageId}`, { headers });
  if (!res.ok) throw new Error(`Failed to get page: ${res.statusText}`);
  return res.json();
}

export async function updatePage(pageId: string, updates: Partial<Pick<LandingPage, 'title' | 'slug' | 'metadata'>> & { html_content?: string }): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/${pageId}`, {
    method: 'PATCH',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error(`Failed to update page: ${res.statusText}`);
}

export async function deletePage(pageId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/${pageId}`, {
    method: 'DELETE',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to delete page: ${res.statusText}`);
}

export async function publishPage(pageId: string): Promise<{ url: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/${pageId}/publish`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to publish: ${res.statusText}`);
  return res.json();
}

export async function unpublishPage(pageId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/${pageId}/unpublish`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to unpublish: ${res.statusText}`);
}

export async function duplicatePage(pageId: string): Promise<{ page_id: string; slug: string; url: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/${pageId}/duplicate`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`Failed to duplicate: ${res.statusText}`);
  return res.json();
}

export async function importPage(title: string, htmlContent: string, source?: string): Promise<{ page_id: string; slug: string; url: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/pages/import`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, html_content: htmlContent, source: source || 'stitch_import' }),
  });
  if (!res.ok) throw new Error(`Failed to import: ${res.statusText}`);
  return res.json();
}
