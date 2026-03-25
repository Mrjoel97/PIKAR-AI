'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useCallback, useEffect, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Shape of a single row from GET /admin/roles/permissions */
interface RolePermissionRow {
  role: string;
  section: string;
  allowed_actions: string[];
}

/** Props for RolePermissionsTab */
export interface RolePermissionsTabProps {
  /** Supabase access_token for Authorization header */
  token: string;
  /** Current user's admin role — determines if editing is allowed */
  adminRole: string;
}

/** The 4 admin roles displayed as columns */
const ROLES = ['junior_admin', 'senior_admin', 'admin', 'super_admin'] as const;
type RoleCol = (typeof ROLES)[number];

/** Role column header colors */
const ROLE_HEADER_COLORS: Record<RoleCol, string> = {
  junior_admin: 'text-blue-400',
  senior_admin: 'text-amber-400',
  admin: 'text-indigo-400',
  super_admin: 'text-rose-400',
};

/** The 10 sections displayed as rows */
const SECTIONS = [
  'users',
  'monitoring',
  'analytics',
  'approvals',
  'config',
  'knowledge',
  'billing',
  'integrations',
  'settings',
  'audit_log',
] as const;
type Section = (typeof SECTIONS)[number];

/** The 3 actions available per cell */
const ACTIONS = ['read', 'write', 'manage'] as const;
type Action = (typeof ACTIONS)[number];

/**
 * Matrix key is `${role}::${section}` → Set of allowed actions.
 * This structure allows O(1) lookup for cell rendering.
 */
type PermMatrix = Record<string, Set<Action>>;

/** Convert API rows to the matrix structure */
function rowsToMatrix(rows: RolePermissionRow[]): PermMatrix {
  const matrix: PermMatrix = {};
  // Pre-populate all combinations so unset cells render empty sets
  for (const role of ROLES) {
    for (const section of SECTIONS) {
      matrix[`${role}::${section}`] = new Set<Action>();
    }
  }
  for (const row of rows) {
    const key = `${row.role}::${row.section}`;
    matrix[key] = new Set(row.allowed_actions as Action[]);
  }
  return matrix;
}

/**
 * RolePermissionsTab renders an editable role × section × action matrix.
 *
 * Rows are sections, columns are the 4 admin roles. Each cell has 3 checkboxes
 * (read/write/manage). Changes call PUT /admin/roles/permissions with optimistic
 * update, reverting on failure.
 * Super admin only: non-super_admin users see read-only view.
 */
export function RolePermissionsTab({ token, adminRole }: RolePermissionsTabProps) {
  const isSuperAdmin = adminRole === 'super_admin';

  const [matrix, setMatrix] = useState<PermMatrix>({});
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  // ─── fetchPermissions ─────────────────────────────────────────────────────

  const fetchPermissions = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const res = await fetch(`${API_URL}/admin/roles/permissions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        setFetchError(`Failed to load role permissions (${res.status})`);
        return;
      }
      const data = (await res.json()) as RolePermissionRow[];
      setMatrix(rowsToMatrix(data));
    } catch {
      setFetchError('Failed to load role permissions. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchPermissions();
  }, [fetchPermissions]);

  // ─── handleCheckboxChange ─────────────────────────────────────────────────

  const handleCheckboxChange = useCallback(
    async (role: RoleCol, section: Section, action: Action, checked: boolean) => {
      if (!isSuperAdmin) return;
      const key = `${role}::${section}`;
      setSavingKey(key);
      setSaveError(null);

      // Compute new action set
      const current = new Set(matrix[key] ?? []);
      if (checked) {
        current.add(action);
      } else {
        current.delete(action);
      }
      const newActions = Array.from(current);

      // Optimistic update
      setMatrix((prev) => {
        const next = { ...prev };
        next[key] = new Set(current);
        return next;
      });

      try {
        const res = await fetch(`${API_URL}/admin/roles/permissions`, {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ role, section, allowed_actions: newActions }),
        });
        if (!res.ok) {
          setSaveError(`Save failed (${res.status})`);
          // Revert
          fetchPermissions();
        }
      } catch {
        setSaveError('Save failed. Check that the backend is running.');
        fetchPermissions();
      } finally {
        setSavingKey(null);
      }
    },
    [isSuperAdmin, matrix, token, fetchPermissions],
  );

  // ─── Loading / error states ───────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="bg-gray-800 rounded-lg border border-gray-700 h-10 animate-pulse" />
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
          onClick={fetchPermissions}
          className="px-4 py-2 bg-gray-800 text-gray-200 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Read-only banner for non-super_admin */}
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

      {/* Matrix table */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-x-auto">
        <table className="w-full text-sm min-w-max">
          <thead>
            <tr className="border-b border-gray-700">
              {/* Section label column */}
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider w-32">
                Section
              </th>
              {/* Role columns — each role has 3 sub-columns */}
              {ROLES.map((role) => (
                <th
                  key={role}
                  colSpan={3}
                  className="text-center px-2 py-3 text-xs font-semibold uppercase tracking-wider border-l border-gray-700"
                >
                  <span className={ROLE_HEADER_COLORS[role]}>{role.replace('_', ' ')}</span>
                </th>
              ))}
            </tr>
            {/* Sub-header: read / write / manage per role */}
            <tr className="border-b border-gray-700">
              <th className="px-4 py-2" />
              {ROLES.map((role) =>
                ACTIONS.map((action) => (
                  <th
                    key={`${role}-${action}`}
                    className="px-2 py-2 text-center text-xs text-gray-500 font-normal border-l first:border-l border-gray-700"
                  >
                    {action}
                  </th>
                )),
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {SECTIONS.map((section) => (
              <tr key={section} className="hover:bg-gray-750">
                {/* Section label */}
                <td className="px-4 py-3 text-gray-300 text-xs font-medium capitalize whitespace-nowrap">
                  {section.replace('_', ' ')}
                </td>
                {/* Checkboxes: role × action */}
                {ROLES.map((role) => {
                  const key = `${role}::${section}`;
                  const actionSet = matrix[key] ?? new Set<Action>();
                  const isSaving = savingKey === key;
                  return ACTIONS.map((action) => (
                    <td
                      key={`${role}-${action}`}
                      className="px-2 py-3 text-center border-l border-gray-700"
                    >
                      <input
                        type="checkbox"
                        checked={actionSet.has(action)}
                        onChange={(e) =>
                          handleCheckboxChange(role, section, action, e.target.checked)
                        }
                        disabled={!isSuperAdmin || isSaving}
                        className="h-3.5 w-3.5 rounded border-gray-500 bg-gray-700 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-gray-800 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                        aria-label={`${role} ${section} ${action}`}
                      />
                    </td>
                  ));
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-500">
        Changes take effect immediately. Each cell controls{' '}
        <span className="text-gray-400">read</span> /{' '}
        <span className="text-gray-400">write</span> /{' '}
        <span className="text-gray-400">manage</span> access per section.
      </p>
    </div>
  );
}
