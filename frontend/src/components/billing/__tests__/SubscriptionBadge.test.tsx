// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import React from 'react';
import { render, screen, cleanup } from '@testing-library/react';
import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest';
import { SubscriptionBadge } from '../SubscriptionBadge';
import type { SubscriptionState, SubscriptionRow, PikarTier } from '@/contexts/SubscriptionContext';

// ---------------------------------------------------------------------------
// Mock the SubscriptionContext module. Each test overrides useSubscription().
// ---------------------------------------------------------------------------

vi.mock('@/contexts/SubscriptionContext', () => ({
    useSubscription: vi.fn(),
}));

import { useSubscription } from '@/contexts/SubscriptionContext';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildRow(overrides: Partial<SubscriptionRow> = {}): SubscriptionRow {
    return {
        user_id: 'user-123',
        stripe_customer_id: 'cus_test',
        stripe_subscription_id: 'sub_test',
        tier: 'solopreneur',
        price_id: 'price_test',
        is_active: true,
        will_renew: true,
        period_type: 'normal',
        current_period_start: '2026-04-01T00:00:00Z',
        current_period_end: '2026-05-01T00:00:00Z',
        billing_issue_at: null,
        last_event_type: 'customer.subscription.created',
        ...overrides,
    };
}

function buildState(overrides: Partial<SubscriptionState> = {}): SubscriptionState {
    return {
        ready: true,
        tier: 'free' as PikarTier,
        subscription: null,
        willRenew: false,
        periodEnd: null,
        hasBillingIssue: false,
        loading: false,
        error: null,
        checkout: vi.fn(async () => {}),
        openPortal: vi.fn(async () => {}),
        refresh: vi.fn(async () => {}),
        ...overrides,
    };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SubscriptionBadge', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        cleanup();
    });

    it('renders "Free" when tier=free and no billing issue', () => {
        vi.mocked(useSubscription).mockReturnValue(
            buildState({ ready: true, tier: 'free', subscription: null, hasBillingIssue: false }),
        );

        render(<SubscriptionBadge />);

        const badge = screen.getByTestId('subscription-badge');
        expect(badge.textContent).toContain('Free');
        expect(badge.getAttribute('data-state')).toBe('free');
    });

    it('renders "Past Due" when hasBillingIssue=true', () => {
        vi.mocked(useSubscription).mockReturnValue(
            buildState({
                ready: true,
                tier: 'solopreneur',
                subscription: buildRow({
                    billing_issue_at: '2026-04-07T12:00:00Z',
                    last_event_type: 'invoice.payment_failed',
                }),
                willRenew: true,
                hasBillingIssue: true,
            }),
        );

        render(<SubscriptionBadge />);

        const badge = screen.getByTestId('subscription-badge');
        expect(badge.textContent).toContain('Past Due');
        expect(badge.getAttribute('data-state')).toBe('past_due');
    });

    it('renders "Trial" when period_type=trial', () => {
        vi.mocked(useSubscription).mockReturnValue(
            buildState({
                ready: true,
                tier: 'startup',
                subscription: buildRow({ tier: 'startup', period_type: 'trial' }),
                willRenew: true,
                hasBillingIssue: false,
            }),
        );

        render(<SubscriptionBadge />);

        const badge = screen.getByTestId('subscription-badge');
        expect(badge.textContent).toContain('Trial');
        expect(badge.textContent).toContain('Startup');
        expect(badge.getAttribute('data-state')).toBe('trial');
    });

    it('renders "Canceling" when is_active=true && willRenew=false', () => {
        vi.mocked(useSubscription).mockReturnValue(
            buildState({
                ready: true,
                tier: 'solopreneur',
                subscription: buildRow({ is_active: true, will_renew: false }),
                willRenew: false,
                hasBillingIssue: false,
            }),
        );

        render(<SubscriptionBadge />);

        const badge = screen.getByTestId('subscription-badge');
        expect(badge.textContent).toContain('Canceling');
        expect(badge.textContent).toContain('Solopreneur');
        expect(badge.getAttribute('data-state')).toBe('canceling');
    });

    it('renders "Active · Solopreneur" when is_active=true && willRenew=true && tier=solopreneur', () => {
        vi.mocked(useSubscription).mockReturnValue(
            buildState({
                ready: true,
                tier: 'solopreneur',
                subscription: buildRow({ is_active: true, will_renew: true }),
                willRenew: true,
                hasBillingIssue: false,
            }),
        );

        render(<SubscriptionBadge />);

        const badge = screen.getByTestId('subscription-badge');
        expect(badge.textContent).toContain('Active');
        expect(badge.textContent).toContain('Solopreneur');
        expect(badge.getAttribute('data-state')).toBe('active');
    });

    it('renders "Loading" when ready=false', () => {
        vi.mocked(useSubscription).mockReturnValue(
            buildState({ ready: false, tier: 'free', subscription: null }),
        );

        render(<SubscriptionBadge />);

        const badge = screen.getByTestId('subscription-badge');
        expect(badge.textContent).toContain('Loading');
        expect(badge.getAttribute('data-state')).toBe('loading');
    });
});
