// frontend/src/contexts/ImpersonationContext.tsx
'use client';

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import { useRouter } from 'next/navigation';
import { PersonaContext } from '@/contexts/PersonaContext';

type Persona = 'solopreneur' | 'startup' | 'sme' | 'enterprise' | null;

/** Shape of the impersonation session state provided to consumers. */
interface ImpersonationState {
  isActive: boolean;
  targetUserId: string;
  targetUserEmail: string;
  targetPersona: Persona;
  targetAgentName: string | null;
  sessionStartTime: Date;
  timeRemainingMs: number;
  exitImpersonation: () => void;
}

/** Target user data required to start an impersonation session. */
interface TargetUser {
  id: string;
  email: string;
  persona: Persona;
  agentName: string | null;
}

const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes

const ImpersonationContext = createContext<ImpersonationState | null>(null);

/**
 * ImpersonationProvider wraps the impersonation view content.
 * It overrides PersonaContext with the target user's static data so any
 * child component calling usePersona() receives the target user's values.
 * A 30-minute session timer is persisted in sessionStorage to survive
 * navigation within the impersonation view.
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

  const exitImpersonation = useCallback(() => {
    if (typeof window !== 'undefined') {
      window.sessionStorage.removeItem(storageKey);
    }
    router.push('/admin/users');
  }, [router, storageKey]);

  // Countdown effect: tick every second, auto-exit when timer reaches zero.
  useEffect(() => {
    const interval = setInterval(() => {
      const remaining = SESSION_TIMEOUT_MS - (Date.now() - sessionStartTime.getTime());
      if (remaining <= 0) {
        clearInterval(interval);
        if (typeof window !== 'undefined') {
          window.sessionStorage.removeItem(storageKey);
        }
        router.push('/admin/users');
        return;
      }
      setTimeRemainingMs(remaining);
    }, 1000);

    return () => clearInterval(interval);
  }, [sessionStartTime, storageKey, router]);

  const impersonationState: ImpersonationState = {
    isActive: true,
    targetUserId: targetUser.id,
    targetUserEmail: targetUser.email,
    targetPersona: targetUser.persona,
    targetAgentName: targetUser.agentName,
    sessionStartTime,
    timeRemainingMs,
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
