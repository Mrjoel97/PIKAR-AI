'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { createClient } from '@/lib/supabase/client';
import type { RealtimeChannel } from '@supabase/supabase-js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PikarTier = 'free' | 'solopreneur' | 'startup' | 'sme' | 'enterprise';

export interface SubscriptionRow {
    user_id: string;
    stripe_customer_id: string | null;
    stripe_subscription_id: string | null;
    tier: PikarTier;
    price_id: string | null;
    is_active: boolean;
    will_renew: boolean;
    period_type: 'normal' | 'trial' | 'intro';
    current_period_start: string | null;
    current_period_end: string | null;
    billing_issue_at: string | null;
    last_event_type: string | null;
}

export interface SubscriptionState {
    /** Whether the initial load has completed. */
    ready: boolean;
    /** Current active tier. */
    tier: PikarTier;
    /** Full subscription row from Supabase, or null for free users. */
    subscription: SubscriptionRow | null;
    /** Whether the subscription will auto-renew. */
    willRenew: boolean;
    /** End of current billing period. */
    periodEnd: Date | null;
    /** True when billing issue detected (past_due). */
    hasBillingIssue: boolean;
    /** True while a checkout/portal redirect is in flight. */
    loading: boolean;
    /** Last error message. */
    error: string | null;

    /** Redirect to Stripe Checkout for a given price ID. */
    checkout: (priceId: string) => Promise<void>;
    /** Redirect to Stripe Customer Portal (manage/cancel/update payment). */
    openPortal: () => Promise<void>;
    /** Refresh subscription state from Supabase. */
    refresh: () => Promise<void>;
}

const SubscriptionContext = createContext<SubscriptionState | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function SubscriptionProvider({ children }: { children: React.ReactNode }) {
    const [ready, setReady] = useState(false);
    const [subscription, setSubscription] = useState<SubscriptionRow | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    // Current user ID — tracked in state (not a ref) so the realtime effect
    // re-runs when the user changes (sign-in / sign-out). `null` before
    // bootstrap completes or while signed out.
    const [userId, setUserId] = useState<string | null>(null);
    const initRef = useRef(false);

    // Derived state.
    const tier: PikarTier = subscription?.is_active ? subscription.tier : 'free';
    const willRenew = subscription?.will_renew ?? false;
    const periodEnd = subscription?.current_period_end
        ? new Date(subscription.current_period_end)
        : null;
    const hasBillingIssue = Boolean(subscription?.billing_issue_at);

    // ── Load subscription from Supabase ──────────────────────────────────
    const loadSubscription = useCallback(async () => {
        const supabase = createClient();
        const { data: { user } } = await supabase.auth.getUser();
        if (!user) {
            setSubscription(null);
            setUserId(null);
            return;
        }

        setUserId(user.id);

        const { data } = await supabase
            .from('subscriptions')
            .select('*')
            .eq('user_id', user.id)
            .single();

        setSubscription(data as SubscriptionRow | null);
    }, []);

    // ── Bootstrap ────────────────────────────────────────────────────────
    useEffect(() => {
        if (initRef.current) return;
        initRef.current = true;

        loadSubscription().finally(() => setReady(true));

        // React to auth changes.
        const supabase = createClient();
        const { data: { subscription: authSub } } = supabase.auth.onAuthStateChange(
            async (_event, session) => {
                if (session?.user) {
                    await loadSubscription();
                } else {
                    setSubscription(null);
                    setUserId(null);
                }
            },
        );

        return () => {
            authSub.unsubscribe();
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // ── Realtime: subscribe to the user's subscription row ──────────────
    // When the Stripe webhook updates the row, the frontend receives a
    // postgres_changes event and the badge updates without a reload.
    //
    // Scoped per-user via filter=user_id=eq.${userId} — never subscribe
    // globally. Channel name includes the user ID so multi-tab sessions
    // stay cleanly separated. Effect depends on userId, so sign-in /
    // sign-out automatically tears down the old channel and opens a new
    // one (or no channel at all when signed out).
    useEffect(() => {
        if (!userId) return;

        const supabase = createClient();
        const channel: RealtimeChannel = supabase
            .channel(`subscription:user:${userId}`)
            .on(
                'postgres_changes',
                {
                    event: '*',
                    schema: 'public',
                    table: 'subscriptions',
                    filter: `user_id=eq.${userId}`,
                },
                (payload: {
                    eventType: 'INSERT' | 'UPDATE' | 'DELETE';
                    new: Record<string, unknown>;
                    old: Record<string, unknown>;
                }) => {
                    if (payload.eventType === 'DELETE') {
                        setSubscription(null);
                    } else {
                        setSubscription(payload.new as unknown as SubscriptionRow);
                    }
                },
            )
            .subscribe();

        return () => {
            supabase.removeChannel(channel);
        };
    }, [userId]);

    // ── Checkout (redirect to Stripe) ────────────────────────────────────
    const checkout = useCallback(async (priceId: string) => {
        setError(null);
        setLoading(true);
        try {
            const res = await fetch('/api/stripe/checkout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ priceId }),
            });

            const data = await res.json();
            if (!res.ok) {
                setError(data.error || 'Checkout failed');
                return;
            }

            // Redirect to Stripe-hosted checkout page.
            window.location.href = data.url;
        } catch {
            setError('Failed to start checkout. Please try again.');
        } finally {
            setLoading(false);
        }
    }, []);

    // ── Customer Portal (redirect to Stripe) ─────────────────────────────
    const openPortal = useCallback(async () => {
        setError(null);
        setLoading(true);
        try {
            const res = await fetch('/api/stripe/portal', {
                method: 'POST',
            });

            const data = await res.json();
            if (!res.ok) {
                setError(data.error || 'Could not open billing portal');
                return;
            }

            window.location.href = data.url;
        } catch {
            setError('Failed to open billing portal. Please try again.');
        } finally {
            setLoading(false);
        }
    }, []);

    // ── Refresh ──────────────────────────────────────────────────────────
    const refresh = useCallback(async () => {
        await loadSubscription();
    }, [loadSubscription]);

    return (
        <SubscriptionContext.Provider
            value={{
                ready,
                tier,
                subscription,
                willRenew,
                periodEnd,
                hasBillingIssue,
                loading,
                error,
                checkout,
                openPortal,
                refresh,
            }}
        >
            {children}
        </SubscriptionContext.Provider>
    );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useSubscription(): SubscriptionState {
    const ctx = useContext(SubscriptionContext);
    if (!ctx) {
        throw new Error('useSubscription must be used within a <SubscriptionProvider>');
    }
    return ctx;
}
