// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

type SessionPayload = {
  access_token?: string;
  refresh_token?: string;
};

export async function POST(request: Request) {
  let payload: SessionPayload;

  try {
    payload = (await request.json()) as SessionPayload;
  } catch {
    return NextResponse.json({ error: 'Invalid session payload.' }, { status: 400 });
  }

  if (!payload.access_token || !payload.refresh_token) {
    return NextResponse.json(
      { error: 'Both access_token and refresh_token are required.' },
      { status: 400 },
    );
  }

  try {
    const supabase = await createClient();
    const { error } = await supabase.auth.setSession({
      access_token: payload.access_token,
      refresh_token: payload.refresh_token,
    });

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 });
    }

    return NextResponse.json({ ok: true });
  } catch {
    return NextResponse.json(
      { error: 'Failed to persist authenticated session.' },
      { status: 500 },
    );
  }
}
