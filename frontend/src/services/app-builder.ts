/**
 * App Builder service — authenticated fetch wrappers for project CRUD
 * and GSD stage transitions.
 */
import { createClient } from '@/lib/supabase/client';
import type {
  AppProject,
  GsdStage,
  DesignBrief,
  SitemapPage,
  BuildPlanPhase,
  ResearchEvent,
  ScreenVariant,
  GenerationEvent,
} from '@/types/app-builder';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getAuthHeaders(): Promise<Record<string, string>> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error('Not authenticated');
  return { Authorization: `Bearer ${session.access_token}` };
}

/**
 * Create a new app project and its linked build session.
 * Calls POST /app-builder/projects.
 */
export async function createProject(payload: {
  title: string;
  creative_brief: Record<string, string>;
}): Promise<AppProject> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/app-builder/projects`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/**
 * Fetch a single app project by ID.
 * Calls GET /app-builder/projects/{id}.
 */
export async function getProject(projectId: string): Promise<AppProject> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/app-builder/projects/${projectId}`, {
    headers,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/**
 * Advance the GSD stage on the project and its build session.
 * Calls PATCH /app-builder/projects/{id}/stage.
 */
export async function advanceStage(
  projectId: string,
  stage: GsdStage,
): Promise<AppProject> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/app-builder/projects/${projectId}/stage`,
    {
      method: 'PATCH',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ stage }),
    },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/**
 * Start design research via SSE stream.
 * Uses fetch ReadableStream (not EventSource) to support Authorization header.
 */
export async function startResearch(
  projectId: string,
  onEvent: (event: ResearchEvent) => void,
): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/app-builder/projects/${projectId}/research`, {
    method: 'POST',
    headers,
  });
  if (!res.ok || !res.body) throw new Error('Research failed to start');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try { onEvent(JSON.parse(line.slice(6))); } catch { /* skip malformed */ }
      }
    }
  }
}

/**
 * Stream screen variant generation via SSE.
 * Calls POST /app-builder/projects/{id}/generate-screen.
 */
export async function generateScreen(
  projectId: string,
  screenName: string,
  pageSlug: string,
  onEvent: (event: GenerationEvent) => void,
): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/app-builder/projects/${projectId}/generate-screen`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ screen_name: screenName, page_slug: pageSlug }),
  });
  if (!res.ok || !res.body) throw new Error('Screen generation failed to start');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try { onEvent(JSON.parse(line.slice(6))); } catch { /* skip malformed */ }
      }
    }
  }
}

/**
 * Stream device-specific variant generation via SSE.
 * Calls POST /app-builder/projects/{id}/screens/{screenId}/generate-device-variant.
 */
export async function generateDeviceVariant(
  projectId: string,
  screenId: string,
  deviceType: 'MOBILE' | 'TABLET',
  promptUsed: string,
  onEvent: (event: GenerationEvent) => void,
): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/app-builder/projects/${projectId}/screens/${screenId}/generate-device-variant`,
    {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_type: deviceType, prompt_used: promptUsed }),
    },
  );
  if (!res.ok || !res.body) throw new Error('Device variant generation failed to start');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try { onEvent(JSON.parse(line.slice(6))); } catch { /* skip malformed */ }
      }
    }
  }
}

/**
 * Fetch all variants for a screen ordered by variant_index.
 * Calls GET /app-builder/projects/{id}/screens/{screenId}/variants.
 */
export async function getScreenVariants(
  projectId: string,
  screenId: string,
): Promise<ScreenVariant[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/app-builder/projects/${projectId}/screens/${screenId}/variants`,
    { headers },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/**
 * Mark a variant as selected (deselects all others on the screen).
 * Calls PATCH /app-builder/projects/{id}/screens/{screenId}/variants/{variantId}/select.
 */
export async function selectVariant(
  projectId: string,
  screenId: string,
  variantId: string,
): Promise<{ success: boolean; selected_variant_id: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/app-builder/projects/${projectId}/screens/${screenId}/variants/${variantId}/select`,
    { method: 'PATCH', headers },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/**
 * Approve the design brief — locks design system, generates build plan, advances to building.
 */
export async function approveBrief(
  projectId: string,
  payload: { design_system: Record<string, unknown>; sitemap: SitemapPage[]; raw_markdown: string },
): Promise<{ success: boolean; build_plan: BuildPlanPhase[]; stage: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/app-builder/projects/${projectId}/approve-brief`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
