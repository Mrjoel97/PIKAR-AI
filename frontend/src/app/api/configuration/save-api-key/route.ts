import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { rateLimiters, getClientIp } from '@/lib/rate-limit';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Map tool IDs to environment variable names
const TOOL_ENV_VARS: Record<string, string> = {
  tavily: 'TAVILY_API_KEY',
  firecrawl: 'FIRECRAWL_API_KEY',
  stitch: 'STITCH_API_KEY',
  resend: 'RESEND_API_KEY',
  hubspot: 'HUBSPOT_API_KEY',
  google_seo: 'GOOGLE_SEO_SERVICE_ACCOUNT_JSON',
  google_analytics: 'GOOGLE_ANALYTICS_PROPERTY_ID',
};

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

    const envVar = TOOL_ENV_VARS[tool_id];
    if (!envVar) {
      return NextResponse.json(
        { error: 'Unknown tool ID' },
        { status: 400 }
      );
    }

    // Save to user_configurations via backend
    const response = await fetch(`${API_BASE_URL}/configuration/save-user-config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session?.access_token}`,
      },
      body: JSON.stringify({
        key: envVar,
        value: api_key,
        user_id: user.id,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'Failed to save configuration');
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


