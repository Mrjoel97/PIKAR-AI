// frontend/src/contexts/PersonaContext.tsx
'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { createContext, useContext, useState, ReactNode, useEffect, useRef, useCallback } from 'react';
import { createClient, getAuthenticatedUser } from '@/lib/supabase/client';

type Persona = 'solopreneur' | 'startup' | 'sme' | 'enterprise' | null;
const PERSONA_STORAGE_KEY = 'pikar:persona';
// Persisted across reloads so the dashboard header doesn't flash a generic
// fallback on every mount while the Supabase fetch resolves. Cleared on
// SIGNED_OUT; momentarily stale across cross-account login on the same
// browser, then overwritten by the fetch.
const AGENT_NAME_CACHE_KEY = 'pikar:agent_display_name';
type PersonaAgentRow = { persona: Persona; agent_name: string | null };

interface PersonaContextType {
  persona: Persona;
  setPersona: (persona: Persona) => void;
  isLoading: boolean;
  userId: string | null;
  userEmail: string | null;
  agentName: string | null;
  // Distinguishes "still loading" from "loaded, no custom name set" so
  // consumers can pick between a skeleton and the default fallback.
  agentLoaded: boolean;
}

const PersonaContext = createContext<PersonaContextType | undefined>(undefined);

const PERSONA_FETCH_TIMEOUT_MS = 10_000;
const PERSONA_FETCH_RETRY_DELAY_MS = 2_000;

function withTimeout<T>(promise: Promise<T>, timeoutMs: number, message: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error(message)), timeoutMs);
    promise.then(
      (value) => {
        window.clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        window.clearTimeout(timer);
        reject(error);
      },
    );
  });
}

function isValidPersona(value: string | null): value is Exclude<Persona, null> {
  return value === 'solopreneur' || value === 'startup' || value === 'sme' || value === 'enterprise';
}

function readCookie(name: string): string | null {
  if (typeof document === 'undefined' || !document.cookie) {
    return null;
  }

  const target = `${encodeURIComponent(name)}=`;
  const match = document.cookie
    .split('; ')
    .find((entry) => entry.startsWith(target));

  if (!match) {
    return null;
  }

  return decodeURIComponent(match.slice(target.length));
}

function getCachedAgentName(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    return window.localStorage.getItem(AGENT_NAME_CACHE_KEY);
  } catch {
    return null;
  }
}

function writeCachedAgentName(name: string | null): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    if (name) {
      window.localStorage.setItem(AGENT_NAME_CACHE_KEY, name);
    } else {
      window.localStorage.removeItem(AGENT_NAME_CACHE_KEY);
    }
  } catch {
    // localStorage unavailable — ignore
  }
}

function getCachedPersona(): Persona {
  if (typeof window === 'undefined') {
    return null;
  }

  const sessionPersona = window.sessionStorage.getItem(PERSONA_STORAGE_KEY);
  if (isValidPersona(sessionPersona)) {
    return sessionPersona;
  }

  const cookiePersona = readCookie('x-pikar-persona');
  if (isValidPersona(cookiePersona)) {
    return cookiePersona;
  }

  const pathPersona = window.location.pathname.match(/^\/(solopreneur|startup|sme|enterprise)(?:\/|$)/)?.[1] ?? null;
  return isValidPersona(pathPersona) ? pathPersona : null;
}

export function PersonaProvider({ children }: { children: ReactNode }) {
  const [persona, setPersona] = useState<Persona>(() => getCachedPersona());
  const [isLoading, setIsLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  // Seed from localStorage so a returning user's dashboard header renders
  // the correct name on the very first paint instead of flashing a default
  // while the Supabase query races (the bug behind sometimes-Pikar-AI).
  const [agentName, setAgentName] = useState<string | null>(() => getCachedAgentName());
  const [agentLoaded, setAgentLoaded] = useState(false);
  const hasFetched = useRef(false);

  const fetchPersonaAndAgent = useCallback(async (uid: string, attempt = 0): Promise<void> => {
    try {
      const supabase = createClient();
      const { data, error } = await withTimeout(
        supabase
          .from('user_executive_agents')
          .select('persona, agent_name')
          .eq('user_id', uid)
          .maybeSingle() as Promise<{ data: PersonaAgentRow | null; error: Error | null }>,
        PERSONA_FETCH_TIMEOUT_MS,
        'Persona lookup timed out',
      );

      if (data && !error) {
        setPersona(data.persona as Persona);
        const resolvedName = data.agent_name ?? null;
        setAgentName(resolvedName);
        writeCachedAgentName(resolvedName);
      }
      setAgentLoaded(true);
      setIsLoading(false);
    } catch (err) {
      if (!(err instanceof Error) || err.message !== 'Persona lookup timed out') {
        console.error('Error loading persona and agent:', err);
      }
      // One automatic retry covers transient network blips / cold Supabase
      // pods that the previous 4 s timeout used to lose to permanently.
      if (attempt === 0) {
        window.setTimeout(() => {
          void fetchPersonaAndAgent(uid, 1);
        }, PERSONA_FETCH_RETRY_DELAY_MS);
        return;
      }
      // Second attempt also failed — release the loading state so consumers
      // can fall back to the default display rather than spin forever.
      setAgentLoaded(true);
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (persona) {
      window.sessionStorage.setItem(PERSONA_STORAGE_KEY, persona);
      return;
    }
    window.sessionStorage.removeItem(PERSONA_STORAGE_KEY);
  }, [persona]);

  useEffect(() => {
    const supabase = createClient();
    let cancelled = false;

    const loadUser = async () => {
      const user = await getAuthenticatedUser({ timeoutMs: PERSONA_FETCH_TIMEOUT_MS });
      if (cancelled) {
        return;
      }

      if (user) {
        setUserId(user.id);
        setUserEmail(user.email ?? null);
        setPersona((current) => current ?? getCachedPersona());
        setIsLoading(false);
        if (!hasFetched.current) {
          hasFetched.current = true;
          void fetchPersonaAndAgent(user.id);
        }
      } else {
        setPersona(null);
        setIsLoading(false);
      }
    };

    void loadUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event: string, session: { user: { id: string; email?: string } } | null) => {
        if (event === 'SIGNED_IN' && session?.user) {
          setUserId(session.user.id);
          setUserEmail(session.user.email ?? null);
          setPersona((current) => current ?? getCachedPersona());
          setIsLoading(false);
          if (!hasFetched.current) {
            hasFetched.current = true;
            fetchPersonaAndAgent(session.user.id);
          }
        } else if (event === 'SIGNED_OUT') {
          setPersona(null);
          setUserId(null);
          setUserEmail(null);
          setAgentName(null);
          setAgentLoaded(false);
          writeCachedAgentName(null);
          hasFetched.current = false;
          setIsLoading(false);
        }
      }
    );

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, [fetchPersonaAndAgent]);

  return (
    <PersonaContext.Provider value={{ persona, setPersona, isLoading, userId, userEmail, agentName, agentLoaded }}>
      {children}
    </PersonaContext.Provider>
  );
}

export function usePersona() {
  const context = useContext(PersonaContext);
  if (context === undefined) {
    throw new Error('usePersona must be used within a PersonaProvider');
  }
  return context;
}

export { PersonaContext };
