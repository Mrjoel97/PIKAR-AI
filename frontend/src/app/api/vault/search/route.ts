import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const { query, top_k = 5 } = body;

        if (!query) {
            return NextResponse.json(
                { error: 'query is required' },
                { status: 400 }
            );
        }

        // Get user from Supabase session
        const supabase = await createClient();
        const { data: { user }, error: authError } = await supabase.auth.getUser();

        if (authError || !user) {
            return NextResponse.json(
                { error: 'Unauthorized' },
                { status: 401 }
            );
        }

        // Call backend to search the knowledge vault
        const response = await fetch(`${BACKEND_URL}/vault/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query,
                top_k,
                user_id: user.id,
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
