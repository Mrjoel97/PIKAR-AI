// frontend/src/app/(admin)/impersonate/[userId]/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { ImpersonationProvider } from '@/contexts/ImpersonationContext';
import { ImpersonationBanner } from '@/components/admin/ImpersonationBanner';

type Persona = 'solopreneur' | 'startup' | 'sme' | 'enterprise' | null;

interface TargetUser {
  id: string;
  email: string;
  persona: Persona;
  agent_name: string | null;
  created_at: string;
  banned_until: string | null;
  onboarding_completed: boolean;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Impersonation view page.
 * Fetches the target user's profile from the admin API and renders a read-only
 * view wrapped in ImpersonationProvider (which overrides PersonaContext) and
 * ImpersonationBanner (non-dismissible session indicator).
 *
 * This page sits inside the (admin) layout, so AdminSidebar is still visible
 * on the left — the admin context is intentionally preserved.
 *
 * Full interactive impersonation (rendering actual persona layouts) is Phase 13.
 * This plan establishes the foundation: context, banner, session timer, and a
 * read-only user summary.
 */
export default function ImpersonatePage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.userId as string;

  const [user, setUser] = useState<TargetUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;

    async function fetchUser() {
      setIsLoading(true);
      setError(null);
      try {
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();

        if (!session) {
          router.push('/auth/login');
          return;
        }

        const res = await fetch(`${API_URL}/admin/users/${userId}`, {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });

        if (!res.ok) {
          if (res.status === 404) {
            setError('User not found');
          } else {
            setError('Failed to load user data');
          }
          return;
        }

        const data = (await res.json()) as { user: TargetUser };
        setUser(data.user);
      } catch {
        setError('Failed to load user data');
      } finally {
        setIsLoading(false);
      }
    }

    fetchUser();
  }, [userId, router]);

  // Redirect if user not found after load attempt
  useEffect(() => {
    if (!isLoading && error) {
      const timeout = setTimeout(() => {
        router.push('/admin/users');
      }, 2000);
      return () => clearTimeout(timeout);
    }
  }, [isLoading, error, router]);

  if (isLoading) {
    return (
      <div className="p-6 bg-gray-950 min-h-screen">
        <div className="max-w-7xl mx-auto space-y-4 animate-pulse">
          <div className="h-8 bg-gray-800 rounded w-1/3" />
          <div className="h-4 bg-gray-800 rounded w-1/4" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
            <div className="h-24 bg-gray-800 rounded" />
            <div className="h-24 bg-gray-800 rounded" />
            <div className="h-24 bg-gray-800 rounded" />
            <div className="h-24 bg-gray-800 rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="p-6 bg-gray-950 min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 text-sm">{error ?? 'User not found'}</p>
          <p className="text-gray-500 text-xs mt-1">Redirecting to user list...</p>
        </div>
      </div>
    );
  }

  return (
    <ImpersonationProvider
      targetUser={{
        id: user.id,
        email: user.email,
        persona: user.persona,
        agentName: user.agent_name,
      }}
    >
      <ImpersonationBanner />
      <div className="bg-gray-100 min-h-screen">
        <div className="max-w-7xl mx-auto p-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Dashboard View for {user.email}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 rounded">
                <p className="text-sm text-gray-500">Persona</p>
                <p className="text-lg font-medium text-gray-900 capitalize">
                  {user.persona ?? 'Not set'}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded">
                <p className="text-sm text-gray-500">Agent</p>
                <p className="text-lg font-medium text-gray-900">
                  {user.agent_name ?? 'No agent'}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded">
                <p className="text-sm text-gray-500">Member Since</p>
                <p className="text-lg font-medium text-gray-900">
                  {new Date(user.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded">
                <p className="text-sm text-gray-500">Status</p>
                <p className="text-lg font-medium text-gray-900">
                  {user.banned_until ? 'Suspended' : 'Active'}
                </p>
              </div>
            </div>
            <p className="mt-6 text-sm text-gray-500 italic">
              This is a read-only view. Interactive impersonation will be available in Phase 13.
            </p>
          </div>
        </div>
      </div>
    </ImpersonationProvider>
  );
}
