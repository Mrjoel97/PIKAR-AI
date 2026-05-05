// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { createClient as createSupabaseClient, type SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co';
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder-anon-key';
const authStorageKey = `sb-${
  new URL(supabaseUrl).hostname.split('.')[0]
}-auth-token`;

let browserClient: SupabaseClient | null = null;

// Browser client uses plain @supabase/supabase-js with localStorage storage.
// This intentionally bypasses cookie storage because some browsers (Brave
// Shields, Safari ITP, Firefox Total Cookie Protection) clear cookies during
// the cross-site OAuth round-trip, which strands the PKCE verifier and breaks
// sign-in. localStorage is origin-scoped and not affected by those policies.
//
// After OAuth exchange completes client-side, the session tokens are POSTed
// to /auth/session, which uses createServerClient (cookie-based) to write
// the SSR session cookies that route guards and server components read.
export function createClient(): SupabaseClient {
  if (typeof window === 'undefined') {
    return createSupabaseClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        storageKey: authStorageKey,
        flowType: 'pkce',
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    });
  }

  if (!browserClient) {
    browserClient = createSupabaseClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        storageKey: authStorageKey,
        flowType: 'pkce',
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        storage: window.localStorage,
      },
    });
  }

  return browserClient;
}
