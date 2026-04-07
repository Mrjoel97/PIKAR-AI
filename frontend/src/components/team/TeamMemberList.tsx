'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview TeamMemberList — table of workspace members with role management.
 *
 * Fetches workspace members from the backend on mount and renders a table with:
 * - Member name / email
 * - Role (editable via RoleDropdown for admins)
 * - Joined date
 * - Remove action (admin-only, owner-protected)
 *
 * All mutations refetch the member list to keep state in sync with the server.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { fetchWithAuth } from '@/services/api';
import { type WorkspaceMember, type WorkspaceRole } from '@/contexts/WorkspaceContext';
import { RoleDropdown } from '@/components/team/RoleDropdown';
import { PermissionGate } from '@/components/ui/PermissionGate';

// AUTH-03 (Phase 49 Plan 03): visible UI labels for the canonical role taxonomy.
// Schema identifier "editor" is rendered as "Member" to match v7.0 ROADMAP wording.
const ROLE_DISPLAY_LABELS: Record<string, string> = {
  admin: 'Admin',
  editor: 'Member',
  viewer: 'Viewer',
};

// ============================================================================
// Types
// ============================================================================

interface TeamMemberListProps {
  /** Workspace ID used to scope member list and mutation requests. */
  workspaceId: string;
  /** Current user's role — controls whether role dropdowns are interactive. */
  currentUserRole: WorkspaceRole;
  /** Owner's user_id — the owner row renders static "Owner (Admin)" text. */
  ownerId: string;
}

// ============================================================================
// Helpers
// ============================================================================

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return iso;
  }
}

// ============================================================================
// Loading skeleton
// ============================================================================

function MemberRowSkeleton() {
  return (
    <tr className="animate-pulse">
      {[1, 2, 3, 4].map((i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 rounded bg-slate-100" />
        </td>
      ))}
    </tr>
  );
}

// ============================================================================
// Component
// ============================================================================

/**
 * Renders a table of all workspace members with role dropdowns and remove
 * buttons for admins. Viewer members see the table but cannot modify roles.
 */
export function TeamMemberList({
  workspaceId,
  currentUserRole,
  ownerId,
}: TeamMemberListProps) {
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [confirmRemoveId, setConfirmRemoveId] = useState<string | null>(null);

  const isAdmin = currentUserRole === 'admin';

  // ── Fetch members ─────────────────────────────────────────────────────────

  const fetchMembers = useCallback(async () => {
    try {
      const response = await fetchWithAuth('/teams/members');
      if (!response.ok) {
        setError('Failed to load team members.');
        return;
      }
      const data: WorkspaceMember[] = await response.json();
      setMembers(data);
      setError(null);
    } catch {
      setError('Network error — could not load team members.');
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchMembers().finally(() => setLoading(false));
  }, [fetchMembers, workspaceId]);

  // ── Role change ──────────────────────────────────────────────────────────

  const handleRoleChange = async (memberId: string, newRole: string) => {
    try {
      const response = await fetchWithAuth(
        `/teams/members/${memberId}/role`,
        {
          method: 'PATCH',
          body: JSON.stringify({ role: newRole }),
        },
      );
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const message =
          typeof data?.detail === 'string'
            ? data.detail
            : 'Failed to update role.';
        toast.error(message);
        throw new Error(message);
      }
      const displayLabel = ROLE_DISPLAY_LABELS[newRole] ?? newRole;
      toast.success(`Role updated to ${displayLabel}`);
      await fetchMembers();
    } catch (err) {
      if (err instanceof Error && err.message) {
        // Already toasted above for !response.ok; re-throw so RoleDropdown
        // knows the change failed and resets its pending state.
        throw err;
      }
      toast.error('Failed to update role. Please try again.');
      throw err;
    }
  };

  // ── Remove member ────────────────────────────────────────────────────────

  const handleRemove = async (memberId: string) => {
    setRemovingId(memberId);
    try {
      const response = await fetchWithAuth(`/teams/members/${memberId}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const message =
          typeof data?.detail === 'string'
            ? data.detail
            : 'Failed to remove member.';
        setError(message);
        return;
      }
      await fetchMembers();
    } catch {
      setError('Network error — could not remove member.');
    } finally {
      setRemovingId(null);
      setConfirmRemoveId(null);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  if (error) {
    return (
      <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
        {error}
      </p>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 bg-slate-50">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
              Member
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
              Role
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
              Joined
            </th>
            {isAdmin && (
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                Actions
              </th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50">
          {loading ? (
            <>
              <MemberRowSkeleton />
              <MemberRowSkeleton />
              <MemberRowSkeleton />
            </>
          ) : members.length === 0 ? (
            <tr>
              <td
                colSpan={isAdmin ? 4 : 3}
                className="px-4 py-6 text-center text-sm text-slate-400"
              >
                No members yet.
              </td>
            </tr>
          ) : (
            members.map((member) => {
              const isOwnerRow = member.user_id === ownerId;
              const isRemoving = removingId === member.user_id;
              const awaitingConfirm = confirmRemoveId === member.user_id;

              return (
                <tr
                  key={member.user_id}
                  data-testid="team-member-row"
                  data-user-id={member.user_id}
                  className="group transition-colors hover:bg-slate-50"
                >
                  {/* Name / Email */}
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-800">
                      {member.display_name ?? member.email}
                    </div>
                    {member.display_name && (
                      <div className="text-xs text-slate-400">{member.email}</div>
                    )}
                  </td>

                  {/* Role */}
                  <td
                    className="px-4 py-3"
                    data-testid={`role-dropdown-${member.user_id}`}
                  >
                    <RoleDropdown
                      currentRole={member.role}
                      memberId={member.user_id}
                      isOwner={isOwnerRow}
                      disabled={!isAdmin}
                      onRoleChange={handleRoleChange}
                    />
                  </td>

                  {/* Joined */}
                  <td className="px-4 py-3 text-slate-500">
                    {formatDate(member.joined_at)}
                  </td>

                  {/* Actions (admin only) */}
                  {isAdmin && (
                    <td className="px-4 py-3">
                      {!isOwnerRow && (
                        <PermissionGate require="manage-team">
                          {awaitingConfirm ? (
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-slate-500">Remove?</span>
                              <button
                                type="button"
                                onClick={() => handleRemove(member.user_id)}
                                disabled={isRemoving}
                                className="rounded-lg bg-red-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-60 transition-colors"
                              >
                                {isRemoving ? 'Removing…' : 'Confirm'}
                              </button>
                              <button
                                type="button"
                                onClick={() => setConfirmRemoveId(null)}
                                className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:border-slate-300 transition-colors"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              type="button"
                              onClick={() => setConfirmRemoveId(member.user_id)}
                              className="inline-flex items-center gap-1 rounded-lg border border-transparent px-2 py-1 text-xs font-medium text-slate-400 opacity-0 group-hover:opacity-100 hover:border-red-200 hover:text-red-600 focus:opacity-100 transition-all"
                              aria-label={`Remove ${member.display_name ?? member.email}`}
                            >
                              {/* Trash icon */}
                              <svg
                                className="h-3.5 w-3.5"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                strokeWidth={2}
                                aria-hidden="true"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M9 7V4h6v3M3 7h18"
                                />
                              </svg>
                              Remove
                            </button>
                          )}
                        </PermissionGate>
                      )}
                    </td>
                  )}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

export default TeamMemberList;
