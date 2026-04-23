// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { createBrowserClient } from '@supabase/ssr';

// Fallback values allow the build (static page generation) to succeed
// even when env vars are not set. At runtime, the real values are required.
const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co';
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder-anon-key';
const authStorageKey = `sb-${
  new URL(supabaseUrl).hostname.split('.')[0]
}-auth-token`;

let browserClient: ReturnType<typeof createBrowserClient> | null = null;

export function createClient() {
  if (typeof window === 'undefined') {
    return createBrowserClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        storageKey: authStorageKey,
      },
    });
  }

  if (!browserClient) {
    browserClient = createBrowserClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        storageKey: authStorageKey,
      },
    });
  }

  return browserClient;
}
