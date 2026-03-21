'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { ArrowLeft, Shield, ShieldOff, UserCog, Eye, MessageSquare } from 'lucide-react';
import { toast } from 'sonner';

/** Detailed user record returned by GET /admin/users/{id} */
interface UserDetail {
  id: string;
  email: string;
  persona: string | null;
  agent_name: string | null;
  created_at: string;
  banned_until: string | null;
  onboarding_completed: boolean;
  activity: {
    action_count: number;
  };
}

/** Colored badge classes for persona values */
const personaBadgeClass: Record<string, string> = {
  solopreneur: 'bg-blue-900 text-blue-300',
  startup: 'bg-green-900 text-green-300',
  sme: 'bg-amber-900 text-amber-300',
  enterprise: 'bg-purple-900 text-purple-300',
};

/** Returns true when the user is currently suspended */
function isSuspended(bannedUntil: string | null): boolean {
  if (!bannedUntil) return false;
  return new Date(bannedUntil) > new Date();
}

/** Format ISO date string as YYYY-MM-DD */
function formatDate(iso: string): string {
  return iso.split('T')[0] ?? iso;
}

/**
 * UserDetailPage renders /admin/users/[id] with:
 * - Profile card (email, persona, status, signup date, agent name)
 * - Activity stats card (chat count, workflow count)
 * - Actions: suspend/unsuspend with confirmation, persona change, impersonate
 */
export default function UserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const supabase = createClient();
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const userId = params.id as string;

  const [user, setUser] = useState<UserDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const fetchUser = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setFetchError('Not authenticated');
        return;
      }

      const res = await fetch(`${API_URL}/admin/users/${userId}`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (res.status === 404) {
        setFetchError('User not found.');
        return;
      }

      if (!res.ok) {
        setFetchError(`Failed to load user (${res.status})`);
        return;
      }

      const json = (await res.json()) as { user: UserDetail };
      setUser(json.user);
    } catch {
      setFetchError('Failed to load user. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [supabase, API_URL, userId]);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  /** PATCH suspend or unsuspend */
  const handleSuspendToggle = async () => {
    if (!user) return;
    const suspended = isSuspended(user.banned_until);
    const action = suspended ? 'unsuspend' : 'suspend';
    const confirmed = window.confirm(
      suspended
        ? `Unsuspend ${user.email}? They will regain access immediately.`
        : `Suspend ${user.email}? They will lose access immediately.`
    );
    if (!confirmed) return;

    setIsProcessing(true);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Not authenticated');
        return;
      }

      const res = await fetch(`${API_URL}/admin/users/${userId}/${action}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        toast.error(body.detail ?? `Failed to ${action} user (${res.status})`);
        return;
      }

      toast.success(suspended ? 'User unsuspended' : 'User suspended');
      await fetchUser();
    } catch {
      toast.error(`Failed to ${action} user. Check that the backend is running.`);
    } finally {
      setIsProcessing(false);
    }
  };

  /** PATCH persona change */
  const handlePersonaChange = async (newPersona: string) => {
    if (!user || newPersona === user.persona) return;

    setIsProcessing(true);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        toast.error('Not authenticated');
        return;
      }

      const res = await fetch(`${API_URL}/admin/users/${userId}/persona`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ persona: newPersona }),
      });

      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        toast.error(body.detail ?? `Failed to change persona (${res.status})`);
        return;
      }

      toast.success(`Persona changed to ${newPersona}`);
      await fetchUser();
    } catch {
      toast.error('Failed to change persona. Check that the backend is running.');
    } finally {
      setIsProcessing(false);
    }
  };

  // --- Render states ---

  if (isLoading) {
    return (
      <div className="p-8">
        <button
          type="button"
          onClick={() => router.push('/admin/users')}
          className="flex items-center gap-2 text-gray-400 hover:text-gray-200 text-sm mb-6 transition-colors"
        >
          <ArrowLeft size={16} />
          Back to Users
        </button>
        {/* Loading skeleton */}
        <div className="space-y-4 max-w-2xl">
          <div className="bg-gray-800 rounded-xl h-36 animate-pulse border border-gray-700" />
          <div className="bg-gray-800 rounded-xl h-24 animate-pulse border border-gray-700" />
          <div className="bg-gray-800 rounded-xl h-28 animate-pulse border border-gray-700" />
        </div>
      </div>
    );
  }

  if (fetchError || !user) {
    return (
      <div className="p-8">
        <button
          type="button"
          onClick={() => router.push('/admin/users')}
          className="flex items-center gap-2 text-gray-400 hover:text-gray-200 text-sm mb-6 transition-colors"
        >
          <ArrowLeft size={16} />
          Back to Users
        </button>
        <div className="flex flex-col items-center justify-center py-20 gap-4">
          <p className="text-red-400 text-sm">{fetchError ?? 'User not found.'}</p>
          <button
            type="button"
            onClick={() => fetchUser()}
            className="px-4 py-2 bg-gray-800 text-gray-200 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const suspended = isSuspended(user.banned_until);

  return (
    <div className="p-8 max-w-2xl">
      {/* Back link */}
      <button
        type="button"
        onClick={() => router.push('/admin/users')}
        className="flex items-center gap-2 text-gray-400 hover:text-gray-200 text-sm mb-6 transition-colors"
      >
        <ArrowLeft size={16} />
        Back to Users
      </button>

      {/* Profile card */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 mb-4">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h1 className="text-xl font-bold text-gray-100 break-all">{user.email}</h1>
            {user.agent_name && (
              <p className="mt-0.5 text-sm text-gray-400">Agent: {user.agent_name}</p>
            )}
          </div>
          {/* Status badge */}
          {suspended ? (
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-red-900 text-red-300 whitespace-nowrap">
              Suspended
            </span>
          ) : (
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-900 text-green-300 whitespace-nowrap">
              Active
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500 text-xs uppercase tracking-wide mb-0.5">Persona</p>
            {user.persona ? (
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                  personaBadgeClass[user.persona] ?? 'bg-gray-700 text-gray-300'
                }`}
              >
                {user.persona}
              </span>
            ) : (
              <span className="text-gray-500">—</span>
            )}
          </div>
          <div>
            <p className="text-gray-500 text-xs uppercase tracking-wide mb-0.5">Signup Date</p>
            <p className="text-gray-300">{formatDate(user.created_at)}</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs uppercase tracking-wide mb-0.5">Onboarding</p>
            <p className="text-gray-300">{user.onboarding_completed ? 'Complete' : 'Incomplete'}</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs uppercase tracking-wide mb-0.5">User ID</p>
            <p className="text-gray-500 text-xs font-mono break-all">{user.id}</p>
          </div>
        </div>
      </div>

      {/* Activity stats card */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 mb-4">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-4">
          Activity
        </h2>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gray-800 rounded-lg">
            <MessageSquare size={18} className="text-indigo-400" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-100">{user.activity.action_count}</p>
            <p className="text-xs text-gray-500">Admin actions</p>
          </div>
        </div>
      </div>

      {/* Actions card */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-4">
          Actions
        </h2>
        <div className="space-y-4">
          {/* Suspend / Unsuspend */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-200">
                {suspended ? 'Unsuspend User' : 'Suspend User'}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                {suspended
                  ? 'Restore access for this user.'
                  : 'Block this user from accessing the platform.'}
              </p>
            </div>
            <button
              type="button"
              onClick={handleSuspendToggle}
              disabled={isProcessing}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                suspended
                  ? 'bg-green-700 hover:bg-green-600 text-white'
                  : 'bg-red-700 hover:bg-red-600 text-white'
              }`}
            >
              {suspended ? <ShieldOff size={16} /> : <Shield size={16} />}
              {suspended ? 'Unsuspend' : 'Suspend'}
            </button>
          </div>

          <div className="border-t border-gray-700" />

          {/* Persona change */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-200">Change Persona</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Switch the user to a different persona tier.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <UserCog size={16} className="text-gray-500" />
              <select
                value={user.persona ?? ''}
                onChange={(e) => handlePersonaChange(e.target.value)}
                disabled={isProcessing}
                className="bg-gray-800 text-gray-100 text-sm rounded-lg px-3 py-1.5 border border-gray-600 outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value="" disabled>
                  Select persona
                </option>
                <option value="solopreneur">Solopreneur</option>
                <option value="startup">Startup</option>
                <option value="sme">SME</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </div>
          </div>

          <div className="border-t border-gray-700" />

          {/* Impersonate */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-200">View as User</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Browse the platform from this user&apos;s perspective.
              </p>
            </div>
            <button
              type="button"
              onClick={() => router.push(`/admin/impersonate/${userId}`)}
              disabled={isProcessing}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-gray-700 hover:bg-gray-600 text-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-gray-600"
            >
              <Eye size={16} />
              Impersonate
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
