// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Server-side Stripe client.
 *
 * Used in API routes (checkout session creation, portal, webhook verification).
 * NEVER import this from client components — it uses the secret key.
 */

import Stripe from 'stripe';

let _stripe: Stripe | null = null;

export function getStripe(): Stripe {
    if (_stripe) return _stripe;

    const secretKey = process.env.STRIPE_SECRET_KEY;
    if (!secretKey) {
        throw new Error(
            'STRIPE_SECRET_KEY is not set. Add it to your environment variables.',
        );
    }

    _stripe = new Stripe(secretKey, {
        typescript: true,
    });

    return _stripe;
}
