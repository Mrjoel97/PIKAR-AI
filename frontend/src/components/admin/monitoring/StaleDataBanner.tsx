/**
 * StaleDataBanner renders an amber warning when health data hasn't been refreshed
 * in more than 5 minutes. Renders nothing when data is fresh or when no data exists yet.
 */
interface StaleDataBannerProps {
  /** ISO timestamp of the most recent health check, or null when no data exists. */
  latestCheckAt: string | null;
}

/** 5 minutes in milliseconds */
const STALE_THRESHOLD_MS = 5 * 60 * 1000;

function formatRelativeTime(isoTimestamp: string): string {
  const diffMs = Date.now() - new Date(isoTimestamp).getTime();
  const diffMinutes = Math.floor(diffMs / 60_000);
  if (diffMinutes < 1) return 'just now';
  if (diffMinutes === 1) return '1 minute ago';
  if (diffMinutes < 60) return `${diffMinutes} minutes ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours === 1) return '1 hour ago';
  return `${diffHours} hours ago`;
}

export function StaleDataBanner({ latestCheckAt }: StaleDataBannerProps) {
  // No data yet -- not stale, just empty
  if (latestCheckAt === null) return null;

  const isStale = Date.now() - new Date(latestCheckAt).getTime() > STALE_THRESHOLD_MS;

  if (!isStale) return null;

  return (
    <div className="bg-amber-900/50 border border-amber-600 text-amber-300 rounded-xl px-4 py-3 text-sm">
      Warning: Health check data is stale -- last updated {formatRelativeTime(latestCheckAt)}.
      Cloud Scheduler may be paused.
    </div>
  );
}
