'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useCallback, useEffect, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Shape of a single MCP endpoint from GET /admin/config/mcp-endpoints */
interface McpEndpoint {
  name: string;
  display_name?: string;
  url: string;
  status: string;
  description?: string;
  capabilities?: string[];
}

/** Props for McpEndpoints */
export interface McpEndpointsProps {
  /** Supabase access_token for Authorization header */
  token: string;
}

/**
 * McpEndpoints renders a read-only list of MCP endpoint configurations.
 *
 * Endpoint status badges: active=emerald, inactive=gray.
 * Includes a note that endpoint management requires a developer.
 */
export function McpEndpoints({ token }: McpEndpointsProps) {
  const [endpoints, setEndpoints] = useState<McpEndpoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const fetchEndpoints = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const res = await fetch(`${API_URL}/admin/config/mcp-endpoints`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        setFetchError(`Failed to load MCP endpoints (${res.status})`);
        return;
      }
      const data = (await res.json()) as McpEndpoint[];
      setEndpoints(data);
    } catch {
      setFetchError('Failed to load MCP endpoints. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchEndpoints();
  }, [fetchEndpoints]);

  // ─── Render ───────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-gray-800 rounded-lg h-16 animate-pulse" />
        ))}
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-4">
        <p className="text-red-400 text-sm">{fetchError}</p>
        <button
          type="button"
          onClick={() => { setIsLoading(true); fetchEndpoints(); }}
          className="px-4 py-2 bg-gray-800 text-gray-200 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Read-only notice */}
      <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-gray-800 border border-gray-700 text-gray-400 text-sm">
        <svg
          className="w-4 h-4 mt-0.5 shrink-0 text-gray-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span>
          MCP endpoint management is read-only. Contact a developer to add or remove
          endpoints.
        </span>
      </div>

      {/* Endpoint cards */}
      {endpoints.length === 0 && (
        <div className="text-center py-12 text-gray-500 text-sm">
          No MCP endpoints configured.
        </div>
      )}

      <div className="space-y-3">
        {endpoints.map((endpoint) => {
          const isActive = endpoint.status === 'active';
          return (
            <div
              key={endpoint.name}
              className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 flex items-center justify-between gap-4"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-100">
                  {endpoint.display_name || endpoint.name}
                </p>
                {endpoint.description && (
                  <p className="text-xs text-gray-400 mt-0.5">{endpoint.description}</p>
                )}
                <p className="text-xs text-gray-500 font-mono truncate mt-0.5">
                  {endpoint.url}
                </p>
              </div>
              <span
                className={`shrink-0 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'bg-gray-600/20 text-gray-400 border border-gray-600'
                }`}
              >
                {isActive ? 'Active' : 'Inactive'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
