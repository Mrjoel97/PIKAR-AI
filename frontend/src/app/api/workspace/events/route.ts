// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Proxy for the per-user workspace SSE channel.
 *
 * The browser hook (`useWorkspaceEvents`) opens an `EventSource` against the
 * Next.js origin so cookie auth flows naturally. The FastAPI backend exposes
 * the actual stream at `${BACKEND}/workspace/events`. This route forwards the
 * request — auth cookie + `Authorization` header included — and pipes the
 * upstream `ReadableStream` straight back to the client without buffering.
 */

import { NextResponse } from 'next/server';

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

    const headers: Record<string, string> = {
        accept: 'text/event-stream',
    };
    const cookie = req.headers.get('cookie');
    if (cookie) headers.cookie = cookie;
    const auth = req.headers.get('authorization');
    if (auth) headers.authorization = auth;

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
