// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Proxy for the per-user workspace SSE channel.
 *
 * The browser hook (`useWorkspaceEvents`) opens an `EventSource` against the
 * Next.js origin. Native `EventSource` cannot attach an `Authorization`
 * header, and the FastAPI backend at `${BACKEND}/workspace/events` requires
 * `Authorization: Bearer <jwt>`. So we use the SSR Supabase client to read
 * the access token from the auth cookie and inject it as a Bearer header
 * before piping the upstream `ReadableStream` straight back to the client.
 */

import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function resolveBackendUrl(): string {
    // Evaluated per request so test harnesses (and prod env mutations on
    // restart) pick up the latest value without re-importing the module.
    return (
        process.env.WORKSPACE_EVENTS_BACKEND_URL
        || process.env.NEXT_PUBLIC_API_URL
        || 'http://127.0.0.1:8000'
    );
}

export async function GET(req: Request): Promise<Response> {
    const upstreamUrl = `${resolveBackendUrl().replace(/\/$/, '')}/workspace/events`;

    // Pull the Supabase access token from the auth cookie. EventSource can
    // only send cookies, so the backend's Bearer-only auth would otherwise
    // reject the request with 403. (See sessions/list/route.ts for the
    // same SSR cookie → Bearer pattern.)
    let accessToken: string | null = null;
    try {
        const supabase = await createClient();
        const { data: sessionData } = await supabase.auth.getSession();
        accessToken = sessionData.session?.access_token ?? null;
    } catch (err) {
        // Cookie store or Supabase client failure — fall through to upstream
        // attempt below; the existing Authorization header (if any) still
        // gets a chance to authenticate.
        console.error('[api/workspace/events] supabase session read failed:', err);
    }

    const headers: Record<string, string> = {
        accept: 'text/event-stream',
    };
    const cookie = req.headers.get('cookie');
    if (cookie) headers.cookie = cookie;
    const auth = req.headers.get('authorization');
    if (auth) {
        headers.authorization = auth;
    } else if (accessToken) {
        headers.authorization = `Bearer ${accessToken}`;
    }

    try {
        const upstream = await fetch(upstreamUrl, {
            method: 'GET',
            headers,
            // SSE streams must not be cached or buffered.
            cache: 'no-store',
        });

        if (!upstream.ok || !upstream.body) {
            return NextResponse.json(
                { error: `upstream returned ${upstream.status}` },
                { status: upstream.status || 502 },
            );
        }

        return new Response(upstream.body, {
            status: 200,
            headers: {
                'content-type': 'text/event-stream',
                'cache-control': 'no-cache, no-transform',
                connection: 'keep-alive',
                'x-accel-buffering': 'no',
            },
        });
    } catch (err) {
        return NextResponse.json(
            { error: 'workspace events upstream unavailable', detail: String(err) },
            { status: 502 },
        );
    }
}
