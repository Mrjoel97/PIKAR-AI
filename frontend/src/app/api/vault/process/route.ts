// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { rateLimiters, getClientIp } from '@/lib/rate-limit';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

function decodeJwtSub(token: string | null | undefined): string | null {
    if (!token) {
        return null;
    }

    const segments = token.split('.');
    if (segments.length < 2) {
        return null;
    }

    try {
        const payload = JSON.parse(Buffer.from(segments[1], 'base64url').toString('utf-8')) as {
            sub?: unknown;
        };
        return typeof payload.sub === 'string' ? payload.sub : null;
    } catch {
        return null;
    }
}

function extractBearerToken(headerValue: string | null): string | null {
    if (!headerValue) {
        return null;
    }

    const [scheme, token] = headerValue.trim().split(/\s+/, 2);
    if (scheme?.toLowerCase() !== 'bearer' || !token) {
        return null;
    }

    return token;
}

export async function POST(request: NextRequest) {
    const rl = rateLimiters.authenticated.check(getClientIp(request));
    if (!rl.success) {
        return NextResponse.json(
            { error: 'Too many requests' },
            { status: 429, headers: { 'Retry-After': String(rl.retryAfter) } }
        );
    }

    try {
        const body = await request.json();
        const { file_path } = body;

        if (!file_path) {
            return NextResponse.json(
                { error: 'file_path is required' },
                { status: 400 }
            );
        }

        // Resolve the authenticated user first so we only ever forward a token
        // that belongs to the current SSR-backed session cookie.
        const supabase = await createClient();
        const { data: { user }, error: authError } = await supabase.auth.getUser();

        if (authError || !user) {
            return NextResponse.json(
                { error: 'Unauthorized' },
                { status: 401 }
            );
        }

        const incomingToken = extractBearerToken(request.headers.get('Authorization'));
        const incomingTokenUserId = decodeJwtSub(incomingToken);

        const { data: { session } } = await supabase.auth.getSession();
        const sessionToken = session?.access_token ?? null;
        const sessionTokenUserId = decodeJwtSub(sessionToken);

        const bearerToken =
            incomingToken && incomingTokenUserId === user.id
                ? incomingToken
                : sessionToken && sessionTokenUserId === user.id
                    ? sessionToken
                    : null;

        if (!bearerToken) {
            return NextResponse.json(
                { error: 'Unauthorized' },
                { status: 401 }
            );
        }

        // Forward only the token that belongs to the authenticated cookie-backed
        // session. The backend remains the trust boundary for token validation.

        // Call backend to process the document for RAG, forwarding bearer auth
        const response = await fetch(`${BACKEND_URL}/vault/process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${bearerToken}`,
            },
            body: JSON.stringify({
                file_path,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const detail =
                (typeof errorData?.detail === 'string' && errorData.detail)
                || (typeof errorData?.message === 'string' && errorData.message)
                || (typeof errorData?.error === 'string' && errorData.error)
                || 'Processing failed';
            return NextResponse.json(
                {
                    success: false,
                    detail,
                    error: detail,
                    message: detail,
                },
                { status: response.status }
            );
        }

        const result = await response.json();
        return NextResponse.json(result);

    } catch (error: unknown) {
        console.error('Vault process error:', error);
        const errorMessage = error instanceof Error ? error.message : 'Internal server error';
        return NextResponse.json(
            { error: errorMessage },
            { status: 500 }
        );
    }
}
