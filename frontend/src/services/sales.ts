// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { fetchWithAuth } from './api';

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
  const params = new URLSearchParams();
  if (stageFilter && stageFilter !== 'all') params.set('stage', stageFilter);
  const qs = params.toString();
  const response = await fetchWithAuth(`/sales/contacts${qs ? `?${qs}` : ''}`);
  return response.json();
}

export async function getContactActivities(limit = 10): Promise<ContactActivity[]> {
  const response = await fetchWithAuth(`/sales/contacts/activities?limit=${limit}`);
  return response.json();
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
  const response = await fetchWithAuth('/sales/connected-accounts');
  return response.json();
}

export async function getCampaignMetrics(): Promise<Campaign[]> {
  const response = await fetchWithAuth('/sales/campaigns');
  return response.json();
}

export async function getPageAnalytics(): Promise<PageAnalytic[]> {
  const response = await fetchWithAuth('/sales/page-analytics');
  return response.json();
}
