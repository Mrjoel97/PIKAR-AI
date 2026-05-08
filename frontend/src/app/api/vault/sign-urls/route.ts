// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Server-side signing for Vault storage previews.
 *
 * The browser-side Supabase client doesn't reliably materialise a JWT from
 * the SSR cookies, so `supabase.storage.from(bucket).createSignedUrls` from
 * the browser silently returned no URLs and image cards collapsed to the
 * file-icon fallback. Same root cause as /api/vault/list (bf317b3e).
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const SIGNED_URL_TTL_SECONDS = 3600;
const MAX_PATHS_PER_REQUEST = 200;
const ALLOWED_BUCKETS = new Set(['knowledge-vault', 'media-assets']);

interface SignUrlsBody {
  bucket?: unknown;
  paths?: unknown;
}

/**
 * Returns true when a storage path belongs to the given user.
 *
 * Handles both bucket conventions used in this repo:
 *   knowledge-vault  →  <userId>/<uuid>.<ext>      (user-id is first segment)
 *   media-assets     →  media/<userId>/<assetId>   (user-id is second segment)
 */
function pathBelongsToUser(path: string, userId: string): boolean {
  // Path conventions in use:
  //   knowledge-vault: <userId>/<uuid>.<ext>
  //   media-assets:    media/<userId>/<assetId>.<ext>
  return (
    path === userId ||
    path.startsWith(`${userId}/`) ||
    path.startsWith(`media/${userId}/`)
  );
}

export async function POST(request: NextRequest) {
  let body: SignUrlsBody;
  try {
    body = (await request.json()) as SignUrlsBody;
  } catch {
    return NextResponse.json({ error: 'invalid json' }, { status: 400 });
  }

  if (typeof body.bucket !== 'string' || !body.bucket) {
    return NextResponse.json({ error: 'bucket is required' }, { status: 400 });
  }
  if (!ALLOWED_BUCKETS.has(body.bucket)) {
    return NextResponse.json({ error: 'unknown bucket' }, { status: 400 });
  }
  if (!Array.isArray(body.paths) || body.paths.length === 0) {
    return NextResponse.json({ error: 'paths must be a non-empty array' }, { status: 400 });
  }
  if (body.paths.length > MAX_PATHS_PER_REQUEST) {
    return NextResponse.json(
      { error: `paths exceeds max ${MAX_PATHS_PER_REQUEST}` },
      { status: 400 },
    );
  }
  if (!body.paths.every((p) => typeof p === 'string' && p.length > 0)) {
    return NextResponse.json({ error: 'paths must be non-empty strings' }, { status: 400 });
  }

  const bucket = body.bucket;
  const paths = body.paths as string[];

  try {
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      return NextResponse.json({ error: 'unauthenticated' }, { status: 401 });
    }

    if (!paths.every((p) => pathBelongsToUser(p, user.id))) {
      return NextResponse.json({ error: 'forbidden' }, { status: 403 });
    }

    const { data, error } = await supabase.storage
      .from(bucket)
      .createSignedUrls(paths, SIGNED_URL_TTL_SECONDS);

    if (error) {
      console.error('[api/vault/sign-urls] failed:', error.message);
      return NextResponse.json({ items: [], error: error.message }, { status: 500 });
    }

    const items = (data ?? []).map((row) => ({
      path: row.path,
      signedUrl: row.signedUrl,
    }));

    return NextResponse.json({ items });
  } catch (err) {
    console.error('[api/vault/sign-urls] threw:', err);
    return NextResponse.json({ error: 'internal' }, { status: 500 });
  }
}
