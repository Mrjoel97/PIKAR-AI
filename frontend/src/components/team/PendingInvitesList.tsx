'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { fetchWithAuth } from '@/services/api';

interface PendingInvitesListProps {
  workspaceId: string;
  refreshKey?: number;
}

interface PendingInvite {
  id: string;
  role: string;
  invited_email: string | null;
  expires_at: string;
  created_at: string;
  is_active: boolean;
  token?: string;
}

type UiRole = {
  label: string;
  className: string;
  apiRole: 'admin' | 'member' | 'viewer';
};

const BADGE_BASE =
  'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium';

function getRoleMeta(role: string): UiRole {
  if (role === 'admin') {
    return {
      label: 'Admin',
      className: `${BADGE_BASE} border-blue-200 bg-blue-50 text-blue-700`,
      apiRole: 'admin',
    };
  }

  if (role === 'viewer') {
    return {
      label: 'Viewer',
      className: `${BADGE_BASE} border-amber-200 bg-amber-50 text-amber-700`,
      apiRole: 'viewer',
    };
  }

  return {
    label: 'Member',
    className: `${BADGE_BASE} border-slate-300 bg-slate-100 text-slate-700`,
    apiRole: 'member',
  };
}

function getExpiryLabel(expiresAt: string): { label: string; expired: boolean } {
  const expiryMs = new Date(expiresAt).getTime();
  if (!Number.isFinite(expiryMs)) {
    return { label: 'Expires soon', expired: false };
  }

  const remainingMs = expiryMs - Date.now();
  if (remainingMs <= 0) {
    return { label: 'Expired', expired: true };
  }

  const hours = Math.ceil(remainingMs / (1000 * 60 * 60));
  if (hours < 24) {
    return {
      label: `Expires in ${hours} hour${hours === 1 ? '' : 's'}`,
      expired: false,
    };
  }

  const days = Math.ceil(hours / 24);
  return {
    label: `Expires in ${days} day${days === 1 ? '' : 's'}`,
    expired: false,
  };
}

function PendingInviteRowSkeleton() {
  return (
    <div className="h-12 rounded-xl bg-slate-100 animate-pulse" />
  );
}

export function PendingInvitesList({
  workspaceId,
  refreshKey = 0,
}: PendingInvitesListProps) {
  const [invites, setInvites] = useState<PendingInvite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resendingId, setResendingId] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const fetchPendingInvites = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchWithAuth('/teams/invites');
      if (!response.ok) {
        const data = (await response.json().catch(() => ({}))) as { detail?: string };
        setError(
          typeof data.detail === 'string'
            ? data.detail
            : 'Failed to load pending invitations.',
        );
        return;
      }

      const data = (await response.json()) as PendingInvite[];
      setInvites(Array.isArray(data) ? data : []);
      setError(null);
    } catch {
      setError('Network error - could not load pending invitations.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchPendingInvites();
  }, [fetchPendingInvites, refreshKey, workspaceId]);

  const handleResend = async (invite: PendingInvite) => {
    setResendingId(invite.id);
    try {
      const resendResponse = await fetchWithAuth(`/teams/invites/${invite.id}/resend`, {
        method: 'POST',
      });

      if (!resendResponse.ok) {
        const data = (await resendResponse.json().catch(() => ({}))) as { detail?: string };
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'Failed to resend invitation.',
        );
      }

      const refreshedInvite = (await resendResponse.json()) as PendingInvite;
      if (refreshedInvite.invited_email) {
        if (!refreshedInvite.token) {
          throw new Error('Invite token refresh failed. Please try again.');
        }

        const roleMeta = getRoleMeta(refreshedInvite.role);
        const emailResponse = await fetch('/api/teams/invite', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: refreshedInvite.invited_email,
            role: roleMeta.apiRole,
            workspaceId,
            inviteId: refreshedInvite.id,
            inviteToken: refreshedInvite.token,
            inviteExpiresAt: refreshedInvite.expires_at,
          }),
        });

        if (!emailResponse.ok) {
          const data = (await emailResponse.json().catch(() => ({}))) as { error?: string };
          throw new Error(
            typeof data.error === 'string'
              ? data.error
              : 'Invite token refreshed, but email delivery failed.',
          );
        }

        toast.success(`Invitation resent to ${refreshedInvite.invited_email}`);
      } else {
        toast.success('Invite link refreshed');
      }

      await fetchPendingInvites();
    } catch (err) {
      const message =
        err instanceof Error && err.message
          ? err.message
          : 'Failed to resend invitation.';
      toast.error(message);
    } finally {
      setResendingId(null);
    }
  };

  const handleRevoke = async (inviteId: string) => {
    setRevokingId(inviteId);
    try {
      const response = await fetchWithAuth(`/teams/invites/${inviteId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const data = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(
          typeof data.detail === 'string' ? data.detail : 'Failed to revoke invitation.',
        );
      }

      toast.success('Invitation revoked');
      await fetchPendingInvites();
    } catch (err) {
      const message =
        err instanceof Error && err.message
          ? err.message
          : 'Failed to revoke invitation.';
      toast.error(message);
    } finally {
      setRevokingId(null);
    }
  };

  return (
    <section className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-base font-semibold text-slate-900">Pending Invitations</h2>

      {loading ? (
        <div className="space-y-3">
          <PendingInviteRowSkeleton />
          <PendingInviteRowSkeleton />
          <PendingInviteRowSkeleton />
        </div>
      ) : error ? (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : invites.length === 0 ? (
        <p className="py-6 text-center text-sm text-slate-400">No pending invitations</p>
      ) : (
        <div className="space-y-3">
          {invites.map((invite) => {
            const role = getRoleMeta(invite.role);
            const expiry = getExpiryLabel(invite.expires_at);
            const sentDate = new Date(invite.created_at).toLocaleDateString();
            const isResending = resendingId === invite.id;
            const isRevoking = revokingId === invite.id;

            return (
              <div
                key={invite.id}
                className="flex flex-col gap-3 rounded-xl border border-slate-100 bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-800">
                    {invite.invited_email ?? 'Link invite'}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <span className={role.className}>{role.label}</span>
                    <span className="text-xs text-slate-500">Sent {sentDate}</span>
                    <span
                      className={[
                        'text-xs',
                        expiry.expired ? 'text-red-600' : 'text-slate-500',
                      ].join(' ')}
                    >
                      {expiry.label}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleResend(invite)}
                    disabled={isResending || isRevoking}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:border-indigo-300 hover:text-indigo-600 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isResending ? 'Resending...' : 'Resend'}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRevoke(invite.id)}
                    disabled={isResending || isRevoking}
                    className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-600 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isRevoking ? 'Revoking...' : 'Revoke'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default PendingInvitesList;
