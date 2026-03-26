'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useCallback, useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { AutonomyTierTab } from '@/components/admin/settings/AutonomyTierTab';
import { RoleManagementTab } from '@/components/admin/settings/RoleManagementTab';
import { RolePermissionsTab } from '@/components/admin/settings/RolePermissionsTab';

/** Tab identifiers */
type SettingsTab = 'autonomy' | 'roles' | 'permissions';

/** Response shape from GET /admin/check-access */
interface CheckAccessResponse {
  access: boolean;
  email?: string;
  admin_role?: string;
}

const TAB_LABELS: { id: SettingsTab; label: string }[] = [
  { id: 'autonomy', label: 'Autonomy Tiers' },
  { id: 'roles', label: 'Role Management' },
  { id: 'permissions', label: 'Role Permissions' },
];

/**
 * SettingsPage renders /admin/settings with three tabs:
 * - Autonomy Tiers: grouped tool permission editor (58+ actions)
 * - Role Management: admin account CRUD (super_admin only)
 * - Role Permissions: role × section × action matrix (super_admin only)
 *
 * Fetches the current user's admin_role from /admin/check-access to gate
 * super_admin-only tabs. Passes the Bearer token to each tab component.
 */
export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('autonomy');
  const [token, setToken] = useState<string | null>(null);
  const [adminRole, setAdminRole] = useState<string>('junior_admin');
  const [isLoadingSession, setIsLoadingSession] = useState(true);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const supabase = createClient();
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // ─── Load session + admin role ────────────────────────────────────────────

  const loadSession = useCallback(async () => {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setSessionError('Not authenticated');
        setIsLoadingSession(false);
        return;
      }

      setToken(session.access_token);

      // Fetch admin role from check-access
      const res = await fetch(`${API_URL}/admin/check-access`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
        cache: 'no-store',
      });

      if (res.ok) {
        const data = (await res.json()) as CheckAccessResponse;
        if (data.admin_role) {
          setAdminRole(data.admin_role);
        }
      }
    } catch {
      setSessionError('Failed to load session. Check that the backend is running.');
    } finally {
      setIsLoadingSession(false);
    }
  }, [supabase, API_URL]);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Admin Settings</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Manage autonomy tiers, admin roles, and role-based permissions
        </p>
      </div>

      {/* Session error */}
      {sessionError && (
        <div className="mb-6 flex items-center gap-3 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {sessionError}
        </div>
      )}

      {/* Tab bar */}
      <div className="mb-6">
        <div className="inline-flex bg-gray-800 rounded-lg p-1 gap-1">
          {TAB_LABELS.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActiveTab(id)}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === id
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Loading skeleton (waiting for session) */}
      {isLoadingSession && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="bg-gray-800 rounded-lg border border-gray-700 h-12 animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Tab content */}
      {!isLoadingSession && !sessionError && token && (
        <>
          {activeTab === 'autonomy' && <AutonomyTierTab token={token} />}
          {activeTab === 'roles' && (
            <RoleManagementTab token={token} adminRole={adminRole} />
          )}
          {activeTab === 'permissions' && (
            <RolePermissionsTab token={token} adminRole={adminRole} />
          )}
        </>
      )}
    </div>
  );
}
