// frontend/src/contexts/PersonaContext.tsx
'use client';

import { createContext, useContext, useState, ReactNode, useEffect } from 'react';
import { createClient } from '@/lib/supabase/client';

type Persona = 'solopreneur' | 'startup' | 'sme' | 'enterprise' | null;

interface PersonaContextType {
  persona: Persona;
  setPersona: (persona: Persona) => void;
  isLoading: boolean;
}

const PersonaContext = createContext<PersonaContextType | undefined>(undefined);

export function PersonaProvider({ children }: { children: ReactNode }) {
  const [persona, setPersona] = useState<Persona>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadPersona() {
      try {
        const supabase = createClient();
        const { data: { session } } = await supabase.auth.getSession();

        if (session?.user) {
          const { data, error } = await supabase
            .from('user_executive_agents')
            .select('persona')
            .eq('user_id', session.user.id)
            .maybeSingle();

          if (data && !error) {
            setPersona(data.persona as Persona);
          }
        }
      } catch (err) {
        console.error('Error loading persona:', err);
      } finally {
        setIsLoading(false);
      }
    }

    loadPersona();
  }, []);

  return (
    <PersonaContext.Provider value={{ persona, setPersona, isLoading }}>
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