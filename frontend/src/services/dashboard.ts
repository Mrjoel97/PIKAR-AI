import { fetchWithAuth } from './api';

export interface DashboardListItem {
  id: string;
  title: string;
  status?: string;
  category?: string;
  phase?: string;
  progress?: number;
  summary?: string;
  created_at?: string;
  updated_at?: string;
  completed_at?: string;
  workflow_execution_id?: string | null;
}

export interface DashboardKPI {
  label: string;
  value: string;
  tone: string;
}

export interface DashboardSummary {
  persona: string;
  label: string;
  summary: string;
  headline: string;
  subheadline: string;
  brief: {
    title: string;
    body: string;
  };
  kpis: DashboardKPI[];
  recommended_action: {
    title: string;
    description: string;
    href: string;
  };
  collections: {
    initiatives: DashboardListItem[];
    workflows: DashboardListItem[];
    completed_workflows: DashboardListItem[];
    tasks: DashboardListItem[];
    approvals: DashboardListItem[];
    brain_dumps: DashboardListItem[];
    content_queue: DashboardListItem[];
    reports: DashboardListItem[];
    departments: DashboardListItem[];
    audits: DashboardListItem[];
    risks: DashboardListItem[];
    execution_audit: DashboardListItem[];
    template_audit: DashboardListItem[];
  };
  signals: {
    active_workflows: number;
    active_initiatives: number;
    open_tasks: number;
    pending_approvals: number;
    recent_reports: number;
    active_departments: number;
    scheduled_audits: number;
    open_risks: number;
    recent_execution_audit: number;
  };
  finance: {
    currency: string;
    revenue: number;
    cash_position: number;
    monthly_burn: number;
    runway_months: number | null;
  };
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const response = await fetchWithAuth('/briefing/dashboard-summary');
  if (!response.ok) {
    throw new Error('Failed to load dashboard summary');
  }
  return response.json();
}
