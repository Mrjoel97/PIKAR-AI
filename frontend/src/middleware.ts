import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export async function middleware(req: NextRequest) {
  const res = NextResponse.next()
  const supabase = createMiddlewareClient({ req, res })

  const {
    data: { session },
  } = await supabase.auth.getSession()

  // Protected routes pattern
  // Adjust this pattern to match your actual protected routes
  const protectedPaths = ['/dashboard', '/solopreneur', '/startup', '/sme', '/enterprise', '/settings']
  const isProtected = protectedPaths.some(path => req.nextUrl.pathname.startsWith(path))

  if (isProtected && !session) {
    return NextResponse.redirect(new URL('/sign-in', req.url))
  }

  // If user is signed in and tries to access auth pages, redirect to dashboard?
  // Optional but good UX
  const authPaths = ['/sign-in', '/sign-up']
  const isAuthPage = authPaths.some(path => req.nextUrl.pathname.startsWith(path))

  if (isAuthPage && session) {
    return NextResponse.redirect(new URL('/dashboard', req.url))
  }

  return res
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
