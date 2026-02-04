import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return request.cookies.get(name)?.value
        },
        set(name: string, value: string, options: CookieOptions) {
          request.cookies.set({
            name,
            value,
            ...options,
          })
          response = NextResponse.next({
            request: {
              headers: request.headers,
            },
          })
          response.cookies.set({
            name,
            value,
            ...options,
          })
        },
        remove(name: string, options: CookieOptions) {
          request.cookies.set({
            name,
            value: '',
            ...options,
          })
          response = NextResponse.next({
            request: {
              headers: request.headers,
            },
          })
          response.cookies.set({
            name,
            value: '',
            ...options,
          })
        },
      },
    }
  )

  const {
    data: { user },
  } = await supabase.auth.getUser()

  // Protected routes pattern
  // Adjust this pattern to match your actual protected routes
  const protectedPaths = ['/dashboard', '/solopreneur', '/startup', '/sme', '/enterprise', '/settings', '/onboarding']
  const isProtected = protectedPaths.some(path => request.nextUrl.pathname.startsWith(path))

  if (isProtected && !user) {
    return NextResponse.redirect(new URL('/auth/login', request.url))
  }

  // If user is signed in
  if (user) {
    // Check onboarding status and persona
    const { data: agentProfile } = await supabase
      .from('user_executive_agents')
      .select('onboarding_completed, persona')
      .eq('user_id', user.id)
      .single()

    const isOnboardingCompleted = agentProfile?.onboarding_completed === true
    const persona = agentProfile?.persona
    const isOnboardingPath = request.nextUrl.pathname.startsWith('/onboarding')
    const isApiRoute = request.nextUrl.pathname.startsWith('/api')

    // If not onboarded and trying to access protected pages (excluding onboarding pages and API)
    if (!isOnboardingCompleted && !isOnboardingPath && !isApiRoute && isProtected) {
      return NextResponse.redirect(new URL('/onboarding', request.url))
    }

    // Persona-based routing logic
    if (isOnboardingCompleted && persona) {
      const currentPath = request.nextUrl.pathname

      // 1. Redirect generic /dashboard to persona-specific route
      if (currentPath === '/dashboard') {
        return NextResponse.redirect(new URL(`/${persona}`, request.url))
      }

      // 2. Prevent access to other persona routes
      const personaRoutes = ['/solopreneur', '/startup', '/sme', '/enterprise']
      const matchedPersonaRoute = personaRoutes.find(route => currentPath.startsWith(route))

      if (matchedPersonaRoute) {
        const routePersona = matchedPersonaRoute.substring(1) // Remove leading slash
        if (routePersona !== persona && !currentPath.includes('/settings')) {
          return NextResponse.redirect(new URL(`/${persona}`, request.url))
        }
      }
    }

    // Auth pages logic
    const authPaths = ['/auth/login', '/auth/signup', '/sign-in', '/sign-up']
    const isAuthPage = authPaths.some(path => request.nextUrl.pathname.startsWith(path))

    if (isAuthPage) {
      if (!isOnboardingCompleted) {
        return NextResponse.redirect(new URL('/onboarding', request.url))
      } else {
        return NextResponse.redirect(new URL('/dashboard', request.url))
      }
    }
  }

  return response
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
}
