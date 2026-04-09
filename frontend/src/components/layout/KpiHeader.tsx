'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { RefreshCw } from 'lucide-react';
import { useKpis, type KpiItem } from '@/hooks/useKpis';

// ---------------------------------------------------------------------------
// KPI card skeleton for loading state
// ---------------------------------------------------------------------------

function KpiCardSkeleton() {
  return (
    <div className="rounded-2xl border border-slate-100/80 bg-white p-3 shadow-[0_2px_12px_-4px_rgba(15,23,42,0.08)] animate-pulse">
      <div className="h-2.5 w-16 bg-slate-200 rounded-full mb-2" />
      <div className="h-5 w-20 bg-slate-200 rounded-full" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Individual KPI card
// ---------------------------------------------------------------------------

interface KpiCardProps {
  kpi: KpiItem;
  isZero: boolean;
}

function KpiCard({ kpi, isZero }: KpiCardProps) {
  return (
    <div className="rounded-2xl border border-slate-100/80 bg-white p-3 shadow-[0_2px_12px_-4px_rgba(15,23,42,0.08)] transition-shadow hover:shadow-[0_4px_16px_-4px_rgba(15,23,42,0.12)]">
      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-400 truncate">
        {kpi.label}
      </p>
      <p className="mt-1 text-lg font-semibold text-slate-900 truncate leading-tight">
        {kpi.value}
      </p>
      {isZero && kpi.subtitle && (
        <p className="mt-0.5 text-xs text-slate-400 leading-snug line-clamp-2">
          {kpi.subtitle}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// KpiHeader — row of 4 KPI cards with refresh button
// ---------------------------------------------------------------------------

/**
 * Renders a compact horizontal row of 4 persona-specific KPI cards.
 * Placed in PremiumShell between the top bar and page content.
 */
export function KpiHeader() {
  const { kpis, isLoading, error, refresh } = useKpis();

  // Determine if a KPI value represents an empty/zero state
  function isZeroValue(value: string): boolean {
    return (
      value === '$0' ||
      value === '0' ||
      value === '0%' ||
      value === '+0%' ||
      value === '0 hrs'
    );
  }

  return (
    <div className="mb-4 flex items-start gap-3">
      {/* KPI grid — 2 cols on mobile, 4 on large screens */}
      <div className="flex-1 grid grid-cols-2 lg:grid-cols-4 gap-3">
        {isLoading ? (
          <>
            <KpiCardSkeleton />
            <KpiCardSkeleton />
            <KpiCardSkeleton />
            <KpiCardSkeleton />
          </>
        ) : error ? (
          <>
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="rounded-2xl border border-red-100 bg-red-50/50 p-3 shadow-sm"
              >
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-red-400 truncate">
                  Error
                </p>
                <p className="mt-1 text-lg font-semibold text-slate-400">---</p>
              </div>
            ))}
          </>
        ) : (
          kpis.slice(0, 4).map((kpi) => (
            <KpiCard
              key={kpi.label}
              kpi={kpi}
              isZero={isZeroValue(kpi.value)}
            />
          ))
        )}
      </div>

      {/* Refresh button */}
      <button
        onClick={refresh}
        disabled={isLoading}
        aria-label="Refresh KPIs"
        className="mt-0.5 shrink-0 inline-flex items-center justify-center h-8 w-8 rounded-xl border border-slate-100/80 bg-white text-slate-400 shadow-[0_2px_8px_-4px_rgba(15,23,42,0.1)] hover:text-teal-600 hover:border-teal-200 hover:shadow-[0_2px_12px_-4px_rgba(20,184,166,0.2)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <RefreshCw
          size={14}
          className={isLoading ? 'animate-spin' : ''}
        />
      </button>
    </div>
  );
}

export default KpiHeader;
