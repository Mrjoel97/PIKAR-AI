'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useCallback, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { KpiCards } from '@/components/admin/analytics/KpiCards';
import { ActivityChart } from '@/components/admin/analytics/ActivityChart';
import { AgentEffectivenessChart } from '@/components/admin/analytics/AgentEffectivenessChart';
import { FeatureUsageChart } from '@/components/admin/analytics/FeatureUsageChart';
import { ConfigStatusCard } from '@/components/admin/analytics/ConfigStatusCard';

/** Full response from GET /admin/analytics/summary */
interface AnalyticsSummaryResponse {
  usage_trends: Array<{
    stat_date: string;
    dau: number;
    mau: number;
    messages: number;
    workflows: number;
  }>;
  agent_effectiveness: Array<{
    agent_name: string;
    success_rate: number;
    avg_duration_ms: number;
    total_calls: number;
  }>;
  feature_usage: {
    by_tool: Array<{ tool_name: string; call_count: number }>;
    by_category: Array<{ category: string; event_count: number }>;
  };
  config_status: {
    permission_counts: { auto: number; confirm: number; blocked: number };
    last_config_change: string | null;
  };
  days: number;
  data_source: 'aggregated' | 'no_data';
}

/** Auto-refresh interval: 60 seconds */
const REFRESH_INTERVAL_MS = 60_000;

/**
 * AnalyticsPage renders the /admin/analytics dashboard with:
 * - KPI cards (DAU, MAU, messages, workflows)
 * - Dual-line activity trend chart (DAU/MAU over 30 days)
 * - Horizontal bar chart for agent success rates
 * - Feature usage breakdown by category + top tools table
 * - Config status card with permission tier counts
 * - 60-second auto-refresh polling
 */
export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const supabase = createClient();
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchAnalytics = useCallback(async () => {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setFetchError('Not authenticated');
        setIsLoading(false);
        return;
      }

      const res = await fetch(`${API_URL}/admin/analytics/summary?days=30`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (!res.ok) {
        setFetchError(`Failed to load analytics data (${res.status})`);
        setIsLoading(false);
        return;
      }

      const json = (await res.json()) as AnalyticsSummaryResponse;
      setData(json);
      setFetchError(null);
    } catch {
      setFetchError('Failed to load analytics data. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [supabase, API_URL]);

  // Initial fetch + 60-second polling
  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchAnalytics]);

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">Usage Analytics</h1>
        <button
          type="button"
          onClick={() => {
            setIsLoading(true);
            fetchAnalytics();
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-600 transition-colors"
          aria-label="Refresh analytics data"
        >
          Refresh
        </button>
      </div>

      {/* Loading skeleton */}
      {isLoading && !data && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="bg-gray-800 rounded-lg border border-gray-700 p-4 h-20 animate-pulse"
              />
            ))}
          </div>
          <div className="bg-gray-800 rounded-lg border border-gray-700 h-64 animate-pulse" />
          <div className="bg-gray-800 rounded-lg border border-gray-700 h-64 animate-pulse" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-gray-800 rounded-lg border border-gray-700 h-64 animate-pulse" />
            <div className="bg-gray-800 rounded-lg border border-gray-700 h-64 animate-pulse" />
          </div>
        </div>
      )}

      {/* Error state */}
      {fetchError && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <p className="text-red-400 text-sm">{fetchError}</p>
          <button
            type="button"
            onClick={() => {
              setIsLoading(true);
              fetchAnalytics();
            }}
            className="px-4 py-2 bg-gray-800 text-gray-200 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Dashboard content */}
      {data && !fetchError && (
        <div className="space-y-6">
          {/* Empty data state */}
          {data.data_source === 'no_data' && (
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 text-center text-gray-400 text-sm">
              Analytics data is being computed for the first time. Data will appear after the next
              scheduled aggregation.
            </div>
          )}

          {/* Section 1: KPI Cards */}
          <KpiCards usageTrends={data.usage_trends} />

          {/* Section 2: Activity Chart (DAU/MAU dual-line) */}
          <ActivityChart usageTrends={data.usage_trends} />

          {/* Section 3: Agent Effectiveness horizontal bars */}
          <AgentEffectivenessChart agentEffectiveness={data.agent_effectiveness} />

          {/* Section 4: Feature Usage + Config Status (two-column) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FeatureUsageChart featureUsage={data.feature_usage} />
            <ConfigStatusCard configStatus={data.config_status} />
          </div>
        </div>
      )}
    </div>
  );
}
