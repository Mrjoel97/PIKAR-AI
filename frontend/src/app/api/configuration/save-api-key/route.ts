// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { rateLimiters, getClientIp } from '@/lib/rate-limit';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  const rl = rateLimiters.sensitive.check(getClientIp(request));
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

    const body = await request.json();
    const { tool_id, api_key } = body;

    if (!tool_id || !api_key) {
      return NextResponse.json(
        { error: 'Missing tool_id or api_key' },
        { status: 400 }
      );
    }

    // Backend owns the tool_id allowlist and env-var mapping.
    const response = await fetch(`${API_BASE_URL}/configuration/save-api-key`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session?.access_token}`,
      },
      body: JSON.stringify({
        tool_id,
        api_key,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message =
        errorData.message ||
        errorData.detail ||
        errorData.error ||
        'Failed to save API key';
      return NextResponse.json(
        { error: message },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json({
      success: data.success,
      message: data.message,
    });
  } catch (error) {
    console.error('Error saving API key:', error);
    return NextResponse.json(
      { error: 'Failed to save API key' },
      { status: 500 }
    );
  }
}
