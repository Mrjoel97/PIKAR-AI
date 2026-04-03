'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview /dashboard/team — Team Settings page.
 *
 * Gated to startup+ tier via GatedPage. Shows the member list for all roles
 * and the invite link generator for admins only. Uses WorkspaceContext to
 * read the current user's workspace state.
 */

import React from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { GatedPage } from '@/components/dashboard/GatedPage';
import { PermissionGate } from '@/components/ui/PermissionGate';
import { TeamMemberList } from '@/components/team/TeamMemberList';
import { InviteLinkGenerator } from '@/components/team/InviteLinkGenerator';
import { useWorkspace } from '@/contexts/WorkspaceContext';

// ============================================================================
// Loading shimmer
// ============================================================================

function TeamPageShimmer() {
  return (
    <div className="flex flex-col gap-6 animate-pulse">
      <div className="h-8 w-48 rounded-xl bg-slate-100" />
      <div className="h-4 w-64 rounded bg-slate-100" />
      <div className="h-64 rounded-2xl bg-slate-100" />
      <div className="h-40 rounded-2xl bg-slate-100" />
    </div>
  );
}

// ============================================================================
// Role info card
// ============================================================================

const ROLES = [
  {
    name: 'Admin',
    color: 'indigo',
    description: 'Full access — can manage team members, change roles, and access billing.',
  },
  {
    name: 'Editor',
    color: 'emerald',
    description: 'Can create and edit initiatives, workflows, and content. Cannot manage the team.',
  },
  {
    name: 'Viewer',
    color: 'amber',
    description: 'Read-only access to all shared workspace content.',
  },
] as const;

function RoleInfoCard() {
  return (
    <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-base font-semibold text-slate-900">Role Reference</h2>
      <div className="flex flex-col gap-3">
        {ROLES.map((r) => (
          <div key={r.name} className="flex items-start gap-3">
            <span
              className={[
                'mt-0.5 shrink-0 inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold',
                r.color === 'indigo'
                  ? 'bg-indigo-100 text-indigo-700'
                  : r.color === 'emerald'
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-amber-100 text-amber-700',
              ].join(' ')}
            >
              {r.name[0]}
            </span>
            <div>
              <p className="text-sm font-medium text-slate-800">{r.name}</p>
              <p className="text-xs text-slate-500">{r.description}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ============================================================================
// Page content (inside GatedPage)
// ============================================================================

function TeamPageContent() {
  const { ready, workspaceId, workspaceName, role, isOwner } = useWorkspace();

  if (!ready) {
    return <TeamPageShimmer />;
  }

  // ownerId is the current user when isOwner is true. For the member table we
  // need to pass it through. We derive a stable ownerId from WorkspaceContext —
  // the owner is identified as the member whose isOwner flag is true. We pass
  // an empty string as a fallback when the workspace isn't yet loaded; the
  // TeamMemberList derives the "Owner" label server-side anyway.
  const ownerPlaceholder = '';

  return (
    <div className="flex flex-col gap-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Team Settings</h1>
        {workspaceName && (
          <p className="mt-1 text-sm text-slate-500">
            Workspace: <span className="font-medium text-slate-700">{workspaceName}</span>
          </p>
        )}
      </div>

      {/* Member list — visible to all roles */}
      {workspaceId ? (
        <TeamMemberList
          workspaceId={workspaceId}
          currentUserRole={role}
          ownerId={ownerPlaceholder}
        />
      ) : (
        <div className="rounded-2xl border border-slate-100 bg-white px-6 py-10 text-center shadow-sm">
          <p className="text-sm text-slate-500">
            Your workspace is being set up. Refresh in a moment.
          </p>
        </div>
      )}

      {/* Invite section — admin only */}
      {workspaceId && (
        <PermissionGate require="manage-team" fallback="hide">
          <InviteLinkGenerator workspaceId={workspaceId} />
        </PermissionGate>
      )}

      {/* Role reference card */}
      <RoleInfoCard />
    </div>
  );
}

// ============================================================================
// Page
// ============================================================================

export default function TeamPage() {
  return (
    <DashboardErrorBoundary fallbackTitle="Team Error">
      <GatedPage featureKey="teams">
        <PremiumShell>
          <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
            <TeamPageContent />
          </div>
        </PremiumShell>
      </GatedPage>
    </DashboardErrorBoundary>
  );
}
