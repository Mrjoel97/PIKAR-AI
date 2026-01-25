import { describe, it, expect, vi, beforeEach } from 'vitest'
import { middleware } from './middleware'
import { NextRequest, NextResponse } from 'next/server'

// Mock dependencies
const mockGetSession = vi.fn()

vi.mock('@supabase/auth-helpers-nextjs', () => ({
  createMiddlewareClient: () => ({
    auth: {
      getSession: mockGetSession
    }
  })
}))

describe('Middleware', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('redirects unauthenticated users to sign-in when accessing protected routes', async () => {
    // Mock no session
    mockGetSession.mockResolvedValue({
      data: { session: null }
    })

    const req = new NextRequest(new URL('http://localhost:3000/dashboard'))
    const res = await middleware(req)

    // Check for redirect
    expect(res.status).toBe(307) // Temporary redirect
    expect(res.headers.get('Location')).toBe('http://localhost:3000/sign-in')
  })

  it('allows authenticated users to access protected routes', async () => {
    // Mock valid session
    mockGetSession.mockResolvedValue({
      data: { session: { user: { id: '123' } } }
    })

    const req = new NextRequest(new URL('http://localhost:3000/dashboard'))
    const res = await middleware(req)

    // Check for success (next)
    expect(res.status).toBe(200)
    expect(res.headers.get('Location')).toBeNull()
  })

  it('redirects authenticated users away from auth pages', async () => {
    // Mock valid session
    mockGetSession.mockResolvedValue({
      data: { session: { user: { id: '123' } } }
    })

    const req = new NextRequest(new URL('http://localhost:3000/sign-in'))
    const res = await middleware(req)

    // Check for redirect to dashboard
    expect(res.status).toBe(307)
    expect(res.headers.get('Location')).toBe('http://localhost:3000/dashboard')
  })

  it('allows unauthenticated users to access public pages', async () => {
    // Mock no session
    mockGetSession.mockResolvedValue({
      data: { session: null }
    })

    const req = new NextRequest(new URL('http://localhost:3000/'))
    const res = await middleware(req)

    // Check for success
    expect(res.status).toBe(200)
  })
})
