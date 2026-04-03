'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * @fileoverview /dashboard/team/join — Invite acceptance page.
 *
 * Reads `?token=xxx` from the URL, presents an "Accept Invitation" button,
 * calls the backend accept endpoint, then redirects to /dashboard/team.
 *
 * No GatedPage wrapper — any authenticated user can accept an invite. The
 * backend validates tier requirements. Unauthenticated users are redirected
 * to the login page with a return URL.
 *
 * Next.js requires useSearchParams() to be wrapped in a Suspense boundary.
 */

import React, { Suspense, useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { fetchWithAuth } from '@/services/api';
import { useWorkspace } from '@/contexts/WorkspaceContext';

// ============================================================================
// Types
// ============================================================================

type JoinState = 'idle' | 'loading' | 'success' | 'error';

// ============================================================================
// Loading shimmer (shown while Suspense is resolving)
// ============================================================================

function JoinPageShimmer() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-slate-100 bg-white p-8 shadow-sm animate-pulse">
        <div className="mb-4 h-6 w-2/3 rounded bg-slate-100" />
        <div className="mb-6 h-4 w-full rounded bg-slate-100" />
        <div className="h-10 w-full rounded-xl bg-slate-100" />
      </div>
    </div>
  );
}

// ============================================================================
// Inner component — reads searchParams, must be in Suspense
// ============================================================================

function JoinPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { refresh } = useWorkspace();

  const token = searchParams.get('token');

  const [joinState, setJoinState] = useState<JoinState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // ── Auth guard ────────────────────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        const returnUrl = encodeURIComponent(
          `/dashboard/team/join${token ? `?token=${token}` : ''}`,
        );
        router.replace(`/login?returnUrl=${returnUrl}`);
      }
    })();
  }, [router, token]);

  // ── Accept invite ────────────────────────────────────────────────────────
  const handleAccept = useCallback(async () => {
    if (!token) {
      setErrorMessage('Invalid invite link — no token found.');
      setJoinState('error');
      return;
    }

    setJoinState('loading');
    setErrorMessage(null);

    try {
      const response = await fetchWithAuth('/teams/invites/accept', {
        method: 'POST',
        body: JSON.stringify({ token }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const msg =
          typeof data?.detail === 'string'
            ? data.detail
            : 'Failed to accept invitation. The link may have expired or already been used.';
        setErrorMessage(msg);
        setJoinState('error');
        return;
      }

      setJoinState('success');

      // Refresh workspace context so the new membership is reflected immediately.
      await refresh();

      // Redirect to team settings after a short delay so the user sees the
      // success state before navigating away.
      setTimeout(() => {
        router.push('/dashboard/team');
      }, 2000);
    } catch {
      setErrorMessage('Network error — please check your connection and try again.');
      setJoinState('error');
    }
  }, [token, refresh, router]);

  // ── No token in URL ───────────────────────────────────────────────────────
  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="w-full max-w-sm rounded-2xl border border-red-100 bg-white p-8 shadow-sm text-center">
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-red-50">
            <svg
              className="h-6 w-6 text-red-500"
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
                d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
              />
            </svg>
          </div>
          <h1 className="mb-2 text-lg font-semibold text-slate-900">Invalid Invite Link</h1>
          <p className="text-sm text-slate-500">
            This invite link is missing a token. Please check the link and try again.
          </p>
        </div>
      </div>
    );
  }

  // ── Success state ─────────────────────────────────────────────────────────
  if (joinState === 'success') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="w-full max-w-sm rounded-2xl border border-emerald-100 bg-white p-8 shadow-sm text-center">
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
            You&apos;ve joined the workspace!
          </h1>
          <p className="text-sm text-slate-500">
            Redirecting you to the team page&hellip;
          </p>
        </div>
      </div>
    );
  }

  // ── Default / error state ─────────────────────────────────────────────────
  const isLoading = joinState === 'loading';

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-slate-100 bg-white p-8 shadow-sm">
        {/* Icon */}
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

        <h1 className="mb-2 text-xl font-bold text-slate-900">
          You&apos;ve been invited to a workspace
        </h1>
        <p className="mb-6 text-sm text-slate-500">
          Accept the invitation to start collaborating with your team.
        </p>

        {/* Error message */}
        {joinState === 'error' && errorMessage && (
          <div
            className="mb-5 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700"
            role="alert"
          >
            {errorMessage}
          </div>
        )}

        {/* Accept button */}
        <button
          type="button"
          onClick={handleAccept}
          disabled={isLoading}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
        >
          {isLoading && (
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
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
          )}
          {isLoading ? 'Accepting…' : 'Accept Invitation'}
        </button>

        {joinState === 'error' && (
          <p className="mt-3 text-center text-xs text-slate-400">
            Need help?{' '}
            <a href="/dashboard" className="text-indigo-600 hover:underline">
              Return to dashboard
            </a>
          </p>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Page (Suspense boundary required for useSearchParams)
// ============================================================================

export default function TeamJoinPage() {
  return (
    <Suspense fallback={<JoinPageShimmer />}>
      <JoinPageInner />
    </Suspense>
  );
}
