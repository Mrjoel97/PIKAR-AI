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
