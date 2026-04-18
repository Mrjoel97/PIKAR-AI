'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useCallback, useEffect, useState } from 'react';
import { Loader2, Plus, Trash2 } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Valid admin role values */
type AdminRole = 'junior_admin' | 'senior_admin' | 'admin' | 'super_admin';

/** Shape of a single admin role row from GET /admin/roles */
interface AdminRoleRow {
  user_id: string;
  role: AdminRole;
  created_at: string;
  updated_at: string;
}

/** Props for RoleManagementTab */
export interface RoleManagementTabProps {
  /** Supabase access_token for Authorization header */
  token: string;
  /** Current user's admin role — determines if CRUD is allowed */
  adminRole: string;
}

/** Role badge color classes */
const ROLE_BADGE: Record<AdminRole, string> = {
  junior_admin: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  senior_admin: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  admin: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30',
  super_admin: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
};

const ROLE_OPTIONS: AdminRole[] = ['junior_admin', 'senior_admin', 'admin', 'super_admin'];

/** Truncate a UUID to first 8 chars */
function truncateId(id: string): string {
  return id.length > 8 ? `${id.slice(0, 8)}…` : id;
}

/** Format a date string to a short readable form */
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/**
 * RoleManagementTab shows admin accounts with role assignment.
 *
 * Full CRUD is super_admin only. Non-super_admin users see a read-only table
 * with an informational message.
 */
export function RoleManagementTab({ token, adminRole }: RoleManagementTabProps) {
  const isSuperAdmin = adminRole === 'super_admin';

  const [roles, setRoles] = useState<AdminRoleRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  /** Add admin form state */
  const [showAddForm, setShowAddForm] = useState(false);
  const [newUserId, setNewUserId] = useState('');
  const [newRole, setNewRole] = useState<AdminRole>('junior_admin');
  const [isSubmitting, setIsSubmitting] = useState(false);

  /** Per-row role change tracking */
  const [changingRoleId, setChangingRoleId] = useState<string | null>(null);

  // ─── fetchRoles ───────────────────────────────────────────────────────────

  const fetchRoles = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const res = await fetch(`${API_URL}/admin/roles`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        setFetchError(`Failed to load admin roles (${res.status})`);
        return;
      }
      const data = (await res.json()) as AdminRoleRow[];
      setRoles(data);
    } catch {
      setFetchError('Failed to load admin roles. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchRoles();
  }, [fetchRoles]);

  // ─── handleAddAdmin ───────────────────────────────────────────────────────

  const handleAddAdmin = useCallback(async () => {
    if (!newUserId.trim()) return;
    setIsSubmitting(true);
    setSaveError(null);
    try {
      const res = await fetch(`${API_URL}/admin/roles`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: newUserId.trim(), role: newRole }),
      });
      if (!res.ok) {
        setSaveError(`Failed to add admin (${res.status})`);
        return;
      }
      setNewUserId('');
      setNewRole('junior_admin');
      setShowAddForm(false);
      await fetchRoles();
    } catch {
      setSaveError('Failed to add admin. Check that the backend is running.');
    } finally {
      setIsSubmitting(false);
    }
  }, [token, newUserId, newRole, fetchRoles]);

  // ─── handleRoleChange ─────────────────────────────────────────────────────

  const handleRoleChange = useCallback(
    async (userId: string, newRoleValue: AdminRole) => {
      setChangingRoleId(userId);
      setSaveError(null);
      try {
        const res = await fetch(`${API_URL}/admin/roles`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ user_id: userId, role: newRoleValue }),
        });
        if (!res.ok) {
          setSaveError(`Failed to update role (${res.status})`);
          return;
        }
        // Optimistic update
        setRoles((prev) =>
          prev.map((r) => (r.user_id === userId ? { ...r, role: newRoleValue } : r)),
        );
      } catch {
        setSaveError('Failed to update role. Check that the backend is running.');
      } finally {
        setChangingRoleId(null);
      }
    },
    [token],
  );

  // ─── handleDelete ─────────────────────────────────────────────────────────

  const handleDelete = useCallback(
    async (userId: string) => {
      const confirmed = window.confirm(`Remove admin access for user ${truncateId(userId)}?`);
      if (!confirmed) return;
      setSaveError(null);
      try {
        const res = await fetch(`${API_URL}/admin/roles/${userId}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          setSaveError(`Failed to remove admin (${res.status})`);
          return;
        }
        setRoles((prev) => prev.filter((r) => r.user_id !== userId));
      } catch {
        setSaveError('Failed to remove admin. Check that the backend is running.');
      }
    },
    [token],
  );

  // ─── Loading / error states ───────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-gray-800 rounded-lg border border-gray-700 h-12 animate-pulse" />
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
          onClick={fetchRoles}
          className="px-4 py-2 bg-gray-800 text-gray-200 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Super admin gate message */}
      {!isSuperAdmin && (
        <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm">
          Role management requires super admin access. You are viewing in read-only mode.
        </div>
      )}

      {/* Save error banner */}
      {saveError && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <span className="flex-1">{saveError}</span>
          <button
            type="button"
            onClick={() => setSaveError(null)}
            className="opacity-60 hover:opacity-100"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      {/* Header with Add Admin button */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">
          <span className="text-gray-200 font-semibold">{roles.length}</span> admin account
          {roles.length !== 1 ? 's' : ''}
        </p>
        {isSuperAdmin && (
          <button
            type="button"
            onClick={() => setShowAddForm((prev) => !prev)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-600 transition-colors"
          >
            <Plus size={14} />
            Add Admin
          </button>
        )}
      </div>

      {/* Add Admin inline form */}
      {isSuperAdmin && showAddForm && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-3">
          <p className="text-sm font-medium text-gray-200">Add Admin Account</p>
          <div className="flex flex-wrap gap-3">
            <div className="flex-1 min-w-48">
              <label htmlFor="new-user-id" className="text-xs text-gray-400 mb-1 block">
                User ID (UUID)
              </label>
              <input
                id="new-user-id"
                type="text"
                value={newUserId}
                onChange={(e) => setNewUserId(e.target.value)}
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                className="w-full text-sm bg-gray-700 border border-gray-600 text-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-gray-500 font-mono"
              />
            </div>
            <div>
              <label htmlFor="new-role" className="text-xs text-gray-400 mb-1 block">
                Role
              </label>
              <select
                id="new-role"
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as AdminRole)}
                className="text-sm bg-gray-700 border border-gray-600 text-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {ROLE_OPTIONS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleAddAdmin}
              disabled={isSubmitting || !newUserId.trim()}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
            >
              {isSubmitting ? <Loader2 size={12} className="animate-spin" /> : null}
              Add
            </button>
            <button
              type="button"
              onClick={() => {
                setShowAddForm(false);
                setNewUserId('');
                setNewRole('junior_admin');
              }}
              className="px-3 py-1.5 text-sm text-gray-400 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Roles table */}
      {roles.length === 0 ? (
        <div className="bg-gray-800 border border-gray-700 rounded-lg py-12 text-center">
          <p className="text-gray-400 text-sm">No admin accounts configured.</p>
        </div>
      ) : (
        <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  User ID
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Role
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Created
                </th>
                {isSuperAdmin && (
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {roles.map((row) => {
                const badgeClass =
                  ROLE_BADGE[row.role] ?? 'bg-gray-500/15 text-gray-400 border-gray-500/30';
                const isChanging = changingRoleId === row.user_id;
                return (
                  <tr key={row.user_id} className="hover:bg-gray-750">
                    {/* User ID */}
                    <td className="px-4 py-3">
                      <span
                        className="text-gray-400 font-mono text-xs cursor-help"
                        title={row.user_id}
                      >
                        {truncateId(row.user_id)}
                      </span>
                    </td>

                    {/* Role — clickable dropdown for super_admin */}
                    <td className="px-4 py-3">
                      {isSuperAdmin ? (
                        <select
                          value={row.role}
                          onChange={(e) =>
                            handleRoleChange(row.user_id, e.target.value as AdminRole)
                          }
                          disabled={isChanging}
                          className={`text-xs font-medium rounded-full px-2.5 py-0.5 border focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-60 bg-transparent cursor-pointer ${badgeClass}`}
                          aria-label={`Role for ${truncateId(row.user_id)}`}
                        >
                          {ROLE_OPTIONS.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${badgeClass}`}
                        >
                          {row.role}
                        </span>
                      )}
                    </td>

                    {/* Created date */}
                    <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                      {formatDate(row.created_at)}
                    </td>

                    {/* Delete action — super_admin only */}
                    {isSuperAdmin && (
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          onClick={() => handleDelete(row.user_id)}
                          className="p-1.5 text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                          aria-label={`Remove admin ${truncateId(row.user_id)}`}
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    )}
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
