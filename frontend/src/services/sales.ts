import { createClient } from '@/lib/supabase/client';

export interface Contact {
  id: string;
  user_id: string;
  name: string;
  email: string | null;
  phone: string | null;
  company: string | null;
  lifecycle_stage: string; // lead, qualified, opportunity, customer, churned, inactive
  source: string | null;
  estimated_value: number | null;
  tags: string[] | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContactActivity {
  id: string;
  contact_id: string;
  activity_type: string;
  description: string | null;
  metadata: unknown;
  created_at: string;
}

export interface ConnectedAccount {
  id: string;
  user_id: string;
  platform: string; // linkedin, twitter, facebook, instagram, youtube, tiktok
  account_name: string | null;
  account_id: string | null;
  status: string;
  connected_at: string | null;
  last_synced_at: string | null;
}

export interface Campaign {
  id: string;
  name: string;
  type: string | null;
  target_audience: string | null;
  status: string;
  schedule: unknown;
  metrics: {
    views?: number;
    clicks?: number;
    conversions?: number;
    engagement?: number;
    likes?: number;
    comments?: number;
    shares?: number;
    impressions?: number;
    reach?: number;
    ctr?: number;
  } | null;
  created_at: string;
}

export interface PageAnalytic {
  id: string;
  page_url: string | null;
  platform: string | null;
  views: number;
  clicks: number | null;
  conversions: number | null;
  engagement_rate: number | null;
  created_at: string;
}

export interface PipelineStats {
  totalValue: number;
  activeLeads: number;
  customers: number;
  conversionRate: number;
  avgDealSize: number;
  byStage: Record<string, { count: number; value: number }>;
}

export async function getContacts(stageFilter?: string): Promise<Contact[]> {
  const supabase = createClient();
  let query = supabase.from('contacts').select('*').order('updated_at', { ascending: false });
  if (stageFilter && stageFilter !== 'all') {
    query = query.eq('lifecycle_stage', stageFilter);
  }
  const { data, error } = await query.limit(200);
  if (error) throw error;
  return (data ?? []) as Contact[];
}

export async function getContactActivities(limit = 10): Promise<ContactActivity[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from('contact_activities')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit);
  if (error) throw error;
  return (data ?? []) as ContactActivity[];
}

export function computePipelineStats(contacts: Contact[]): PipelineStats {
  const byStage: Record<string, { count: number; value: number }> = {};
  let totalValue = 0;
  let customers = 0;

  for (const c of contacts) {
    const stage = c.lifecycle_stage || 'lead';
    if (!byStage[stage]) byStage[stage] = { count: 0, value: 0 };
    byStage[stage].count++;
    const val = c.estimated_value ?? 0;
    byStage[stage].value += val;
    totalValue += val;
    if (stage === 'customer') customers++;
  }

  const leads =
    (byStage['lead']?.count ?? 0) +
    (byStage['qualified']?.count ?? 0) +
    (byStage['opportunity']?.count ?? 0);
  const conversionRate = contacts.length > 0 ? (customers / contacts.length) * 100 : 0;
  const avgDealSize = customers > 0 ? (byStage['customer']?.value ?? 0) / customers : 0;

  return { totalValue, activeLeads: leads, customers, conversionRate, avgDealSize, byStage };
}

export async function getConnectedAccounts(): Promise<ConnectedAccount[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from('connected_accounts')
    .select('*')
    .order('connected_at', { ascending: false });
  if (error) throw error;
  return (data ?? []) as ConnectedAccount[];
}

export async function getCampaignMetrics(): Promise<Campaign[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from('campaigns')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(50);
  if (error) throw error;
  return (data ?? []) as Campaign[];
}

export async function getPageAnalytics(): Promise<PageAnalytic[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from('page_analytics')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(50);
  if (error) throw error;
  return (data ?? []) as PageAnalytic[];
}
