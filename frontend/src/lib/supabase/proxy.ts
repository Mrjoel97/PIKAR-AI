// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { createServerClient } from '@supabase/ssr';
import { NextRequest, NextResponse } from 'next/server';

/**
 * Validated JWT claims returned by Supabase getClaims().
 *
 * Only the fields the proxy actually consumes are projected here. The full
 * claim payload is intentionally NOT exported because it varies by JWT
 * issuer configuration and we want a stable downstream contract.
 */
export type ProxyClaims = { sub: string; email?: string } | null;

/**
 * Result of refreshing the Supabase session for an incoming proxy request.
 *
 * `response` MUST be the same object that the proxy ultimately returns to
 * Next.js — creating a fresh NextResponse mid-flow drops any refreshed
 * Set-Cookie headers and breaks transparent token rotation.
 */
export type UpdateSessionResult = {
  response: NextResponse;
  claims: ProxyClaims;
};

/**
 * Refresh the Supabase session for an incoming proxy request and return
 * both the outgoing response (with any refreshed cookies attached) and the
 * validated JWT claims.
 *
 * IMPORTANT: This uses `getClaims()` — NOT `getSession()`. `getSession()`
 * trusts the raw cookie which can be spoofed in server-side contexts.
 * `getClaims()` validates the JWT signature against the published JWKS on
 * every call, so the proxy never trusts an unverified token.
 *
 * The function is shaped so that the SAME response object is reused across
 * the entire flow. When Supabase calls our `setAll()` cookie adapter
 * (which happens during silent refresh), we mirror the new cookies onto
 * the request (so any downstream RSCs see them) and rebuild the response
 * (so the browser receives the new Set-Cookie headers).
 */
export async function updateSession(
  request: NextRequest,
): Promise<UpdateSessionResult> {
  // CRITICAL: a single response object MUST be reused throughout this
  // function so refreshed Set-Cookie headers are not dropped.
  let response = NextResponse.next({ request });

  // Read env at call-time so the proxy picks up runtime values rather than
  // any placeholder captured at module load (the build can run with empty
  // env vars; the request handler must always use the real ones).
  const supabaseUrl =
    process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co';
  const supabaseAnonKey =
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder-anon-key';

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        // Mirror refreshed cookies to BOTH the request (for downstream RSCs)
        // and the response (for the browser).
        for (const { name, value } of cookiesToSet) {
          request.cookies.set(name, value);
        }
        response = NextResponse.next({ request });
        for (const { name, value, options } of cookiesToSet) {
          response.cookies.set(name, value, options);
        }
      },
    },
  });

  const { data, error } = await supabase.auth.getClaims();
  if (error || !data?.claims) {
    return { response, claims: null };
  }

  const sub = data.claims.sub;
  const email = (data.claims as { email?: unknown }).email;
  return {
    response,
    claims: {
      sub: typeof sub === 'string' ? sub : String(sub),
      email: typeof email === 'string' ? email : undefined,
    },
  };
}
