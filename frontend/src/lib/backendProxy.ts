// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// Shared helper for Next.js API routes that proxy to the Cloud Run backend
// fronted by Cloudflare. Cloudflare's managed challenge fires on
// server-to-server fetches (the Vercel function can't solve a JS challenge),
// so we send a shared secret header that a CF WAF skip rule on the
// api.pikar-ai.com zone recognizes and bypasses for. Without this header,
// uploads and other server-side proxy calls hit a CF interstitial and the
// browser receives challenge HTML in place of the expected JSON response.

const PROXY_SECRET_HEADER = 'X-Pikar-Proxy-Secret';

// Drop-in replacement for fetch() — injects the proxy secret when set.
// Falls through to plain fetch when PIKAR_PROXY_SECRET is missing so the
// helper can be deployed before the env var is configured (same broken
// behavior as today, no worse).
export function backendFetch(
    url: string | URL,
    init: RequestInit = {},
): Promise<Response> {
    const secret = process.env.PIKAR_PROXY_SECRET;
    if (!secret) return fetch(url, init);

    const headers = new Headers(init.headers ?? {});
    if (!headers.has(PROXY_SECRET_HEADER)) {
        headers.set(PROXY_SECRET_HEADER, secret);
    }
    return fetch(url, { ...init, headers });
}
