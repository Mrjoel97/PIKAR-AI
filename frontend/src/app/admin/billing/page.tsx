'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useCallback, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { BillingKpiCards } from '@/components/admin/billing/BillingKpiCards';
import { PlanDistributionChart } from '@/components/admin/billing/PlanDistributionChart';

/** Full response from GET /admin/billing/summary */
interface BillingSummaryResponse {
  mrr: number;
  arr: number;
  churn_rate: number;
  active_subscriptions: number;
  plan_distribution: Array<{ tier: string; count: number }>;
  churn_pending: number;
  billing_issues: number;
  data_source: 'live' | 'db_only' | 'no_data';
  days: number;
}

/** Auto-refresh interval: 60 seconds */
const REFRESH_INTERVAL_MS = 60_000;

/**
 * BillingPage renders the /admin/billing dashboard with:
 * - KPI cards (MRR, ARR, churn rate, active subscriptions)
 * - Plan distribution pie chart (tier breakdown)
 * - Data-source context banners (Stripe live / DB only / no data)
 * - 60-second auto-refresh polling
 */
export default function BillingPage() {
  const [data, setData] = useState<BillingSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const supabase = createClient();
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchBilling = useCallback(async () => {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setFetchError('Not authenticated');
        setIsLoading(false);
        return;
      }

      const res = await fetch(`${API_URL}/admin/billing/summary`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (!res.ok) {
        setFetchError(`Failed to load billing data (${res.status})`);
        setIsLoading(false);
        return;
      }

      const json = (await res.json()) as BillingSummaryResponse;
      setData(json);
      setFetchError(null);
    } catch {
      setFetchError('Failed to load billing data. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [supabase, API_URL]);

  // Initial fetch + 60-second polling
  useEffect(() => {
    fetchBilling();
    const interval = setInterval(fetchBilling, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchBilling]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Billing</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Revenue metrics and subscription distribution
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setIsLoading(true);
            fetchBilling();
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-600 transition-colors"
          aria-label="Refresh billing data"
        >
          Refresh
        </button>
      </div>

      {/* Loading skeleton */}
      {isLoading && !data && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="bg-gray-800 rounded-lg border border-gray-700 p-4 h-20 animate-pulse"
              />
            ))}
          </div>
          <div className="bg-gray-800 rounded-lg border border-gray-700 h-80 animate-pulse" />
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
              fetchBilling();
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
          {/* Section 1: KPI Cards (handles no_data internally) */}
          <BillingKpiCards
            mrr={data.mrr}
            arr={data.arr}
            churnRate={data.churn_rate}
            activeSubscriptions={data.active_subscriptions}
            dataSource={data.data_source}
          />

          {/* Section 2: Plan Distribution Chart (skip when no data) */}
          {data.data_source !== 'no_data' && (
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 shadow-sm">
              <h2 className="text-base font-semibold text-gray-200 mb-4">Plan Distribution</h2>
              <PlanDistributionChart data={data.plan_distribution} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
