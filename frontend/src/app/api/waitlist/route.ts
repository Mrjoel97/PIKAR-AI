import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { getResend, RESEND_AUDIENCE_ID, FROM_ADDRESS } from '@/lib/resend';
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

export async function POST(request: NextRequest) {
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
        { error: 'A valid work email is required.' },
        { status: 400 }
      );
    }

    const forwardedFor = request.headers.get('x-forwarded-for');
    const ipAddress = forwardedFor?.split(',')[0]?.trim() || null;
    const userAgent = request.headers.get('user-agent');

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

    // ─── 2. Fire-and-forget: email + audience (don't block the response) ──────
    // Both operations run in parallel after the DB write succeeds.
    const firstName = fullName?.split(' ')[0] ?? null;
    const lastName = fullName?.split(' ').slice(1).join(' ') || null;

    const resend = getResend();
    const emailAndAudiencePromises: Promise<unknown>[] = [
      // Confirmation email — idempotency key prevents duplicate sends on retry
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

    // Add to Resend audience for broadcast campaigns (requires RESEND_AUDIENCE_ID)
    if (RESEND_AUDIENCE_ID) {
      emailAndAudiencePromises.push(
        resend.contacts.create({
          audienceId: RESEND_AUDIENCE_ID,
          email,
          firstName: firstName ?? undefined,
          lastName: lastName ?? undefined,
          unsubscribed: false,
        })
      );
    }

    // Run in background — don't await so the user gets an instant response
    Promise.allSettled(emailAndAudiencePromises).then((results) => {
      results.forEach((result, i) => {
        if (result.status === 'rejected') {
          console.error(`Waitlist post-signup task ${i} failed:`, result.reason);
        }
      });
    });

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
