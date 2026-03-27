// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { fetchPublicApi, fetchWithAuth } from './api';

export interface ApprovalRequest {
  id: string;
  action_type: string;
  payload: Record<string, unknown>;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
  expires_at: string;
}

export interface ApprovalHistoryItem {
  id: string;
  action_type: string;
  status: 'APPROVED' | 'REJECTED' | 'EXPIRED';
  created_at: string;
  responded_at: string | null;
}

export type ApprovalDecision = 'APPROVED' | 'REJECTED';

export interface ApprovalResponse {
  success: boolean;
  status: string;
  message: string;
}

export async function getApprovalRequest(token: string): Promise<ApprovalRequest> {
  const response = await fetchPublicApi(`/approvals/${encodeURIComponent(token)}`);
  return response.json();
}

export async function submitApprovalDecision(token: string, decision: ApprovalDecision): Promise<ApprovalResponse> {
  const response = await fetchPublicApi(`/approvals/${encodeURIComponent(token)}/decision`, {
    method: 'POST',
    body: JSON.stringify({ token, decision }),
  });
  return response.json();
}

export async function getApprovalHistory(
  status?: 'APPROVED' | 'REJECTED' | 'EXPIRED',
  limit = 50,
  offset = 0,
): Promise<ApprovalHistoryItem[]> {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  params.set('limit', String(limit));
  params.set('offset', String(offset));
  const response = await fetchWithAuth(`/approvals/history?${params.toString()}`);
  return response.json();
}
