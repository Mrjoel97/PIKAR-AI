# Where Chat History Is Stored

## Backend (source of truth)

**Chat message content is stored in the backend** in Supabase (PostgreSQL):

| Table            | Purpose |
|------------------|--------|
| **`sessions`**  | One row per conversation: `app_name`, `user_id`, `session_id`, `state` (JSON: title, lastMessage), `created_at`, `updated_at`. |
| **`session_events`** | One row per message/event: `session_id`, `app_name`, `user_id`, `event_data` (JSON: user/agent content), `event_index`, `version`, etc. |

- **Who writes:** The Python backend (FastAPI) when you send a message:
  - Endpoint: `POST /a2a/app/run_sse`
  - Uses `SupabaseSessionService` in `app/persistence/supabase_session_service.py`
  - Creates a row in `sessions` if needed, then appends each user/agent turn to `session_events` with `app_name = "agents"`.

- **App name:** Backend uses `adk_app.name` which is **`"agents"`** (see `app/agent.py`).

## Frontend (UI and which session to show)

The frontend does **not** store message content. It only:

1. **Stores the current session id** in `localStorage` under the key **`pikar_current_session_id`** so after refresh or navigation it knows which conversation to load.
2. **Fetches history from the backend** by calling Supabase from the browser:
   - In **`useAgentChat.ts`** → `loadHistory(sessionId)`:
     - Queries **`session_events`** with:
       - `session_id` = the conversation id
       - `app_name` = `'agents'`
       - `user_id` = current Supabase auth user
       - `superseded_by` is null
     - Orders by `event_index` and maps `event_data` into chat messages.
   - In **`ChatSessionContext.tsx`** → `fetchSessions()`:
     - Queries **`sessions`** for the user to build the chat history list (titles, previews, dates).

So:

- **Message content:** backend (Supabase `session_events`).
- **Which conversation is “current”:** frontend (`localStorage` + context).
- **Listing of past chats:** frontend reads from backend (`sessions` table).

## Flow summary

1. User sends a message → frontend calls `run_sse` with `session_id` + auth.
2. Backend ensures the session exists in `sessions`, runs the agent, appends user + agent events to `session_events`.
3. On load/refresh or when opening a chat from history, frontend calls `loadHistory(sessionId)` and reads from `session_events` for that `session_id` and user.

If messages don’t appear after refresh or when opening from history, the problem is usually one of:

- **Session id mismatch** (e.g. different id in `localStorage` vs the one used when sending messages).
- **Auth timing** (e.g. `getUser()` null when `loadHistory` runs).
- **RLS** (e.g. frontend query not allowed for the current user).
- **Backend not writing** (e.g. session never created or wrong `app_name`/`user_id`).

Use the browser Network tab and Supabase dashboard to confirm that rows exist in `sessions` and `session_events` for the expected `session_id` and `user_id`, and that the frontend request uses the same ids.
