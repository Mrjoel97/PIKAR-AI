// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/** Server-side proxy for /upload/smart. See ../route.ts for rationale. */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL =
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://localhost:8000';

export const maxDuration = 300;
const SMART_UPLOAD_UPSTREAM_TIMEOUT_MS = 35_000;

export async function POST(request: NextRequest): Promise<NextResponse> {
    let timeout: ReturnType<typeof setTimeout> | null = null;
    try {
        const incomingAuth = request.headers.get('authorization') ?? '';
        if (!incomingAuth) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const controller = new AbortController();
        timeout = setTimeout(() => {
            controller.abort('Smart upload proxy upstream timed out');
        }, SMART_UPLOAD_UPSTREAM_TIMEOUT_MS);

        const upstream = await fetch(`${BACKEND_URL}/upload/smart`, {
            method: 'POST',
            headers: {
                Authorization: incomingAuth,
                ...(request.headers.get('content-type')
                    ? { 'Content-Type': request.headers.get('content-type')! }
                    : {}),
            },
            body: request.body,
            signal: controller.signal,
            // @ts-expect-error — required for streaming a request body in Node fetch
            duplex: 'half',
        });
        clearTimeout(timeout);
        timeout = null;

        const text = await upstream.text();
        return new NextResponse(text, {
            status: upstream.status,
            headers: {
                'content-type': upstream.headers.get('content-type') ?? 'application/json',
            },
        });
    } catch (error: unknown) {
        console.error('[api/upload/smart] proxy error:', error);
        const isAbort =
            error instanceof DOMException && error.name === 'AbortError';
        const message = isAbort
            ? 'Smart upload proxy timed out while waiting for the backend.'
            : error instanceof Error
                ? error.message
                : 'Internal server error';
        return NextResponse.json({ error: message }, { status: isAbort ? 504 : 502 });
    } finally {
        if (timeout) {
            clearTimeout(timeout);
        }
    }
}
