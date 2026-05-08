// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Server-side proxy for `workspace_items` queries.
 *
 * Why this exists: the Vercel SSR auth flow stores Supabase session in
 * httpOnly cookies. The Next.js server client picks those up correctly,
 * but the BROWSER-side `@supabase/ssr` client doesn't always translate
 * them into a JWT — RLS then rejects every direct query as anon, and
 * the workspace canvas appears empty.
 *
 * Routing the query through this endpoint guarantees we use the
 * cookie-backed server client, so `auth.uid()` is the signed-in user
 * and RLS lets the rows through. Strictly read-only.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return NextResponse.json({ items: [] }, { status: 200 });
    }

    const sessionId = request.nextUrl.searchParams.get('session_id');
    const limitRaw = request.nextUrl.searchParams.get('limit');
    const limit = Math.min(
      200,
      Math.max(1, Number.isFinite(Number(limitRaw)) ? Number(limitRaw) || 100 : 100),
    );

    let query = supabase
      .from('workspace_items')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })
      .limit(limit);

    if (sessionId) {
      query = query.eq('session_id', sessionId);
    }

    const { data, error } = await query;

    if (error) {
      console.error('[api/workspace/items] query failed:', error.message);
      return NextResponse.json(
        { items: [], error: error.message },
        { status: 500 },
      );
    }

    return NextResponse.json({
      items: data ?? [],
      user_id: user.id,
    });
  } catch (err) {
    console.error('[api/workspace/items] threw:', err);
    return NextResponse.json({ items: [], error: 'internal' }, { status: 500 });
  }
}
