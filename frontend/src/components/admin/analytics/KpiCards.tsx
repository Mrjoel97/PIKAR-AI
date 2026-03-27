'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


/**
 * UsageTrendEntry describes one day of usage data from the analytics summary API.
 */
interface UsageTrendEntry {
  stat_date: string;
  dau: number;
  mau: number;
  messages: number;
  workflows: number;
}

interface KpiCardsProps {
  /** Usage trend rows ordered newest-first (as returned by the API). */
  usageTrends: UsageTrendEntry[];
}

interface KpiCardProps {
  label: string;
  value: number | string;
  colorClass: string;
}

/** Single KPI card with label, value, and a colored accent bar. */
function KpiCard({ label, value, colorClass }: KpiCardProps) {
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 flex flex-col gap-2">
      <span className="text-gray-400 text-sm">{label}</span>
      <span className={`text-2xl font-bold ${colorClass}`}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </span>
    </div>
  );
}

/**
 * KpiCards renders four KPI metric cards:
 * - DAU (latest day from usage_trends)
 * - MAU (latest day from usage_trends)
 * - Total Messages over the period
 * - Total Workflows over the period
 */
export function KpiCards({ usageTrends }: KpiCardsProps) {
  const latest = usageTrends.length > 0 ? usageTrends[0] : null;
  const totalMessages = usageTrends.reduce((sum, row) => sum + row.messages, 0);
  const totalWorkflows = usageTrends.reduce((sum, row) => sum + row.workflows, 0);

  const dau = latest?.dau ?? 0;
  const mau = latest?.mau ?? 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <KpiCard label="Daily Active Users" value={dau} colorClass="text-blue-400" />
      <KpiCard label="Monthly Active Users" value={mau} colorClass="text-purple-400" />
      <KpiCard label="Total Messages" value={totalMessages} colorClass="text-emerald-400" />
      <KpiCard label="Total Workflows" value={totalWorkflows} colorClass="text-amber-400" />
    </div>
  );
}
