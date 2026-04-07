/**
 * @vitest-environment node
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest, NextResponse } from 'next/server';

// ---------------------------------------------------------------------------
// Mock @supabase/ssr so we can control what getClaims() returns per test.
// ---------------------------------------------------------------------------
const getClaimsMock = vi.fn();
const createServerClientMock = vi.fn();

vi.mock('@supabase/ssr', () => ({
  createServerClient: (...args: unknown[]) => {
    createServerClientMock(...args);
    return {
      auth: {
        getClaims: getClaimsMock,
      },
    };
  },
}));

// Re-import the module under test AFTER the mock is registered.
import { updateSession } from '../src/lib/supabase/proxy';

function makeRequest(url: string, cookies: Array<{ name: string; value: string }> = []): NextRequest {
  const req = new NextRequest(new URL(url));
  for (const { name, value } of cookies) {
    req.cookies.set(name, value);
  }
  return req;
}

describe('updateSession (Supabase SSR proxy client)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'https://example.supabase.co';
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'anon-test-key';
  });

  it('returns a NextResponse with request cookies forwarded', async () => {
    getClaimsMock.mockResolvedValue({ data: { claims: null }, error: null });
    const req = makeRequest('http://localhost:3000/');

    const { response } = await updateSession(req);

    expect(response).toBeInstanceOf(NextResponse);
  });

  it('returns claims=null when there is no auth cookie', async () => {
    getClaimsMock.mockResolvedValue({ data: { claims: null }, error: null });
    const req = makeRequest('http://localhost:3000/dashboard');

    const { claims } = await updateSession(req);

    expect(claims).toBeNull();
  });

  it('returns parsed claims when getClaims() resolves with a valid JWT', async () => {
    getClaimsMock.mockResolvedValue({
      data: { claims: { sub: 'user-123', email: 'a@b.co' } },
      error: null,
    });
    const req = makeRequest('http://localhost:3000/dashboard', [
      { name: 'sb-example-auth-token', value: 'fake-jwt' },
    ]);

    const { claims } = await updateSession(req);

    expect(claims).not.toBeNull();
    expect(claims?.sub).toBe('user-123');
    expect(claims?.email).toBe('a@b.co');
  });

  it('forwards refreshed Set-Cookie headers when Supabase mutates cookies', async () => {
    // Simulate Supabase calling setAll() during the refresh cycle BEFORE
    // resolving getClaims(). The proxy client should mirror the new cookies
    // onto the outgoing response.
    let capturedSetAll: ((cookies: Array<{ name: string; value: string; options?: object }>) => void) | null = null;

    createServerClientMock.mockImplementation((...args: unknown[]) => {
      const opts = args[2] as { cookies: { setAll: typeof capturedSetAll } };
      capturedSetAll = opts.cookies.setAll;
    });

    getClaimsMock.mockImplementation(async () => {
      // Drive the refresh path: Supabase pushes a fresh cookie pair.
      capturedSetAll?.([
        { name: 'sb-refreshed-token', value: 'new-jwt-value', options: { path: '/' } },
      ]);
      return { data: { claims: { sub: 'user-456' } }, error: null };
    });

    const req = makeRequest('http://localhost:3000/dashboard', [
      { name: 'sb-refreshed-token', value: 'old-jwt-value' },
    ]);

    const { response, claims } = await updateSession(req);

    expect(claims?.sub).toBe('user-456');
    // The response must carry the refreshed cookie back to the browser.
    expect(response.cookies.get('sb-refreshed-token')?.value).toBe('new-jwt-value');
  });

  it('invokes createServerClient from @supabase/ssr with env vars', async () => {
    getClaimsMock.mockResolvedValue({ data: { claims: null }, error: null });
    const req = makeRequest('http://localhost:3000/');

    await updateSession(req);

    expect(createServerClientMock).toHaveBeenCalledTimes(1);
    expect(createServerClientMock).toHaveBeenCalledWith(
      'https://example.supabase.co',
      'anon-test-key',
      expect.objectContaining({
        cookies: expect.objectContaining({
          getAll: expect.any(Function),
          setAll: expect.any(Function),
        }),
      }),
    );
  });
});

// ---------------------------------------------------------------------------
// Root proxy matcher + redirect behaviour.
//
// The proxy module imports updateSession via the `@/lib/supabase/proxy` alias
// which resolves to the SAME source file the Task 1 suite imports by relative
// path. We therefore cannot blanket-mock that module — doing so would replace
// the real `updateSession` for the Task 1 tests above.
//
// Instead we install a partial mock that preserves every real export by
// default and exposes a `__setUpdateSessionImpl` test hook. The Task 1 suite
// uses the real implementation; the Task 2 suite swaps in a controlled
// implementation per test.
// ---------------------------------------------------------------------------

const updateSessionMock = vi.fn();

vi.mock('@/lib/supabase/proxy', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/lib/supabase/proxy')>();
  return {
    ...actual,
    // Default: fall through to the real implementation so Task 1 tests keep
    // exercising the actual Supabase SSR client. Task 2 tests override the
    // mock's implementation per test case.
    updateSession: (req: NextRequest) => {
      if (updateSessionMock.getMockImplementation()) {
        return updateSessionMock(req);
      }
      return actual.updateSession(req);
    },
  };
});

// Re-import the proxy module under test AFTER the mock is registered.
import { proxy } from '../proxy';

function defaultPassthrough(req: NextRequest) {
  return Promise.resolve({
    response: NextResponse.next({ request: req }),
    claims: null,
  });
}

function defaultAuthenticated(req: NextRequest) {
  return Promise.resolve({
    response: NextResponse.next({ request: req }),
    claims: { sub: 'user-001', email: 'a@b.co' },
  });
}

describe('root proxy() matcher and redirect behaviour', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('passes through the landing page (/) without redirect', async () => {
    updateSessionMock.mockImplementation(defaultPassthrough);
    const req = new NextRequest(new URL('http://localhost:3000/'));

    const res = await proxy(req);

    // 200 next() (no Location header)
    expect(res.headers.get('location')).toBeNull();
  });

  it('passes through /auth/login without redirect', async () => {
    updateSessionMock.mockImplementation(defaultPassthrough);
    const req = new NextRequest(new URL('http://localhost:3000/auth/login'));

    const res = await proxy(req);

    expect(res.headers.get('location')).toBeNull();
  });

  it('redirects unauthenticated /dashboard to /auth/login?next=%2Fdashboard', async () => {
    updateSessionMock.mockImplementation(defaultPassthrough);
    const req = new NextRequest(new URL('http://localhost:3000/dashboard'));

    const res = await proxy(req);

    const location = res.headers.get('location');
    expect(location).not.toBeNull();
    const loc = new URL(location!);
    expect(loc.pathname).toBe('/auth/login');
    expect(loc.searchParams.get('next')).toBe('/dashboard');
  });

  it('redirects unauthenticated /settings/profile preserving the next path', async () => {
    updateSessionMock.mockImplementation(defaultPassthrough);
    const req = new NextRequest(new URL('http://localhost:3000/settings/profile'));

    const res = await proxy(req);

    const location = res.headers.get('location');
    expect(location).not.toBeNull();
    const loc = new URL(location!);
    expect(loc.pathname).toBe('/auth/login');
    expect(loc.searchParams.get('next')).toBe('/settings/profile');
  });

  it('redirects unauthenticated /admin to /auth/login?next=%2Fadmin', async () => {
    updateSessionMock.mockImplementation(defaultPassthrough);
    const req = new NextRequest(new URL('http://localhost:3000/admin'));

    const res = await proxy(req);

    const loc = new URL(res.headers.get('location')!);
    expect(loc.pathname).toBe('/auth/login');
    expect(loc.searchParams.get('next')).toBe('/admin');
  });

  it('redirects unauthenticated persona routes (/solopreneur/dashboard)', async () => {
    updateSessionMock.mockImplementation(defaultPassthrough);
    const req = new NextRequest(new URL('http://localhost:3000/solopreneur/dashboard'));

    const res = await proxy(req);

    const loc = new URL(res.headers.get('location')!);
    expect(loc.pathname).toBe('/auth/login');
    expect(loc.searchParams.get('next')).toBe('/solopreneur/dashboard');
  });

  it('lets authenticated requests through to /dashboard without redirect', async () => {
    updateSessionMock.mockImplementation(defaultAuthenticated);
    const req = new NextRequest(new URL('http://localhost:3000/dashboard'));

    const res = await proxy(req);

    expect(res.headers.get('location')).toBeNull();
  });

  it('does NOT redirect /api/* even when claims are null (matcher exclusion)', async () => {
    updateSessionMock.mockImplementation(defaultPassthrough);
    const req = new NextRequest(new URL('http://localhost:3000/api/health'));

    const res = await proxy(req);

    // The proxy still runs (matcher exclusion is applied by Next.js, not the
    // function body), but it must NOT classify /api/* as protected and so
    // must NOT issue a redirect.
    expect(res.headers.get('location')).toBeNull();
  });

  it('does NOT redirect _next static asset requests', async () => {
    updateSessionMock.mockImplementation(defaultPassthrough);
    const req = new NextRequest(new URL('http://localhost:3000/_next/static/chunk.js'));

    const res = await proxy(req);

    expect(res.headers.get('location')).toBeNull();
  });
});
