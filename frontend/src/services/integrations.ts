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

/**
 * Disconnect Google Workspace via the dedicated configuration endpoint so the
 * backend revoke (Phase 102, WORKSPACE-05) runs before deleting the local row.
 *
 * The generic `/integrations/{provider}` DELETE path bypasses the revoke step
 * and only removes the credential row, leaving the refresh token live at
 * Google. Google Workspace MUST go through `/configuration/google-workspace`
 * (handled by GoogleWorkspaceAuthService.disconnect) to call
 * https://oauth2.googleapis.com/revoke before delete.
 *
 * Uses a plain `fetch` (not `fetchWithAuth`) because the request goes through
 * the same-origin Next.js API proxy, which forwards the user's session cookie.
 */
export async function disconnectGoogleWorkspace(): Promise<void> {
  const response = await fetch('/api/configuration/google-workspace', {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(
      `Failed to disconnect Google Workspace (status ${response.status})`,
    );
  }
}
