# Phase 45: Communication & Notifications - Research

**Researched:** 2026-04-05
**Domain:** Slack Bot API, Microsoft Teams Webhooks, notification routing, interactive approvals
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NOTIF-01 | User can connect Slack workspace via OAuth from configuration page | Slack OAuth v2 with `channels:read,chat:write,chat:write.public` bot scopes; existing `integrations/{provider}/authorize` flow reused; `slack` already in PROVIDER_REGISTRY |
| NOTIF-02 | User can connect Microsoft Teams via Azure AD OAuth from configuration page | Teams uses OAuth but interactive buttons via incoming webhooks (user-provided URL); hybrid model: OAuth for future Graph API, webhook URL stored as credential |
| NOTIF-03 | Configurable notification rules: which events route to which channel | `notification_rules` table (user_id, provider, event_type, channel_id); `NotificationRuleService` evaluates rules on event dispatch |
| NOTIF-04 | Approval buttons in Slack messages (approve/reject inline without leaving Slack) | Slack Block Kit `actions` block with `style: primary/danger` buttons; Slack POSTs `block_actions` payload to `/webhooks/slack/interact`; backend resolves approval token from `value` field |
| NOTIF-05 | Daily briefing auto-posted to configured Slack/Teams channel | `SlackBriefingService` follows existing `briefing_digest_service.py` pattern; scheduled via existing `/scheduled/*` endpoint pattern with `X-Scheduler-Secret` auth |
| NOTIF-06 | Rich formatted messages (Slack Block Kit / Teams Adaptive Cards) | Slack: `blocks` JSON with `section`, `actions`, `divider` block types; Teams: `{"type":"message","attachments":[{"contentType":"application/vnd.microsoft.card.adaptive",...}]}` POST to webhook URL |
</phase_requirements>

---

## Summary

Phase 45 adds Slack and Microsoft Teams as notification delivery channels. Slack integration is a full OAuth v2 bot with interactive Block Kit buttons that allow approvals directly from Slack. Teams integration uses incoming webhooks (user-configured URLs stored as credentials) with Adaptive Card rich formatting — interactive buttons are delivered as deep links back to Pikar since Teams incoming webhooks do not support `Action.Execute` interactivity.

The architecture follows established Phase 39-44 patterns exactly: provider already exists in `PROVIDER_REGISTRY`, `IntegrationManager.get_valid_token` handles Slack OAuth tokens, and the outbound notification delivery mirrors the `WebhookDeliveryService` pattern. The new work is: (1) a `notification_rules` table and service, (2) `SlackNotificationService` and `TeamsNotificationService`, (3) a `/webhooks/slack/interact` endpoint for button callbacks, (4) a daily briefing scheduler, and (5) a frontend notification rules UI in the configuration page.

**Primary recommendation:** Build Slack first (fully interactive, OAuth already plumbed), then Teams as incoming-webhook-only for v6.0 (interactive buttons redirect to Pikar UI). Both use the same `NotificationDispatcher` with provider-specific formatters.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `slack-sdk` | `>=3.27.0` | Slack Web API client + signature verification | Official Slack Python SDK; `AsyncWebClient` for async ops; `SignatureVerifier` for request validation |
| `httpx` | already pinned `>=0.27.0` | Teams incoming webhook POSTs | Already in project; no new dep needed |
| `slack-sdk[async]` (via aiohttp) | with `aiohttp>=3.9` | AsyncWebClient requires aiohttp | AsyncWebClient uses aiohttp internally |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `aiohttp` | `>=3.9` | Required by `slack_sdk.web.async_client.AsyncWebClient` | Needed when using `AsyncWebClient` |
| `python-slack-sdk` | same as `slack-sdk` | Same package, alternate name | slack-sdk is the canonical pip name |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `slack-sdk AsyncWebClient` | Raw `httpx` for Slack | SDK provides signature verification, retry, token refresh — use it |
| Teams incoming webhook | Teams Graph API `ChannelMessage.Send` | Graph API requires delegated scope (cannot use client credentials) and Bot Framework registration; incoming webhook is zero-infrastructure |
| Teams Adaptive Card `Action.Execute` (bot-only) | Link button back to Pikar | `Action.Execute` only works with full Bot Framework bot; incoming webhook cannot receive responses — use `Action.OpenUrl` linking to `/approval/{token}` |

**Installation:**
```bash
uv add "slack-sdk>=3.27.0" "aiohttp>=3.9.0"
```

---

## Architecture Patterns

### Recommended Project Structure
```
app/
├── services/
│   ├── slack_notification_service.py   # Slack API client + Block Kit formatters
│   ├── teams_notification_service.py   # Teams incoming webhook + Adaptive Card formatters
│   ├── notification_rule_service.py    # Rule evaluation: event_type → channels
│   └── notification_dispatcher.py     # Fan-out: routes events to connected providers
├── agents/tools/
│   └── communication_tools.py          # Agent tools: send_slack_message, list_notification_rules
├── routers/
│   └── webhooks.py                     # ADD: POST /webhooks/slack/interact (block_actions)
│   └── integrations.py                 # ADD: notification rule CRUD endpoints
supabase/migrations/
└── 20260405970000_notification_rules.sql
frontend/src/app/dashboard/configuration/
└── page.tsx                            # ADD: NotificationRulesSection component
```

### Pattern 1: Slack Block Kit Approval Message
**What:** Sends an approval request to a configured Slack channel with interactive Approve/Reject buttons
**When to use:** When `approval.pending` event fires for a user with Slack connected

```python
# Source: https://docs.slack.dev/reference/block-kit/block-elements/button-element
def build_approval_blocks(
    description: str,
    approval_token: str,
    details: str = "",
) -> list[dict]:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Approval Required"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{description}*\n{details}"},
        },
        {"type": "divider"},
        {
            "type": "actions",
            "block_id": f"approval_{approval_token[:16]}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "style": "primary",
                    "value": f"APPROVED:{approval_token}",
                    "action_id": "approval_approve",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Reject"},
                    "style": "danger",
                    "value": f"REJECTED:{approval_token}",
                    "action_id": "approval_reject",
                },
            ],
        },
    ]
    return blocks
```

### Pattern 2: Teams Adaptive Card Notification
**What:** POST an Adaptive Card to a Teams incoming webhook URL
**When to use:** User has Teams connected (stores webhook URL as credential)

```python
# Source: https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/connectors-using
async def post_teams_adaptive_card(
    webhook_url: str,
    title: str,
    body_text: str,
    action_url: str | None = None,
) -> bool:
    card_body = [
        {"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": title},
        {"type": "TextBlock", "wrap": True, "text": body_text},
    ]
    actions = []
    if action_url:
        actions.append({
            "type": "Action.OpenUrl",
            "title": "View in Pikar",
            "url": action_url,
        })
    payload = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "contentUrl": None,
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.2",
                "body": card_body,
                "actions": actions,
            },
        }],
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(webhook_url, json=payload)
        return response.status_code == 200
```

### Pattern 3: Slack Interactivity Endpoint
**What:** Receives block_actions payloads from Slack when a user clicks Approve/Reject
**When to use:** POST to `/webhooks/slack/interact`

```python
# Source: https://docs.slack.dev/reference/interaction-payloads/block_actions-payload/
@router.post("/slack/interact")
async def slack_interact(request: Request) -> JSONResponse:
    """Handle Slack block_actions interactive payloads."""
    body = await request.body()

    # Verify Slack signature (MANDATORY)
    from slack_sdk.signature import SignatureVerifier
    verifier = SignatureVerifier(os.environ["SLACK_SIGNING_SECRET"])
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    if not verifier.is_valid(body, timestamp, signature):
        raise HTTPException(status_code=403, detail="Invalid Slack signature")

    # Slack sends payload as form-encoded JSON string
    form = await request.form()
    payload = json.loads(form["payload"])

    if payload.get("type") == "block_actions":
        action = payload["actions"][0]
        action_id = action["action_id"]          # "approval_approve" or "approval_reject"
        value = action["value"]                   # "APPROVED:{token}" or "REJECTED:{token}"
        response_url = payload.get("response_url")  # for updating the original message

        # Extract action and token
        status, _, token = value.partition(":")
        # ... update approval_requests table, post follow-up via response_url

    return JSONResponse(content={"ok": True})
```

### Pattern 4: Notification Rule Evaluation
**What:** Fan-out dispatcher checks rules on each Pikar event and routes to appropriate channels
**When to use:** Called by `enqueue_webhook_event`, approval creation, task creation

```python
# notification_rule_service.py
async def dispatch_event(
    user_id: str,
    event_type: str,
    payload: dict,
) -> None:
    """Evaluate notification rules and dispatch to connected providers."""
    rules = await _get_matching_rules(user_id, event_type)
    for rule in rules:
        if rule["provider"] == "slack":
            await slack_service.send_notification(
                user_id=user_id,
                channel_id=rule["channel_id"],
                event_type=event_type,
                payload=payload,
            )
        elif rule["provider"] == "teams":
            await teams_service.send_notification(
                user_id=user_id,
                webhook_url=rule["channel_id"],  # Teams uses webhook URL as channel id
                event_type=event_type,
                payload=payload,
            )
```

### Anti-Patterns to Avoid
- **Storing Slack bot token in plaintext:** Always encrypt via `encrypt_secret`/`decrypt_secret` (Fernet) — same as all other integration credentials.
- **Using Teams `Action.Submit` for approvals via incoming webhook:** `Action.Submit` only works with Bot Framework bots. Incoming webhooks cannot receive responses. Use `Action.OpenUrl` back to Pikar instead.
- **Calling Slack synchronously in request handlers:** Slack API calls can take 1-3 seconds. Always fire-and-forget with `asyncio.create_task` or background task.
- **Not acknowledging Slack interactions within 3 seconds:** Slack closes the connection if the endpoint does not return HTTP 200 within 3 seconds. Return 200 immediately, process asynchronously.
- **Using legacy Office 365 Connectors for Teams:** Microsoft is retiring these. Use incoming webhooks (Workflows-based) or the Graph API bot model.
- **Missing `chat:write.public` scope for Slack:** Without this scope, the bot must join a channel before posting. With `chat:write.public`, it can post to any public channel.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slack request signature verification | Custom HMAC comparison | `slack_sdk.signature.SignatureVerifier` | Handles timestamp replay attack prevention (5-minute window), correct byte ordering |
| Slack API client with retries | Raw httpx with retry logic | `AsyncWebClient` from `slack-sdk` | Built-in rate limit handling, automatic retry, typed responses |
| Slack OAuth token exchange | Custom token exchange | Existing `integrations/{provider}/callback` router | Already handles code exchange, Fernet encryption, storage — just add Slack-specific post-processing for `bot_token` field |
| Teams Adaptive Card JSON schema | Custom JSON builder | Follow Adaptive Card spec exactly | Schema version must be `1.2` for incoming webhook compatibility; `Action.Submit` silently fails in webhooks |
| Notification deduplication | Custom bloom filter | Short-lived Redis key `pikar:notif:sent:{user}:{event_id}` with 60s TTL | Prevents duplicate delivery on retry without complex state |

**Key insight:** Slack SDK handles the hardest parts (signature replay attacks, rate limits). Teams interactive approvals via incoming webhook are architecturally impossible — the fallback `Action.OpenUrl` pattern is the correct approach for v6.0.

---

## Common Pitfalls

### Pitfall 1: Slack OAuth v2 Returns `authed_user` AND `bot` Token
**What goes wrong:** Developers use `access_token` from the OAuth response (user token) instead of `bot_token` (bot token). User tokens have different scopes.
**Why it happens:** Slack OAuth v2 returns a nested JSON; the bot token is at `response["access_token"]` only when the response comes from a bot scope flow.
**How to avoid:** After token exchange, check for `bot_token` key in the response; if present, store that as the bot token. The `token_type: bot` field identifies it.
**Warning signs:** `not_in_channel` errors when posting; `invalid_auth` with user-scoped methods.

### Pitfall 2: Slack Interactivity Endpoint Must Return 200 in Under 3 Seconds
**What goes wrong:** Approval processing (DB update + response message) takes > 3 seconds, Slack shows "Action failed" to the user.
**Why it happens:** Slack has a hard 3-second timeout on interactivity endpoints.
**How to avoid:** Return `JSONResponse({"ok": True})` immediately, process in `asyncio.create_task()`.
**Warning signs:** User sees "This app didn't respond" in Slack.

### Pitfall 3: Teams Incoming Webhook Interactive Buttons Don't Work
**What goes wrong:** Adding `Action.Submit` or `Action.Execute` to an Adaptive Card sent via incoming webhook — buttons render but clicking them does nothing.
**Why it happens:** Incoming webhooks are one-way. `Action.Execute` requires Universal Action Model with a bot endpoint; `Action.Submit` requires Bot Framework. Neither is available in the webhook path.
**How to avoid:** Use `Action.OpenUrl` for all interactivity in Teams, linking to Pikar's approval page. Document this limitation explicitly in the frontend.
**Warning signs:** Buttons appear but nothing happens on click; no request arrives at any backend endpoint.

### Pitfall 4: Missing Slack Signing Secret Causes Silent Security Bypass
**What goes wrong:** `SLACK_SIGNING_SECRET` not set in environment; verification skipped or always passes.
**Why it happens:** Signing secret is separate from the bot token — it's found in "Basic Information" in Slack App settings, not OAuth.
**How to avoid:** Store `SLACK_SIGNING_SECRET` in env; fail fast at startup if missing when Slack is connected.
**Warning signs:** Any POST to `/webhooks/slack/interact` succeeds without authentication.

### Pitfall 5: Teams OAuth Scopes vs Incoming Webhook URL Model
**What goes wrong:** Trying to use the user's OAuth token to post channel messages programmatically fails because `ChannelMessage.Send` requires either delegated scope (user must be present) or a full bot registration.
**Why it happens:** Teams "communication" category in PROVIDER_REGISTRY stores an OAuth token, but Teams channel messaging via Graph API requires application-level bot permissions that Pikar cannot get without a Bot Framework registration.
**How to avoid:** For Teams, store the incoming webhook URL as the `account_name` field in `integration_credentials` (not an OAuth token). The "OAuth flow" for Teams is simplified: user pastes their webhook URL in the config page, Pikar stores it. No token exchange needed.
**Warning signs:** 403 errors on Graph API calls; scope errors even with `ChannelMessage.Send` approved.

### Pitfall 6: Slack `channels:read` vs `conversations:list`
**What goes wrong:** Using `channels.list` API method (deprecated) instead of `conversations.list`.
**Why it happens:** Older documentation references the legacy method.
**How to avoid:** Use `client.conversations_list(exclude_archived=True, types="public_channel,private_channel")`.
**Warning signs:** API returns `unknown_method` error.

### Pitfall 7: Teams Rate Limiting on Incoming Webhooks
**What goes wrong:** Sending too many daily briefings or batch notifications triggers HTTP 429.
**Why it happens:** Teams allows max 4 requests/second, 60/30s, 1800/day per incoming webhook.
**How to avoid:** For daily briefings, send one message per user per day. Add exponential backoff on 429 responses. Never batch-blast multiple messages simultaneously.
**Warning signs:** HTTP 429 responses from `*.webhook.office.com`.

---

## Code Examples

Verified patterns from official sources:

### Slack: Send Message with Block Kit
```python
# Source: https://docs.slack.dev/tools/python-slack-sdk/web/
from slack_sdk.web.async_client import AsyncWebClient

async def send_slack_blocks(
    bot_token: str,
    channel_id: str,
    text: str,
    blocks: list[dict],
) -> dict:
    client = AsyncWebClient(token=bot_token)
    response = await client.chat_postMessage(
        channel=channel_id,
        text=text,  # fallback for notifications that don't render blocks
        blocks=blocks,
    )
    return {"ts": response["ts"], "channel": response["channel"]}
```

### Slack: List Available Channels
```python
# Source: https://docs.slack.dev/tools/python-slack-sdk/web/
async def list_slack_channels(bot_token: str) -> list[dict]:
    client = AsyncWebClient(token=bot_token)
    response = await client.conversations_list(
        exclude_archived=True,
        types="public_channel,private_channel",
        limit=200,
    )
    return [
        {"id": ch["id"], "name": ch["name"], "is_private": ch["is_private"]}
        for ch in response["channels"]
    ]
```

### Slack: Verify Workspace Connection
```python
# Source: https://docs.slack.dev/tools/python-slack-sdk/web/
async def verify_slack_token(bot_token: str) -> dict:
    client = AsyncWebClient(token=bot_token)
    response = await client.auth_test()
    return {
        "team": response["team"],
        "bot_id": response["bot_id"],
        "user": response["user"],
    }
```

### Teams: Post Adaptive Card via Incoming Webhook
```python
# Source: https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/connectors-using
async def post_teams_card(webhook_url: str, card_content: dict) -> bool:
    payload = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "contentUrl": None,
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.2",
                **card_content,
            },
        }],
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(webhook_url, json=payload)
        return resp.status_code == 200
```

### Slack: Block Actions Signature Verification
```python
# Source: https://docs.slack.dev/tools/bolt-python/reference/
from slack_sdk.signature import SignatureVerifier

def verify_slack_signature(
    body: bytes,
    timestamp: str,
    signature: str,
    signing_secret: str,
) -> bool:
    verifier = SignatureVerifier(signing_secret)
    return verifier.is_valid(body.decode(), timestamp, signature)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Office 365 Connectors for Teams | Power Automate Workflows incoming webhook | 2024-2025 (retirement announced) | New Teams integrations MUST use Workflows-based webhook URL (looks like `*.webhook.office.com` or Power Automate URL) |
| Slack `channels.list` | `conversations.list` | 2020+ | Legacy method deprecated; use `conversations.list` with `types` parameter |
| Slack classic apps (single OAuth token) | Slack apps with bot user (v2 OAuth) | 2019+ | Must use `oauth.v2.access` endpoint; response has nested `access_token` for bot |
| Teams `Action.Submit` in webhooks | `Action.OpenUrl` for interactivity | Always been true | Incoming webhooks cannot receive responses; interactive approval must redirect to web |

**Deprecated/outdated:**
- `channels.list` Slack API method: replaced by `conversations.list`
- Office 365 Connectors webhook URLs (`outlook.office.com/webhook/...`): being retired; new integrations use `*.webhook.office.com` (Power Automate) URLs
- Slack `api.slack.com` redirect: all docs now at `docs.slack.dev`

---

## Codebase Integration Points

### PROVIDER_REGISTRY: Already Has Slack and Teams
Both `slack` and `teams` entries already exist in `app/config/integration_providers.py`:

- **Slack** scopes: `channels:read, chat:write, users:read, files:read`
  - Need to ADD: `chat:write.public` (post to public channels without joining), `channels:history` (optional for context)
  - The existing `integrations/{provider}/authorize` flow handles the OAuth redirect
  - Post-callback: Slack's token exchange response for v2 has `access_token` (bot token) — store as `access_token` in `integration_credentials`

- **Teams**: Currently has full OAuth2 scopes (`ChannelMessage.Send`, etc.) but research shows these require Bot Framework
  - **Architecture decision needed:** Keep Teams as "incoming webhook URL" model for v6.0
  - Option A: Simplify Teams to `api_key` auth_type (user pastes webhook URL)
  - Option B: Keep OAuth2 entry in registry but skip token exchange; prompt user for webhook URL in the Teams section of the config page

### Approval Token Integration
The existing `approval_requests` table and `approval_tool.py` already generate tokens. The Slack interaction endpoint:
1. Receives `block_actions` payload
2. Extracts token from button `value` field: `"APPROVED:{token_plain}"` 
3. Hashes token: `hashlib.sha256(token.encode()).hexdigest()`
4. Updates `approval_requests` row where `token = hash` and `status = PENDING`
5. Posts follow-up message via `response_url` to update the original Slack message

### Scheduled Daily Briefing Integration
Follow `app/services/scheduled_endpoints.py` pattern:
- New endpoint: `POST /scheduled/slack-daily-briefing` authenticated with `X-Scheduler-Secret`
- Queries all users with `slack` connected and a `daily_briefing` rule configured
- Calls `SlackNotificationService.send_daily_briefing(user_id, channel_id)`
- Daily briefing content: aggregate from `kpi_service`, pending approvals count, upcoming tasks

### Frontend Integration Point
Follows `PMSyncSection`/`BudgetCapSection` pattern in `dashboard/configuration/page.tsx`:
- New `NotificationRulesSection` component renders only when Slack/Teams connected
- Shows per-event rules table: event_type | channel | provider toggle
- "Test Notification" button triggers a sample message

---

## Database Schema

### New Table: `notification_rules`
```sql
CREATE TABLE IF NOT EXISTS public.notification_rules (
    id            uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id       uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider      text        NOT NULL CHECK (provider IN ('slack', 'teams')),
    event_type    text        NOT NULL,   -- 'task.created', 'approval.pending', 'workflow.completed', etc.
    channel_id    text        NOT NULL,   -- Slack: channel ID (C0XXXXXX); Teams: webhook URL
    channel_name  text        NOT NULL DEFAULT '',  -- display name
    enabled       boolean     NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_notification_rule UNIQUE (user_id, provider, event_type, channel_id)
);
```

### New Table: `notification_channel_config`
```sql
CREATE TABLE IF NOT EXISTS public.notification_channel_config (
    id                uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id           uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider          text        NOT NULL CHECK (provider IN ('slack', 'teams')),
    daily_briefing    boolean     NOT NULL DEFAULT false,
    briefing_channel_id text,              -- Slack channel or Teams webhook URL for briefing
    briefing_channel_name text DEFAULT '',
    briefing_time_utc text NOT NULL DEFAULT '08:00',  -- HH:MM UTC
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_notification_channel_config UNIQUE (user_id, provider)
);
```

---

## Supported Event Types

For `notification_rules.event_type`, these Pikar events map to notification triggers:

| Event Type | Trigger | Source |
|-----------|---------|--------|
| `approval.pending` | New approval request created | `approval_tool.py`, `magic_link_approvals.py` |
| `task.created` | New task inserted | `task_service.py` |
| `task.completed` | Task status → completed | `task_service.py` |
| `workflow.completed` | Workflow run finishes | `workflow_trigger_service.py` |
| `workflow.failed` | Workflow run fails | `workflow_trigger_service.py` |
| `campaign.milestone` | Campaign hits milestone | `campaign_orchestrator_service.py` |
| `daily.briefing` | Scheduled daily summary | Scheduler endpoint |

---

## Open Questions

1. **Teams OAuth vs Webhook URL model for NOTIF-02**
   - What we know: Graph API `ChannelMessage.Send` requires delegated permissions (user must authorize) or full Bot Framework registration. Client credentials flow cannot post to channels.
   - What's unclear: Does the requirement "connect Microsoft Teams via Azure AD OAuth" imply a true OAuth flow that stores a user token, or is the user experience "paste your Teams webhook URL"?
   - Recommendation: Implement Teams as `api_key` auth_type where the user provides their incoming webhook URL. This fully satisfies NOTIF-02's "connect via configuration page" success criterion without requiring Bot Framework. The PROVIDER_REGISTRY `teams` entry can be updated to `api_key` auth_type with `scopes: []`.

2. **Slack `bot_token` field in OAuth v2 response**
   - What we know: Slack v2 OAuth response returns `access_token` as the bot token (when bot scopes are requested). The existing callback handler stores `access_token` from the token exchange response.
   - What's unclear: Does the Slack v2 response actually return `bot_token` as a separate key or is `access_token` the bot token?
   - Recommendation: After callback, call `auth.test` with the received token to confirm it's a bot token (`token_type: bot`). Log and fail if it's a user token.

3. **Approval response_url expiry**
   - What we know: Slack's `response_url` expires after 30 minutes.
   - What's unclear: For approvals that are acted on hours later (not via Slack), should the Slack message be updated?
   - Recommendation: Store `response_url` in the `approval_requests` payload JSONB. After approval via any channel (Pikar UI or Slack), attempt to update via `response_url` if still within 30 minutes.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/unit/services/test_slack_notification_service.py -x` |
| Full suite command | `uv run pytest tests/ -x --timeout=30` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NOTIF-01 | Slack OAuth stores bot token encrypted | unit | `uv run pytest tests/unit/services/test_slack_notification_service.py::test_token_stored_encrypted -x` | ❌ Wave 0 |
| NOTIF-02 | Teams webhook URL stored as credential | unit | `uv run pytest tests/unit/services/test_teams_notification_service.py::test_webhook_url_stored -x` | ❌ Wave 0 |
| NOTIF-03 | Notification rules CRUD and event matching | unit | `uv run pytest tests/unit/services/test_notification_rule_service.py -x` | ❌ Wave 0 |
| NOTIF-04 | Slack block_actions signature verification and approval update | unit | `uv run pytest tests/unit/services/test_slack_notification_service.py::test_interact_approval -x` | ❌ Wave 0 |
| NOTIF-05 | Daily briefing constructs valid Block Kit payload | unit | `uv run pytest tests/unit/services/test_slack_notification_service.py::test_daily_briefing_blocks -x` | ❌ Wave 0 |
| NOTIF-06 | Block Kit message structure valid (section+actions blocks), Teams Adaptive Card valid JSON | unit | `uv run pytest tests/unit/services/test_slack_notification_service.py::test_block_kit_structure -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/services/test_slack_notification_service.py tests/unit/services/test_teams_notification_service.py tests/unit/services/test_notification_rule_service.py -x`
- **Per wave merge:** `uv run pytest tests/ -x --timeout=30`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/services/test_slack_notification_service.py` — covers NOTIF-01, NOTIF-04, NOTIF-05, NOTIF-06 (Slack)
- [ ] `tests/unit/services/test_teams_notification_service.py` — covers NOTIF-02, NOTIF-06 (Teams)
- [ ] `tests/unit/services/test_notification_rule_service.py` — covers NOTIF-03

---

## Sources

### Primary (HIGH confidence)
- `https://docs.slack.dev/reference/block-kit/block-elements/button-element` — Button element JSON structure, style field (primary/danger), action_id, value
- `https://docs.slack.dev/reference/interaction-payloads/block_actions-payload/` — block_actions payload structure, response_url, actions array fields
- `https://docs.slack.dev/tools/python-slack-sdk/web/` — AsyncWebClient, chat_postMessage with blocks, conversations_list, auth_test
- `https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/connectors-using` — Teams Adaptive Card incoming webhook JSON format, rate limits, Action.OpenUrl
- `https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook` — Teams incoming webhook deprecation status (O365 Connectors retiring), creation steps

### Secondary (MEDIUM confidence)
- `https://docs.slack.dev/authentication/installing-with-oauth` — OAuth v2 bot scopes: `chat:write`, `channels:read`, `commands`
- `https://docs.slack.dev/tools/bolt-python/reference/adapter/fastapi/` — FastAPI adapter for Bolt (not used directly but confirms FastAPI integration pattern)
- `https://learn.microsoft.com/en-us/graph/api/channel-post-messages` — Graph API requires delegated scope for channel messaging (confirms bot/Graph API path is not viable without Bot Framework)

### Tertiary (LOW confidence)
- WebSearch findings on Teams Graph API `ChannelMessage.Send` client credentials flow limitation — confirmed by multiple Microsoft Q&A posts that this requires delegated scope or Bot Framework

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `slack-sdk` is the official Slack Python SDK; Teams incoming webhook format verified from official Microsoft docs (updated 2026-03-13)
- Architecture: HIGH — follows established Phase 39-44 patterns exactly; Slack already in PROVIDER_REGISTRY; approval token flow already exists
- Pitfalls: HIGH — Teams interactive button limitation verified against official docs; Slack 3-second timeout is documented constraint; signing secret pitfall well-documented
- Teams interactive approval limitation: HIGH — verified from official Microsoft docs that incoming webhooks cannot receive responses

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (Teams incoming webhook retirement schedule may accelerate; check for O365 Connector deadline)
