'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import {
  Line,
  LineChart,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

/** One row from usage_trends in the analytics summary API response. */
interface UsageTrendEntry {
  stat_date: string;
  dau: number;
  mau: number;
  messages: number;
  workflows: number;
}

interface ActivityChartProps {
  /** Usage trend rows ordered newest-first (as returned by the API). */
  usageTrends: UsageTrendEntry[];
}

/** Format "2026-03-20" → "Mar 20" */
function formatDate(isoDate: string): string {
  const date = new Date(isoDate + 'T00:00:00Z');
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
}

/**
 * ActivityChart renders a dual-line DAU/MAU trend over 30 days.
 * Data is reversed from API DESC order to ASC for left-to-right chronological display.
 * Uses recharts 3.x: accessibilityLayer=false, isAnimationActive=false, no activeIndex prop.
 */
export function ActivityChart({ usageTrends }: ActivityChartProps) {
  if (usageTrends.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h2 className="text-gray-100 font-semibold mb-4">Activity Trends (DAU / MAU)</h2>
        <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
          No activity data available
        </div>
      </div>
    );
  }

  // API returns newest-first; recharts needs oldest-first (left → right)
  const chartData = [...usageTrends]
    .reverse()
    .map((row) => ({ ...row, date: formatDate(row.stat_date) }));

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h2 className="text-gray-100 font-semibold mb-4">Activity Trends (DAU / MAU)</h2>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={chartData} accessibilityLayer={false}>
          <XAxis
            dataKey="date"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            axisLine={{ stroke: '#374151' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            axisLine={{ stroke: '#374151' }}
            tickLine={false}
            width={40}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1f2937',
              border: '1px solid #4b5563',
              borderRadius: '6px',
              color: '#f3f4f6',
              fontSize: 12,
            }}
          />
          <Legend
            wrapperStyle={{ color: '#9ca3af', fontSize: 12, paddingTop: 8 }}
          />
          <Line
            type="monotone"
            dataKey="dau"
            name="DAU"
            stroke="#60a5fa"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="mau"
            name="MAU"
            stroke="#a78bfa"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
