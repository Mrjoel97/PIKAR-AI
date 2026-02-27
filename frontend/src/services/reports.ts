import { fetchWithAuth } from './api';

export type ReportStatus = 'Completed' | 'Processing' | 'Failed';
export type ReportSourceType = 'workflow' | 'initiative' | 'scheduled' | 'manual';

export interface Report {
  id: string;
  title: string;
  type?: string;
  category: string;
  status: ReportStatus;
  date?: string;
  summary: string | null;
  content: string | null;
  source_type: ReportSourceType;
  source_id?: string | null;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ListReportsParams {
  category?: string;
  source_type?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export async function listReports(params: ListReportsParams = {}): Promise<Report[]> {
  const sp = new URLSearchParams();
  if (params.category) sp.set('category', params.category);
  if (params.source_type) sp.set('source_type', params.source_type);
  if (params.search) sp.set('search', params.search);
  if (params.limit != null) sp.set('limit', String(params.limit));
  if (params.offset != null) sp.set('offset', String(params.offset));
  const response = await fetchWithAuth(`/reports?${sp.toString()}`);
  if (!response.ok) throw new Error('Failed to list reports');
  const data = await response.json();
  return (Array.isArray(data) ? data : []).map(normalizeReport);
}

export async function getReportCategories(): Promise<string[]> {
  const response = await fetchWithAuth('/reports/categories');
  if (!response.ok) throw new Error('Failed to get report categories');
  const data = await response.json();
  return data?.categories ?? [];
}

export async function getReport(reportId: string): Promise<Report> {
  const response = await fetchWithAuth(`/reports/${reportId}`);
  if (!response.ok) throw new Error('Failed to get report');
  const data = await response.json();
  return normalizeReport(data);
}

function normalizeReport(r: Record<string, unknown>): Report {
  const created = (r.created_at as string) || '';
  return {
    id: (r.id as string) ?? '',
    title: (r.title as string) ?? 'Untitled',
    type: r.category as string,
    category: (r.category as string) ?? 'general',
    status: (r.status as ReportStatus) ?? 'Completed',
    date: formatReportDate(created),
    summary: (r.summary as string) ?? null,
    content: (r.content as string) ?? null,
    source_type: (r.source_type as ReportSourceType) ?? 'manual',
    source_id: r.source_id as string | null | undefined,
    metadata: r.metadata as Record<string, unknown> | undefined,
    created_at: created,
    updated_at: (r.updated_at as string) ?? created,
  };
}

function formatReportDate(iso: string): string {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffMins < 60) return diffMins <= 1 ? 'Just now' : `${diffMins} minutes ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
  return d.toLocaleDateString();
}
