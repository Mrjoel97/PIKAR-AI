// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// -----------------------------------------------------------------------------
// Next.js 16 root proxy (formerly known as middleware.ts).
//
// This file is the FIRST gate every request hits. It runs BEFORE any page
// HTML, RSC payload, or layout is streamed to the browser, so unauthenticated
// visitors can never see the shell of a protected page.
//
// Why proxy.ts and not middleware.ts?
//   Next.js 16 renamed the convention. The file MUST live at the project root
//   (sibling to package.json) and MUST be named `proxy.ts`.
//
// Why getClaims() and not getSession()?
//   getSession() trusts the raw cookie, which can be spoofed in server-side
//   contexts. getClaims() validates the JWT signature against the published
//   JWKS on every call — see frontend/src/lib/supabase/proxy.ts.
//
// Defence in depth:
//   - frontend/src/components/auth/ProtectedRoute.tsx is intentionally
//     retained as a client-side fallback for any branch this proxy may not
//     cover (Phase 53 may revisit).
//   - frontend/src/app/(admin)/layout.tsx already runs its own server-side
//     session check; this proxy adds a gate IN FRONT of that check.
// -----------------------------------------------------------------------------

import { createServerClient } from '@supabase/ssr';
import { NextRequest, NextResponse } from 'next/server';
import { updateSession } from '@/lib/supabase/proxy';

/**
 * Path prefixes that REQUIRE an authenticated session. A request whose
 * pathname equals one of these prefixes OR starts with `<prefix>/` is
 * gated by the proxy.
 *
 * Keep this list narrow: anything not listed here is treated as public.
 */
const PROTECTED_PREFIXES = [
  '/dashboard',
  '/settings',
  '/admin',
  '/onboarding',
  '/approval',
  '/departments',
  '/org-chart',
  '/solopreneur',
  '/startup',
  '/sme',
  '/enterprise',
] as const;

const PERSONA_ROUTE_PREFIXES = [
  '/solopreneur',
  '/startup',
  '/sme',
  '/enterprise',
] as const;

function isProtected(pathname: string): boolean {
  return PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

function copyResponseCookies(from: NextResponse, to: NextResponse) {
  for (const cookie of from.cookies.getAll()) {
    to.cookies.set(cookie);
  }
}

function buildLoginRedirect(request: NextRequest, response: NextResponse, pathname: string) {
  const loginUrl = new URL('/auth/login', request.url);
  loginUrl.searchParams.set('next', pathname);
  const redirect = NextResponse.redirect(loginUrl);
  copyResponseCookies(response, redirect);
  return redirect;
}

function buildRedirectWithCookies(
  request: NextRequest,
  response: NextResponse,
  pathname: string,
) {
  const redirect = NextResponse.redirect(new URL(pathname, request.url));
  copyResponseCookies(response, redirect);
  return redirect;
}

function createProxySupabaseClient(request: NextRequest, response: NextResponse) {
  const supabaseUrl =
    process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co';
  const supabaseAnonKey =
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder-anon-key';

  return createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        for (const { name, value } of cookiesToSet) {
          request.cookies.set(name, value);
        }
        for (const { name, value, options } of cookiesToSet) {
          response.cookies.set(name, value, options);
        }
      },
    },
  });
}

function cachePersonaState(
  response: NextResponse,
  request: NextRequest,
  isOnboarded: boolean,
  persona: string | null | undefined,
) {
  const secure = request.nextUrl.protocol === 'https:';
  const options = {
    path: '/',
    maxAge: 300,
    httpOnly: true,
    sameSite: 'lax' as const,
    secure,
  };

  response.cookies.set('x-pikar-onboarded', String(isOnboarded), options);
  response.cookies.set('x-pikar-persona', persona || 'none', options);
}

/**
 * Root proxy entry point. Next.js calls this for every request that matches
 * the `config.matcher` below.
 *
 * Flow:
 *   1. Refresh the Supabase session for EVERY request (not just protected
 *      ones) so downstream RSCs always see fresh tokens.
 *   2. If the request is for a protected path AND the user has no valid
 *      claims, redirect to /auth/login with the original path preserved in
 *      ?next= so the login page can return the user where they intended.
 *   3. Otherwise return the response from updateSession() — which carries
 *      any refreshed Set-Cookie headers back to the browser.
 */
export async function proxy(request: NextRequest): Promise<NextResponse> {
  const { pathname } = request.nextUrl;

  const { response, claims } = await updateSession(request);

  if (isProtected(pathname) && !claims) {
    return buildLoginRedirect(request, response, pathname);
  }

  if (!claims) {
    return response;
  }

  const isOnboardingPath =
    pathname === '/onboarding' || pathname.startsWith('/onboarding/');
  const isSettingsPath =
    pathname === '/settings' ||
    pathname.startsWith('/settings/') ||
    pathname === '/dashboard/settings' ||
    pathname.startsWith('/dashboard/settings/');
  const isAdminPath = pathname === '/admin' || pathname.startsWith('/admin/');

  if (isOnboardingPath) {
    response.cookies.delete('x-pikar-persona');
    response.cookies.delete('x-pikar-onboarded');
    return response;
  }

  if (isProtected(pathname) && !isSettingsPath && !isAdminPath) {
    try {
      const cachedPersona = request.cookies.get('x-pikar-persona')?.value;
      const cachedOnboarded = request.cookies.get('x-pikar-onboarded')?.value;

      let isOnboarded: boolean;
      let persona: string | null | undefined;

      if (cachedOnboarded !== undefined && cachedPersona) {
        isOnboarded = cachedOnboarded === 'true';
        persona = cachedPersona === 'none' ? null : cachedPersona;
      } else {
        const supabase = createProxySupabaseClient(request, response);
        const { data: agentProfile } = await supabase
          .from('user_executive_agents')
          .select('onboarding_completed, persona')
          .eq('user_id', claims.sub)
          .maybeSingle();

        isOnboarded = agentProfile?.onboarding_completed === true;
        persona = agentProfile?.persona;
        cachePersonaState(response, request, isOnboarded, persona);
      }

      if (!isOnboarded) {
        const redirect = buildRedirectWithCookies(request, response, '/onboarding');
        cachePersonaState(redirect, request, false, persona);
        return redirect;
      }

      if (persona && pathname === '/dashboard') {
        return buildRedirectWithCookies(request, response, `/${persona}`);
      }

      const matchedPersonaPrefix = PERSONA_ROUTE_PREFIXES.find(
        (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
      );
      if (persona && matchedPersonaPrefix) {
        const routePersona = matchedPersonaPrefix.slice(1);
        if (routePersona !== persona) {
          return buildRedirectWithCookies(request, response, `/${persona}`);
        }
      }
    } catch (error) {
      console.error('Proxy profile check error:', error);
    }
  }

  return response;
}

/**
 * Run on every request EXCEPT:
 *   - /api/*           (backend handles its own auth via verify_token)
 *   - /_next/static/*  (Next.js build output)
 *   - /_next/image/*   (image optimiser)
 *   - /favicon.ico, /robots.txt
 *   - any file with a static asset extension (images, fonts, etc.)
 *
 * The matcher is the cheapest gate — it skips invocation entirely for
 * excluded paths so we never pay the Supabase round-trip on static assets.
 */
export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|robots.txt|.*\\.(?:png|jpg|jpeg|gif|svg|webp|woff|woff2|ttf|ico)$).*)',
  ],
};
