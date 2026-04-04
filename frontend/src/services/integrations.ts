// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { fetchWithAuth } from './api';

// ============================================================================
// Types
// ============================================================================

export interface IntegrationProvider {
  key: string;
  name: string;
  auth_type: 'oauth2' | 'api_key';
  category: 'crm_sales' | 'finance_commerce' | 'productivity' | 'communication' | 'analytics';
  icon_url: string;
  scopes: string[];
}

export interface IntegrationStatus {
  provider: string;
  name: string;
  category: string;
  connected: boolean;
  account_name: string | null;
  last_sync_at: string | null;
  error_count: number;
  last_error: string | null;
}

// ============================================================================
// API Client
// ============================================================================

/**
 * Fetch all available integration providers from the registry.
 * GET /integrations/providers
 */
export async function fetchProviders(): Promise<IntegrationProvider[]> {
  const response = await fetchWithAuth('/integrations/providers');
  return response.json();
}

/**
 * Fetch per-provider connection status for the current user.
 * GET /integrations/status
 */
export async function fetchIntegrationStatus(): Promise<IntegrationStatus[]> {
  const response = await fetchWithAuth('/integrations/status');
  return response.json();
}

/**
 * Disconnect (remove credentials for) a provider.
 * DELETE /integrations/{provider}
 */
export async function disconnectProvider(
  provider: string,
): Promise<{ disconnected: boolean; provider: string }> {
  const response = await fetchWithAuth(`/integrations/${provider}`, {
    method: 'DELETE',
  });
  return response.json();
}
