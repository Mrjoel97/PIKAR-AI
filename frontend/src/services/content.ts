// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { fetchWithAuth } from './api';

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
  const response = await fetchWithAuth('/content/bundles');
  return response.json();
}

export async function getContentDeliverables(bundleIds: string[]): Promise<ContentDeliverable[]> {
  if (bundleIds.length === 0) return [];
  const response = await fetchWithAuth(`/content/bundles/deliverables?bundle_ids=${bundleIds.join(',')}`);
  return response.json();
}

export async function getCampaigns(): Promise<Campaign[]> {
  const response = await fetchWithAuth('/content/campaigns');
  return response.json();
}
