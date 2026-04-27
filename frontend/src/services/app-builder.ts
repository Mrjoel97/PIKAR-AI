// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * App Builder service — authenticated fetch wrappers for project CRUD
 * and GSD stage transitions.
 */
import { getAccessToken } from '@/lib/supabase/client';
import type {
  AppProject,
  AppScreen,
  GsdStage,
  DesignBrief,
  SitemapPage,
  BuildPlanPhase,
  ResearchEvent,
  ScreenVariant,
  GenerationEvent,
  IterationEvent,
  MultiPageEvent,
  ShipEvent,
  ShipTarget,
} from '@/types/app-builder';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getAuthHeaders(): Promise<Record<string, string>> {
  const accessToken = await getAccessToken();
  if (!accessToken) throw new Error('Not authenticated');
  return { Authorization: `Bearer ${accessToken}` };
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
 * Stream screen iteration via SSE.
 * Calls POST /app-builder/projects/{id}/screens/{screenId}/iterate.
 */
export async function iterateScreen(
  projectId: string,
  screenId: string,
  changeDescription: string,
  onEvent: (event: IterationEvent) => void,
): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/app-builder/projects/${projectId}/screens/${screenId}/iterate`,
    {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ change_description: changeDescription }),
    },
  );
  if (!res.ok || !res.body) throw new Error('Screen iteration failed to start');

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
 * Fetch version history for a screen ordered by iteration DESC.
 * Calls GET /app-builder/projects/{id}/screens/{screenId}/history.
 */
export async function getScreenHistory(
  projectId: string,
  screenId: string,
): Promise<ScreenVariant[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/app-builder/projects/${projectId}/screens/${screenId}/history`,
    { headers },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/**
 * Rollback a screen to a previous variant.
 * Calls POST /app-builder/projects/{id}/screens/{screenId}/rollback/{variantId}.
 */
export async function rollbackVariant(
  projectId: string,
  screenId: string,
  variantId: string,
): Promise<{ success: boolean; selected_variant_id: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/app-builder/projects/${projectId}/screens/${screenId}/rollback/${variantId}`,
    { method: 'POST', headers },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/**
 * Approve a screen — marks it as approved without advancing stage.
 * Calls POST /app-builder/projects/{id}/screens/{screenId}/approve.
 */
export async function approveScreen(
  projectId: string,
  screenId: string,
): Promise<{ success: boolean; screen_id: string; approved: boolean }> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/app-builder/projects/${projectId}/screens/${screenId}/approve`,
    { method: 'POST', headers },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/**
 * Stream multi-page build via SSE.
 * Calls POST /app-builder/projects/{id}/build-all.
 */
export async function buildAllPages(
  projectId: string,
  onEvent: (event: MultiPageEvent) => void,
): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/app-builder/projects/${projectId}/build-all`, {
    method: 'POST',
    headers,
  });
  if (!res.ok || !res.body) throw new Error('Multi-page build failed to start');

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
 * Fetch all selected screens for a project (one per page).
 * Calls GET /app-builder/projects/{id}/screens.
 */
export async function listProjectScreens(
  projectId: string,
): Promise<(AppScreen & { html_url: string })[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/app-builder/projects/${projectId}/screens`, { headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/**
 * Persist sitemap changes (reorder or remove pages) to the backend.
 * Calls PATCH /app-builder/projects/{id}/sitemap.
 */
export async function updateSitemap(
  projectId: string,
  sitemap: SitemapPage[],
): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/app-builder/projects/${projectId}/sitemap`, {
    method: 'PATCH',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ sitemap }),
  });
  if (!res.ok) throw new Error(await res.text());
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

/**
 * Stream multi-target ship process via SSE.
 * Calls POST /app-builder/projects/{id}/ship with selected targets.
 * Uses fetch ReadableStream (not EventSource) to support Authorization header + request body.
 */
export async function shipProject(
  projectId: string,
  targets: ShipTarget[],
  onEvent: (event: ShipEvent) => void,
): Promise<void> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/app-builder/projects/${projectId}/ship`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ targets }),
  });
  if (!res.ok || !res.body) throw new Error('Ship process failed to start');

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

// ---------------------------------------------------------------------------
// Autopilot
// ---------------------------------------------------------------------------

export type AutopilotState =
  | 'idle'
  | 'running'
  | 'paused_brief'
  | 'paused_variant'
  | 'paused_screen'
  | 'paused_ship'
  | 'failed'
  | 'done';

export interface AutopilotEvent {
  ts: string;
  kind: 'status' | 'progress' | 'result' | 'error';
  message: string;
  payload?: Record<string, unknown>;
}

export interface AutopilotStatusResponse {
  autopilot_status: AutopilotState;
  stage: string;
  error: string | null;
  events: AutopilotEvent[];
}

export interface ResumeAutopilotBody {
  completed_screen_ids?: string[];
  ship_target?: 'react' | 'pwa' | 'capacitor' | 'video';
}

/** POST /app-builder/projects/{id}/start-autopilot */
export async function startAutopilot(
  projectId: string,
  sessionId: string,
): Promise<AppProject> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/app-builder/projects/${projectId}/start-autopilot`,
    {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/** GET /app-builder/projects/{id}/autopilot-status */
export async function getAutopilotStatus(
  projectId: string,
): Promise<AutopilotStatusResponse> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/app-builder/projects/${projectId}/autopilot-status`,
    { headers },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/** POST /app-builder/projects/{id}/resume-autopilot */
export async function resumeAutopilot(
  projectId: string,
  body: ResumeAutopilotBody = {},
): Promise<AppProject> {
  const headers = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/app-builder/projects/${projectId}/resume-autopilot`,
    {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
