'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { Line, LineChart, ResponsiveContainer } from 'recharts';

/**
 * Sparkline renders a compact response-time history chart for a health endpoint.
 * Uses recharts 3.x (no activeIndex prop, no CategoricalChartState, accessibilityLayer=false).
 */
interface SparklineProps {
  /** Response-time history, oldest entry first for left-to-right chronological display. */
  data: { response_time_ms: number }[];
  /** Controls stroke color: green when healthy, red when degraded/unhealthy. */
  isHealthy: boolean;
}

export function Sparkline({ data, isHealthy }: SparklineProps) {
  if (data.length === 0) {
    return <div className="h-10 flex items-center justify-center text-gray-600 text-xs">No data</div>;
  }

  const stroke = isHealthy ? '#4ade80' : '#f87171';

  return (
    <ResponsiveContainer width="100%" height={40}>
      <LineChart data={data} accessibilityLayer={false}>
        <Line
          type="monotone"
          dataKey="response_time_ms"
          stroke={stroke}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
