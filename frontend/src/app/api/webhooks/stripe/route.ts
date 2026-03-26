// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * POST /api/webhooks/stripe
 *
 * Receives Stripe webhook events and syncs subscription state to the
 * `subscriptions` Supabase table. Uses signature verification to ensure
 * events are authentic.
 *
 * Key events handled:
 *   - checkout.session.completed     → initial subscription creation
 *   - customer.subscription.updated  → renewals, upgrades, downgrades, cancellations
 *   - customer.subscription.deleted  → subscription ended
 *   - invoice.payment_failed         → billing issue detected
 */

import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';
import { createClient } from '@supabase/supabase-js';

// ---------------------------------------------------------------------------
// Stripe price ID → Pikar tier mapping
// ---------------------------------------------------------------------------
// These must match the Price IDs you create in Stripe Dashboard.
// Format: { [stripe_price_id]: pikar_tier }
// Loaded from env to avoid hardcoding Stripe IDs in code.

function resolveTier(priceId: string | null | undefined): string {
    if (!priceId) return 'free';

    // Try env-based mapping first: STRIPE_PRICE_TIER_MAP=price_xxx:solopreneur,price_yyy:startup,...
    const mapping = process.env.STRIPE_PRICE_TIER_MAP;
    if (mapping) {
        for (const pair of mapping.split(',')) {
            const [pid, tier] = pair.trim().split(':');
            if (pid === priceId) return tier;
        }
    }

    // Fallback: check if the price ID contains the tier name (common naming convention).
    const lower = priceId.toLowerCase();
    if (lower.includes('enterprise')) return 'enterprise';
    if (lower.includes('sme')) return 'sme';
    if (lower.includes('startup')) return 'startup';
    if (lower.includes('solopreneur')) return 'solopreneur';

    return 'solopreneur'; // Default paid tier.
}

// ---------------------------------------------------------------------------
// Extract the Supabase user ID from Stripe metadata
// ---------------------------------------------------------------------------

function getUserId(obj: { metadata?: Record<string, string> | null }): string | null {
    return obj.metadata?.supabase_user_id ?? null;
}

/** Extract billing period from a subscription (handles SDK version differences). */
function getPeriod(sub: Stripe.Subscription): { start: string | null; end: string | null } {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const raw = sub as any;
    const startTs: number | undefined = raw.current_period_start
        ?? sub.items?.data?.[0]?.current_period_start;
    const endTs: number | undefined = raw.current_period_end
        ?? sub.items?.data?.[0]?.current_period_end;
    return {
        start: startTs ? new Date(startTs * 1000).toISOString() : null,
        end: endTs ? new Date(endTs * 1000).toISOString() : null,
    };
}

/** Safely extract the subscription ID string from an invoice. */
function getInvoiceSubscriptionId(invoice: Stripe.Invoice): string | null {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const raw = invoice as any;
    if (typeof raw.subscription === 'string') return raw.subscription;
    if (raw.subscription?.id) return raw.subscription.id;
    return null;
}

// ---------------------------------------------------------------------------
// Handler
// ---------------------------------------------------------------------------

function getStripe() {
    const key = process.env.STRIPE_SECRET_KEY;
    if (!key) throw new Error('STRIPE_SECRET_KEY not configured');
    return new Stripe(key);
}

export async function POST(request: NextRequest) {
    const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
    if (!webhookSecret) {
        console.error('[stripe-webhook] STRIPE_WEBHOOK_SECRET not configured');
        return NextResponse.json({ error: 'Webhook not configured' }, { status: 500 });
    }

    // ── Verify signature ─────────────────────────────────────────────────
    const rawBody = await request.text();
    const sig = request.headers.get('stripe-signature');

    if (!sig) {
        return NextResponse.json({ error: 'Missing stripe-signature' }, { status: 400 });
    }

    let stripe: Stripe;
    try {
        stripe = getStripe();
    } catch {
        console.error('[stripe-webhook] STRIPE_SECRET_KEY not configured');
        return NextResponse.json({ error: 'Stripe not configured' }, { status: 500 });
    }

    let event: Stripe.Event;
    try {
        event = stripe.webhooks.constructEvent(rawBody, sig, webhookSecret);
    } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        console.error('[stripe-webhook] Signature verification failed:', message);
        return NextResponse.json({ error: `Webhook Error: ${message}` }, { status: 400 });
    }

    // ── Build Supabase service-role client ────────────────────────────────
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!supabaseUrl || !serviceRoleKey) {
        console.error('[stripe-webhook] Missing Supabase config');
        return NextResponse.json({ error: 'Server config error' }, { status: 500 });
    }

    const supabase = createClient(supabaseUrl, serviceRoleKey);

    // ── Handle events ────────────────────────────────────────────────────
    try {
        switch (event.type) {
            case 'checkout.session.completed': {
                const session = event.data.object as Stripe.Checkout.Session;
                if (session.mode !== 'subscription') break;

                const userId = getUserId(session);
                if (!userId) {
                    console.warn('[stripe-webhook] checkout.session.completed missing supabase_user_id');
                    break;
                }

                // Retrieve the full subscription to get price info.
                const subscriptionId = typeof session.subscription === 'string'
                    ? session.subscription
                    : session.subscription?.id;

                if (!subscriptionId) break;

                const subscription = await stripe.subscriptions.retrieve(subscriptionId);
                const priceId = subscription.items.data[0]?.price?.id;
                const tier = resolveTier(priceId);
                const period = getPeriod(subscription);

                await supabase.from('subscriptions').upsert({
                    user_id: userId,
                    stripe_customer_id: typeof session.customer === 'string'
                        ? session.customer
                        : session.customer?.id ?? '',
                    stripe_subscription_id: subscriptionId,
                    tier,
                    price_id: priceId ?? null,
                    is_active: true,
                    will_renew: !subscription.cancel_at_period_end,
                    period_type: subscription.status === 'trialing' ? 'trial' : 'normal',
                    current_period_start: period.start,
                    current_period_end: period.end,
                    billing_issue_at: null,
                    last_event_type: event.type,
                    last_event_at: new Date().toISOString(),
                }, { onConflict: 'user_id' });

                console.info(`[stripe-webhook] checkout.session.completed user=${userId} tier=${tier}`);
                break;
            }

            case 'customer.subscription.updated': {
                const subscription = event.data.object as Stripe.Subscription;
                const userId = getUserId(subscription);
                if (!userId) break;

                const priceId = subscription.items.data[0]?.price?.id;
                const tier = resolveTier(priceId);
                const isActive = ['active', 'trialing', 'past_due'].includes(subscription.status);
                const period = getPeriod(subscription);

                await supabase.from('subscriptions').upsert({
                    user_id: userId,
                    stripe_customer_id: typeof subscription.customer === 'string'
                        ? subscription.customer
                        : subscription.customer?.id ?? '',
                    stripe_subscription_id: subscription.id,
                    tier: isActive ? tier : 'free',
                    price_id: priceId ?? null,
                    is_active: isActive,
                    will_renew: !subscription.cancel_at_period_end,
                    period_type: subscription.status === 'trialing' ? 'trial' : 'normal',
                    current_period_start: period.start,
                    current_period_end: period.end,
                    billing_issue_at: subscription.status === 'past_due'
                        ? new Date().toISOString()
                        : null,
                    last_event_type: event.type,
                    last_event_at: new Date().toISOString(),
                }, { onConflict: 'user_id' });

                console.info(`[stripe-webhook] subscription.updated user=${userId} tier=${tier} status=${subscription.status}`);
                break;
            }

            case 'customer.subscription.deleted': {
                const subscription = event.data.object as Stripe.Subscription;
                const userId = getUserId(subscription);
                if (!userId) break;

                await supabase.from('subscriptions').upsert({
                    user_id: userId,
                    stripe_customer_id: typeof subscription.customer === 'string'
                        ? subscription.customer
                        : subscription.customer?.id ?? '',
                    stripe_subscription_id: subscription.id,
                    tier: 'free',
                    is_active: false,
                    will_renew: false,
                    billing_issue_at: null,
                    last_event_type: event.type,
                    last_event_at: new Date().toISOString(),
                }, { onConflict: 'user_id' });

                console.info(`[stripe-webhook] subscription.deleted user=${userId}`);
                break;
            }

            case 'invoice.payment_failed': {
                const invoice = event.data.object as Stripe.Invoice;
                const subId = getInvoiceSubscriptionId(invoice);

                if (!subId) break;

                // Look up the subscription to get the user ID.
                const subscription = await stripe.subscriptions.retrieve(subId);
                const userId = getUserId(subscription);
                if (!userId) break;

                await supabase.from('subscriptions').update({
                    billing_issue_at: new Date().toISOString(),
                    last_event_type: event.type,
                    last_event_at: new Date().toISOString(),
                }).eq('user_id', userId);

                console.info(`[stripe-webhook] invoice.payment_failed user=${userId}`);
                break;
            }

            default:
                // Unhandled event — acknowledge receipt.
                break;
        }
    } catch (err) {
        console.error('[stripe-webhook] Processing error:', err);
        return NextResponse.json({ error: 'Webhook processing error' }, { status: 500 });
    }

    return NextResponse.json({ received: true });
}
