// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Admin overview page — the default view at /admin.
 * Shows a welcome heading and placeholder status cards for later phases.
 */
export default function AdminOverviewPage() {
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-100">Welcome to Pikar Admin</h1>
        <p className="mt-2 text-gray-400">
          Manage and monitor your platform from a single place.
        </p>
      </div>

      {/* Status cards — populated in later phases */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatusCard title="System Status" value="Operational" status="ok" />
        <StatusCard title="Active Users" value="—" status="neutral" />
        <StatusCard title="Pending Approvals" value="—" status="neutral" />
        <StatusCard title="Agent Health" value="—" status="neutral" />
        <StatusCard title="Workflow Queue" value="—" status="neutral" />
        <StatusCard title="Recent Alerts" value="—" status="neutral" />
      </div>
    </div>
  );
}

interface StatusCardProps {
  title: string;
  value: string;
  status: 'ok' | 'warn' | 'error' | 'neutral';
}

function StatusCard({ title, value, status }: StatusCardProps) {
  const statusColors: Record<StatusCardProps['status'], string> = {
    ok: 'text-green-400',
    warn: 'text-amber-400',
    error: 'text-red-400',
    neutral: 'text-gray-400',
  };

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
      <p className="text-sm font-medium text-gray-400">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${statusColors[status]}`}>{value}</p>
    </div>
  );
}
