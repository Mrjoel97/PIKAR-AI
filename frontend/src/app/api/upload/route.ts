// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Server-side proxy for /upload — forwards multipart upload from browser
 * to the Cloud Run backend. The browser-direct path (NEXT_PUBLIC_API_URL)
 * was getting cancelled by some upstream layer (CDN, proxy, browser
 * navigation cleanup) with the opaque "signal is aborted without reason"
 * message. Routing through the Next.js server eliminates that path.
 */

import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL =
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://localhost:8000';

// Allow long-running uploads (DOCX/PDF text extraction can take a while
// on the backend). The default Vercel function timeout is 300s on Hobby
// and 900s on Pro; this aligns with our backend timeouts.
export const maxDuration = 300;

export async function POST(request: NextRequest): Promise<NextResponse> {
    try {
        // Forward the auth header (caller's bearer token) to the backend.
        // The backend is the trust boundary and validates the token itself.
        const incomingAuth = request.headers.get('authorization') ?? '';
        if (!incomingAuth) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        // Stream the body straight through. We do NOT read it into memory
        // here because that would (a) double the memory footprint and (b)
        // require us to reconstruct the multipart boundary correctly.
        const upstream = await fetch(`${BACKEND_URL}/upload`, {
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
        console.error('[api/upload] proxy error:', error);
        const message = error instanceof Error ? error.message : 'Internal server error';
        return NextResponse.json({ error: message }, { status: 502 });
    }
}
