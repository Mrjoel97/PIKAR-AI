// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

// Shared helper for Next.js API routes that proxy to the Cloud Run backend
// fronted by Cloudflare. There are two distinct problems server-side fetches
// have to deal with that browser-side fetches don't:
//
// 1. Cloudflare Bot Fight Mode (Free) flags Vercel's Node.js fetch
//    (`User-Agent: node`, AWS-egress IP, no cookies) as a bot at a phase
//    that runs BEFORE the WAF custom-rules phase. Result: 403 + JS-challenge
//    HTML in the response body, regardless of any "skip" rule we add. The
//    only reliable workaround is to skip CF entirely for these calls and
//    talk to the Cloud Run direct URL.
// 2. The shared secret header (X-Pikar-Proxy-Secret) is kept as
//    defense-in-depth — if a route is misconfigured to hit the CF-fronted
//    URL despite the rewrite below, the CF skip rule on the api.pikar-ai.com
//    zone will (best-effort) skip the post-custom-rules products.
//
// `BACKEND_PUBLIC_HOST` is the CF-fronted hostname browsers must use (so
// the Authorization cookie scope, CORS origin, and OAuth redirect URLs all
// continue to work). `CLOUD_RUN_DIRECT_URL` is the .run.app origin the
// server-side fetch should actually hit. When both are set and the URL
// passed in starts with the public host, we rewrite to the direct origin
// at fetch time. This means routes don't have to know which env var to
// prefer — `backendFetch` handles it.

const PROXY_SECRET_HEADER = 'X-Pikar-Proxy-Secret';

function rewriteToDirect(url: string | URL): string | URL {
    const publicHost = process.env.BACKEND_PUBLIC_HOST;
    const directOrigin = process.env.CLOUD_RUN_DIRECT_URL;
    if (!publicHost || !directOrigin) return url;

    const asString = typeof url === 'string' ? url : url.toString();
    // Match exact host. Trim trailing slash on directOrigin to avoid
    // double-slashed paths after substitution.
    const trimmedDirect = directOrigin.replace(/\/+$/, '');
    const trimmedPublic = publicHost.replace(/\/+$/, '');
    if (asString.startsWith(`${trimmedPublic}/`) || asString === trimmedPublic) {
        return asString.replace(trimmedPublic, trimmedDirect);
    }
    return url;
}

// Drop-in replacement for fetch() for Next.js API routes that proxy to the
// Cloud Run backend. Two transparent behaviors:
//   • Rewrites api.pikar-ai.com → Cloud Run direct URL (skips CF entirely)
//   • Injects X-Pikar-Proxy-Secret header for any residual CF-fronted calls
// Both are no-ops when the corresponding env vars are unset, so this helper
// is safe to deploy before the env vars are configured.
export function backendFetch(
    url: string | URL,
    init: RequestInit = {},
): Promise<Response> {
    const targetUrl = rewriteToDirect(url);
    const secret = process.env.PIKAR_PROXY_SECRET;
    if (!secret) return fetch(targetUrl, init);

    const headers = new Headers(init.headers ?? {});
    if (!headers.has(PROXY_SECRET_HEADER)) {
        headers.set(PROXY_SECRET_HEADER, secret);
    }
    return fetch(targetUrl, { ...init, headers });
}
