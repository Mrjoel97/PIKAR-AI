// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function GET(request: Request) {
  const { origin, searchParams } = new URL(request.url);
  const next = searchParams.get('next') || '/login';

  try {
    const supabase = await createClient();
    await supabase.auth.signOut();
  } catch {
    // Even if cookie clearing fails, still continue to the requested location.
  }

  return NextResponse.redirect(new URL(next, origin));
}
