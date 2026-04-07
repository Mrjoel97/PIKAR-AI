/**
 * @vitest-environment node
 *
 * Tests for POST /api/stripe/portal — BILL-05 test-coverage gap closed by
 * Plan 50-04 Task 2.
 *
 * The portal route creates a Stripe Customer Portal session and returns the
 * URL. It was shipped in a prior phase without unit coverage; this file adds
 * regression tests against the ACTUAL behaviour of the existing handler:
 *
 *   - 401 when no Supabase session
 *   - 404 when the authenticated user has no stripe_customer_id
 *     (route emits 404, not 400 — we match the handler, not the task brief)
 *   - 200 + { url } on happy path (asserts stripe.billingPortal.sessions.create
 *     is called with { customer, return_url })
 *   - 500 + generic error body when the Stripe SDK throws (does NOT leak the
 *     Stripe error stack to the client)
 *
 * DO NOT modify frontend/src/app/api/stripe/portal/route.ts — this file
 * describes existing behaviour. If a test fails, investigate the route only
 * to reconcile the mock shape; do not change route semantics in 50-04.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// ---------------------------------------------------------------------------
// Mocks — we stub @/lib/supabase/server and @/lib/stripe at the project
// boundary so the test never hits a real Supabase cookie store or Stripe SDK.
// ---------------------------------------------------------------------------

// Controlled return values for the Supabase auth + subscriptions query.
const authGetUserMock = vi.fn();
const subscriptionsSingleMock = vi.fn();

// The query chain is
//   supabase.from('subscriptions').select('stripe_customer_id').eq('user_id', user.id).single()
// so we return a builder per call that records nothing — the final
// .single() resolves to whatever subscriptionsSingleMock is configured to.
const supabaseFromMock = vi.fn((_table: string) => {
    void _table;
    return {
        select: (_cols: string) => {
            void _cols;
            return {
                eq: (_col: string, _val: unknown) => {
                    void _col;
                    void _val;
                    return {
                        single: () => subscriptionsSingleMock(),
                    };
                },
            };
        },
    };
});

const createClientMock = vi.fn().mockImplementation(async () => ({
    auth: {
        getUser: authGetUserMock,
    },
    from: supabaseFromMock,
}));

vi.mock('@/lib/supabase/server', () => ({
    createClient: createClientMock,
}));

// Stripe SDK mock — getStripe() returns an object exposing
// billingPortal.sessions.create(). We spy on it per test.
const billingPortalCreateMock = vi.fn();

const getStripeMock = vi.fn(() => ({
    billingPortal: {
        sessions: {
            create: billingPortalCreateMock,
        },
    },
}));

vi.mock('@/lib/stripe', () => ({
    getStripe: getStripeMock,
}));

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

async function loadRoute() {
    return import('../route');
}

const USER_ID = '22222222-2222-2222-2222-222222222222';
const CUSTOMER_ID = 'cus_test123';
const PORTAL_URL = 'https://billing.stripe.com/session/test';

// ---------------------------------------------------------------------------
// Env setup
// ---------------------------------------------------------------------------

beforeEach(() => {
    vi.resetModules();
    authGetUserMock.mockReset();
    subscriptionsSingleMock.mockReset();
    billingPortalCreateMock.mockReset();
    supabaseFromMock.mockClear();
    createClientMock.mockClear();
    getStripeMock.mockClear();

    process.env.STRIPE_SECRET_KEY = 'sk_test_dummy';
    process.env.NEXT_PUBLIC_APP_URL = 'http://localhost:3000';
});

afterEach(() => {
    vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('POST /api/stripe/portal', () => {
    it('Test 1: returns 401 when no Supabase session', async () => {
        authGetUserMock.mockResolvedValue({
            data: { user: null },
            error: { message: 'No session' },
        });

        const { POST } = await loadRoute();
        const res = await POST();

        expect(res.status).toBe(401);
        const body = await res.json();
        expect(body).toEqual({ error: 'Unauthorized' });

        // No Supabase subscription lookup and no Stripe SDK call allowed.
        expect(supabaseFromMock).not.toHaveBeenCalled();
        expect(getStripeMock).not.toHaveBeenCalled();
        expect(billingPortalCreateMock).not.toHaveBeenCalled();
    });

    it('Test 2: returns 404 when user has no stripe_customer_id', async () => {
        authGetUserMock.mockResolvedValue({
            data: { user: { id: USER_ID } },
            error: null,
        });
        // Subscription row exists but stripe_customer_id is null (e.g. free tier).
        subscriptionsSingleMock.mockResolvedValue({
            data: { stripe_customer_id: null },
            error: null,
        });

        const { POST } = await loadRoute();
        const res = await POST();

        // NOTE: the route returns 404 (not 400) because the caller "has no
        // billable customer" is semantically "not found". Task brief said
        // 400 but the brief also told us to match actual route behaviour.
        expect(res.status).toBe(404);
        const body = await res.json();
        expect(body).toEqual({
            error: 'No subscription found. Please subscribe first.',
        });

        // Supabase WAS consulted but Stripe must NOT have been called.
        expect(supabaseFromMock).toHaveBeenCalledWith('subscriptions');
        expect(getStripeMock).not.toHaveBeenCalled();
        expect(billingPortalCreateMock).not.toHaveBeenCalled();
    });

    it('Test 3: returns 200 and portal URL on happy path', async () => {
        authGetUserMock.mockResolvedValue({
            data: { user: { id: USER_ID } },
            error: null,
        });
        subscriptionsSingleMock.mockResolvedValue({
            data: { stripe_customer_id: CUSTOMER_ID },
            error: null,
        });
        billingPortalCreateMock.mockResolvedValue({ url: PORTAL_URL });

        const { POST } = await loadRoute();
        const res = await POST();

        expect(res.status).toBe(200);
        const body = await res.json();
        expect(body).toEqual({ url: PORTAL_URL });

        // Stripe SDK called with the customer ID and a return URL on this app.
        expect(getStripeMock).toHaveBeenCalledTimes(1);
        expect(billingPortalCreateMock).toHaveBeenCalledTimes(1);
        const call = billingPortalCreateMock.mock.calls[0][0];
        expect(call).toMatchObject({
            customer: CUSTOMER_ID,
            return_url: 'http://localhost:3000/dashboard/billing',
        });
    });

    it('Test 4: returns 500 with generic error when Stripe SDK throws', async () => {
        authGetUserMock.mockResolvedValue({
            data: { user: { id: USER_ID } },
            error: null,
        });
        subscriptionsSingleMock.mockResolvedValue({
            data: { stripe_customer_id: CUSTOMER_ID },
            error: null,
        });
        // Silence the expected console.error emitted by the route's catch.
        const consoleErrorSpy = vi
            .spyOn(console, 'error')
            .mockImplementation(() => {});
        const stripeErrorMessage =
            'StripeAuthenticationError: Invalid API Key provided: sk_test_***';
        billingPortalCreateMock.mockRejectedValue(new Error(stripeErrorMessage));

        const { POST } = await loadRoute();
        const res = await POST();

        expect(res.status).toBe(500);
        const body = await res.json();
        // Generic error only — must NOT leak the underlying Stripe message.
        expect(body).toEqual({ error: 'Failed to create portal session' });
        expect(JSON.stringify(body)).not.toContain('Invalid API Key');
        expect(JSON.stringify(body)).not.toContain('StripeAuthenticationError');

        consoleErrorSpy.mockRestore();
    });
});
