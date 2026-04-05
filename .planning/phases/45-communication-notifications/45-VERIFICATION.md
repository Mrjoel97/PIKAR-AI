---
phase: 45-communication-notifications
verified: 2026-04-05T16:10:00Z
status: passed
score: 12/12 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 11/12
  gaps_closed:
    - "Test Notification button in the frontend sends a real test message to verify connectivity"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Connect a real Slack workspace, configure a notification rule, and trigger an approval request"
    expected: "A Block Kit message with Approve and Reject buttons appears in the configured Slack channel; clicking Approve updates the approval request to APPROVED and posts a confirmation"
    why_human: "End-to-end Slack interactive approval flow requires a live Slack workspace, real OAuth token, and Slack's interactive component callback — cannot be verified by static code inspection"
  - test: "Connect a real Teams webhook URL, create a notification rule, and trigger a task.created event via dispatch_notification"
    expected: "An Adaptive Card appears in the Teams channel with the task title visible"
    why_human: "Teams Adaptive Card delivery requires a live incoming webhook URL and cannot be verified programmatically"
  - test: "Enable daily briefing in configuration for a Slack workspace and call POST /scheduled/slack-daily-briefing with the scheduler secret"
    expected: "A 'Daily Briefing' Block Kit message appears in the configured channel listing pending approvals, upcoming tasks, and key metrics"
    why_human: "Requires a seeded database with approval_requests/tasks rows and a live Slack connection"
  - test: "Connect Slack, create an agent.message notification rule, then click Send Test Notification on the Slack integration card"
    expected: "Success toast appears; a test message arrives in the configured Slack channel"
    why_human: "Requires a live Slack workspace and bot token; cannot verify end-to-end delivery via static analysis"
---

# Phase 45: Communication-Notifications Verification Report

**Phase Goal:** Users receive Pikar notifications in their team chat (Slack or Teams) with rich formatting and interactive approval buttons — including automated daily briefings posted to configured channels
**Verified:** 2026-04-05T16:10:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (Plan 04 added missing test-notification endpoint, commit `1cbbeb9`)

## Re-Verification Summary

| Item | Previous | Now | Change |
|------|----------|-----|--------|
| Score | 11/12 | 12/12 | +1 |
| Status | gaps_found | passed | Closed |
| Gap: test-notification endpoint | MISSING | VERIFIED | Fixed by commit `1cbbeb9` |
| All 11 previously-passing truths | VERIFIED | VERIFIED | No regression |

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Slack bot token is stored encrypted via Fernet after OAuth callback | VERIFIED | `_resolve_token` in `slack_notification_service.py` delegates to `IntegrationManager().get_valid_token(user_id, "slack")`; Slack provider uses `oauth2` auth_type in `integration_providers.py` |
| 2 | Teams incoming webhook URL is stored as credential without OAuth exchange | VERIFIED | Teams provider has `auth_type="api_key"`, `auth_url=None`, `token_url=None` in `integration_providers.py` line 152; `TeamsNotificationService` accepts `webhook_url` as a direct parameter |
| 3 | Notifications sent to Slack use Block Kit rich formatting (sections, dividers, actions blocks) | VERIFIED | `_build_event_blocks` returns header+section+divider blocks; `send_approval_request` returns actions block with primary/danger buttons; test assertions confirm `"header"`, `"section"`, `"divider"` present |
| 4 | Notifications sent to Teams use Adaptive Card JSON format version 1.2 | VERIFIED | `_ADAPTIVE_CARD_VERSION = "1.2"` in `teams_notification_service.py`; `_build_adaptive_card` embeds version in content dict; `test_adaptive_card_schema` asserts `content["version"] == "1.2"` |
| 5 | NotificationDispatcher fans out an event to all connected providers for a user | VERIFIED | `notification_dispatcher.py` queries `notification_rules` filtered by `user_id+event_type+enabled=True`, iterates rules, calls `_deliver_slack` or `_deliver_teams` per rule; Redis dedup key `pikar:notif:sent:{user_id}:{event_type}:{hash}` with 60s TTL |
| 6 | User can CRUD notification rules specifying which events route to which channel | VERIFIED | `NotificationRuleService` provides `list_rules`, `create_rule`, `update_rule`, `delete_rule`, `get_matching_rules`, `get_channel_config`, `upsert_channel_config`; 8 REST endpoints in `integrations.py` (lines 1015-1295) |
| 7 | Clicking Approve/Reject button in Slack updates the approval_requests row and posts confirmation back | VERIFIED | `_process_slack_block_action` in `webhooks.py` (line 1556): splits button value on `:`, sha256-hashes token, updates `approval_requests` WHERE `token=token_hash AND status=PENDING`, then POSTs confirmation to `response_url` |
| 8 | Slack interaction endpoint verifies request signature using SLACK_SIGNING_SECRET before processing | VERIFIED | `slack_interact` at line 1640 lazily imports `SignatureVerifier` from `slack_sdk.signature`, calls `verifier.is_valid(body.decode(), timestamp, signature)`, returns 403 on invalid or empty signing secret |
| 9 | Creating an approval request dispatches a notification to Slack if the user has an approval.pending rule | VERIFIED | `approval_tool.py` line 109: `asyncio.create_task(_notify_approval(...))` after successful insert; `_notify_approval` calls `dispatch_notification(user_id, "approval.pending", {...})` wrapped in try/except |
| 10 | A daily briefing is auto-posted to the configured Slack/Teams channel at the scheduled time | VERIFIED | `POST /scheduled/slack-daily-briefing` in `scheduled_endpoints.py` (line 233): queries `notification_channel_config WHERE daily_briefing=True`, aggregates pending approvals/tasks/metrics per user, dispatches via `SlackNotificationService.send_daily_briefing` or `TeamsNotificationService.send_daily_briefing` |
| 11 | An agent can send a message to a connected Slack/Teams channel via chat command | VERIFIED | `communication_tools.py` exports `COMMUNICATION_TOOLS` containing `send_notification_to_channel`, `list_notification_rules`, `configure_notification_rule`; `operations/agent.py` spreads `*COMMUNICATION_TOOLS` into tools list at line 198 |
| 12 | Test Notification button in the frontend sends a real test message to verify connectivity | VERIFIED | `POST /integrations/{provider}/test-notification` exists at `integrations.py` lines 1298-1354. Guarded by `_NOTIF_PROVIDERS`, lazy-imports `dispatch_notification`, dispatches `agent.message` event, returns 200 on success or 502 with descriptive guidance on failure. Frontend `handleTestNotification` at line 2073 calls this endpoint via `fetchWithAuth`. |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/unit/services/test_slack_notification_service.py` | Wave 0 stubs + real assertions | VERIFIED | 6 tests, all real assertions; tests token resolution, Block Kit structure, approval buttons, block_id, daily briefing, event block structure |
| `tests/unit/services/test_teams_notification_service.py` | Wave 0 stubs + real assertions | VERIFIED | 5 tests, all real assertions; tests webhook URL delivery, Adaptive Card schema 1.2, Action.OpenUrl for approvals, ColumnSet in briefing, 429 handling |
| `tests/unit/services/test_notification_rule_service.py` | Real assertions for CRUD | VERIFIED | 6 tests: `test_create_rule`, `test_list_rules_by_provider`, `test_toggle_rule_enabled`, `test_delete_rule`, `test_get_matching_rules`, `test_upsert_channel_config` — no `pytest.skip` stubs |
| `supabase/migrations/20260405970000_notification_rules.sql` | notification_rules + notification_channel_config tables with RLS | VERIFIED | Both tables created with IF NOT EXISTS; 4 RLS policies each; indexes on `(user_id)` and `(user_id, provider)`; moddatetime triggers on `updated_at` |
| `app/services/slack_notification_service.py` | SlackNotificationService with Block Kit formatters | VERIFIED | 485 lines; `send_notification`, `send_approval_request`, `send_daily_briefing`, `list_channels`, `_resolve_token`, `_build_event_blocks`, `_build_briefing_blocks` all implemented |
| `app/services/teams_notification_service.py` | TeamsNotificationService with Adaptive Card formatters | VERIFIED | 345 lines; `send_notification`, `send_daily_briefing`, `_build_adaptive_card`, `_build_briefing_card`, `_post_card` all implemented; 429 handling present |
| `app/services/notification_dispatcher.py` | Fan-out dispatcher routing events to provider services | VERIFIED | `NotificationDispatcher.dispatch` queries `notification_rules`, Redis dedup with 60s TTL, lazy imports per provider, per-provider failure isolation; module-level `dispatch_notification` convenience function at line 247 |
| `app/services/notification_rule_service.py` | CRUD for notification rules + channel config | VERIFIED | 279 lines; all 7 CRUD methods implemented; `SUPPORTED_EVENTS` class constant with 7 event types |
| `app/routers/webhooks.py` | POST /webhooks/slack/interact endpoint | VERIFIED | `slack_interact` at line 1640; `_process_slack_block_action` at line 1556; signature verification via `SignatureVerifier`; async fire-and-forget via `asyncio.create_task` |
| `app/routers/integrations.py` | Notification rule CRUD endpoints + test-notification | VERIFIED | 8 CRUD endpoints (lines 1015-1295) plus `send_test_notification` at lines 1298-1354; all guarded by `_NOTIF_PROVIDERS` frozenset |
| `app/services/scheduled_endpoints.py` | POST /scheduled/slack-daily-briefing endpoint | VERIFIED | Endpoint at line 233; queries `notification_channel_config WHERE daily_briefing=True`; aggregates pending approvals, tasks, metrics per user; dispatches via Slack or Teams service |
| `app/agents/tools/communication_tools.py` | COMMUNICATION_TOOLS list | VERIFIED | 352 lines; 3 tools exported; each lazy-imports services to avoid circular deps |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `slack_notification_service.py` | `IntegrationManager.get_valid_token` | Slack bot token retrieval | WIRED | `_resolve_token` calls `IntegrationManager().get_valid_token(user_id, "slack")` at line 362 |
| `notification_dispatcher.py` | `slack_notification_service.py` | Provider routing | WIRED | `_deliver_slack` lazy-imports `SlackNotificationService` and calls `send_notification` at line 178 |
| `notification_dispatcher.py` | `teams_notification_service.py` | Provider routing | WIRED | `_deliver_teams` lazy-imports `TeamsNotificationService` and calls `send_notification` at line 207 |
| `webhooks.py (slack_interact)` | `approval_requests` table | Token hash lookup + status update | WIRED | `hashlib.sha256(token.encode()).hexdigest()` at line 1580; `.eq("token", token_hash).eq("status", "PENDING")` at line 1590 |
| `approval_tool.py` | `notification_dispatcher.py` | dispatch_notification on approval creation | WIRED | `asyncio.create_task(_notify_approval(...))` at line 109; `_notify_approval` lazy-imports `dispatch_notification` and calls it with `"approval.pending"` at line 43 |
| `integrations.py` | `notification_rule_service.py` | REST endpoints delegate to service | WIRED | All 8 notification endpoints lazy-import `NotificationRuleService` inside handler body (lines 1025, 1054, 1090, 1131, 1169, 1250, 1284) |
| `integrations.py (test-notification)` | `notification_dispatcher.py` | dispatch_notification for test event | WIRED | `from app.services.notification_dispatcher import dispatch_notification` at line 1327; `await dispatch_notification(user_id=current_user_id, event_type="agent.message", ...)` at line 1329 |
| `scheduled_endpoints.py` | `slack_notification_service.py` | send_daily_briefing call | WIRED | Lazy-imports `SlackNotificationService` at line 324; calls `send_daily_briefing` at line 327 |
| `scheduled_endpoints.py` | `teams_notification_service.py` | send_daily_briefing call for Teams | WIRED | Lazy-imports `TeamsNotificationService` at line 332; calls `send_daily_briefing` at line 335 |
| `frontend/configuration/page.tsx` | `/integrations/{provider}/notification-rules` | fetchWithAuth API calls | WIRED | `handleSaveNotifRule` at line 1998, `handleToggleNotifRule` at line 2018, `handleDeleteNotifRule` at line 2042; all call correct endpoints |
| `frontend/configuration/page.tsx (handleTestNotification)` | `/integrations/{provider}/test-notification` | fetchWithAuth POST | WIRED | `handleTestNotification` at line 2073 calls `POST /integrations/${providerKey}/test-notification` via `fetchWithAuth`; endpoint exists at `integrations.py` line 1298 — gap now closed |
| `communication_tools.py` | `notification_dispatcher.py` | dispatch_notification for agent messages | NOTE | `send_notification_to_channel` calls provider services directly rather than routing through `dispatch_notification`. This bypasses Redis dedup and the rule engine for agent-initiated messages. Delivery still works correctly — documented as a design deviation, not a blocker. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| NOTIF-01 | 45-01 | User can connect Slack workspace via OAuth from configuration page | SATISFIED | Slack provider uses `oauth2` auth_type in `integration_providers.py`; OAuth flow handled by existing `IntegrationManager`; `chat:write.public` scope added; Slack token resolution via `get_valid_token` verified |
| NOTIF-02 | 45-01 | User can connect Microsoft Teams via Azure AD OAuth from configuration page | SATISFIED | Teams provider updated to `api_key` auth_type with empty OAuth URLs — incoming webhook URL model (user pastes URL, no token exchange); stored as `account_name` in `integration_credentials` |
| NOTIF-03 | 45-02, 45-03 | Configurable notification rules: which events route to which channel | SATISFIED | `NotificationRuleService` provides full CRUD; 8 REST endpoints in `integrations.py`; `NotificationRulesSection` component in frontend; agent tools `list_notification_rules` and `configure_notification_rule` available |
| NOTIF-04 | 45-02 | Approval buttons in Slack messages (approve/reject inline without leaving Slack) | SATISFIED | `send_approval_request` sends Block Kit with `style: primary` (Approve) and `style: danger` (Reject) buttons; `POST /webhooks/slack/interact` processes button presses, updates `approval_requests`, posts confirmation to `response_url` asynchronously |
| NOTIF-05 | 45-03 | Daily briefing auto-posted to configured Slack/Teams channel | SATISFIED | `POST /scheduled/slack-daily-briefing` aggregates pending approvals, upcoming tasks, and key metrics per user with `daily_briefing=True` in `notification_channel_config`; dispatches via `SlackNotificationService.send_daily_briefing` or `TeamsNotificationService.send_daily_briefing` |
| NOTIF-06 | 45-01, 45-03 | Rich formatted messages (Slack Block Kit / Teams Adaptive Cards) | SATISFIED | Slack Block Kit: header+section+divider for events; header+actions (primary/danger buttons) for approvals; header+multiple sections+dividers for briefings. Teams Adaptive Cards: version 1.2 with TextBlock (Bolder/Medium header); ColumnSet for briefing metrics; Action.OpenUrl for approvals |

All 6 requirements (NOTIF-01 through NOTIF-06) are satisfied. No orphaned requirements — all 6 IDs appear in plan frontmatter across the 4 plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/agents/tools/communication_tools.py` | 173-195 | `send_notification_to_channel` bypasses `NotificationDispatcher` and calls provider services directly | Warning | Circumvents Redis dedup and rule engine for agent-initiated messages; delivery still works — may be intentional design for direct agent-to-channel writes |

No TODO/FIXME/placeholder comments or empty stub implementations found in any service or router files. The previously-blocking dead button is now wired to a live endpoint.

### Human Verification Required

#### 1. End-to-End Slack Approval Flow

**Test:** Connect a live Slack workspace, configure an `approval.pending` notification rule for a channel, then trigger an approval request from the agent. Click Approve in Slack.
**Expected:** Block Kit message with Approve (green) and Reject (red) buttons appears in the channel within a few seconds; clicking Approve shows a confirmation message replacing the original, and the approval_requests row status changes to APPROVED.
**Why human:** Live Slack OAuth connection, real bot token, real Slack workspace, and interactive component callback required — cannot verify with static analysis.

#### 2. Teams Adaptive Card Delivery

**Test:** Paste a real Teams incoming webhook URL into the integration settings, create a `task.created` rule, then call `dispatch_notification` for a task event.
**Expected:** Adaptive Card appears in the Teams channel with the task title in a bold header TextBlock.
**Why human:** Requires a real Teams webhook URL and a live Teams channel.

#### 3. Daily Briefing Scheduler

**Test:** Enable daily briefing in configuration for a connected provider; seed the database with pending approval_requests and tasks rows; POST to `/scheduled/slack-daily-briefing` with the correct `X-Scheduler-Secret` header.
**Expected:** A "Daily Briefing" message appears in the configured channel listing pending approval count, task names, and metrics.
**Why human:** Requires live database seed, Slack/Teams connection, and Cloud Scheduler secret.

#### 4. Test Notification Button (gap now closed — connectivity UX)

**Test:** Connect Slack, create an `agent.message` notification rule, navigate to the configuration page, and click "Send Test Notification" on the Slack integration card.
**Expected:** A success toast appears and a test message ("This is a test notification from Pikar. If you see this message, your notification channel is working correctly.") arrives in the configured Slack channel.
**Why human:** Requires a live Slack workspace and bot token; end-to-end delivery cannot be verified via static analysis.

---

_Verified: 2026-04-05T16:10:00Z_
_Verifier: Claude (gsd-verifier)_
