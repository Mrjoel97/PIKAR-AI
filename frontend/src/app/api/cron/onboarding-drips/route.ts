import { NextRequest, NextResponse } from 'next/server';
import { createClient as createServiceClient } from '@supabase/supabase-js';
import { getResend, FROM_ADDRESS } from '@/lib/resend';
import { rateLimiters, getClientIp } from '@/lib/rate-limit';
import OnboardingDripEmail, { DRIP_SUBJECTS } from '../../../../../emails/onboarding-drip';

type Persona = 'solopreneur' | 'startup' | 'sme' | 'enterprise';
type DripKey = 'welcome' | 'tips' | 'checkin';

const CRON_SECRET = process.env.CRON_SECRET;

/**
 * GET /api/cron/onboarding-drips
 * Processes pending drip emails that are due.
 * Called by Vercel Cron every hour.
 */
export async function GET(request: NextRequest) {
  const rl = rateLimiters.cron.check(getClientIp(request));
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Too many requests' },
      { status: 429, headers: { 'Retry-After': String(rl.retryAfter) } }
    );
  }

  // Verify cron secret to prevent unauthorized access
  if (CRON_SECRET) {
    const authHeader = request.headers.get('authorization');
    if (authHeader !== `Bearer ${CRON_SECRET}`) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !serviceRoleKey) {
    return NextResponse.json({ error: 'Missing Supabase config' }, { status: 500 });
  }

  // Use service role client for cross-user access
  const supabase = createServiceClient(supabaseUrl, serviceRoleKey);

  // Find pending drips that are due
  const { data: pendingDrips, error: fetchError } = await supabase
    .from('onboarding_drip_emails')
    .select('*')
    .eq('status', 'pending')
    .lte('scheduled_at', new Date().toISOString())
    .order('scheduled_at', { ascending: true })
    .limit(50); // Process in batches

  if (fetchError) {
    console.error('Drip fetch error:', fetchError);
    return NextResponse.json({ error: 'Failed to fetch drips' }, { status: 500 });
  }

  if (!pendingDrips || pendingDrips.length === 0) {
    return NextResponse.json({ processed: 0 });
  }

  const resend = getResend();
  let sent = 0;
  let failed = 0;

  for (const drip of pendingDrips) {
    const persona = drip.persona as Persona;
    const dripKey = drip.drip_key as DripKey;

    try {
      const subject = DRIP_SUBJECTS[dripKey](persona);

      await resend.emails.send(
        {
          from: FROM_ADDRESS,
          to: drip.email,
          subject,
          react: OnboardingDripEmail({
            firstName: drip.first_name,
            persona,
            dripKey,
          }),
        },
        {
          headers: {
            'Idempotency-Key': `onboarding-drip-${drip.user_id}-${dripKey}`,
          },
        }
      );

      // Mark as sent
      await supabase
        .from('onboarding_drip_emails')
        .update({ status: 'sent', sent_at: new Date().toISOString() })
        .eq('id', drip.id);

      sent++;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      console.error(`Drip send failed for ${drip.email} (${dripKey}):`, message);

      // Mark as failed with error message
      await supabase
        .from('onboarding_drip_emails')
        .update({ status: 'failed', error_message: message.slice(0, 500) })
        .eq('id', drip.id);

      failed++;
    }
  }

  return NextResponse.json({ processed: pendingDrips.length, sent, failed });
}
