# Phase 47: Team Collaboration & Webhook Polish - Research

**Researched:** 2026-04-06
**Domain:** Team data sharing / RBAC visibility + outbound webhook CRUD + Zapier-compatible payloads
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Admin visibility:** Full visibility — team admins see ALL initiatives, workflows, and agent interactions across the workspace. Regular members see only assigned/shared work.
- **Invitations:** Magic link only (existing WorkspaceService.create_invite_link pattern) — no email server dependency.
- **Dashboard KPIs:** Aggregate metrics by default (total workflows, initiatives, approvals across team), admin can drill down to per-member breakdown.
- **Activity feed structure:** Grouped by resource — see all recent activity on a given initiative/workflow in one cluster, not a flat chronological stream.
- **Dashboard placement:** Dedicated `/dashboard/team` page — separate from personal dashboard.
- **Creation flow:** Both equally — full CRUD in config page AND agent tools for chat-based management.
- **Signing verification:** Show the endpoint's HMAC signing secret in the UI, with copy-paste verification code snippets (Node.js, Python, cURL) — like Stripe's signing docs.

### Claude's Discretion
- Sharing model (explicit share vs team-visible by default)
- Shared workflow interaction level (view + approve vs view only)
- Activity feed refresh mechanism (SSE vs load)
- Event catalog presentation
- Delivery log presentation
- Test webhook feature inclusion
- Zapier integration depth (full app vs catch-hook compatible)
- Payload structure (flat vs nested)
- Webhook REST API inclusion

### Deferred Ideas (OUT OF SCOPE)
- External agent connector — using webhook/connector infrastructure to let external tools (Claude Code, other AI agents) plug into Pikar as an inbound API.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEAM-01 | Team members can share initiatives and view shared workflow runs | `workspace_data_filter.get_workspace_user_ids` already implements shared data queries; sharing logic needs extension in teams router |
| TEAM-02 | Team-level analytics dashboard showing aggregate KPIs | `DashboardSummaryService` already uses `scoped_user_ids`; need new `/dashboard/team` page pulling workspace-scoped data |
| TEAM-03 | Role-based visibility (team admin sees all, member sees assigned work) | `WorkspaceService.get_member_role` + `require_role("admin")` pattern established; apply same to resource queries |
| TEAM-04 | Activity feed showing team member actions on shared resources | `governance_audit_log` table exists; needs resource-grouped query endpoint |
| HOOK-01 | User can create outbound webhook endpoints for Pikar events | `webhook_endpoints` table and `webhook_delivery_service` exist; need CRUD REST endpoints + UI |
| HOOK-02 | Event catalog listing all available trigger events with payload schemas | `EVENT_CATALOG` dict in `app/models/webhook_events.py` exists with 9 events and JSON schemas |
| HOOK-03 | Zapier-compatible webhook format (standard JSON payload structure) | Need envelope wrapper; existing payload format is bare event data — add `event`, `timestamp`, `version` envelope |
| HOOK-04 | Webhook delivery log with success/failure status visible in config page | `webhook_deliveries` table exists with status/attempts/response_code; need read endpoint + frontend section |
| HOOK-05 | Agent can create and manage webhook endpoints via chat commands | New `WEBHOOK_TOOLS` list following `COMMUNICATION_TOOLS` / `PM_TASK_TOOLS` pattern |
</phase_requirements>

---

## Summary

Phase 47 has two tracks that share a common pattern: surface existing backend infrastructure through user-facing APIs and UI.

**Track 1 — Team Collaboration:** The core data model (workspaces, workspace_members, workspace_invites, roles) and the workspace_data_filter helper are already live from Phase 35/39. `DashboardSummaryService` already fetches workspace-scoped data via `get_workspace_user_ids`. What is missing: (a) a dedicated `/dashboard/team` page with aggregate KPI tiles and per-member drill-down, (b) resource-grouped activity feed from governance_audit_log, (c) role-based query enforcement at the router level for admin-vs-member visibility, and (d) sharing API endpoints on the teams router. The sharing model decision (explicit vs team-visible by default) should be team-visible by default for resources created by workspace members, as this aligns with the workspace_data_filter approach already in place.

**Track 2 — Webhook Polish:** The outbound delivery pipeline (`webhook_endpoints`, `webhook_deliveries`, `webhook_delivery_service`) is fully built from Phase 39. The event catalog with 9 event types and JSON schemas lives in `app/models/webhook_events.py`. What is missing: (a) user-facing CRUD REST endpoints for managing webhook endpoints, (b) a `WebhooksSection` UI component in the configuration page, (c) Zapier-compatible payload envelope, (d) delivery log read endpoint + UI, and (e) agent tools for webhook CRUD. Agent tools follow the established `COMMUNICATION_TOOLS` / `PM_TASK_TOOLS` pattern.

**Primary recommendation:** Follow the incremental extension pattern used in phases 44-46: add new router with minimal new tables, extend existing services with targeted methods, wire agent tools to the new router, add frontend section to the existing configuration page.

---

## Standard Stack

### Core (already in project)
| Library/Service | Version | Purpose | Notes |
|----------------|---------|---------|-------|
| FastAPI | (project version) | REST endpoints | All routers follow established patterns |
| Supabase (postgrest-py) | (project version) | DB queries | `execute_async` + service-role client pattern |
| `app.services.workspace_service.WorkspaceService` | internal | Workspace + member CRUD | Already covers invite, role, member CRUD |
| `app.services.webhook_delivery_service` | internal | Delivery pipeline | enqueue, retry, circuit breaker all done |
| `app.models.webhook_events.EVENT_CATALOG` | internal | Event catalog | 9 events, JSON schemas defined |
| `app.services.workspace_data_filter.get_workspace_user_ids` | internal | Shared data scoping | Core building block for team visibility |
| `app.services.governance_service.GovernanceService` | internal | Audit log | `log_event` used by all routers for audit trail |
| `app.middleware.feature_gate.require_feature` | internal | Feature gating | `require_feature("teams")` on all team endpoints |
| `app.middleware.workspace_role.require_role` | internal | Role gating | `require_role("admin")` for admin-only ops |

### Supporting
| Library | Purpose | When to Use |
|---------|---------|-------------|
| `app.services.encryption.encrypt_secret` | Encrypt new webhook signing secrets | When creating new webhook endpoints |
| `app.services.encryption.decrypt_secret` | Used internally by delivery service | Already wired |
| `hmac` / `hashlib` (stdlib) | HMAC-SHA256 signature computation | For "Test Webhook" and verification snippets |
| `secrets` (stdlib) | Generate signing secrets | Same pattern as invite tokens in WorkspaceService |

### Alternatives Considered
| Standard | Alternative | Tradeoff |
|----------|-------------|----------|
| Team-visible by default (workspace_data_filter pattern) | Explicit share per resource | Default visibility aligns with existing workspace_data_filter — avoids new sharing columns/tables |
| Per-page delivery log in config UI | Global feed | Per-endpoint log is cleaner UX; matches CONTEXT.md "Claude's discretion" |
| Catch-hook compatible Zapier (no partner listing) | Full Zapier app | Full partner listing requires Zapier review (explicitly deferred as FUTURE-01) |

---

## Architecture Patterns

### Recommended Project Structure (new files only)
```
app/
├── routers/
│   └── outbound_webhooks.py      # CRUD for webhook_endpoints + delivery log reads
├── agents/tools/
│   └── webhook_tools.py          # WEBHOOK_TOOLS list (CRUD via outbound_webhooks router)
└── services/
    └── team_analytics_service.py  # Team KPI aggregation + activity feed

frontend/src/app/dashboard/
├── team/
│   └── page.tsx                  # /dashboard/team — team analytics page
│   └── join/
│       └── page.tsx              # /dashboard/team/join?token=... (already exists)

supabase/migrations/
└── YYYYMMDD_shared_resources.sql  # shared_initiatives, shared_workflows tables (if explicit share chosen)
```

### Pattern 1: Outbound Webhook CRUD Router
**What:** New `app/routers/outbound_webhooks.py` with full CRUD for `webhook_endpoints`, event catalog read, and delivery log reads. Separate from `app/routers/webhooks.py` (inbound only).
**When to use:** All webhook management operations.
**Key implementation notes:**
- Use `require_feature("teams")` is NOT needed — webhooks are available to all tiers
- Use user_id from JWT for ownership; service client for delivery log reads
- Encrypt signing secret with `encrypt_secret` on create; return plaintext secret ONCE on creation response (never again — show in UI on create only, like Stripe)
- `GET /outbound-webhooks/events` returns EVENT_CATALOG as list

```python
# Source: established router pattern (app/routers/teams.py)
router = APIRouter(prefix="/outbound-webhooks", tags=["Outbound Webhooks"])

@router.get("/events")
async def list_event_catalog() -> list[dict]:
    from app.models.webhook_events import EVENT_CATALOG
    return [
        {"event_type": k, "description": v["description"], "schema": v["payload_schema"]}
        for k, v in EVENT_CATALOG.items()
    ]

@router.post("/endpoints", response_model=WebhookEndpointResponse)
async def create_endpoint(body: CreateEndpointRequest, user_id=Depends(get_current_user_id)):
    secret = secrets.token_urlsafe(32)
    encrypted = encrypt_secret(secret)
    # insert webhook_endpoints row
    # return endpoint + plaintext secret (only time it's returned)
    ...

@router.get("/endpoints/{endpoint_id}/deliveries")
async def get_delivery_log(endpoint_id: str, user_id=Depends(get_current_user_id)):
    # verify endpoint belongs to user, then query webhook_deliveries
    ...
```

### Pattern 2: Zapier-Compatible Payload Envelope
**What:** Wrap bare event payloads in a standard envelope before delivery.
**When to use:** All `enqueue_webhook_event` calls.
**Recommendation:** Flat envelope + nested `data` — mirrors Stripe/Zapier standard.

```python
# Source: Zapier/Stripe webhook standard
payload_envelope = {
    "id": str(uuid.uuid4()),          # unique delivery ID
    "event": event_type,              # e.g. "task.created"
    "api_version": "2026-04",
    "timestamp": datetime.now(UTC).isoformat(),
    "data": original_payload          # existing event payload
}
```

The envelope change should happen in `enqueue_webhook_event` so all existing callers get the standard format automatically. The `data` field preserves backward compatibility — original consumers still find the same fields, just nested.

### Pattern 3: Team Analytics Service
**What:** `TeamAnalyticsService` that queries workspace-scoped KPIs and the activity feed.
**When to use:** Called by the `/dashboard/team` page endpoint.

```python
# Source: app/services/dashboard_summary_service.py pattern
class TeamAnalyticsService:
    async def get_team_kpis(self, workspace_id: str) -> dict:
        member_ids = [m["user_id"] for m in await ws_service.get_workspace_members(workspace_id)]
        # Count workflows, initiatives, tasks, approvals across all member_ids
        # Return per-member breakdown as well (admin can drill down)
        ...

    async def get_activity_feed(self, workspace_id: str, limit: int = 50) -> list[dict]:
        # Query governance_audit_log for all member_ids in workspace
        # Group by resource_type + resource_id
        # Return resource-grouped clusters
        ...
```

### Pattern 4: Webhook Agent Tools
**What:** `WEBHOOK_TOOLS` list following the `COMMUNICATION_TOOLS` pattern exactly.
**When to use:** Wire into `OPERATIONS_AGENT_TOOLS` spread in `app/agents/operations/agent.py`.

```python
# Source: app/agents/tools/communication_tools.py pattern
WEBHOOK_TOOLS = [
    list_webhook_endpoints,
    create_webhook_endpoint,
    delete_webhook_endpoint,
    list_webhook_events,       # returns EVENT_CATALOG summary
    get_webhook_delivery_log,
]
```

### Pattern 5: Team Visibility — Role Enforcement
**What:** Admin sees all workspace members' data; member sees only their own + explicitly shared resources.
**Decision:** Use `get_workspace_user_ids` for members (returns all co-member IDs), but gate per-member breakdown behind role check.

```python
# In team analytics endpoint:
role = await workspace_service.get_member_role(user_id, workspace_id)
scoped_ids = await get_workspace_user_ids(user_id)
if role == "admin":
    # return per-member breakdown
    member_breakdown = await team_analytics.get_per_member_kpis(workspace_id)
else:
    # return only aggregate, no per-member detail
    member_breakdown = None
```

### Anti-Patterns to Avoid
- **Adding workspace_id columns to existing tables:** The established pattern is application-layer workspace scoping via `workspace_data_filter`. Do not add `workspace_id` FK to `initiatives`, `workflow_executions`, etc.
- **Returning plaintext secrets after creation:** Follow Stripe model — only return plaintext on POST, encrypted thereafter. Config page shows masked secret + "Regenerate" option.
- **Building a separate delivery worker for "send test":** Reuse the existing `_deliver_single` function with a synthetic delivery row — don't bypass the signing logic.
- **Separate outbound webhook router confusion:** Keep `app/routers/webhooks.py` for inbound only; new `app/routers/outbound_webhooks.py` for user-facing outbound CRUD. Prevents naming collisions.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Webhook delivery with retry | Custom retry loop | `webhook_delivery_service.enqueue_webhook_event` | Phase 39 — full backoff, circuit breaker, dead letter already done |
| HMAC-SHA256 signing | Custom signing | `webhook_delivery_service._deliver_single` | Already signs correctly with X-Pikar-Signature header |
| Workspace membership/invite | Custom RBAC tables | `WorkspaceService` | Full CRUD with role checks already implemented |
| Workspace-scoped data queries | Adding workspace_id columns | `get_workspace_user_ids` | Application-layer pattern already deployed to 10+ tables |
| Secret encryption | Custom crypto | `encrypt_secret` / `decrypt_secret` | Fernet encryption consistent with all integration credentials |
| Governance audit entries | Custom log table | `GovernanceService.log_event` | Teams router already uses this pattern |

---

## Common Pitfalls

### Pitfall 1: Exposing Plaintext Signing Secrets in GET Responses
**What goes wrong:** The `webhook_endpoints` table stores the encrypted secret. If a GET endpoint decrypts and returns it in every API response, secrets leak into logs, browser history, and frontend state.
**Why it happens:** Temptation to show the secret for UX convenience.
**How to avoid:** Return plaintext secret ONLY in the POST creation response (one-time). Subsequent GETs return `secret_preview: "whsec_••••••••{last4}"`. Provide a "Regenerate Secret" action to replace it.
**Warning signs:** `decrypt_secret` called in a list/get endpoint.

### Pitfall 2: Activity Feed N+1 on governance_audit_log
**What goes wrong:** Fetching activity for each resource individually produces N+1 queries.
**Why it happens:** Naive implementation queries per initiative, per workflow.
**How to avoid:** Single query with `.in_("resource_id", resource_ids)` filtered by member_ids, then group in Python. Limit to last 100 rows.
**Warning signs:** Loop calling execute_async per resource.

### Pitfall 3: Role Check Missing on Team Analytics Endpoint
**What goes wrong:** Members can access per-member KPI breakdown (which reveals teammates' work volumes).
**Why it happens:** Dashboard endpoint returns all data; role check omitted.
**How to avoid:** Add `role = await workspace_service.get_member_role(user_id, workspace_id)` check; gate `member_breakdown` on `role == "admin"`.

### Pitfall 4: Payload Envelope Breaking Existing enqueue_webhook_event Callers
**What goes wrong:** Adding the Zapier envelope changes the payload structure that existing consumers (workflow engine, etc.) already send.
**Why it happens:** `enqueue_webhook_event` is called from multiple places with raw event dicts.
**How to avoid:** Wrap payload in envelope INSIDE `enqueue_webhook_event` before inserting to `webhook_deliveries`. Existing callers pass the `data` portion; the function adds envelope fields. No caller changes needed.

### Pitfall 5: Webhook CRUD Endpoints Without Feature Gate Check
**What goes wrong:** Webhook CRUD endpoints should be available to all users (not just team tier), but accidentally gated.
**Why it happens:** Copy-paste from teams router which has `require_feature("teams")` dependency on the router.
**How to avoid:** `outbound_webhooks` router has NO router-level feature gate. The TEAM-01 to TEAM-04 endpoints stay on the gated `teams` router; HOOK-01 to HOOK-05 go on the ungated `outbound_webhooks` router.

---

## Code Examples

### Webhook Endpoint Create/List (established router pattern)
```python
# Source: app/routers/teams.py + app/services/workspace_service.py pattern
class CreateWebhookEndpointRequest(BaseModel):
    url: str
    events: list[str]
    description: str | None = None

class WebhookEndpointResponse(BaseModel):
    id: str
    url: str
    events: list[str]
    active: bool
    consecutive_failures: int
    created_at: str
    # secret_preview only — full secret returned once on POST
    secret_preview: str

@router.post("/endpoints")
async def create_webhook_endpoint(
    body: CreateEndpointRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    secret = secrets.token_urlsafe(32)
    encrypted = encrypt_secret(secret)
    # validate events against EVENT_CATALOG
    # insert to webhook_endpoints
    # return endpoint + plaintext secret (only time)
    return {"endpoint": endpoint_row, "secret": secret}
```

### Activity Feed Query (group-by-resource pattern)
```python
# Source: dashboard_summary_service.py pattern extended for team
async def get_activity_feed(self, workspace_id: str) -> list[dict]:
    members = await self.ws_service.get_workspace_members(workspace_id)
    member_ids = [m["user_id"] for m in members]

    rows = await self._safe_rows(
        self.client.table("governance_audit_log")
        .select("user_id, action_type, resource_type, resource_id, details, created_at")
        .in_("user_id", member_ids)
        .order("created_at", desc=True)
        .limit(100)
    )

    # Group by (resource_type, resource_id)
    groups: dict[tuple, list] = {}
    for row in rows:
        key = (row["resource_type"], row["resource_id"])
        groups.setdefault(key, []).append(row)

    return [
        {"resource_type": k[0], "resource_id": k[1], "events": v}
        for k, v in groups.items()
    ]
```

### Zapier-Compatible Envelope (enqueue_webhook_event modification)
```python
# Source: Stripe/Zapier webhook standard; modify app/services/webhook_delivery_service.py
import uuid

async def enqueue_webhook_event(event_type: str, payload: dict) -> int:
    envelope = {
        "id": str(uuid.uuid4()),
        "event": event_type,
        "api_version": "2026-04",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "data": payload,
    }
    # rest of function uses `envelope` instead of `payload`
```

### Signing Verification Snippets (Stripe pattern)
```python
# Node.js snippet template (rendered in frontend):
NODE_SNIPPET = """
const crypto = require('crypto');
const sig = req.headers['x-pikar-signature']; // "sha256=..."
const computed = 'sha256=' + crypto.createHmac('sha256', SECRET)
    .update(JSON.stringify(req.body)).digest('hex');
if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(computed))) {
    throw new Error('Invalid signature');
}
"""

PYTHON_SNIPPET = """
import hmac, hashlib, json
sig = request.headers['X-Pikar-Signature']  # "sha256=..."
computed = 'sha256=' + hmac.new(SECRET.encode(), 
    json.dumps(payload, separators=(',',':')).encode(),
    hashlib.sha256).hexdigest()
assert hmac.compare_digest(sig, computed), 'Invalid signature'
"""
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pytest.ini` or `pyproject.toml` (existing) |
| Quick run command | `uv run pytest tests/unit/test_outbound_webhooks.py tests/unit/test_team_analytics.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEAM-01 | Shared initiatives/workflows visible to workspace members | unit | `uv run pytest tests/unit/test_team_analytics.py::TestTeamSharing -x` | Wave 0 |
| TEAM-02 | Team KPI endpoint returns aggregate + per-member for admin | unit | `uv run pytest tests/unit/test_team_analytics.py::TestTeamKpis -x` | Wave 0 |
| TEAM-03 | Members get aggregate only; admin gets per-member breakdown | unit | `uv run pytest tests/unit/test_team_analytics.py::TestRoleVisibility -x` | Wave 0 |
| TEAM-04 | Activity feed groups events by resource | unit | `uv run pytest tests/unit/test_team_analytics.py::TestActivityFeed -x` | Wave 0 |
| HOOK-01 | Webhook endpoint CRUD (create, list, delete, activate/deactivate) | unit | `uv run pytest tests/unit/test_outbound_webhooks.py::TestEndpointCrud -x` | Wave 0 |
| HOOK-02 | Event catalog endpoint returns all 9 events with schemas | unit | `uv run pytest tests/unit/test_outbound_webhooks.py::TestEventCatalog -x` | Wave 0 |
| HOOK-03 | Envelope wraps payload with event/timestamp/api_version/data | unit | `uv run pytest tests/unit/test_outbound_webhooks.py::TestZapierEnvelope -x` | Wave 0 |
| HOOK-04 | Delivery log endpoint returns deliveries for owned endpoint | unit | `uv run pytest tests/unit/test_outbound_webhooks.py::TestDeliveryLog -x` | Wave 0 |
| HOOK-05 | Agent tools create/list/delete endpoints via chat commands | unit | `uv run pytest tests/unit/test_outbound_webhooks.py::TestWebhookTools -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/test_outbound_webhooks.py tests/unit/test_team_analytics.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_outbound_webhooks.py` — covers HOOK-01 through HOOK-05
- [ ] `tests/unit/test_team_analytics.py` — covers TEAM-01 through TEAM-04
- [ ] `tests/unit/services/test_team_analytics_service.py` — unit tests for TeamAnalyticsService

*(Existing `tests/unit/test_webhook_service.py` covers the Phase 39 delivery infrastructure and does NOT need to change.)*

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No sharing | `get_workspace_user_ids` application-layer scoping | Phase 35/39 | All major data queries already workspace-aware |
| No outbound webhooks | Full delivery pipeline with circuit breaker | Phase 39 | Only CRUD UI + Zapier envelope missing |
| Bare payload | Zapier-compatible envelope (to add) | Phase 47 | Enables native Zapier catch-hook compatibility without partner listing |

**Deprecated/outdated:**
- Nothing deprecated — all Phase 39 infrastructure is current and in production.

---

## Open Questions

1. **Sharing model: team-visible by default vs explicit share**
   - What we know: `get_workspace_user_ids` already returns all co-member IDs and is used in DashboardSummaryService, meaning initiatives/workflows created by ANY workspace member are already partially visible via the home dashboard.
   - Recommendation: **Team-visible by default** — consistent with existing behavior, simpler implementation (no new sharing columns), matches the "workspace as shared context" mental model. Members who want private work can create resources in a solo workspace.

2. **Activity feed refresh: SSE vs on-load polling**
   - What we know: The project uses SSE for long-running operations (chat, file imports). GovernanceService log queries are fast Supabase reads.
   - Recommendation: **On-load + manual refresh button** for Phase 47. The activity feed is not a real-time dashboard — it's a history view. SSE adds complexity without clear benefit here. Can be upgraded in a future phase.

3. **Test webhook "Send Test" button**
   - What we know: The delivery service `_deliver_single` function can be called directly with a synthetic delivery row.
   - Recommendation: **Include it** — it's high value for users verifying their webhook URL. Simple: POST `/outbound-webhooks/endpoints/{id}/test` → build synthetic payload for a sample event, call `_deliver_single` or `httpx.post` directly.

4. **Webhook endpoint description field**
   - What we know: `webhook_endpoints` table has no description column.
   - Recommendation: Add optional `description text` column in the Phase 47 migration. Low cost, high UX value (users can label "Zapier Automation" vs "n8n Integration").

---

## Sources

### Primary (HIGH confidence)
- Direct code reading: `app/services/workspace_service.py` — confirmed WorkspaceService API surface
- Direct code reading: `app/services/webhook_delivery_service.py` — confirmed delivery pipeline API
- Direct code reading: `app/models/webhook_events.py` — confirmed EVENT_CATALOG shape (9 events, JSON schemas)
- Direct code reading: `app/services/workspace_data_filter.py` — confirmed team scoping pattern
- Direct code reading: `supabase/migrations/20260404600000_webhook_infrastructure.sql` — confirmed table schema for webhook_endpoints and webhook_deliveries
- Direct code reading: `supabase/migrations/20260403200000_teams_rbac.sql` — confirmed workspace, workspace_members, workspace_invites schema + RLS
- Direct code reading: `app/routers/teams.py` — confirmed require_feature("teams") + require_role("admin") pattern
- Direct code reading: `app/agents/tools/communication_tools.py` + `pm_task_tools.py` — confirmed WEBHOOK_TOOLS list pattern
- Direct code reading: `app/services/dashboard_summary_service.py` — confirmed workspace-scoped query pattern + governance_audit_log usage
- Direct code reading: `app/fast_api_app.py` — confirmed router registration pattern

### Secondary (MEDIUM confidence)
- Zapier webhook standard (well-known): flat JSON, `event` + `timestamp` + `data` envelope — matches Stripe/GitHub patterns
- Stripe signing docs (well-known): one-time secret reveal on create, masked thereafter, HMAC-SHA256 verification snippets

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — read directly from source code, all infrastructure confirmed in place
- Architecture: HIGH — patterns derived from 5+ existing routers/tools following identical structure
- Pitfalls: HIGH — discovered from direct code review (encrypted secrets, N+1 patterns, role enforcement gaps)

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable infrastructure, no external library changes needed)
