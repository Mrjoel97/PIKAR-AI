// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { clearSupabaseBrowserState, createClient } from '@/lib/supabase/client';

const PERSONA_STORAGE_KEY = 'pikar:persona';
const SESSION_CONTROL_STORAGE_KEY = 'pikar_current_session_id';
const AUTH_OPERATION_TIMEOUT_MS = 3000;

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

function normalizeError(error: unknown): Error {
  return error instanceof Error ? error : new Error(String(error));
}

function clearClientAuthArtifacts() {
  if (typeof window === 'undefined') {
    return;
  }

  window.sessionStorage.removeItem(PERSONA_STORAGE_KEY);
  window.localStorage.removeItem(SESSION_CONTROL_STORAGE_KEY);
  window.sessionStorage.removeItem(SESSION_CONTROL_STORAGE_KEY);

  const secure = window.location.protocol === 'https:' ? '; Secure' : '';
  document.cookie = `x-pikar-persona=; Max-Age=0; Path=/; SameSite=Lax${secure}`;
  document.cookie = `x-pikar-onboarded=; Max-Age=0; Path=/; SameSite=Lax${secure}`;
  clearSupabaseBrowserState();
}

export const signUp = async (email: string, password: string, fullName?: string) => {
  const supabase = createClient();
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: `${window.location.origin}/auth/callback`,
      data: fullName ? { full_name: fullName } : undefined,
    },
  });
  if (error) throw error;
  return data;
};

export const signIn = async (email: string, password: string) => {
  const supabase = createClient();
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });
  if (error) throw error;
  return data;
};

export const signInWithGoogle = async () => {
  const supabase = createClient();
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: `${window.location.origin}/auth/callback`,
      scopes: 'email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/calendar',
      queryParams: {
        access_type: 'offline',
        prompt: 'consent',
      },
    },
  });
  if (error) throw error;
  return data;
};

export const signOut = async (options?: { redirectTo?: string; redirect?: boolean }) => {
  const supabase = createClient();
  let finalError: Error | null = null;

  // Prefer a full logout, but fall back to local logout so the UI always
  // clears the session even if the network/global sign-out step fails.
  try {
    const globalSignOutResult: Awaited<ReturnType<typeof supabase.auth.signOut>> = await withTimeout(
      supabase.auth.signOut(),
      AUTH_OPERATION_TIMEOUT_MS,
      'Supabase sign-out timed out',
    );
    const { error } = globalSignOutResult;
    if (error) {
      finalError = normalizeError(error);
      const localSignOutResult: Awaited<ReturnType<typeof supabase.auth.signOut>> = await withTimeout(
        supabase.auth.signOut({ scope: 'local' }),
        AUTH_OPERATION_TIMEOUT_MS,
        'Local sign-out timed out',
      );
      const { error: localError } = localSignOutResult;
      if (!localError) {
        finalError = null;
      } else {
        finalError = normalizeError(localError);
      }
    }
  } catch (error) {
    finalError = normalizeError(error);
    try {
      const localSignOutResult: Awaited<ReturnType<typeof supabase.auth.signOut>> = await withTimeout(
        supabase.auth.signOut({ scope: 'local' }),
        AUTH_OPERATION_TIMEOUT_MS,
        'Local sign-out timed out',
      );
      const { error: localError } = localSignOutResult;
      if (!localError) {
        finalError = null;
      } else {
        finalError = normalizeError(localError);
      }
    } catch {
      // Keep the original error; we still clear client-side artifacts below.
    }
  }

  clearClientAuthArtifacts();

  if (options?.redirect && typeof window !== 'undefined') {
    window.location.assign(options.redirectTo ?? '/auth/login');
  }

  if (finalError) throw finalError;
};

export const resetPasswordForEmail = async (email: string) => {
  const supabase = createClient();
  const { data, error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${window.location.origin}/auth/reset-password`,
  });
  if (error) throw error;
  return data;
};

export const updateUser = async (params: { password?: string }) => {
  const supabase = createClient();
  const { data, error } = await supabase.auth.updateUser(params);
  if (error) throw error;
  return data;
};
