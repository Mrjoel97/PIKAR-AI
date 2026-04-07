// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * POST /api/webhooks/stripe
 *
 * Receives Stripe webhook events and syncs subscription state to the
 * `subscriptions` Supabase table. Hardened with the `stripe_webhook_events`
 * idempotency ledger (BILL-02) and the BILL-01 event-ordering race fix.
 *
 * SOURCE-OF-TRUTH RULES:
 *   - customer.subscription.created / .updated / .deleted are the SOLE
 *     writers of tier / is_active / will_renew / period / price_id.
 *   - checkout.session.completed is DEMOTED to only setting
 *     stripe_customer_id on the subscriptions row, so a late re-delivery
 *     cannot regress state written by a later customer.subscription.*
 *     event (closes BILL-01).
 *
 * IDEMPOTENCY PATTERN (canonical — the only pattern used):
 *   1. Verify the Stripe signature.
 *   2. SELECT stripe_webhook_events WHERE event_id = ?
 *        - row exists + status='processed' -> short-circuit (duplicate)
 *        - row exists + status='error'     -> fall through and re-process
 *        - no row                          -> fall through and process
 *   3. Run the switch handler inside try/catch.
 *   4. On success: UPSERT stripe_webhook_events { status: 'processed' | 'skipped' }
 *   5. On error:   UPSERT stripe_webhook_events { status: 'error', error_message }
 *                  and return HTTP 500 so Stripe retries.
 *
 * Events handled:
 *   - checkout.session.completed     -> DEMOTED; only sets stripe_customer_id
 *   - customer.subscription.created  -> upsert full active row
 *   - customer.subscription.updated  -> upsert full row (renewals, cancels)
 *   - customer.subscription.deleted  -> deactivate row
 *   - invoice.payment_failed         -> set billing_issue_at
 *   - invoice.payment_succeeded      -> clear billing_issue_at (past_due recovery)
 */

import { createHash } from 'crypto';
import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';
import { createClient } from '@supabase/supabase-js';

// ---------------------------------------------------------------------------
// Stripe price ID -> Pikar tier mapping
// ---------------------------------------------------------------------------

function resolveTier(priceId: string | null | undefined): string {
    if (!priceId) return 'free';

    // Try env-based mapping first: STRIPE_PRICE_TIER_MAP=price_xxx:solopreneur,...
    const mapping = process.env.STRIPE_PRICE_TIER_MAP;
    if (mapping) {
        for (const pair of mapping.split(',')) {
            const [pid, tier] = pair.trim().split(':');
            if (pid === priceId) return tier;
        }
    }

    // Fallback: check if the price ID contains the tier name.
    const lower = priceId.toLowerCase();
    if (lower.includes('enterprise')) return 'enterprise';
    if (lower.includes('sme')) return 'sme';
    if (lower.includes('startup')) return 'startup';
    if (lower.includes('solopreneur')) return 'solopreneur';

    return 'solopreneur'; // Default paid tier.
}

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

function getStripe() {
    const key = process.env.STRIPE_SECRET_KEY;
    if (!key) throw new Error('STRIPE_SECRET_KEY not configured');
    return new Stripe(key);
}

function resolveCustomerId(customer: string | Stripe.Customer | Stripe.DeletedCustomer | null | undefined): string {
    if (!customer) return '';
    if (typeof customer === 'string') return customer;
    return customer.id ?? '';
}

// ---------------------------------------------------------------------------
// Handler
// ---------------------------------------------------------------------------

export async function POST(request: NextRequest) {
    const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
    if (!webhookSecret) {
        console.error('[stripe-webhook] STRIPE_WEBHOOK_SECRET not configured');
        return NextResponse.json({ error: 'Webhook not configured' }, { status: 500 });
    }

    // -- Verify signature -------------------------------------------------
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

    // -- Build Supabase service-role client -------------------------------
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (!supabaseUrl || !serviceRoleKey) {
        console.error('[stripe-webhook] Missing Supabase config');
        return NextResponse.json({ error: 'Server config error' }, { status: 500 });
    }

    const supabase = createClient(supabaseUrl, serviceRoleKey);

    // -- Idempotency: SELECT-first on stripe_webhook_events ---------------
    // Race window for parallel deliveries of the same event_id is narrow
    // and acceptable because (a) the downstream subscriptions writes are
    // themselves idempotent UPSERTs keyed on user_id, and (b) the event_id
    // PRIMARY KEY on stripe_webhook_events means only one of the parallel
    // deliveries can ultimately land a 'processed' row — the other will
    // conflict and be rewritten. No user-visible inconsistency is possible.
    const { data: existing } = await supabase
        .from('stripe_webhook_events')
        .select('event_id, status')
        .eq('event_id', event.id)
        .maybeSingle();

    if (existing && (existing as { status?: string }).status === 'processed') {
        console.info(`[stripe-webhook] duplicate delivery short-circuited event=${event.id}`);
        return NextResponse.json({ received: true, duplicate: true });
    }

    const payloadHash = createHash('sha256').update(rawBody).digest('hex');

    // -- Handle events ----------------------------------------------------
    let handled = true;
    let resolvedUserId: string | null = null;

    try {
        switch (event.type) {
            case 'checkout.session.completed': {
                // DEMOTED — customer.subscription.* is the sole source of truth
                // for tier/is_active/will_renew/period. This handler only sets
                // stripe_customer_id to avoid regressing state on late
                // re-delivery (BILL-01). If the row does not yet exist, insert
                // a minimal shell with stripe_customer_id only — the parallel
                // customer.subscription.created event will upgrade it.
                const session = event.data.object as Stripe.Checkout.Session;
                if (session.mode !== 'subscription') break;

                const userId = getUserId(session);
                if (!userId) {
                    console.warn('[stripe-webhook] checkout.session.completed missing supabase_user_id');
                    break;
                }
                resolvedUserId = userId;

                const customerId = resolveCustomerId(session.customer);

                // UPDATE-only write: set stripe_customer_id if the row exists.
                // Does NOT touch tier, is_active, will_renew, period, price_id.
                const { data: existingSub } = await supabase
                    .from('subscriptions')
                    .select('user_id')
                    .eq('user_id', userId)
                    .maybeSingle();

                if (existingSub) {
                    const { error: updErr } = await supabase
                        .from('subscriptions')
                        .update({
                            stripe_customer_id: customerId,
                        })
                        .eq('user_id', userId);
                    if (updErr) throw updErr;
                } else {
                    // Insert minimal shell with ONLY user_id + stripe_customer_id.
                    // Defaults (tier='free', is_active=false) will be overwritten
                    // by the parallel customer.subscription.created event.
                    const { error: insErr } = await supabase
                        .from('subscriptions')
                        .insert({
                            user_id: userId,
                            stripe_customer_id: customerId,
                        });
                    if (insErr) throw insErr;
                }

                console.info(`[stripe-webhook] checkout.session.completed user=${userId} (demoted: customer_id only)`);
                break;
            }

            case 'customer.subscription.created':
            case 'customer.subscription.updated': {
                // The authoritative state writer. Full upsert keyed on user_id.
                const subscription = event.data.object as Stripe.Subscription;
                const userId = getUserId(subscription);
                if (!userId) break;
                resolvedUserId = userId;

                const priceId = subscription.items.data[0]?.price?.id;
                const tier = resolveTier(priceId);
                const isActive = ['active', 'trialing', 'past_due'].includes(subscription.status);
                const period = getPeriod(subscription);

                const { error: upErr } = await supabase
                    .from('subscriptions')
                    .upsert(
                        {
                            user_id: userId,
                            stripe_customer_id: resolveCustomerId(subscription.customer),
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
                        },
                        { onConflict: 'user_id' },
                    );
                if (upErr) throw upErr;

                console.info(
                    `[stripe-webhook] ${event.type} user=${userId} tier=${tier} status=${subscription.status}`,
                );
                break;
            }

            case 'customer.subscription.deleted': {
                const subscription = event.data.object as Stripe.Subscription;
                const userId = getUserId(subscription);
                if (!userId) break;
                resolvedUserId = userId;

                const { error: upErr } = await supabase
                    .from('subscriptions')
                    .upsert(
                        {
                            user_id: userId,
                            stripe_customer_id: resolveCustomerId(subscription.customer),
                            stripe_subscription_id: subscription.id,
                            tier: 'free',
                            is_active: false,
                            will_renew: false,
                            billing_issue_at: null,
                            last_event_type: event.type,
                            last_event_at: new Date().toISOString(),
                        },
                        { onConflict: 'user_id' },
                    );
                if (upErr) throw upErr;

                console.info(`[stripe-webhook] subscription.deleted user=${userId}`);
                break;
            }

            case 'invoice.payment_failed': {
                const invoice = event.data.object as Stripe.Invoice;
                const subId = getInvoiceSubscriptionId(invoice);
                if (!subId) break;

                const subscription = await stripe.subscriptions.retrieve(subId);
                const userId = getUserId(subscription);
                if (!userId) break;
                resolvedUserId = userId;

                const { error: updErr } = await supabase
                    .from('subscriptions')
                    .update({
                        billing_issue_at: new Date().toISOString(),
                        last_event_type: event.type,
                        last_event_at: new Date().toISOString(),
                    })
                    .eq('user_id', userId);
                if (updErr) throw updErr;

                console.info(`[stripe-webhook] invoice.payment_failed user=${userId}`);
                break;
            }

            case 'invoice.payment_succeeded': {
                // Past_due recovery path: clear billing_issue_at if set.
                const invoice = event.data.object as Stripe.Invoice;
                const subId = getInvoiceSubscriptionId(invoice);
                if (!subId) break;

                const subscription = await stripe.subscriptions.retrieve(subId);
                const userId = getUserId(subscription);
                if (!userId) break;
                resolvedUserId = userId;

                const { error: updErr } = await supabase
                    .from('subscriptions')
                    .update({
                        billing_issue_at: null,
                        last_event_type: event.type,
                        last_event_at: new Date().toISOString(),
                    })
                    .eq('user_id', userId);
                if (updErr) throw updErr;

                console.info(`[stripe-webhook] invoice.payment_succeeded user=${userId} (billing_issue cleared)`);
                break;
            }

            default:
                handled = false;
                break;
        }
    } catch (err) {
        console.error('[stripe-webhook] Processing error:', err);
        const errorMessage = (err instanceof Error ? err.message : String(err)).slice(0, 500);

        await supabase.from('stripe_webhook_events').upsert(
            {
                event_id: event.id,
                type: event.type,
                status: 'error',
                payload_hash: payloadHash,
                error_message: errorMessage,
                user_id: resolvedUserId,
                received_at: new Date().toISOString(),
                processed_at: null,
            },
            { onConflict: 'event_id' },
        );

        return NextResponse.json({ error: 'Webhook processing error' }, { status: 500 });
    }

    // -- Record success in the idempotency ledger -------------------------
    await supabase.from('stripe_webhook_events').upsert(
        {
            event_id: event.id,
            type: event.type,
            status: handled ? 'processed' : 'skipped',
            payload_hash: payloadHash,
            error_message: null,
            user_id: resolvedUserId,
            received_at: new Date().toISOString(),
            processed_at: new Date().toISOString(),
        },
        { onConflict: 'event_id' },
    );

    if (!handled) {
        return NextResponse.json({ received: true, handled: false });
    }

    return NextResponse.json({ received: true });
}
