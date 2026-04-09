'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { GatedPage } from '@/components/dashboard/GatedPage';
import {
  Activity,
  AlertTriangle,
  BarChart2,
  CheckCircle,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Minus,
} from 'lucide-react';
import {
  getPortfolioHealth,
  type PortfolioHealth,
} from '@/services/governance';

// ============================================================================
// Helpers
// ============================================================================

function scoreColor(score: number): string {
  if (score >= 70) return 'text-emerald-600';
  if (score >= 40) return 'text-amber-500';
  return 'text-red-500';
}

function scoreBorderColor(score: number): string {
  if (score >= 70) return 'border-emerald-300';
  if (score >= 40) return 'border-amber-300';
  return 'border-red-300';
}

function scoreBg(score: number): string {
  if (score >= 70) return 'bg-emerald-50 dark:bg-emerald-900/20';
  if (score >= 40) return 'bg-amber-50 dark:bg-amber-900/20';
  return 'bg-red-50 dark:bg-red-900/20';
}

function scoreLabel(score: number): string {
  if (score >= 70) return 'Healthy';
  if (score >= 40) return 'Needs Attention';
  return 'At Risk';
}

function barColor(pct: number): string {
  if (pct >= 70) return 'bg-emerald-400';
  if (pct >= 40) return 'bg-amber-400';
  return 'bg-red-400';
}

function formatCurrency(amount: number): string {
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
  if (amount >= 1_000) return `$${(amount / 1_000).toFixed(1)}K`;
  return `$${amount.toFixed(0)}`;
}

// ============================================================================
// Sub-components
// ============================================================================

function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-[28px] bg-slate-100 dark:bg-slate-800 ${className}`}
    />
  );
}

function LoadingSkeleton() {
  return (
    <PremiumShell>
      <div className="mx-auto max-w-7xl space-y-8">
        <SkeletonCard className="h-8 w-64" />
        <SkeletonCard className="h-52" />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} className="h-28" />
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} className="h-40" />
          ))}
        </div>
      </div>
    </PremiumShell>
  );
}

function ComponentBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.max(0, Math.round(value)));
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>{label}</span>
        <span className="font-medium text-slate-700 dark:text-slate-200">{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
        <div
          className={`h-full transition-all ${barColor(pct)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function InitiativeStatCard({
  label,
  count,
  colorClass,
}: {
  label: string;
  count: number;
  colorClass: string;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-2xl border border-slate-100/80 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800/60">
      <span className={`text-2xl font-bold ${colorClass}`}>{count}</span>
      <span className="text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">
        {label}
      </span>
    </div>
  );
}

// ============================================================================
// Main page
// ============================================================================

export default function PortfolioPage() {
  const [health, setHealth] = useState<PortfolioHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPortfolioHealth();
      setHealth(data);
    } catch {
      setError('Failed to load portfolio health data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHealth();
  }, [loadHealth]);

  if (loading) {
    return (
      <DashboardErrorBoundary fallbackTitle="Portfolio Error">
        <LoadingSkeleton />
      </DashboardErrorBoundary>
    );
  }

  const isEmpty =
    !health ||
    (health.components.initiative_breakdown.total === 0 &&
      health.components.workflow_success_rate === 0);

  const revenueDiff =
    health &&
    health.components.revenue_trend.current_month -
      health.components.revenue_trend.prior_month;

  const riskExposure = health
    ? Math.max(0, Math.round(100 - health.components.risk_coverage))
    : 0;

  return (
    <GatedPage featureKey="governance">
      <DashboardErrorBoundary fallbackTitle="Portfolio Error">
        <PremiumShell>
          <motion.div
            className="mx-auto max-w-7xl space-y-8"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <BarChart2 className="h-7 w-7 text-indigo-600" />
                <h1 className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">
                  Portfolio Health
                </h1>
              </div>
              <button
                onClick={loadHealth}
                className="inline-flex items-center gap-2 rounded-2xl bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
                aria-label="Refresh portfolio health"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh
              </button>
            </div>

            {/* Error state */}
            {error && (
              <div className="flex items-center gap-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
                <AlertTriangle className="h-5 w-5 flex-shrink-0" />
                <span>{error}</span>
                <button
                  onClick={loadHealth}
                  className="ml-auto rounded-xl bg-red-100 px-3 py-1.5 font-medium hover:bg-red-200 dark:bg-red-900/40 dark:hover:bg-red-900/60"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Empty state */}
            {!error && isEmpty && (
              <section className="rounded-[28px] border border-slate-100/80 bg-white p-10 text-center shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] dark:border-slate-700 dark:bg-slate-800/60">
                <Activity className="mx-auto mb-4 h-12 w-12 text-slate-300" />
                <h2 className="text-lg font-semibold text-slate-700 dark:text-slate-200">
                  No initiatives yet
                </h2>
                <p className="mt-2 text-sm text-slate-400">
                  Create your first initiative to see portfolio health metrics.
                </p>
                <Link
                  href="/dashboard/workspace"
                  className="mt-6 inline-flex items-center gap-2 rounded-2xl bg-indigo-600 px-6 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700"
                >
                  Go to Workspace
                </Link>
              </section>
            )}

            {/* Main content */}
            {!error && !isEmpty && health && (
              <>
                {/* Portfolio Health Score */}
                <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] dark:border-slate-700 dark:bg-slate-800/60">
                  <h2 className="mb-5 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                    Overall Portfolio Score
                  </h2>
                  <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
                    {/* Score gauge */}
                    <div
                      className={`flex h-28 w-28 flex-shrink-0 items-center justify-center rounded-full border-4 ${scoreBorderColor(health.score)} ${scoreBg(health.score)}`}
                    >
                      <div className="text-center">
                        <span
                          className={`block text-3xl font-bold leading-none ${scoreColor(health.score)}`}
                        >
                          {health.score}
                        </span>
                        <span className="text-[10px] font-medium text-slate-400">/ 100</span>
                      </div>
                    </div>

                    <div className="flex-1 space-y-4">
                      <div>
                        <p
                          className={`text-xl font-semibold ${scoreColor(health.score)}`}
                        >
                          {scoreLabel(health.score)}
                        </p>
                        <p className="text-sm text-slate-400 dark:text-slate-500">
                          Weighted composite of initiative completion, risk coverage, and resource allocation
                        </p>
                      </div>

                      {/* Component bars */}
                      <div className="space-y-3">
                        <ComponentBar
                          label="Initiative Completion (40%)"
                          value={health.components.initiative_completion}
                        />
                        <ComponentBar
                          label="Risk Coverage (30%)"
                          value={health.components.risk_coverage}
                        />
                        <ComponentBar
                          label="Resource Allocation (30%)"
                          value={health.components.resource_allocation}
                        />
                      </div>
                    </div>
                  </div>
                </section>

                {/* Initiative Breakdown */}
                <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] dark:border-slate-700 dark:bg-slate-800/60">
                  <h2 className="mb-5 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                    Initiative Breakdown
                  </h2>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <InitiativeStatCard
                      label="In Progress"
                      count={health.components.initiative_breakdown.in_progress}
                      colorClass="text-sky-600 dark:text-sky-400"
                    />
                    <InitiativeStatCard
                      label="Completed"
                      count={health.components.initiative_breakdown.completed}
                      colorClass="text-emerald-600 dark:text-emerald-400"
                    />
                    <InitiativeStatCard
                      label="Blocked"
                      count={health.components.initiative_breakdown.blocked}
                      colorClass="text-red-500 dark:text-red-400"
                    />
                    <InitiativeStatCard
                      label="Not Started"
                      count={health.components.initiative_breakdown.not_started}
                      colorClass="text-slate-400 dark:text-slate-500"
                    />
                  </div>
                  <p className="mt-3 text-xs text-slate-400">
                    {health.components.initiative_breakdown.total} total initiatives
                  </p>
                </section>

                {/* Metrics Row: Workflow Success Rate + Risk Score + Revenue Trend */}
                <div className="grid gap-6 lg:grid-cols-3">
                  {/* Workflow Success Rate */}
                  <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] dark:border-slate-700 dark:bg-slate-800/60">
                    <div className="mb-3 flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-indigo-500" />
                      <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                        Workflow Success Rate
                      </h2>
                    </div>
                    <p
                      className={`text-4xl font-bold ${scoreColor(health.components.workflow_success_rate)}`}
                    >
                      {health.components.workflow_success_rate}%
                    </p>
                    <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
                      <div
                        className={`h-full transition-all ${barColor(health.components.workflow_success_rate)}`}
                        style={{ width: `${health.components.workflow_success_rate}%` }}
                      />
                    </div>
                    <p className="mt-2 text-xs text-slate-400">
                      Completed workflow executions
                    </p>
                  </section>

                  {/* Risk Score */}
                  <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] dark:border-slate-700 dark:bg-slate-800/60">
                    <div className="mb-3 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                      <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                        Risk Exposure
                      </h2>
                    </div>
                    <p
                      className={`text-4xl font-bold ${riskExposure >= 60 ? 'text-red-500' : riskExposure >= 30 ? 'text-amber-500' : 'text-emerald-600'}`}
                    >
                      {riskExposure}%
                    </p>
                    <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
                      <div
                        className={`h-full transition-all ${riskExposure >= 60 ? 'bg-red-400' : riskExposure >= 30 ? 'bg-amber-400' : 'bg-emerald-400'}`}
                        style={{ width: `${riskExposure}%` }}
                      />
                    </div>
                    <p className="mt-2 text-xs text-slate-400">
                      Risks without mitigation plans (100 - risk coverage)
                    </p>
                  </section>

                  {/* Revenue Trend */}
                  <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] dark:border-slate-700 dark:bg-slate-800/60">
                    <div className="mb-3 flex items-center gap-2">
                      <Activity className="h-4 w-4 text-teal-500" />
                      <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
                        Revenue Trend
                      </h2>
                    </div>
                    <p className="text-4xl font-bold text-slate-900 dark:text-white">
                      {formatCurrency(health.components.revenue_trend.current_month)}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">This month</p>
                    <div className="mt-3 flex items-center gap-1.5">
                      {revenueDiff === null ? null : revenueDiff > 0 ? (
                        <TrendingUp className="h-4 w-4 text-emerald-500" />
                      ) : revenueDiff < 0 ? (
                        <TrendingDown className="h-4 w-4 text-red-400" />
                      ) : (
                        <Minus className="h-4 w-4 text-slate-400" />
                      )}
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        Prior month: {formatCurrency(health.components.revenue_trend.prior_month)}
                      </span>
                    </div>
                  </section>
                </div>
              </>
            )}
          </motion.div>
        </PremiumShell>
      </DashboardErrorBoundary>
    </GatedPage>
  );
}
