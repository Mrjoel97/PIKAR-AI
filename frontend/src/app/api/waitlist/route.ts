import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { getResend, RESEND_AUDIENCE_ID, FROM_ADDRESS } from '@/lib/resend';
import { rateLimiters, getClientIp } from '@/lib/rate-limit';
import WaitlistConfirmationEmail from '../../../../emails/waitlist-confirmation';

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

/**
 * Send confirmation email + sync contact to Resend audience.
 * Both operations are idempotent: the email uses an Idempotency-Key header
 * and contacts.create upserts by email within the audience.
 */
async function syncToResend(email: string, firstName: string | null, lastName: string | null) {
  const resend = getResend();
  const promises: Promise<unknown>[] = [
    resend.emails.send(
      {
        from: FROM_ADDRESS,
        to: email,
        subject: "You're on the Pikar AI waitlist 🎉",
        react: WaitlistConfirmationEmail({ firstName }),
      },
      {
        headers: {
          'Idempotency-Key': `waitlist-confirmation-${email}`,
        },
      }
    ),
  ];

  if (RESEND_AUDIENCE_ID) {
    promises.push(
      resend.contacts.create({
        audienceId: RESEND_AUDIENCE_ID,
        email,
        firstName: firstName ?? undefined,
        lastName: lastName ?? undefined,
        unsubscribed: false,
      })
    );
  }

  const results = await Promise.allSettled(promises);
  results.forEach((result, i) => {
    if (result.status === 'rejected') {
      console.error(`Waitlist Resend task ${i} failed:`, result.reason);
    }
  });
}

export async function POST(request: NextRequest) {
  const rl = rateLimiters.public.check(getClientIp(request));
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Too many requests. Please try again later.' },
      { status: 429, headers: { 'Retry-After': String(rl.retryAfter) } }
    );
  }

  try {
    const body = (await request.json()) as WaitlistRequestBody;

    // Honeypot — bots fill this, humans don't
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
        { error: 'A valid email is required.' },
        { status: 400 }
      );
    }

    const forwardedFor = request.headers.get('x-forwarded-for');
    const ipAddress = forwardedFor?.split(',')[0]?.trim() || null;
    const userAgent = request.headers.get('user-agent');

    const firstName = fullName?.split(' ')[0] ?? null;
    const lastName = fullName?.split(' ').slice(1).join(' ') || null;

    // ─── 1. Persist to Supabase ───────────────────────────────────────────────
    const supabase = await createClient();
    const { error: dbError } = await supabase.from('waitlist_signups').insert({
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

    if (dbError) {
      if (dbError.code === '23505') {
        // ─── Duplicate signup — still ensure the contact lands in Resend ────
        // Both Resend operations are idempotent, so this is safe to retry.
        await syncToResend(email, firstName, lastName);

        return NextResponse.json(
          { error: 'This email is already on the waitlist.' },
          { status: 409 }
        );
      }

      console.error('Waitlist signup error:', dbError);
      return NextResponse.json(
        { error: 'Unable to join the waitlist right now.' },
        { status: 500 }
      );
    }

    // ─── 2. Send confirmation email + add to Resend audience ──────────────────
    await syncToResend(email, firstName, lastName);

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
