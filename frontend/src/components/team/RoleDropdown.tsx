'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview RoleDropdown — member role selector for the team settings page.
 *
 * Renders a <select> for changing a workspace member's role. The workspace
 * owner always renders as static "Owner (Admin)" text — their role cannot be
 * changed. External `disabled` prop allows non-admin viewers to see the
 * dropdown in a read-only state.
 */

import React, { useState } from 'react';

// ============================================================================
// Types
// ============================================================================

export interface RoleDropdownProps {
  /** The member's current role string ('admin' | 'editor' | 'viewer'). */
  currentRole: string;
  /** The member's user_id — passed back in the onRoleChange callback. */
  memberId: string;
  /** If true, renders static "Owner (Admin)" text — owner role is immutable. */
  isOwner: boolean;
  /** External disable flag (e.g. the current viewer cannot change roles). */
  disabled?: boolean;
  /** Async callback invoked when the user selects a new role. */
  onRoleChange: (memberId: string, newRole: string) => Promise<void>;
}

const ROLE_LABELS: Record<string, string> = {
  admin: 'Admin',
  editor: 'Editor',
  viewer: 'Viewer',
};

// ============================================================================
// Component
// ============================================================================

/**
 * A controlled role <select> for workspace member role management.
 *
 * Shows a loading spinner inline while the async role change is in-flight.
 * If the member is the workspace owner, renders static text instead of a
 * dropdown because the owner role cannot be changed.
 */
export function RoleDropdown({
  currentRole,
  memberId,
  isOwner,
  disabled = false,
  onRoleChange,
}: RoleDropdownProps) {
  const [pending, setPending] = useState(false);

  // Owner's role cannot be changed — render static badge.
  if (isOwner) {
    return (
      <span className="inline-flex items-center gap-1.5 text-sm text-slate-600 font-medium">
        <span className="inline-block h-2 w-2 rounded-full bg-indigo-500" />
        Owner (Admin)
      </span>
    );
  }

  const handleChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newRole = e.target.value;
    if (newRole === currentRole) return;
    setPending(true);
    try {
      await onRoleChange(memberId, newRole);
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="relative inline-flex items-center gap-1.5">
      <select
        value={currentRole}
        onChange={handleChange}
        disabled={disabled || pending}
        className={[
          'rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-sm text-slate-700',
          'focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'transition-colors',
        ].join(' ')}
        aria-label="Member role"
      >
        <option value="admin">{ROLE_LABELS.admin}</option>
        <option value="editor">{ROLE_LABELS.editor}</option>
        <option value="viewer">{ROLE_LABELS.viewer}</option>
      </select>

      {pending && (
        <svg
          className="h-4 w-4 animate-spin text-indigo-500"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-label="Saving role..."
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      )}
    </div>
  );
}

export default RoleDropdown;
