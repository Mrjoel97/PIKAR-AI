// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function toLoginError(message: string) {
  return `/login?error=${encodeURIComponent(message)}`;
}

function AdminAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const startedRef = useRef(false);
  const [status, setStatus] = useState('Finishing sign-in...');

  useEffect(() => {
    if (startedRef.current) {
      return;
    }
    startedRef.current = true;

    const completeSignIn = async () => {
      const codeError = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      if (codeError) {
        router.replace(toLoginError(errorDescription || codeError));
        return;
      }

      const code = searchParams.get('code');
      if (!code) {
        router.replace(toLoginError('No authorization code'));
        return;
      }

      try {
        const supabase = createClient();
        const { data, error } = await supabase.auth.exchangeCodeForSession(code);

        if (error) {
          router.replace(toLoginError(error.message));
          return;
        }

        const accessToken = data.session?.access_token;
        const refreshToken = data.session?.refresh_token;

        if (!accessToken || !refreshToken) {
          await supabase.auth.signOut();
          router.replace(toLoginError('Authenticated session is incomplete.'));
          return;
        }

        setStatus('Verifying admin access...');
        const res = await fetch(`${API_URL}/admin/check-access`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
            'X-Admin-Client': 'pikar-admin/1.0',
          },
        });

        if (!res.ok) {
          await supabase.auth.signOut();
          router.replace(
            toLoginError('Access denied. This account does not have admin privileges.'),
          );
          return;
        }

        setStatus('Establishing admin session...');
        const persistRes = await fetch('/auth/session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            access_token: accessToken,
            refresh_token: refreshToken,
          }),
        });

        if (!persistRes.ok) {
          await supabase.auth.signOut();
          router.replace(toLoginError('Failed to establish admin session.'));
          return;
        }

        router.replace('/');
      } catch {
        router.replace(toLoginError('Unable to verify admin access.'));
      }
    };

    void completeSignIn();
  }, [router, searchParams]);

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-gray-800 bg-gray-900/70 p-8 text-center shadow-2xl shadow-black/30">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-teal-500/15">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-teal-400 border-t-transparent" />
        </div>
        <h1 className="text-xl font-display font-semibold text-white">
          Connecting your admin session
        </h1>
        <p className="mt-3 text-sm text-gray-400">{status}</p>
      </div>
    </div>
  );
}

export default function AdminAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
          <div className="w-full max-w-md rounded-2xl border border-gray-800 bg-gray-900/70 p-8 text-center shadow-2xl shadow-black/30">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-teal-500/15">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-teal-400 border-t-transparent" />
            </div>
            <h1 className="text-xl font-display font-semibold text-white">
              Connecting your admin session
            </h1>
            <p className="mt-3 text-sm text-gray-400">Preparing secure sign-in...</p>
          </div>
        </div>
      }
    >
      <AdminAuthCallbackContent />
    </Suspense>
  );
}
