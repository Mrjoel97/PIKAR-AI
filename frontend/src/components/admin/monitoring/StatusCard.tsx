'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { Sparkline } from './Sparkline';

/**
 * EndpointStatus describes the current health of one monitored endpoint,
 * matching the GET /admin/monitoring/status API response shape.
 */
export interface EndpointStatus {
  name: string;
  current_status: string;
  latest_check_at: string | null;
  response_time_ms: number | null;
  history: HistoryEntry[];
}

interface HistoryEntry {
  checked_at: string;
  response_time_ms: number;
  status: string;
}

/** Badge style per status value */
const STATUS_BADGE: Record<string, string> = {
  healthy: 'bg-emerald-900 text-emerald-300',
  degraded: 'bg-amber-900 text-amber-300',
  unhealthy: 'bg-rose-900 text-rose-300',
  unknown: 'bg-gray-700 text-gray-400',
};

function formatRelativeTime(isoTimestamp: string | null): string {
  if (!isoTimestamp) return 'Never';
  const diffMs = Date.now() - new Date(isoTimestamp).getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  if (diffSeconds < 60) return 'just now';
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes === 1) return '1 min ago';
  if (diffMinutes < 60) return `${diffMinutes} min ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours === 1) return '1 hour ago';
  return `${diffHours} hours ago`;
}

/**
 * StatusCard renders a single health endpoint card with current status badge,
 * response time, last-checked time, and a sparkline of recent history.
 */
interface StatusCardProps {
  endpoint: EndpointStatus;
}

export function StatusCard({ endpoint }: StatusCardProps) {
  const badgeClass = STATUS_BADGE[endpoint.current_status] ?? STATUS_BADGE.unknown;
  const isHealthy = endpoint.current_status === 'healthy';

  // History comes in DESC order from API -- reverse for left-to-right chronological display
  const sparklineData = [...endpoint.history].reverse().map((h) => ({
    response_time_ms: h.response_time_ms,
  }));

  const displayName =
    endpoint.name.charAt(0).toUpperCase() + endpoint.name.slice(1);

  return (
    <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 flex flex-col gap-3">
      {/* Header row: name + status badge */}
      <div className="flex items-center justify-between">
        <h3 className="text-gray-100 font-semibold text-sm">{displayName}</h3>
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${badgeClass}`}
        >
          {endpoint.current_status}
        </span>
      </div>

      {/* Metrics row */}
      <div className="flex items-center justify-between text-xs text-gray-400">
        <span>
          {endpoint.response_time_ms !== null
            ? `${endpoint.response_time_ms}ms`
            : 'N/A'}
        </span>
        <span>Checked {formatRelativeTime(endpoint.latest_check_at)}</span>
      </div>

      {/* Sparkline */}
      <Sparkline data={sparklineData} isHealthy={isHealthy} />
    </div>
  );
}
