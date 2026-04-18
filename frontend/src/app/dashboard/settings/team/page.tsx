'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React, { useEffect, useState } from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { PermissionGate } from '@/components/ui/PermissionGate';
import { TeamMemberList } from '@/components/team/TeamMemberList';
import { InviteLinkGenerator } from '@/components/team/InviteLinkGenerator';
import { PendingInvitesList } from '@/components/team/PendingInvitesList';
import { useWorkspace } from '@/contexts/WorkspaceContext';
import { fetchWithAuth } from '@/services/api';

interface WorkspaceDetails {
  owner_id?: string;
}

const ROLE_REFERENCE = [
  {
    name: 'Admin',
    iconClass: 'bg-indigo-100 text-indigo-700',
    description: 'Full access - can manage team members, billing, and admin settings.',
  },
  {
    name: 'Member',
    iconClass: 'bg-slate-200 text-slate-700',
    description: 'Can create and edit initiatives, workflows, and content.',
  },
] as const;

function TeamSettingsShimmer() {
  return (
    <div className="flex flex-col gap-6 animate-pulse">
      <div className="h-8 w-48 rounded-xl bg-slate-100" />
      <div className="h-4 w-72 rounded bg-slate-100" />
      <div className="h-40 rounded-2xl bg-slate-100" />
      <div className="h-56 rounded-2xl bg-slate-100" />
      <div className="h-64 rounded-2xl bg-slate-100" />
    </div>
  );
}

function RoleInfoCard() {
  return (
    <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-base font-semibold text-slate-900">Role Reference</h2>
      <div className="flex flex-col gap-3">
        {ROLE_REFERENCE.map((role) => (
          <div key={role.name} className="flex items-start gap-3">
            <span
              className={[
                'mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold',
                role.iconClass,
              ].join(' ')}
            >
              {role.name[0]}
            </span>
            <div>
              <p className="text-sm font-medium text-slate-800">{role.name}</p>
              <p className="text-xs text-slate-500">{role.description}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function TeamSettingsPageContent() {
  const { ready, workspaceId, workspaceName, role } = useWorkspace();
  const [refreshKey, setRefreshKey] = useState(0);
  const [ownerId, setOwnerId] = useState<string>('');

  useEffect(() => {
    if (!workspaceId) {
      setOwnerId('');
      return;
    }

    let cancelled = false;
    const loadWorkspaceDetails = async () => {
      try {
        const response = await fetchWithAuth('/teams/workspace');
        if (!response.ok) {
          return;
        }

        const data = (await response.json()) as WorkspaceDetails;
        if (!cancelled) {
          setOwnerId(typeof data.owner_id === 'string' ? data.owner_id : '');
        }
      } catch {
        if (!cancelled) {
          setOwnerId('');
        }
      }
    };

    void loadWorkspaceDetails();
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  if (!ready) {
    return <TeamSettingsShimmer />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Team Settings</h1>
        {workspaceName && (
          <p className="mt-1 text-sm text-slate-500">
            Workspace: <span className="font-medium text-slate-700">{workspaceName}</span>
          </p>
        )}
      </div>

      {workspaceId ? (
        <>
          <PermissionGate require="manage-team" fallback="hide">
            <div className="flex flex-col gap-6">
              <InviteLinkGenerator
                workspaceId={workspaceId}
                onInviteSent={() => setRefreshKey((value) => value + 1)}
              />
              <PendingInvitesList workspaceId={workspaceId} refreshKey={refreshKey} />
            </div>
          </PermissionGate>

          <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-base font-semibold text-slate-900">Team Members</h2>
            <TeamMemberList
              workspaceId={workspaceId}
              currentUserRole={role}
              ownerId={ownerId}
            />
          </section>

          <RoleInfoCard />
        </>
      ) : (
        <div className="rounded-2xl border border-slate-100 bg-white px-6 py-10 text-center shadow-sm">
          <p className="text-sm text-slate-500">
            Your workspace is being set up. Refresh in a moment.
          </p>
        </div>
      )}
    </div>
  );
}

export default function TeamSettingsPage() {
  return (
    <DashboardErrorBoundary fallbackTitle="Team Settings Error">
      <PremiumShell>
        <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
          <TeamSettingsPageContent />
        </div>
      </PremiumShell>
    </DashboardErrorBoundary>
  );
}
