// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// @vitest-environment jsdom
import React, { act } from 'react';
import { render, screen, cleanup, waitFor } from '@testing-library/react';
import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest';
import { SubscriptionProvider, useSubscription, type SubscriptionRow } from '../SubscriptionContext';

// ---------------------------------------------------------------------------
// Mock @/lib/supabase/client
// ---------------------------------------------------------------------------

type PostgresChangesHandler = (payload: {
    eventType: 'INSERT' | 'UPDATE' | 'DELETE';
    new: Record<string, unknown>;
    old: Record<string, unknown>;
}) => void;

interface MockSupabaseClient {
    __authStateChangeCallback: ((event: string, session: unknown) => Promise<void> | void) | null;
    __postgresChangesHandler: PostgresChangesHandler | null;
    __removeChannelSpy: ReturnType<typeof vi.fn>;
    __channelSpy: ReturnType<typeof vi.fn>;
    __subscribeSpy: ReturnType<typeof vi.fn>;
    __currentUser: { id: string } | null;
    __subscriptionRow: SubscriptionRow | null;
    auth: {
        getUser: () => Promise<{ data: { user: { id: string } | null } }>;
        onAuthStateChange: (
            cb: (event: string, session: unknown) => Promise<void> | void,
        ) => { data: { subscription: { unsubscribe: () => void } } };
    };
    from: (table: string) => {
        select: (...args: unknown[]) => {
            eq: (...args: unknown[]) => {
                single: () => Promise<{ data: SubscriptionRow | null; error: null }>;
            };
        };
    };
    channel: (name: string) => {
        on: (
            event: string,
            config: Record<string, unknown>,
            handler: PostgresChangesHandler,
        ) => { subscribe: () => unknown };
    };
    removeChannel: (channel: unknown) => void;
}

let mockClient: MockSupabaseClient;

function makeMockClient(
    user: { id: string } | null,
    subscriptionRow: SubscriptionRow | null,
): MockSupabaseClient {
    const client: MockSupabaseClient = {
        __authStateChangeCallback: null,
        __postgresChangesHandler: null,
        __removeChannelSpy: vi.fn(),
        __channelSpy: vi.fn(),
        __subscribeSpy: vi.fn(),
        __currentUser: user,
        __subscriptionRow: subscriptionRow,
        auth: {
            getUser: vi.fn(async () => ({ data: { user: client.__currentUser } })),
            onAuthStateChange: vi.fn((cb) => {
                client.__authStateChangeCallback = cb;
                return {
                    data: { subscription: { unsubscribe: vi.fn() } },
                };
            }),
        },
        from: vi.fn(() => ({
            select: vi.fn(() => ({
                eq: vi.fn(() => ({
                    single: vi.fn(async () => ({
                        data: client.__subscriptionRow,
                        error: null,
                    })),
                })),
            })),
        })),
        channel: vi.fn((name: string) => {
            client.__channelSpy(name);
            const channelObj = {
                on: vi.fn((_event, _config, handler: PostgresChangesHandler) => {
                    client.__postgresChangesHandler = handler;
                    return channelObj;
                }),
                subscribe: vi.fn(() => {
                    client.__subscribeSpy();
                    return channelObj;
                }),
            };
            return channelObj;
        }),
        removeChannel: vi.fn((channel: unknown) => {
            client.__removeChannelSpy(channel);
        }),
    };
    return client;
}

vi.mock('@/lib/supabase/client', () => ({
    createClient: () => mockClient,
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const fixtureUser = { id: 'user-123' };

const fixtureRow: SubscriptionRow = {
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
};

// Simple consumer that exposes the context state via data attributes.
function Consumer() {
    const state = useSubscription();
    return (
        <div
            data-testid="consumer"
            data-ready={String(state.ready)}
            data-tier={state.tier}
            data-sub-tier={state.subscription?.tier ?? 'none'}
            data-is-active={String(state.subscription?.is_active ?? false)}
            data-last-event={state.subscription?.last_event_type ?? 'none'}
            data-has-billing-issue={String(state.hasBillingIssue)}
        >
            <button type="button" onClick={() => state.checkout('price_xyz')}>
                checkout
            </button>
            <button type="button" onClick={() => state.openPortal()}>
                portal
            </button>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

const originalLocation = window.location;

beforeEach(() => {
    mockClient = makeMockClient(fixtureUser, fixtureRow);

    // Mock fetch for checkout/portal
    global.fetch = vi.fn(async () => ({
        ok: true,
        json: async () => ({ url: 'https://stripe.test/session/123' }),
    })) as unknown as typeof fetch;

    // Stub window.location so checkout/openPortal redirects don't navigate jsdom.
    // @ts-expect-error overriding for tests
    delete window.location;
    // @ts-expect-error overriding for tests
    window.location = { href: '' };
});

afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    // @ts-expect-error restoring
    window.location = originalLocation;
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SubscriptionContext', () => {
    it('Test 1: loads subscription on mount for authenticated user', async () => {
        render(
            <SubscriptionProvider>
                <Consumer />
            </SubscriptionProvider>,
        );

        await waitFor(() => {
            expect(screen.getByTestId('consumer').getAttribute('data-ready')).toBe('true');
        });

        expect(mockClient.auth.getUser).toHaveBeenCalled();
        expect(mockClient.from).toHaveBeenCalledWith('subscriptions');
        expect(screen.getByTestId('consumer').getAttribute('data-sub-tier')).toBe('solopreneur');
        expect(screen.getByTestId('consumer').getAttribute('data-is-active')).toBe('true');
    });

    it('Test 2: reloads subscription on auth state change (SIGNED_IN)', async () => {
        render(
            <SubscriptionProvider>
                <Consumer />
            </SubscriptionProvider>,
        );

        await waitFor(() => {
            expect(screen.getByTestId('consumer').getAttribute('data-ready')).toBe('true');
        });

        const initialGetUserCalls = (mockClient.auth.getUser as ReturnType<typeof vi.fn>).mock
            .calls.length;
        const initialFromCalls = (mockClient.from as ReturnType<typeof vi.fn>).mock.calls.length;

        // Trigger the auth state change callback as Supabase would on SIGNED_IN.
        expect(mockClient.__authStateChangeCallback).not.toBeNull();
        await act(async () => {
            await mockClient.__authStateChangeCallback!('SIGNED_IN', {
                user: fixtureUser,
            });
        });

        // loadSubscription should have been called again — from('subscriptions') invoked anew.
        expect((mockClient.from as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(
            initialFromCalls,
        );
        // getUser is also invoked inside loadSubscription
        expect((mockClient.auth.getUser as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(
            initialGetUserCalls,
        );
    });

    it('Test 3: postgres_changes UPDATE event updates subscription state', async () => {
        render(
            <SubscriptionProvider>
                <Consumer />
            </SubscriptionProvider>,
        );

        await waitFor(() => {
            expect(screen.getByTestId('consumer').getAttribute('data-ready')).toBe('true');
        });

        // The SubscriptionContext should have opened a realtime channel scoped to the user.
        expect(mockClient.channel).toHaveBeenCalled();
        const channelName = (mockClient.__channelSpy as ReturnType<typeof vi.fn>).mock.calls[0]?.[0];
        expect(channelName).toContain('user-123');

        // Simulate a Stripe-webhook-triggered UPDATE arriving over postgres_changes.
        expect(mockClient.__postgresChangesHandler).not.toBeNull();
        const updatedRow: SubscriptionRow = {
            ...fixtureRow,
            last_event_type: 'customer.subscription.updated',
            billing_issue_at: '2026-04-07T12:00:00Z',
        };
        await act(async () => {
            mockClient.__postgresChangesHandler!({
                eventType: 'UPDATE',
                new: updatedRow as unknown as Record<string, unknown>,
                old: fixtureRow as unknown as Record<string, unknown>,
            });
        });

        await waitFor(() => {
            expect(screen.getByTestId('consumer').getAttribute('data-last-event')).toBe(
                'customer.subscription.updated',
            );
        });
        expect(screen.getByTestId('consumer').getAttribute('data-has-billing-issue')).toBe('true');
    });

    it('Test 4: removes realtime channel on unmount', async () => {
        const { unmount } = render(
            <SubscriptionProvider>
                <Consumer />
            </SubscriptionProvider>,
        );

        await waitFor(() => {
            expect(screen.getByTestId('consumer').getAttribute('data-ready')).toBe('true');
        });

        expect(mockClient.channel).toHaveBeenCalled();

        unmount();

        expect(mockClient.removeChannel).toHaveBeenCalled();
    });

    it('Test 5: checkout() posts to /api/stripe/checkout and redirects', async () => {
        render(
            <SubscriptionProvider>
                <Consumer />
            </SubscriptionProvider>,
        );

        await waitFor(() => {
            expect(screen.getByTestId('consumer').getAttribute('data-ready')).toBe('true');
        });

        const button = screen.getByText('checkout');
        await act(async () => {
            button.click();
        });

        expect(global.fetch).toHaveBeenCalledWith(
            '/api/stripe/checkout',
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({ priceId: 'price_xyz' }),
            }),
        );

        await waitFor(() => {
            expect(window.location.href).toBe('https://stripe.test/session/123');
        });
    });

    it('Test 6: openPortal() posts to /api/stripe/portal and redirects', async () => {
        render(
            <SubscriptionProvider>
                <Consumer />
            </SubscriptionProvider>,
        );

        await waitFor(() => {
            expect(screen.getByTestId('consumer').getAttribute('data-ready')).toBe('true');
        });

        const button = screen.getByText('portal');
        await act(async () => {
            button.click();
        });

        expect(global.fetch).toHaveBeenCalledWith(
            '/api/stripe/portal',
            expect.objectContaining({ method: 'POST' }),
        );

        await waitFor(() => {
            expect(window.location.href).toBe('https://stripe.test/session/123');
        });
    });
});
