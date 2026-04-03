// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { fetchWithAuth } from './api';

export interface AuditLogEntry {
  id: string;
  user_id: string;
  action_type: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface PortfolioHealth {
  score: number;
  components: {
    initiative_completion: number;
    risk_coverage: number;
    resource_allocation: number;
  };
}

export interface ApprovalChainStep {
  id: string;
  step_order: number;
  role_label: string;
  approver_user_id: string | null;
  status: 'pending' | 'approved' | 'rejected' | 'skipped';
  decided_at: string | null;
  comment: string | null;
}

export interface ApprovalChain {
  id: string;
  user_id: string;
  action_type: string;
  resource_id: string | null;
  resource_label: string | null;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  steps: ApprovalChainStep[];
  created_at: string;
  resolved_at: string | null;
}

export async function getAuditLog(
  limit = 50,
  offset = 0,
  actionType?: string,
): Promise<AuditLogEntry[]> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (actionType) {
    params.set('action_type', actionType);
  }
  const response = await fetchWithAuth(`/governance/audit-log?${params.toString()}`);
  return response.json();
}

export async function getPortfolioHealth(): Promise<PortfolioHealth> {
  const response = await fetchWithAuth('/governance/portfolio-health');
  return response.json();
}

export async function getApprovalChains(): Promise<ApprovalChain[]> {
  const response = await fetchWithAuth('/governance/approval-chains');
  return response.json();
}
