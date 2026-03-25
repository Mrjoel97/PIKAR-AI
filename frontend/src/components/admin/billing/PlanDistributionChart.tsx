'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface PlanDistributionChartProps {
  data: Array<{ tier: string; count: number }>;
}

/** Color map for each subscription tier. */
const PLAN_COLORS: Record<string, string> = {
  free: '#6b7280',
  solopreneur: '#3b82f6',
  startup: '#8b5cf6',
  sme: '#f59e0b',
  enterprise: '#10b981',
};

/** Default color for unknown tiers. */
const DEFAULT_COLOR = '#94a3b8';

/** Capitalize first letter of a string for display labels. */
function capitalize(s: string): string {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/**
 * PlanDistributionChart renders a pie chart showing the breakdown of
 * subscriptions by tier (free, solopreneur, startup, sme, enterprise).
 *
 * Uses established recharts 3.x patterns:
 * - accessibilityLayer={false}
 * - isAnimationActive={false}
 */
export function PlanDistributionChart({ data }: PlanDistributionChartProps) {
  if (!data || data.length === 0) {
    return (
      <p className="text-center text-gray-500 text-sm py-8">No plan distribution data</p>
    );
  }

  /** Map tier data to display-ready entries with capitalized names. */
  const chartData = data.map((entry) => ({
    name: capitalize(entry.tier),
    tier: entry.tier,
    value: entry.count,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart accessibilityLayer={false}>
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="45%"
          outerRadius={90}
          isAnimationActive={false}
        >
          {chartData.map((entry) => (
            <Cell
              key={entry.tier}
              fill={PLAN_COLORS[entry.tier] ?? DEFAULT_COLOR}
            />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: '#1f2937',
            border: '1px solid #374151',
            borderRadius: '8px',
            color: '#f3f4f6',
          }}
          formatter={(value, name) => [
            typeof value === 'number' ? value.toLocaleString() : String(value ?? 0),
            String(name),
          ]}
        />
        <Legend
          formatter={(value) => (
            <span style={{ color: '#9ca3af', fontSize: '12px' }}>{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
