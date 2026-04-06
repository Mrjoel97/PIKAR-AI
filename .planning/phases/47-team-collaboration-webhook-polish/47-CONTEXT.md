# Phase 47: Team Collaboration & Webhook Polish - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Two tracks: (1) Team collaboration — share initiatives and workflow runs across workspace members with role-based visibility, team analytics dashboard with aggregate and per-member KPIs, and a resource-grouped activity feed. (2) Webhook polish — user-facing CRUD for outbound webhook endpoints (config page + agent chat), browsable event catalog, Zapier-compatible payloads, delivery logs with signing secret and verification code snippets. All built on Phase 39 infrastructure (WorkspaceService, webhook_delivery_service, event catalog).

</domain>

<decisions>
## Implementation Decisions

### Shared Work & Visibility
- **Sharing model:** Claude's discretion — pick what fits the solopreneur-to-team upgrade path best (explicit share vs team-visible by default)
- **Admin visibility:** Full visibility — team admins see ALL initiatives, workflows, and agent interactions across the workspace. Regular members see only assigned/shared work.
- **Shared workflow interaction:** Claude's discretion on whether non-owners can act on shared workflows (view + approve vs view only)
- **Invitations:** Magic link only (existing WorkspaceService.create_invite_link pattern) — no email server dependency

### Team Analytics & Activity Feed
- **Dashboard KPIs:** Aggregate metrics by default (total workflows, initiatives, approvals across team), admin can drill down to per-member breakdown
- **Activity feed structure:** Grouped by resource — see all recent activity on a given initiative/workflow in one cluster, not a flat chronological stream
- **Feed refresh:** Claude's discretion based on existing SSE infrastructure complexity
- **Dashboard placement:** Dedicated `/dashboard/team` page — separate from personal dashboard

### Webhook Endpoint Management
- **Creation flow:** Both equally — full CRUD in config page AND agent tools for chat-based management. Users pick their preferred interaction style.
- **Event catalog:** Claude's discretion on presentation (browsable list vs inline during creation)
- **Delivery logs:** Claude's discretion on log presentation (per-endpoint vs global feed)
- **Test webhook send:** Claude's discretion on whether to include a "Send Test" button

### Zapier Compatibility & Payload Format
- **Zapier integration depth:** Claude's discretion for v6.0 — balance between full Zapier app listing and catch-hook compatibility
- **Payload structure:** Claude's discretion — balance developer experience with automation tool compatibility
- **Signing verification:** Show the endpoint's HMAC signing secret in the UI, with copy-paste verification code snippets (Node.js, Python, cURL) — like Stripe's signing docs
- **Webhook REST API:** Claude's discretion on whether a separate REST API adds value given chat + UI paths

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

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/workspace_service.py`: Full WorkspaceService — create workspace, invite (magic link), accept invite, role management (admin/member), member CRUD. Ready to extend with sharing logic.
- `app/services/webhook_delivery_service.py`: Complete delivery pipeline — enqueue, deliver with HMAC-SHA256, retry (5 attempts, exponential backoff), dead letter, per-endpoint circuit breaker. Need to add user-facing CRUD on top.
- `app/routers/teams.py`: Teams router with `require_feature("teams")` gate + `require_role("admin")` for write ops. Add sharing endpoints here.
- `app/routers/webhooks.py`: Currently handles inbound webhooks only (LinkedIn, Shopify, HubSpot). Extend or create separate outbound router.
- `app/models/webhook_events.py`: Webhook event models — extend with event catalog schema definitions.
- `app/services/dashboard_summary_service.py`: Dashboard KPI aggregation — extend with team-level queries.
- `app/services/kpi_service.py`: KPI computation — add workspace-scoped aggregation.

### Established Patterns
- Feature gating via `require_feature("teams")` middleware — team features use this gate
- Role-based access via `require_role("admin")` dependency — admin-only endpoints
- WorkspaceService CRUD pattern with governance service integration
- Event catalog hardcoded as Python dict with JSON schema definitions (Phase 39 decision)
- Agent tools for CRUD operations (monitoring tools from Phase 46 — same pattern for webhook tools)

### Integration Points
- `app/agents/operations/agent.py` — add webhook management tools here
- `frontend/src/app/dashboard/` — add `/team` page alongside existing persona dashboards
- `frontend/src/app/dashboard/configuration/page.tsx` — add WebhooksSection
- `app/fast_api_app.py` — register new routers (outbound webhooks, team analytics)
- Existing `enqueue_webhook_event` — already called from workflow engine; add calls from initiative/approval/task actions

</code_context>

<specifics>
## Specific Ideas

- Team analytics dashboard should feel like a manager's overview — glanceable aggregate KPIs at top, drill into per-member detail on demand
- Activity feed grouped by resource feels like GitHub's PR activity — all updates on "Q3 Campaign" in one thread
- Webhook signing verification snippets should be as polished as Stripe's — copy-paste ready for Node.js, Python, cURL
- Admin full visibility is intentional — team admins are accountable for all workspace activity

</specifics>

<deferred>
## Deferred Ideas

- **External agent connector:** Using the webhook/connector infrastructure to let external tools (Claude Code, other AI agents) plug into Pikar as an inbound API. Would be a great "Agent-to-Agent Protocol" or "External Agent Connector" phase — enables Pikar as a platform that other agents can call into.

</deferred>

---

*Phase: 47-team-collaboration-webhook-polish*
*Context gathered: 2026-04-06*
