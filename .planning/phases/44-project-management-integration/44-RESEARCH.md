# Phase 44: Project Management Integration — Research

**Researched:** 2026-04-05
**Phase Goal:** Bidirectional task synchronization with Linear and Asana

## Executive Summary

Phase 44 connects Pikar to Linear and Asana for bidirectional task sync. Linear and Asana are already in PROVIDER_REGISTRY (Phase 39), so OAuth connection works out of the box. The main work is: (1) new `synced_tasks` table for external issues, (2) Linear API client service with GraphQL, (3) Asana API client service with REST, (4) bidirectional sync with status mapping and Redis skip-flag loop prevention, (5) webhook handlers for real-time updates, (6) agent tools on OperationsAgent, (7) frontend project picker + status mapping UI.

## Codebase Analysis

### What Already Exists

**Provider registry (`app/config/integration_providers.py`):**
- `linear`: OAuth2, auth_url `https://linear.app/oauth/authorize`, scopes `["read", "write", "issues:create", "comments:create"]`, webhook header `Linear-Signature`
- `asana`: OAuth2, auth_url `https://app.asana.com/-/oauth_authorize`, scopes `["default"]`, webhook header `X-Hook-Secret`

**Integration infrastructure (Phase 39):**
- `IntegrationManager` — credential storage, token refresh with async locking
- `integrations.py` router — OAuth authorize/callback flow
- `webhooks.py` router — inbound webhook with HMAC verification
- Frontend configuration page with provider cards

**Bidirectional sync pattern (Phase 42 HubSpot):**
- `HubSpotService` — asyncio.to_thread for sync SDK, AdminService for DB writes
- Redis skip-flag: `pikar:hubspot:skip:{id}` with 30s TTL prevents sync loops
- Last-write-wins conflict resolution with logging

**Task systems in Pikar:**
- `ai_jobs` table — agent processing queue (TaskService)
- `department_tasks` table — cross-department handoffs with status enum: pending/in_progress/completed/cancelled
- Neither is suitable for external PM sync — new `synced_tasks` table needed per CONTEXT.md

**OperationsAgent (`app/agents/operations/agent.py`):**
- Has task CRUD tools from sales module (create_task, get_task, list_tasks, update_task)
- Has skill tools, security/cloud guides, inventory, API connectors
- Sub-agent architecture with routing model
- Will receive new PM task management tools

### What Must Be Built

1. **Database migration** — `synced_tasks` table + `pm_status_mappings` table
2. **LinearService** — GraphQL API client for issues, projects, teams, webhooks
3. **AsanaService** — REST API client for tasks, projects, sections, webhooks
4. **PMSyncService** — Bidirectional sync orchestrator with status mapping + conflict resolution
5. **Webhook handlers** — Linear + Asana inbound webhook processing
6. **Agent tools** — `PM_TASK_TOOLS` list on OperationsAgent
7. **Frontend** — Project picker + status mapping UI on Linear/Asana cards
8. **Integration endpoints** — Project listing, sync config, status mapping CRUD

## Technical Decisions

### Linear API

**API type:** GraphQL (`https://api.linear.app/graphql`)

**Recommendation:** Use `httpx` with direct GraphQL queries (not the `linear` Python SDK which is community-maintained and may lag). Linear's GraphQL is well-documented and simple.

**Key queries/mutations:**
- `teams { nodes { id name } }` — list teams (Linear's equivalent of projects)
- `team(id) { issues { nodes { id title description state { name } priority assignee { name } labels { nodes { name } } } } }` — list issues
- `issueCreate(input: { title, description, teamId, priority, stateId })` — create issue
- `issueUpdate(id, input: { title, description, stateId, priority })` — update issue
- `workflowStates(filter: { team: { id: { eq: $teamId } } }) { nodes { id name type } }` — list workflow states for status mapping

**Webhook events:** `Issue` (create, update, remove). Linear signs webhooks with HMAC-SHA256 using the webhook signing secret.

**Rate limits:** 1,500 complexity points per minute. Simple queries cost ~1 point. Batch queries with pagination use more.

### Asana API

**API type:** REST (`https://app.asana.com/api/1.0/`)

**Recommendation:** Use `httpx` directly. Asana REST API is straightforward.

**Key endpoints:**
- `GET /workspaces` — list workspaces
- `GET /projects?workspace={id}` — list projects
- `GET /tasks?project={id}&opt_fields=name,notes,completed,assignee.name,memberships.section.name` — list tasks
- `POST /tasks` — create task with `{ name, notes, projects: [id], assignee }` 
- `PUT /tasks/{id}` — update task
- `GET /sections?project={id}` — list sections (used for status mapping)

**Webhook events:** Asana uses webhook subscriptions per resource. Subscribe to project events: `POST /webhooks` with `{ resource: project_gid, target: callback_url }`. Asana webhook handshake requires responding to `X-Hook-Secret` header on first call.

**Rate limits:** 150 requests per minute per user token. Standard tier.

### Status Mapping Storage

**New `pm_status_mappings` table:**
```sql
CREATE TABLE pm_status_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    provider TEXT NOT NULL CHECK (provider IN ('linear', 'asana')),
    external_state_id TEXT NOT NULL,
    external_state_name TEXT NOT NULL,
    pikar_status TEXT NOT NULL CHECK (pikar_status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    UNIQUE (user_id, provider, external_state_id)
);
```

**Default mappings seeded on first sync config save:**
- Linear: state.type `triage`/`backlog`/`unstarted` → pending, `started` → in_progress, `completed` → completed, `cancelled` → cancelled
- Asana: section-based — first section → pending, middle sections → in_progress, last section → completed

### Sync Architecture

**Bidirectional with Redis skip-flag (Phase 42 pattern):**

1. **Pikar → PM tool:** When agent creates/updates a synced_task:
   - Set Redis flag `pikar:pm:skip:{external_id}` (TTL 30s)
   - Call Linear/Asana API
   - Update synced_tasks record

2. **PM tool → Pikar (webhook):** When webhook arrives:
   - Check Redis flag — if set, skip (prevents loop)
   - Upsert synced_tasks record with mapped status
   - Set Redis flag `pikar:pm:skip:{external_id}` (TTL 30s)

3. **Conflict:** Last-write-wins with logging, same as HubSpot.

### Project Sync Configuration

**Storage:** `integration_sync_state.sync_cursor` JSONB field (already exists):
```json
{
  "synced_projects": ["team_abc123", "team_def456"],
  "status_mapping_seeded": true,
  "last_full_sync": "2026-04-05T12:00:00Z"
}
```

**Initial sync flow:**
1. User connects Linear/Asana via OAuth
2. Frontend fetches available projects/teams via `GET /integrations/{provider}/projects`
3. User selects projects → `PUT /integrations/{provider}/sync-config` saves to sync_cursor
4. Backend runs initial sync: import issues updated in last 30 days from selected projects
5. Backend registers webhook subscriptions for selected projects

## Validation Architecture

### Requirement Coverage

| Req ID | What to Validate | How |
|--------|-----------------|-----|
| PM-01 | Linear OAuth connect | Provider in registry, OAuth flow works, credentials stored encrypted |
| PM-02 | Asana OAuth connect | Same as PM-01 for Asana |
| PM-03 | Bidirectional task sync | Create in Pikar → appears in Linear/Asana; create in Linear/Asana → appears in synced_tasks |
| PM-04 | Status mapping | Default mappings applied, custom overrides work, bidirectional status changes propagate |
| PM-05 | Agent task commands | OperationsAgent can list/create/update tasks via chat, auto-detects provider |

## Implementation Approach

### Plan Structure (3 plans)

**Plan 1 (Wave 1): Database + API Client Services**
- Migration: `synced_tasks` + `pm_status_mappings` tables
- `LinearService` — GraphQL client: list teams, list issues, create/update issue, list workflow states
- `AsanaService` — REST client: list workspaces/projects, list tasks, create/update task, list sections
- `PMSyncService` — Bidirectional sync orchestrator with status mapping + Redis skip-flag
- Integration endpoints: project listing, sync config, status mapping CRUD

**Plan 2 (Wave 1): Webhook Handlers + Initial Sync**
- Linear webhook handler (HMAC-SHA256 verification, issue create/update events)
- Asana webhook handler (X-Hook-Secret handshake, task create/update events)
- Webhook subscription registration on sync config save
- Initial sync: import last 30 days of issues from selected projects
- Integration router extensions for sync trigger

**Plan 3 (Wave 2, depends on Plans 1+2): Agent Tools + Frontend**
- `PM_TASK_TOOLS` for OperationsAgent (list, create, update, get_projects)
- Provider auto-detection logic
- OperationsAgent instruction update
- Frontend project picker on Linear/Asana cards
- Frontend status mapping UI (dropdown per external state → Pikar state)

## RESEARCH COMPLETE
