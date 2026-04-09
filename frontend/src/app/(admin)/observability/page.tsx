'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type TabKey = 'errors' | 'performance' | 'cost' | 'health';
type WindowKey = '1h' | '24h' | '7d' | '30d';

interface SummaryResponse {
  error_rate_24h: { error_rate: number; error_count: number; total_count: number };
  mtd_ai_spend: {
    mtd_actual: number;
    projected_full_month: number;
    projection_method: string;
  };
  p95_latency_24h: {
    p50: number;
    p95: number;
    p99: number;
    sample_count: number;
    error_count: number;
  };
  threshold_breach: unknown | null;
}

interface LatencyResponse {
  p50: number;
  p95: number;
  p99: number;
  sample_count: number;
  error_count: number;
}

interface ErrorsResponse {
  error_rate: number;
  error_count: number;
  total_count: number;
}

interface CostByAgentResponse {
  [agent: string]: number;
}

interface CostByDayItem {
  date: string;
  cost_usd: number;
}

interface EndpointStatus {
  name: string;
  status: 'ok' | 'degraded' | 'down' | string;
  response_time_ms: number | null;
  latest_check_at: string | null;
}

interface Incident {
  id: string;
  title: string;
  severity: string;
  created_at: string;
}

interface MonitoringStatusResponse {
  endpoints: EndpointStatus[];
  open_incidents: Incident[];
  latest_check_at: string | null;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Auto-refresh interval: 60 seconds */
const REFRESH_INTERVAL_MS = 60_000;

const TABS: { key: TabKey; label: string }[] = [
  { key: 'errors', label: 'Errors' },
  { key: 'performance', label: 'Performance' },
  { key: 'cost', label: 'AI Cost' },
  { key: 'health', label: 'Health' },
];

const WINDOWS: WindowKey[] = ['1h', '24h', '7d', '30d'];

const CHART_COLORS = [
  '#818cf8', // indigo-400
  '#34d399', // emerald-400
  '#f472b6', // pink-400
  '#fb923c', // orange-400
  '#a78bfa', // violet-400
  '#60a5fa', // blue-400
  '#facc15', // yellow-400
  '#4ade80', // green-400
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatMs(ms: number | null | undefined): string {
  if (ms == null) return '—';
  return `${Math.round(ms)}ms`;
}

function formatPercent(rate: number | null | undefined): string {
  if (rate == null) return '—';
  return `${(rate * 100).toFixed(1)}%`;
}

function formatUsd(amount: number | null | undefined): string {
  if (amount == null) return '—';
  return `$${amount.toFixed(2)}`;
}

function errorRateColor(rate: number): string {
  if (rate < 0.02) return 'text-green-400';
  if (rate <= 0.05) return 'text-amber-400';
  return 'text-red-400';
}

function endpointStatusColor(status: string): string {
  if (status === 'ok') return 'bg-green-500';
  if (status === 'degraded') return 'bg-amber-500';
  return 'bg-red-500';
}

function healthOverallColor(endpoints: EndpointStatus[]): string {
  if (endpoints.length === 0) return 'bg-gray-500';
  if (endpoints.some((e) => e.status === 'down')) return 'bg-red-500';
  if (endpoints.some((e) => e.status === 'degraded')) return 'bg-amber-500';
  return 'bg-green-500';
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SkeletonCard() {
  return <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 h-20 animate-pulse" />;
}

function MetricCard({
  title,
  value,
  subtitle,
  valueClass,
  dot,
}: {
  title: string;
  value: string;
  subtitle?: string;
  valueClass?: string;
  dot?: string;
}) {
  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700/50 p-4 shadow-sm">
      <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">{title}</p>
      <div className="flex items-center gap-2">
        {dot && <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${dot}`} />}
        <p className={`text-2xl font-bold text-gray-100 ${valueClass ?? ''}`}>{value}</p>
      </div>
      {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

/**
 * ObservabilityPage renders the /admin/observability dashboard with:
 * - Hero metrics row (error rate, MTD AI spend, p95 latency, health traffic light)
 * - Four tabs (Errors, Performance, AI Cost, Health) with URL persistence
 * - Time-range picker (1h, 24h, 7d, 30d)
 * - Recharts visualizations for cost trends and latency
 * - 60-second auto-refresh polling
 */
export default function ObservabilityPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const rawTab = searchParams.get('tab') as TabKey | null;
  const activeTab: TabKey = TABS.some((t) => t.key === rawTab) ? (rawTab as TabKey) : 'errors';
  const [window, setWindow] = useState<WindowKey>('24h');

  // Data state
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [healthData, setHealthData] = useState<MonitoringStatusResponse | null>(null);
  const [errorsData, setErrorsData] = useState<ErrorsResponse | null>(null);
  const [latencyData, setLatencyData] = useState<LatencyResponse | null>(null);
  const [costByAgent, setCostByAgent] = useState<CostByAgentResponse | null>(null);
  const [costByDay, setCostByDay] = useState<CostByDayItem[] | null>(null);

  // Loading / error state
  const [isLoadingSummary, setIsLoadingSummary] = useState(true);
  const [isLoadingTab, setIsLoadingTab] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [tabError, setTabError] = useState<string | null>(null);

  const supabase = createClient();
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // -------------------------------------------------------------------------
  // Tab navigation (URL persistence)
  // -------------------------------------------------------------------------

  function setTab(tab: TabKey) {
    const params = new URLSearchParams(searchParams.toString());
    params.set('tab', tab);
    router.replace(`?${params.toString()}`);
  }

  // -------------------------------------------------------------------------
  // Fetch helpers
  // -------------------------------------------------------------------------

  async function getToken(): Promise<string | null> {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  }

  const fetchSummary = useCallback(async () => {
    const token = await getToken();
    if (!token) {
      setSummaryError('Not authenticated');
      setIsLoadingSummary(false);
      return;
    }
    try {
      const res = await fetch(`${API_URL}/admin/observability/summary`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        setSummaryError(`Failed to load summary (${res.status})`);
        setIsLoadingSummary(false);
        return;
      }
      const json = (await res.json()) as SummaryResponse;
      setSummary(json);
      setSummaryError(null);
    } catch {
      setSummaryError('Failed to load summary. Check that the backend is running.');
    } finally {
      setIsLoadingSummary(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [API_URL]);

  const fetchHealth = useCallback(async () => {
    const token = await getToken();
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/admin/monitoring/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const json = (await res.json()) as MonitoringStatusResponse;
        setHealthData(json);
      }
    } catch {
      // non-fatal — health card shows gray if unavailable
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [API_URL]);

  const fetchTabData = useCallback(async () => {
    setIsLoadingTab(true);
    setTabError(null);
    const token = await getToken();
    if (!token) {
      setTabError('Not authenticated');
      setIsLoadingTab(false);
      return;
    }

    try {
      if (activeTab === 'errors') {
        const res = await fetch(
          `${API_URL}/admin/observability/errors?window=${window}`,
          { headers: { Authorization: `Bearer ${token}` } },
        );
        if (!res.ok) throw new Error(`${res.status}`);
        setErrorsData((await res.json()) as ErrorsResponse);
      } else if (activeTab === 'performance') {
        const res = await fetch(
          `${API_URL}/admin/observability/latency?window=${window}`,
          { headers: { Authorization: `Bearer ${token}` } },
        );
        if (!res.ok) throw new Error(`${res.status}`);
        setLatencyData((await res.json()) as LatencyResponse);
      } else if (activeTab === 'cost') {
        const [agentRes, dayRes] = await Promise.all([
          fetch(`${API_URL}/admin/observability/cost?window=${window}&group_by=agent`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_URL}/admin/observability/cost?window=${window}&group_by=day`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);
        if (!agentRes.ok || !dayRes.ok) throw new Error('Failed to load cost data');
        setCostByAgent((await agentRes.json()) as CostByAgentResponse);
        setCostByDay((await dayRes.json()) as CostByDayItem[]);
      } else if (activeTab === 'health') {
        // Health data is already fetched by fetchHealth — re-fetch on tab switch
        await fetchHealth();
      }
    } catch (err) {
      setTabError(`Failed to load ${activeTab} data. ${err instanceof Error ? err.message : ''}`);
    } finally {
      setIsLoadingTab(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, window, API_URL, fetchHealth]);

  // -------------------------------------------------------------------------
  // Effects
  // -------------------------------------------------------------------------

  // Initial load + 60-second polling for summary + health
  useEffect(() => {
    setIsLoadingSummary(true);
    fetchSummary();
    fetchHealth();
    const interval = setInterval(() => {
      fetchSummary();
      fetchHealth();
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchSummary, fetchHealth]);

  // Fetch tab-specific data when tab or window changes
  useEffect(() => {
    fetchTabData();
  }, [fetchTabData]);

  // -------------------------------------------------------------------------
  // Derived values for hero cards
  // -------------------------------------------------------------------------

  const errorRate = summary?.error_rate_24h?.error_rate ?? null;
  const mtdSpend = summary?.mtd_ai_spend?.mtd_actual ?? null;
  const projectedSpend = summary?.mtd_ai_spend?.projected_full_month ?? null;
  const p95Latency = summary?.p95_latency_24h?.p95 ?? null;
  const sampleCount = summary?.p95_latency_24h?.sample_count ?? null;
  const hasThresholdBreach = summary?.threshold_breach != null;
  const healthEndpoints = healthData?.endpoints ?? [];

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Observability</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Agent performance, errors, AI cost, and health
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setIsLoadingSummary(true);
            fetchSummary();
            fetchHealth();
            fetchTabData();
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-600 transition-colors"
          aria-label="Refresh observability data"
        >
          Refresh
        </button>
      </div>

      {/* Summary error banner */}
      {summaryError && (
        <div className="mb-4 flex items-center gap-3 bg-red-900/30 border border-red-700/50 rounded-lg px-4 py-3">
          <p className="text-red-300 text-sm flex-1">{summaryError}</p>
          <button
            type="button"
            onClick={() => {
              setIsLoadingSummary(true);
              fetchSummary();
            }}
            className="px-3 py-1 bg-red-800 text-red-100 rounded text-xs hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Hero metrics row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {isLoadingSummary ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <MetricCard
              title="Error Rate 24h"
              value={errorRate != null ? formatPercent(errorRate) : '—'}
              valueClass={errorRate != null ? errorRateColor(errorRate) : ''}
              subtitle={
                summary?.error_rate_24h
                  ? `${summary.error_rate_24h.error_count} errors / ${summary.error_rate_24h.total_count} requests`
                  : undefined
              }
              dot={hasThresholdBreach ? 'bg-red-500' : undefined}
            />
            <MetricCard
              title="MTD AI Spend"
              value={mtdSpend != null ? formatUsd(mtdSpend) : '—'}
              subtitle={
                projectedSpend != null
                  ? `Projected: ${formatUsd(projectedSpend)}/mo (7-day avg)`
                  : undefined
              }
            />
            <MetricCard
              title="p95 Latency"
              value={p95Latency != null ? formatMs(p95Latency) : '—'}
              subtitle={sampleCount != null ? `24h · ${sampleCount} requests` : '24h'}
            />
            <MetricCard
              title="System Health"
              value={
                healthEndpoints.length === 0
                  ? 'No data'
                  : healthEndpoints.every((e) => e.status === 'ok')
                    ? 'All OK'
                    : healthEndpoints.some((e) => e.status === 'down')
                      ? 'Degraded'
                      : 'Warning'
              }
              dot={healthOverallColor(healthEndpoints)}
            />
          </>
        )}
      </div>

      {/* Time-range picker */}
      <div className="flex gap-2 mb-4">
        {WINDOWS.map((w) => (
          <button
            key={w}
            type="button"
            onClick={() => setWindow(w)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              window === w
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-gray-200'
            }`}
          >
            {w}
          </button>
        ))}
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-gray-700 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? 'border-b-2 border-indigo-500 text-white'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content loading skeleton */}
      {isLoadingTab && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <div className="bg-gray-800 rounded-lg border border-gray-700 h-64 animate-pulse" />
        </div>
      )}

      {/* Tab error banner */}
      {tabError && !isLoadingTab && (
        <div className="flex flex-col items-center justify-center py-16 gap-4">
          <p className="text-red-400 text-sm">{tabError}</p>
          <button
            type="button"
            onClick={fetchTabData}
            className="px-4 py-2 bg-gray-800 text-gray-200 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* ERRORS TAB                                                          */}
      {/* ------------------------------------------------------------------ */}
      {activeTab === 'errors' && !isLoadingTab && !tabError && (
        <div className="space-y-6">
          {errorsData == null || errorsData.total_count === 0 ? (
            <div className="flex items-center justify-center py-20 text-gray-500 text-sm">
              No agent activity in the last {window}. Make some requests to see metrics here.
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <MetricCard
                  title="Error Count"
                  value={String(errorsData.error_count)}
                  valueClass={errorsData.error_count > 0 ? 'text-red-400' : 'text-green-400'}
                />
                <MetricCard
                  title="Total Requests"
                  value={String(errorsData.total_count)}
                />
                <MetricCard
                  title="Error Rate"
                  value={formatPercent(errorsData.error_rate)}
                  valueClass={errorRateColor(errorsData.error_rate)}
                />
              </div>

              {/* Simple area chart showing a single error-rate bar */}
              <div className="bg-gray-900 rounded-lg border border-gray-700/50 p-6">
                <h2 className="text-base font-semibold text-gray-200 mb-4">
                  Error Rate ({window})
                </h2>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart
                    data={[
                      {
                        name: 'Success',
                        value: errorsData.total_count - errorsData.error_count,
                      },
                      { name: 'Errors', value: errorsData.error_count },
                    ]}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="name" stroke="#9ca3af" tick={{ fontSize: 12 }} />
                    <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '6px',
                      }}
                      labelStyle={{ color: '#f3f4f6' }}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#818cf8"
                      fill="#818cf8"
                      fillOpacity={0.2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* PERFORMANCE TAB                                                     */}
      {/* ------------------------------------------------------------------ */}
      {activeTab === 'performance' && !isLoadingTab && !tabError && (
        <div className="space-y-6">
          {latencyData == null || latencyData.sample_count === 0 ? (
            <div className="flex items-center justify-center py-20 text-gray-500 text-sm">
              No agent activity in the last {window}. Make some requests to see latency data here.
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <MetricCard
                  title="p50 Latency"
                  value={formatMs(latencyData.p50)}
                  subtitle={`${latencyData.sample_count} requests`}
                />
                <MetricCard title="p95 Latency" value={formatMs(latencyData.p95)} />
                <MetricCard title="p99 Latency" value={formatMs(latencyData.p99)} />
              </div>

              <div className="bg-gray-900 rounded-lg border border-gray-700/50 p-6">
                <h2 className="text-base font-semibold text-gray-200 mb-4">
                  Latency Percentiles ({window})
                </h2>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart
                    data={[
                      {
                        percentile: 'p50',
                        latency: Math.round(latencyData.p50),
                      },
                      {
                        percentile: 'p95',
                        latency: Math.round(latencyData.p95),
                      },
                      {
                        percentile: 'p99',
                        latency: Math.round(latencyData.p99),
                      },
                    ]}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="percentile" stroke="#9ca3af" tick={{ fontSize: 12 }} />
                    <YAxis
                      stroke="#9ca3af"
                      tick={{ fontSize: 12 }}
                      label={{
                        value: 'ms',
                        angle: -90,
                        position: 'insideLeft',
                        fill: '#9ca3af',
                        fontSize: 11,
                      }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '6px',
                      }}
                      formatter={(v) => [`${v}ms`, 'Latency']}
                    />
                    <Bar dataKey="latency" fill="#818cf8" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* AI COST TAB                                                         */}
      {/* ------------------------------------------------------------------ */}
      {activeTab === 'cost' && !isLoadingTab && !tabError && (
        <div className="space-y-6">
          {costByAgent == null ||
          (Object.keys(costByAgent).length === 0 && (costByDay ?? []).length === 0) ? (
            <div className="flex items-center justify-center py-20 text-gray-500 text-sm">
              No AI cost data in the last {window}. Make some agent requests to see cost metrics
              here.
            </div>
          ) : (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <MetricCard
                  title={`Total Cost (${window})`}
                  value={formatUsd(
                    Object.values(costByAgent ?? {}).reduce((a, b) => a + b, 0),
                  )}
                />
                {summary?.mtd_ai_spend && (
                  <MetricCard
                    title="Monthly Projection"
                    value={formatUsd(summary.mtd_ai_spend.projected_full_month)}
                    subtitle="projection based on last 7 days"
                  />
                )}
              </div>

              {/* Cost by agent pie chart */}
              {costByAgent && Object.keys(costByAgent).length > 0 && (
                <div className="bg-gray-900 rounded-lg border border-gray-700/50 p-6">
                  <h2 className="text-base font-semibold text-gray-200 mb-4">
                    Cost by Agent ({window})
                  </h2>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={Object.entries(costByAgent).map(([name, value]) => ({
                          name,
                          value: parseFloat(value.toFixed(4)),
                        }))}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        label={({ name, percent }: { name?: string; percent?: number }) =>
                          `${(name ?? '').replace('Agent', '')} (${((percent ?? 0) * 100).toFixed(0)}%)`
                        }
                        labelLine={false}
                      >
                        {Object.keys(costByAgent).map((_, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={CHART_COLORS[index % CHART_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1f2937',
                          border: '1px solid #374151',
                          borderRadius: '6px',
                        }}
                        formatter={(v) => [formatUsd(typeof v === 'number' ? v : 0), 'Cost']}
                      />
                      <Legend
                        wrapperStyle={{ color: '#9ca3af', fontSize: '12px' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Cost by day line chart */}
              {costByDay && costByDay.length > 0 && (
                <div className="bg-gray-900 rounded-lg border border-gray-700/50 p-6">
                  <h2 className="text-base font-semibold text-gray-200 mb-4">
                    Daily Spend Trend ({window})
                  </h2>
                  <ResponsiveContainer width="100%" height={240}>
                    <LineChart data={costByDay}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis
                        dataKey="date"
                        stroke="#9ca3af"
                        tick={{ fontSize: 11 }}
                        tickFormatter={(d: string) => d.slice(5)} // MM-DD
                      />
                      <YAxis
                        stroke="#9ca3af"
                        tick={{ fontSize: 12 }}
                        tickFormatter={(v) => `$${(typeof v === 'number' ? v : 0).toFixed(2)}`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1f2937',
                          border: '1px solid #374151',
                          borderRadius: '6px',
                        }}
                        formatter={(v) => [formatUsd(typeof v === 'number' ? v : 0), 'Daily spend']}
                      />
                      <Line
                        type="monotone"
                        dataKey="cost_usd"
                        stroke="#818cf8"
                        strokeWidth={2}
                        dot={{ fill: '#818cf8', r: 3 }}
                        activeDot={{ r: 5 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* HEALTH TAB                                                          */}
      {/* ------------------------------------------------------------------ */}
      {activeTab === 'health' && !isLoadingTab && !tabError && (
        <div className="space-y-6">
          {healthData == null || healthData.endpoints.length === 0 ? (
            <div className="flex items-center justify-center py-20 text-gray-500 text-sm">
              No health check data available.
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {healthData.endpoints.map((endpoint) => (
                  <div
                    key={endpoint.name}
                    className="bg-gray-900 rounded-lg border border-gray-700/50 p-4 shadow-sm"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${endpointStatusColor(endpoint.status)}`}
                      />
                      <p className="text-sm font-semibold text-gray-200 truncate">
                        {endpoint.name}
                      </p>
                    </div>
                    <p className="text-xs text-gray-400 capitalize mb-1">{endpoint.status}</p>
                    {endpoint.response_time_ms != null && (
                      <p className="text-xs text-gray-500">
                        Response: {formatMs(endpoint.response_time_ms)}
                      </p>
                    )}
                    {endpoint.latest_check_at && (
                      <p className="text-xs text-gray-600 mt-1">
                        Checked: {formatDate(endpoint.latest_check_at)}
                      </p>
                    )}
                  </div>
                ))}
              </div>

              {/* Open incidents */}
              {healthData.open_incidents.length > 0 && (
                <div className="bg-gray-900 rounded-lg border border-red-700/30 p-6">
                  <h2 className="text-base font-semibold text-red-400 mb-4">
                    Open Incidents ({healthData.open_incidents.length})
                  </h2>
                  <div className="space-y-3">
                    {healthData.open_incidents.map((incident) => (
                      <div
                        key={incident.id}
                        className="flex items-start justify-between gap-4 border-b border-gray-800 pb-3 last:border-0 last:pb-0"
                      >
                        <div>
                          <p className="text-sm text-gray-200">{incident.title}</p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {formatDate(incident.created_at)}
                          </p>
                        </div>
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            incident.severity === 'critical'
                              ? 'bg-red-900/50 text-red-300'
                              : 'bg-amber-900/50 text-amber-300'
                          }`}
                        >
                          {incident.severity}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
