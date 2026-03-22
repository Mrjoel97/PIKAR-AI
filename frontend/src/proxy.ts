import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function proxy(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  })

  const pathname = request.nextUrl.pathname

  // Fast-path: Skip proxy entirely for public/static routes
  // This avoids ANY Supabase calls for the landing page and auth pages
  const publicPaths = ['/', '/auth', '/api/health', '/api/waitlist', '/privacy', '/terms']
  const isPublicPath = publicPaths.some(path =>
    pathname === path || pathname.startsWith(path + '/')
  )
  if (isPublicPath) {
    return response
  }

  // Protected routes pattern
  const protectedPaths = ['/dashboard', '/solopreneur', '/startup', '/sme', '/enterprise', '/settings', '/onboarding']
  const isProtected = protectedPaths.some(path => pathname.startsWith(path))

  // Skip proxy for non-protected routes (e.g. api, fonts, images)
  if (!isProtected) {
    return response
  }

  // --- Only create Supabase client for protected routes ---
  let user = null
  let supabase = null

  try {
    supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return request.cookies.getAll()
          },
          setAll(cookiesToSet) {
            cookiesToSet.forEach(({ name, value }) =>
              request.cookies.set(name, value)
            )
            response = NextResponse.next({
              request: { headers: request.headers },
            })
            cookiesToSet.forEach(({ name, value, options }) =>
              response.cookies.set({ name, value, ...options })
            )
          },
        },
      }
    )

    const { data, error } = await supabase.auth.getUser()
    if (error) {
      console.error('Proxy auth error:', error.message)
    }
    user = data?.user ?? null
  } catch (error) {
    console.error('Proxy Supabase connection error:', error)
    return NextResponse.redirect(new URL('/auth/login', request.url))
  }

  // Redirect to login if accessing protected route without auth
  if (!user) {
    return NextResponse.redirect(new URL('/auth/login', request.url))
  }

  // --- Onboarding/persona check: only when needed ---
  // Skip the expensive DB query for onboarding page itself and settings
  const isOnboardingPath = pathname.startsWith('/onboarding')
  const isSettingsPath = pathname.startsWith('/settings')

  // For /dashboard redirect and persona enforcement, we need the profile.
  // For onboarding and settings pages, skip the DB call entirely.
  if (!isOnboardingPath && !isSettingsPath) {
    try {
      // Try to use cached persona/onboarding from cookie to skip DB query (~100-200ms saved)
      const cachedPersona = request.cookies.get('x-pikar-persona')?.value
      const cachedOnboarded = request.cookies.get('x-pikar-onboarded')?.value

      let isOnboardingCompleted: boolean
      let persona: string | null | undefined

      if (cachedOnboarded !== undefined && cachedPersona) {
        // Fast path: use cached values, no DB query needed
        isOnboardingCompleted = cachedOnboarded === 'true'
        persona = cachedPersona === 'none' ? null : cachedPersona
      } else {
        // Slow path: query DB and cache the result for subsequent requests
        const { data: agentProfile } = await supabase!
          .from('user_executive_agents')
          .select('onboarding_completed, persona')
          .eq('user_id', user.id)
          .maybeSingle()

        isOnboardingCompleted = agentProfile?.onboarding_completed === true
        persona = agentProfile?.persona

        // Cache in cookies for 5 minutes to speed up subsequent navigations
        const isProduction = process.env.NODE_ENV === 'production'
        const cookieOptions = { path: '/', maxAge: 300, httpOnly: true, sameSite: 'lax' as const, secure: isProduction }
        response.cookies.set('x-pikar-onboarded', String(isOnboardingCompleted), cookieOptions)
        response.cookies.set('x-pikar-persona', persona || 'none', cookieOptions)
      }

      // If not onboarded, redirect to onboarding
      if (!isOnboardingCompleted) {
        const redirectResponse = NextResponse.redirect(new URL('/onboarding', request.url))
        // Carry forward cache cookies on redirect
        redirectResponse.cookies.set('x-pikar-onboarded', 'false', { path: '/', maxAge: 300, httpOnly: true, sameSite: 'lax' })
        redirectResponse.cookies.set('x-pikar-persona', persona || 'none', { path: '/', maxAge: 300, httpOnly: true, sameSite: 'lax' })
        return redirectResponse
      }

      // Persona-based routing logic
      if (persona) {
        // Redirect generic /dashboard to persona-specific route
        if (pathname === '/dashboard') {
          return NextResponse.redirect(new URL(`/${persona}`, request.url))
        }

        // Prevent access to wrong persona routes
        const personaRoutes = ['/solopreneur', '/startup', '/sme', '/enterprise']
        const matchedPersonaRoute = personaRoutes.find(route => pathname.startsWith(route))

        if (matchedPersonaRoute) {
          const routePersona = matchedPersonaRoute.substring(1)
          if (routePersona !== persona) {
            return NextResponse.redirect(new URL(`/${persona}`, request.url))
          }
        }
      }
    } catch (error) {
      console.error('Proxy profile check error:', error)
      // Allow the request to continue if profile check fails
    }
  }

  // Clear persona cache when visiting onboarding (will be re-cached after completion)
  if (isOnboardingPath) {
    response.cookies.delete('x-pikar-persona')
    response.cookies.delete('x-pikar-onboarded')
  }

  return response
}
