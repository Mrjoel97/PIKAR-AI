// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Client-side Stripe.js loader (singleton).
 *
 * Used if we ever need Stripe Elements on the client.
 * For now, we use Stripe-hosted Checkout (redirect), so this
 * is here as a convenience for future embedded checkout.
 */

import { loadStripe, type Stripe } from '@stripe/stripe-js';

let stripePromise: Promise<Stripe | null> | null = null;

export function getStripeClient(): Promise<Stripe | null> {
    if (!stripePromise) {
        const key = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;
        if (!key) {
            console.warn('NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY is not set');
            return Promise.resolve(null);
        }
        stripePromise = loadStripe(key);
    }
    return stripePromise;
}
