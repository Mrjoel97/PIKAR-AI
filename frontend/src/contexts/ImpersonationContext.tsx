// frontend/src/contexts/ImpersonationContext.tsx
'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  useCallback,
  type ReactNode,
} from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { PersonaContext } from '@/contexts/PersonaContext';

type Persona = 'solopreneur' | 'startup' | 'sme' | 'enterprise' | null;

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Shape of the impersonation session state provided to consumers. */
interface ImpersonationState {
  isActive: boolean;
  targetUserId: string;
  targetUserEmail: string;
  targetPersona: Persona;
  targetAgentName: string | null;
  sessionStartTime: Date;
  timeRemainingMs: number;
  mode: 'read_only' | 'interactive';
  sessionToken: string | null;
  impersonatedFetch: (url: string, init?: RequestInit) => Promise<Response>;
  exitImpersonation: () => void;
}

/** Target user data required to start an impersonation session. */
interface TargetUser {
  id: string;
  email: string;
  persona: Persona;
  agentName: string | null;
  sessionToken?: string;
}

const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes

const ImpersonationContext = createContext<ImpersonationState | null>(null);

/**
 * ImpersonationProvider wraps the impersonation view content.
 * It overrides PersonaContext with the target user's static data so any
 * child component calling usePersona() receives the target user's values.
 * A 30-minute session timer is persisted in sessionStorage to survive
 * navigation within the impersonation view.
 *
 * When targetUser.sessionToken is provided, the session is treated as
 * interactive — the banner turns red, mode is 'interactive', and
 * impersonatedFetch injects the X-Impersonation-Session header on API calls.
 */
export function ImpersonationProvider({
  children,
  targetUser,
}: {
  children: ReactNode;
  targetUser: TargetUser;
}) {
  const router = useRouter();
  const storageKey = `pikar:impersonate:${targetUser.id}:start`;

  // Derive mode and sessionToken from targetUser.sessionToken.
  const sessionToken = targetUser.sessionToken ?? null;
  const mode: 'read_only' | 'interactive' = sessionToken ? 'interactive' : 'read_only';

  // Cache the admin's Supabase access token in a ref on mount.
  // Used for fire-and-forget DELETE calls — avoids getSession() on every exit.
  const adminTokenRef = useRef<string | null>(null);
  useEffect(() => {
    const supabase = createClient();
    let cancelled = false;

    const loadSession = async () => {
      const { data } = await supabase.auth.getSession();
      if (!cancelled) {
        adminTokenRef.current = data.session?.access_token ?? null;
      }
    };

    void loadSession();

    return () => {
      cancelled = true;
    };
  }, []);

  // Resolve or create session start time from sessionStorage.
  const resolveSessionStart = (): Date => {
    if (typeof window === 'undefined') {
      return new Date();
    }
    const stored = window.sessionStorage.getItem(storageKey);
    if (stored) {
      const parsed = new Date(stored);
      const age = Date.now() - parsed.getTime();
      if (age < SESSION_TIMEOUT_MS) {
        return parsed;
      }
    }
    const now = new Date();
    window.sessionStorage.setItem(storageKey, now.toISOString());
    return now;
  };

  const [sessionStartTime] = useState<Date>(resolveSessionStart);
  const [timeRemainingMs, setTimeRemainingMs] = useState<number>(
    () => SESSION_TIMEOUT_MS - (Date.now() - sessionStartTime.getTime()),
  );

  /**
   * impersonatedFetch wraps fetch and injects the X-Impersonation-Session
   * header when an interactive session token is available.
   * All user-context API calls during impersonation must use this utility
   * so the backend allow-list middleware can validate the session.
   */
  const impersonatedFetch = useCallback(
    (url: string, init?: RequestInit): Promise<Response> => {
      if (!sessionToken) return fetch(url, init);
      const headers = new Headers(init?.headers);
      headers.set('X-Impersonation-Session', sessionToken);
      return fetch(url, { ...init, headers });
    },
    [sessionToken],
  );

  /**
   * Fire-and-forget DELETE to deactivate backend session.
   * No await — navigation must never be blocked by this call.
   */
  const deactivateBackendSession = useCallback(
    (token: string) => {
      fetch(`${API_URL}/admin/impersonate/sessions/${token}`, {
        method: 'DELETE',
        headers: {
          ...(adminTokenRef.current
            ? { Authorization: `Bearer ${adminTokenRef.current}` }
            : {}),
        },
      }).catch(() => {
        // Intentionally swallowed — session will auto-expire server-side.
      });
    },
    [],
  );

  const exitImpersonation = useCallback(() => {
    if (typeof window !== 'undefined') {
      window.sessionStorage.removeItem(storageKey);
    }
    if (sessionToken) {
      deactivateBackendSession(sessionToken);
    }
    router.push('/admin/users');
  }, [router, storageKey, sessionToken, deactivateBackendSession]);

  // Countdown effect: tick every second, auto-exit when timer reaches zero.
  useEffect(() => {
    const interval = setInterval(() => {
      const remaining = SESSION_TIMEOUT_MS - (Date.now() - sessionStartTime.getTime());
      if (remaining <= 0) {
        clearInterval(interval);
        if (typeof window !== 'undefined') {
          window.sessionStorage.removeItem(storageKey);
        }
        if (sessionToken) {
          deactivateBackendSession(sessionToken);
        }
        router.push('/admin/users');
        return;
      }
      setTimeRemainingMs(remaining);
    }, 1000);

    return () => clearInterval(interval);
  }, [sessionStartTime, storageKey, router, sessionToken, deactivateBackendSession]);

  const impersonationState: ImpersonationState = {
    isActive: true,
    targetUserId: targetUser.id,
    targetUserEmail: targetUser.email,
    targetPersona: targetUser.persona,
    targetAgentName: targetUser.agentName,
    sessionStartTime,
    timeRemainingMs,
    mode,
    sessionToken,
    impersonatedFetch,
    exitImpersonation,
  };

  // Override PersonaContext with the target user's static values so any
  // component calling usePersona() inside this tree sees the target user.
  const personaOverride = {
    persona: targetUser.persona,
    setPersona: () => {
      // no-op: persona is read-only in impersonation mode
    },
    isLoading: false,
    userId: targetUser.id,
    userEmail: targetUser.email,
    agentName: targetUser.agentName,
  };

  return (
    <ImpersonationContext.Provider value={impersonationState}>
      <PersonaContext.Provider value={personaOverride}>
        {children}
      </PersonaContext.Provider>
    </ImpersonationContext.Provider>
  );
}

/** Returns the current impersonation context or null if not in impersonation mode. */
export function useImpersonation(): ImpersonationState | null {
  return useContext(ImpersonationContext);
}
