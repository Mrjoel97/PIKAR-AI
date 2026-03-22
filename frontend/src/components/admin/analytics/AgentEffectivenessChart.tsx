'use client';

import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

/** One row from agent_effectiveness in the analytics summary API response. */
interface AgentEffectivenessEntry {
  agent_name: string;
  success_rate: number;
  avg_duration_ms: number;
  total_calls: number;
}

interface AgentEffectivenessChartProps {
  agentEffectiveness: AgentEffectivenessEntry[];
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: AgentEffectivenessEntry }>;
}

/** Custom tooltip showing success rate, avg duration, and total calls. */
function AgentTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  return (
    <div
      className="rounded"
      style={{
        backgroundColor: '#1f2937',
        border: '1px solid #4b5563',
        borderRadius: 6,
        padding: '8px 12px',
        color: '#f3f4f6',
        fontSize: 12,
      }}
    >
      <p className="font-semibold mb-1">{d.agent_name}</p>
      <p>Success rate: {d.success_rate.toFixed(1)}%</p>
      <p>Avg duration: {d.avg_duration_ms.toFixed(0)}ms</p>
      <p>Total calls: {d.total_calls.toLocaleString()}</p>
    </div>
  );
}

/**
 * AgentEffectivenessChart renders a horizontal bar chart of agent success rates.
 * Uses recharts 3.x: accessibilityLayer=false, isAnimationActive=false, no activeIndex prop.
 */
export function AgentEffectivenessChart({ agentEffectiveness }: AgentEffectivenessChartProps) {
  if (agentEffectiveness.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h2 className="text-gray-100 font-semibold mb-4">Agent Effectiveness</h2>
        <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
          No agent activity recorded yet
        </div>
      </div>
    );
  }

  // Truncate long names for Y-axis readability
  const chartData = agentEffectiveness.map((entry) => ({
    ...entry,
    display_name:
      entry.agent_name.length > 16 ? entry.agent_name.slice(0, 15) + '…' : entry.agent_name,
  }));

  const chartHeight = Math.max(240, chartData.length * 36);

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h2 className="text-gray-100 font-semibold mb-4">Agent Effectiveness</h2>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 0, right: 20, bottom: 0, left: 0 }}
          accessibilityLayer={false}
        >
          <XAxis
            type="number"
            domain={[0, 100]}
            tickFormatter={(v: number) => `${v}%`}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            axisLine={{ stroke: '#374151' }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="display_name"
            width={110}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<AgentTooltip />} />
          <Bar
            dataKey="success_rate"
            name="Success Rate"
            fill="#4ade80"
            radius={[0, 3, 3, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
