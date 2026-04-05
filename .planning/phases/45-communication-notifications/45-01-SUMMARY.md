---
phase: 45-communication-notifications
plan: 01
subsystem: api
tags: [slack, teams, notifications, block-kit, adaptive-cards, webhooks, redis, supabase]

# Dependency graph
requires:
  - phase: 39-integration-platform
    provides: IntegrationManager.get_valid_token for Slack OAuth token retrieval
  - phase: 39-integration-platform
    provides: integration_credentials table where Teams webhook URL is stored

provides:
  - SlackNotificationService with Block Kit rich formatting and approval buttons
  - TeamsNotificationService with Adaptive Card 1.2 and Action.OpenUrl
  - NotificationDispatcher fan-out with Redis dedup and notification_rules routing
  - notification_rules and notification_channel_config tables with RLS

affects:
  - 45-02 (NotificationRuleService builds on notification_rules table)
  - 45-03 (router layer calls dispatch_notification)
  - approval workflows (Slack approval buttons route to approval_requests)

# Tech tracking
tech-stack:
  added:
    - slack-sdk (AsyncWebClient, lazy import)
    - httpx (already present, used for Teams webhook POSTs)
  patterns:
    - Lazy import pattern for optional SDK dependencies (slack_sdk inside try block)
    - sys.modules fake SDK injection in tests for lazily-imported libraries
    - Redis dedup key: pikar:notif:sent:{user_id}:{event_type}:{payload_hash} 60s TTL
    - Teams uses incoming webhook URL (api_key model), not OAuth token exchange
    - Slack bot token resolved per-call via IntegrationManager.get_valid_token

key-files:
  created:
    - app/services/slack_notification_service.py
    - app/services/teams_notification_service.py
    - app/services/notification_dispatcher.py
    - supabase/migrations/20260405970000_notification_rules.sql
    - tests/unit/services/test_slack_notification_service.py
    - tests/unit/services/test_teams_notification_service.py
    - tests/unit/services/test_notification_rule_service.py
  modified:
    - app/config/integration_providers.py

key-decisions:
  - "Teams provider uses api_key auth_type with no OAuth URLs — incoming webhook URL model (user pastes URL, no token exchange)"
  - "Slack gains chat:write.public scope to post to public channels without being a member"
  - "sys.modules fake SDK injection for slack_sdk in tests — library not installed, lazy import means standard patch target unavailable"
  - "NotificationDispatcher lazy-imports SlackNotificationService and TeamsNotificationService inside methods to prevent circular imports"
  - "Teams Action.OpenUrl (not Action.Submit) for approvals — incoming webhooks cannot handle interactive responses"
  - "Redis dedup uses payload hash (first 16 hex chars) with 60s TTL to prevent duplicate delivery on rapid-fire events"

patterns-established:
  - "Lazy SDK imports: optional third-party SDKs imported inside async method try blocks, not at module level"
  - "Test fake SDK: sys.modules injection for lazily-imported SDKs that are not installed in dev/test environment"
  - "Provider fan-out: dispatcher queries notification_rules, iterates rules, catches per-provider failures independently"

requirements-completed: [NOTIF-01, NOTIF-02, NOTIF-06]

# Metrics
duration: 17min
completed: 2026-04-05
---

# Phase 45 Plan 01: Notification Infrastructure Summary

**Slack Block Kit service with approval buttons, Teams Adaptive Card 1.2 service with Action.OpenUrl, and a Redis-deduped dispatcher routing events via notification_rules — foundation for all notification delivery.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-04-05T14:27:05Z
- **Completed:** 2026-04-05T14:44:00Z
- **Tasks:** 3 (Task 0, Task 1, Task 2)
- **Files modified:** 8

## Accomplishments

- Wave 0 test stubs: 17 pytest-asyncio stubs across 3 test files, all collected and skipped (behavioral harness ready)
- Database: `notification_rules` and `notification_channel_config` tables with RLS policies, indexes, and moddatetime triggers
- SlackNotificationService: Block Kit event notifications, approval buttons (primary/danger styles with APPROVED/REJECTED values), daily briefing blocks, channel listing — all via lazy AsyncWebClient
- TeamsNotificationService: Adaptive Card 1.2 notifications, ColumnSet briefing layout, Action.OpenUrl for approvals, HTTP 429 handling
- NotificationDispatcher: queries `notification_rules`, fans out to both providers, Redis 60s dedup, per-provider failure isolation
- Slack and Teams test stubs upgraded to 11 fully passing assertions

## Task Commits

Each task was committed atomically:

1. **Task 0: Wave 0 test stubs** - `652be2c` (test)
2. **Task 1: Migration and provider registry** - `d10292a` (feat)
3. **Task 2: Slack, Teams, and Dispatcher services** - `7e5bd13` (feat)

**Plan metadata:** _(to be committed)_

## Files Created/Modified

- `app/services/slack_notification_service.py` — SlackNotificationService: Block Kit, approval buttons, daily briefing, channel listing
- `app/services/teams_notification_service.py` — TeamsNotificationService: Adaptive Card 1.2, Action.OpenUrl, 429 handling
- `app/services/notification_dispatcher.py` — Fan-out dispatcher with Redis dedup and notification_rules routing
- `supabase/migrations/20260405970000_notification_rules.sql` — notification_rules + notification_channel_config tables with RLS
- `app/config/integration_providers.py` — Slack gains chat:write.public; Teams switches to api_key auth model
- `tests/unit/services/test_slack_notification_service.py` — 6 tests, all passing
- `tests/unit/services/test_teams_notification_service.py` — 5 tests, all passing
- `tests/unit/services/test_notification_rule_service.py` — 6 stubs, all skipped (Wave 0, service in Plan 02)

## Decisions Made

- Teams uses `api_key` auth_type with empty OAuth URLs — the incoming webhook URL is stored as `account_name` in `integration_credentials`, no token exchange needed
- Slack receives `chat:write.public` scope so the bot can post to public channels it hasn't joined
- `Action.OpenUrl` (not `Action.Submit`) for Teams approval cards — incoming webhooks are fire-and-forget, they cannot receive interactive response payloads
- `sys.modules` injection for slack_sdk in tests — the library is not installed in the dev environment, and lazy imports inside method bodies cannot be patched at the module namespace level
- Lazy imports for both SlackNotificationService and TeamsNotificationService inside `NotificationDispatcher` delivery methods to avoid circular import chains

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed import patch strategy for lazily-imported slack_sdk**
- **Found during:** Task 2 (test implementation)
- **Issue:** `slack_sdk` is not installed in the project's virtual environment. The lazy import inside the service method body means `app.services.slack_notification_service.AsyncWebClient` does not exist as a module attribute — standard `patch()` target fails with `AttributeError`.
- **Fix:** Used `sys.modules` fake SDK injection (`_install_fake_slack_sdk`) in tests. Patched `_resolve_token` directly via `patch.object` for token control. Removed dependency on `slack_sdk` being installed.
- **Files modified:** `tests/unit/services/test_slack_notification_service.py`
- **Verification:** 6 Slack tests pass without `slack_sdk` installed
- **Committed in:** `7e5bd13` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — test infrastructure bug)
**Impact on plan:** Fix was necessary for tests to run at all. No scope creep, no behavioral changes.

## Issues Encountered

- `ruff --select E,W,F,I,N,D,UP,B` on service files produced D413 (missing blank line after last section) and I001 (unsorted imports inside lazy try blocks) — all fixed with `--fix` flag. One D401 (imperative mood) required manual docstring wording change.
- E501 (line too long) reported on test files by `--select E` but globally ignored in `pyproject.toml` — not a real failure.

## User Setup Required

External Slack service requires manual configuration before notifications can be sent. See plan frontmatter `user_setup` for:
- Create Slack App with Bot Token Scopes: `channels:read`, `chat:write`, `chat:write.public`, `users:read`
- Set `SLACK_CLIENT_ID`, `SLACK_CLIENT_SECRET`, `SLACK_SIGNING_SECRET` environment variables
- Enable Interactivity and set Request URL to `{APP_URL}/webhooks/slack/interact`
- Set OAuth Redirect URL to `{APP_URL}/integrations/slack/callback`

Teams requires no app registration — users paste an incoming webhook URL into the integration settings.

## Next Phase Readiness

- Plan 02: `NotificationRuleService` CRUD layer (the 6 rule-service test stubs are ready and waiting)
- Plan 02 can import `dispatch_notification` from `notification_dispatcher` immediately
- `notification_rules` and `notification_channel_config` tables exist in migration; Plan 02 just needs the service class
- Slack approval button action_ids (`approval_approve`, `approval_reject`) need a webhook handler in Plan 03

---
*Phase: 45-communication-notifications*
*Completed: 2026-04-05*

## Self-Check: PASSED

All 9 expected files found on disk. All 3 task commits (652be2c, d10292a, 7e5bd13) verified in git log.
