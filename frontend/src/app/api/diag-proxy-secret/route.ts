// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// TEMPORARY diagnostic for Cloudflare proxy-secret debugging.
// REMOVE THIS FILE after the issue is confirmed fixed.

import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/backendProxy';

export async function GET() {
    const raw = process.env.PIKAR_PROXY_SECRET;
    const backendUrl = process.env.BACKEND_URL || 'https://api.pikar-ai.com';

    let probeStatus: number | string = 'not run';
    let probeServer = '';
    let probeBodyHead = '';
    let probeError: string | null = null;
    try {
        const r = await backendFetch(`${backendUrl}/upload/smart`, {
            method: 'POST',
            headers: { Authorization: 'Bearer diag-fake-token' },
            body: 'diag-probe',
        });
        probeStatus = r.status;
        probeServer = r.headers.get('server') ?? '';
        probeBodyHead = (await r.text()).substring(0, 120);
    } catch (e) {
        probeError = e instanceof Error ? e.message : String(e);
    }

    return NextResponse.json({
        env: {
            present: typeof raw === 'string',
            length: raw?.length ?? 0,
            head: raw ? raw.substring(0, 4) : null,
            tail: raw ? raw.substring(raw.length - 4) : null,
            backendUrl,
        },
        probe: {
            status: probeStatus,
            server: probeServer,
            bodyHead: probeBodyHead,
            error: probeError,
        },
    });
}
