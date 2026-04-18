'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useState } from 'react';
import { Loader2 } from 'lucide-react';

/** Single approval row from GET /admin/approvals/all */
export interface ApprovalRow {
  id: string;
  action_type: string;
  status: string;
  payload: Record<string, unknown>;
  created_at: string;
  expires_at: string;
  user_id: string | null;
}

/** Status filter options */
type StatusFilter = 'ALL' | 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';

/** Props for ApprovalQueueTable */
export interface ApprovalQueueTableProps {
  /** All approvals to display (pre-filtered by parent page state). */
  approvals: ApprovalRow[];
  /** Called when admin clicks Approve or Reject. */
  onOverride: (id: string, decision: 'APPROVED' | 'REJECTED', reason?: string) => Promise<void>;
  /** Whether the parent page is currently fetching. */
  isLoading: boolean;
  /** Current status filter value (controlled by parent). */
  statusFilter: StatusFilter;
  /** Called when status filter changes. */
  onStatusFilterChange: (status: StatusFilter) => void;
  /** Current action type filter text (controlled by parent). */
  actionTypeFilter: string;
  /** Called when action type filter changes. */
  onActionTypeFilterChange: (value: string) => void;
}

/** Status badge colors */
const STATUS_BADGE: Record<string, string> = {
  PENDING: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  APPROVED: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  REJECTED: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
  EXPIRED: 'bg-gray-500/15 text-gray-400 border-gray-500/30',
};

/** Return a human-readable relative time string */
function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffSec = Math.round(diffMs / 1000);
  const diffMin = Math.round(diffSec / 60);
  const diffHr = Math.round(diffMin / 60);
  const diffDay = Math.round(diffHr / 24);

  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${diffDay}d ago`;
}

/** Returns true if the expiry is within the next 24 hours */
function isExpiringSoon(expiresAt: string): boolean {
  const now = Date.now();
  const expiry = new Date(expiresAt).getTime();
  return expiry > now && expiry - now < 24 * 60 * 60 * 1000;
}

/** Truncate a UUID to first 8 chars */
function truncateId(id: string): string {
  return id.length > 8 ? `${id.slice(0, 8)}…` : id;
}

/**
 * ApprovalQueueTable renders a filterable table of approval requests.
 *
 * Each pending approval has Approve and Reject buttons that open an inline
 * confirmation form with an optional reason textarea before submitting the
 * override.
 */
export function ApprovalQueueTable({
  approvals,
  onOverride,
  isLoading,
  statusFilter,
  onStatusFilterChange,
  actionTypeFilter,
  onActionTypeFilterChange,
}: ApprovalQueueTableProps) {
  /** Track which row has the inline confirm form open and its decision */
  const [confirmState, setConfirmState] = useState<{
    id: string;
    decision: 'APPROVED' | 'REJECTED';
    reason: string;
  } | null>(null);
  /** Track per-row processing state to prevent double-submission */
  const [processingId, setProcessingId] = useState<string | null>(null);

  const STATUS_OPTIONS: StatusFilter[] = ['ALL', 'PENDING', 'APPROVED', 'REJECTED', 'EXPIRED'];

  const handleDecisionClick = (id: string, decision: 'APPROVED' | 'REJECTED') => {
    if (processingId) return;
    setConfirmState({ id, decision, reason: '' });
  };

  const handleSubmitOverride = async () => {
    if (!confirmState || processingId) return;
    const { id, decision, reason } = confirmState;
    setProcessingId(id);
    setConfirmState(null);
    try {
      await onOverride(id, decision, reason || undefined);
    } finally {
      setProcessingId(null);
    }
  };

  const handleCancelOverride = () => {
    setConfirmState(null);
  };

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex flex-wrap gap-3">
        {/* Status dropdown */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="status-filter"
            className="text-xs text-gray-400 font-medium"
          >
            Status
          </label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value as StatusFilter)}
            className="text-sm bg-gray-800 border border-gray-600 text-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s === 'ALL' ? 'All Statuses' : s}
              </option>
            ))}
          </select>
        </div>

        {/* Action type text filter */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="action-type-filter"
            className="text-xs text-gray-400 font-medium"
          >
            Action Type
          </label>
          <input
            id="action-type-filter"
            type="text"
            value={actionTypeFilter}
            onChange={(e) => onActionTypeFilterChange(e.target.value)}
            placeholder="Filter by action…"
            className="text-sm bg-gray-800 border border-gray-600 text-gray-200 rounded-lg px-2.5 py-1.5 w-48 focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-gray-500"
          />
        </div>

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex items-center gap-1.5 text-xs text-gray-400">
            <Loader2 size={12} className="animate-spin" />
            Loading…
          </div>
        )}
      </div>

      {/* Table */}
      {approvals.length === 0 && !isLoading ? (
        <div className="bg-gray-800 border border-gray-700 rounded-lg py-16 text-center">
          <p className="text-gray-400 text-sm">No approvals match the current filters.</p>
        </div>
      ) : (
        <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Action Type
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  User
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Created
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Expires
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {approvals.map((row) => {
                const userId =
                  (row.payload?.requester_user_id as string | undefined) ?? row.user_id ?? '';
                const badgeClass =
                  STATUS_BADGE[row.status] ?? 'bg-gray-500/15 text-gray-400 border-gray-500/30';
                const isConfirming = confirmState?.id === row.id;
                const isProcessing = processingId === row.id;

                return (
                  <tr key={row.id} className="hover:bg-gray-750">
                    {/* Action Type */}
                    <td className="px-4 py-3 text-gray-100 font-medium">{row.action_type}</td>

                    {/* User (truncated UUID with tooltip) */}
                    <td className="px-4 py-3">
                      {userId ? (
                        <span
                          className="text-gray-400 font-mono text-xs cursor-help"
                          title={userId}
                        >
                          {truncateId(userId)}
                        </span>
                      ) : (
                        <span className="text-gray-600 text-xs">—</span>
                      )}
                    </td>

                    {/* Created relative time */}
                    <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                      {relativeTime(row.created_at)}
                    </td>

                    {/* Expires — red if within 24h */}
                    <td className="px-4 py-3 text-xs whitespace-nowrap">
                      <span
                        className={
                          isExpiringSoon(row.expires_at) ? 'text-rose-400' : 'text-gray-400'
                        }
                      >
                        {relativeTime(row.expires_at)}
                      </span>
                    </td>

                    {/* Status badge */}
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${badgeClass}`}
                      >
                        {row.status}
                      </span>
                    </td>

                    {/* Actions — only shown for PENDING */}
                    <td className="px-4 py-3">
                      {row.status === 'PENDING' && !isConfirming && (
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            disabled={isProcessing || !!processingId}
                            onClick={() => handleDecisionClick(row.id, 'APPROVED')}
                            className="px-2.5 py-1 text-xs font-medium text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {isProcessing ? (
                              <Loader2 size={12} className="animate-spin" />
                            ) : (
                              'Approve'
                            )}
                          </button>
                          <button
                            type="button"
                            disabled={isProcessing || !!processingId}
                            onClick={() => handleDecisionClick(row.id, 'REJECTED')}
                            className="px-2.5 py-1 text-xs font-medium text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            Reject
                          </button>
                        </div>
                      )}

                      {/* Inline confirm form */}
                      {row.status === 'PENDING' && isConfirming && confirmState && (
                        <div className="space-y-2 min-w-48">
                          <p className="text-xs text-gray-300 font-medium">
                            {confirmState.decision === 'APPROVED'
                              ? 'Approve this request?'
                              : 'Reject this request?'}
                          </p>
                          <textarea
                            value={confirmState.reason}
                            onChange={(e) =>
                              setConfirmState((prev) =>
                                prev ? { ...prev, reason: e.target.value } : prev,
                              )
                            }
                            placeholder="Optional reason…"
                            rows={2}
                            className="w-full text-xs bg-gray-700 border border-gray-600 text-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none placeholder:text-gray-500"
                          />
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={handleSubmitOverride}
                              className={`px-2.5 py-1 text-xs font-medium rounded-lg transition-colors ${
                                confirmState.decision === 'APPROVED'
                                  ? 'text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30'
                                  : 'text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30'
                              }`}
                            >
                              Confirm
                            </button>
                            <button
                              type="button"
                              onClick={handleCancelOverride}
                              className="px-2.5 py-1 text-xs font-medium text-gray-400 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
