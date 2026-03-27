// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { fetchWithAuth } from './api';

export interface ComplianceAudit {
  id: string;
  user_id: string;
  title: string;
  scope: string | null;
  auditor: string | null;
  scheduled_date: string | null;
  completed_date: string | null;
  status: string; // scheduled, in_progress, completed, cancelled
  findings: unknown; // JSONB
  created_at: string;
  updated_at: string;
}

export interface ComplianceRisk {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  severity: string; // low, medium, high, critical
  category: string | null;
  mitigation_plan: string | null;
  owner: string | null;
  status: string; // open, mitigating, resolved, accepted
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export async function getAudits(): Promise<ComplianceAudit[]> {
  const response = await fetchWithAuth('/compliance/audits');
  return response.json();
}

export async function getRisks(): Promise<ComplianceRisk[]> {
  const response = await fetchWithAuth('/compliance/risks');
  return response.json();
}

export function computeComplianceScore(audits: ComplianceAudit[]): number {
  if (audits.length === 0) return 0;
  const completed = audits.filter((a) => a.status === 'completed').length;
  return Math.round((completed / audits.length) * 100);
}
