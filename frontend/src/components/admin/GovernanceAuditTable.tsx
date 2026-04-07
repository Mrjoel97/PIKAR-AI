'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * GovernanceAuditTable
 *
 * Filterable, paginated table for the user-action audit trail
 * (governance_audit_log). Reads via GET /admin/governance-audit-log
 * (Phase 49 Plan 05 — AUTH-05).
 *
 * Sibling of the admin_audit_log table rendered by
 * frontend/src/app/(admin)/audit-log/page.tsx — two tables, two components.
 *
 * data-testid attributes are stable anchors for Phase 51 (Observability)
 * UAT + playwright smoke tests:
 *   - filter-email, filter-action-type, filter-start-date, filter-end-date
 *   - audit-row (one per entry)
 *   - pagination-prev, pagination-next
 */

import React, { useCallback, useEffect, useState } from 'react';
import { fetchWithAuthRaw } from '@/services/api';

/** One row of governance_audit_log as returned by the admin endpoint. */
interface AuditEntry {
  id: string;
  user_id: string;
  actor_email: string;
  action_type: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

interface AuditLogResponse {
  entries: AuditEntry[];
  total: number;
  limit: number;
  offset: number;
}

interface ActionsResponse {
  actions: string[];
}

interface Filters {
  email: string;
  action_type: string;
  start_date: string;
  end_date: string;
}

const PAGE_SIZE = 50;

/**
 * Renders the governance audit log with filter bar + paginated table.
 * Fetches the distinct action_type list once on mount to populate the
 * dropdown, then re-fetches entries whenever filters or offset change.
 */
export function GovernanceAuditTable(): React.ReactElement {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionsList, setActionsList] = useState<string[]>([]);
  const [filters, setFilters] = useState<Filters>({
    email: '',
    action_type: '',
    start_date: '',
    end_date: '',
  });

  // Fetch the distinct action_type list once on mount.
  useEffect(() => {
    let cancelled = false;
    fetchWithAuthRaw('/admin/governance-audit-log/actions')
      .then((r) => (r.ok ? r.json() : Promise.resolve({ actions: [] })))
      .then((d: ActionsResponse) => {
        if (!cancelled) setActionsList(d.actions || []);
      })
      .catch(() => {
        if (!cancelled) setActionsList([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const fetchEntries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set('limit', String(PAGE_SIZE));
      params.set('offset', String(offset));
      if (filters.email) params.set('email', filters.email);
      if (filters.action_type) params.set('action_type', filters.action_type);
      if (filters.start_date) params.set('start_date', filters.start_date);
      if (filters.end_date) params.set('end_date', filters.end_date);

      const r = await fetchWithAuthRaw(
        `/admin/governance-audit-log?${params.toString()}`,
      );
      if (!r.ok) {
        throw new Error(`HTTP ${r.status}`);
      }
      const data = (await r.json()) as AuditLogResponse;
      setEntries(data.entries || []);
      setTotal(data.total || 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load audit log');
    } finally {
      setLoading(false);
    }
  }, [filters, offset]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  const onFilterChange = (key: keyof Filters, value: string) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setOffset(0);
  };

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 p-4 bg-gray-900 border border-gray-700 rounded-xl">
        <input
          type="text"
          placeholder="Filter by user email"
          value={filters.email}
          onChange={(e) => onFilterChange('email', e.target.value)}
          className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 outline-none focus:ring-1 focus:ring-indigo-500"
          data-testid="filter-email"
          aria-label="Filter by user email"
        />
        <select
          value={filters.action_type}
          onChange={(e) => onFilterChange('action_type', e.target.value)}
          className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 outline-none focus:ring-1 focus:ring-indigo-500"
          data-testid="filter-action-type"
          aria-label="Filter by action type"
        >
          <option value="">All actions</option>
          {actionsList.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={filters.start_date}
          onChange={(e) => onFilterChange('start_date', e.target.value)}
          className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 outline-none focus:ring-1 focus:ring-indigo-500"
          data-testid="filter-start-date"
          aria-label="Filter by start date"
        />
        <input
          type="date"
          value={filters.end_date}
          onChange={(e) => onFilterChange('end_date', e.target.value)}
          className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 outline-none focus:ring-1 focus:ring-indigo-500"
          data-testid="filter-end-date"
          aria-label="Filter by end date"
        />
      </div>

      {/* Status */}
      {loading && (
        <div className="text-sm text-gray-400" data-testid="audit-loading">
          Loading…
        </div>
      )}
      {error && (
        <div className="text-sm text-rose-400" data-testid="audit-error">
          Error: {error}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-700">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-800">
            <tr className="text-left text-gray-300">
              <th className="px-4 py-3 font-medium">Timestamp</th>
              <th className="px-4 py-3 font-medium">Actor</th>
              <th className="px-4 py-3 font-medium">Action</th>
              <th className="px-4 py-3 font-medium">Resource</th>
              <th className="px-4 py-3 font-medium">Details</th>
            </tr>
          </thead>
          <tbody className="bg-gray-900 divide-y divide-gray-800">
            {entries.map((entry) => (
              <tr key={entry.id} data-testid="audit-row">
                <td className="px-4 py-3 text-gray-400 whitespace-nowrap">
                  {new Date(entry.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-gray-200">{entry.actor_email}</td>
                <td className="px-4 py-3 text-indigo-300 font-mono">
                  {entry.action_type}
                </td>
                <td className="px-4 py-3 text-gray-400">
                  {entry.resource_type}
                  {entry.resource_id && (
                    <span className="text-gray-600">/{entry.resource_id}</span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-500 max-w-xs truncate">
                  <code className="text-xs">{JSON.stringify(entry.details)}</code>
                </td>
              </tr>
            ))}
            {!loading && entries.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-12 text-center text-gray-500"
                >
                  No audit entries match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-gray-400">
        <div>
          Showing {entries.length === 0 ? 0 : offset + 1}–
          {offset + entries.length} of {total}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            disabled={offset === 0}
            className="px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            data-testid="pagination-prev"
          >
            Previous
          </button>
          <button
            type="button"
            onClick={() => setOffset(offset + PAGE_SIZE)}
            disabled={offset + PAGE_SIZE >= total}
            className="px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            data-testid="pagination-next"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

export default GovernanceAuditTable;
