import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const ALLOWED_PLATFORMS = ['twitter', 'linkedin', 'facebook', 'instagram', 'google', 'tiktok', 'youtube'];

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');

    // Handle OAuth errors
    if (error) {
      return NextResponse.redirect(
        new URL(`/dashboard/configuration?error=${encodeURIComponent(error)}`, request.url)
      );
    }

    if (!code || !state) {
      return NextResponse.redirect(
        new URL('/dashboard/configuration?error=missing_params', request.url)
      );
    }

    // Extract platform from state (format: userId:platform:random)
    const stateParts = state.split(':');
    const platform = stateParts[1] || 'unknown';

    if (!ALLOWED_PLATFORMS.includes(platform)) {
      return NextResponse.json({ error: 'Invalid platform' }, { status: 400 });
    }

    // Forward to backend for token exchange
    const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';
    const redirectUri = `${appUrl}/api/configuration/oauth-callback`;

    const response = await fetch(
      `${API_BASE_URL}/configuration/oauth/callback/${platform}?code=${code}&state=${state}&redirect_uri=${encodeURIComponent(redirectUri)}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    const data = await response.json();

    if (data.success) {
      return NextResponse.redirect(
        new URL(`/dashboard/configuration?success=${encodeURIComponent(platform)}`, request.url)
      );
    } else {
      return NextResponse.redirect(
        new URL(`/dashboard/configuration?error=${encodeURIComponent(data.error || 'connection_failed')}`, request.url)
      );
    }
  } catch (error) {
    console.error('OAuth callback error:', error);
    return NextResponse.redirect(
      new URL('/dashboard/configuration?error=callback_error', request.url)
    );
  }
}
