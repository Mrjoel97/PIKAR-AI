import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { createServerClient } from '@supabase/ssr';

// Routes that require completed onboarding
const PROTECTED_ROUTES = ['/dashboard', '/solopreneur', '/startup', '/sme', '/enterprise', '/settings'];

// Routes that should be accessible without onboarding
const PUBLIC_ROUTES = ['/auth', '/onboarding', '/privacy', '/terms', '/'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip for public routes, API routes, and static assets
  if (
    PUBLIC_ROUTES.some((route) => pathname === route || pathname.startsWith(route + '/')) ||
    pathname.startsWith('/api') ||
    pathname.startsWith('/_next') ||
    pathname.startsWith('/favicon') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  // Check if this is a protected route
  const isProtected = PROTECTED_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route + '/')
  );

  if (!isProtected) {
    return NextResponse.next();
  }

  // Create Supabase client for middleware
  const response = NextResponse.next();

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            response.cookies.set(name, value, options);
          });
        },
      },
    }
  );

  try {
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
      // Not authenticated — redirect to login
      const loginUrl = new URL('/auth/login', request.url);
      loginUrl.searchParams.set('returnTo', pathname);
      return NextResponse.redirect(loginUrl);
    }

    // Check if onboarding is completed by looking for a persona cookie
    // (Set by the onboarding completion flow)
    const onboardingComplete = request.cookies.get('pikar_onboarding_complete')?.value;

    if (onboardingComplete === 'true') {
      return response;
    }

    // Check via database if cookie not set
    const { data: profile } = await supabase
      .from('users_profile')
      .select('persona')
      .eq('user_id', user.id)
      .maybeSingle();

    if (profile?.persona) {
      // Set cookie for future requests to avoid DB roundtrips
      response.cookies.set('pikar_onboarding_complete', 'true', {
        path: '/',
        maxAge: 60 * 60 * 24 * 30, // 30 days
        httpOnly: false,
        sameSite: 'lax',
      });
      return response;
    }

    // Check legacy table
    const { data: agentConfig } = await supabase
      .from('user_executive_agents')
      .select('onboarding_completed')
      .eq('user_id', user.id)
      .maybeSingle();

    if (agentConfig?.onboarding_completed) {
      response.cookies.set('pikar_onboarding_complete', 'true', {
        path: '/',
        maxAge: 60 * 60 * 24 * 30,
        httpOnly: false,
        sameSite: 'lax',
      });
      return response;
    }

    // User hasn't completed onboarding — redirect
    return NextResponse.redirect(new URL('/onboarding', request.url));

  } catch (error) {
    console.error('Middleware error:', error);
    // On error, let the request through (don't block users)
    return response;
  }
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
