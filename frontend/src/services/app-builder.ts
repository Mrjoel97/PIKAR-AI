/**
 * App Builder service — authenticated fetch wrappers for project CRUD
 * and GSD stage transitions.
 */
import { createClient } from '@/lib/supabase/client';
import type { AppProject, GsdStage } from '@/types/app-builder';

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
