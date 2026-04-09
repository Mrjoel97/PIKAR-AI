// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { createClient } from '@/lib/supabase/client';

// ============================================================================
// Upgrade-gate event system
// ============================================================================

/**
 * Payload dispatched on the window when a 403 feature-gate response is
 * received from the backend.  Consumed by PremiumShell to show
 * UpgradeGateModal without requiring a global state manager.
 */
export interface UpgradeGateEvent {
  /** Feature key from the backend 403 response (e.g. "compliance"). */
  feature: string;
  /** The user's current persona tier. */
  currentTier: string;
  /** The minimum tier required to access the feature. */
  requiredTier: string;
}

/** Custom DOM event name used to signal a feature-gate 403. */
export const UPGRADE_GATE_EVENT = 'pikar:upgrade-gate';

/**
 * Dispatch a feature-gate custom event on the window.
 * No-op in SSR / non-browser environments.
 */
function dispatchUpgradeGate(detail: UpgradeGateEvent): void {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(UPGRADE_GATE_EVENT, { detail }));
  }
}

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const DEFAULT_FETCH_TIMEOUT_MS = 15000;
const MAX_RETRIES = 3;
const RETRY_BASE_MS = 500;
const RETRYABLE_STATUS_CODES = new Set([408, 429, 500, 502, 503, 504]);
const PERSONA_STORAGE_KEY = 'pikar:persona';
const PERSONA_PATH_RE = /^\/(solopreneur|startup|sme|enterprise)(?:\/|$)/;

type FetchOptions = RequestInit;

export function getClientPersonaHeader(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const stored = window.sessionStorage.getItem(PERSONA_STORAGE_KEY);
  if (stored && ['solopreneur', 'startup', 'sme', 'enterprise'].includes(stored)) {
    return stored;
  }

  const routeMatch = window.location.pathname.match(PERSONA_PATH_RE);
  if (routeMatch?.[1]) {
    return routeMatch[1];
  }

  return null;
}

async function buildHttpError(response: Response): Promise<Error> {
  let errorMessage = response.statusText || 'API Request Failed';
  try {
    const errorData = await response.json();
    if (errorData && typeof errorData === 'object' && 'detail' in errorData) {
      errorMessage = JSON.stringify(errorData.detail);
    } else if (errorData && typeof errorData === 'object' && 'message' in errorData) {
      errorMessage = String(errorData.message);
    }
  } catch (_error) {
    // Response was not JSON.
  }
  return new Error(`API Error ${response.status}: ${errorMessage}`);
}

async function fetchApiInternal(
  endpoint: string,
  options: FetchOptions,
  headers: Headers,
  throwOnHttpError: boolean,
): Promise<Response> {
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  let lastError: Error | undefined;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), DEFAULT_FETCH_TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: options.signal ?? controller.signal,
      });
      clearTimeout(timeout);

      if (response.ok || !RETRYABLE_STATUS_CODES.has(response.status) || attempt === MAX_RETRIES) {
        // Intercept 403 feature-gate responses and fire an upgrade-gate event
        // so UpgradeGateModal can be triggered from any fetchWithAuth call.
        // Use response.clone() so the body is not consumed for the caller.
        if (response.status === 403) {
          try {
            const cloned = response.clone();
            const body = await cloned.json() as { detail?: { feature?: string; current_tier?: string; required_tier?: string } };
            if (body?.detail?.feature) {
              dispatchUpgradeGate({
                feature: body.detail.feature,
                currentTier: body.detail.current_tier ?? '',
                requiredTier: body.detail.required_tier ?? '',
              });
            }
          } catch {
            // Not a feature-gate 403 — let it fall through to normal error handling.
          }
        }

        if (throwOnHttpError && !response.ok) {
          throw await buildHttpError(response);
        }
        return response;
      }

      // Retryable status — will loop
      lastError = new Error(`API Error ${response.status}`);
    } catch (error) {
      clearTimeout(timeout);
      if (error instanceof Error && error.name === 'AbortError') {
        lastError = new Error(`API timeout after ${DEFAULT_FETCH_TIMEOUT_MS / 1000}s for ${endpoint}`);
      } else {
        lastError = error instanceof Error ? error : new Error(String(error));
      }

      // Don't retry if the caller supplied their own abort signal and it triggered
      if (options.signal?.aborted) throw lastError;

      if (attempt === MAX_RETRIES) break;
    }

    // Exponential backoff with jitter: 500ms, 1000ms, 2000ms (+/- 25%)
    const backoff = RETRY_BASE_MS * Math.pow(2, attempt);
    const jitter = backoff * (0.75 + Math.random() * 0.5);
    await new Promise(resolve => setTimeout(resolve, jitter));
  }

  console.error('Fetch failed after retries:', lastError);
  throw lastError;
}

async function fetchWithAuthInternal(
  endpoint: string,
  options: FetchOptions = {},
  throwOnHttpError = true,
): Promise<Response> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();

  const headers = new Headers(options.headers);

  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`);
  }

  const persona = getClientPersonaHeader();
  if (persona && !headers.has('x-pikar-persona')) {
    headers.set('x-pikar-persona', persona);
  }

  return fetchApiInternal(endpoint, options, headers, throwOnHttpError);
}

export async function fetchWithAuth(endpoint: string, options: FetchOptions = {}): Promise<Response> {
  return fetchWithAuthInternal(endpoint, options, true);
}

export async function fetchWithAuthRaw(endpoint: string, options: FetchOptions = {}): Promise<Response> {
  return fetchWithAuthInternal(endpoint, options, false);
}

export async function fetchPublicApi(endpoint: string, options: FetchOptions = {}, throwOnHttpError = true): Promise<Response> {
  return fetchApiInternal(endpoint, options, new Headers(options.headers), throwOnHttpError);
}
