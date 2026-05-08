// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Server-side proxy for the Vault tabs.
 *
 * Same root cause as /api/workspace/items: the browser-side Supabase
 * client doesn't reliably reconstruct an authenticated session from
 * the SSR cookies, so direct queries hit RLS and return empty. This
 * route uses the server client which reads cookies correctly.
 *
 * One endpoint per tab via ?tab=. Returns rows in the shape the
 * frontend already consumes (snake_case columns), so the only change
 * required in VaultInterface is the URL.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const TAB_HANDLERS: Record<string, (supabase: any, userId: string) => any> = {
  uploads: (supabase, userId) =>
    supabase
      .from('vault_documents')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .limit(200),

  images: (supabase, userId) =>
    supabase
      .from('media_assets')
      .select('*')
      .eq('user_id', userId)
      .like('file_type', 'image/%')
      .order('created_at', { ascending: false })
      .limit(100),

  videos: (supabase, userId) =>
    supabase
      .from('media_assets')
      .select('*')
      .eq('user_id', userId)
      .like('file_type', 'video/%')
      .order('created_at', { ascending: false })
      .limit(100),

  workspace: (supabase, userId) =>
    supabase
      .from('landing_pages')
      .select('id, title, created_at, config')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .limit(100),

  google: (supabase, userId) =>
    supabase
      .from('agent_google_docs')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .limit(100),

  braindump: (supabase, userId) =>
    supabase
      .from('vault_documents')
      .select('*')
      .eq('user_id', userId)
      .in('category', [
        'Brain Dump',
        'Brain Dump Transcript',
        'Validation Plan',
        'Brain Dump Analysis',
      ])
      .order('created_at', { ascending: false })
      .limit(100),
};

export async function GET(request: NextRequest) {
  const tab = (request.nextUrl.searchParams.get('tab') || 'uploads').toLowerCase();
  const handler = TAB_HANDLERS[tab];
  if (!handler) {
    return NextResponse.json({ error: 'unknown tab', items: [] }, { status: 400 });
  }

  try {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json({ items: [], user_id: null });
    }

    const { data, error } = await handler(supabase, user.id);
    if (error) {
      console.error(`[api/vault/list?tab=${tab}] failed:`, error.message);
      return NextResponse.json({ items: [], error: error.message }, { status: 500 });
    }

    return NextResponse.json({ items: data ?? [], user_id: user.id, tab });
  } catch (err) {
    console.error('[api/vault/list] threw:', err);
    return NextResponse.json({ items: [], error: 'internal' }, { status: 500 });
  }
}
