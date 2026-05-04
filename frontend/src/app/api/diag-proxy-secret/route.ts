// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// TEMPORARY diagnostic for Cloudflare proxy-secret debugging.
// REMOVE THIS FILE after the issue is confirmed fixed.

import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/backendProxy';

interface ProbeResult {
    status: number | string;
    server?: string;
    bodyHead?: string;
    headersEchoed?: Record<string, string> | null;
    error?: string | null;
}

export async function GET() {
    const raw = process.env.PIKAR_PROXY_SECRET;
    const backendUrl = process.env.BACKEND_URL || 'https://api.pikar-ai.com';

    // Probe 1: hit the actual backend (where it's failing)
    const backend: ProbeResult = { status: 'not run' };
    try {
        const r = await backendFetch(`${backendUrl}/upload/smart`, {
            method: 'POST',
            headers: { Authorization: 'Bearer diag-fake-token' },
            body: 'diag-probe',
        });
        backend.status = r.status;
        backend.server = r.headers.get('server') ?? '';
        backend.bodyHead = (await r.text()).substring(0, 120);
    } catch (e) {
        backend.error = e instanceof Error ? e.message : String(e);
    }

    // Probe 2: hit httpbin.org (echoes received request headers) to verify
    // the Vercel function is REALLY sending the X-Pikar-Proxy-Secret header
    // — that confirms whether the env-var injection works regardless of CF.
    const echo: ProbeResult = { status: 'not run' };
    try {
        const r = await backendFetch('https://httpbin.org/headers', {
            method: 'GET',
            headers: { 'X-Diag-Source': 'vercel-diag' },
        });
        echo.status = r.status;
        const data = await r.json();
        const recvd = (data?.headers ?? {}) as Record<string, string>;
        // Only echo back proxy-secret-related headers (keep others private)
        const secretHeader = recvd['X-Pikar-Proxy-Secret'] ?? recvd['x-pikar-proxy-secret'] ?? '';
        echo.headersEchoed = {
            'X-Pikar-Proxy-Secret_present': String(Boolean(secretHeader)),
            'X-Pikar-Proxy-Secret_length': String(secretHeader.length),
            'X-Pikar-Proxy-Secret_head': secretHeader.substring(0, 4),
            'X-Pikar-Proxy-Secret_tail': secretHeader.substring(Math.max(0, secretHeader.length - 4)),
            'User-Agent': recvd['User-Agent'] ?? '',
            'X-Diag-Source': recvd['X-Diag-Source'] ?? '',
            'Authorization_present': String(Boolean(recvd['Authorization'])),
        };
    } catch (e) {
        echo.error = e instanceof Error ? e.message : String(e);
    }

    return NextResponse.json({
        env: {
            present: typeof raw === 'string',
            length: raw?.length ?? 0,
            head: raw ? raw.substring(0, 4) : null,
            tail: raw ? raw.substring(raw.length - 4) : null,
            backendUrl,
        },
        backend,
        echo,
    });
}
