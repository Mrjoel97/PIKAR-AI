# Phase 44: Project Management Integration - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Connect Linear and Asana via OAuth for bidirectional task synchronization. Tasks explicitly created through the agent or UI sync outbound. Issues from user-selected projects sync inbound into a new `synced_tasks` table. Status changes map bidirectionally with sensible defaults and user-customizable mapping. The OperationsAgent can list, create, and update issues via chat.

</domain>

<decisions>
## Implementation Decisions

### Which Tasks Sync (Outbound: Pikar → PM Tool)
- **Only explicitly tagged tasks** sync outbound to Linear/Asana
- Agent recognizes platform references in commands: "create a bug ticket in Linear", "add this to Asana", "as a Linear issue"
- If the user just says "create a task" without mentioning a PM tool, it stays local in Pikar
- Agent may prompt: "Want me to create this in Linear too?" when context suggests it would be useful
- Internal agent processing tasks (`ai_jobs`) and department handoffs (`department_tasks`) never auto-sync

### Which Tasks Sync (Inbound: PM Tool → Pikar)
- **New `synced_tasks` table** purpose-built for bidirectional sync
  - Columns: id, user_id, external_id, provider (linear/asana), external_project_id, title, description, status (pending/in_progress/completed/cancelled), priority, assignee, labels, metadata JSONB, created_at, updated_at
  - UNIQUE constraint on (user_id, provider, external_id)
  - RLS per user
- External issues land here — kept separate from `ai_jobs` (agent queue) and `department_tasks` (internal handoffs)
- When an agent creates a task "in Linear", it creates both a `synced_tasks` record AND the Linear issue simultaneously

### Sync Scope & Filtering
- **User picks projects to sync** after OAuth connection
  - Settings page shows a project picker: checkboxes for Linear teams/projects or Asana projects
  - Only issues from selected projects sync into Pikar
  - Project selection stored in `integration_sync_state.sync_cursor` JSONB (or a new sync config table — Claude's discretion)
- **Initial sync:** Import issues updated in the last 30 days from selected projects
  - Gives immediate context without overwhelming with old closed issues
- **Real-time sync:** Webhooks from Linear/Asana for new/updated issues going forward
- **UI on settings page:** After OAuth, project list appears on the integration card with checkboxes and issue counts

### Status Mapping
- **Sensible defaults with user override:**
  - Linear defaults: Triage/Backlog/Todo → pending, In Progress → in_progress, Done → completed, Cancelled → cancelled
  - Asana defaults: Not Started → pending, In Progress → in_progress, Complete → completed
  - User can customize the mapping on the settings page (dropdown per external state → Pikar state)
- **Bidirectional status sync:** Completing a task in Pikar marks it Done in Linear. Moving to in_progress in Pikar moves it to In Progress in Linear. Uses the same mapping table in reverse.
- **Conflict resolution:** Last-write-wins with logging — same pattern as Phase 42 HubSpot sync
- **Loop prevention:** Redis skip-flag with 30s TTL (Phase 42 pattern) — prevents Pikar→Linear→webhook→Pikar infinite loops

### Agent Task Commands
- **OperationsAgent** gets Linear/Asana task management tools — operations handles project management, task coordination, workflow orchestration
- **Auto-detect connected provider:** If only Linear connected → use Linear. If only Asana → use Asana. If both → ask "Linear or Asana?" on first ambiguous command, remember preference.
- **Default issue context:** Agent sets title + description + target project. Priority and labels are optional — set if user mentions them, otherwise use defaults. Assignee left blank unless specified.
- **Tools:**
  - `list_pm_tasks(project?, status?, provider?)` — list synced tasks with filters
  - `create_pm_task(title, description, project, provider?, priority?, labels?)` — creates in PM tool + synced_tasks
  - `update_pm_task(task_id, status?, title?, description?, priority?)` — updates both Pikar and PM tool
  - `get_pm_projects(provider?)` — list available projects from connected PM tool

### Claude's Discretion
- Linear SDK vs httpx REST API choice
- Asana SDK vs httpx REST API choice
- Exact webhook event types to subscribe to
- Status mapping storage (new table vs integration_sync_state metadata)
- Project picker component styling
- Sync worker scheduling (integrated into existing workflow_trigger_service or dedicated)
- Error handling for webhook delivery failures
- How to handle Asana custom fields

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/config/integration_providers.py`: Linear and Asana already registered in PROVIDER_REGISTRY with OAuth URLs and scopes
- `app/services/integration_manager.py`: Phase 39 credential storage + token refresh with async locking
- `app/routers/integrations.py`: OAuth authorize/callback flow — Linear and Asana can connect today
- `app/services/hubspot_service.py`: Bidirectional sync pattern with Redis skip-flag loop prevention (Phase 42)
- `app/services/shopify_service.py`: Webhook processing + external API sync pattern (Phase 41)
- `app/services/department_task_service.py`: Task CRUD with status/priority enums — pattern for synced_tasks service
- `app/routers/webhooks.py`: Generalized inbound webhook with HMAC verification (Phase 39)
- `app/services/cache.py`: Redis operations for skip-flag pattern
- `app/notifications/notification_service.py`: Notification delivery for sync status alerts

### Established Patterns
- External API sync: wrap sync SDK in asyncio.to_thread, store external_id, UNIQUE constraint
- Bidirectional sync: Redis skip-flag (30s TTL) prevents infinite loops, last-write-wins with logging
- Webhook processing: inbound → HMAC verify → webhook_events → process
- Agent tools: raw async function exports, sanitize_tools wraps at agent level
- Integration config: settings page provider cards with expandable details

### Integration Points
- `app/agents/operations/agent.py`: Add Linear/Asana task management tools on OperationsAgent
- `app/config/integration_providers.py`: Linear and Asana already registered — no changes needed
- `app/routers/webhooks.py`: Add Linear + Asana webhook handlers
- `app/routers/integrations.py`: Add project listing + sync config endpoints
- `frontend/src/app/dashboard/configuration/page.tsx`: Add project picker to Linear/Asana cards + status mapping UI
- `supabase/migrations/`: New synced_tasks table + optional status_mapping table

</code_context>

<specifics>
## Specific Ideas

- Project picker should feel like GitHub's repository selection — simple checkboxes, not a complex tree
- Status mapping defaults should "just work" for 90% of users — the override is for power users with custom Linear workflows
- Agent should feel natural: "create a bug in Linear for the checkout crash" → creates issue with title "Checkout crash", description from context, in the synced Engineering project
- Bidirectional sync should be invisible — user completes a task in Linear, it's completed in Pikar by the time they check

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 44-project-management-integration*
*Context gathered: 2026-04-05*
