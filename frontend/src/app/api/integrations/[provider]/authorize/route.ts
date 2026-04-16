// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type RouteContext = {
  params: Promise<{
    provider: string;
  }>;
};

export async function GET(request: NextRequest, context: RouteContext) {
  try {
    const { provider } = await context.params;
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    const { data: { session } } = await supabase.auth.getSession();

    if (!user || !session?.access_token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const incomingUrl = new URL(request.url);
    const backendUrl = new URL(`${API_BASE_URL}/integrations/${encodeURIComponent(provider)}/authorize`);
    incomingUrl.searchParams.forEach((value, key) => {
      backendUrl.searchParams.set(key, value);
    });

    const response = await fetch(backendUrl.toString(), {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${session.access_token}`,
      },
      redirect: 'manual',
    });

    const location = response.headers.get('location');
    if (location && response.status >= 300 && response.status < 400) {
      return NextResponse.redirect(location, { status: response.status });
    }

    return new NextResponse(await response.text(), {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('content-type') || 'text/plain; charset=utf-8',
      },
    });
  } catch (error) {
    console.error('Integration authorize proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to initiate integration authorization' },
      { status: 500 },
    );
  }
}
