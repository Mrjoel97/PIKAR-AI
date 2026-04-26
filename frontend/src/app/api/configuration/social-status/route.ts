// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { rateLimiters, getClientIp } from '@/lib/rate-limit';

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
    
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetch(
      `${API_BASE_URL}/configuration/social-status?user_id=${user.id}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
        },
      }
    );

    if (!response.ok) {
      const body = await response.text();
      return new NextResponse(body, {
        status: response.status,
        headers: {
          'Content-Type': response.headers.get('content-type') || 'application/json',
        },
      });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching social status:', error);
    return NextResponse.json(
      { error: 'Failed to fetch social status' },
      { status: 500 }
    );
  }
}


