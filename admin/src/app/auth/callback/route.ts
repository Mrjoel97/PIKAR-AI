// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { type NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function loginRedirect(origin: string, message: string) {
  const url = new URL('/login', origin);
  url.searchParams.set('error', message);
  return NextResponse.redirect(url);
}

function exchangeErrorMessage(message?: string) {
  if (!message) {
    return 'Unable to complete Google sign-in. Please start again from login.';
  }

  if (message.toLowerCase().includes('code verifier')) {
    return (
      'Sign-in session expired or was opened in a different browser. ' +
      'Please start again from login.'
    );
  }

  return message;
}

export async function GET(request: NextRequest) {
  const origin = request.nextUrl.origin;
  const codeError = request.nextUrl.searchParams.get('error');
  const errorDescription = request.nextUrl.searchParams.get('error_description');
  const code = request.nextUrl.searchParams.get('code');

  if (codeError) {
    return loginRedirect(origin, errorDescription || codeError);
  }

  if (!code) {
    return loginRedirect(origin, 'No authorization code returned from Google.');
  }

  const supabase = await createClient();
  const {
    data: { session },
    error,
  } = await supabase.auth.exchangeCodeForSession(code);

  if (error || !session?.access_token) {
    return loginRedirect(origin, exchangeErrorMessage(error?.message));
  }

  let accessCheck: Response;
  try {
    accessCheck = await fetch(`${API_URL}/admin/check-access`, {
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        'X-Admin-Client': 'pikar-admin/1.0',
      },
      cache: 'no-store',
    });
  } catch {
    await supabase.auth.signOut();
    return loginRedirect(origin, 'Unable to verify admin access.');
  }

  if (!accessCheck.ok) {
    await supabase.auth.signOut();
    return loginRedirect(
      origin,
      'Access denied. This account does not have admin privileges.',
    );
  }

  return NextResponse.redirect(new URL('/', origin));
}
