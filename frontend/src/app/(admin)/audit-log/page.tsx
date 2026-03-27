'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useCallback, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';

/**
 * Audit log entry returned by GET /admin/audit-log.
 */
interface AuditEntry {
  id: string;
  created_at: string;
  admin_email: string;
  action: string;
  target_type?: string;
  target_id?: string;
  source: 'manual' | 'ai_agent' | 'impersonation' | 'monitoring_loop' | string;
  details?: Record<string, unknown>;
}

interface AuditLogResponse {
  entries: AuditEntry[];
  total: number;
  limit: number;
  offset: number;
}

const SOURCE_OPTIONS = [
  { label: 'All Sources', value: '' },
  { label: 'Manual', value: 'manual' },
  { label: 'AI Agent', value: 'ai_agent' },
  { label: 'Impersonation', value: 'impersonation' },
  { label: 'Monitoring Loop', value: 'monitoring_loop' },
];

const sourceBadgeClass: Record<string, string> = {
  manual: 'bg-blue-900 text-blue-300',
  ai_agent: 'bg-purple-900 text-purple-300',
  impersonation: 'bg-orange-900 text-orange-300',
  monitoring_loop: 'bg-gray-700 text-gray-300',
};

const LIMIT = 25;

/**
 * AuditLogPage renders the admin audit trail at /admin/audit-log.
 * Provides source filter, date-range filter, and prev/next pagination.
 */
export default function AuditLogPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [sourceFilter, setSourceFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const supabase = createClient();
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchEntries = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        setFetchError('Not authenticated');
        return;
      }

      const params = new URLSearchParams({
        limit: String(LIMIT),
        offset: String(offset),
      });
      if (sourceFilter) params.set('source', sourceFilter);
      if (dateFrom) params.set('date_from', dateFrom);
      if (dateTo) params.set('date_to', dateTo);

      const res = await fetch(`${API_URL}/admin/audit-log?${params.toString()}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (!res.ok) {
        setFetchError(`Failed to load audit log (${res.status})`);
        return;
      }

      const data = (await res.json()) as AuditLogResponse;
      setEntries(data.entries ?? []);
      setTotal(data.total ?? 0);
    } catch {
      setFetchError('Failed to load audit log. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [supabase, API_URL, offset, sourceFilter, dateFrom, dateTo]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  const handleFilterChange = () => {
    setOffset(0);
    fetchEntries();
  };

  const totalPages = Math.ceil(total / LIMIT);
  const currentPage = Math.floor(offset / LIMIT) + 1;

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Audit Log</h1>
          <p className="mt-1 text-sm text-gray-400">All admin actions across the platform.</p>
        </div>
        <button
          type="button"
          onClick={() => fetchEntries()}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-600 transition-colors"
          aria-label="Refresh audit log"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3 mb-5 bg-gray-900 border border-gray-700 rounded-xl p-4">
        <div className="flex items-center gap-2">
          <label htmlFor="source-filter" className="text-sm text-gray-400">Source</label>
          <select
            id="source-filter"
            value={sourceFilter}
            onChange={(e) => { setSourceFilter(e.target.value); setOffset(0); }}
            className="bg-gray-800 text-gray-100 text-sm rounded-lg px-3 py-1.5 border border-gray-600 outline-none focus:ring-1 focus:ring-indigo-500"
          >
            {SOURCE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="date-from" className="text-sm text-gray-400">From</label>
          <input
            id="date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setOffset(0); }}
            className="bg-gray-800 text-gray-100 text-sm rounded-lg px-3 py-1.5 border border-gray-600 outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="date-to" className="text-sm text-gray-400">To</label>
          <input
            id="date-to"
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setOffset(0); }}
            className="bg-gray-800 text-gray-100 text-sm rounded-lg px-3 py-1.5 border border-gray-600 outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
        <button
          type="button"
          onClick={handleFilterChange}
          className="px-4 py-1.5 text-sm font-medium bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors"
        >
          Apply
        </button>
      </div>

      {/* Content area */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-gray-400">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-500 border-t-transparent" />
        </div>
      ) : fetchError ? (
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <p className="text-red-400 text-sm">{fetchError}</p>
          <button
            type="button"
            onClick={() => fetchEntries()}
            className="px-4 py-2 bg-gray-800 text-gray-200 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      ) : entries.length === 0 ? (
        <div className="flex items-center justify-center py-20 text-gray-500 text-sm">
          No audit entries yet.
        </div>
      ) : (
        <>
          {/* Table */}
          <div className="overflow-x-auto rounded-xl border border-gray-700">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-800 text-gray-400 text-left">
                  <th className="px-4 py-3 font-medium">Timestamp</th>
                  <th className="px-4 py-3 font-medium">Admin</th>
                  <th className="px-4 py-3 font-medium">Action</th>
                  <th className="px-4 py-3 font-medium">Target</th>
                  <th className="px-4 py-3 font-medium">Source</th>
                  <th className="px-4 py-3 font-medium">Details</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <React.Fragment key={entry.id}>
                    <tr className="border-t border-gray-700 hover:bg-gray-800/50 transition-colors">
                      <td className="px-4 py-3 text-gray-300 whitespace-nowrap">
                        {new Date(entry.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-gray-300 truncate max-w-[180px]">
                        {entry.admin_email}
                      </td>
                      <td className="px-4 py-3 text-gray-100 font-medium">{entry.action}</td>
                      <td className="px-4 py-3 text-gray-400">
                        {entry.target_type && (
                          <span>
                            {entry.target_type}
                            {entry.target_id ? ` #${entry.target_id}` : ''}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                            sourceBadgeClass[entry.source] ?? 'bg-gray-700 text-gray-300'
                          }`}
                        >
                          {entry.source.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {entry.details && Object.keys(entry.details).length > 0 && (
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedId(expandedId === entry.id ? null : entry.id)
                            }
                            className="text-xs text-indigo-400 hover:text-indigo-300 underline"
                          >
                            {expandedId === entry.id ? 'Hide' : 'Show'}
                          </button>
                        )}
                      </td>
                    </tr>
                    {expandedId === entry.id && entry.details && (
                      <tr className="border-t border-gray-700 bg-gray-900">
                        <td colSpan={6} className="px-4 py-3">
                          <pre className="text-xs text-gray-300 overflow-x-auto bg-gray-800 rounded-lg p-3">
                            {JSON.stringify(entry.details, null, 2)}
                          </pre>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4 text-sm text-gray-400">
            <span>
              {total} total {total === 1 ? 'entry' : 'entries'} — page {currentPage} of {Math.max(1, totalPages)}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setOffset(Math.max(0, offset - LIMIT))}
                disabled={offset === 0}
                className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed border border-gray-600 transition-colors"
                aria-label="Previous page"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                type="button"
                onClick={() => setOffset(offset + LIMIT)}
                disabled={offset + LIMIT >= total}
                className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed border border-gray-600 transition-colors"
                aria-label="Next page"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
