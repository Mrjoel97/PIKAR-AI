// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * POST /api/stripe/checkout
 *
 * Creates a Stripe Checkout Session in subscription mode and returns the URL.
 * The frontend redirects the user to this URL to complete payment on Stripe's
 * hosted checkout page.
 *
 * Body: { priceId: string }
 * Returns: { url: string }
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { getStripe } from '@/lib/stripe';

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';

export async function POST(request: NextRequest) {
    // ── Auth ─────────────────────────────────────────────────────────────
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();

    if (!user) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // ── Parse body ───────────────────────────────────────────────────────
    let priceId: string;
    try {
        const body = await request.json();
        priceId = body.priceId;
    } catch {
        return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
    }

    if (!priceId || typeof priceId !== 'string') {
        return NextResponse.json({ error: 'priceId is required' }, { status: 400 });
    }

    // ── Resolve or create Stripe customer ────────────────────────────────
    const stripe = getStripe();

    // Check if user already has a Stripe customer ID in subscriptions table.
    const { data: sub } = await supabase
        .from('subscriptions')
        .select('stripe_customer_id')
        .eq('user_id', user.id)
        .single();

    let customerId = sub?.stripe_customer_id;

    if (!customerId) {
        // Look up by email, or create new customer.
        const existing = await stripe.customers.list({
            email: user.email,
            limit: 1,
        });

        if (existing.data.length > 0) {
            customerId = existing.data[0].id;
        } else {
            const customer = await stripe.customers.create({
                email: user.email ?? undefined,
                metadata: { supabase_user_id: user.id },
            });
            customerId = customer.id;
        }
    }

    // ── Create Checkout Session ──────────────────────────────────────────
    try {
        const session = await stripe.checkout.sessions.create({
            mode: 'subscription',
            customer: customerId,
            line_items: [{ price: priceId, quantity: 1 }],
            success_url: `${APP_URL}/dashboard/billing?checkout=success`,
            cancel_url: `${APP_URL}/dashboard/billing?checkout=cancelled`,
            metadata: { supabase_user_id: user.id },
            subscription_data: {
                metadata: { supabase_user_id: user.id },
            },
        });

        return NextResponse.json({ url: session.url });
    } catch (err) {
        console.error('[stripe/checkout] Session creation failed:', err);
        return NextResponse.json(
            { error: 'Failed to create checkout session' },
            { status: 500 },
        );
    }
}
