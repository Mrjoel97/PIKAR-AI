/**
 * @vitest-environment node
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Hoisted so the mocked module is in place before `./route` is evaluated.
const getSessionMock = vi.hoisted(() => vi.fn());
const createClientMock = vi.hoisted(() =>
    vi.fn(async () => ({
        auth: { getSession: getSessionMock },
    })),
);

vi.mock('@/lib/supabase/server', () => ({
    createClient: createClientMock,
}));

import { GET } from './route';

describe('GET /api/workspace/events', () => {
    beforeEach(() => {
        process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com';
        delete process.env.WORKSPACE_EVENTS_BACKEND_URL;
        vi.restoreAllMocks();
        getSessionMock.mockResolvedValue({ data: { session: null }, error: null });
    });

    afterEach(() => {
        delete process.env.NEXT_PUBLIC_API_URL;
        delete process.env.WORKSPACE_EVENTS_BACKEND_URL;
    });

    it('proxies to the backend SSE endpoint with text/event-stream content-type', async () => {
        const upstream = new Response(new ReadableStream(), {
            status: 200,
            headers: { 'content-type': 'text/event-stream' },
        });
        const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(upstream);

        const req = new Request('http://localhost/api/workspace/events', {
            headers: { cookie: 'sb-session=abc' },
        });
        const res = await GET(req as unknown as Request);
        expect(res.headers.get('content-type')).toBe('text/event-stream');
        expect(fetchSpy).toHaveBeenCalledWith(
            'https://api.example.com/workspace/events',
            expect.objectContaining({
                method: 'GET',
                headers: expect.any(Object),
            }),
        );
    });

    it('forwards both cookie and authorization headers to the backend', async () => {
        const upstream = new Response(new ReadableStream(), {
            status: 200,
            headers: { 'content-type': 'text/event-stream' },
        });
        const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(upstream);

        const req = new Request('http://localhost/api/workspace/events', {
            headers: {
                cookie: 'sb-session=abc',
                authorization: 'Bearer token-123',
            },
        });
        await GET(req as unknown as Request);

        const init = fetchSpy.mock.calls[0][1] as RequestInit;
        const headers = init.headers as Record<string, string>;
        expect(headers.cookie).toBe('sb-session=abc');
        expect(headers.authorization).toBe('Bearer token-123');
        expect(headers.accept).toBe('text/event-stream');
    });

    it('injects the Supabase access token as Bearer when no Authorization header is supplied', async () => {
        getSessionMock.mockResolvedValue({
            data: { session: { access_token: 'cookie-derived-jwt' } },
            error: null,
        });
        const upstream = new Response(new ReadableStream(), {
            status: 200,
            headers: { 'content-type': 'text/event-stream' },
        });
        const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(upstream);

        const req = new Request('http://localhost/api/workspace/events', {
            headers: { cookie: 'sb-access-token=abc' },
        });
        await GET(req as unknown as Request);

        const init = fetchSpy.mock.calls[0][1] as RequestInit;
        const headers = init.headers as Record<string, string>;
        expect(headers.authorization).toBe('Bearer cookie-derived-jwt');
    });

    it('prefers an explicit Authorization header over the cookie-derived token', async () => {
        getSessionMock.mockResolvedValue({
            data: { session: { access_token: 'cookie-derived-jwt' } },
            error: null,
        });
        const upstream = new Response(new ReadableStream(), {
            status: 200,
            headers: { 'content-type': 'text/event-stream' },
        });
        const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(upstream);

        const req = new Request('http://localhost/api/workspace/events', {
            headers: { authorization: 'Bearer explicit-jwt' },
        });
        await GET(req as unknown as Request);

        const init = fetchSpy.mock.calls[0][1] as RequestInit;
        const headers = init.headers as Record<string, string>;
        expect(headers.authorization).toBe('Bearer explicit-jwt');
    });

    it('uses WORKSPACE_EVENTS_BACKEND_URL when set, overriding NEXT_PUBLIC_API_URL', async () => {
        process.env.WORKSPACE_EVENTS_BACKEND_URL = 'http://internal.svc:9000';
        const upstream = new Response(new ReadableStream(), {
            status: 200,
            headers: { 'content-type': 'text/event-stream' },
        });
        const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValue(upstream);

        await GET(
            new Request('http://localhost/api/workspace/events') as unknown as Request,
        );

        expect(fetchSpy).toHaveBeenCalledWith(
            'http://internal.svc:9000/workspace/events',
            expect.anything(),
        );
    });

    it('returns 502 if the upstream is unreachable', async () => {
        vi.spyOn(global, 'fetch').mockRejectedValue(new Error('connection refused'));
        const req = new Request('http://localhost/api/workspace/events');
        const res = await GET(req as unknown as Request);
        expect(res.status).toBe(502);
    });

    it('mirrors upstream non-2xx status to the client', async () => {
        vi.spyOn(global, 'fetch').mockResolvedValue(
            new Response('upstream down', { status: 503 }),
        );
        const req = new Request('http://localhost/api/workspace/events');
        const res = await GET(req as unknown as Request);
        expect(res.status).toBe(503);
    });
});
