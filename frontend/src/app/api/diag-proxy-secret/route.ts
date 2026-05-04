// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// TEMPORARY diagnostic for the Cloudflare proxy-secret debugging.
// REMOVE THIS FILE after the issue is confirmed fixed. Returns
// non-secret metadata only — length, presence, env name — never the value.

import { NextResponse } from 'next/server';

export async function GET() {
    const raw = process.env.PIKAR_PROXY_SECRET;
    return NextResponse.json({
        present: typeof raw === 'string',
        length: raw?.length ?? 0,
        head: raw ? raw.substring(0, 4) : null,
        tail: raw ? raw.substring(raw.length - 4) : null,
        nodeEnv: process.env.NODE_ENV,
        vercelEnv: process.env.VERCEL_ENV,
        deploymentId: process.env.VERCEL_DEPLOYMENT_ID,
    });
}
