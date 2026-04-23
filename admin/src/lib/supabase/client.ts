// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { createBrowserClient } from '@supabase/ssr';

// Fallback values allow the build (static page generation) to succeed
// even when env vars are not set. At runtime, the real values are required.
const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co';
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder-anon-key';

let browserClient: ReturnType<typeof createBrowserClient> | null = null;
const PKCE_COOKIE_MARKER = '-code-verifier';
const PKCE_MIRROR_PREFIX = 'pikar-admin-pkce:';

function parseBrowserCookies() {
  if (typeof document === 'undefined') {
    return [];
  }

  return document.cookie
    .split(';')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const separatorIndex = part.indexOf('=');
      if (separatorIndex === -1) {
        return { name: part, value: '' };
      }

      return {
        name: decodeURIComponent(part.slice(0, separatorIndex)),
        value: decodeURIComponent(part.slice(separatorIndex + 1)),
      };
    });
}

function isPkceCookieName(name: string) {
  return name.includes(PKCE_COOKIE_MARKER);
}

function getPkceMirrorEntries() {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    const entries: Array<{ name: string; value: string }> = [];

    for (let index = 0; index < window.sessionStorage.length; index += 1) {
      const storageKey = window.sessionStorage.key(index);
      if (!storageKey || !storageKey.startsWith(PKCE_MIRROR_PREFIX)) {
        continue;
      }

      const value = window.sessionStorage.getItem(storageKey);
      if (!value) {
        continue;
      }

      entries.push({
        name: storageKey.slice(PKCE_MIRROR_PREFIX.length),
        value,
      });
    }

    return entries;
  } catch {
    return [];
  }
}

function mirrorPkceCookie(name: string, value: string) {
  if (typeof window === 'undefined' || !isPkceCookieName(name)) {
    return;
  }

  try {
    if (value) {
      window.sessionStorage.setItem(`${PKCE_MIRROR_PREFIX}${name}`, value);
    } else {
      window.sessionStorage.removeItem(`${PKCE_MIRROR_PREFIX}${name}`);
    }
  } catch {
    // Ignore storage failures and fall back to cookies-only behavior.
  }
}

export function createClient() {
  if (typeof window === 'undefined') {
    return createBrowserClient(supabaseUrl, supabaseAnonKey);
  }

  if (!browserClient) {
    browserClient = createBrowserClient(supabaseUrl, supabaseAnonKey, {
      cookies: {
        getAll() {
          const cookieEntries = parseBrowserCookies();
          const cookieNames = new Set(cookieEntries.map(({ name }) => name));
          const mirroredPkceEntries = getPkceMirrorEntries().filter(
            ({ name }) => !cookieNames.has(name),
          );

          return [...cookieEntries, ...mirroredPkceEntries];
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            let serialized = `${encodeURIComponent(name)}=${encodeURIComponent(value)}`;

            const path = options?.path ?? '/';
            serialized += `; path=${path}`;

            if (typeof options?.maxAge === 'number') {
              serialized += `; max-age=${options.maxAge}`;
            }

            if (options?.sameSite) {
              serialized += `; samesite=${options.sameSite}`;
            }

            if (options?.domain) {
              serialized += `; domain=${options.domain}`;
            }

            if (options?.secure) {
              serialized += '; secure';
            }

            if (options?.httpOnly) {
              serialized += '; httponly';
            }

            document.cookie = serialized;
            mirrorPkceCookie(name, value);
          });
        },
      },
    });
  }

  return browserClient;
}
