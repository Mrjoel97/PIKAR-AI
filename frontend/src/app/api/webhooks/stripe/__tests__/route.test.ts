/**
 * @vitest-environment node
 *
 * Tests for POST /api/webhooks/stripe — BILL-01 (event-ordering race) and
 * BILL-02 (webhook idempotency).
 *
 * The 9 tests in this file enforce the invariant that customer.subscription.*
 * events are the sole source of truth for subscription state, that
 * checkout.session.completed is demoted to only setting stripe_customer_id,
 * and that duplicate / out-of-order webhook deliveries cannot regress fresh
 * state.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// ---------------------------------------------------------------------------
// Stripe mock — we stub constructEvent to return whatever the test sets up
// ---------------------------------------------------------------------------

const constructEventMock = vi.fn();
const subscriptionsRetrieveMock = vi.fn();

vi.mock('stripe', () => {
    // Return a ctor whose instance exposes webhooks.constructEvent and
    // subscriptions.retrieve (both spied).
    const Stripe = vi.fn().mockImplementation(() => ({
        webhooks: { constructEvent: constructEventMock },
        subscriptions: { retrieve: subscriptionsRetrieveMock },
    }));
    return { default: Stripe };
});

// ---------------------------------------------------------------------------
// Supabase mock — a stateful recorder so the BILL-01 regression test can
// assert the EXACT shape of each write the handler performs.
// ---------------------------------------------------------------------------

type WriteOp = {
    table: string;
    op: 'select' | 'upsert' | 'update' | 'insert';
    payload?: Record<string, unknown>;
    match?: Record<string, unknown>;
};

const writes: WriteOp[] = [];

// Controlled return values for specific (table, op) combinations.
const controlled: Record<string, unknown> = {};

function setControlled(key: string, value: unknown) {
    controlled[key] = value;
}

function resetSupabaseState() {
    writes.length = 0;
    for (const k of Object.keys(controlled)) delete controlled[k];
}

const createClientMock = vi.fn().mockImplementation(() => ({
    from(table: string) {
        const builder = {
            _table: table,
            select(_cols: string) {
                return {
                    eq(_col: string, val: unknown) {
                        return {
                            maybeSingle: async () => {
                                writes.push({
                                    table,
                                    op: 'select',
                                    match: { [_col]: val },
                                });
                                const key = `${table}.select.${val}`;
                                if (controlled[key] !== undefined) {
                                    return {
                                        data: controlled[key] as Record<string, unknown> | null,
                                        error: null,
                                    };
                                }
                                return { data: null, error: null };
                            },
                        };
                    },
                };
            },
            upsert(payload: Record<string, unknown>, _opts?: unknown) {
                writes.push({ table, op: 'upsert', payload });
                const key = `${table}.upsert.error`;
                if (controlled[key]) {
                    return Promise.resolve({ data: null, error: controlled[key] });
                }
                return Promise.resolve({ data: null, error: null });
            },
            insert(payload: Record<string, unknown>) {
                writes.push({ table, op: 'insert', payload });
                const key = `${table}.insert.error`;
                if (controlled[key]) {
                    return Promise.resolve({ data: null, error: controlled[key] });
                }
                return Promise.resolve({ data: null, error: null });
            },
            update(payload: Record<string, unknown>) {
                return {
                    eq(_col: string, val: unknown) {
                        writes.push({
                            table,
                            op: 'update',
                            payload,
                            match: { [_col]: val },
                        });
                        const key = `${table}.update.error`;
                        if (controlled[key]) {
                            return Promise.resolve({ data: null, error: controlled[key] });
                        }
                        return Promise.resolve({ data: null, error: null });
                    },
                };
            },
        };
        return builder;
    },
}));

vi.mock('@supabase/supabase-js', () => ({
    createClient: createClientMock,
}));

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

type StripeEventFixture = {
    id: string;
    type: string;
    data: { object: Record<string, unknown> };
};

/** Build a NextRequest-ish object that the handler can consume via text(). */
function buildRequest(body: string, headers: Record<string, string> = {}) {
    return {
        async text() {
            return body;
        },
        headers: {
            get(name: string) {
                return headers[name.toLowerCase()] ?? headers[name] ?? null;
            },
        },
    } as unknown as import('next/server').NextRequest;
}

/** Dynamically import the route module so each test hits a fresh instance. */
async function loadRoute() {
    return import('../route');
}

const USER_ID = '11111111-1111-1111-1111-111111111111';
const CUSTOMER_ID = 'cus_test_123';
const SUBSCRIPTION_ID = 'sub_test_123';
const PRICE_ID = 'price_solopreneur_monthly';

function subscriptionObject(overrides: Partial<Record<string, unknown>> = {}) {
    return {
        id: SUBSCRIPTION_ID,
        customer: CUSTOMER_ID,
        status: 'active',
        cancel_at_period_end: false,
        current_period_start: 1_700_000_000,
        current_period_end: 1_702_592_000,
        items: { data: [{ price: { id: PRICE_ID } }] },
        metadata: { supabase_user_id: USER_ID },
        ...overrides,
    };
}

function checkoutSessionObject(overrides: Partial<Record<string, unknown>> = {}) {
    return {
        id: 'cs_test_123',
        mode: 'subscription',
        customer: CUSTOMER_ID,
        subscription: SUBSCRIPTION_ID,
        metadata: { supabase_user_id: USER_ID },
        ...overrides,
    };
}

function invoiceObject(overrides: Partial<Record<string, unknown>> = {}) {
    return {
        id: 'in_test_123',
        subscription: SUBSCRIPTION_ID,
        ...overrides,
    };
}

// ---------------------------------------------------------------------------
// Env setup
// ---------------------------------------------------------------------------

beforeEach(() => {
    vi.resetModules();
    constructEventMock.mockReset();
    subscriptionsRetrieveMock.mockReset();
    createClientMock.mockClear();
    resetSupabaseState();

    process.env.STRIPE_WEBHOOK_SECRET = 'whsec_test';
    process.env.STRIPE_SECRET_KEY = 'sk_test_dummy';
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://localhost:54321';
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'service_role_dummy';
    process.env.STRIPE_PRICE_TIER_MAP = `${PRICE_ID}:solopreneur`;
});

afterEach(() => {
    vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('POST /api/webhooks/stripe', () => {
    it('Test 1: returns 400 and writes nothing when signature is invalid', async () => {
        constructEventMock.mockImplementation(() => {
            throw new Error('Invalid signature');
        });

        const { POST } = await loadRoute();
        const res = await POST(buildRequest('{}', { 'stripe-signature': 'bad' }));

        expect(res.status).toBe(400);
        // No subscriptions or stripe_webhook_events writes allowed.
        expect(writes.filter((w) => w.table === 'subscriptions')).toHaveLength(0);
        expect(
            writes.filter((w) => w.table === 'stripe_webhook_events' && w.op !== 'select'),
        ).toHaveLength(0);
    });

    it('Test 2: checkout.session.completed only writes stripe_customer_id (demoted)', async () => {
        const event: StripeEventFixture = {
            id: 'evt_checkout_1',
            type: 'checkout.session.completed',
            data: { object: checkoutSessionObject() },
        };
        constructEventMock.mockReturnValue(event);
        subscriptionsRetrieveMock.mockResolvedValue(subscriptionObject());

        const { POST } = await loadRoute();
        const res = await POST(
            buildRequest(JSON.stringify(event), { 'stripe-signature': 'sig' }),
        );

        expect(res.status).toBe(200);

        // Find the subscriptions write — must be an UPDATE (or a narrow INSERT)
        // that touches ONLY stripe_customer_id.
        const subsWrites = writes.filter((w) => w.table === 'subscriptions');
        expect(subsWrites.length).toBeGreaterThanOrEqual(1);

        const forbiddenKeys = [
            'tier',
            'is_active',
            'will_renew',
            'price_id',
            'current_period_start',
            'current_period_end',
            'stripe_subscription_id',
            'period_type',
        ];

        for (const w of subsWrites) {
            const keys = Object.keys(w.payload ?? {});
            for (const forbidden of forbiddenKeys) {
                expect(
                    keys.includes(forbidden),
                    `checkout.session.completed must NOT write ${forbidden} (found in ${w.op})`,
                ).toBe(false);
            }
            // Positive assertion: stripe_customer_id must be written.
            expect(keys).toContain('stripe_customer_id');
        }

        // stripe_webhook_events upsert must happen once with status=processed.
        const swe = writes.filter(
            (w) => w.table === 'stripe_webhook_events' && w.op === 'upsert',
        );
        expect(swe).toHaveLength(1);
        expect(swe[0].payload?.status).toBe('processed');
    });

    it('Test 3: customer.subscription.created upserts full active row', async () => {
        const event: StripeEventFixture = {
            id: 'evt_sub_created_1',
            type: 'customer.subscription.created',
            data: { object: subscriptionObject() },
        };
        constructEventMock.mockReturnValue(event);

        const { POST } = await loadRoute();
        const res = await POST(
            buildRequest(JSON.stringify(event), { 'stripe-signature': 'sig' }),
        );

        expect(res.status).toBe(200);

        const subsUpsert = writes.find(
            (w) => w.table === 'subscriptions' && w.op === 'upsert',
        );
        expect(subsUpsert).toBeDefined();
        expect(subsUpsert!.payload).toMatchObject({
            user_id: USER_ID,
            is_active: true,
            tier: 'solopreneur',
            will_renew: true,
            price_id: PRICE_ID,
        });
    });

    it('Test 4: duplicate event.id short-circuits second delivery', async () => {
        const event: StripeEventFixture = {
            id: 'evt_dup_1',
            type: 'customer.subscription.updated',
            data: { object: subscriptionObject() },
        };
        constructEventMock.mockReturnValue(event);

        const { POST } = await loadRoute();

        // First delivery: handler processes normally.
        const res1 = await POST(
            buildRequest(JSON.stringify(event), { 'stripe-signature': 'sig' }),
        );
        expect(res1.status).toBe(200);
        const firstRunWriteCount = writes.length;

        // Simulate the row now being in the ledger with status='processed'.
        setControlled('stripe_webhook_events.select.evt_dup_1', {
            event_id: 'evt_dup_1',
            status: 'processed',
        });

        // Second delivery: must short-circuit.
        const res2 = await POST(
            buildRequest(JSON.stringify(event), { 'stripe-signature': 'sig' }),
        );
        expect(res2.status).toBe(200);
        const body2 = await res2.json();
        expect(body2).toMatchObject({ received: true, duplicate: true });

        // Only the SELECT on stripe_webhook_events should have happened on
        // the second run — no upserts to subscriptions or ledger.
        const secondRunWrites = writes.slice(firstRunWriteCount);
        const writeOps = secondRunWrites.filter((w) => w.op !== 'select');
        expect(writeOps).toHaveLength(0);
    });

    it('Test 5: invoice.payment_failed sets billing_issue_at', async () => {
        const event: StripeEventFixture = {
            id: 'evt_pay_failed_1',
            type: 'invoice.payment_failed',
            data: { object: invoiceObject() },
        };
        constructEventMock.mockReturnValue(event);
        subscriptionsRetrieveMock.mockResolvedValue(subscriptionObject());

        const { POST } = await loadRoute();
        const res = await POST(
            buildRequest(JSON.stringify(event), { 'stripe-signature': 'sig' }),
        );

        expect(res.status).toBe(200);
        const update = writes.find(
            (w) => w.table === 'subscriptions' && w.op === 'update',
        );
        expect(update).toBeDefined();
        expect(update!.payload?.billing_issue_at).toBeTruthy();
    });

    it('Test 6: invoice.payment_succeeded clears billing_issue_at after past_due', async () => {
        const event: StripeEventFixture = {
            id: 'evt_pay_ok_1',
            type: 'invoice.payment_succeeded',
            data: { object: invoiceObject() },
        };
        constructEventMock.mockReturnValue(event);
        subscriptionsRetrieveMock.mockResolvedValue(subscriptionObject());

        const { POST } = await loadRoute();
        const res = await POST(
            buildRequest(JSON.stringify(event), { 'stripe-signature': 'sig' }),
        );

        expect(res.status).toBe(200);
        const update = writes.find(
            (w) => w.table === 'subscriptions' && w.op === 'update',
        );
        expect(update).toBeDefined();
        expect(update!.payload?.billing_issue_at).toBeNull();
    });

    it('Test 7: unknown event type is recorded as status=skipped', async () => {
        const event: StripeEventFixture = {
            id: 'evt_unknown_1',
            type: 'customer.discount.created',
            data: { object: {} },
        };
        constructEventMock.mockReturnValue(event);

        const { POST } = await loadRoute();
        const res = await POST(
            buildRequest(JSON.stringify(event), { 'stripe-signature': 'sig' }),
        );

        expect(res.status).toBe(200);
        const body = await res.json();
        expect(body).toMatchObject({ received: true, handled: false });

        // No subscriptions writes at all.
        expect(writes.filter((w) => w.table === 'subscriptions')).toHaveLength(0);

        // stripe_webhook_events upsert with status='skipped'.
        const swe = writes.find(
            (w) => w.table === 'stripe_webhook_events' && w.op === 'upsert',
        );
        expect(swe).toBeDefined();
        expect(swe!.payload?.status).toBe('skipped');
    });

    it('Test 8: handler error records status=error and returns 500', async () => {
        const event: StripeEventFixture = {
            id: 'evt_boom_1',
            type: 'customer.subscription.updated',
            data: { object: subscriptionObject() },
        };
        constructEventMock.mockReturnValue(event);
        setControlled('subscriptions.upsert.error', {
            message: 'db blew up',
        });

        const { POST } = await loadRoute();
        const res = await POST(
            buildRequest(JSON.stringify(event), { 'stripe-signature': 'sig' }),
        );

        expect(res.status).toBe(500);
        const swe = writes.find(
            (w) => w.table === 'stripe_webhook_events' && w.op === 'upsert',
        );
        expect(swe).toBeDefined();
        expect(swe!.payload?.status).toBe('error');
        expect(swe!.payload?.error_message).toBeTruthy();
    });

    it('Test 9: BILL-01 regression — late checkout.session.completed cannot regress subscription state', async () => {
        const { POST } = await loadRoute();

        // Step A: customer.subscription.created — row becomes active, will_renew=true.
        const eventA: StripeEventFixture = {
            id: 'evt_A_created',
            type: 'customer.subscription.created',
            data: { object: subscriptionObject() },
        };
        constructEventMock.mockReturnValue(eventA);
        await POST(buildRequest(JSON.stringify(eventA), { 'stripe-signature': 'sig' }));

        const writeA = writes.findLast(
            (w) => w.table === 'subscriptions' && w.op === 'upsert',
        );
        expect(writeA).toBeDefined();
        expect(writeA!.payload?.will_renew).toBe(true);
        expect(writeA!.payload?.tier).toBe('solopreneur');

        // Step B: customer.subscription.updated with cancel_at_period_end=true.
        const eventB: StripeEventFixture = {
            id: 'evt_B_updated',
            type: 'customer.subscription.updated',
            data: {
                object: subscriptionObject({ cancel_at_period_end: true }),
            },
        };
        constructEventMock.mockReturnValue(eventB);
        await POST(buildRequest(JSON.stringify(eventB), { 'stripe-signature': 'sig' }));

        const writeB = writes.findLast(
            (w) => w.table === 'subscriptions' && w.op === 'upsert',
        );
        expect(writeB).toBeDefined();
        expect(writeB!.payload?.will_renew).toBe(false);

        // Snapshot the write index BEFORE the late checkout event.
        const writeCountBeforeC = writes.length;

        // Step C: LATE checkout.session.completed (different event_id, same customer/sub).
        // In the legacy handler this would overwrite tier/will_renew/etc.
        // In the hardened handler this must ONLY touch stripe_customer_id.
        const eventC: StripeEventFixture = {
            id: 'evt_C_checkout_late',
            type: 'checkout.session.completed',
            data: { object: checkoutSessionObject() },
        };
        constructEventMock.mockReturnValue(eventC);
        subscriptionsRetrieveMock.mockResolvedValue(
            subscriptionObject({ cancel_at_period_end: false }), // the "stale" state
        );
        const resC = await POST(
            buildRequest(JSON.stringify(eventC), { 'stripe-signature': 'sig' }),
        );
        expect(resC.status).toBe(200);

        // Assert: any subscriptions writes made during step C touched ONLY
        // stripe_customer_id — NO tier/is_active/will_renew/period/price_id.
        const writesC = writes.slice(writeCountBeforeC);
        const subsWritesC = writesC.filter((w) => w.table === 'subscriptions');

        const forbiddenKeys = [
            'tier',
            'is_active',
            'will_renew',
            'price_id',
            'current_period_start',
            'current_period_end',
            'stripe_subscription_id',
            'period_type',
        ];

        for (const w of subsWritesC) {
            const keys = Object.keys(w.payload ?? {});
            for (const forbidden of forbiddenKeys) {
                expect(
                    keys.includes(forbidden),
                    `BILL-01 regression: checkout.session.completed wrote forbidden key ${forbidden}`,
                ).toBe(false);
            }
        }

        // And the authoritative state (from step B) must still be will_renew=false.
        // Since our mock is stateless we verify this indirectly by asserting that
        // step C never wrote will_renew=true — which the loop above already did.
    });
});
