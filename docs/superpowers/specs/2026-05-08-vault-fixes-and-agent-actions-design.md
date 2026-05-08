# Vault thumbnail + chat-history regressions, and vault-as-an-interaction-surface

**Date:** 2026-05-08
**Status:** Draft for review

## Problem

Three issues, reported together:

1. **Chat history disappears on reload (intermittent).** On `/dashboard/history`, a hard reload sometimes shows zero past sessions even though the data is in Supabase. A subsequent reload usually brings it back.
2. **Vault image cards no longer show thumbnails.** Recent `bf317b3e` ("route data fetches through server-side API") fixed the row queries but broke the storage URL signing. Image cards collapse to the file-icon fallback, so users can't visually identify an asset they're searching for.
3. **The Vault is read-only.** Users can download or delete an asset, but cannot select images/videos and ask the agent to act on them (post to social, use in a campaign, attach to an email, etc.). The Vault is a viewing surface, not an interaction surface.

## Root causes

### Chat-history reload (#1)

- `dashboard/history/page.tsx:99` calls `refreshSessions()` on mount. That eventually hits `services/sessions.ts:36` → `${NEXT_PUBLIC_API_URL}/sessions` with a Bearer JWT obtained from `getAccessToken()`.
- On hard reload, two async sources race: `userId` from `supabase.auth.getUser()` and the cookie-stored access token. If `getAccessToken()` is briefly unavailable, or the backend cold-starts and returns 401, `listUserSessions()` throws.
- `SessionControlContext.tsx:464` swallows the error with only `console.error`. The page renders the empty state and shows nothing else.
- The page IS calling `refreshSessions` again on `visibilitychange`, which is why a subsequent reload (or tab away/back) often "fixes" it once auth is warm.

### Vault thumbnails (#2)

- `bf317b3e` correctly moved row queries to `/api/vault/list` (server-side, cookie-aware).
- However the **signing step** in `VaultInterface.tsx:929` still calls `supabase.storage.from(bucket).createSignedUrls(...)` from the **browser client**. That client is exactly the one bf317b3e flagged as JWT-unreliable.
- When signing returns nothing, `signedUrlMap` is empty, `preview_url` stays `undefined`, and the card renders the icon fallback at line 612 instead of the image.
- External absolute URLs (some Veo videos, CDN-served assets) continue to work because `getInitialPreviewUrl()` accepts those directly — that's why **some** media still shows.

### Vault read-only (#3)

- `DocumentCard` exposes only Download / Delete / View-in-workspace.
- The chat composer (`ChatInterface.tsx:282`, `:1124`) has `setInput()` and `sendMessage()` but no entry point to receive selected vault items as context.
- The agent has tools for posting, drafting, campaign building, but no path for the user to hand it specific assets short of typing filenames or URLs.

## Goals

- Restore image/video thumbnails in the Vault (regression).
- Make the chat-history page deterministic on reload (regression).
- Let users select assets in the Vault and hand them to the agent with a clear action ("post to social", "draft an email", etc.).

## Non-goals

- A vault-side ADK tool that lets the agent self-serve assets ("use the latest 3 product photos") — out of scope for this spec, planned as Layer B.
- Migration of legacy `media_assets` rows missing `file_url`/`thumbnail_url` to a unified shape.
- Cross-session attachments (selected vault items only attach to the active or newly-created session).

## Approach

Two PRs, sequenced.

### PR 1 — Restore the regressions

**1a. Server-side vault URL signing**

- Add `POST /api/vault/sign-urls` (Next.js route, SSR Supabase client). Body: `{ bucket: string, paths: string[] }`. Returns `{ items: Array<{ path: string, signedUrl: string | null, error?: string }> }`. 1 hour expiry.
- In `VaultInterface.tsx`, replace the `createSignedUrls` block at line 929 with a `fetch('/api/vault/sign-urls', { method: 'POST', body: JSON.stringify({ bucket, paths }) })` call. Same shape into `signedUrlMap`, no other behavior changes.
- The 15s `withTimeout` wrapper stays.

**1b. Server-side session list**

- Add `GET /api/sessions/list` (Next.js route). It reads the Supabase access token from the SSR cookies and proxies to the backend `${API_BASE}/sessions?limit=...` with the proper `Authorization: Bearer` header. Returns the same `{ sessions, count }` shape.
- `services/sessions.ts` — repoint `listUserSessions()` at `/api/sessions/list`. Drop the direct browser-token dependency.
- Inside `listUserSessions()`, add a single retry on transient failure (network error or 5xx, 500ms backoff). Do not retry on 4xx.

**1c. History page error UX**

- `dashboard/history/page.tsx` — track a `refreshError: Error | null` state from the latest `refreshSessions` call. When set, show an inline retry banner ("Couldn't load your history. Retry") instead of the empty state.
- `SessionControlContext.tsx` — surface the error from `refreshSessions` (currently swallowed) so the page can read it. Smallest change: add a returned `error: Error | null` to the context, set on catch.

### PR 2 — Vault-as-interaction-surface (Layer A)

**2a. Selection state**

- `VaultInterface.tsx` adds `selectedIds: Set<string>` and `selectionMode: boolean`. Selection mode toggles on with the first checkbox click and off when the user clears or completes an action.
- `DocumentCard` gains a checkbox overlay (top-left in grid mode, leading column in list mode) when `selectionMode` is on. Hover always reveals the checkbox; click toggles selection without triggering the card's preview/download handlers.

**2b. Action bar**

- When `selectedIds.size > 0`, render a sticky bottom action bar (`fixed bottom-6 inset-x-6`, blurred bg, rounded). Shows count ("3 selected") and four action chips: **Post to social**, **Use in campaign**, **Draft an email**, **Custom prompt**.
- Plus a "Clear" button.

**2c. Action → composer prefill**

- New module `frontend/src/lib/vaultActions.ts`. Exports `buildVaultActionPrompt(action, items)` returning the prefill text. Templates are kept here so they're easy to tune later.
- Selected items are resolved to `{ id, filename, file_type, signed_url }` objects. `signed_url` comes from the already-cached `preview_url` on the doc, or is freshly minted via `/api/vault/sign-urls` if missing.
- Action chip click:
  1. Build the prompt via `buildVaultActionPrompt`.
  2. Navigate to `/dashboard/workspace` with a fresh session id (mint via the same `generateSessionId()` used elsewhere). Use a query param like `?prefill_session=<id>` to signal to the workspace page that there's a queued prefill.
  3. Stash the prompt in `sessionStorage` under `pikar_vault_prefill_${sessionId}` (single-use; cleared on read).
- `ChatInterface.tsx` — on mount, if the session matches the queued prefill key, read it from `sessionStorage`, `setInput(prompt)`, focus the textarea, and clear the storage key. Do NOT auto-send.

**Action prompt templates (initial):**

- *Post to social*: "Post these assets to social media. Use the [PRIMARY_TYPE] for the main visual. Suggest captions for LinkedIn and X. Assets: <bulleted list with filenames + signed URLs>."
- *Use in campaign*: "Build a marketing campaign that uses these assets. Suggest the channel mix and timing. Assets: <list>."
- *Draft an email*: "Draft an email to [my list / a customer — ask me] using these assets as inline images or attachments. Assets: <list>."
- *Custom prompt*: just the assets list — user writes the request.

The agent already has tools for posting, drafting, and campaign building. As long as the message contains the filename + signed URL, those tools can act on the assets.

### Out of scope (Layer B)

- ADK `vault.fetch_asset(asset_id)` / `vault.search_assets(query)` tools. The agent could then resolve "the latest three product photos" without preselection. Worth doing, but separate spec.

## Components / files touched

**PR 1:**
- New: `frontend/src/app/api/vault/sign-urls/route.ts`
- New: `frontend/src/app/api/sessions/list/route.ts`
- Edit: `frontend/src/components/vault/VaultInterface.tsx` (~30 lines around line 929)
- Edit: `frontend/src/services/sessions.ts` (URL + retry)
- Edit: `frontend/src/contexts/SessionControlContext.tsx` (surface error)
- Edit: `frontend/src/app/dashboard/history/page.tsx` (error banner)
- Tests: extend `__tests__/services/vault-proxy.test.ts` if it exists; new test for sessions retry

**PR 2:**
- New: `frontend/src/lib/vaultActions.ts`
- New: `frontend/src/components/vault/VaultActionBar.tsx`
- Edit: `frontend/src/components/vault/VaultInterface.tsx` (selection state, action bar mount, prop drilling to `DocumentCard`)
- Edit: `DocumentCard` inside `VaultInterface.tsx` (checkbox UI + props)
- Edit: `frontend/src/components/chat/ChatInterface.tsx` (prefill read-on-mount)
- Tests: vault selection unit tests, prefill read test

## Data flow

**Vault thumbnails (PR 1):**
```
VaultInterface.fetchDocuments
  → GET /api/vault/list?tab=images  (rows)
  → POST /api/vault/sign-urls       (signed URLs for paths)
  → setDocuments(docs with preview_url)
  → DocumentCard renders <img src={doc.preview_url} />
```

**History (PR 1):**
```
HistoryPage mount
  → SessionControlContext.refreshSessions
  → GET /api/sessions/list  (server-proxies to backend /sessions with cookie JWT)
  → setSessions
On error: setRefreshError → page shows retry banner
```

**Vault → Agent (PR 2):**
```
User clicks 3 image checkboxes → selectedIds = {a,b,c}
User clicks "Post to social"
  → buildVaultActionPrompt('post_social', items)
  → mint new session id; sessionStorage.set('pikar_vault_prefill_<id>', prompt)
  → router.push('/dashboard/workspace?prefill_session=<id>')
ChatInterface mounts on that session
  → reads sessionStorage; setInput(prompt); focus
  → user reviews, optionally edits, hits send
Agent receives the message with embedded URLs and acts via existing tools
```

## Testing

**PR 1:**
- Unit: `/api/vault/sign-urls` returns signed URLs for valid paths, error tag for invalid.
- Unit: `/api/sessions/list` proxies and returns 401 cleanly (not as 500).
- Unit: `listUserSessions` retries once on 503.
- Manual: hard-reload `/dashboard/history` 5x in a row; sessions render every time. Hard-reload `/dashboard/vault` on the Images tab; thumbnails appear.

**PR 2:**
- Unit: `buildVaultActionPrompt` produces stable templates for each action.
- Unit: vault selection state correctly tracks add/remove/clear.
- Unit: `ChatInterface` reads the prefill key on mount and clears it.
- Manual: select 3 images → "Post to social" → workspace opens with a fresh session, composer pre-filled, user can edit and send. Agent message preserves the URLs.

## Risks

- **Signed URLs leak into prompts.** When the user sends the prefilled message, signed URLs (1h expiry) end up in the session log. Acceptable for now — they're per-user, expire, and the agent needs them. Worth re-evaluating if we add export/share-chat features.
- **Backend `/sessions` can still 401.** The PR 1 retry helps with cold starts; persistent auth issues are surfaced with the new error banner instead of being silent.
- **Action prompt templates may be too generic.** The `vaultActions.ts` module localizes templates so we can iterate without re-touching the UI.

## Open questions (resolved with user)

- Sequencing: fixes first, feature after — confirmed.
- Send behavior: prefill, don't auto-send — confirmed.
- Initial action chips: all four (Post to social, Use in campaign, Draft an email, Custom prompt) — confirmed.
