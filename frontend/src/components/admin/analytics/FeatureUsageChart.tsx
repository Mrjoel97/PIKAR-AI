'use client';

import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface ByCategory {
  category: string;
  event_count: number;
}

interface ByTool {
  tool_name: string;
  call_count: number;
}

interface FeatureUsage {
  by_tool: ByTool[];
  by_category: ByCategory[];
}

interface FeatureUsageChartProps {
  featureUsage: FeatureUsage | null | undefined;
}

/**
 * FeatureUsageChart renders a vertical bar chart for feature usage by category
 * plus a top-10 tools table.
 * Uses recharts 3.x: accessibilityLayer=false, isAnimationActive=false.
 */
export function FeatureUsageChart({ featureUsage }: FeatureUsageChartProps) {
  const byCategory = featureUsage?.by_category ?? [];
  const byTool = featureUsage?.by_tool ?? [];

  const hasData = byCategory.length > 0 || byTool.length > 0;

  if (!hasData) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 h-full">
        <h2 className="text-gray-100 font-semibold mb-4">Feature Usage</h2>
        <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
          No feature usage data recorded yet
        </div>
      </div>
    );
  }

  const topTools = [...byTool]
    .sort((a, b) => b.call_count - a.call_count)
    .slice(0, 10);

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 h-full">
      <h2 className="text-gray-100 font-semibold mb-4">Feature Usage</h2>

      {byCategory.length > 0 && (
        <div className="mb-6">
          <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-2">By Category</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={byCategory} margin={{ top: 0, right: 8, bottom: 0, left: 0 }} accessibilityLayer={false}>
              <XAxis
                dataKey="category"
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                axisLine={{ stroke: '#374151' }}
                tickLine={false}
                interval={0}
                angle={-30}
                textAnchor="end"
                height={40}
              />
              <YAxis
                tick={{ fill: '#9ca3af', fontSize: 11 }}
                axisLine={{ stroke: '#374151' }}
                tickLine={false}
                width={36}
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
              <Bar
                dataKey="event_count"
                name="Events"
                fill="#818cf8"
                radius={[3, 3, 0, 0]}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {topTools.length > 0 && (
        <div>
          <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-2">Top Tools</h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500 border-b border-gray-700">
                <th className="text-left pb-1 font-medium">Tool</th>
                <th className="text-right pb-1 font-medium">Calls</th>
              </tr>
            </thead>
            <tbody>
              {topTools.map((tool) => (
                <tr key={tool.tool_name} className="border-b border-gray-700/50">
                  <td className="py-1 text-gray-300 truncate max-w-[140px]">{tool.tool_name}</td>
                  <td className="py-1 text-gray-400 text-right">{tool.call_count.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
