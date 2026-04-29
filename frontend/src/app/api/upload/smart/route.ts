// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/** Server-side proxy for /upload/smart. See ../route.ts for rationale. */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL =
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://localhost:8000';

export const maxDuration = 300;

export async function POST(request: NextRequest): Promise<NextResponse> {
    try {
        const incomingAuth = request.headers.get('authorization') ?? '';
        if (!incomingAuth) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        const upstream = await fetch(`${BACKEND_URL}/upload/smart`, {
            method: 'POST',
            headers: {
                Authorization: incomingAuth,
                ...(request.headers.get('content-type')
                    ? { 'Content-Type': request.headers.get('content-type')! }
                    : {}),
            },
            body: request.body,
            // @ts-expect-error — required for streaming a request body in Node fetch
            duplex: 'half',
        });

        const text = await upstream.text();
        return new NextResponse(text, {
            status: upstream.status,
            headers: {
                'content-type': upstream.headers.get('content-type') ?? 'application/json',
            },
        });
    } catch (error: unknown) {
        console.error('[api/upload/smart] proxy error:', error);
        const message = error instanceof Error ? error.message : 'Internal server error';
        return NextResponse.json({ error: message }, { status: 502 });
    }
}
