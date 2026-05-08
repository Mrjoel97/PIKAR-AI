# Vault fixes and agent actions — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore Vault image thumbnails and the Chat History page (both broken by browser-side Supabase JWT issues), then add multi-select on Vault assets with agent action chips that prefill the chat composer.

**Architecture:** Same fix pattern that `bf317b3e` already applied to row queries — move work that needs an authenticated Supabase session to Next.js server routes (which read cookies correctly via `@supabase/ssr`). Then add a thin selection layer on top of the existing `VaultInterface` that hands selected assets to the workspace chat via `sessionStorage` prefill.

**Tech Stack:** Next.js 16 App Router (route handlers in `frontend/src/app/api/`), `@supabase/ssr` server client, Vitest, React 19 / Tailwind 4, Framer Motion (already used in `VaultInterface`).

**Spec:** `docs/superpowers/specs/2026-05-08-vault-fixes-and-agent-actions-design.md`

---

## File structure

**PR 1 — Regression fixes:**
- `frontend/src/app/api/vault/sign-urls/route.ts` (new) — POST route that signs storage URLs server-side
- `frontend/src/app/api/sessions/list/route.ts` (new) — GET route that proxies to backend `/sessions` with the cookie JWT
- `frontend/src/components/vault/VaultInterface.tsx` (edit) — call the new sign-urls route instead of `supabase.storage.createSignedUrls`
- `frontend/src/services/sessions.ts` (edit) — call the new sessions route + add transient retry
- `frontend/src/contexts/SessionControlContext.tsx` (edit) — surface `refreshSessions` error in context value
- `frontend/src/app/dashboard/history/page.tsx` (edit) — render an inline retry banner when refresh fails
- `frontend/src/__tests__/api/vault-sign-urls.test.ts` (new)
- `frontend/src/__tests__/api/sessions-list.test.ts` (new)
- `frontend/src/__tests__/services/sessions.retry.test.ts` (new)

**PR 2 — Vault selection + agent actions:**
- `frontend/src/lib/vaultActions.ts` (new) — prompt templates + asset shape helpers
- `frontend/src/lib/vaultPrefill.ts` (new) — sessionStorage helpers + session-id generator
- `frontend/src/components/vault/VaultActionBar.tsx` (new) — sticky bottom bar with chips
- `frontend/src/components/vault/VaultInterface.tsx` (edit) — selection state, action bar mount, checkbox prop drilling
- `frontend/src/components/chat/ChatInterface.tsx` (edit) — read prefill from sessionStorage on mount
- `frontend/src/__tests__/lib/vaultActions.test.ts` (new)
- `frontend/src/__tests__/lib/vaultPrefill.test.ts` (new)
- `frontend/src/__tests__/components/VaultActionBar.test.tsx` (new)

---

## PR 1 — Regression fixes

### Task 1: Server route `/api/vault/sign-urls`

**Files:**
- Create: `frontend/src/app/api/vault/sign-urls/route.ts`
- Test: `frontend/src/__tests__/api/vault-sign-urls.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/__tests__/api/vault-sign-urls.test.ts`:

```typescript
/**
 * @vitest-environment node
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

const getUserMock = vi.fn()
const createSignedUrlsMock = vi.fn()
const fromMock = vi.fn(() => ({ createSignedUrls: createSignedUrlsMock }))

vi.mock('@/lib/supabase/server', () => ({
    createClient: vi.fn(async () => ({
        auth: { getUser: getUserMock },
        storage: { from: fromMock },
    })),
}))

describe('POST /api/vault/sign-urls', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    afterEach(() => {
        vi.resetModules()
    })

    it('returns signed URLs for the given paths in the requested bucket', async () => {
        getUserMock.mockResolvedValue({ data: { user: { id: 'user-1' } } })
        createSignedUrlsMock.mockResolvedValue({
            data: [
                { path: 'user-1/a.png', signedUrl: 'https://x/signed/a', error: null },
                { path: 'user-1/b.jpg', signedUrl: 'https://x/signed/b', error: null },
            ],
            error: null,
        })

        const { POST } = await import('@/app/api/vault/sign-urls/route')
        const req = new Request('http://localhost/api/vault/sign-urls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bucket: 'media-assets', paths: ['user-1/a.png', 'user-1/b.jpg'] }),
        })
        const res = await POST(req as never)
        const body = await res.json()

        expect(res.status).toBe(200)
        expect(fromMock).toHaveBeenCalledWith('media-assets')
        expect(createSignedUrlsMock).toHaveBeenCalledWith(['user-1/a.png', 'user-1/b.jpg'], 3600)
        expect(body.items).toEqual([
            { path: 'user-1/a.png', signedUrl: 'https://x/signed/a' },
            { path: 'user-1/b.jpg', signedUrl: 'https://x/signed/b' },
        ])
    })

    it('rejects unauthenticated requests with 401', async () => {
        getUserMock.mockResolvedValue({ data: { user: null } })

        const { POST } = await import('@/app/api/vault/sign-urls/route')
        const req = new Request('http://localhost/api/vault/sign-urls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bucket: 'media-assets', paths: ['x'] }),
        })
        const res = await POST(req as never)
        expect(res.status).toBe(401)
        expect(createSignedUrlsMock).not.toHaveBeenCalled()
    })

    it('rejects malformed bodies with 400', async () => {
        getUserMock.mockResolvedValue({ data: { user: { id: 'u' } } })

        const { POST } = await import('@/app/api/vault/sign-urls/route')
        const req = new Request('http://localhost/api/vault/sign-urls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bucket: 'media-assets' }), // no paths
        })
        const res = await POST(req as never)
        expect(res.status).toBe(400)
        expect(createSignedUrlsMock).not.toHaveBeenCalled()
    })

    it('caps paths at 200 to avoid runaway requests', async () => {
        getUserMock.mockResolvedValue({ data: { user: { id: 'u' } } })

        const { POST } = await import('@/app/api/vault/sign-urls/route')
        const paths = Array.from({ length: 250 }, (_, i) => `p/${i}`)
        const req = new Request('http://localhost/api/vault/sign-urls', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bucket: 'media-assets', paths }),
        })
        const res = await POST(req as never)
        expect(res.status).toBe(400)
    })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- src/__tests__/api/vault-sign-urls.test.ts`
Expected: FAIL — module `@/app/api/vault/sign-urls/route` not found.

- [ ] **Step 3: Write the route**

Create `frontend/src/app/api/vault/sign-urls/route.ts`:

```typescript
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Server-side signing for Vault storage previews.
 *
 * The browser-side Supabase client doesn't reliably materialise a JWT from
 * the SSR cookies, so `supabase.storage.from(bucket).createSignedUrls` from
 * the browser silently returned no URLs and image cards collapsed to the
 * file-icon fallback. Same root cause as /api/vault/list (bf317b3e).
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

const SIGNED_URL_TTL_SECONDS = 3600
const MAX_PATHS_PER_REQUEST = 200

interface SignUrlsBody {
    bucket?: unknown
    paths?: unknown
}

export async function POST(request: NextRequest) {
    let body: SignUrlsBody
    try {
        body = (await request.json()) as SignUrlsBody
    } catch {
        return NextResponse.json({ error: 'invalid json' }, { status: 400 })
    }

    if (typeof body.bucket !== 'string' || !body.bucket) {
        return NextResponse.json({ error: 'bucket is required' }, { status: 400 })
    }
    if (!Array.isArray(body.paths) || body.paths.length === 0) {
        return NextResponse.json({ error: 'paths must be a non-empty array' }, { status: 400 })
    }
    if (body.paths.length > MAX_PATHS_PER_REQUEST) {
        return NextResponse.json(
            { error: `paths exceeds max ${MAX_PATHS_PER_REQUEST}` },
            { status: 400 },
        )
    }
    if (!body.paths.every((p) => typeof p === 'string' && p.length > 0)) {
        return NextResponse.json({ error: 'paths must be non-empty strings' }, { status: 400 })
    }

    const bucket = body.bucket
    const paths = body.paths as string[]

    try {
        const supabase = await createClient()
        const {
            data: { user },
        } = await supabase.auth.getUser()
        if (!user) {
            return NextResponse.json({ error: 'unauthenticated' }, { status: 401 })
        }

        const { data, error } = await supabase.storage
            .from(bucket)
            .createSignedUrls(paths, SIGNED_URL_TTL_SECONDS)

        if (error) {
            console.error('[api/vault/sign-urls] failed:', error.message)
            return NextResponse.json({ items: [], error: error.message }, { status: 500 })
        }

        const items = (data ?? []).map((row) => ({
            path: row.path,
            signedUrl: row.signedUrl,
        }))

        return NextResponse.json({ items })
    } catch (err) {
        console.error('[api/vault/sign-urls] threw:', err)
        return NextResponse.json({ error: 'internal' }, { status: 500 })
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- src/__tests__/api/vault-sign-urls.test.ts`
Expected: PASS, all four cases.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/api/vault/sign-urls/route.ts frontend/src/__tests__/api/vault-sign-urls.test.ts
git commit -m "feat(vault): server-side sign-urls route for storage previews"
```

---

### Task 2: Wire `VaultInterface` to use the new route

**Files:**
- Modify: `frontend/src/components/vault/VaultInterface.tsx` around line 909–964 (the `needsPreviewDocs` / `createSignedUrls` block)

- [ ] **Step 1: Open the file and locate the block**

Read `frontend/src/components/vault/VaultInterface.tsx:903-964` to confirm the block. The current code maps each bucket to a list of paths, calls `supabase.storage.from(bucket).createSignedUrls(paths, 3600)` from the browser client, and folds the results into `signedUrlMap`.

- [ ] **Step 2: Replace the browser signing call**

Replace lines 926–948 (the `Promise.all` block that calls `createSignedUrls`) with a `fetch('/api/vault/sign-urls', ...)` per bucket. Final shape of the replacement:

```typescript
const signedUrlEntries = await Promise.all(
    Array.from(pathsByBucket.entries()).map(async ([bucket, paths]) => {
        try {
            const resp = await withTimeout(
                fetch('/api/vault/sign-urls', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ bucket, paths }),
                }),
                VAULT_SIGN_TIMEOUT_MS,
                `Signed URL generation timed out for ${bucket}`,
            );
            if (!resp.ok) {
                console.warn('[Vault] /api/vault/sign-urls failed:', bucket, resp.status);
                return [] as Array<{ path: string; signedUrl: string | null; bucket: string }>;
            }
            const body = (await resp.json()) as {
                items?: Array<{ path: string; signedUrl: string | null }>;
            };
            return (body.items ?? []).map((item) => ({ ...item, bucket }));
        } catch (error) {
            console.warn('[Vault] Failed to create preview URLs for bucket:', bucket, error);
            return [] as Array<{ path: string; signedUrl: string | null; bucket: string }>;
        }
    }),
);

const signedUrlMap = new Map<string, string>();
signedUrlEntries.flat().forEach((signedUrl) => {
    if (signedUrl.path && signedUrl.signedUrl) {
        signedUrlMap.set(`${signedUrl.bucket}:${signedUrl.path}`, signedUrl.signedUrl);
    }
});
```

The downstream `docs.map(...)` block that reads `signedUrlMap.get(...)` stays unchanged.

- [ ] **Step 3: Remove now-unused imports**

If `SignedStorageUrl` type from the supabase-js package was imported only for this block, remove it. Verify by grepping:

```bash
grep -n "SignedStorageUrl" frontend/src/components/vault/VaultInterface.tsx
```

If only the (now-removed) usages remain, drop the import line.

- [ ] **Step 4: Manual smoke test**

Run: `cd frontend && npm run dev`
- Navigate to `/dashboard/vault` → Images tab.
- Confirm thumbnails render for uploaded images.
- Open the Network tab, confirm a `POST /api/vault/sign-urls` request returning 200.

- [ ] **Step 5: Lint + typecheck**

Run: `cd frontend && npm run lint`
Expected: clean (no new warnings introduced).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/vault/VaultInterface.tsx
git commit -m "fix(vault): route storage URL signing through server-side API"
```

---

### Task 3: Server route `/api/sessions/list`

**Files:**
- Create: `frontend/src/app/api/sessions/list/route.ts`
- Test: `frontend/src/__tests__/api/sessions-list.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/__tests__/api/sessions-list.test.ts`:

```typescript
/**
 * @vitest-environment node
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

const getUserMock = vi.fn()
const getSessionMock = vi.fn()

const makeJwt = (sub: string) => {
    const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url')
    const payload = Buffer.from(JSON.stringify({ sub, exp: 4070908800 })).toString('base64url')
    return `${header}.${payload}.signature`
}

vi.mock('@/lib/supabase/server', () => ({
    createClient: vi.fn(async () => ({
        auth: { getUser: getUserMock, getSession: getSessionMock },
    })),
}))

describe('GET /api/sessions/list', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        process.env.BACKEND_URL = 'http://backend.test'
    })

    afterEach(() => {
        vi.unstubAllGlobals()
        vi.resetModules()
        delete process.env.BACKEND_URL
    })

    it('forwards the cookie JWT to the backend and returns the response', async () => {
        getUserMock.mockResolvedValue({ data: { user: { id: 'u' } } })
        getSessionMock.mockResolvedValue({
            data: { session: { access_token: makeJwt('u') } },
            error: null,
        })
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            json: async () => ({ sessions: [{ id: 's1', title: 'Hi', created_at: 'x', updated_at: 'y' }], count: 1 }),
        })
        vi.stubGlobal('fetch', fetchMock)

        const { GET } = await import('@/app/api/sessions/list/route')
        const req = new Request('http://localhost/api/sessions/list?limit=25')
        const res = await GET(req as never)
        const body = await res.json()

        expect(res.status).toBe(200)
        expect(body.count).toBe(1)
        const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
        expect(url).toBe('http://backend.test/sessions?limit=25')
        const headers = new Headers(init.headers)
        expect(headers.get('Authorization')).toBe(`Bearer ${makeJwt('u')}`)
    })

    it('returns 401 when no authenticated user', async () => {
        getUserMock.mockResolvedValue({ data: { user: null } })
        getSessionMock.mockResolvedValue({ data: { session: null }, error: null })
        const fetchMock = vi.fn()
        vi.stubGlobal('fetch', fetchMock)

        const { GET } = await import('@/app/api/sessions/list/route')
        const req = new Request('http://localhost/api/sessions/list')
        const res = await GET(req as never)
        expect(res.status).toBe(401)
        expect(fetchMock).not.toHaveBeenCalled()
    })

    it('passes through backend 5xx as 502 so the client can retry', async () => {
        getUserMock.mockResolvedValue({ data: { user: { id: 'u' } } })
        getSessionMock.mockResolvedValue({
            data: { session: { access_token: makeJwt('u') } },
            error: null,
        })
        const fetchMock = vi.fn().mockResolvedValue({
            ok: false,
            status: 503,
            json: async () => ({}),
            text: async () => 'unavailable',
        })
        vi.stubGlobal('fetch', fetchMock)

        const { GET } = await import('@/app/api/sessions/list/route')
        const res = await GET(new Request('http://localhost/api/sessions/list') as never)
        expect(res.status).toBe(502)
    })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- src/__tests__/api/sessions-list.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the route**

Create `frontend/src/app/api/sessions/list/route.ts`:

```typescript
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Server-side proxy for GET /sessions on the Pikar backend.
 *
 * The page used to call the backend directly from the browser using a
 * client-resolved access token. On hard reload there is a brief window
 * where the cookie token is unavailable and the call fails; the silent
 * catch in SessionControlContext then painted an empty Chat History
 * page. This route uses the SSR Supabase client to read the cookie JWT
 * authoritatively, so the auth race is gone.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
    const limitParam = request.nextUrl.searchParams.get('limit') ?? '50'
    const limit = Math.min(Math.max(parseInt(limitParam, 10) || 50, 1), 100)

    try {
        const supabase = await createClient()
        const [{ data: userData }, { data: sessionData }] = await Promise.all([
            supabase.auth.getUser(),
            supabase.auth.getSession(),
        ])
        if (!userData.user) {
            return NextResponse.json({ error: 'unauthenticated' }, { status: 401 })
        }
        const accessToken = sessionData.session?.access_token
        if (!accessToken) {
            return NextResponse.json({ error: 'no access token' }, { status: 401 })
        }

        const url = `${BACKEND_URL}/sessions?limit=${limit}`
        const upstream = await fetch(url, {
            headers: { Authorization: `Bearer ${accessToken}` },
            cache: 'no-store',
        })

        if (!upstream.ok) {
            const isUpstreamFailure = upstream.status >= 500
            console.error('[api/sessions/list] backend returned', upstream.status)
            return NextResponse.json(
                { error: 'upstream_error', upstream_status: upstream.status },
                { status: isUpstreamFailure ? 502 : upstream.status },
            )
        }

        const body = await upstream.json()
        return NextResponse.json(body)
    } catch (err) {
        console.error('[api/sessions/list] threw:', err)
        return NextResponse.json({ error: 'internal' }, { status: 500 })
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- src/__tests__/api/sessions-list.test.ts`
Expected: PASS, all three cases.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/api/sessions/list/route.ts frontend/src/__tests__/api/sessions-list.test.ts
git commit -m "feat(sessions): server-side proxy for backend /sessions"
```

---

### Task 4: Repoint `listUserSessions` and add transient retry

**Files:**
- Modify: `frontend/src/services/sessions.ts`
- Test: `frontend/src/__tests__/services/sessions.retry.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/__tests__/services/sessions.retry.test.ts`:

```typescript
/**
 * @vitest-environment node
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

describe('listUserSessions retry behaviour', () => {
    beforeEach(() => {
        vi.resetModules()
    })

    afterEach(() => {
        vi.unstubAllGlobals()
        vi.useRealTimers()
    })

    it('hits /api/sessions/list and returns the parsed body', async () => {
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            json: async () => ({ sessions: [{ id: 's1' }], count: 1 }),
        })
        vi.stubGlobal('fetch', fetchMock)

        const { listUserSessions } = await import('@/services/sessions')
        const result = await listUserSessions(25)

        expect(result.count).toBe(1)
        expect(fetchMock).toHaveBeenCalledTimes(1)
        const [url] = fetchMock.mock.calls[0] as [string]
        expect(url).toBe('/api/sessions/list?limit=25')
    })

    it('retries once on a 5xx response and succeeds on the second try', async () => {
        const fetchMock = vi.fn()
            .mockResolvedValueOnce({ ok: false, status: 502, json: async () => ({}) })
            .mockResolvedValueOnce({
                ok: true,
                status: 200,
                json: async () => ({ sessions: [], count: 0 }),
            })
        vi.stubGlobal('fetch', fetchMock)

        const { listUserSessions } = await import('@/services/sessions')
        const result = await listUserSessions()

        expect(result.count).toBe(0)
        expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('does NOT retry on 4xx', async () => {
        const fetchMock = vi.fn().mockResolvedValue({
            ok: false,
            status: 401,
            json: async () => ({ error: 'unauthenticated' }),
        })
        vi.stubGlobal('fetch', fetchMock)

        const { listUserSessions } = await import('@/services/sessions')
        await expect(listUserSessions()).rejects.toThrow(/401/)
        expect(fetchMock).toHaveBeenCalledTimes(1)
    })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- src/__tests__/services/sessions.retry.test.ts`
Expected: FAIL — current `listUserSessions` calls `${API_BASE}/sessions` and uses Bearer auth, not the new route.

- [ ] **Step 3: Rewrite `listUserSessions`**

Replace the contents of `frontend/src/services/sessions.ts`:

```typescript
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

export interface SessionSummary {
  id: string;
  title: string;
  preview?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionListResponse {
  sessions: SessionSummary[];
  count: number;
}

const RETRY_DELAY_MS = 500;

async function fetchSessions(limit: number): Promise<Response> {
  return fetch(`/api/sessions/list?limit=${encodeURIComponent(limit)}`, {
    cache: 'no-store',
  });
}

/**
 * Fetch the authenticated user's chat sessions, most recent first.
 *
 * Calls the Next.js server route /api/sessions/list which proxies the
 * backend with the cookie-resolved JWT. We retry once on transient
 * failures (network error, 5xx) but never on 4xx — those are real auth
 * or contract problems the caller should see.
 */
export async function listUserSessions(limit = 50): Promise<SessionListResponse> {
  let lastError: unknown = null;

  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const res = await fetchSessions(limit);
      if (res.ok) {
        return (await res.json()) as SessionListResponse;
      }
      // 5xx is transient — retry once. 4xx is not.
      if (res.status >= 500 && attempt === 0) {
        lastError = new Error(`Failed to load sessions: ${res.status} ${res.statusText}`);
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
        continue;
      }
      throw new Error(`Failed to load sessions: ${res.status} ${res.statusText}`);
    } catch (err) {
      lastError = err;
      // Network-style errors (TypeError from fetch) get one retry.
      if (attempt === 0 && err instanceof TypeError) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
        continue;
      }
      throw err;
    }
  }

  throw lastError instanceof Error ? lastError : new Error('listUserSessions failed');
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- src/__tests__/services/sessions.retry.test.ts`
Expected: PASS, all three cases.

- [ ] **Step 5: Run any existing sessions-related tests to confirm no regression**

Run: `cd frontend && npm test -- src/__tests__/services/`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/services/sessions.ts frontend/src/__tests__/services/sessions.retry.test.ts
git commit -m "fix(sessions): route history fetch through server proxy with retry"
```

---

### Task 5: Surface refresh error in `SessionControlContext` and render retry banner on history page

**Files:**
- Modify: `frontend/src/contexts/SessionControlContext.tsx` (the context value, the `refreshSessions` callback)
- Modify: `frontend/src/contexts/ChatSessionContext.tsx` (re-export the new field)
- Modify: `frontend/src/app/dashboard/history/page.tsx` (render banner on error)

- [ ] **Step 1: Add `refreshError` to `SessionControlContextValue`**

In `frontend/src/contexts/SessionControlContext.tsx`, locate the `SessionControlContextValue` interface (search `interface SessionControlContextValue`). Add:

```typescript
  /** Error from the last `refreshSessions()` call, if any. Cleared on success. */
  refreshError: Error | null
```

- [ ] **Step 2: Track the error in state**

Near the other `useState` calls (around line 178), add:

```typescript
  const [refreshError, setRefreshError] = useState<Error | null>(null)
```

- [ ] **Step 3: Update `refreshSessions` to write `refreshError`**

Inside `refreshSessions` (currently around line 442–470), update the try/catch:

```typescript
  const refreshSessions = useCallback(async (): Promise<void> => {
    if (!userId) return

    try {
      setIsLoadingSessions(true)
      const { sessions: serverSessions } = await listUserSessions()
      const chatSessions: ChatSession[] = serverSessions.map((s) => ({
        id: s.id,
        title:
          s.title && s.title.trim()
            ? s.title
            : extractTitleFromSessionId(s.id),
        preview: s.preview ?? undefined,
        createdAt: s.created_at,
        updatedAt: s.updated_at,
      }))

      setSessions(chatSessions)
      setRefreshError(null)

      if (!initializedRef.current && chatSessions.length > 0) {
        initializedRef.current = true
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err)
      setRefreshError(err instanceof Error ? err : new Error('Failed to load sessions'))
    } finally {
      setIsLoadingSessions(false)
      setSessionsLoaded(true)
    }
  }, [userId, setSessions, setIsLoadingSessions])
```

- [ ] **Step 4: Expose `refreshError` in the provider value**

Locate the `value` / `useMemo` that returns the context value (around line 738–759). Add `refreshError` to it.

- [ ] **Step 5: Re-export through `ChatSessionContext`**

In `frontend/src/contexts/ChatSessionContext.tsx`, find the wrapper that exposes the subset used by chat consumers (around line 67–69). Add:

```typescript
    refreshError: ctrl.refreshError,
```

And update the corresponding `ChatSessionContextValue` interface in the same file to include `refreshError: Error | null`.

- [ ] **Step 6: Render the banner on the history page**

Edit `frontend/src/app/dashboard/history/page.tsx`. Pull `refreshError` from `useChatSession()`:

```typescript
    const {
        sessions,
        isLoadingSessions,
        selectChat,
        deleteChat,
        refreshSessions,
        refreshError,
    } = useChatSession();
```

Then, immediately above the `Empty State` block (around line 252), insert:

```tsx
                        {refreshError && sessions.length === 0 && (
                            <div className="rounded-2xl border border-rose-100 bg-rose-50 p-6 mb-6 flex items-center justify-between">
                                <div>
                                    <p className="text-sm font-semibold text-rose-700">Couldn&apos;t load your history.</p>
                                    <p className="text-xs text-rose-600 mt-1">{refreshError.message}</p>
                                </div>
                                <button
                                    onClick={() => refreshSessions()}
                                    className="rounded-xl bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 transition-colors"
                                >
                                    Retry
                                </button>
                            </div>
                        )}
```

- [ ] **Step 7: Manual smoke test**

Run: `cd frontend && npm run dev`
- Open the Network tab and use a request blocking rule to force `/api/sessions/list` to fail (or stop the backend).
- Reload `/dashboard/history`. Confirm the rose error banner appears with a Retry button.
- Restore the backend, click Retry, confirm sessions populate.

- [ ] **Step 8: Run existing tests to confirm no regression**

Run: `cd frontend && npm test -- src/contexts`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/contexts/SessionControlContext.tsx frontend/src/contexts/ChatSessionContext.tsx frontend/src/app/dashboard/history/page.tsx
git commit -m "fix(history): surface refresh failures with retry banner instead of silent empty"
```

---

## PR 2 — Vault selection + agent actions

### Task 6: Prompt templates module

**Files:**
- Create: `frontend/src/lib/vaultActions.ts`
- Test: `frontend/src/__tests__/lib/vaultActions.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/__tests__/lib/vaultActions.test.ts`:

```typescript
/**
 * @vitest-environment node
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect } from 'vitest'
import { buildVaultActionPrompt, VaultActionItem } from '@/lib/vaultActions'

const items: VaultActionItem[] = [
    { id: 'a1', filename: 'hero.png', file_type: 'image/png', signed_url: 'https://x/a' },
    { id: 'a2', filename: 'demo.mp4', file_type: 'video/mp4', signed_url: 'https://x/b' },
]

describe('buildVaultActionPrompt', () => {
    it('builds a post-to-social prompt that lists every asset with filename and URL', () => {
        const prompt = buildVaultActionPrompt('post_social', items)
        expect(prompt).toContain('post these assets to social')
        expect(prompt.toLowerCase()).toContain('hero.png')
        expect(prompt).toContain('https://x/a')
        expect(prompt).toContain('demo.mp4')
        expect(prompt).toContain('https://x/b')
    })

    it('builds a campaign prompt', () => {
        const prompt = buildVaultActionPrompt('use_campaign', items)
        expect(prompt.toLowerCase()).toContain('marketing campaign')
        expect(prompt).toContain('hero.png')
    })

    it('builds an email prompt', () => {
        const prompt = buildVaultActionPrompt('draft_email', items)
        expect(prompt.toLowerCase()).toContain('email')
        expect(prompt).toContain('demo.mp4')
    })

    it('builds a custom-prompt scaffold with just the assets list', () => {
        const prompt = buildVaultActionPrompt('custom', items)
        expect(prompt).toContain('hero.png')
        expect(prompt).toContain('https://x/a')
        // Custom prompt does not impose an instruction
        expect(prompt.toLowerCase()).not.toContain('post these assets')
        expect(prompt.toLowerCase()).not.toContain('marketing campaign')
    })

    it('throws on unknown action', () => {
        expect(() => buildVaultActionPrompt('explode' as never, items)).toThrow()
    })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- src/__tests__/lib/vaultActions.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the module**

Create `frontend/src/lib/vaultActions.ts`:

```typescript
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Templated prompts for vault → agent actions.
 *
 * Each action turns a list of selected vault assets into a prefilled chat
 * message that the user can review and send. Templates live here so they
 * are easy to tune without touching the UI.
 */

export type VaultActionId = 'post_social' | 'use_campaign' | 'draft_email' | 'custom';

export interface VaultActionItem {
  id: string;
  filename: string;
  file_type: string | null;
  signed_url: string;
}

function renderAssetList(items: VaultActionItem[]): string {
  return items
    .map((item) => `- ${item.filename} (${item.file_type ?? 'unknown'}): ${item.signed_url}`)
    .join('\n');
}

export function buildVaultActionPrompt(
  action: VaultActionId,
  items: VaultActionItem[],
): string {
  const list = renderAssetList(items);

  switch (action) {
    case 'post_social':
      return [
        'Please post these assets to social media. Suggest captions for LinkedIn and X, and recommend the best platform for each asset.',
        '',
        'Assets:',
        list,
      ].join('\n');

    case 'use_campaign':
      return [
        'Build a marketing campaign that uses these assets. Recommend the channel mix, sequencing, and key messaging.',
        '',
        'Assets:',
        list,
      ].join('\n');

    case 'draft_email':
      return [
        'Draft an email using these assets as inline images or attachments. Ask me who the recipient list is and what the goal of the email is.',
        '',
        'Assets:',
        list,
      ].join('\n');

    case 'custom':
      return ['Assets:', list].join('\n');

    default:
      throw new Error(`Unknown vault action: ${String(action)}`);
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- src/__tests__/lib/vaultActions.test.ts`
Expected: PASS, all five cases.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/vaultActions.ts frontend/src/__tests__/lib/vaultActions.test.ts
git commit -m "feat(vault): prompt templates for vault-to-agent actions"
```

---

### Task 7: SessionStorage prefill helpers + session-id generator

**Files:**
- Create: `frontend/src/lib/vaultPrefill.ts`
- Test: `frontend/src/__tests__/lib/vaultPrefill.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/__tests__/lib/vaultPrefill.test.ts`:

```typescript
/**
 * @vitest-environment jsdom
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
    mintPrefillSessionId,
    storeVaultPrefill,
    consumeVaultPrefill,
    PREFILL_STORAGE_PREFIX,
} from '@/lib/vaultPrefill'

vi.mock('@/lib/freshClientSessions', () => ({
    markFreshClientSession: vi.fn(),
}))

describe('vaultPrefill', () => {
    beforeEach(() => {
        sessionStorage.clear()
    })

    afterEach(() => {
        sessionStorage.clear()
    })

    it('mints a session id starting with `session-`', () => {
        const id = mintPrefillSessionId()
        expect(id).toMatch(/^session-\d+-[a-z0-9]+$/)
    })

    it('stores and consumes the prefill exactly once', () => {
        const id = 'session-1-abc'
        storeVaultPrefill(id, 'hello world')
        expect(sessionStorage.getItem(`${PREFILL_STORAGE_PREFIX}${id}`)).toBe('hello world')

        const first = consumeVaultPrefill(id)
        expect(first).toBe('hello world')

        const second = consumeVaultPrefill(id)
        expect(second).toBeNull()
    })

    it('returns null when nothing is stored', () => {
        expect(consumeVaultPrefill('missing')).toBeNull()
    })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- src/__tests__/lib/vaultPrefill.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `frontend/src/lib/vaultPrefill.ts`:

```typescript
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Hand-off layer between the Vault page and the workspace chat composer.
 *
 * When the user picks vault assets and clicks an action chip, we mint a
 * fresh session id, write the templated prompt under a session-scoped
 * sessionStorage key, and navigate to the workspace. The chat composer
 * reads (and clears) the key on mount so the message appears in the
 * input ready to edit and send.
 */

import { markFreshClientSession } from '@/lib/freshClientSessions';

export const PREFILL_STORAGE_PREFIX = 'pikar_vault_prefill_';

/**
 * Mints a session id in the same shape used by SessionControlContext.
 * Marks it fresh so the history-restore effect skips it.
 */
export function mintPrefillSessionId(): string {
  const id = `session-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  markFreshClientSession(id);
  return id;
}

export function storeVaultPrefill(sessionId: string, prompt: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(`${PREFILL_STORAGE_PREFIX}${sessionId}`, prompt);
  } catch {
    // sessionStorage unavailable — nothing else we can do.
  }
}

/**
 * Reads and CLEARS the prefill in one call. Returns null if not present.
 * Single-use is intentional — re-entering the workspace must not refill.
 */
export function consumeVaultPrefill(sessionId: string): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const key = `${PREFILL_STORAGE_PREFIX}${sessionId}`;
    const value = window.sessionStorage.getItem(key);
    if (value !== null) {
      window.sessionStorage.removeItem(key);
    }
    return value;
  } catch {
    return null;
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- src/__tests__/lib/vaultPrefill.test.ts`
Expected: PASS, three cases.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/vaultPrefill.ts frontend/src/__tests__/lib/vaultPrefill.test.ts
git commit -m "feat(vault): sessionStorage prefill helpers for chat composer hand-off"
```

---

### Task 8: `VaultActionBar` component

**Files:**
- Create: `frontend/src/components/vault/VaultActionBar.tsx`
- Test: `frontend/src/__tests__/components/VaultActionBar.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/__tests__/components/VaultActionBar.test.tsx`:

```typescript
/**
 * @vitest-environment jsdom
 */

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { VaultActionBar } from '@/components/vault/VaultActionBar'

describe('<VaultActionBar />', () => {
    it('renders the count and four chips when at least one item is selected', () => {
        render(
            <VaultActionBar
                selectedCount={3}
                onAction={vi.fn()}
                onClear={vi.fn()}
            />,
        )
        expect(screen.getByText(/3 selected/i)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /post to social/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /use in campaign/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /draft an email/i })).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /custom prompt/i })).toBeInTheDocument()
    })

    it('returns null when selectedCount is 0', () => {
        const { container } = render(
            <VaultActionBar selectedCount={0} onAction={vi.fn()} onClear={vi.fn()} />,
        )
        expect(container.firstChild).toBeNull()
    })

    it('calls onAction with the action id when a chip is clicked', () => {
        const onAction = vi.fn()
        render(
            <VaultActionBar selectedCount={2} onAction={onAction} onClear={vi.fn()} />,
        )
        fireEvent.click(screen.getByRole('button', { name: /post to social/i }))
        expect(onAction).toHaveBeenCalledWith('post_social')
    })

    it('calls onClear when Clear is clicked', () => {
        const onClear = vi.fn()
        render(
            <VaultActionBar selectedCount={1} onAction={vi.fn()} onClear={onClear} />,
        )
        fireEvent.click(screen.getByRole('button', { name: /clear/i }))
        expect(onClear).toHaveBeenCalled()
    })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- src/__tests__/components/VaultActionBar.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `frontend/src/components/vault/VaultActionBar.tsx`:

```tsx
// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

'use client';

import React from 'react';
import { Send, Layers, Mail, MessageSquare, X } from 'lucide-react';
import type { VaultActionId } from '@/lib/vaultActions';

interface VaultActionBarProps {
    selectedCount: number;
    onAction: (action: VaultActionId) => void;
    onClear: () => void;
}

const CHIPS: Array<{ id: VaultActionId; label: string; icon: React.ReactNode }> = [
    { id: 'post_social', label: 'Post to social', icon: <Send size={14} /> },
    { id: 'use_campaign', label: 'Use in campaign', icon: <Layers size={14} /> },
    { id: 'draft_email', label: 'Draft an email', icon: <Mail size={14} /> },
    { id: 'custom', label: 'Custom prompt', icon: <MessageSquare size={14} /> },
];

export function VaultActionBar({ selectedCount, onAction, onClear }: VaultActionBarProps) {
    if (selectedCount === 0) return null;

    return (
        <div
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 rounded-2xl bg-white/95 backdrop-blur shadow-xl border border-slate-200 px-5 py-3 flex items-center gap-3"
            role="region"
            aria-label="Vault selection actions"
        >
            <span className="text-sm font-medium text-slate-700">
                {selectedCount} selected
            </span>
            <span className="text-slate-300">|</span>
            <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
                Ask agent to:
            </span>
            <div className="flex items-center gap-2">
                {CHIPS.map((chip) => (
                    <button
                        key={chip.id}
                        type="button"
                        onClick={() => onAction(chip.id)}
                        className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 hover:bg-teal-100 text-teal-700 px-3 py-1.5 text-xs font-medium transition-colors"
                    >
                        {chip.icon}
                        {chip.label}
                    </button>
                ))}
            </div>
            <span className="text-slate-300">|</span>
            <button
                type="button"
                onClick={onClear}
                className="inline-flex items-center gap-1 rounded-full hover:bg-slate-100 text-slate-500 px-3 py-1.5 text-xs font-medium transition-colors"
                aria-label="Clear"
            >
                <X size={14} /> Clear
            </button>
        </div>
    );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- src/__tests__/components/VaultActionBar.test.tsx`
Expected: PASS, four cases.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/vault/VaultActionBar.tsx frontend/src/__tests__/components/VaultActionBar.test.tsx
git commit -m "feat(vault): VaultActionBar component for selection actions"
```

---

### Task 9: Wire selection into `VaultInterface` + dispatch action

**Files:**
- Modify: `frontend/src/components/vault/VaultInterface.tsx` (add selection state, checkboxes on `DocumentCard`, action handler that builds the prompt and navigates)

- [ ] **Step 1: Add imports**

Near the top of `VaultInterface.tsx`, add:

```typescript
import { useRouter } from 'next/navigation';
import { Check } from 'lucide-react';
import { VaultActionBar } from '@/components/vault/VaultActionBar';
import {
    buildVaultActionPrompt,
    VaultActionId,
    VaultActionItem,
} from '@/lib/vaultActions';
import {
    mintPrefillSessionId,
    storeVaultPrefill,
} from '@/lib/vaultPrefill';
```

- [ ] **Step 2: Add selection state to `VaultInterface`**

Inside the `VaultInterface` component body, near other `useState` calls, add:

```typescript
    const router = useRouter();
    const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());

    const toggleSelected = useCallback((id: string) => {
        setSelectedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    }, []);

    const clearSelection = useCallback(() => setSelectedIds(new Set()), []);
```

- [ ] **Step 3: Build the action handler**

Below `clearSelection`, add:

```typescript
    const handleVaultAction = useCallback(
        (action: VaultActionId) => {
            const items: VaultActionItem[] = documents
                .filter((d) => selectedIds.has(d.id))
                .map((d) => ({
                    id: d.id,
                    filename: d.filename,
                    file_type: d.file_type ?? null,
                    signed_url: d.preview_url ?? d.file_url ?? '',
                }))
                .filter((item) => item.signed_url);

            if (items.length === 0) return;

            const prompt = buildVaultActionPrompt(action, items);
            const sessionId = mintPrefillSessionId();
            storeVaultPrefill(sessionId, prompt);
            clearSelection();
            router.push(`/dashboard/workspace?prefill_session=${encodeURIComponent(sessionId)}`);
        },
        [documents, selectedIds, clearSelection, router],
    );
```

- [ ] **Step 4: Pass selection props down to `DocumentCard`**

Find the loop that renders `DocumentCard`. Add the new props:

```tsx
<DocumentCard
    key={doc.id}
    doc={doc}
    onDownload={handleDownload}
    onDelete={handleDelete}
    onViewInWorkspace={handleViewInWorkspace}
    viewMode={viewMode}
    isSelected={selectedIds.has(doc.id)}
    onToggleSelected={toggleSelected}
/>
```

- [ ] **Step 5: Update `DocumentCard` props + render checkbox**

In the `DocumentCard` props (around line 462–474), add:

```typescript
    isSelected: boolean;
    onToggleSelected: (id: string) => void;
```

In the grid-mode return (around line 580), insert this checkbox at the top of the card (just inside the `motion.div`, before any other children):

```tsx
            <button
                type="button"
                aria-label={isSelected ? 'Deselect' : 'Select'}
                onClick={(e) => {
                    e.stopPropagation();
                    onToggleSelected(doc.id);
                }}
                className={`absolute top-2 left-2 z-10 w-6 h-6 rounded-md flex items-center justify-center transition-colors ${
                    isSelected
                        ? 'bg-teal-600 text-white'
                        : 'bg-white/90 border border-slate-300 text-transparent hover:border-teal-400 hover:text-teal-400'
                }`}
            >
                <Check size={14} />
            </button>
```

In the list-mode return (around line 513–577), prepend a similar button as the very first child of the outer `flex` row:

```tsx
                <button
                    type="button"
                    aria-label={isSelected ? 'Deselect' : 'Select'}
                    onClick={(e) => {
                        e.stopPropagation();
                        onToggleSelected(doc.id);
                    }}
                    className={`shrink-0 w-6 h-6 rounded-md flex items-center justify-center transition-colors ${
                        isSelected
                            ? 'bg-teal-600 text-white'
                            : 'bg-white border border-slate-300 text-transparent hover:border-teal-400 hover:text-teal-400'
                    }`}
                >
                    <Check size={14} />
                </button>
```

- [ ] **Step 6: Mount `VaultActionBar` at the bottom of `VaultInterface`'s root JSX**

Just before the closing root `</div>` of `VaultInterface`, add:

```tsx
            <VaultActionBar
                selectedCount={selectedIds.size}
                onAction={handleVaultAction}
                onClear={clearSelection}
            />
```

- [ ] **Step 7: Manual smoke test**

Run: `cd frontend && npm run dev`
- Open `/dashboard/vault` → Images. Click checkboxes on three image cards.
- Confirm the action bar appears at the bottom with "3 selected" + four chips.
- Click "Post to social". Confirm navigation to `/dashboard/workspace?prefill_session=...`.
- Confirm sessionStorage now contains a `pikar_vault_prefill_session-...` key (via DevTools Application tab) — but only until the chat composer reads it (next task).

- [ ] **Step 8: Lint**

Run: `cd frontend && npm run lint`
Expected: clean.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/vault/VaultInterface.tsx
git commit -m "feat(vault): multi-select with action bar dispatch to workspace prefill"
```

---

### Task 10: Read prefill on chat mount

**Files:**
- Modify: `frontend/src/components/chat/ChatInterface.tsx` (use the prefill on mount when the URL contains `prefill_session=<currentSessionId>`)

- [ ] **Step 1: Add imports near the top of `ChatInterface.tsx`**

```typescript
import { useSearchParams } from 'next/navigation';
import { consumeVaultPrefill } from '@/lib/vaultPrefill';
```

- [ ] **Step 2: Read the search param**

Inside the `ChatInterface` component body, near the other hooks (state, refs), add:

```typescript
    const searchParams = useSearchParams();
    const prefillSessionParam = searchParams?.get('prefill_session') ?? null;
```

- [ ] **Step 3: Add the prefill effect**

Find the `useState('')` for `input` (around line 282) and just below the section where `setInput` is first defined, add:

```typescript
    const prefillAppliedRef = useRef(false);
    useEffect(() => {
        if (prefillAppliedRef.current) return;
        if (!prefillSessionParam) return;
        const stored = consumeVaultPrefill(prefillSessionParam);
        if (stored) {
            setInput(stored);
            prefillAppliedRef.current = true;
        }
    }, [prefillSessionParam]);
```

(Ensure `useRef` and `useEffect` are already imported near the top of the file — they are, but double-check.)

- [ ] **Step 4: Manual smoke test**

Run: `cd frontend && npm run dev`
- From `/dashboard/vault` → Images, select 2 images and click "Custom prompt".
- After navigating to the workspace, confirm the chat composer is prefilled with the assets list.
- Edit the text, hit send, confirm the agent receives the URL-bearing message.
- Reload the workspace page on the same URL. Confirm the composer is **not** re-prefilled (single-use).

- [ ] **Step 5: Run frontend test suite**

Run: `cd frontend && npm test`
Expected: all PASS (no regression).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/chat/ChatInterface.tsx
git commit -m "feat(chat): consume vault prefill from sessionStorage on mount"
```

---

## Final verification

- [ ] **Run full frontend test suite + lint**

```bash
cd frontend && npm test && npm run lint
```

Expected: all PASS, no new lint warnings.

- [ ] **Run pre-commit hooks for the touched Python (none in this work — PR 1 is frontend-only) and confirm git tree is clean**

```bash
git status
```

Expected: nothing to commit.

- [ ] **Manual end-to-end smoke**

  1. `/dashboard/history` — hard reload 5 times in a row → sessions render every time. Stop backend, reload → rose error banner with Retry. Restart backend, click Retry → sessions populate.
  2. `/dashboard/vault` → Images tab — thumbnails render for uploaded images.
  3. `/dashboard/vault` → Images tab — select 3 images, click "Post to social" → workspace opens with composer prefilled, edit + send works, agent receives URLs.
  4. `/dashboard/vault` → Videos tab — thumbnails render for video assets too.

- [ ] **Push branch and open PR**

```bash
git push -u origin <branch>
```
