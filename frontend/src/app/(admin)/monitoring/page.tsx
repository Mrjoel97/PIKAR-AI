'use client';

import { useCallback, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { IncidentPanel, type Incident } from '@/components/admin/monitoring/IncidentPanel';
import { StatusCard, type EndpointStatus } from '@/components/admin/monitoring/StatusCard';
import { StaleDataBanner } from '@/components/admin/monitoring/StaleDataBanner';

/** Full response from GET /admin/monitoring/status */
interface MonitoringStatusResponse {
  endpoints: EndpointStatus[];
  open_incidents: Incident[];
  latest_check_at: string | null;
}

/** Auto-refresh interval in milliseconds */
const REFRESH_INTERVAL_MS = 30_000;

/**
 * MonitoringPage renders the /admin/monitoring dashboard with:
 * - Per-endpoint status cards with sparklines
 * - Stale-data banner when data is >5 minutes old
 * - Active incidents panel
 * - 30-second auto-refresh polling
 */
export default function MonitoringPage() {
  const [data, setData] = useState<MonitoringStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const supabase = createClient();
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchStatus = useCallback(async () => {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setFetchError('Not authenticated');
        setIsLoading(false);
        return;
      }

      const res = await fetch(`${API_URL}/admin/monitoring/status`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (!res.ok) {
        setFetchError(`Failed to load monitoring data (${res.status})`);
        setIsLoading(false);
        return;
      }

      const json = (await res.json()) as MonitoringStatusResponse;
      setData(json);
      setFetchError(null);
    } catch {
      setFetchError('Failed to load monitoring data. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [supabase, API_URL]);

  // Initial fetch + 30-second polling
  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">System Monitoring</h1>
        <button
          type="button"
          onClick={() => {
            setIsLoading(true);
            fetchStatus();
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-600 transition-colors"
          aria-label="Refresh monitoring data"
        >
          Refresh
        </button>
      </div>

      {/* Stale-data banner — only shown when data exists and is >5 min old */}
      {data && (
        <div className="mb-4">
          <StaleDataBanner latestCheckAt={data.latest_check_at} />
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && !data && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mb-6">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="bg-gray-800 rounded-xl p-5 border border-gray-700 h-32 animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Error state */}
      {fetchError && (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <p className="text-red-400 text-sm">{fetchError}</p>
          <button
            type="button"
            onClick={() => {
              setIsLoading(true);
              fetchStatus();
            }}
            className="px-4 py-2 bg-gray-800 text-gray-200 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Dashboard content */}
      {data && (
        <>
          {data.endpoints.length === 0 ? (
            <div className="flex items-center justify-center py-20 text-gray-500 text-sm">
              No health endpoint data available yet.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 mb-6">
              {data.endpoints.map((endpoint) => (
                <StatusCard key={endpoint.name} endpoint={endpoint} />
              ))}
            </div>
          )}

          <IncidentPanel incidents={data.open_incidents} />
        </>
      )}
    </div>
  );
}
