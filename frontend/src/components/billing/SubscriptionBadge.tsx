'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useSubscription, type PikarTier } from '@/contexts/SubscriptionContext';

// ---------------------------------------------------------------------------
// Status resolution
// ---------------------------------------------------------------------------

type BadgeState =
    | 'loading'
    | 'free'
    | 'past_due'
    | 'trial'
    | 'canceling'
    | 'active'
    | 'canceled';

interface BadgeView {
    state: BadgeState;
    label: string;
    className: string;
    showIcon: boolean;
}

const TIER_LABELS: Record<PikarTier, string> = {
    free: 'Free',
    solopreneur: 'Solopreneur',
    startup: 'Startup',
    sme: 'SME',
    enterprise: 'Enterprise',
};

const BASE_CLASSES =
    'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium';

/**
 * Resolve the badge state from the current subscription context.
 *
 * State precedence (top match wins):
 *   1. !ready                                   → "Loading"
 *   2. tier=free && no billing issue            → "Free"
 *   3. hasBillingIssue                          → "Past Due"
 *   4. period_type=trial                        → "Trial"
 *   5. is_active && !will_renew                 → "Canceling"
 *   6. is_active                                → "Active · <tier>"
 *   7. otherwise                                → "Canceled"
 */
function resolveBadge(state: ReturnType<typeof useSubscription>): BadgeView {
    const { ready, tier, subscription, willRenew, hasBillingIssue } = state;

    if (!ready) {
        return {
            state: 'loading',
            label: 'Loading',
            className: `${BASE_CLASSES} border-gray-700 bg-gray-800 text-gray-400`,
            showIcon: false,
        };
    }

    if (tier === 'free' && !hasBillingIssue) {
        return {
            state: 'free',
            label: 'Free',
            className: `${BASE_CLASSES} border-gray-700 bg-gray-800 text-gray-300`,
            showIcon: false,
        };
    }

    if (hasBillingIssue) {
        return {
            state: 'past_due',
            label: 'Past Due',
            className: `${BASE_CLASSES} border-red-700/50 bg-red-900/30 text-red-400`,
            showIcon: true,
        };
    }

    if (subscription?.period_type === 'trial') {
        return {
            state: 'trial',
            label: `Trial · ${TIER_LABELS[tier]}`,
            className: `${BASE_CLASSES} border-blue-700/50 bg-blue-900/30 text-blue-400`,
            showIcon: false,
        };
    }

    if (subscription?.is_active && !willRenew) {
        return {
            state: 'canceling',
            label: `Canceling · ${TIER_LABELS[tier]}`,
            className: `${BASE_CLASSES} border-amber-700/50 bg-amber-900/30 text-amber-400`,
            showIcon: true,
        };
    }

    if (subscription?.is_active) {
        return {
            state: 'active',
            label: `Active · ${TIER_LABELS[tier]}`,
            className: `${BASE_CLASSES} border-emerald-700/50 bg-emerald-900/30 text-emerald-400`,
            showIcon: false,
        };
    }

    return {
        state: 'canceled',
        label: 'Canceled',
        className: `${BASE_CLASSES} border-gray-700 bg-gray-800 text-gray-400`,
        showIcon: false,
    };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * SubscriptionBadge renders a color-coded pill reflecting the current
 * subscription state for the authenticated user. Reads from
 * SubscriptionContext — must be placed inside <SubscriptionProvider>.
 *
 * State → color mapping:
 *   - Loading  → gray
 *   - Free     → gray
 *   - Past Due → red (with AlertTriangle icon)
 *   - Trial    → blue
 *   - Canceling→ amber (with AlertTriangle icon)
 *   - Active   → emerald
 *   - Canceled → gray
 *
 * For paid tiers the tier name is appended: "Active · Solopreneur".
 *
 * The component exposes `data-testid="subscription-badge"` and
 * `data-state="<state>"` for e2e test anchoring.
 */
export function SubscriptionBadge() {
    const state = useSubscription();
    const view = resolveBadge(state);

    return (
        <span
            data-testid="subscription-badge"
            data-state={view.state}
            className={view.className}
        >
            {view.showIcon && (
                <AlertTriangle className="h-3 w-3 shrink-0" aria-hidden="true" />
            )}
            <span>{view.label}</span>
        </span>
    );
}
