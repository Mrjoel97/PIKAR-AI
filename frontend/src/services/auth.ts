import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';

export const signUp = async (email: string, password: string) => {
  const supabase = createClientComponentClient();
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: `${window.location.origin}/auth/callback`,
    },
  });
  if (error) throw error;
  return data;
};

export const signIn = async (email: string, password: string) => {
  const supabase = createClientComponentClient();
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });
  if (error) throw error;
  return data;
};

export const signOut = async () => {
  const supabase = createClientComponentClient();
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
};
