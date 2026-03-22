'use client';

interface PermissionCounts {
  auto: number;
  confirm: number;
  blocked: number;
}

interface ConfigStatus {
  permission_counts: PermissionCounts;
  last_config_change: string | null;
}

interface ConfigStatusCardProps {
  configStatus: ConfigStatus | null | undefined;
}

/** Format a timestamp as relative time, e.g. "3 days ago". */
function formatRelativeTime(isoTimestamp: string | null): string {
  if (!isoTimestamp) return 'No config changes recorded';
  const diffMs = Date.now() - new Date(isoTimestamp).getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  if (diffSeconds < 60) return 'just now';
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes === 1) return '1 minute ago';
  if (diffMinutes < 60) return `${diffMinutes} minutes ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours === 1) return '1 hour ago';
  if (diffHours < 24) return `${diffHours} hours ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return '1 day ago';
  return `${diffDays} days ago`;
}

/**
 * ConfigStatusCard shows a compact overview of the active permission tier counts
 * and the last time the admin config was changed.
 */
export function ConfigStatusCard({ configStatus }: ConfigStatusCardProps) {
  const counts = configStatus?.permission_counts ?? { auto: 0, confirm: 0, blocked: 0 };
  const lastChange = configStatus?.last_config_change ?? null;

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 h-full">
      <h2 className="text-gray-100 font-semibold mb-4">Config Status</h2>

      <div className="mb-4">
        <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-2">
          Permission Tiers
        </h3>
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-gray-300 text-sm">Auto</span>
            </span>
            <span className="text-sm font-semibold text-emerald-400">
              {counts.auto.toLocaleString()}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-amber-400" />
              <span className="text-gray-300 text-sm">Confirm</span>
            </span>
            <span className="text-sm font-semibold text-amber-400">
              {counts.confirm.toLocaleString()}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-red-400" />
              <span className="text-gray-300 text-sm">Blocked</span>
            </span>
            <span className="text-sm font-semibold text-red-400">
              {counts.blocked.toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-gray-400 text-xs uppercase tracking-wider mb-2">
          Last Config Change
        </h3>
        <p className="text-gray-300 text-sm">{formatRelativeTime(lastChange)}</p>
      </div>
    </div>
  );
}
