// frontend/src/contexts/PersonaContext.tsx
'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { createContext, useContext, useState, ReactNode, useEffect, useRef, useCallback } from 'react';
import { isAbortLikeError } from '@/lib/abort';
import { createClient } from '@/lib/supabase/client';

type Persona = 'solopreneur' | 'startup' | 'sme' | 'enterprise' | null;
const PERSONA_STORAGE_KEY = 'pikar:persona';

interface PersonaContextType {
  persona: Persona;
  setPersona: (persona: Persona) => void;
  isLoading: boolean;
  userId: string | null;
  userEmail: string | null;
  agentName: string | null;
}

const PersonaContext = createContext<PersonaContextType | undefined>(undefined);

export function PersonaProvider({ children }: { children: ReactNode }) {
  const [persona, setPersona] = useState<Persona>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [agentName, setAgentName] = useState<string | null>(null);
  const hasFetched = useRef(false);

  const fetchPersonaAndAgent = useCallback(async (uid: string) => {
    try {
      const supabase = createClient();
      const { data, error } = await supabase
        .from('user_executive_agents')
        .select('persona, agent_name')
        .eq('user_id', uid)
        .maybeSingle();

      if (data && !error) {
        setPersona(data.persona as Persona);
        setAgentName(data.agent_name ?? null);
      }
    } catch (err) {
      console.error('Error loading persona and agent:', err);
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
    let active = true;

    const loadUser = async () => {
      try {
        const { data: { user } } = await supabase.auth.getUser();
        if (!active) {
          return;
        }

        if (user) {
          setUserId(user.id);
          setUserEmail(user.email ?? null);
          if (!hasFetched.current) {
            hasFetched.current = true;
            fetchPersonaAndAgent(user.id);
          }
        } else {
          setIsLoading(false);
        }
      } catch (error) {
        if (!isAbortLikeError(error)) {
          console.error('Error loading current user persona:', error);
        }
        if (active) {
          setIsLoading(false);
        }
      }
    };

    void loadUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event: string, session: { user: { id: string; email?: string } } | null) => {
        if (event === 'SIGNED_IN' && session?.user) {
          setUserId(session.user.id);
          setUserEmail(session.user.email ?? null);
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
      active = false;
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
