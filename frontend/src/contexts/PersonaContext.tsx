// frontend/src/contexts/PersonaContext.tsx
'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { createContext, useContext, useState, ReactNode, useEffect, useRef, useCallback } from 'react';
import { createClient, getAuthenticatedUser } from '@/lib/supabase/client';

type Persona = 'solopreneur' | 'startup' | 'sme' | 'enterprise' | null;
const PERSONA_STORAGE_KEY = 'pikar:persona';
type PersonaAgentRow = { persona: Persona; agent_name: string | null };

interface PersonaContextType {
  persona: Persona;
  setPersona: (persona: Persona) => void;
  isLoading: boolean;
  userId: string | null;
  userEmail: string | null;
  agentName: string | null;
}

const PersonaContext = createContext<PersonaContextType | undefined>(undefined);

const PERSONA_FETCH_TIMEOUT_MS = 4000;

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
  const [agentName, setAgentName] = useState<string | null>(null);
  const hasFetched = useRef(false);

  const fetchPersonaAndAgent = useCallback(async (uid: string) => {
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
        setAgentName(data.agent_name ?? null);
      }
    } catch (err) {
      if (!(err instanceof Error) || err.message !== 'Persona lookup timed out') {
        console.error('Error loading persona and agent:', err);
      }
    } finally {
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
    <PersonaContext.Provider value={{ persona, setPersona, isLoading, userId, userEmail, agentName }}>
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
