// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { fetchWithAuth } from './api';

export interface SupportTicket {
  id: string;
  user_id: string;
  subject: string;
  description: string;
  customer_email: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  status: 'new' | 'open' | 'in_progress' | 'waiting' | 'resolved' | 'closed';
  assigned_to: string | null;
  resolution: string | null;
  created_at: string;
  updated_at: string;
}

export async function listTickets(params?: {
  status?: string;
  priority?: string;
  limit?: number;
  offset?: number;
}): Promise<SupportTicket[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set('status', params.status);
  if (params?.priority) qs.set('priority', params.priority);
  if (params?.limit) qs.set('limit', String(params.limit));
  if (params?.offset) qs.set('offset', String(params.offset));
  const query = qs.toString();
  const response = await fetchWithAuth(`/support/tickets${query ? `?${query}` : ''}`);
  return response.json();
}

export async function createTicket(data: {
  subject: string;
  description: string;
  customer_email: string;
  priority?: 'low' | 'normal' | 'high' | 'urgent';
}): Promise<SupportTicket> {
  const response = await fetchWithAuth('/support/tickets', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return response.json();
}

export async function updateTicket(
  ticketId: string,
  data: {
    status?: string;
    priority?: string;
    assigned_to?: string;
    resolution?: string;
  }
): Promise<SupportTicket> {
  const response = await fetchWithAuth(`/support/tickets/${ticketId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
  return response.json();
}

export async function deleteTicket(ticketId: string): Promise<void> {
  await fetchWithAuth(`/support/tickets/${ticketId}`, {
    method: 'DELETE',
  });
}
