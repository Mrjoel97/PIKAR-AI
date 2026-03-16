import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type WaitlistRequestBody = {
  fullName?: unknown;
  email?: unknown;
  companyOrRole?: unknown;
  biggestBottleneck?: unknown;
  source?: unknown;
  pagePath?: unknown;
  referrer?: unknown;
  utmSource?: unknown;
  utmMedium?: unknown;
  utmCampaign?: unknown;
  utmContent?: unknown;
  utmTerm?: unknown;
  website?: unknown;
};

const sanitizeText = (value: unknown, maxLength: number): string | null => {
  if (typeof value !== 'string') {
    return null;
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  return trimmed.slice(0, maxLength);
};

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as WaitlistRequestBody;

    const honeypot = sanitizeText(body.website, 255);
    if (honeypot) {
      return NextResponse.json({ success: true });
    }

    const fullName = sanitizeText(body.fullName, 120);
    const email = sanitizeText(body.email, 320)?.toLowerCase() ?? null;
    const companyOrRole = sanitizeText(body.companyOrRole, 160);
    const biggestBottleneck = sanitizeText(body.biggestBottleneck, 1000);
    const source = sanitizeText(body.source, 80) ?? 'landing_page';
    const pagePath = sanitizeText(body.pagePath, 255) ?? request.nextUrl.pathname;
    const referrer = sanitizeText(body.referrer, 1024) ?? request.headers.get('referer');
    const utmSource = sanitizeText(body.utmSource, 120);
    const utmMedium = sanitizeText(body.utmMedium, 120);
    const utmCampaign = sanitizeText(body.utmCampaign, 160);
    const utmContent = sanitizeText(body.utmContent, 160);
    const utmTerm = sanitizeText(body.utmTerm, 160);

    if (!email || !EMAIL_PATTERN.test(email)) {
      return NextResponse.json(
        { error: 'A valid work email is required.' },
        { status: 400 }
      );
    }

    const forwardedFor = request.headers.get('x-forwarded-for');
    const ipAddress = forwardedFor?.split(',')[0]?.trim() || null;
    const userAgent = request.headers.get('user-agent');

    const supabase = await createClient();
    const { error } = await supabase.from('waitlist_signups').insert({
      email,
      full_name: fullName,
      company_or_role: companyOrRole,
      biggest_bottleneck: biggestBottleneck,
      source,
      page_path: pagePath,
      referrer: referrer,
      utm_source: utmSource,
      utm_medium: utmMedium,
      utm_campaign: utmCampaign,
      utm_content: utmContent,
      utm_term: utmTerm,
      user_agent: userAgent,
      ip_address: ipAddress,
      metadata: {
        submitted_at: new Date().toISOString(),
        origin: request.headers.get('origin'),
      },
    });

    if (error) {
      if (error.code === '23505') {
        return NextResponse.json(
          { error: 'This email is already on the waitlist.' },
          { status: 409 }
        );
      }

      console.error('Waitlist signup error:', error);
      return NextResponse.json(
        { error: 'Unable to join the waitlist right now.' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: 'You are on the waitlist.',
    });
  } catch (error: unknown) {
    console.error('Waitlist route error:', error);
    const message = error instanceof Error ? error.message : 'Internal server error';

    return NextResponse.json(
      { error: message },
      { status: 500 }
    );
  }
}
