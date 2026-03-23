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
 * Allow-listed actions that the backend impersonation middleware permits.
 * Mirrors IMPERSONATION_ALLOWED_PATHS from impersonation_service.py.
 */
const ALLOWED_ACTIONS = [
  'Chat',
  'Workflows',
  'Approvals',
  'Briefing',
  'Reports',
] as const;

/**
 * Impersonation view page.
 * Fetches the target user's profile from the admin API and renders a view
 * wrapped in ImpersonationProvider (which overrides PersonaContext) and
 * ImpersonationBanner (non-dismissible session indicator).
 *
 * In read-only mode: shows the user profile card with an "Activate Interactive
 * Mode" button. On activation, calls POST /admin/impersonate/{userId}/start and
 * stores the returned session_id, upgrading the session to interactive mode.
 *
 * In interactive mode: shows the profile card with an "INTERACTIVE SESSION
 * ACTIVE" indicator and the list of allowed actions.
 *
 * This page sits inside the (admin) layout, so AdminSidebar is still visible
 * on the left — the admin context is intentionally preserved.
 */
export default function ImpersonatePage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.userId as string;

  const [user, setUser] = useState<TargetUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Interactive session state
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [isActivating, setIsActivating] = useState(false);
  const [activationError, setActivationError] = useState<string | null>(null);

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

  /**
   * Activates an interactive impersonation session by calling the backend.
   * Double-click protected via isActivating guard.
   */
  async function activateInteractiveMode() {
    if (isActivating) return;
    setIsActivating(true);
    setActivationError(null);

    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.push('/auth/login');
        return;
      }

      const res = await fetch(`${API_URL}/admin/impersonate/${userId}/start`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (res.ok) {
        const data = (await res.json()) as { session_id: string };
        setSessionToken(data.session_id);
      } else if (res.status === 403) {
        setActivationError('Super admin access required for interactive impersonation.');
      } else {
        setActivationError('Failed to activate interactive session. Please try again.');
      }
    } catch {
      setActivationError('Failed to activate interactive session. Please try again.');
    } finally {
      setIsActivating(false);
    }
  }

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
        ...(sessionToken ? { sessionToken } : {}),
      }}
    >
      <ImpersonationBanner />
      <div className="bg-gray-100 min-h-screen">
        <div className="max-w-7xl mx-auto p-6">
          <div className="bg-white rounded-lg shadow p-6">
            {/* Interactive session active indicator */}
            {sessionToken ? (
              <>
                <div className="mb-4 flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <span className="text-red-600 font-bold text-sm" aria-label="Interactive session active">
                    &#9888; INTERACTIVE SESSION ACTIVE
                  </span>
                </div>

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

                <div className="mt-6">
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    Allowed actions in this session:
                  </p>
                  <ul className="flex flex-wrap gap-2">
                    {ALLOWED_ACTIONS.map((action) => (
                      <li
                        key={action}
                        className="px-3 py-1 bg-red-100 text-red-800 text-xs font-semibold rounded-full"
                      >
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            ) : (
              <>
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

                {/* Activate Interactive Mode section */}
                <div className="mt-6 p-4 border border-gray-200 rounded-lg">
                  <h3 className="text-sm font-semibold text-gray-900 mb-1">
                    Interactive Mode
                  </h3>
                  <p className="text-xs text-gray-500 mb-3">
                    This will allow you to take actions on behalf of this user for 30 minutes.
                  </p>

                  {activationError && (
                    <p className="text-xs text-red-600 mb-3" role="alert">
                      {activationError}
                    </p>
                  )}

                  <button
                    type="button"
                    onClick={activateInteractiveMode}
                    disabled={isActivating}
                    className="bg-red-600 text-white text-sm font-semibold px-4 py-2 rounded hover:bg-red-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                  >
                    {isActivating ? 'Activating...' : 'Activate Interactive Mode'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </ImpersonationProvider>
  );
}
