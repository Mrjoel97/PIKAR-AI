'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


/** Provider descriptions keyed by provider name */
const PROVIDER_DESCRIPTIONS: Record<string, string> = {
  sentry: 'Error tracking and performance monitoring',
  posthog: 'Product analytics and user behavior',
  github: 'Repository, PRs, and CI/CD status',
  stripe: 'Billing, subscriptions, and revenue',
};

/**
 * Returns a human-readable relative time string from an ISO timestamp.
 * E.g. "2 min ago", "1 hour ago", "just now"
 */
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

/** Health indicator dot color by status */
function HealthDot({ status }: { status: string }) {
  let colorClass = 'bg-gray-400';
  if (status === 'healthy') colorClass = 'bg-green-400';
  else if (status === 'unhealthy') colorClass = 'bg-red-400';

  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${colorClass} mr-1.5`}
      aria-label={`Health: ${status}`}
    />
  );
}

/** Props for the ProviderCard component */
export interface ProviderCardProps {
  /** "sentry" | "posthog" | "github" | "stripe" */
  provider: string;
  isActive: boolean;
  /** "healthy" | "unhealthy" | "unknown" */
  healthStatus: string;
  keyLast4: string | null;
  updatedAt: string | null;
  /** Opens the configure modal for this provider */
  onConfigure: () => void;
  /** Triggers a test-connection API call */
  onTestConnection: () => void;
  /** Loading state while test is in progress */
  isTesting: boolean;
}

/**
 * ProviderCard renders a single integration provider card with:
 * - Provider name + description
 * - Connection status badge (green = connected, gray = not configured)
 * - Masked API key display and health indicator when connected
 * - Last-checked relative time
 * - Configure and Test Connection action buttons
 */
export function ProviderCard({
  provider,
  isActive,
  healthStatus,
  keyLast4,
  updatedAt,
  onConfigure,
  onTestConnection,
  isTesting,
}: ProviderCardProps) {
  const displayName = provider.charAt(0).toUpperCase() + provider.slice(1);
  const description = PROVIDER_DESCRIPTIONS[provider] ?? provider;

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 flex flex-col gap-4">
      {/* Header: name + status badge */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-gray-100 font-semibold text-base">{displayName}</h3>
          <p className="text-gray-400 text-sm mt-0.5">{description}</p>
        </div>
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${
            isActive
              ? 'bg-green-500/10 text-green-400'
              : 'bg-gray-600/10 text-gray-400 border border-gray-600'
          }`}
        >
          {isActive ? 'Connected' : 'Not configured'}
        </span>
      </div>

      {/* Connected details */}
      {isActive && (
        <div className="space-y-1.5 text-sm text-gray-400">
          {keyLast4 && (
            <div className="flex items-center gap-1">
              <span className="text-gray-500">Key:</span>
              <span className="font-mono text-gray-300">****...{keyLast4}</span>
            </div>
          )}
          <div className="flex items-center">
            <HealthDot status={healthStatus} />
            <span className="capitalize">{healthStatus}</span>
            {updatedAt && (
              <span className="ml-2 text-gray-500">
                &bull; Last checked: {formatRelativeTime(updatedAt)}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2 mt-auto pt-2">
        <button
          type="button"
          onClick={onConfigure}
          className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 text-gray-100 rounded-lg border border-gray-600 transition-colors"
        >
          Configure
        </button>
        {isActive && (
          <button
            type="button"
            onClick={onTestConnection}
            disabled={isTesting}
            className="px-3 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-1.5"
          >
            {isTesting ? (
              <>
                <svg
                  className="w-3.5 h-3.5 animate-spin"
                  fill="none"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Testing…
              </>
            ) : (
              'Test Connection'
            )}
          </button>
        )}
      </div>
    </div>
  );
}
