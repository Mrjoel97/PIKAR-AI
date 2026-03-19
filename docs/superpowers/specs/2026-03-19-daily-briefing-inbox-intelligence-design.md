# Daily Briefing & Inbox Intelligence — Design Spec

**Date:** 2026-03-19
**Status:** Approved
**Author:** Claude + User collaborative brainstorm

## Problem Statement

Scheduling, inbox handling, planning, and event reminders are the biggest pain points for Pikar-AI's target users (startup founders, SMB owners, executives, and team leads). These users are drowning in emails, juggling calendars, and dropping balls because there's no intelligent system catching things for them.

## Solution Overview

A **Daily Briefing system** powered by Gmail inbox intelligence that acts as an AI chief of staff. The system pre-fetches and triages emails, drafts replies, auto-handles trivial messages, and presents everything in a morning briefing widget with approval workflows.

**Delivery channels:** Dashboard widget (primary), chat interface, email digest, and in-app notifications.

**Approach:** Hybrid — background pre-fetch + agent interaction. A background worker triages emails periodically, stores results in an `email_triage` table, and the dashboard widget + chat agent both read from this pre-computed data layer.

## Roadmap Context

This spec covers **Phase 1: Daily Briefing (Gmail-first)**. The system is designed to absorb future phases without schema changes:

- **Phase 2:** AI Scheduling Assistant — "schedule a demo with Acme next week"
- **Phase 3:** Follow-up Tracker — extract commitments, set reminders, nudge before things go stale
- **Phase 4:** Unified Inbox — CRM, Slack, and other channels feed into triage alongside email

## Target Personas

- **Startup founder** (primary) — wearing all hats, no EA, needs AI to be their chief of staff
- **SMB owner** — similar to founder but with a small team
- **Executive with EA** — has support but still overwhelmed by volume
- **Team lead / manager** — coordination pain across reports and meetings

---

## Section 1: Gmail Inbox Reading — Backend

### Extend Existing Service: `app/integrations/google/gmail.py`

Add to `GmailService`:

| Method | Purpose |
|--------|---------|
| `list_messages(user_id, query, max_results, label_ids)` | Fetch unread/recent messages from Gmail API. Supports filters: unread only, date range, label, max results. Returns message IDs + thread IDs. |
| `get_message(user_id, message_id, format)` | Fetch full message content by ID: sender, subject, body (plain + HTML), attachments metadata, labels, date, thread context. |
| `batch_get_messages(user_id, message_ids)` | Fetch multiple messages in one API call for efficiency. |
| `modify_message(user_id, message_id, add_labels, remove_labels)` | Add/remove labels, mark read/unread, archive. Needed for auto-act. |

### New Tool Module: `app/agents/tools/gmail_inbox.py`

ADK tool definitions:

| Tool | Description |
|------|-------------|
| `read_inbox()` | Get recent unread emails — returns list with sender, subject, snippet, date, urgency signals |
| `read_email()` | Get full email by sender/subject — returns full body + thread context |
| `classify_email()` | Thin wrapper around `EmailTriageService.classify()` — single classification engine shared with background worker. Ad-hoc classification via chat is persisted to `email_triage` table. |
| `archive_email()` | Mark as read + archive |
| `label_email()` | Apply labels |

Exported as `GMAIL_INBOX_TOOLS` list.

### Google OAuth Scope Changes

Current: `gmail.send`

Required additions:
- `gmail.readonly` — read messages, labels
- `gmail.modify` — mark read, archive, label

**Impact:** Existing users will need to re-authorize via OAuth consent screen.

### OAuth Token Lifecycle for Background Access

The background triage worker needs to call Gmail API when the user is not in an active session. This requires:

**1. Offline access with refresh tokens:**
- Update `frontend/src/services/auth.ts` to request offline access: add `queryParams: { access_type: 'offline', prompt: 'consent' }` to the `signInWithOAuth` options.
- This ensures Google issues a refresh token that persists beyond the session.
- Configure scopes in two places: Supabase Dashboard (Google provider settings) AND the `scopes` parameter in the frontend OAuth call.

**2. Refresh token storage:**
- Supabase Auth stores the `provider_refresh_token` in the `auth.sessions` table. The triage worker reads it from there via the service role key.
- Create a helper `get_user_gmail_credentials(user_id)` that: fetches the refresh token from `auth.sessions`, creates a `google.oauth2.credentials.Credentials` object with `client_id`, `client_secret`, and `refresh_token`, and handles automatic token refresh.

**3. Re-authorization flow for existing users:**
- On first visit after deployment, check if the user's stored token has `gmail.readonly` scope.
- If not, show a banner: "Pikar-AI needs additional permissions to read your inbox" with a re-authorize button.
- The re-authorize button triggers `signInWithOAuth` with the expanded scopes and `prompt: 'consent'`.

**4. Token refresh handling:**
- Access tokens expire after ~1 hour. The credential helper must use the refresh token to obtain new access tokens automatically.
- If the refresh token itself is revoked (user revokes access in Google account), mark the user's triage as `paused` and notify them to re-authorize.

---

## Section 2: AI Email Triage System

### New Service: `app/services/email_triage_service.py`

#### Classification Engine

For each email, the AI assigns:

| Field | Values |
|-------|--------|
| **Priority** | `urgent` / `important` / `normal` / `low` |
| **Action type** | `needs_reply` / `needs_review` / `fyi` / `auto_handle` / `spam` |
| **Category** | `meeting` / `deal` / `task` / `report` / `personal` / `newsletter` / `notification` |
| **Confidence** | 0.0 - 1.0 (below 0.85 → always routes to human) |

#### Classification Signals

- Sender importance (VIP contacts, known clients, investors — learned over time)
- Subject urgency keywords + patterns
- Thread context (is this a follow-up the user hasn't replied to?)
- Time sensitivity (contains dates, deadlines, "ASAP")
- Email type detection (automated notification vs. human-written)

#### Draft Reply Generation

For `needs_reply` emails:
- AI generates a draft reply using email thread context + user's past writing style
- Each draft has a `confidence` score — high confidence drafts get one-click approve, low confidence open an editor
- Drafts reference relevant Pikar-AI data when helpful (e.g., calendar context)

#### Auto-Act Rules

For `auto_handle` emails with confidence >= 0.85:

| Email Type | Auto-Action |
|-----------|-------------|
| Meeting confirmations | Auto-reply "confirmed," add to calendar |
| Newsletters / notifications | Archive, surface in FYI section |
| FYI emails from teammates | Mark read, brief summary only |

User can configure: "always auto-handle from [type/sender]" or "never auto-handle."

### Database Table: `email_triage`

```sql
CREATE TABLE email_triage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    gmail_message_id TEXT NOT NULL,
    thread_id TEXT,

    -- Email metadata
    sender TEXT NOT NULL,
    sender_name TEXT,
    subject TEXT,
    snippet TEXT,
    received_at TIMESTAMPTZ,

    -- AI classification
    priority TEXT NOT NULL CHECK (priority IN ('urgent', 'important', 'normal', 'low')),
    action_type TEXT NOT NULL CHECK (action_type IN ('needs_reply', 'needs_review', 'fyi', 'auto_handle', 'spam')),
    category TEXT CHECK (category IN ('meeting', 'deal', 'task', 'report', 'personal', 'newsletter', 'notification')),
    confidence FLOAT NOT NULL,
    classification_reasoning TEXT,

    -- Draft response
    draft_reply TEXT,
    draft_confidence FLOAT,

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'sent', 'dismissed', 'auto_handled')),
    auto_action_taken TEXT,
    user_action TEXT,
    acted_at TIMESTAMPTZ,

    -- Briefing association
    briefing_date DATE NOT NULL DEFAULT CURRENT_DATE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(user_id, gmail_message_id)
);

CREATE INDEX idx_email_triage_user_date ON email_triage(user_id, briefing_date);
CREATE INDEX idx_email_triage_status ON email_triage(user_id, status);
CREATE INDEX idx_email_triage_gmail_id ON email_triage(gmail_message_id);
```

RLS policies:

```sql
ALTER TABLE email_triage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own triage items"
    ON email_triage FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own triage items"
    ON email_triage FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Service role has full access to email_triage"
    ON email_triage FOR ALL
    USING (auth.role() = 'service_role');

-- Enable realtime for frontend live updates
ALTER PUBLICATION supabase_realtime ADD TABLE email_triage;

-- Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_email_triage_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER email_triage_updated_at
    BEFORE UPDATE ON email_triage
    FOR EACH ROW
    EXECUTE FUNCTION update_email_triage_updated_at();
```

### Background Worker: `app/services/email_triage_worker.py`

**Execution model:** Cloud Scheduler-triggered HTTP endpoint, following the pattern in `app/services/scheduled_endpoints.py`. A scheduled endpoint (`POST /scheduled/triage-tick`) is secured by `X-Scheduler-Secret` header, following the existing `/scheduled/*` convention. When triggered:

1. Queries `user_briefing_preferences` for all users with email triage enabled
2. For each user, fetches their stored refresh token from `auth.sessions` via service role
3. Processes each user's inbox independently — one user's failure does not block others
4. Runs every **30 minutes** via Cloud Scheduler (configurable globally; per-user frequency is a Phase 2 enhancement)

**Per-user processing:**
- Fetches new unread emails since last check
- Deduplicates against `email_triage` by `gmail_message_id`
- Runs AI classification + draft generation in batch
- Executes auto-act for high-confidence `auto_handle` items
- Sends notification for new `urgent` items
- Records all actions in `email_triage` table

### Gmail API Rate Limiting

Follow the existing codebase retry strategy (5 attempts, exponential backoff, 2s initial, 2x multiplier, 60s max):

| Concern | Strategy |
|---------|----------|
| Per-user batch size | Max 50 messages per triage run |
| 429 rate limit errors | Exponential backoff per existing `RETRY_OPTIONS` in `app/agents/shared.py` |
| 403 insufficient permissions | Mark user triage as `paused`, send notification to re-authorize |
| 401 token expired | Attempt refresh; if refresh fails, pause and notify |
| Per-user isolation | Each user processed in a try/except — one failure logged and skipped |
| Daily quota awareness | Track API calls per user per day; pause triage if approaching Gmail daily limit (10,000 queries/day) |

### Trust & Safety Guardrails

| Guardrail | Rule |
|-----------|------|
| Confidence threshold | Auto-act never touches emails with confidence < 0.85 |
| Daily cap | Auto-replies capped at 10 per day initially |
| Reversibility | All auto-actions are logged and reversible (email stays in Gmail) |
| User control | Auto-act can be disabled entirely or per-category |
| Shadow mode | First week shows what AI *would* do but doesn't act. User must explicitly enable auto-act after reviewing shadow results. |

---

## Section 3: Daily Briefing Widget — Frontend

### Component: `DailyBriefingWidget.tsx`

Placed at the top of the main dashboard — the first thing users see.

#### Layout: Four Sections

**1. Header Bar**
- "Good morning, [Name]" with today's date
- Freshness indicator: "Updated 5 min ago" + refresh button
- Quick stats: `3 urgent` · `7 need reply` · `4 auto-handled` · `12 FYI`

**2. Urgent & Needs Reply Queue** (primary section)
- Card per email: sender avatar, name, subject, snippet, time, priority badge, category pill
- Expand inline to reveal:
  - Full email preview
  - AI-drafted reply (editable textarea)
  - Actions: **Approve & Send** | **Edit & Send** | **Dismiss**
  - Collapsible "Why this classification?" with AI reasoning
- Batch action: "Approve all high-confidence drafts" (confidence > 0.9)

**3. Auto-Handled Log** (collapsible, collapsed by default)
- Each row: sender, subject, action taken
- Undo button per row
- Shadow mode variant: "Would have done: ..." with approve/reject to train preferences

**4. FYI Section** (collapsible)
- Low-priority emails summarized in 1-2 lines
- Grouped by category
- "Mark all read" action

#### Interaction Patterns

- **Keyboard:** `j/k` navigate, `a` approve, `e` edit, `d` dismiss
- **Mobile swipe:** right to approve, left to dismiss
- **Optimistic updates:** card slides out on approve, send happens async
- **Empty state:** "Inbox zero — nothing needs your attention"

#### Real-Time Updates

- Supabase realtime subscription on `email_triage` table
- New items from background worker appear live
- Urgent items get pulse animation + notification bell badge

#### Chat Integration

- "Discuss in chat" button on any email → opens chat with email context pre-loaded
- "Brief me" in chat → AI narrates from `email_triage` data

---

## Section 4: Notification & Email Delivery Channels

### Email Briefing Digest

**New Service: `app/services/briefing_digest_service.py`**

- Runs at user's configured time (default 7 AM in their timezone)
- HTML email: urgent items, draft count, auto-handled summary, CTA to dashboard
- Uses existing `GmailService.send_email()`
- Frequency options: daily, weekday-only, off

### In-App Notifications

Uses existing `NotificationService` + Supabase realtime:

| Event | Notification |
|-------|-------------|
| Morning briefing ready | "Your daily briefing is ready — 3 urgent items" |
| New urgent email mid-day | "Urgent from [sender]: [subject]" with Review action |
| Auto-act confirmation | "I replied to [sender] confirming your meeting" with Undo |
| Afternoon nudge | "You have 3 unanswered drafts from this morning" |

### Notification Center UI: `NotificationCenter.tsx`

- Bell icon in top nav with unread badge
- Dropdown panel: recent notifications grouped by type
- Each notification: icon, title, message, timestamp, action button
- "Mark all read" + "View all" link
- Connects to existing `notifications` table via Supabase realtime

### User Preferences Table: `user_briefing_preferences`

```sql
CREATE TABLE user_briefing_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    briefing_time TIME NOT NULL DEFAULT '07:00',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    email_digest_enabled BOOLEAN NOT NULL DEFAULT true,
    email_digest_frequency TEXT NOT NULL DEFAULT 'daily' CHECK (email_digest_frequency IN ('daily', 'weekdays', 'off')),
    auto_act_enabled BOOLEAN NOT NULL DEFAULT false,
    auto_act_daily_cap INTEGER NOT NULL DEFAULT 10,
    auto_act_categories TEXT[] DEFAULT '{}',
    vip_senders TEXT[] DEFAULT '{}',
    ignored_senders TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

```sql
ALTER TABLE user_briefing_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own preferences"
    ON user_briefing_preferences FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own preferences"
    ON user_briefing_preferences FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own preferences"
    ON user_briefing_preferences FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role has full access to briefing preferences"
    ON user_briefing_preferences FOR ALL
    USING (auth.role() = 'service_role');

-- Auto-update updated_at
CREATE TRIGGER briefing_preferences_updated_at
    BEFORE UPDATE ON user_briefing_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_email_triage_updated_at();
```

`auto_act_categories` allowed values correspond exactly to the `email_triage.category` enum: `meeting`, `deal`, `task`, `report`, `personal`, `newsletter`, `notification`. Application-layer validation enforces this.

Settings page in frontend for user configuration. Sensible defaults = works without configuration.

---

## Section 5: Agent Architecture & Integration

### Agent Ownership

The **ExecutiveAgent** (`app/agent.py`) owns the daily briefing. Rationale: briefing is fundamentally an executive function — triaging, prioritizing, delegating. It extends the "chief of staff" persona already established.

### New Tools Added to ExecutiveAgent

| Tool Group | Tools |
|-----------|-------|
| `GMAIL_INBOX_TOOLS` | read_inbox, read_email, classify_email, archive_email, label_email |
| `BRIEFING_TOOLS` | get_daily_briefing, refresh_briefing, approve_draft, dismiss_item, undo_auto_action |

### ExecutiveAgent Instruction Additions

- **Proactive briefing:** When user opens chat or says "good morning" / "brief me" / "what's happening," pull from `email_triage` and present conversationally
- **Draft reply persona:** Match user's writing style, keep replies concise, never commit to anything unauthorized

### Cross-Agent Data Flow

```
Email Triage Worker
    → category: "deal" → Sales Agent can reference
    → category: "meeting" → Calendar tools can act
    → category: "task" → Task service can create follow-up
```

Cross-referencing is Phase 3 territory, but the `category` field in `email_triage` supports it from day one.

### New Tool Module: `app/agents/tools/briefing_tools.py`

Contains the `BRIEFING_TOOLS` list exported for use in `app/agent.py`. These tools wrap the same service methods that the API endpoints call — single service layer, two access paths (agent tools for chat, API for frontend).

### API Endpoints — Extend Existing `app/routers/briefing.py`

The briefing router already exists with endpoints at `/briefing` and `/briefing/dashboard-summary`. New endpoints are added to the same router, following the existing path convention (no `/api/` prefix):

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/briefing/today` | Current day's triage items grouped by section |
| `POST` | `/briefing/refresh` | Trigger on-demand triage refresh |
| `PATCH` | `/briefing/items/{id}/approve` | Approve and send drafted reply |
| `PATCH` | `/briefing/items/{id}/dismiss` | Dismiss an item |
| `PATCH` | `/briefing/items/{id}/undo` | Undo an auto-action |
| `GET` | `/briefing/preferences` | Get user preferences |
| `PUT` | `/briefing/preferences` | Update user preferences |
| `GET` | `/briefing/history` | Past briefings for review |

All endpoints user-scoped via JWT auth and RLS.

---

## Section 6: Implementation Phases & Build Order

### Phase 1A: Gmail Reading Foundation (backend)

1. Extend `GmailService` with read methods
2. Create `gmail_inbox.py` tool module
3. Update OAuth scopes
4. Add tools to ExecutiveAgent
5. **Milestone:** "read my inbox" works in chat

### Phase 1B: Triage Engine (backend)

1. Create `email_triage` migration
2. Build `EmailTriageService` — classification + draft generation
3. Build auto-act rule engine with safety guardrails
4. Build `EmailTriageWorker` — 30-min polling background job
5. **Milestone:** Worker classifies emails, stores in DB, shadow mode works

### Phase 1C: Briefing API (backend)

1. Create `user_briefing_preferences` migration
2. Build `briefing.py` router
3. Build `BriefingDigestService` for email delivery
4. Wire notifications for urgent items and auto-act confirmations
5. **Milestone:** `GET /briefing/today` returns structured briefing JSON

### Phase 1D: Frontend (dashboard + notifications)

1. Build `NotificationCenter.tsx`
2. Build `DailyBriefingWidget.tsx` — all sections, approval flow, keyboard shortcuts
3. Build briefing preferences settings page
4. Wire Supabase realtime for live updates
5. Integrate "discuss in chat" flow
6. **Milestone:** Full briefing experience end-to-end

### Phase 1E: Polish & Safety

1. Shadow mode → live transition flow
2. VIP sender learning
3. Email digest tested across clients
4. Gmail API quota rate limiting and error handling
5. **Milestone:** Stable for daily use over one week

### Dependency Chain

```
1A → 1B → 1C → 1D
                → 1E
```

1D can start UI scaffolding in parallel once the API contract from 1C is defined.

---

## Files to Create

| File | Type |
|------|------|
| `app/agents/tools/gmail_inbox.py` | New tool module — GMAIL_INBOX_TOOLS |
| `app/agents/tools/briefing_tools.py` | New tool module — BRIEFING_TOOLS |
| `app/services/email_triage_service.py` | New service — classification engine + draft generation |
| `app/services/email_triage_worker.py` | New scheduled endpoint — Cloud Scheduler-triggered triage |
| `app/services/briefing_digest_service.py` | New service — email digest delivery |
| `supabase/migrations/XXXXXXXX_email_triage.sql` | New migration — email_triage table, RLS, realtime, triggers |
| `supabase/migrations/XXXXXXXX_user_briefing_preferences.sql` | New migration — preferences table, RLS, triggers |
| `frontend/src/components/widgets/DailyBriefingWidget.tsx` | New widget |
| `frontend/src/components/NotificationCenter.tsx` | New component — bell icon + dropdown panel |
| `frontend/src/app/settings/briefing/page.tsx` | New settings page |

## Files to Modify

| File | Change |
|------|--------|
| `app/integrations/google/gmail.py` | Add `list_messages()`, `get_message()`, `batch_get_messages()`, `modify_message()` |
| `app/integrations/google/client.py` | Add `get_user_gmail_credentials(user_id)` helper with refresh token support |
| `app/agent.py` | Add GMAIL_INBOX_TOOLS + BRIEFING_TOOLS to ExecutiveAgent |
| `app/routers/briefing.py` | Add triage endpoints (`/briefing/today`, `/briefing/items/{id}/approve`, etc.) to existing router |
| `app/fast_api_app.py` | Register triage scheduled endpoint |
| `app/agents/tools/registry.py` | Register GMAIL_INBOX_TOOLS + BRIEFING_TOOLS for workflow engine access |
| `frontend/src/services/auth.ts` | Add `access_type: 'offline'`, `prompt: 'consent'`, and Gmail scopes to OAuth call |
| Dashboard layout (persona-specific layouts in `src/app/(personas)/`) | Add DailyBriefingWidget at top |
| Top nav layout component | Add NotificationCenter bell icon |

---

## Testing Strategy

| Layer | Test Approach |
|-------|---------------|
| Classification logic | Unit tests: given email metadata, assert correct priority/action_type/category. Test edge cases: empty body, non-English, very long threads. |
| Draft generation | Unit tests: given email + context, assert draft is relevant and concise. Test persona matching. |
| Auto-act safety | Unit tests: verify confidence < 0.85 never auto-acts, daily cap enforced, shadow mode blocks real sends. |
| Triage worker | Integration tests with mocked Gmail API: verify dedup, batch processing, per-user isolation, error handling. |
| Briefing API | Integration tests: verify endpoints return correct triage groupings, approve/dismiss/undo state transitions. |
| OAuth token handling | Integration tests: verify refresh token flow, scope detection, re-authorization trigger. |
| Frontend widget | Component tests: render with mock data, verify approve/dismiss interactions, keyboard shortcuts, empty state. |
| End-to-end | Staging test: connect a test Gmail account, verify full flow from email arrival to briefing display to draft approval. |
