// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * POST /api/stripe/portal
 *
 * Creates a Stripe Customer Portal session and returns the URL.
 * The portal lets users manage their subscription (upgrade, downgrade,
 * cancel, update payment method) entirely on Stripe's hosted UI.
 *
 * Returns: { url: string }
 */

import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { getStripe } from '@/lib/stripe';

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';

export async function POST() {
    // ── Auth ─────────────────────────────────────────────────────────────
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // ── Look up Stripe customer ID ───────────────────────────────────────
    const { data: sub } = await supabase
        .from('subscriptions')
        .select('stripe_customer_id')
        .eq('user_id', user.id)
        .single();

    if (!sub?.stripe_customer_id) {
        return NextResponse.json(
            { error: 'No subscription found. Please subscribe first.' },
            { status: 404 },
        );
    }

    // ── Create portal session ────────────────────────────────────────────
    try {
        const stripe = getStripe();
        const session = await stripe.billingPortal.sessions.create({
            customer: sub.stripe_customer_id,
            return_url: `${APP_URL}/dashboard/billing`,
        });

        return NextResponse.json({ url: session.url });
    } catch (err) {
        console.error('[stripe/portal] Session creation failed:', err);
        return NextResponse.json(
            { error: 'Failed to create portal session' },
            { status: 500 },
        );
    }
}
