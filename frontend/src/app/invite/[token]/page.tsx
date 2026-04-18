'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React, { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { createClient } from '@/lib/supabase/client';
import { fetchPublicApi, fetchWithAuth } from '@/services/api';
import { WorkspaceProvider, useWorkspace } from '@/contexts/WorkspaceContext';

type InviteViewState = 'loading' | 'ready' | 'accepting' | 'success' | 'error';

interface InviteDetails {
  id: string;
  workspaceName: string;
  role: string;
  invitedEmail: string | null;
  inviterName: string | null;
  expiresAt: string;
  isActive: boolean;
}

function getRoleLabel(role: string): string {
  if (role === 'admin') {
    return 'Admin';
  }

  if (role === 'viewer') {
    return 'Viewer';
  }

  return 'Member';
}

function getRoleBadgeClass(role: string): string {
  if (role === 'admin') {
    return 'border-blue-200 bg-blue-50 text-blue-700';
  }

  if (role === 'viewer') {
    return 'border-amber-200 bg-amber-50 text-amber-700';
  }

  return 'border-slate-300 bg-slate-100 text-slate-700';
}

function InviteShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-slate-100 bg-white p-8 shadow-sm">
        {children}
      </div>
    </div>
  );
}

function InvitePageShimmer() {
  return (
    <InviteShell>
      <div className="animate-pulse">
        <div className="mb-4 h-12 w-12 rounded-full bg-slate-100" />
        <div className="mb-3 h-7 w-2/3 rounded bg-slate-100" />
        <div className="mb-6 h-4 w-full rounded bg-slate-100" />
        <div className="mb-3 h-16 rounded-xl bg-slate-100" />
        <div className="h-10 rounded-xl bg-slate-100" />
      </div>
    </InviteShell>
  );
}

function AcceptInvitation({ token }: { token: string }) {
  const router = useRouter();
  const { refresh } = useWorkspace();
  const [viewState, setViewState] = useState<InviteViewState>('loading');
  const [details, setDetails] = useState<InviteDetails | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const returnUrl = useMemo(() => `/invite/${encodeURIComponent(token)}`, [token]);

  const authQuery = useMemo(() => {
    const params = new URLSearchParams({ returnUrl });
    if (details?.invitedEmail) {
      params.set('email', details.invitedEmail);
    }
    return params.toString();
  }, [details?.invitedEmail, returnUrl]);

  const loginHref = `/auth/login?${authQuery}`;
  const signupHref = `/auth/signup?${authQuery}`;

  useEffect(() => {
    let cancelled = false;

    const loadInvite = async () => {
      setViewState('loading');
      setErrorMessage(null);

      try {
        const supabase = createClient();
        const [inviteResponse, authResult] = await Promise.all([
          fetchPublicApi(
            `/teams/invites/details?token=${encodeURIComponent(token)}`,
            { cache: 'no-store' },
            false,
          ),
          supabase.auth.getUser(),
        ]);

        const user = authResult.data.user;
        const payload = await inviteResponse.json().catch(() => ({})) as Record<string, unknown>;

        if (!inviteResponse.ok) {
          throw new Error(
            typeof payload.error === 'string'
              ? payload.error
              : typeof payload.detail === 'string'
                ? payload.detail
                : 'This invitation is no longer valid.',
          );
        }

        if (!cancelled) {
          setDetails(payload as unknown as InviteDetails);
          setIsAuthenticated(Boolean(user));
          setViewState('ready');
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(
            error instanceof Error && error.message
              ? error.message
              : 'Failed to load invitation details.',
          );
          setViewState('error');
        }
      }
    };

    void loadInvite();

    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (viewState !== 'success') {
      return;
    }

    const timer = window.setTimeout(() => {
      router.push('/dashboard');
    }, 2000);

    return () => window.clearTimeout(timer);
  }, [router, viewState]);

  const handleAccept = useCallback(async () => {
    setViewState('accepting');
    setErrorMessage(null);

    try {
      const response = await fetchWithAuth('/teams/invites/accept', {
        method: 'POST',
        body: JSON.stringify({ token }),
      });

      if (!response.ok) {
        const data = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'Failed to accept invitation. The link may have expired or already been used.',
        );
      }

      await refresh();
      toast.success(`Joined ${details?.workspaceName ?? 'workspace'} successfully`);
      setViewState('success');
    } catch (error) {
      setErrorMessage(
        error instanceof Error && error.message
          ? error.message
          : 'Failed to accept invitation.',
      );
      setViewState('error');
    }
  }, [details?.workspaceName, refresh, token]);

  if (viewState === 'loading') {
    return <InvitePageShimmer />;
  }

  if (viewState === 'success') {
    return (
      <InviteShell>
        <div className="text-center">
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50">
            <svg
              className="h-6 w-6 text-emerald-500"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h1 className="mb-2 text-lg font-semibold text-slate-900">
            You&apos;ve joined the workspace
          </h1>
          <p className="text-sm text-slate-500">
            Redirecting you to your dashboard now...
          </p>
        </div>
      </InviteShell>
    );
  }

  const isAccepting = viewState === 'accepting';
  const expiresLabel = details?.expiresAt
    ? new Date(details.expiresAt).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : null;

  return (
    <InviteShell>
      <div className="mb-5 inline-flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
        <svg
          className="h-6 w-6 text-indigo-500"
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
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
      </div>

      <h1 className="mb-2 text-xl font-bold text-slate-900">You&apos;re invited to join</h1>
      <p className="mb-6 text-sm text-slate-500">
        Review the invitation details below, then accept to start collaborating.
      </p>

      {details && (
        <div className="mb-5 rounded-xl border border-slate-100 bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-900">{details.workspaceName}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span
              className={[
                'inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium',
                getRoleBadgeClass(details.role),
              ].join(' ')}
            >
              {getRoleLabel(details.role)}
            </span>
            {expiresLabel && (
              <span className="text-xs text-slate-500">Expires {expiresLabel}</span>
            )}
          </div>
          {details.inviterName && (
            <p className="mt-2 text-xs text-slate-500">
              Invited by {details.inviterName}
            </p>
          )}
          {details.invitedEmail && (
            <p className="mt-1 text-xs text-slate-500">{details.invitedEmail}</p>
          )}
        </div>
      )}

      {errorMessage && (
        <div className="mb-5 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
          {errorMessage}
        </div>
      )}

      {isAuthenticated ? (
        <button
          type="button"
          onClick={() => void handleAccept()}
          disabled={isAccepting}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isAccepting && (
            <svg
              className="h-4 w-4 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
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
                d="M4 12a8 8 0 018-8V4C7.582 4 4 7.582 4 12z"
              />
            </svg>
          )}
          {isAccepting ? 'Accepting...' : 'Accept Invitation'}
        </button>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-slate-500">
            Sign up or log in to accept this invitation.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Link
              href={signupHref}
              className="inline-flex flex-1 items-center justify-center rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700"
            >
              Sign Up
            </Link>
            <Link
              href={loginHref}
              className="inline-flex flex-1 items-center justify-center rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:border-indigo-300 hover:text-indigo-600"
            >
              Log In
            </Link>
          </div>
        </div>
      )}
    </InviteShell>
  );
}

export default function InviteTokenPage() {
  const params = useParams<{ token: string }>();
  const token = typeof params?.token === 'string' ? params.token : '';

  return (
    <WorkspaceProvider>
      <Suspense fallback={<InvitePageShimmer />}>
        <AcceptInvitation token={token} />
      </Suspense>
    </WorkspaceProvider>
  );
}
