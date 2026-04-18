'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useCallback, useEffect, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Autonomy level values */
type AutonomyLevel = 'auto' | 'confirm' | 'blocked';

/** Shape of a single permission from GET /admin/config/permissions */
interface Permission {
  action_name: string;
  action_category: string;
  autonomy_level: AutonomyLevel;
  risk_level: string;
  description: string | null;
}

/** Props for AutonomyTable */
export interface AutonomyTableProps {
  /** Supabase access_token for Authorization header */
  token: string;
}

/** Color classes for each autonomy tier */
const TIER_COLORS: Record<AutonomyLevel, string> = {
  auto: 'text-emerald-400',
  confirm: 'text-amber-400',
  blocked: 'text-rose-400',
};

/** Background pill classes for tier select */
const TIER_BG: Record<AutonomyLevel, string> = {
  auto: 'bg-emerald-500/10 border-emerald-500/30',
  confirm: 'bg-amber-500/10 border-amber-500/30',
  blocked: 'bg-rose-500/10 border-rose-500/30',
};

/**
 * AutonomyTable renders a grouped table of admin action permissions.
 *
 * Each row has a tier selector dropdown (auto / confirm / blocked).
 * Changes send PUT /admin/config/permissions/{action_name} with a
 * window.confirm dialog before committing.
 */
export function AutonomyTable({ token }: AutonomyTableProps) {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [savingAction, setSavingAction] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  // ─── fetchPermissions ─────────────────────────────────────────────────────

  const fetchPermissions = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const res = await fetch(`${API_URL}/admin/config/permissions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        setFetchError(`Failed to load permissions (${res.status})`);
        return;
      }
      const data = (await res.json()) as Permission[];
      setPermissions(data);
    } catch {
      setFetchError('Failed to load permissions. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchPermissions();
  }, [fetchPermissions]);

  // ─── handleTierChange ─────────────────────────────────────────────────────

  const handleTierChange = useCallback(
    async (actionName: string, newLevel: AutonomyLevel) => {
      const confirmed = window.confirm(
        `Change autonomy tier for "${actionName}" to "${newLevel}"?`,
      );
      if (!confirmed) return;

      setSavingAction(actionName);
      setSaveError(null);
      try {
        const res = await fetch(
          `${API_URL}/admin/config/permissions/${actionName}`,
          {
            method: 'PUT',
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ autonomy_level: newLevel }),
          },
        );
        if (!res.ok) {
          setSaveError(`Save failed (${res.status})`);
          return;
        }
        // Optimistic update
        setPermissions((prev) =>
          prev.map((p) =>
            p.action_name === actionName ? { ...p, autonomy_level: newLevel } : p,
          ),
        );
      } catch {
        setSaveError('Save failed. Check that the backend is running.');
      } finally {
        setSavingAction(null);
      }
    },
    [token],
  );

  // ─── Group permissions by category ───────────────────────────────────────

  const grouped = permissions.reduce<Record<string, Permission[]>>((acc, p) => {
    const cat = p.action_category || 'Uncategorized';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(p);
    return acc;
  }, {});

  const categories = Object.keys(grouped).sort();

  // ─── Render ───────────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="bg-gray-800 rounded-lg h-12 animate-pulse" />
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
          onClick={() => { setIsLoading(true); fetchPermissions(); }}
          className="px-4 py-2 bg-gray-800 text-gray-200 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
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

      {categories.map((category) => (
        <div key={category}>
          {/* Category header */}
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 px-1">
            {category}
          </h3>

          {/* Table */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-400">
                    Action
                  </th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-400">
                    Risk
                  </th>
                  <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-400">
                    Tier
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {grouped[category].map((permission) => {
                  const tier = permission.autonomy_level;
                  return (
                    <tr key={permission.action_name} className="hover:bg-gray-750">
                      <td className="px-4 py-3">
                        <p className="text-gray-100 font-medium">
                          {permission.action_name}
                        </p>
                        {permission.description && (
                          <p className="text-xs text-gray-500 mt-0.5">
                            {permission.description}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs text-gray-400 capitalize">
                          {permission.risk_level}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={tier}
                          onChange={(e) =>
                            handleTierChange(
                              permission.action_name,
                              e.target.value as AutonomyLevel,
                            )
                          }
                          disabled={savingAction === permission.action_name}
                          className={`text-xs font-medium rounded-lg px-2.5 py-1 border focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed bg-transparent cursor-pointer transition-colors ${TIER_BG[tier]} ${TIER_COLORS[tier]}`}
                          aria-label={`Autonomy tier for ${permission.action_name}`}
                        >
                          <option value="auto">auto</option>
                          <option value="confirm">confirm</option>
                          <option value="blocked">blocked</option>
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {permissions.length === 0 && (
        <div className="text-center py-12 text-gray-500 text-sm">
          No permissions configured.
        </div>
      )}
    </div>
  );
}
