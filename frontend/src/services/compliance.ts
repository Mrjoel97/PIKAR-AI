import { createClient } from '@/lib/supabase/client';

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
  const supabase = createClient();
  const { data, error } = await supabase
    .from('compliance_audits')
    .select('*')
    .order('scheduled_date', { ascending: false })
    .limit(50);
  if (error) throw error;
  return (data ?? []) as ComplianceAudit[];
}

export async function getRisks(): Promise<ComplianceRisk[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from('compliance_risks')
    .select('*')
    .neq('status', 'resolved')
    .order('created_at', { ascending: false })
    .limit(50);
  if (error) throw error;
  return (data ?? []) as ComplianceRisk[];
}

export function computeComplianceScore(audits: ComplianceAudit[]): number {
  if (audits.length === 0) return 0;
  const completed = audits.filter((a) => a.status === 'completed').length;
  return Math.round((completed / audits.length) * 100);
}
