// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { createClient } from '@/lib/supabase/server';
import { NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get('code');

  const codeError = searchParams.get('error');
  const errorDescription = searchParams.get('error_description');

  if (codeError) {
    return NextResponse.redirect(
      `${origin}/login?error=${encodeURIComponent(errorDescription || codeError)}`,
    );
  }

  if (!code) {
    return NextResponse.redirect(`${origin}/login?error=No+authorization+code`);
  }

  const supabase = await createClient();
  const { data, error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    return NextResponse.redirect(
      `${origin}/login?error=${encodeURIComponent(error.message)}`,
    );
  }

  // Verify admin access before allowing entry
  try {
    const res = await fetch(`${API_URL}/admin/check-access`, {
      headers: {
        Authorization: `Bearer ${data.session.access_token}`,
        'X-Admin-Client': 'pikar-admin/1.0',
      },
    });

    if (!res.ok) {
      await supabase.auth.signOut();
      return NextResponse.redirect(
        `${origin}/login?error=Access+denied.+This+account+does+not+have+admin+privileges.`,
      );
    }
  } catch {
    await supabase.auth.signOut();
    return NextResponse.redirect(
      `${origin}/login?error=Unable+to+verify+admin+access.+Please+try+again.`,
    );
  }

  return NextResponse.redirect(`${origin}/`);
}
