'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useCallback, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import {
  ApprovalQueueTable,
  type ApprovalRow,
} from '@/components/admin/approvals/ApprovalQueueTable';

/** Status filter type */
type StatusFilter = 'ALL' | 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';

/** Auto-refresh interval: 60 seconds */
const REFRESH_INTERVAL_MS = 60_000;

/**
 * ApprovalsPage renders the /admin/approvals dashboard.
 *
 * Displays a cross-user approval queue with status and action-type filters.
 * Approve/Reject override actions call POST /admin/approvals/{id}/override.
 * Polls every 60 seconds for new items.
 */
export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('PENDING');
  const [actionTypeFilter, setActionTypeFilter] = useState('');

  const supabase = createClient();
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // ─── fetchApprovals ───────────────────────────────────────────────────────

  const fetchApprovals = useCallback(async () => {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setFetchError('Not authenticated');
        setIsLoading(false);
        return;
      }

      const params = new URLSearchParams({ limit: '50' });
      if (statusFilter !== 'ALL') params.set('status', statusFilter);
      if (actionTypeFilter.trim()) params.set('action_type', actionTypeFilter.trim());

      const res = await fetch(`${API_URL}/admin/approvals/all?${params.toString()}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (!res.ok) {
        setFetchError(`Failed to load approvals (${res.status})`);
        setIsLoading(false);
        return;
      }

      const json = (await res.json()) as ApprovalRow[];
      setApprovals(json);
      setFetchError(null);
    } catch {
      setFetchError('Failed to load approvals. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [supabase, API_URL, statusFilter, actionTypeFilter]);

  // Initial fetch + 60-second polling
  useEffect(() => {
    setIsLoading(true);
    fetchApprovals();
    const interval = setInterval(fetchApprovals, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchApprovals]);

  // ─── handleOverride ───────────────────────────────────────────────────────

  const handleOverride = useCallback(
    async (id: string, decision: 'APPROVED' | 'REJECTED', reason?: string) => {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setFetchError('Not authenticated');
        return;
      }

      const res = await fetch(`${API_URL}/admin/approvals/${id}/override`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ decision, reason: reason ?? null }),
      });

      if (!res.ok) {
        setFetchError(`Override failed (${res.status})`);
        return;
      }

      // Refetch the list to reflect updated status
      setIsLoading(true);
      await fetchApprovals();
    },
    [supabase, API_URL, fetchApprovals],
  );

  // ─── Filter change handlers ───────────────────────────────────────────────

  const handleStatusFilterChange = useCallback((status: StatusFilter) => {
    setStatusFilter(status);
  }, []);

  const handleActionTypeFilterChange = useCallback((value: string) => {
    setActionTypeFilter(value);
  }, []);

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Approval Oversight</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Review and override pending approval requests across all users
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setIsLoading(true);
            fetchApprovals();
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-600 transition-colors"
          aria-label="Refresh approvals"
        >
          Refresh
        </button>
      </div>

      {/* Error banner */}
      {fetchError && (
        <div className="mb-4 flex items-center justify-between px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <span>{fetchError}</span>
          <button
            type="button"
            onClick={() => {
              setFetchError(null);
              setIsLoading(true);
              fetchApprovals();
            }}
            className="ml-4 text-xs underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading skeleton (initial load only) */}
      {isLoading && approvals.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="bg-gray-800 rounded-lg border border-gray-700 h-12 animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Approval queue table */}
      {(!isLoading || approvals.length > 0) && (
        <ApprovalQueueTable
          approvals={approvals}
          onOverride={handleOverride}
          isLoading={isLoading}
          statusFilter={statusFilter}
          onStatusFilterChange={handleStatusFilterChange}
          actionTypeFilter={actionTypeFilter}
          onActionTypeFilterChange={handleActionTypeFilterChange}
        />
      )}
    </div>
  );
}
