// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { rateLimiters, getClientIp } from '@/lib/rate-limit';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

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
        const { query, top_k = 5 } = body;

        if (!query) {
            return NextResponse.json(
                { error: 'query is required' },
                { status: 400 }
            );
        }

        // Get user and session from Supabase — session provides the bearer token
        const supabase = await createClient();
        const { data: { user }, error: authError } = await supabase.auth.getUser();

        if (authError || !user) {
            return NextResponse.json(
                { error: 'Unauthorized' },
                { status: 401 }
            );
        }

        // Extract bearer token from the incoming request to forward to the backend.
        // The backend is the authoritative trust boundary and validates token identity.
        const incomingAuth = request.headers.get('Authorization') ?? '';

        // Call backend to search the knowledge vault, forwarding bearer auth
        const response = await fetch(`${BACKEND_URL}/vault/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(incomingAuth ? { 'Authorization': incomingAuth } : {}),
            },
            body: JSON.stringify({
                query,
                top_k,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            return NextResponse.json(
                { error: errorData.detail || 'Search failed' },
                { status: response.status }
            );
        }

        const result = await response.json();
        return NextResponse.json(result);

    } catch (error: unknown) {
        console.error('Vault search error:', error);
        const errorMessage = error instanceof Error ? error.message : 'Internal server error';
        return NextResponse.json(
            { error: errorMessage },
            { status: 500 }
        );
    }
}
