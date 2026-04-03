'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview PermissionGate — role-based UI access control wrapper.
 *
 * Conditionally renders or disables children based on the current user's
 * workspace role. Solo users (no workspace) always pass through.
 *
 * Usage:
 * ```tsx
 * // Hide entirely when permission denied
 * <PermissionGate require="manage-team" fallback="hide">
 *   <InviteLinkGenerator workspaceId={id} />
 * </PermissionGate>
 *
 * // Render disabled with tooltip (default)
 * <PermissionGate require="edit">
 *   <button onClick={handleCreate}>Create Initiative</button>
 * </PermissionGate>
 * ```
 */

import React, { useState } from 'react';
import { useWorkspace } from '@/contexts/WorkspaceContext';

// ============================================================================
// Types
// ============================================================================

export interface PermissionGateProps {
  /** What permission level is required to interact with the children. */
  require: 'edit' | 'manage-team';
  /** Content to render (or gate) based on permission. */
  children: React.ReactNode;
  /**
   * Behavior when permission is denied:
   * - 'hide'    — removes children from the DOM entirely
   * - 'disable' — renders children with a semi-transparent overlay and tooltip (default)
   */
  fallback?: 'hide' | 'disable';
  /** Custom message shown in the tooltip when disabled. */
  deniedMessage?: string;
}

// ============================================================================
// Component
// ============================================================================

const DEFAULT_DENIED_MESSAGE = 'Contact your workspace admin to perform this action';

/**
 * Wraps children with role-based access control.
 *
 * During the initial workspace load (`ready === false`), children render
 * normally to avoid a flash of disabled content. Solo users (no workspace)
 * always receive full access.
 */
export function PermissionGate({
  require: requiredPermission,
  children,
  fallback = 'disable',
  deniedMessage = DEFAULT_DENIED_MESSAGE,
}: PermissionGateProps) {
  const { ready, canEdit, canManageTeam } = useWorkspace();
  const [tooltipVisible, setTooltipVisible] = useState(false);

  // During loading or solo-user passthrough, render normally.
  if (!ready) {
    return <>{children}</>;
  }

  const hasPermission =
    requiredPermission === 'edit' ? canEdit : canManageTeam;

  if (hasPermission) {
    return <>{children}</>;
  }

  // Permission denied — apply fallback behaviour.
  if (fallback === 'hide') {
    return null;
  }

  // Default: 'disable' — render children with an overlay that blocks interaction.
  return (
    <div
      className="relative"
      onMouseEnter={() => setTooltipVisible(true)}
      onMouseLeave={() => setTooltipVisible(false)}
      onFocus={() => setTooltipVisible(true)}
      onBlur={() => setTooltipVisible(false)}
    >
      {/* Children rendered but non-interactive */}
      <div
        className="pointer-events-none opacity-50 select-none"
        aria-disabled="true"
      >
        {children}
      </div>

      {/* Invisible hit-area over the disabled content to capture hover */}
      <div className="absolute inset-0 cursor-not-allowed" />

      {/* Tooltip */}
      {tooltipVisible && (
        <div
          role="tooltip"
          className="absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 rounded-lg bg-slate-800 px-3 py-2 text-xs text-white shadow-lg whitespace-nowrap"
        >
          {deniedMessage}
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
        </div>
      )}
    </div>
  );
}

export default PermissionGate;
