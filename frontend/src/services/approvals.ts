import { fetchPublicApi } from './api';

export interface ApprovalRequest {
  id: string;
  action_type: string;
  payload: Record<string, unknown>;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
  expires_at: string;
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
