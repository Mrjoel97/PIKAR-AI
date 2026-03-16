import { fetchWithAuth, fetchWithAuthRaw } from './api';

export type InitiativeChecklistStatus = 'pending' | 'in_progress' | 'completed' | 'blocked' | 'skipped';
export type InitiativePhase = 'ideation' | 'validation' | 'prototype' | 'build' | 'scale';

export interface InitiativeChecklistItem {
  id: string;
  initiative_id: string;
  user_id: string;
  phase: InitiativePhase;
  title: string;
  description?: string | null;
  status: InitiativeChecklistStatus;
  owner_user_id?: string | null;
  owner_label?: string | null;
  due_at?: string | null;
  evidence?: unknown[];
  sort_order: number;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface InitiativeChecklistEvent {
  id: string;
  item_id?: string | null;
  initiative_id: string;
  user_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  actor_user_id?: string | null;
  created_at: string;
}

export interface InitiativeChecklistItemsResponse {
  items: InitiativeChecklistItem[];
  count: number;
}

export interface InitiativeChecklistEventsResponse {
  events: InitiativeChecklistEvent[];
  count: number;
}

export interface InitiativeOperationalRecord {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  progress: number;
  phase: InitiativePhase;
  phase_progress: Record<string, number>;
  created_at: string;
  template_id?: string | null;
  metadata: Record<string, unknown>;
  workflow_execution_id?: string | null;
  journey_outcomes_prompt?: string | null;
  goal?: string;
  success_criteria?: string[];
  owner_agents?: string[];
  primary_workflow?: string | null;
  deliverables?: unknown[];
  evidence?: unknown[];
  blockers?: unknown[];
  next_actions?: unknown[];
  current_phase?: string;
  verification_status?: string;
  trust_summary?: Record<string, unknown>;
}

export interface UpdateInitiativeRequest {
  status?: string;
  progress?: number;
  title?: string;
  description?: string;
  phase?: InitiativePhase;
  phase_progress?: Record<string, number>;
  metadata?: Record<string, unknown>;
  workflow_execution_id?: string | null;
}

export interface StartInitiativeJourneyWorkflowResponse {
  success: boolean;
  workflow_execution_id?: string;
  template_name?: string;
  message?: string;
  requirements_satisfied?: boolean;
  missing_inputs?: string[];
  blockers?: unknown[];
  trust_summary?: Record<string, unknown>;
  verification_status?: string | null;
}

export class InitiativeApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.name = 'InitiativeApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function readJson<T>(response: Response): Promise<T | null> {
  return response.json().catch(() => null);
}

function getDetailMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }
  if (detail && typeof detail === 'object') {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === 'string' && message.trim()) {
      return message;
    }
  }
  return fallback;
}

export async function listInitiativeChecklistItems(
  initiativeId: string,
  params?: {
    phase?: InitiativePhase;
    status?: InitiativeChecklistStatus;
    owner_label?: string;
    due_before?: string;
    due_after?: string;
    limit?: number;
    offset?: number;
    sort_by?: 'sort_order' | 'created_at' | 'updated_at' | 'due_at' | 'status' | 'title';
    sort_order?: 'asc' | 'desc';
  },
): Promise<InitiativeChecklistItem[]> {
  const result = await listInitiativeChecklistItemsPage(initiativeId, params);
  return result.items;
}

export async function listInitiativeChecklistItemsPage(
  initiativeId: string,
  params?: {
    phase?: InitiativePhase;
    status?: InitiativeChecklistStatus;
    owner_label?: string;
    due_before?: string;
    due_after?: string;
    limit?: number;
    offset?: number;
    sort_by?: 'sort_order' | 'created_at' | 'updated_at' | 'due_at' | 'status' | 'title';
    sort_order?: 'asc' | 'desc';
  },
): Promise<InitiativeChecklistItemsResponse> {
  const sp = new URLSearchParams();
  if (params?.phase) sp.set('phase', params.phase);
  if (params?.status) sp.set('status', params.status);
  if (params?.owner_label) sp.set('owner_label', params.owner_label);
  if (params?.due_before) sp.set('due_before', params.due_before);
  if (params?.due_after) sp.set('due_after', params.due_after);
  if (typeof params?.limit === 'number') sp.set('limit', String(params.limit));
  if (typeof params?.offset === 'number') sp.set('offset', String(params.offset));
  if (params?.sort_by) sp.set('sort_by', params.sort_by);
  if (params?.sort_order) sp.set('sort_order', params.sort_order);
  const qs = sp.toString();
  const response = await fetchWithAuth(`/initiatives/${initiativeId}/checklist${qs ? `?${qs}` : ''}`);
  const data = await readJson<{ items?: InitiativeChecklistItem[]; count?: number }>(response);
  return {
    items: data?.items ?? [],
    count: data?.count ?? 0,
  };
}

export async function createInitiativeChecklistItem(
  initiativeId: string,
  body: {
    title: string;
    phase: InitiativePhase;
    description?: string;
    status?: InitiativeChecklistStatus;
    owner_label?: string;
    due_at?: string;
    evidence?: unknown[];
    sort_order?: number;
    metadata?: Record<string, unknown>;
  },
): Promise<InitiativeChecklistItem> {
  const response = await fetchWithAuth(`/initiatives/${initiativeId}/checklist`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
  const data = await readJson<{ item: InitiativeChecklistItem }>(response);
  if (!data?.item) {
    throw new Error('Failed to create checklist item');
  }
  return data.item;
}

export async function updateInitiativeChecklistItem(
  initiativeId: string,
  itemId: string,
  body: Partial<{
    title: string;
    phase: InitiativePhase;
    description: string;
    status: InitiativeChecklistStatus;
    owner_label: string;
    due_at: string | null;
    evidence: unknown[];
    sort_order: number;
    metadata: Record<string, unknown>;
  }>,
): Promise<InitiativeChecklistItem> {
  const response = await fetchWithAuth(`/initiatives/${initiativeId}/checklist/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
  const data = await readJson<{ item: InitiativeChecklistItem }>(response);
  if (!data?.item) {
    throw new Error('Failed to update checklist item');
  }
  return data.item;
}

export async function deleteInitiativeChecklistItem(
  initiativeId: string,
  itemId: string,
): Promise<void> {
  await fetchWithAuth(`/initiatives/${initiativeId}/checklist/${itemId}`, {
    method: 'DELETE',
  });
}

export async function listInitiativeChecklistEvents(
  initiativeId: string,
  params?: {
    limit?: number;
    offset?: number;
    event_type?: string;
    item_id?: string;
    actor_user_id?: string;
  },
): Promise<InitiativeChecklistEvent[]> {
  const result = await listInitiativeChecklistEventsPage(initiativeId, params);
  return result.events;
}

export async function listInitiativeChecklistEventsPage(
  initiativeId: string,
  params?: {
    limit?: number;
    offset?: number;
    event_type?: string;
    item_id?: string;
    actor_user_id?: string;
  },
): Promise<InitiativeChecklistEventsResponse> {
  const sp = new URLSearchParams();
  if (typeof params?.limit === 'number') sp.set('limit', String(params.limit));
  if (typeof params?.offset === 'number') sp.set('offset', String(params.offset));
  if (params?.event_type) sp.set('event_type', params.event_type);
  if (params?.item_id) sp.set('item_id', params.item_id);
  if (params?.actor_user_id) sp.set('actor_user_id', params.actor_user_id);
  const qs = sp.toString();
  const response = await fetchWithAuth(`/initiatives/${initiativeId}/checklist/events${qs ? `?${qs}` : ''}`);
  const data = await readJson<{ events?: InitiativeChecklistEvent[]; count?: number }>(response);
  return {
    events: data?.events ?? [],
    count: data?.count ?? 0,
  };
}

export async function createInitiativeFromBraindump(braindumpId: string): Promise<any> {
  const response = await fetchWithAuth('/initiatives/from-braindump', {
    method: 'POST',
    body: JSON.stringify({ braindump_id: braindumpId }),
  });
  return readJson(response);
}

export async function listInitiatives(params?: {
  status?: string;
  phase?: InitiativePhase;
  priority?: string;
  limit?: number;
}): Promise<InitiativeOperationalRecord[]> {
  const sp = new URLSearchParams();
  if (params?.status) sp.set('status', params.status);
  if (params?.phase) sp.set('phase', params.phase);
  if (params?.priority) sp.set('priority', params.priority);
  if (typeof params?.limit === 'number') sp.set('limit', String(params.limit));
  const qs = sp.toString();
  const response = await fetchWithAuth(`/initiatives${qs ? `?${qs}` : ''}`);
  const data = await readJson<{ initiatives?: InitiativeOperationalRecord[] }>(response);
  return data?.initiatives ?? [];
}

export async function getInitiative(initiativeId: string): Promise<InitiativeOperationalRecord> {
  const response = await fetchWithAuth(`/initiatives/${initiativeId}`);
  const data = await readJson<{ initiative?: InitiativeOperationalRecord }>(response);
  if (!data?.initiative) {
    throw new Error('Failed to get initiative');
  }
  return data.initiative;
}

export async function updateInitiative(
  initiativeId: string,
  body: UpdateInitiativeRequest,
): Promise<InitiativeOperationalRecord> {
  const response = await fetchWithAuth(`/initiatives/${initiativeId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
  const data = await readJson<{ initiative?: InitiativeOperationalRecord }>(response);
  if (!data?.initiative) {
    throw new Error('Failed to update initiative');
  }
  return data.initiative;
}

export async function deleteInitiative(initiativeId: string): Promise<boolean> {
  await fetchWithAuth(`/initiatives/${initiativeId}`, {
    method: 'DELETE',
  });
  return true;
}

export async function startInitiativeJourneyWorkflow(
  initiativeId: string,
): Promise<StartInitiativeJourneyWorkflowResponse> {
  const response = await fetchWithAuthRaw(`/initiatives/${initiativeId}/start-journey-workflow`, {
    method: 'POST',
  });
  const data = await readJson<StartInitiativeJourneyWorkflowResponse & { detail?: unknown }>(response);
  if (!response.ok) {
    const detail = data?.detail ?? null;
    throw new InitiativeApiError(
      getDetailMessage(detail, 'Failed to start journey workflow'),
      response.status,
      detail,
    );
  }
  return data ?? { success: false };
}
