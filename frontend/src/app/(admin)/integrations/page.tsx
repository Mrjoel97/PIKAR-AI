'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useCallback, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { ProviderCard } from '@/components/admin/integrations/ProviderCard';
import { ConfigureModal } from '@/components/admin/integrations/ConfigureModal';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** All supported integration providers in display order */
const ALL_PROVIDERS = ['sentry', 'posthog', 'github', 'stripe'] as const;

/** Shape returned by GET /admin/integrations */
interface IntegrationStatus {
  provider: string;
  is_active: boolean;
  health_status: string;
  key_last4: string | null;
  base_url: string | null;
  config: Record<string, string>;
  updated_at: string;
}

/** Default placeholder entry for a provider not yet configured */
function defaultEntry(provider: string): IntegrationStatus {
  return {
    provider,
    is_active: false,
    health_status: 'unknown',
    key_last4: null,
    base_url: null,
    config: {},
    updated_at: new Date().toISOString(),
  };
}

/**
 * IntegrationsPage renders /admin/integrations with:
 * - A 2-column grid of all 4 provider cards (Sentry, PostHog, GitHub, Stripe)
 * - A configure modal for entering API keys and provider-specific settings
 * - A test-connection banner showing pass/fail results
 */
export default function IntegrationsPage() {
  const supabase = createClient();

  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  /** Which provider's configure modal is open; null = closed */
  const [configuringProvider, setConfiguringProvider] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  /** Which provider is currently being tested; null = none */
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    provider: string;
    healthy: boolean;
    error?: string;
  } | null>(null);

  // ─── fetchIntegrations ───────────────────────────────────────────────────────

  const fetchIntegrations = useCallback(async () => {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setFetchError('Not authenticated');
        setIsLoading(false);
        return;
      }

      const res = await fetch(`${API_URL}/admin/integrations`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (!res.ok) {
        setFetchError(`Failed to load integrations (${res.status})`);
        setIsLoading(false);
        return;
      }

      const apiData = (await res.json()) as IntegrationStatus[];

      // Always show all 4 providers — merge API response with full provider list
      const byProvider = new Map(apiData.map((d) => [d.provider, d]));
      const merged = ALL_PROVIDERS.map(
        (p) => byProvider.get(p) ?? defaultEntry(p),
      );

      setIntegrations(merged);
      setFetchError(null);
    } catch {
      setFetchError('Failed to load integrations. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [supabase]);

  useEffect(() => {
    fetchIntegrations();
  }, [fetchIntegrations]);

  // ─── handleSave ─────────────────────────────────────────────────────────────

  const handleSave = useCallback(
    async (data: {
      api_key?: string;
      base_url?: string;
      config: Record<string, string>;
    }) => {
      if (!configuringProvider) return;
      setIsSaving(true);
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();

        if (!session) {
          window.alert('Not authenticated');
          return;
        }

        const res = await fetch(
          `${API_URL}/admin/integrations/${configuringProvider}`,
          {
            method: 'PUT',
            headers: {
              Authorization: `Bearer ${session.access_token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
          },
        );

        if (!res.ok) {
          const body = await res.text();
          window.alert(`Save failed (${res.status}): ${body}`);
          return;
        }

        setConfiguringProvider(null);
        await fetchIntegrations();
      } catch {
        window.alert('Save failed. Check that the backend is running.');
      } finally {
        setIsSaving(false);
      }
    },
    [configuringProvider, supabase, fetchIntegrations],
  );

  // ─── handleTestConnection ────────────────────────────────────────────────────

  const handleTestConnection = useCallback(
    async (provider: string) => {
      setTestingProvider(provider);
      setTestResult(null);
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();

        if (!session) return;

        const res = await fetch(
          `${API_URL}/admin/integrations/${provider}/test`,
          {
            method: 'POST',
            headers: { Authorization: `Bearer ${session.access_token}` },
          },
        );

        const body = (await res.json()) as { healthy: boolean; error?: string };
        setTestResult({ provider, healthy: body.healthy, error: body.error });

        // Refetch so health_status badge updates
        await fetchIntegrations();

        // Auto-dismiss test result after 5 seconds
        setTimeout(() => {
          setTestResult(null);
        }, 5000);
      } catch {
        setTestResult({ provider, healthy: false, error: 'Request failed' });
        setTimeout(() => setTestResult(null), 5000);
      } finally {
        setTestingProvider(null);
      }
    },
    [supabase, fetchIntegrations],
  );

  // ─── Derived state ───────────────────────────────────────────────────────────

  const currentIntegration = integrations.find(
    (i) => i.provider === configuringProvider,
  );

  // ─── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Integrations</h1>
        <p className="text-gray-400 mt-1">
          Connect external services to monitor and manage your platform
        </p>
      </div>

      {/* Test result banner (auto-dismisses after 5s) */}
      {testResult && (
        <div
          className={`mb-6 flex items-center gap-3 px-4 py-3 rounded-lg text-sm ${
            testResult.healthy
              ? 'bg-green-500/10 text-green-400 border border-green-500/20'
              : 'bg-red-500/10 text-red-400 border border-red-500/20'
          }`}
          role="status"
        >
          <span className={`font-medium ${testResult.healthy ? '' : ''}`}>
            {testResult.healthy
              ? `${testResult.provider.charAt(0).toUpperCase() + testResult.provider.slice(1)}: Connection successful`
              : `${testResult.provider.charAt(0).toUpperCase() + testResult.provider.slice(1)}: Connection failed${testResult.error ? ` — ${testResult.error}` : ''}`}
          </span>
          <button
            type="button"
            onClick={() => setTestResult(null)}
            className="ml-auto text-current opacity-60 hover:opacity-100"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="bg-gray-800 border border-gray-700 rounded-lg h-40 animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Error state */}
      {fetchError && !isLoading && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <p className="text-red-400 text-sm">{fetchError}</p>
          <button
            type="button"
            onClick={() => {
              setIsLoading(true);
              fetchIntegrations();
            }}
            className="px-4 py-2 bg-gray-800 text-gray-200 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Provider grid */}
      {!isLoading && !fetchError && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {integrations.map((integration) => (
            <ProviderCard
              key={integration.provider}
              provider={integration.provider}
              isActive={integration.is_active}
              healthStatus={integration.health_status}
              keyLast4={integration.key_last4}
              updatedAt={integration.updated_at}
              onConfigure={() => setConfiguringProvider(integration.provider)}
              onTestConnection={() => handleTestConnection(integration.provider)}
              isTesting={testingProvider === integration.provider}
            />
          ))}
        </div>
      )}

      {/* Configure modal */}
      <ConfigureModal
        provider={configuringProvider}
        currentConfig={currentIntegration?.config ?? {}}
        onClose={() => setConfiguringProvider(null)}
        onSave={handleSave}
        isSaving={isSaving}
      />
    </div>
  );
}
