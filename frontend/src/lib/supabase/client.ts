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
let hasWarnedAccessTokenFallback = false;

const SUPABASE_COOKIE_PREFIX = 'base64-';
const DEFAULT_SESSION_LOOKUP_TIMEOUT_MS = 2500;

type StoredSupabaseSession = {
  access_token?: string | null;
};

export type AuthenticatedUserSnapshot = {
  id: string;
  email?: string | null;
};

function withTimeout<T>(
  promise: Promise<T>,
  timeoutMs = DEFAULT_SESSION_LOOKUP_TIMEOUT_MS,
  message = 'Supabase session lookup timed out',
): Promise<T> {
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

export function getSupabaseAuthStorageKey(): string | null {
  const prefix = getSupabaseStorageKeyPrefix();
  return prefix ? `${prefix}-auth-token` : null;
}

export function getSupabaseStorageKeyPrefix(): string | null {
  try {
    return `sb-${new URL(supabaseUrl).hostname.split('.')[0]}`;
  } catch {
    return null;
  }
}

function getCookieEntries(): Array<{ name: string; value: string }> {
  if (typeof document === 'undefined' || !document.cookie) {
    return [];
  }

  return document.cookie
    .split('; ')
    .map((entry) => {
      const separatorIndex = entry.indexOf('=');
      if (separatorIndex === -1) {
        return { name: entry, value: '' };
      }

      return {
        name: decodeURIComponent(entry.slice(0, separatorIndex)),
        value: entry.slice(separatorIndex + 1),
      };
    });
}

function clearStorageEntriesWithPrefix(storage: Storage, prefix: string) {
  const keysToRemove: string[] = [];

  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index);
    if (key?.startsWith(prefix)) {
      keysToRemove.push(key);
    }
  }

  keysToRemove.forEach((key) => storage.removeItem(key));
}

function expireCookie(name: string) {
  if (typeof document === 'undefined' || typeof window === 'undefined') {
    return;
  }

  const secure = window.location.protocol === 'https:' ? '; Secure' : '';
  document.cookie = `${encodeURIComponent(name)}=; Max-Age=0; Path=/; SameSite=Lax${secure}`;
}

function readChunkedCookieValue(storageKey: string): string | null {
  const matchingCookies = getCookieEntries()
    .filter(({ name }) => name === storageKey || name.startsWith(`${storageKey}.`))
    .sort((left, right) => {
      const leftSuffix = left.name === storageKey ? -1 : Number.parseInt(left.name.slice(storageKey.length + 1), 10);
      const rightSuffix = right.name === storageKey ? -1 : Number.parseInt(right.name.slice(storageKey.length + 1), 10);
      return leftSuffix - rightSuffix;
    });

  if (matchingCookies.length === 0) {
    return null;
  }

  return matchingCookies.map(({ value }) => value).join('');
}

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=');

  if (typeof window !== 'undefined' && typeof window.atob === 'function') {
    const binary = window.atob(padded);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  }

  if (typeof Buffer !== 'undefined') {
    return Buffer.from(padded, 'base64').toString('utf-8');
  }

  throw new Error('Unable to decode Supabase auth cookie');
}

function parseStoredSession(rawValue: string): StoredSupabaseSession | null {
  try {
    const decodedValue = rawValue.startsWith(SUPABASE_COOKIE_PREFIX)
      ? decodeBase64Url(rawValue.slice(SUPABASE_COOKIE_PREFIX.length))
      : rawValue;
    return JSON.parse(decodedValue) as StoredSupabaseSession;
  } catch {
    return null;
  }
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const segments = token.split('.');
  if (segments.length < 2) {
    return null;
  }

  try {
    return JSON.parse(decodeBase64Url(segments[1])) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function getStoredAccessToken(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }

  const storageKey = getSupabaseAuthStorageKey();
  if (!storageKey) {
    return null;
  }

  const rawSession = readChunkedCookieValue(storageKey);
  if (!rawSession) {
    return null;
  }

  return parseStoredSession(rawSession)?.access_token ?? null;
}

export function getUserFromAccessToken(token: string | null): AuthenticatedUserSnapshot | null {
  if (!token) {
    return null;
  }

  const payload = decodeJwtPayload(token);
  const id = typeof payload?.sub === 'string' ? payload.sub : null;
  if (!id) {
    return null;
  }

  return {
    id,
    email: typeof payload?.email === 'string' ? payload.email : null,
  };
}

export function clearSupabaseBrowserState() {
  if (typeof window === 'undefined') {
    return;
  }

  const storagePrefix = getSupabaseStorageKeyPrefix();
  if (storagePrefix) {
    try {
      clearStorageEntriesWithPrefix(window.localStorage, storagePrefix);
    } catch {
      // Ignore browser storage access failures.
    }

    try {
      clearStorageEntriesWithPrefix(window.sessionStorage, storagePrefix);
    } catch {
      // Ignore browser storage access failures.
    }

    getCookieEntries()
      .filter(({ name }) => name.startsWith(storagePrefix))
      .forEach(({ name }) => expireCookie(name));
  }

  browserClient = null;
  hasWarnedAccessTokenFallback = false;
}

export async function getAccessToken(options?: {
  timeoutMs?: number;
}): Promise<string | null> {
  const storedToken = getStoredAccessToken();
  if (storedToken) {
    return storedToken;
  }

  const client = createClient();

  try {
    const sessionResult: Awaited<ReturnType<typeof client.auth.getSession>> = await withTimeout(
      client.auth.getSession(),
      options?.timeoutMs,
    );
    const session = sessionResult.data.session;

    return session?.access_token ?? getStoredAccessToken();
  } catch (error) {
    const fallbackToken = getStoredAccessToken();
    if (fallbackToken) {
      if (!hasWarnedAccessTokenFallback) {
        hasWarnedAccessTokenFallback = true;
        console.warn(
          '[supabase] Falling back to cookie-backed access token after getSession failed.',
          error,
        );
      }
      return fallbackToken;
    }

    throw error;
  }
}

export async function getAuthenticatedUser(options?: {
  timeoutMs?: number;
}): Promise<AuthenticatedUserSnapshot | null> {
  const storedUser = getUserFromAccessToken(getStoredAccessToken());
  if (storedUser) {
    return storedUser;
  }

  const client = createClient();

  try {
    const userResult: Awaited<ReturnType<typeof client.auth.getUser>> = await withTimeout(
      client.auth.getUser(),
      options?.timeoutMs,
      'Supabase user lookup timed out',
    );
    const user = userResult.data.user;
    if (user) {
      return {
        id: user.id,
        email: user.email ?? null,
      };
    }
  } catch {
    // Fall through to token-backed fallback.
  }

  const fallbackToken = await getAccessToken(options).catch(() => null);
  return getUserFromAccessToken(fallbackToken);
}

export function createClient() {
  if (typeof window === 'undefined') {
    return createBrowserClient(supabaseUrl, supabaseAnonKey);
  }

  if (!browserClient) {
    browserClient = createBrowserClient(supabaseUrl, supabaseAnonKey);
  }

  return browserClient;
}
