import { createClient } from '@/lib/supabase/client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const DEFAULT_FETCH_TIMEOUT_MS = 15000;
const PERSONA_STORAGE_KEY = 'pikar:persona';
const PERSONA_PATH_RE = /^\/(solopreneur|startup|sme|enterprise)(?:\/|$)/;

type FetchOptions = RequestInit & {
  // Add any custom options here if needed
};

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

export async function fetchWithAuth(endpoint: string, options: FetchOptions = {}): Promise<Response> {
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

  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), DEFAULT_FETCH_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: options.signal ?? controller.signal,
    });
    clearTimeout(timeout);

    if (!response.ok) {
      let errorMessage = response.statusText || 'API Request Failed';
      try {
        const errorData = await response.json();
        if (errorData && typeof errorData === 'object' && 'detail' in errorData) {
          errorMessage = JSON.stringify(errorData.detail);
        } else if (errorData && typeof errorData === 'object' && 'message' in errorData) {
          errorMessage = errorData.message;
        }
      } catch (_error) {
        // response was not JSON
      }

      throw new Error(`API Error ${response.status}: ${errorMessage}`);
    }

    return response;
  } catch (error) {
    clearTimeout(timeout);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`API timeout after ${DEFAULT_FETCH_TIMEOUT_MS / 1000}s for ${endpoint}`);
    }
    console.error('Fetch error:', error);
    throw error;
  }
}
