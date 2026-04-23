// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { createBrowserClient } from '@supabase/ssr';

// Fallback values allow the build (static page generation) to succeed
// even when env vars are not set. At runtime, the real values are required.
const supabaseUrl =
  process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co';
const supabaseAnonKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder-anon-key';
const authStorageKey = `sb-${new URL(supabaseUrl).hostname.split('.')[0]}-auth-token`;

let browserClient: ReturnType<typeof createBrowserClient> | null = null;
const PKCE_COOKIE_MARKER = '-code-verifier';
const PKCE_MIRROR_PREFIX = 'pikar-admin-pkce:';
const PKCE_COOKIE_MAX_AGE_SECONDS = 400 * 24 * 60 * 60;

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

function writeBrowserCookie(
  name: string,
  value: string,
  options: {
    path?: string;
    maxAge?: number;
    sameSite?: boolean | 'lax' | 'strict' | 'none';
    domain?: string;
    secure?: boolean;
    httpOnly?: boolean;
  } = {},
) {
  if (typeof document === 'undefined') {
    return;
  }

  let serialized = `${encodeURIComponent(name)}=${encodeURIComponent(value)}`;

  const path = options.path ?? '/';
  serialized += `; path=${path}`;

  if (typeof options.maxAge === 'number') {
    serialized += `; max-age=${options.maxAge}`;
  }

  if (options.sameSite && typeof options.sameSite === 'string') {
    serialized += `; samesite=${options.sameSite}`;
  }

  if (options.domain) {
    serialized += `; domain=${options.domain}`;
  }

  if (options.secure) {
    serialized += '; secure';
  }

  if (options.httpOnly) {
    serialized += '; httponly';
  }

  document.cookie = serialized;
}

function encodeBase64Url(bytes: Uint8Array) {
  const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join('');
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

async function generatePkcePair() {
  const verifierBytes = new Uint8Array(32);
  crypto.getRandomValues(verifierBytes);
  const verifier = Array.from(verifierBytes, (byte) => byte.toString(16).padStart(2, '0')).join(
    '',
  );

  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  const challenge = encodeBase64Url(new Uint8Array(digest));

  return { verifier, challenge };
}

export async function buildAdminGoogleOAuthUrl(redirectTo: string) {
  const { verifier, challenge } = await generatePkcePair();
  const verifierStorageValue = JSON.stringify(verifier);
  const verifierKey = `${authStorageKey}-code-verifier`;

  writeBrowserCookie(verifierKey, verifierStorageValue, {
    path: '/',
    maxAge: PKCE_COOKIE_MAX_AGE_SECONDS,
    sameSite: 'lax',
    secure: window.location.protocol === 'https:',
  });
  mirrorPkceCookie(verifierKey, verifierStorageValue);

  const authorizeUrl = new URL('/auth/v1/authorize', supabaseUrl);
  authorizeUrl.searchParams.set('provider', 'google');
  authorizeUrl.searchParams.set('redirect_to', redirectTo);
  authorizeUrl.searchParams.set('scopes', 'email profile');
  authorizeUrl.searchParams.set('code_challenge', challenge);
  authorizeUrl.searchParams.set('code_challenge_method', 's256');
  authorizeUrl.searchParams.set('prompt', 'select_account');

  return authorizeUrl.toString();
}

export function createClient() {
  if (typeof window === 'undefined') {
    return createBrowserClient(supabaseUrl, supabaseAnonKey);
  }

  if (!browserClient) {
    browserClient = createBrowserClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        storageKey: authStorageKey,
      },
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
            writeBrowserCookie(name, value, options);
            mirrorPkceCookie(name, value);
          });
        },
      },
    });
  }

  return browserClient;
}
