'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { DollarSign, TrendingUp, AlertTriangle, Users } from 'lucide-react';

interface BillingKpiCardsProps {
  mrr: number;
  arr: number;
  churnRate: number;
  activeSubscriptions: number;
  dataSource: 'live' | 'db_only' | 'no_data';
}

/** Format a number as USD currency with no decimal places. */
function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

/** Derive Tailwind color class for churn rate. */
function churnColorClass(rate: number): string {
  const pct = rate * 100;
  if (pct < 5) return 'text-emerald-400';
  if (pct <= 10) return 'text-amber-400';
  return 'text-red-400';
}

/**
 * BillingKpiCards renders four KPI metric cards for the billing dashboard:
 * - MRR (Monthly Recurring Revenue)
 * - ARR (Annual Recurring Revenue)
 * - Churn Rate (color-coded by severity)
 * - Active Subscriptions
 *
 * Shows data-source context banners for db_only and no_data states.
 */
export function BillingKpiCards({
  mrr,
  arr,
  churnRate,
  activeSubscriptions,
  dataSource,
}: BillingKpiCardsProps) {
  if (dataSource === 'no_data') {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 text-center text-gray-400 text-sm">
        No subscription data yet. Connect Stripe on the Integrations page to see billing metrics.
      </div>
    );
  }

  const churnPct = churnRate * 100;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* MRR Card */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <DollarSign className="h-4 w-4 text-gray-500" aria-hidden="true" />
            <span className="text-gray-400 text-sm">Monthly Recurring Revenue</span>
          </div>
          <span className="text-2xl font-bold text-blue-400">{formatCurrency(mrr)}</span>
        </div>

        {/* ARR Card */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-gray-500" aria-hidden="true" />
            <span className="text-gray-400 text-sm">Annual Recurring Revenue</span>
          </div>
          <span className="text-2xl font-bold text-purple-400">{formatCurrency(arr)}</span>
        </div>

        {/* Churn Rate Card */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-gray-500" aria-hidden="true" />
            <span className="text-gray-400 text-sm">Churn Rate</span>
          </div>
          <span className={`text-2xl font-bold ${churnColorClass(churnRate)}`}>
            {churnPct.toFixed(1)}%
          </span>
        </div>

        {/* Active Subscriptions Card */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-gray-500" aria-hidden="true" />
            <span className="text-gray-400 text-sm">Active Subscriptions</span>
          </div>
          <span className="text-2xl font-bold text-emerald-400">
            {activeSubscriptions.toLocaleString()}
          </span>
        </div>
      </div>

      {/* db_only banner */}
      {dataSource === 'db_only' && (
        <div className="flex items-center gap-2 px-3 py-2 bg-amber-900/30 border border-amber-700/50 rounded-lg">
          <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" aria-hidden="true" />
          <p className="text-amber-300 text-xs">
            Stripe not connected — showing DB data only. Connect Stripe on the Integrations page
            for live revenue data.
          </p>
        </div>
      )}
    </div>
  );
}
