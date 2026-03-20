import { Resend } from 'resend';

/** Lazy singleton — created on first use, not at import time */
let _resend: Resend | null = null;

export function getResend(): Resend {
  if (!_resend) {
    const key = process.env.RESEND_API_KEY;
    if (!key) {
      throw new Error('RESEND_API_KEY environment variable is not set');
    }
    _resend = new Resend(key);
  }
  return _resend;
}

/** Resend audience ID for waitlist contacts — set via RESEND_AUDIENCE_ID env var */
export const RESEND_AUDIENCE_ID = process.env.RESEND_AUDIENCE_ID ?? null;

/** From address — pikar-ai.com is verified in Resend (DKIM + SPF green) */
export const FROM_ADDRESS =
  process.env.RESEND_FROM_ADDRESS ?? 'Pikar AI <hello@pikar-ai.com>';
