# Phase 42: CRM & Email Automation - Research

**Researched:** 2026-04-04
**Domain:** HubSpot CRM integration, email sequence automation, Resend deliverability
**Confidence:** HIGH

## Summary

Phase 42 connects HubSpot CRM with bidirectional contact/deal sync, makes agents CRM-aware for sales queries, and builds an email sequence engine with multi-step drip campaigns, tracking, bounce protection, and deliverability safeguards. The codebase already has strong foundational patterns from Phase 39 (integration infrastructure), Phase 41 (Stripe/Shopify sync services), and existing Resend email sending -- all of which can be directly extended.

The HubSpot Python SDK (`hubspot-api-client` v12.0.0) is a synchronous library that must be wrapped with `asyncio.to_thread()`, exactly matching the Stripe SDK pattern from Phase 41. HubSpot webhook signature verification uses a different algorithm than the generic HMAC handler (base64-encoded HMAC-SHA256 of `method+url+body+timestamp`), so it needs a dedicated `/webhooks/hubspot` endpoint like Stripe and Shopify got. The email sequence engine is a new subsystem but follows existing patterns: campaign FSM for state management, workflow worker tick cycle for scheduled delivery, Redis for daily send counters, and Resend for actual sending with custom headers for List-Unsubscribe compliance.

**Primary recommendation:** Follow the Phase 41 sync service pattern (StripeSyncService/ShopifyService) for HubSpot, with dedicated webhook endpoint. Build email sequences as a new service with its own tables, integrated into the existing workflow worker tick cycle for delivery scheduling.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **HubSpot SDK:** `hubspot-api-client` (sync SDK, wrap with `asyncio.to_thread()`)
- **Connection:** Via Phase 39 OAuth infrastructure -- HubSpot already in PROVIDER_REGISTRY
- **Data sync:** Contacts bidirectional, Deals read+write, Activities read-only from HubSpot
- **Sync strategy:** Initial full import + HubSpot webhooks for real-time + immediate push on Pikar changes
- **Conflict resolution:** Last-write-wins with `hs_lastmodifieddate` comparison; flag if both modified
- **New tables:** `hubspot_deals`, `email_sequences`, `email_sequence_steps`, `email_sequence_enrollments`, `email_tracking_events`
- **New column:** `hubspot_contact_id` on existing `contacts` table
- **Template system:** Jinja2 with `{{first_name}}`, `{{company}}`, `{{deal_name}}`, `{{custom.field}}`
- **Scheduling:** Timezone-aware, 60-second delivery tick in workflow worker
- **Send limits:** Auto-increasing warm-up (50/100/250/500 per day over 4 weeks)
- **Tracking:** Open pixel + click wrapping via `/tracking/open/{id}` and `/tracking/click/{id}`
- **Bounce protection:** >5% bounce rate auto-pauses ALL sequences for user
- **Unsubscribe:** RFC 8058 one-click List-Unsubscribe header + footer link
- **Sending:** Via existing Resend integration
- **CRM-aware agents:** SalesIntelligenceAgent gets `get_hubspot_deal_context(contact_name)` tool
- **HubSpot tools:** On SalesIntelligenceAgent (5 tools)
- **Email tools:** On MarketingAutomationAgent's EmailMarketingAgent sub-agent (6 tools)
- **New services:** `app/services/hubspot_service.py`, `app/services/email_sequence_service.py`
- **New router:** `app/routers/email_sequences.py`

### Claude's Discretion
- Exact HubSpot property-to-Pikar-column mapping details
- HubSpot webhook subscription API call details
- Email template HTML structure and default styling
- Tracking pixel implementation (transparent PNG vs SVG)
- Exact Redis key structure for send limit tracking
- Conflict resolution UI (if needed -- could be agent-mediated)
- Whether to add HubSpot contact data to DataExportService's exportable tables
- Email sequence step delay computation algorithm

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CRM-01 | User can connect HubSpot account via OAuth from configuration page | HubSpot already in PROVIDER_REGISTRY with OAuth URLs + scopes; Phase 39 OAuth flow handles connection |
| CRM-02 | Bidirectional contact sync between HubSpot and Pikar contacts table | HubSpot SDK contacts API verified; contacts table schema mapped; `hubspot_contact_id` column addition |
| CRM-03 | User can view HubSpot deals and pipeline stages in Pikar dashboard | HubSpot SDK deals + pipelines API verified; new `hubspot_deals` table schema designed |
| CRM-04 | Agent can create/update HubSpot contacts and deals via chat commands | 5 HubSpot tools designed for SalesIntelligenceAgent; SDK methods verified |
| CRM-05 | Agent responses are CRM-aware (agent sees deal context before responding) | `get_hubspot_deal_context` tool + instruction update for SalesIntelligenceAgent |
| CRM-06 | HubSpot webhook processing for real-time sync on contact/deal changes | Dedicated webhook endpoint with v3 signature verification; property change subscriptions |
| EMAIL-01 | User can create multi-step email sequences with templates and variables | 4 new tables designed; Jinja2 template rendering; CRUD router |
| EMAIL-02 | Sequence scheduling with timezone-aware send times | `next_send_at` per enrollment with timezone; 60s worker tick cycle |
| EMAIL-03 | Open and click tracking via tracking pixels and link wrapping | Tracking endpoints + `email_tracking_events` table; 1x1 transparent PNG |
| EMAIL-04 | Sequence pause/resume on bounce rate threshold (>5%) | Resend `email.bounced` webhook handler; auto-pause logic in service |
| EMAIL-05 | Daily send limit per user (configurable, default 50/day for warm-up) | Redis counter with TTL; warm-up schedule in integration_sync_state |
| EMAIL-06 | Agent can generate email sequence content based on campaign context | `generate_sequence_content` tool on EmailMarketingAgent; AI content via Gemini |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| hubspot-api-client | 12.0.0 | HubSpot CRM API access (contacts, deals, pipelines, search) | Official HubSpot Python SDK, actively maintained, V3 API |
| jinja2 | (transitive via weasyprint) | Email template variable substitution | Already available in project, used by document_service.py |
| redis (existing) | >=5.0.0 | Daily send limit counters, rate limiting | Already in project deps with circuit breaker |
| httpx (existing) | >=0.27.0 | Resend API calls for email sending with custom headers | Already used by EmailService |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Resend API (existing) | via httpx | Email delivery with tracking headers | Every sequence email send |
| supabase (existing) | >=2.27.2 | All DB operations for new tables | CRM data, sequences, tracking events |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hubspot-api-client (sync) | hubspot-api-client-async (v12.0.3) | Async variant exists but less battle-tested; sync + to_thread matches codebase pattern |
| Jinja2 for templates | str.format() / string.Template | Jinja2 supports conditionals, loops, filters -- needed for complex email templates |
| Redis for send counters | PostgreSQL increment | Redis is faster for high-frequency counter checks; TTL-based auto-expiry |

**Installation:**
```bash
uv add hubspot-api-client
```

Note: `jinja2` is already a transitive dependency via `weasyprint`. It should be added as an explicit dependency to make the requirement clear:
```bash
uv add jinja2
```

## Architecture Patterns

### Recommended Project Structure
```
app/
  services/
    hubspot_service.py          # HubSpot sync + CRUD (extends BaseService)
    email_sequence_service.py   # Sequence engine (extends BaseService)
  agents/
    tools/
      hubspot_tools.py          # 5 HubSpot agent tools
      email_sequence_tools.py   # 6 email sequence agent tools
    sales/agent.py              # Updated: add HubSpot tools, remove hubspot_setup_guide
    marketing/agent.py          # Updated: add email tools to EmailMarketingAgent
  routers/
    webhooks.py                 # Updated: add /webhooks/hubspot endpoint
    email_sequences.py          # NEW: CRUD + enrollment + tracking endpoints
supabase/
  migrations/
    20260404800000_crm_email_automation.sql  # All new tables + column additions
```

### Pattern 1: HubSpot Sync Service (follows StripeSyncService)
**What:** Service that wraps HubSpot SDK in asyncio.to_thread() and syncs data to local tables
**When to use:** All HubSpot API interactions
**Example:**
```python
# Source: Verified from app/services/stripe_sync_service.py pattern
from hubspot import HubSpot

class HubSpotService(BaseService):
    """Bidirectional HubSpot CRM sync."""

    async def _get_client(self, user_id: str) -> HubSpot:
        """Get HubSpot client with user's OAuth token."""
        mgr = IntegrationManager()
        token = await mgr.get_valid_token(user_id, "hubspot")
        if not token:
            raise ValueError("HubSpot not connected")
        return HubSpot(access_token=token)

    async def sync_contacts(self, user_id: str) -> dict:
        """Import HubSpot contacts into Pikar contacts table."""
        client = await self._get_client(user_id)

        def _fetch():
            return client.crm.contacts.basic_api.get_page(
                limit=100,
                properties=["email", "firstname", "lastname", "phone",
                            "company", "lifecyclestage", "hs_lastmodifieddate"]
            )

        result = await asyncio.to_thread(_fetch)
        # Map and upsert to contacts table...
```

### Pattern 2: Dedicated Webhook Endpoint (follows Stripe/Shopify pattern)
**What:** Provider-specific webhook handler with custom signature verification
**When to use:** HubSpot webhooks need v3 signature verification (different from generic HMAC)
**Example:**
```python
# Source: Verified from app/routers/webhooks.py Stripe/Shopify pattern
import hashlib, hmac, base64, time

def _verify_hubspot_signature_v3(
    body: bytes,
    method: str,
    url: str,
    timestamp: str,
    secret: str,
    signature: str,
) -> bool:
    """Verify HubSpot v3 webhook signature.

    v3 signs: requestMethod + requestUri + requestBody + timestamp
    then HMAC-SHA256 with client secret, base64-encoded.
    """
    if abs(time.time() - int(timestamp)) > 300:  # 5 min tolerance
        return False
    source = f"{method}{url}{body.decode()}{timestamp}"
    expected = base64.b64encode(
        hmac.new(secret.encode(), source.encode(), hashlib.sha256).digest()
    ).decode()
    return hmac.compare_digest(expected, signature)
```

### Pattern 3: Worker Tick for Email Delivery (follows workflow_trigger pattern)
**What:** Periodic tick in the existing WorkflowWorker that processes due email sends
**When to use:** Every 60 seconds, check for enrollments where next_send_at <= now()
**Example:**
```python
# Source: Verified from app/workflows/worker.py tick pattern
class WorkflowWorker:
    def __init__(self):
        # ... existing init ...
        self.last_email_sequence_tick = datetime.min
        self.email_sequence_interval_seconds = 60

    async def run_email_sequence_tick_if_due(self):
        now = datetime.now()
        if (now - self.last_email_sequence_tick).total_seconds() < self.email_sequence_interval_seconds:
            return
        self.last_email_sequence_tick = now
        from app.services.email_sequence_service import run_email_delivery_tick
        results = await run_email_delivery_tick()
```

### Pattern 4: Agent Tool with Request Context (follows shopify_tools.py)
**What:** Raw function exports that extract user_id from request context
**When to use:** All HubSpot and email sequence tools
**Example:**
```python
# Source: Verified from app/agents/tools/shopify_tools.py
async def search_hubspot_contacts(query: str) -> dict[str, Any]:
    """Search HubSpot contacts by name, email, or company."""
    user_id = _get_user_id()
    if not user_id:
        return {"error": "Authentication required"}
    from app.services.hubspot_service import HubSpotService
    svc = HubSpotService()
    try:
        contacts = await svc.search_contacts(user_id=user_id, query=query)
        return {"contacts": contacts, "count": len(contacts)}
    except Exception as exc:
        return {"error": f"Failed to search HubSpot contacts: {exc}"}
```

### Anti-Patterns to Avoid
- **Using the generic /webhooks/inbound/hubspot endpoint:** HubSpot v3 signature uses method+url+body+timestamp (not just sha256=hex). Needs a dedicated handler.
- **Synchronous HubSpot SDK calls without to_thread():** Will block the event loop. Always wrap in `asyncio.to_thread()`.
- **Sending all sequence emails in one batch:** Must respect daily send limits and check bounce rate before each send.
- **Storing tracking pixel inline as base64:** Serve from an endpoint so the HTTP request triggers the tracking event.
- **Hardcoding warm-up limits:** Store in `integration_sync_state` so they advance with time.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HubSpot API access | Raw httpx requests to HubSpot | `hubspot-api-client` SDK | Handles pagination, error types, rate limit headers, auth refresh |
| Email template rendering | String concatenation/regex | Jinja2 `Environment.from_string()` | Safe escaping, conditionals, loops, filters, error handling |
| Webhook signature verification | Copy-paste from generic handler | Dedicated `_verify_hubspot_signature_v3()` | v3 uses different algorithm (method+url+body+timestamp) |
| Daily send counters | PostgreSQL UPDATE + SELECT | Redis INCR + EXPIRE | Atomic increment, auto-expiry, no lock contention |
| One-click unsubscribe | Custom POST endpoint only | RFC 8058 List-Unsubscribe + List-Unsubscribe-Post headers | Gmail/Yahoo require these headers since June 2024 for bulk senders |

**Key insight:** HubSpot's Python SDK is synchronous but well-structured. The project already solved this pattern with Stripe (asyncio.to_thread). Do not fight the SDK -- wrap it.

## Common Pitfalls

### Pitfall 1: HubSpot Webhook Subscription Requires Per-Property Setup
**What goes wrong:** Assuming you can subscribe to "all property changes" with a wildcard
**Why it happens:** HubSpot's webhook API requires specifying EACH property you want to monitor (e.g., `contact.propertyChange` for `email`, separately for `firstname`, etc.)
**How to avoid:** On initial HubSpot connect, register webhook subscriptions for each monitored property explicitly: email, firstname, lastname, phone, company, lifecyclestage for contacts; dealname, amount, dealstage, pipeline, closedate for deals. Also subscribe to `contact.creation`, `deal.creation`.
**Warning signs:** Webhooks work for creation events but not property updates

### Pitfall 2: HubSpot Rate Limits (190/10s burst)
**What goes wrong:** Initial full contact import exceeding burst rate limit
**Why it happens:** HubSpot allows only 190 requests per 10 seconds for private apps
**How to avoid:** Use batch API endpoints where available. For initial sync, paginate with limit=100 and add a small sleep (0.5s) between pages. Track `X-HubSpot-RateLimit-Remaining` header.
**Warning signs:** 429 responses during initial sync

### Pitfall 3: Resend Custom Headers Must Be Sent via API Parameter
**What goes wrong:** Assuming Resend automatically adds List-Unsubscribe headers
**Why it happens:** Resend handles some headers automatically for audience-based sends, but for API sends you must explicitly include `headers` parameter
**How to avoid:** Always include both headers in every sequence email:
```python
headers={
    "List-Unsubscribe": f"<https://app.pikar.ai/unsubscribe/{enrollment_id}>",
    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
}
```
**Warning signs:** Gmail not showing "Unsubscribe" button in email header

### Pitfall 4: Tracking Pixel Blocked by Email Clients
**What goes wrong:** Open rate shows 0% even though emails are delivered
**Why it happens:** Many email clients block remote images by default; Apple Mail Privacy does proxy opens
**How to avoid:** Accept that open tracking is an approximation, not exact. Use click tracking as the more reliable engagement signal. Don't make critical business decisions based solely on open rates.
**Warning signs:** Click rate > open rate (impossible in reality, means opens are underreported)

### Pitfall 5: Timezone-Naive Scheduling Causes Sends at Wrong Times
**What goes wrong:** Emails scheduled for "9am" send at 9am UTC instead of recipient's timezone
**Why it happens:** Storing `next_send_at` without timezone conversion
**How to avoid:** Store enrollment timezone explicitly. Compute `next_send_at` in UTC but based on the desired local time: `desired_local_time.astimezone(timezone.utc)`. The worker always queries `next_send_at <= utcnow()`.
**Warning signs:** Complaints about receiving emails at 3am

### Pitfall 6: Bidirectional Sync Infinite Loop
**What goes wrong:** Pikar updates contact -> pushes to HubSpot -> HubSpot webhook fires -> Pikar updates contact -> pushes to HubSpot -> infinite loop
**Why it happens:** Webhook handler doesn't distinguish between Pikar-originated changes and external changes
**How to avoid:** Before processing a HubSpot webhook update, compare the `hs_lastmodifieddate` with the contact's `updated_at`. If they match (within a few seconds), skip the update -- it was our own change echoing back. Alternatively, set a short-lived Redis flag `pikar:hubspot:skip:{contact_id}` after pushing to HubSpot, and check it before processing the webhook.
**Warning signs:** Contact `updated_at` changing every few seconds; high HubSpot API usage

### Pitfall 7: Bounce Rate Calculation Window
**What goes wrong:** A single bounce on a new account with 1 total send triggers the 5% threshold (100% bounce rate)
**Why it happens:** Using lifetime bounce rate instead of rolling window
**How to avoid:** Calculate bounce rate over a rolling 24-hour window with a minimum send threshold (e.g., at least 20 sends before the rate is meaningful). Below minimum, still pause on 3+ bounces.
**Warning signs:** Sequences being auto-paused after a single bounced email on a new account

## Code Examples

### Email Sending with Tracking and Unsubscribe Headers
```python
# Source: Verified from app/mcp/integrations/email_service.py + Resend docs
async def send_sequence_email(
    to_email: str,
    subject: str,
    html_body: str,
    enrollment_id: str,
    step_number: int,
    tracking_base_url: str = "https://app.pikar.ai",
) -> dict[str, Any]:
    """Send a single sequence email with tracking and compliance headers."""
    tracking_id = f"{enrollment_id}_{step_number}"

    # Inject tracking pixel before closing </body>
    pixel_url = f"{tracking_base_url}/tracking/open/{tracking_id}"
    pixel_html = f'<img src="{pixel_url}" width="1" height="1" style="display:none" alt="" />'
    tracked_html = html_body.replace("</body>", f"{pixel_html}</body>")

    # Wrap links for click tracking
    tracked_html = _wrap_links(tracked_html, tracking_id, tracking_base_url)

    # Unsubscribe URL
    unsub_url = f"{tracking_base_url}/unsubscribe/{enrollment_id}"

    # Add footer
    tracked_html = tracked_html.replace(
        "</body>",
        f'<div style="margin-top:24px;padding-top:12px;border-top:1px solid #e5e7eb;'
        f'font-size:12px;color:#6b7280;text-align:center;">'
        f'<a href="{unsub_url}" style="color:#6b7280;">Unsubscribe</a>'
        f'</div></body>'
    )

    email_data = {
        "from": "noreply@pikar-ai.com",  # or user's configured from
        "to": [to_email],
        "subject": subject,
        "html": tracked_html,
        "headers": {
            "List-Unsubscribe": f"<{unsub_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=email_data,
        )
    return response.json()
```

### HubSpot Contact Sync with Conflict Detection
```python
# Source: Verified from StripeSyncService + ShopifyService patterns
LIFECYCLE_MAP = {
    "subscriber": "lead",
    "lead": "lead",
    "marketingqualifiedlead": "qualified",
    "salesqualifiedlead": "qualified",
    "opportunity": "opportunity",
    "customer": "customer",
    "evangelist": "customer",
    "other": "lead",
}

async def _sync_contact_from_hubspot(
    self,
    hubspot_contact: dict,
    user_id: str,
) -> dict[str, Any]:
    """Map HubSpot contact to Pikar contacts row and upsert."""
    props = hubspot_contact.get("properties", {})
    hs_id = hubspot_contact.get("id")
    hs_modified = props.get("hs_lastmodifieddate")

    row = {
        "user_id": user_id,
        "hubspot_contact_id": hs_id,
        "email": props.get("email"),
        "name": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip() or "Unknown",
        "phone": props.get("phone"),
        "company": props.get("company"),
        "lifecycle_stage": LIFECYCLE_MAP.get(
            (props.get("lifecyclestage") or "").lower(), "lead"
        ),
        "metadata": {
            "hubspot_modified": hs_modified,
            "hubspot_properties": {
                k: v for k, v in props.items()
                if k not in ("email", "firstname", "lastname", "phone", "company")
            },
        },
    }

    admin = AdminService()
    result = await execute_async(
        admin.client.table("contacts").upsert(
            row,
            on_conflict="user_id,hubspot_contact_id",
            ignore_duplicates=False,
        ),
        op_name="hubspot.sync_contact",
    )
    return result.data[0] if result.data else row
```

### Redis Daily Send Counter
```python
# Source: Verified from app/services/cache.py patterns
import redis.asyncio as redis
from datetime import date

async def check_and_increment_daily_send(
    redis_client: redis.Redis,
    user_id: str,
    max_sends: int,
) -> bool:
    """Atomically check daily send limit and increment if under.

    Returns True if the email can be sent, False if limit reached.
    """
    key = f"pikar:email:daily:{user_id}:{date.today().isoformat()}"

    # Use INCR + check pattern
    current = await redis_client.incr(key)

    # Set TTL on first increment (25 hours to cover timezone edge cases)
    if current == 1:
        await redis_client.expire(key, 90000)

    if current > max_sends:
        # Rolled back -- decrement since we won't actually send
        await redis_client.decr(key)
        return False

    return True
```

### SQL Migration for New Tables
```sql
-- Key schema decisions verified from existing migrations

-- Add HubSpot ID to existing contacts table
ALTER TABLE public.contacts
    ADD COLUMN IF NOT EXISTS hubspot_contact_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_hubspot_id
    ON public.contacts(user_id, hubspot_contact_id)
    WHERE hubspot_contact_id IS NOT NULL;

-- HubSpot deals table
CREATE TABLE public.hubspot_deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    hubspot_deal_id TEXT NOT NULL,
    deal_name TEXT NOT NULL,
    pipeline TEXT,
    stage TEXT,
    amount NUMERIC(14,2),
    close_date DATE,
    associated_contacts UUID[] DEFAULT '{}',
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, hubspot_deal_id)
);

-- Email sequences table
CREATE TABLE public.email_sequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'active', 'paused', 'completed')),
    campaign_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enrollment table with timezone-aware scheduling
CREATE TABLE public.email_sequence_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id UUID NOT NULL REFERENCES public.email_sequences(id) ON DELETE CASCADE,
    contact_id UUID NOT NULL REFERENCES public.contacts(id) ON DELETE CASCADE,
    current_step INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'completed', 'bounced', 'unsubscribed', 'paused')),
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    next_send_at TIMESTAMPTZ,
    timezone TEXT DEFAULT 'UTC',
    UNIQUE(sequence_id, contact_id)
);

-- Critical index for delivery worker efficiency
CREATE INDEX idx_enrollments_next_send
    ON public.email_sequence_enrollments(next_send_at)
    WHERE status = 'active' AND next_send_at IS NOT NULL;
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HubSpot API v1/v2 | HubSpot API v3 (via hubspot-api-client 12.x) | 2023+ | All endpoints use v3 paths; v1/v2 deprecated |
| HubSpot webhook sig v1/v2 | v3 signature (method+url+body+timestamp HMAC-SHA256 base64) | 2022 | Must use X-HubSpot-Signature-v3 header |
| Optional List-Unsubscribe | Required by Gmail/Yahoo for bulk (5000+/day) | June 2024 | Must include RFC 8058 headers for deliverability |
| hubspot_setup_guide tool | Real CRM tools (search, create, update contacts/deals) | This phase | Phase 38 renamed it; Phase 42 replaces with real functionality |

**Deprecated/outdated:**
- `hubspot_setup_guide` tool (enhanced_tools.py): Being replaced by real HubSpot CRM tools
- HubSpot webhook signature v1/v2: v3 is the current standard
- HubSpot Contacts API v1: Use v3 via SDK

## Open Questions

1. **HubSpot Webhook App ID**
   - What we know: Webhook subscriptions require a HubSpot `appId` -- this is the developer app ID, not the user's portal ID
   - What's unclear: Whether webhook subscriptions are created per-user or once globally for the Pikar HubSpot app
   - Recommendation: Register webhook subscriptions at the app level (during HubSpot app setup in the developer portal), not per-user via API. HubSpot routes webhook events to the app, and the payload includes `portalId` which maps to the user. This is the standard pattern for public HubSpot apps.

2. **Jinja2 Explicit Dependency**
   - What we know: Jinja2 is available as a transitive dependency via weasyprint
   - What's unclear: Whether it should be added as an explicit dependency in pyproject.toml
   - Recommendation: Add it explicitly (`uv add jinja2`) since the email sequence feature directly depends on it. Transitive deps can change.

3. **Tracking Base URL Configuration**
   - What we know: Tracking endpoints need a publicly accessible URL
   - What's unclear: Whether to use the existing SUPABASE_URL domain, a separate tracking domain, or a config variable
   - Recommendation: Add a `PIKAR_BASE_URL` environment variable (or reuse an existing one) for tracking URL construction. This avoids hardcoding domains.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | pyproject.toml (existing) |
| Quick run command | `uv run pytest tests/unit/test_hubspot_service.py tests/unit/test_email_sequence_service.py -x` |
| Full suite command | `make test` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CRM-01 | HubSpot OAuth connection (Phase 39 handles) | integration | N/A -- covered by Phase 39 tests | N/A |
| CRM-02 | Bidirectional contact sync | unit | `uv run pytest tests/unit/test_hubspot_service.py::test_sync_contacts -x` | Wave 0 |
| CRM-03 | Deals and pipeline display | unit | `uv run pytest tests/unit/test_hubspot_service.py::test_sync_deals -x` | Wave 0 |
| CRM-04 | Agent create/update contacts/deals | unit | `uv run pytest tests/unit/test_hubspot_tools.py -x` | Wave 0 |
| CRM-05 | CRM-aware agent responses | unit | `uv run pytest tests/unit/test_hubspot_tools.py::test_get_deal_context -x` | Wave 0 |
| CRM-06 | HubSpot webhook processing | unit | `uv run pytest tests/unit/test_hubspot_webhooks.py -x` | Wave 0 |
| EMAIL-01 | Multi-step sequence CRUD | unit | `uv run pytest tests/unit/test_email_sequence_service.py::test_create_sequence -x` | Wave 0 |
| EMAIL-02 | Timezone-aware scheduling | unit | `uv run pytest tests/unit/test_email_sequence_service.py::test_timezone_scheduling -x` | Wave 0 |
| EMAIL-03 | Open/click tracking | unit | `uv run pytest tests/unit/test_email_tracking.py -x` | Wave 0 |
| EMAIL-04 | Bounce rate auto-pause | unit | `uv run pytest tests/unit/test_email_sequence_service.py::test_bounce_auto_pause -x` | Wave 0 |
| EMAIL-05 | Daily send limits | unit | `uv run pytest tests/unit/test_email_sequence_service.py::test_daily_send_limit -x` | Wave 0 |
| EMAIL-06 | Agent content generation | unit | `uv run pytest tests/unit/test_email_sequence_tools.py::test_generate_content -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/test_hubspot_service.py tests/unit/test_email_sequence_service.py -x`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_hubspot_service.py` -- covers CRM-02, CRM-03
- [ ] `tests/unit/test_hubspot_tools.py` -- covers CRM-04, CRM-05
- [ ] `tests/unit/test_hubspot_webhooks.py` -- covers CRM-06
- [ ] `tests/unit/test_email_sequence_service.py` -- covers EMAIL-01, EMAIL-02, EMAIL-04, EMAIL-05
- [ ] `tests/unit/test_email_tracking.py` -- covers EMAIL-03
- [ ] `tests/unit/test_email_sequence_tools.py` -- covers EMAIL-06

## Sources

### Primary (HIGH confidence)
- `app/services/stripe_sync_service.py` -- Pattern for sync SDK wrapping with asyncio.to_thread
- `app/services/shopify_service.py` -- Pattern for external API sync with webhook handling
- `app/routers/webhooks.py` -- Existing webhook infrastructure, Stripe/Shopify dedicated endpoints
- `app/config/integration_providers.py` -- HubSpot already registered with OAuth URLs and scopes
- `app/services/integration_manager.py` -- Token storage, refresh, sync state management
- `app/mcp/integrations/email_service.py` -- Current Resend email sending implementation
- `app/agents/sales/agent.py` -- SalesIntelligenceAgent with hubspot_setup_guide to replace
- `app/agents/marketing/agent.py` -- MarketingAutomationAgent with EmailMarketingAgent sub-agent
- `app/workflows/worker.py` -- Worker tick cycle pattern for scheduled delivery
- `app/services/workflow_trigger_service.py` -- Scheduler tick pattern
- `supabase/migrations/20260301111801_create_contacts_crm.sql` -- Existing contacts table schema
- `app/services/cache.py` -- Redis key namespace prefixes, circuit breaker pattern
- `app/agents/tools/shopify_tools.py` -- Agent tool pattern with request context

### Secondary (MEDIUM confidence)
- [HubSpot API Python SDK README](https://github.com/HubSpot/hubspot-api-python) -- SDK usage patterns, method signatures
- [HubSpot API usage guidelines](https://developers.hubspot.com/docs/developer-tooling/platform/usage-guidelines) -- Rate limits: 190/10s burst
- [HubSpot Webhooks v3 guide](https://developers.hubspot.com/docs/api-reference/legacy/webhooks/guide) -- Webhook subscription API
- [HubSpot v3 signature verification](https://developers.hubspot.com/changelog/introducing-version-3-of-webhook-signatures) -- method+url+body+timestamp HMAC-SHA256 base64
- [Resend Custom Headers docs](https://resend.com/docs/dashboard/emails/custom-headers) -- headers parameter in API request
- [Resend Webhooks introduction](https://resend.com/docs/webhooks/introduction) -- 15 event types including email.bounced, email.delivered, email.opened, email.clicked
- [RFC 8058](https://datatracker.ietf.org/doc/html/rfc8058) -- One-click List-Unsubscribe standard
- [hubspot-api-client PyPI](https://pypi.org/project/hubspot-api-client/) -- Version 12.0.0, May 2025

### Tertiary (LOW confidence)
- Resend auto-generated unsubscribe headers behavior -- docs mention auto-generation for audience sends but unclear for raw API sends. Recommend always sending explicit headers.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- hubspot-api-client is official SDK; Resend/Redis/Jinja2 already in project
- Architecture: HIGH -- following proven Phase 41 patterns (StripeSyncService, ShopifyService, dedicated webhook endpoints)
- Pitfalls: HIGH -- HubSpot rate limits, webhook sig v3, RFC 8058 requirements well-documented; sync loop prevention is known pattern
- Email deliverability: MEDIUM -- CAN-SPAM/RFC 8058 requirements verified, but email client tracking pixel behavior varies

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (30 days -- HubSpot SDK and Resend API are stable)
