# Plan: Chat media persistence and view-in-workspace

## Goals

1. **Images and videos must not disappear** after reload or when leaving the page; they should persist in the chat like text messages and rehydrate correctly.
2. **No “Image could not be loaded”** after reload when the file exists in storage; fix rehydration so signed URLs are created and applied reliably.
3. **Click to view in workspace:** When the user clicks an image/video in the chat or in the Knowledge Vault **Media Files** tab, the media should open **immediately in the workspace**, and (for vault) the app should open the chat/session where that media was created so the user sees it in context.

---

## Current behavior (problems)

- After **reload**, chat history is loaded from `session_events` and rehydration runs for widgets with `asset_id`, but images often show **“Image could not be loaded. It may have expired or was removed.”** So either rehydration is failing or the stored widget does not have `asset_id`.
- **View in workspace** from chat uses the same widget (with rehydrated or stale URL); if the URL is broken, the workspace shows the same error.
- **Knowledge Vault → Media Files:** Clicking a media item does not open it in the workspace or open the related chat.

---

## Root causes to address

1. **Rehydration failing**
   - Stored `event_data` might not expose `asset_id` in the shape the frontend expects (e.g. widget inside `content.parts[].function_response.response` vs `response.result`).
   - Frontend might not be getting a valid signed URL (storage path mismatch, RLS, or `createSignedUrl` result shape).
   - Auth might not be ready when `loadHistory` runs (there is already one retry; may need a more robust wait).

2. **Widget shape in DB**
   - Events are stored with `event.model_dump(mode="json")` (raw ADK event). The SSE layer injects `event.widget` for the client but does **not** change what is persisted. So persisted events have the widget only inside `content.parts[].function_response` (or nested `result`). The frontend must extract the widget from that and must see `data.asset_id`.

3. **No link from vault media to chat**
   - `media_assets` does not store `session_id`. So when the user clicks a media file in the vault, we can show it in the workspace (by building a widget and focusing it) but we cannot yet “open the chat where it was created” without either storing that link or searching `session_events`.

---

## Plan (implementation order)

### Phase 1: Fix rehydration so images/videos persist after reload

**1.1 Ensure stored events carry `asset_id`**

- **Backend:** When the agent returns an image/video widget from the tool, the tool already includes `data.asset_id`. Verify that the event that gets appended to `session_events` contains this (i.e. the ADK does not strip it). If the widget is only in `content.parts[].function_response.response` or `.response.result`, the frontend extraction must read from both and preserve `data.asset_id`.
- **Frontend – `useAgentChat.loadHistory`:** When building `historyMessages`, ensure the widget extracted from `event_data` is the same object that contains `data.asset_id`. Today we take `candidate` from `response` or `response.result`; confirm that in both cases the tool result has `data.asset_id`. Add a single `console.log` (or dev-only trace) when rehydrating so we can see “rehydrating asset_id X” and success/failure.

**1.2 Rehydration path and storage**

- **Path:** Backend stores files at `media/{user_id}/{asset_id}.png` or `.mp4` in bucket `knowledge-vault`. Frontend rehydration uses the same path. Confirm no typo or extra prefix.
- **RLS:** Policy in `0033_knowledge_vault_tables.sql` allows `auth.uid()::text` as first folder in `name`. Path `media/{user_id}/{asset_id}.png` gives first folder `media`, second folder `user_id`. So RLS must allow by **second** segment (user_id), not first. Check `storage.foldername(name)[1]` – if it is 1-based, `[1]` might be `media` and `[2]` might be `user_id`. Verify RLS so that the authenticated user can `createSignedUrl` for their own `media/{user_id}/*` files.
- **createSignedUrl result:** Frontend already handles both `signedUrl` and `signedURL`. Ensure the Supabase client version used returns one of these. On rehydration error, log `error.message` and the attempted path so we can see “permission denied” vs “not found”.

**1.3 Robust rehydration and UX**

- If `createSignedUrl` fails for an image/video widget that has `asset_id`, keep the message in the list but ensure the widget’s `imageUrl`/`videoUrl` is set to a value that triggers **ImageWidget**’s “invalid URL” branch (e.g. empty or placeholder), so we show “Image is loading or unavailable” instead of a broken image. Optionally, set a flag like `rehydrationFailed: true` so the UI can show “Refresh” or “Try again” that re-runs rehydration for that message.
- Consider a **short retry** for rehydration: if the first `createSignedUrl` fails (e.g. auth delay), wait 1–2 seconds and retry once for that asset before giving up.

**1.4 video_spec**

- If `video_spec` widgets also have an `asset_id` and a stored file, apply the same rehydration logic for them so they persist after reload.

---

### Phase 2: Chat and workspace always use rehydrated URLs

**2.1 Single source of truth**

- After `loadHistory`, all image/video widgets in `messages` should have valid signed URLs when rehydration succeeds. “View in workspace” uses the same `msg.widget` from state, so it will show the rehydrated URL. No extra fetch for workspace view.

**2.2 ImageWidget / VideoWidget**

- Keep the current behavior: if URL is missing, placeholder, or invalid, show a short message; on `onError` show “Image could not be loaded…”. Once rehydration is fixed, this will only appear when the file is actually missing or access is denied.

---

### Phase 3: Knowledge Vault Media → view in workspace and open chat

**3.1 Click media in Vault → workspace**

- In **VaultInterface**, for the **Media Files** tab, when the user clicks a document row (or a “View” action):
  - Build a signed URL for that document (`file_path` is like `media/{user_id}/{asset_id}.png` or `.mp4`). Use the same bucket and expiry as chat rehydration.
  - Build a minimal widget: `{ type: 'image'|'video', data: { imageUrl|videoUrl: signedUrl, asset_id } }` (derive `asset_id` from `file_path`: last segment without extension).
  - Call `dispatchFocusWidget(widget, userId)` so the workspace shows the media in focus immediately.
- Ensure the workspace can render this widget even when it’s not from the current chat (it’s the same `ImageWidget`/`VideoWidget`).

**3.2 Open the chat where the media was created**

- **Option A – Store session in metadata:** When the backend creates a media asset (e.g. in `canva_media`), it does not currently have access to `session_id` in the tool. If we can pass `session_id` (and optionally `event_id`) into the tool and add `session_id` to `media_assets.metadata` on insert, then when the user clicks the media in the vault we can:
  - Read `metadata.session_id`,
  - Set the current session in **ChatSessionContext** (or equivalent) to that `session_id`,
  - Load that session’s history so the chat panel shows the conversation where the image/video was created,
  - And keep the workspace focused on the media (already done in 3.1).
- **Option B – Search session_events:** Without changing the backend, the frontend can try to find a session that contains this `asset_id`: query `session_events` for the user (e.g. by `user_id`), fetch event_data, and find an event whose `content.parts` or `widget` contains `data.asset_id === asset_id`. Then set that session as current and load history. This can be expensive if the user has many sessions; limit to recent N sessions or add a backend RPC later (e.g. `find_session_for_asset(asset_id)`).
- Prefer **Option A** if we can pass `session_id` into the tool; otherwise implement **Option B** with a reasonable limit (e.g. last 50 sessions or last 30 days).

---

### Phase 4: Optional improvements

- **Retry / Refresh:** In the chat message or in ImageWidget, add a “Refresh” or “Try again” when the image failed to load, which re-runs rehydration for that message (or re-requests a signed URL for that `asset_id`) and updates the widget URL.
- **VideoWidget:** Apply the same invalid-URL and `onError` handling as in ImageWidget so videos show a clear message instead of a broken player when the URL is missing or fails.
- **Backend RPC:** If Option B is slow, add a Supabase RPC or small API that, given `user_id` and `asset_id`, returns `session_id` (and optionally `event_id`) by querying `session_events` with a JSON path or GIN index on `event_data`.

---

## Success criteria

- After reload, all image and video messages that have a stored file and `asset_id` show the image/video in the chat (no “Image could not be loaded” unless the file is actually missing or access denied).
- Clicking an image/video in the chat (“View in workspace”) shows it in the workspace with a valid URL.
- In Knowledge Vault → Media Files, clicking a media item opens it in the workspace immediately and (when implemented) opens the chat session where that media was created.

---

## Files to touch (summary)

| Area | Files |
|------|--------|
| Rehydration / history | `frontend/src/hooks/useAgentChat.ts` |
| Widget extraction | Same; ensure `asset_id` from `response` and `response.result` |
| Storage RLS | `supabase/migrations/0033_knowledge_vault_tables.sql` (verify or fix policy) |
| Image/Video UX | `frontend/src/components/widgets/ImageWidget.tsx`, `VideoWidget.tsx` |
| Vault → workspace | `frontend/src/components/vault/VaultInterface.tsx` |
| Session context / open chat | `frontend/src/contexts/ChatSessionContext.tsx`, dashboard layout that holds chat + workspace |
| Backend (optional) | `app/mcp/tools/canva_media.py` (add session_id to metadata if passed in), session service or API for find-session-by-asset |

---

## Verification

1. Create an image in chat (e.g. “generate an image of X”). Confirm it appears in chat and in workspace when clicked.
2. Reload the page. Confirm the image still appears in the chat (no “Image could not be loaded”).
3. Click “View in workspace” for that image. Confirm it shows in the workspace.
4. Go to Knowledge Vault → Media Files. Click the same image. Confirm it opens in the workspace and (after Phase 3.2) the chat switches to the session where it was created.
