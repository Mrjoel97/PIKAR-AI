// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { getClientIp, rateLimiters } from '@/lib/rate-limit';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.BACKEND_URL ||
  'http://localhost:8000';

export async function GET(request: NextRequest) {
  const rl = rateLimiters.authenticated.check(getClientIp(request));
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Too many requests' },
      { status: 429, headers: { 'Retry-After': String(rl.retryAfter) } }
    );
  }

  try {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    const { data: { session } } = await supabase.auth.getSession();

    if (!user || !session?.access_token) {
      return NextResponse.json(null);
    }

    const response = await fetch(`${API_BASE_URL}/briefing`, {
      headers: {
        Authorization: `Bearer ${session.access_token}`,
      },
      cache: 'no-store',
    });

    if (response.status === 401 || response.status === 403 || response.status === 404) {
      return NextResponse.json(null);
    }

    if (!response.ok) {
      console.warn('[api/briefing] Backend returned unexpected status', response.status);
      return NextResponse.json(null);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[api/briefing] Failed to load briefing:', error);
    return NextResponse.json(null);
  }
}
