import { fetchWithAuth } from './api';

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
  if (!response.ok) throw new Error('Failed to list checklist items');
  const data = await response.json();
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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to create checklist item' }));
    throw new Error(error?.detail || 'Failed to create checklist item');
  }
  const data = await response.json();
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
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to update checklist item' }));
    throw new Error(error?.detail || 'Failed to update checklist item');
  }
  const data = await response.json();
  return data.item;
}

export async function deleteInitiativeChecklistItem(
  initiativeId: string,
  itemId: string,
): Promise<void> {
  const response = await fetchWithAuth(`/initiatives/${initiativeId}/checklist/${itemId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete checklist item' }));
    throw new Error(error?.detail || 'Failed to delete checklist item');
  }
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
  if (!response.ok) throw new Error('Failed to list checklist events');
  const data = await response.json();
  return {
    events: data?.events ?? [],
    count: data?.count ?? 0,
  };
}

export async function createInitiativeFromBraindump(braindumpId: string): Promise<any> {
  const response = await fetchWithAuth(`/initiatives/from-braindump`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ braindump_id: braindumpId }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to create initiative from braindump' }));
    throw new Error(error?.detail || 'Failed to create initiative from braindump');
  }
  const data = await response.json();
  return data;
}
