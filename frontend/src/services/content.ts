import { createClient } from '@/lib/supabase/client';

export interface ContentBundle {
  id: string;
  user_id: string;
  title: string;
  bundle_type: string | null; // image, video, audio, mixed, text
  status: string; // draft, in_progress, review, approved, published, archived
  description: string | null;
  target_date: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContentDeliverable {
  id: string;
  bundle_id: string;
  title: string;
  type: string | null;
  status: string;
  platform: string | null;
  content_url: string | null;
  created_at: string;
}

export interface Campaign {
  id: string;
  name: string;
  type: string | null;
  status: string;
  target_audience: string | null;
  schedule: unknown;
  metrics: unknown;
  created_at: string;
}

export async function getContentBundles(): Promise<ContentBundle[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from('content_bundles')
    .select('*')
    .order('target_date', { ascending: true })
    .limit(100);
  if (error) throw error;
  return (data ?? []) as ContentBundle[];
}

export async function getContentDeliverables(bundleIds: string[]): Promise<ContentDeliverable[]> {
  if (bundleIds.length === 0) return [];
  const supabase = createClient();
  const { data, error } = await supabase
    .from('content_bundle_deliverables')
    .select('*')
    .in('bundle_id', bundleIds);
  if (error) throw error;
  return (data ?? []) as ContentDeliverable[];
}

export async function getCampaigns(): Promise<Campaign[]> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from('campaigns')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(50);
  if (error) throw error;
  return (data ?? []) as Campaign[];
}
